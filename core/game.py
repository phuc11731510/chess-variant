# chess-variant\core\game.py
from __future__ import annotations
import sys
from pathlib import Path

# Cho phép chạy trực tiếp file này trên Windows (không đụng venv)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.board import Board
from core.move import Move

def position_key(board: "Board", turn: str) -> str:
  """
  Tạo khóa vị thế gọn & nhanh cho threefold.
  Thành phần: bên sắp đi + toàn bộ quân (kind,color,royal,x,y) + quyền EP.
  - Ưu tiên O(P) đọc từ board._pieces nếu có; fallback quét H×W.
  - EP-rights: lấy ô đích bắt EP (cap_x, cap_y) nếu hợp lệ; else "~".
  """
  items = []
  idx = getattr(board, "_pieces", None)

  if isinstance(idx, dict):
    # New schema: {'w': [(p,x,y),...], 'b': [(p,x,y),...]}
    for bucket in idx.values():
      for entry in bucket:
        # entry chuẩn: (p, x, y)
        if isinstance(entry, (list, tuple)):
          if len(entry) == 3:
            p, x, y = entry
          elif len(entry) == 1 and isinstance(entry[0], (list, tuple)) and len(entry[0]) == 3:
            # phòng trường hợp lồng 1 lớp ((p,x,y),)
            p, x, y = entry[0]
          elif len(entry) == 2:
            # legacy: (x,y) → cần tra p
            x, y = entry
            p = board.at(x, y)
          else:
            continue
        else:
          # entry không phải tuple/list → bỏ qua
          continue
        if p is None:
          continue
        items.append((p.kind, p.color, bool(getattr(p, "_is_royal", False)), int(x), int(y)))

  elif idx:
    # Fallback: iterable phẳng [(p,x,y)] hoặc {(x,y)}
    for entry in idx:
      if isinstance(entry, (list, tuple)):
        if len(entry) == 3:
          p, x, y = entry
        elif len(entry) == 2:
          x, y = entry
          p = board.at(x, y)
        elif len(entry) == 1 and isinstance(entry[0], (list, tuple)):
          inner = entry[0]
          if len(inner) == 3:
            p, x, y = inner
          elif len(inner) == 2:
            x, y = inner
            p = board.at(x, y)
          else:
            continue
        else:
          continue
      else:
        continue
      if p is None:
        continue
      items.append((p.kind, p.color, bool(getattr(p, "_is_royal", False)), int(x), int(y)))

  else:
    # Quét toàn bảng (ít dùng)
    H, W = getattr(board, "h", 10), getattr(board, "w", 10)
    for x in range(H):
      for y in range(W):
        p = board.at(x, y)
        if p:
          items.append((p.kind, p.color, bool(getattr(p, "_is_royal", False)), x, y))

  items.sort(key=lambda t: (t[1], t[0], t[3], t[4]))  # color, kind, x, y

  ep = getattr(board, "en_passant_target", None)
  ep_str = "~"
  if ep and isinstance(ep, (list, tuple)) and len(ep) == 2 and isinstance(ep[0], (list, tuple)) and len(ep[0]) == 2:
    # theo schema hiện tại: ep[0] là ô đích bắt EP (midx, midy)
    ep_str = f"{int(ep[0][0])},{int(ep[0][1])}"

  parts = ["t=", turn, "|p=", ";".join(f"{k},{c},{1 if r else 0},{x},{y}" for k, c, r, x, y in items), "|ep=", ep_str]
  return "".join(parts)

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
  # Demo tối giản: EP đích trống nhưng vẫn tính là bắt → halfmove_clock reset
  b = Board(10, 10)
  b.setup_from_layout()
  g = Game(b, turn="b")
  print(position_key(b,'w'))