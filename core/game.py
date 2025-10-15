# chess-variant\core\game.py
from __future__ import annotations
import sys
from pathlib import Path
from itertools import chain
from random import *
from time import perf_counter

# Cho phép chạy trực tiếp file này trên Windows (không đụng venv)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.board import Board
from core.move import Move

from itertools import chain

def position_key(board: "Board", turn: str) -> str:
  """
  Khóa vị thế (threefold) tối ưu:
    - Duyệt _pieces O(P) bằng một vòng for nhờ chain(['w'],['b']).
    - Fallback quét bảng chỉ khi index rỗng.
  Thành phần: t (turn) + p (k,c,r,x,y) + ep (midx,midy hoặc "~").
  """
  items: list[tuple[str, str, int, int, int]] = []

  idx = getattr(board, "_pieces", None)
  if isinstance(idx, dict):
    entries = chain(idx.get("w", ()), idx.get("b", ()))  # 1 vòng for
    for e in entries:
      if not isinstance(e, (list, tuple)) or len(e) not in (2, 3):
        continue
      if len(e) == 3:
        p, x, y = e
      else:  # (x,y) legacy
        x, y = e
        p = board.at(x, y)
      if p is None:
        continue
      items.append((p.kind, p.color, 1 if getattr(p, "_is_royal", False) else 0, int(x), int(y)))

  elif idx:
    # Iterable phẳng: duyệt 1 vòng for
    for e in idx:
      if not isinstance(e, (list, tuple)) or len(e) not in (2, 3):
        continue
      if len(e) == 3:
        p, x, y = e
      else:
        x, y = e
        p = board.at(x, y)
      if p is None:
        continue
      items.append((p.kind, p.color, 1 if getattr(p, "_is_royal", False) else 0, int(x), int(y)))

  if not items:
    # Fallback duy nhất dùng 2 vòng for (chỉ khi index rỗng → hiếm)
    H, W = getattr(board, "h", 10), getattr(board, "w", 10)
    for x in range(H):
      for y in range(W):
        p = board.at(x, y)
        if p:
          items.append((p.kind, p.color, 1 if getattr(p, "_is_royal", False) else 0, x, y))

  # Thứ tự ổn định
  items.sort(key=lambda t: (t[1], t[0], t[3], t[4], t[2]))

  # EP-rights
  ep = getattr(board, "en_passant_target", None)
  ep_str = "~"
  if (isinstance(ep, (list, tuple)) and len(ep) == 2 and
      isinstance(ep[0], (list, tuple)) and len(ep[0]) == 2):
    midx, midy = int(ep[0][0]), int(ep[0][1])
    ep_str = f"{midx},{midy}"

  pieces_blob = ";".join(f"{k},{c},{r},{x},{y}" for k, c, r, x, y in items)
  return f"t={turn}|p={pieces_blob}|ep={ep_str}"

class Game:
  """
  Bộ điều phối ván cờ ở mức tối thiểu (bước 1):
    - Quản lý lượt đi (self.turn).
    - Quản lý 50-nước (self.halfmove_clock) với tính bắt quân tiền-apply,
      bao gồm cả en passant (đích trống).
  """

  def __init__(self, board: "Board", turn: str = "w") -> None:
    self.board = board
    self.turn = turn
    self.halfmove_clock = 0  # 100 nửa-nước = 50 nước đầy đủ

    self.position_counts: dict[str, int] = {}
    k0 = position_key(self.board, self.turn)  # cần hàm position_key đã có ở trên file
    self.position_counts[k0] = self.position_counts.get(k0, 0) + 1
  
  def result_if_over(self) -> str | None:
    """
    Kết luận ván cờ nếu đã ngã ngũ.
    Ưu tiên:
      1) Hòa threefold nếu có khóa vị thế xuất hiện ≥ 3 lần.
      2) Hòa 50-nước nếu halfmove_clock >= 100.
      3) Dùng Board.result_if_over() nếu có; nếu không, kiểm tra
        Board.is_checkmated(self.turn) và Board.is_stalemated(self.turn).
    Trả về:
      - "draw_threefold" | "draw_50m" | "checkmate_w" | "checkmate_b" | "stalemate" | None
    """
    if getattr(self, "position_counts", None):
      if max(self.position_counts.values(), default=0) >= 3:
        return "draw_threefold"
    if self.halfmove_clock >= 100:
      return "draw_50m"

    b = self.board
    # Nếu Board đã có hàm tổng hợp:
    if hasattr(b, "result_if_over"):
      return b.result_if_over()

    # Fallback: tự kiểm tra nếu Board có các API này
    is_cm = getattr(b, "is_checkmated", None)
    is_sm = getattr(b, "is_stalemated", None)
    if callable(is_cm) and is_cm(self.turn):
      # self.turn là bên SẮP đi và bị chiếu hết đường → checkmate cho đối phương
      return "checkmate_b" if self.turn == "w" else "checkmate_w"
    if callable(is_sm) and is_sm(self.turn):
      return "stalemate"
    return None
  
  def is_fifty_move_rule_draw(self) -> bool:
    """Hòa 50-nước nếu không bắt và không P/Δ di chuyển trong 50 nước."""
    return self.halfmove_clock >= 100
  
  def current_repetitions(self) -> int:
    """Số lần xuất hiện của khóa vị thế hiện tại."""
    return self.position_counts.get(position_key(self.board, self.turn), 0)
  
  def is_threefold(game: "Game") -> bool:
    """Trả về True nếu có vị thế xuất hiện ≥ 3 lần (tiện kiểm tra nhanh)."""
    return max(game.position_counts.values(), default=0) >= 3
      
  def play(self, mv: "Move") -> None:
    """
    Thực thi 1 nước đi:
      - Xác định 'did_capture' TRƯỚC khi apply (EP vẫn là bắt).
      - Gọi board.apply_move(mv).
      - Cập nhật halfmove_clock (reset khi bắt hoặc P/Δ đi), rồi đổi lượt.
    """
    dst = self.board.at(mv.tx, mv.ty)
    did_capture = bool(getattr(mv, "is_en_passant", False) or
                       (dst is not None and dst.color != mv.piece.color))

    self.board.apply_move(mv)

    is_pawn_like = getattr(mv.piece, "kind", "") in {"P", "Δ"}
    self.halfmove_clock = 0 if (did_capture or is_pawn_like) else (self.halfmove_clock + 1)
    self.turn = "b" if self.turn == "w" else "w"
    
    # Ghi nhận key sau-apply cho threefold
    k = position_key(self.board, self.turn)
    self.position_counts[k] = self.position_counts.get(k, 0) + 1



if __name__ == "__main__":
  Danh_Sach_O=[(i, j) for i in range(10) for j in range(10)]
  Danh_Sach_Quan=["K","Q","R","N","M","V","δ","Y","H"]
  while True:
    b=Board()
    g=Game(b,turn='w')
    Danh_Sach_60_O=sample(Danh_Sach_O,60)
    Danh_Sach_60_Quan=choices(Danh_Sach_Quan,k=60)
    for i in range(30):
      x,y=Danh_Sach_60_O[i]
      kind,color=Danh_Sach_60_Quan[i],'w'
      g.board.put(x,y,kind,color)
    for i in range(30,60):
      x,y=Danh_Sach_60_O[i]
      kind,color=Danh_Sach_60_Quan[i],'b'
      g.board.put(x,y,kind,color)
    t1=perf_counter()
    
    print(g.board)
    break