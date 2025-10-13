# chess-variant\core\core.py

def to_alg(x: int, y: int, h: int = 10, w: int = 10) -> str:
  """
  Đổi (x,y) → ký hiệu file-rank (ví dụ 'A1') cho bàn h×w.
  Quy ước:
    - Gốc (0,0) ở góc trên-trái; x tăng xuống, y sang phải.
    - Rank chuẩn cờ: rank = h - x (hàng dưới cùng là rank 1).
    - File theo cột y, dùng A..Z, chỉ hỗ trợ w ≤ 26.
  Raises:
    ValueError: nếu ngoài biên hoặc w > 26.
  """
  if not (0 <= x < h and 0 <= y < w):
    raise ValueError(f"Tọa độ ngoài biên: (x={x}, y={y}) cho bảng {h}×{w}.")
  if w > 26:
    raise ValueError("to_alg chỉ hỗ trợ w ≤ 26 (file A..Z).")
  file_ch = chr(ord('A') + y)
  rank = h - x
  return f"{file_ch}{rank}"

def from_alg(coord: str, h: int = 10, w: int = 10) -> tuple[int, int]:
  """
  Đổi ký hiệu file-rank (ví dụ 'A1') → (x,y) cho bàn h×w.
  Quy ước:
    - Không phân biệt hoa/thường cho file.
    - x = h - rank, y = file - 'A'.
    - Chỉ hỗ trợ 1 ký tự file (A..Z) → w ≤ 26.
  Raises:
    ValueError: nếu ký hiệu không hợp lệ hoặc ngoài biên.
  """
  if w > 26:
    raise ValueError("from_alg chỉ hỗ trợ w ≤ 26 (file A..Z).")
  s = coord.strip().upper()
  if len(s) < 2 or not s[0].isalpha():
    raise ValueError(f"Ký hiệu không hợp lệ: '{coord}'.")
  file_ch = s[0]
  if not ('A' <= file_ch <= 'Z'):
    raise ValueError(f"File không hợp lệ: '{file_ch}'.")
  try:
    rank = int(s[1:])
  except Exception as e:
    raise ValueError(f"Rank không hợp lệ: '{s[1:]}'.") from e
  if not (1 <= rank <= h):
    raise ValueError(f"Rank ngoài biên: {rank} cho bảng cao {h}.")
  y = ord(file_ch) - ord('A')
  x = h - rank
  if not (0 <= y < w):
    raise ValueError(f"File ngoài biên: {file_ch} cho bảng rộng {w}.")
  return (x, y)

if __name__ == "__main__":
  # Demo ngắn (Windows/terminal)
  H, W = 10, 10
  print(to_alg(9, 0, H, W))   # A1
  print(to_alg(0, 9, H, W))   # J10
  print(from_alg("a1", H, W)) # (9, 0)
  print(from_alg("j10", H, W))# (0, 9)