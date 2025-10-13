# # chess-variant\core\piece_factory.py
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from typing import Callable, Dict
from core.piece import Piece
# === BỔ SUNG: import các quân chuẩn (tên lớp có thể đã sẵn trong core/piece.py) ===
from core.piece import King, Queen, Rook, Knight, Pawn
# === Giữ import fairy như bạn đã làm ===
from core.fairy import General, Wildebeest, Alibaba, Sergeant, Archbishop
# Registry đầy đủ: 6 quân chuẩn + 5 quân fairy bạn dùng
PIECE_REGISTRY: Dict[str, Callable[[str], Piece]] = {
  # --- Standard ---
  "K": King,
  "Q": Queen,
  "R": Rook,
  "N": Knight,
  "P": Pawn,
  # --- Fairy (bạn yêu cầu) ---
  "M": General,     # General (Mann)
  "V": Wildebeest,  # Wildebeest
  "Y": Alibaba,     # Alibaba
  "δ": Sergeant,    # Sergeant (delta)
  "H": Archbishop,  # Archbishop
}

def create(kind: str, color: str) -> Piece:
  """
  Tạo một quân cờ từ mã (kind) và màu (color).
  Args:
    kind: 'K','Q','R','B','N','P' hoặc 'M','V','Y','δ','H'
    color: 'w' hoặc 'b'
  Returns:
    Instance của Piece tương ứng.
  Raises:
    KeyError: nếu kind chưa được đăng ký.
  """
  try:
    return PIECE_REGISTRY[kind](color)
  except KeyError as e:
    raise KeyError(f"Unknown piece kind: {kind!r}") from e

if __name__ == "__main__":
  # Client code rất ngắn: in thử glyph xác nhận registry
  samples = [("K","w"), ("Q","b"), ("R","w"), ("B","b"), ("N","w"), ("P","b"),
             ("M","w"), ("V","b"), ("Y","w"), ("δ","b"), ("H","w")]
  for k, c in samples:
    p = create(k, c)
    side = "white" if p.is_white() else "black"
    print(f"{k}({side}) -> {p.glyph()}")
