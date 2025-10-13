# chess-variant\core\move.py
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Tránh vòng phụ thuộc lúc runtime; chỉ dùng cho type hints
    from core.piece import Piece

@dataclass(slots=True)
class Move:
  """
  Thùng chứa (container) nước đi nhẹ, dùng cho pseudo/legal moves.
  Hệ toạ độ: (x, y) với x tăng xuống dưới, y tăng sang phải.
  Flags:
    - is_double_step: Tốt/Sergeant đi 2 ô.
    - is_en_passant : Bắt en passant.
    - promotion_to  : Ký hiệu quân phong cấp (vd 'Q','R','B','N',...), hoặc None.
  """
  fx: int
  fy: int
  tx: int
  ty: int
  piece: "Piece"
  is_double_step: bool = False
  is_en_passant: bool = False
  promotion_to: str | None = None
  
  def __repr__(self) -> str:
    """Chuỗi mô tả thân thiện để debug:
    - piece_tag: 'wP'/'bN' nếu có color & symbol; fallback là tên lớp.
    - toạ độ dạng (fx,fy)->(tx,ty).
    - cờ hiển thị gọn: [double], [en-passant], [promote=Q].
    """
    color = getattr(self.piece, "color", None)   # kỳ vọng 'w' hoặc 'b'
    symbol = getattr(self.piece, "symbol", None) # kỳ vọng 'P','N','δ',...
    if color and symbol:
      piece_tag = f"{color}{symbol}"
    else:
      piece_tag = self.piece.__class__.__name__

    core = f"{piece_tag} ({self.fx},{self.fy})->({self.tx},{self.ty})"

    flags: list[str] = []
    if self.is_double_step:
      flags.append("double")
    if self.is_en_passant:
      flags.append("en-passant")
    if self.promotion_to:
      flags.append(f"promote={self.promotion_to}")

    return f"<Move {core}{(' [' + '; '.join(flags) + ']') if flags else ''}>"

if __name__=="__main__":
  M=Move()
  print(M.fx)