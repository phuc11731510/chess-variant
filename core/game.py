# chess-variant\core\game.py
from __future__ import annotations
import sys
from pathlib import Path

# Cho phép chạy trực tiếp file này trên Windows (không đụng venv)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.board import Board
from core.move import Move


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
  b.put(3, 3, "P", "w")      # trắng
  b.put(1, 4, "P", "b")      # đen
  g = Game(b, turn="b")
  print(b)
  # # Đen double-step để mở EP (giả sử luật cho phép):
  g.play(Move(1, 4, 3, 4, b.at(1, 4), is_double_step=True))
  print(b)
  # Trắng bắt EP: đích (2,4) trống nhưng là capture:
  g.play(Move(3, 3, 2, 4, b.at(3, 3), is_en_passant=True))
  print("halfmove_clock:", g.halfmove_clock, "turn:", g.turn)
  print(b)