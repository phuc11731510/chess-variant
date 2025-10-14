# chess-variant\core\game.py
from __future__ import annotations
import sys
from pathlib import Path
from itertools import chain

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


if __name__ == "__main__":
  """
  Mock test ngắn (không assert) để kiểm thử:
    1) position_key trước/sau double-step mở EP.
    2) EP-capture làm halfmove_clock reset và ep=~.
    3) Đếm lặp vị thế qua position_counts.
  """

  b = Board(10, 10)

  # Đặt ít quân đủ tái hiện EP:
  # Trắng đi xuống (x+1), Đen đi lên (x-1).
  b.put(3, 3, "P", "w")  # White pawn tại (3,3)
  b.put(1, 4, "P", "b")  # Black pawn tại (1,4)

  # # Game tối giản: chỉ quản lý turn + halfmove + position_counts
  g = Game(b, turn="b")

  print(b)
  
  print("== START ==")
  k0 = position_key(b, g.turn)
  print("Turn:", g.turn, "| Key:", k0)
  print("Repetitions of current key:", g.position_counts.get(k0, 0))
  # print("Halfmove clock:", g.halfmove_clock)
  # print("-")

  # # Nước 1 (Đen): double-step (1,4)->(3,4) để mở EP
  # mv_b_ds = Move(1, 4, 3, 4, b.at(1, 4), is_double_step=True)
  # g.play(mv_b_ds)

  # k1 = position_key(b, g.turn)  # Sau khi đổi lượt → đến Trắng
  # print("After Black double-step")
  # print("Turn:", g.turn, "| Key:", k1)
  # print("EP should be set (ep!=~). Key tail:", k1.split("|ep=")[-1])
  # print("Repetitions of current key:", g.position_counts.get(k1, 0))
  # print("Halfmove clock (should NOT reset yet):", g.halfmove_clock)
  # print("-")

  # # Nước 2 (Trắng): bắt EP (3,3)->(2,4) — đích trống nhưng là capture
  # mv_w_ep = Move(3, 3, 2, 4, b.at(3, 3), is_en_passant=True)
  # g.play(mv_w_ep)

  # k2 = position_key(b, g.turn)  # Sau khi đổi lượt → đến Đen
  # print("After White EP capture")
  # print("Turn:", g.turn, "| Key:", k2)
  # print("EP should be cleared (ep=~). Key tail:", k2.split("|ep=")[-1])
  # print("Repetitions of current key:", g.position_counts.get(k2, 0))
  # print("Halfmove clock (should RESET to 0):", g.halfmove_clock)
  # print("-")

  # # Minh họa threefold (đơn giản): in đếm key hiện tại rồi lặp lại chính key đó 2 lần
  # # (Ở đây không phát sinh nước đi để quay lại vị thế y hệt; chỉ minh họa cơ chế đếm.)
  # # Trong thực tế, bạn hãy tạo chuỗi nước đi qua lại để quay về cùng key.
  # for i in range(2):
  #   k = position_key(b, g.turn)
  #   g.position_counts[k] = g.position_counts.get(k, 0) + 1
  #   print(f"Manual bump #{i+1} → repetitions of current key:", g.position_counts[k])

  # print("== END ==")
