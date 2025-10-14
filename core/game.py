# chess-variant\core\game.py
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.board import Board
from core.move import Move

class Game:
  """
  Orchestrator cấp cao cho ván cờ:
  - Giữ `board`, lượt đi hiện tại (`turn`: 'w'|'b').
  - Quản lí bộ đếm 50-nước và bản đồ lặp lại vị thế (repetition).
  - Sau này sẽ mở rộng: vòng lặp CLI, parse nước đi 'e2e4', logging, v.v.

  Thiết kế:
  - Trách nhiệm cập nhật rule-counters tách khỏi Board (nguyên tắc SRP).
  - Khóa lặp lại tạm thời dựa trên `turn` + `board.as_ascii()` (đủ dùng trước khi có hashing).
  """

  def __init__(self, board: "Board", turn: str = "w") -> None:
    self.board = board
    self.turn: str = turn  # 'w' hoặc 'b'
    self.halfmove_clock: int = 0
    self.position_counts: dict[str, int] = {}
    # Ghi nhận vị thế ban đầu (bên sẽ đi trước)
    initial_key = f"{self.turn}|{self.board.as_ascii()}"
    self.position_counts[initial_key] = self.position_counts.get(initial_key, 0) + 1

  def update_rule_counters(self, mv: "Move", did_capture: bool) -> None:
    """
    Cập nhật bộ đếm 50-nước và bảng đếm lặp lại sau khi đã áp dụng `mv` lên `self.board`.

    Quy ước gọi:
      - `self.board` ĐÃ apply xong nước `mv` trước khi gọi hàm này.
      - `did_capture` = True nếu nước đi vừa rồi có bắt quân (kể cả en passant).

    Hành vi:
      1) 50-nước: reset nếu là nước đi của Tốt/Sergeant hoặc có bắt quân; ngược lại +1.
      2) Đổi lượt `self.turn` ('w' <-> 'b').
      3) Repetition-map: tạo khóa đơn giản = f"{turn}|{board.as_ascii()}" và tăng đếm.

    Ghi chú:
      - Nhận diện Tốt/Sergeant qua `mv.piece.kind` ∈ {'P','Δ'} (giữ tương thích ký hiệu hiện tại).
      - Sau này có thể thay `as_ascii()` bằng hashing (Zobrist) để mạnh hơn và nhanh hơn.
    """
    is_pawn_like = getattr(mv.piece, "kind", "") in {"P", "Δ"}
    if did_capture or is_pawn_like:
      self.halfmove_clock = 0
    else:
      self.halfmove_clock += 1

    # Đổi lượt
    self.turn = "b" if self.turn == "w" else "w"

    # Cập nhật đếm lặp lại (bao gồm thông tin bên sắp đi)
    key = f"{self.turn}|{self.board.as_ascii()}"
    self.position_counts[key] = self.position_counts.get(key, 0) + 1

if __name__ == "__main__":
  # Mock test tối giản cho Game.update_rule_counters
  b = Board(10, 10)

  # Đặt vài quân tối thiểu để di chuyển: vua không cần thiết cho test này
  b.put(3, 4, "P", "w")   # White Pawn ở (3,4) sẽ đi xuống (4,4)
  b.put(5, 6, "N", "b")   # Black Knight ở (5,6) sẽ nhảy tới (3,5)

  g = Game(b, turn="w")

  # Kiểm tra vị thế ban đầu đã được đếm
  init_key = f"{g.turn}|{b.as_ascii()}"
  print(b)
  
  # 1) White Pawn tiến 1 ô, không bắt
  mv1 = Move(3, 4, 2, 4, b.at(3, 4))
  pre_dst = b.at(mv1.tx, mv1.ty)
  did_capture = pre_dst is not None and getattr(pre_dst, "color", None) != mv1.piece.color
  b.apply_move(mv1)
  g.update_rule_counters(mv1, did_capture)
  key_after_mv1 = f"{g.turn}|{b.as_ascii()}"

  print(g.position_counts)
  
  # print("[MV1] halfmove_clock (expect 0) =", g.halfmove_clock)
  # print("[MV1] position_counts[key_after_mv1] =", g.position_counts.get(key_after_mv1, 0))

  # # 2) Black Knight nhảy không bắt
  # mv2 = Move(5, 6, 3, 5, b.at(5, 6))
  # pre_dst2 = b.at(mv2.tx, mv2.ty)
  # did_capture2 = pre_dst2 is not None and getattr(pre_dst2, "color", None) != mv2.piece.color
  # b.apply_move(mv2)
  # g.update_rule_counters(mv2, did_capture2)
  # key_after_mv2 = f"{g.turn}|{b.as_ascii()}"

  # print("[MV2] halfmove_clock (expect 1) =", g.halfmove_clock)
  # print("[MV2] position_counts[key_after_mv2] =", g.position_counts.get(key_after_mv2, 0))