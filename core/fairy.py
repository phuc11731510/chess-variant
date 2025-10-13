# chess-variant\core\fairy.py
from __future__ import annotations
from typing import TYPE_CHECKING
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.piece import Piece
from core.move import Move
if TYPE_CHECKING:
  from core.board import Board

class General(Piece):
  """
  General (Mann) — ký hiệu 'M'.
  Giai đoạn này: chỉ nhận diện/glyph; chưa sinh nước đi.
  """
  __slots__ = ()
  def __init__(self, color: str) -> None:
    """Khởi tạo General với color = 'w' hoặc 'b'."""
    super().__init__("M", color)
    
  def can_attack(self, board: "Board", sx: int, sy: int, tx: int, ty: int) -> bool:
    """
    Trả về True nếu General (M) tại (sx, sy) khống chế ô (tx, ty).
    - M = K + N: khống chế như King (1 ô kề, gồm chéo) HOẶC như Knight (L-jump).
    - Độ phức tạp: O(1). Không xét lượt, EP hay “royal safety”.
    """
    dx = tx - sx
    dy = ty - sy
    if dx < 0: dx = -dx
    if dy < 0: dy = -dy
    # King-like (mọi ô kề, trừ chính nó)
    if (dx | dy) != 0 and max(dx, dy) == 1:
      return True
    # Knight-like (L-jump)
    return (dx == 1 and dy == 2) or (dx == 2 and dy == 1)
    
  def generate_moves(self, board: "Board", x: int, y: int) -> list[Move]:
    """
    Pseudo-legal moves cho General (M):
      - Kết hợp: King-like (8 hướng, 1 ô) + Knight-like (8 bước chữ L).
      - Không đi vào ô có quân cùng màu; được capture quân khác màu.
      - Chưa kiểm tra an toàn cho royal (lọc chiếu).
    Args:
      board: Bàn cờ hiện tại.
      x, y: Tọa độ quân (gốc trên-trái; x xuống, y sang phải).
    Returns:
      list[Move]: Danh sách nước đi/capture (pseudo-legal).
    """
    king_deltas = [(-1,-1), (-1,0), (-1,1),
                  ( 0,-1),         ( 0,1),
                  ( 1,-1), ( 1,0), ( 1,1)]
    knight_deltas = [(-2,-1), (-2, 1), (-1,-2), (-1, 2),
                    ( 1,-2), ( 1, 2), ( 2,-1), ( 2, 1)]

    moves: list[Move] = []
    seen: set[tuple[int, int]] = set()

    # King-like
    for dx, dy in king_deltas:
      nx, ny = x + dx, y + dy
      if 0 <= nx < board.h and 0 <= ny < board.w:
        target = board.at(nx, ny)
        if target is None or target.color != self.color:
          if (nx, ny) not in seen:
            seen.add((nx, ny))
            moves.append(Move(x, y, nx, ny, self))

    # Knight-like
    for dx, dy in knight_deltas:
      nx, ny = x + dx, y + dy
      if 0 <= nx < board.h and 0 <= ny < board.w:
        target = board.at(nx, ny)
        if target is None or target.color != self.color:
          if (nx, ny) not in seen:
            seen.add((nx, ny))
            moves.append(Move(x, y, nx, ny, self))

    return moves
    
class Wildebeest(Piece):
  """
  Wildebeest — ký hiệu 'V'.
  Giai đoạn này: chỉ nhận diện/glyph; chưa sinh nước đi.
  """
  __slots__ = ()
  def __init__(self, color: str) -> None:
    """Khởi tạo Wildebeest với color = 'w' hoặc 'b'."""
    super().__init__("V", color)
  
  def can_attack(self, board: "Board", sx: int, sy: int, tx: int, ty: int) -> bool:
    """
    Trả về True nếu Wildebeest (V) tại (sx, sy) khống chế ô (tx, ty).
    - V = Knight (1,2) + Camel (3,1) — đều là leaper, không cần đường trống.
    - Độ phức tạp: O(1). Không xét lượt/EP/“royal safety”.
    """
    dx = tx - sx
    dy = ty - sy
    if dx < 0: dx = -dx
    if dy < 0: dy = -dy
    # Knight (1,2) hoặc (2,1) — OR — Camel (1,3) hoặc (3,1)
    return ((dx == 1 and dy == 2) or (dx == 2 and dy == 1) or
            (dx == 1 and dy == 3) or (dx == 3 and dy == 1))
  
  def generate_moves(self, board: "Board", x: int, y: int) -> list[Move]:
    """
    Pseudo-legal moves cho Wildebeest (V):
      - Leaper: Knight (±2,±1; ±1,±2) + Camel (±3,±1; ±1,±3).
      - Không bị cản; không vào ô có quân cùng màu; được capture quân khác màu.
      - Chưa kiểm tra an toàn royal.
    Args:
      board: Bàn cờ hiện tại.
      x, y : Tọa độ (gốc trên-trái; x xuống, y sang phải).
    Returns:
      list[Move]: Danh sách nước đi/capture (pseudo-legal).
    """
    knight = [(-2,-1), (-2, 1), (-1,-2), (-1, 2),
              ( 1,-2), ( 1, 2), ( 2,-1), ( 2, 1)]
    camel  = [(-3,-1), (-3, 1), (-1,-3), (-1, 3),
              ( 1,-3), ( 1, 3), ( 3,-1), ( 3, 1)]
    deltas = knight + camel

    moves: list[Move] = []
    seen: set[tuple[int, int]] = set()

    for dx, dy in deltas:
      nx, ny = x + dx, y + dy
      if 0 <= nx < board.h and 0 <= ny < board.w:
        target = board.at(nx, ny)
        if target is None or target.color != self.color:
          if (nx, ny) not in seen:
            seen.add((nx, ny))
            moves.append(Move(x, y, nx, ny, self))
    return moves
    
class Alibaba(Piece):
  """
  Alibaba — ký hiệu 'Y'.
  Giai đoạn này: chỉ nhận diện/glyph; chưa sinh nước đi.
  """
  __slots__ = ()
  def __init__(self, color: str) -> None:
    """Khởi tạo Alibaba với color = 'w' hoặc 'b'."""
    super().__init__("Y", color)
  
  def can_attack(self, board: "Board", sx: int, sy: int, tx: int, ty: int) -> bool:
    """
    Trả về True nếu Alibaba (Y) tại (sx, sy) khống chế ô (tx, ty).
    - Quy tắc: nhảy đúng 2 ô theo 8 hướng (như King nhưng dài hơn 1 ô, có thể nhảy).
      • Orthogonal: |dx|=2, dy=0 hoặc dx=0, |dy|=2
      • Diagonal  : |dx|=|dy|=2
    - Độ phức tạp: O(1). Không xét lượt/EP/“royal safety”.
    """
    dx = tx - sx
    dy = ty - sy
    if dx < 0: dx = -dx
    if dy < 0: dy = -dy
    if dx == 2 and dy == 0:  # 2 ô thẳng dọc
      return True
    if dx == 0 and dy == 2:  # 2 ô thẳng ngang
      return True
    if dx == 2 and dy == 2:  # 2 ô chéo
      return True
    return False
  
  def generate_moves(self, board: "Board", x: int, y: int) -> list[Move]:
    """
    Pseudo-legal moves cho Alibaba (Y):
      - Di chuyển theo 8 hướng của King nhưng với bước dài 2 ô: (±2,0), (0,±2), (±2,±2).
      - Là leaper: có thể nhảy qua quân khác.
      - Không vào ô có quân cùng màu; được capture quân khác màu.
      - Chưa kiểm tra an toàn cho royal (lọc chiếu).
    Args:
      board: Bàn cờ hiện tại.
      x, y : Tọa độ (gốc trên-trái; x xuống, y sang phải).
    Returns:
      list[Move]: Danh sách nước đi/capture (pseudo-legal).
    """
    deltas = [(-2,-2), (-2, 0), (-2, 2),
              ( 0,-2),          ( 0, 2),
              ( 2,-2), ( 2, 0), ( 2, 2)]
    moves: list[Move] = []
    for dx, dy in deltas:
      nx, ny = x + dx, y + dy
      if 0 <= nx < board.h and 0 <= ny < board.w:
        target = board.at(nx, ny)
        if target is None or target.color != self.color:
          moves.append(Move(x, y, nx, ny, self))
    return moves
  
class Sergeant(Piece):
  """
  Sergeant — ký hiệu 'δ' (delta).
  Giai đoạn này: chỉ nhận diện/glyph; chưa sinh nước đi.
  """
  __slots__ = ()
  def __init__(self, color: str) -> None:
    """Khởi tạo Sergeant với color = 'w' hoặc 'b'."""
    super().__init__("δ", color)
    
  def can_attack(self, board: "Board", sx: int, sy: int, tx: int, ty: int) -> bool:
    """
    Trả về True nếu Sergeant (δ) tại (sx, sy) khống chế ô (tx, ty).
    Quy tắc khống chế:
      - PHỤ THUỘC MÀU: đi "lên" theo hướng của màu.
        • Trắng: dx = -1 (lên trên).
        • Đen  : dx = +1 (xuống dưới).
      - Một bước: THẲNG hoặc CHÉO về phía trước (3 ô trước mặt).
        → Hợp lệ khi: tx == sx + step và |ty - sy| ∈ {0,1}.
    Không xét EP/lượt/“royal safety”. Độ phức tạp: O(1).
    """
    step = -1 if self.color == 'w' else 1
    if tx != sx + step:
      return False
    dy = ty - sy
    if dy < 0: dy = -dy
    return dy <= 1
    
  def _in_bounds(self, board: "Board", i: int, j: int) -> bool:
    """Trả về True nếu (i,j) nằm trong biên bàn cờ; False nếu ngoài biên.
    Không ném ngoại lệ. Dùng board.at(...) để tận dụng kiểm tra sẵn có."""
    try:
      board.at(i, j)
      return True
    except Exception:
      return False
    
  def _safe_at(self, board: "Board", i: int, j: int):
    """Trả về Piece ở (i,j) nếu trong biên, ngược lại trả về None.
    Không ném ngoại lệ ngay cả khi ngoài biên."""
    if not self._in_bounds(board, i, j):
      return None
    return board.at(i, j)
  
  def _emit_step(self,
                board: "Board",
                x: int, y: int,
                nx: int, ny: int,
                moves: list["Move"],
                promo_row: int,
                promo_syms: list[str],
                ep) -> None:
    """Thêm nước đi 1-bước (thẳng/chéo), gồm thường, phong cấp, và en passant.
    Ghi chú EP: schema dạng danh sách/tuple 2 phần tử: [(midx,midy),(tx,ty)]."""
    if not self._in_bounds(board, nx, ny):
      return
    target = self._safe_at(board, nx, ny)
    if target is not None and target.color == self.color:
      return  # chặn đi/ăn quân mình

    # Phong cấp khi chạm hàng phong
    if nx == promo_row:
      for cand in promo_syms:
        moves.append(Move(x, y, nx, ny, self, promotion_to=cand))
      return

    # En passant an toàn
    if ep and isinstance(ep, (list, tuple)) and len(ep) == 2:
      ep_dst, ep_victim = ep[0], ep[1]
      if isinstance(ep_dst, (list, tuple)) and isinstance(ep_victim, (list, tuple)):
        if (nx, ny) == (int(ep_dst[0]), int(ep_dst[1])):
          vx, vy = int(ep_victim[0]), int(ep_victim[1])
          victim = self._safe_at(board, vx, vy)
          if victim is not None and victim.color != self.color:
            moves.append(Move(x, y, nx, ny, self, is_en_passant=True))
            return

    # Nước đi/ăn thường
    moves.append(Move(x, y, nx, ny, self))
  
  def generate_moves(self, board: "Board", x: int, y: int) -> list[Move]:
    """
    Pseudo-legal moves cho Sergeant (δ):
      - 1 bước: thẳng hoặc chéo (trái/phải).
      - 2 bước từ HAI hàng xuất phát: thẳng/chéo; ô trung gian & đích đều trống; is_double_step=True.
      - En passant: ep == [(midx,midy), (tx,ty)] (generator chỉ gắn cờ).
      - Phong cấp: khi chạm hàng phong cấp (board.promotion_row(...)).
    """
    moves: list[Move] = []

    dx = -1 if self.color == 'w' else 1
    side = 'white' if self.color == 'w' else 'black'

    start_rows: set[int] = board.pawn_start_rows(side)
    promo_row: int = board.promotion_row(side)
    promo_syms: list[str] = board.promotion_candidates()
    ep = board.en_passant_target

    # 1-bước: thẳng, chéo trái, chéo phải
    self._emit_step(board, x, y, x + dx, y, moves, promo_row, promo_syms, ep)
    self._emit_step(board, x, y, x + dx, y - 1, moves, promo_row, promo_syms, ep)
    self._emit_step(board, x, y, x + dx, y + 1, moves, promo_row, promo_syms, ep)

    # 2-bước (chỉ nếu đang ở hàng xuất phát)
    nx2 = x + 2 * dx
    if x in start_rows:
      # thẳng 2
      if (self._in_bounds(board, x + dx, y) and self._safe_at(board, x + dx, y) is None and
          self._in_bounds(board, nx2, y) and self._safe_at(board, nx2, y) is None):
        moves.append(Move(x, y, nx2, y, self, is_double_step=True))
      # chéo trái 2
      if (self._in_bounds(board, x + dx, y - 1) and self._safe_at(board, x + dx, y - 1) is None and
          self._in_bounds(board, nx2, y - 2) and self._safe_at(board, nx2, y - 2) is None):
        moves.append(Move(x, y, nx2, y - 2, self, is_double_step=True))
      # chéo phải 2
      if (self._in_bounds(board, x + dx, y + 1) and self._safe_at(board, x + dx, y + 1) is None and
          self._in_bounds(board, nx2, y + 2) and self._safe_at(board, nx2, y + 2) is None):
        moves.append(Move(x, y, nx2, y + 2, self, is_double_step=True))

    return moves
    
class Archbishop(Piece):
  """
  Archbishop (Cardinal) — ký hiệu 'H'.
  Giai đoạn này: chỉ nhận diện/glyph; chưa sinh nước đi.
  (Sau này: Bishop rider + Knight leaper.)
  """
  __slots__ = ()
  def __init__(self, color: str) -> None:
    """Khởi tạo Archbishop với color = 'w' hoặc 'b'."""
    super().__init__("H", color)
  
  def can_attack(self, board: "Board", sx: int, sy: int, tx: int, ty: int) -> bool:
    """
    Trả về True nếu Archbishop (H) tại (sx, sy) khống chế ô (tx, ty).
    - H = Bishop (tia chéo, bị chặn) + Knight (L-jump, không bị chặn).
    - Độ phức tạp: Knight O(1), Bishop O(|khoảng cách|). Không xét lượt/EP/“royal safety”.
    """
    dx = tx - sx
    dy = ty - sy
    if dx < 0: dx = -dx
    if dy < 0: dy = -dy

    # Knight (1,2)/(2,1)
    if (dx == 1 and dy == 2) or (dx == 2 and dy == 1):
      return True

    # Bishop: cùng độ lệch |dx|==|dy|, quét tia chéo
    if dx == dy and dx != 0:
      at = board.at
      stepx = 1 if tx > sx else -1
      stepy = 1 if ty > sy else -1
      x, y = sx + stepx, sy + stepy
      while x != tx and y != ty:
        if at(x, y) is not None:
          return False
        x += stepx
        y += stepy
      return True

    return False
  
  def generate_moves(self, board: "Board", x: int, y: int) -> list[Move]:
    """
    Pseudo-legal moves cho Archbishop (H):
      - Knight-like: 8 bước (±2,±1), (±1,±2), nhảy qua quân khác.
      - Bishop-like: trượt 4 hướng chéo đến khi bị chặn; capture quân khác màu.
      - Không vào ô có quân cùng màu. Chưa kiểm tra an toàn cho royal.
    Args:
      board: Bàn cờ hiện tại.
      x, y:  Tọa độ quân (gốc trên-trái; x xuống, y sang phải).
    Returns:
      list[Move]: Danh sách nước đi/capture (pseudo-legal).
    """
    moves: list[Move] = []
    seen: set[tuple[int, int]] = set()

    # 1) Knight-like (leaper)
    k_deltas = [(-2,-1), (-2, 1), (-1,-2), (-1, 2),
                ( 1,-2), ( 1, 2), ( 2,-1), ( 2, 1)]
    for dx, dy in k_deltas:
      nx, ny = x + dx, y + dy
      if 0 <= nx < board.h and 0 <= ny < board.w:
        t = board.at(nx, ny)
        if t is None or t.color != self.color:
          if (nx, ny) not in seen:
            seen.add((nx, ny))
            moves.append(Move(x, y, nx, ny, self))

    # 2) Bishop-like (sliding on diagonals)
    for dx, dy in [(-1,-1), (-1, 1), (1,-1), (1, 1)]:
      nx, ny = x + dx, y + dy
      while 0 <= nx < board.h and 0 <= ny < board.w:
        t = board.at(nx, ny)
        if t is None:
          if (nx, ny) not in seen:
            seen.add((nx, ny))
            moves.append(Move(x, y, nx, ny, self))
        else:
          if t.color != self.color:
            if (nx, ny) not in seen:
              seen.add((nx, ny))
              moves.append(Move(x, y, nx, ny, self))  # capture
          break
        nx += dx
        ny += dy

    return moves
    
if __name__ == "__main__":
  """
  Client code nhỏ: in glyph để kiểm tra mapping kind-letter.
  Ví dụ đầu ra: General(w) -> wM
  """
  samples = [
    General("w"), Wildebeest("b"), Alibaba("w"),
    Sergeant("b"), Archbishop("w"),
  ]
  for p in samples:
    side = "white" if p.is_white() else "black"
    print(f"{p.__class__.__name__}({side}) -> {p.glyph()}")
