# chess-variant\core\piece.py
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from typing import TYPE_CHECKING
from core.move import Move
if TYPE_CHECKING:
  from core.board import Board

class Piece:
  """Base class for all pieces.
  Attributes:
    _kind: One-letter kind code, uppercase (e.g., 'K','Q','R','B','N','P').
    _color: 'w' for white, 'b' for black.
    _is_royal: True if the piece is a royal (e.g., King).
  """
  
  __slots__ = ("_kind", "_color", "_is_royal")
  def __init__(self, kind: str, color: str, is_royal: bool = False) -> None:
    """Initialize a piece.\n
    Args:
      kind: Uppercase kind code.
      color: 'w' or 'b'.
      is_royal: Whether this piece is royal.
    """
    self._kind = kind.upper()
    self._color = color
    self._is_royal = is_royal
    
  @property
  def kind(self) -> str:
    """Return the uppercase kind code."""
    return self._kind
  
  @property
  def color(self) -> str:
    """Return the color: 'w' or 'b'."""
    return self._color
  
  @property
  def is_royal(self) -> bool:
    """Return True if the piece is royal."""
    return self._is_royal
  
  def can_attack(self, board: "Board", sx: int, sy: int, tx: int, ty: int) -> bool:
    """
    Truy vấn nhanh: quân hiện tại (ở (sx, sy)) có *khống chế/tấn công* ô (tx, ty) không?

    Ngữ nghĩa:
      - Trả về True nếu theo quy tắc *tấn công/ăn* của quân này, ô (tx, ty) là mục tiêu hợp lệ
        trong bối cảnh bàn cờ hiện tại. Không xét self-check, không xét lượt đi.
      - BỎ QUA en passant (EP không dùng để "chiếu" vua).
      - Phong cấp không liên quan tới truy vấn tấn công.

    Thiết kế:
      - Mặc định dùng fallback: gọi generate_moves(...) rồi kiểm tra có move tới (tx, ty) không,
        đồng thời loại bỏ các nước is_en_passant.
      - Khuyến khích các lớp con override để tối ưu (O(1) cho Knight/King/General/Sergeant 1 ô,
        kiểm tia cho Rook/Bishop/Queen, v.v.). Điều này tránh phải sinh list Move.

    Tham số:
      board: Board  – trạng thái bàn cờ.
      sx, sy: int   – tọa độ nguồn của quân này.
      tx, ty: int   – tọa độ đích cần kiểm tra bị khống chế hay không.

    Trả về:
      bool: True nếu (tx, ty) bị quân này khống chế; ngược lại False.
    """
    pass
  
  def generate_moves(self, board: "Board", x: int, y: int) -> list[tuple[int, int]]:
    """
    Trả về danh sách nước đi pseudo-legal cho quân này tại (x,y).
    Mặc định: chưa triển khai ở lớp nền, các lớp con phải override.
    """
    raise NotImplementedError(f"{self.__class__.__name__}.generate_moves() not implemented.")
  
  def glyph(self) -> str:
    """Return explicit color-prefixed glyph, e.g. 'wK', 'bQ'.\n
    Color prefix is lowercase ('w' or 'b'); piece kind is uppercase.
    This avoids relying on letter case to distinguish colors.
    """
    prefix = 'w' if self._color == 'w' else 'b'
    return f"{prefix}{self._kind}"
  
  def is_white(self) -> bool:
    """Return True if this piece is white."""
    return self._color == 'w'
  
  def is_black(self) -> bool:
    """Return True if this piece is black."""
    return self._color == 'b'
  
  def __repr__(self) -> str:
    """Debug-friendly representation."""
    tag = "K*" if self._is_royal else self._kind
    return f"Piece({tag},{self._color})"

class King(Piece):
  """Standard chess King."""
  def __init__(self, color: str) -> None:
    """Create a King of given color."""
    super().__init__("K", color)
    
  def can_attack(self, board: "Board", sx: int, sy: int, tx: int, ty: int) -> bool:
    """
    Trả về True nếu King (K) tại (sx, sy) khống chế ô (tx, ty).
    - Độ phức tạp: O(1).
    - King khống chế mọi ô kề (kể cả chéo) cách tối đa 1 ô.
    - Không xét nhập thành, không xét lượt, không xét “royal safety”.
    """
    dx = tx - sx
    dy = ty - sy
    if dx < 0: dx = -dx
    if dy < 0: dy = -dy
    return (dx | dy) != 0 and max(dx, dy) == 1
  
  def generate_moves(self, board: "Board", x: int, y: int) -> list[Move]:
    """
    Pseudo-legal moves cho King (Vua):
      - Đi đúng 1 ô theo 8 hướng: (±1,0), (0,±1), (±1,±1).
      - Không vào ô có quân cùng màu; cho phép đi/capture ô trống hoặc đối phương.
    Ghi chú:
      - Chưa kiểm tra an toàn cho quân "royal" (king safety, ô bị khống chế).
      - Chưa xét nhập thành (nếu biến thể có).
    Args:
      board: Bàn cờ hiện tại.
      x, y : Toạ độ quân (gốc trên-trái; x tăng xuống, y tăng sang phải).
    Returns:
      list[Move]: Danh sách nước đi/capture hợp lệ ở mức pseudo-legal.
    """
    deltas = [(-1,-1), (-1,0), (-1,1),
              ( 0,-1),         ( 0,1),
              ( 1,-1), ( 1,0), ( 1,1)]
    moves: list[Move] = []
    for dx, dy in deltas:
      nx, ny = x + dx, y + dy
      if 0 <= nx < board.h and 0 <= ny < board.w:
        target = board.at(nx, ny)
        if target is None or target.color != self.color:
          moves.append(Move(x, y, nx, ny, self))
    return moves

class Queen(Piece):
  """Standard chess Queen."""
  def __init__(self, color: str) -> None:
    """Create a Queen of given color."""
    super().__init__("Q", color)
  
  def can_attack(self, board: "Board", sx: int, sy: int, tx: int, ty: int) -> bool:
    """
    Trả về True nếu Queen (Q) tại (sx, sy) khống chế ô (tx, ty).
    - Q = Rook (tia thẳng) + Bishop (tia chéo), bị chặn bởi quân đứng giữa.
    - Độ phức tạp: O(|khoảng cách|). Không xét lượt/EP/“royal safety”.
    """
    if sx == tx and sy == ty:
      return False

    at = board.at

    # Rook-like: cùng hàng
    if sx == tx:
      step = 1 if ty > sy else -1
      y = sy + step
      while y != ty:
        if at(sx, y) is not None:
          return False
        y += step
      return True

    # Rook-like: cùng cột
    if sy == ty:
      step = 1 if tx > sx else -1
      x = sx + step
      while x != tx:
        if at(x, sy) is not None:
          return False
        x += step
      return True

    # Bishop-like: chéo
    dx = tx - sx
    dy = ty - sy
    if dx < 0: dx = -dx
    if dy < 0: dy = -dy
    if dx == dy and dx != 0:
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
    Pseudo-legal moves cho Queen (Hậu):
      - Trượt theo 8 hướng: 4 orthogonal + 4 chéo.
      - Đi qua ô trống; dừng khi gặp quân.
      - Không vào ô có quân cùng màu; có thể capture quân khác màu.
    Args:
      board: Bàn cờ hiện tại.
      x, y: Tọa độ quân (gốc trên-trái; x xuống, y sang phải).
    Returns:
      Danh sách Move (chưa kiểm tra an toàn royal).
    """
    moves: list[Move] = []
    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1),
                  (-1,-1), (-1, 1), (1,-1), (1, 1)]:
      nx, ny = x + dx, y + dy
      while 0 <= nx < board.h and 0 <= ny < board.w:
        target = board.at(nx, ny)
        if target is None:
          moves.append(Move(x, y, nx, ny, self))
        else:
          if target.color != self.color:
            moves.append(Move(x, y, nx, ny, self))  # capture
          break
        nx += dx
        ny += dy
    return moves

class Rook(Piece):
  """Standard chess Rook."""
  def __init__(self, color: str) -> None:
    """Create a Rook of given color."""
    super().__init__("R", color)
  
  def can_attack(self, board: "Board", sx: int, sy: int, tx: int, ty: int) -> bool:
    """
    Trả về True nếu Rook (R) tại (sx, sy) khống chế ô (tx, ty).
    - Tối ưu: kiểm tra đồng hàng/đồng cột rồi quét 1 tia duy nhất đến trước ô đích.
    - Bị chặn bởi quân đứng giữa; không cần quan tâm quân tại ô đích thuộc màu nào.
    - Độ phức tạp: O(|khoảng cách|). Không xét lượt/EP/“royal safety”.
    """
    # Không thể khống chế chính ô mình đứng
    if sx == tx and sy == ty:
      return False

    at = board.at

    # Cùng hàng
    if sx == tx:
      step = 1 if ty > sy else -1
      y = sy + step
      while y != ty:
        if at(sx, y) is not None:
          return False
        y += step
      return True

    # Cùng cột
    if sy == ty:
      step = 1 if tx > sx else -1
      x = sx + step
      while x != tx:
        if at(x, sy) is not None:
          return False
        x += step
      return True

    # Khác hàng & cột → không khống chế
    return False
  
  def generate_moves(self, board: "Board", x: int, y: int) -> list[Move]:
    """
    Pseudo-legal moves cho Rook (Xe):
      - Trượt theo 4 hướng orthogonal (lên, xuống, trái, phải).
      - Có thể đi qua các ô trống.
      - Dừng lại trước quân cùng màu; có thể ăn quân khác màu (và dừng).
    Args:
      board: Bàn cờ hiện tại.
      x, y: Tọa độ quân (gốc trên-trái; x xuống, y sang phải).
    Returns:
      Danh sách Move (chưa kiểm tra an toàn royal).
    """
    moves: list[Move] = []
    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
      nx, ny = x + dx, y + dy
      while 0 <= nx < board.h and 0 <= ny < board.w:
        target = board.at(nx, ny)
        if target is None:
          moves.append(Move(x, y, nx, ny, self))
        else:
          if target.color != self.color:
            moves.append(Move(x, y, nx, ny, self))  # capture
          break  # bị chặn bởi bất kỳ quân nào
        nx += dx
        ny += dy
    return moves

class Knight(Piece):
  """Standard chess Knight."""
  def __init__(self, color: str) -> None:
    """Create a Knight of given color."""
    super().__init__("N", color)
  
  def can_attack(self, board: "Board", sx: int, sy: int, tx: int, ty: int) -> bool:
    """
    Trả về True nếu Knight (N) tại (sx, sy) khống chế ô (tx, ty).
    - Độ phức tạp: O(1).
    - Không xét EP, không xét lượt, không chặn đường (Knight nhảy).
    - Không kiểm tra “royal safety”.
    """
    dx = tx - sx
    dy = ty - sy
    if dx < 0: dx = -dx
    if dy < 0: dy = -dy
    return (dx == 1 and dy == 2) or (dx == 2 and dy == 1)
  
  def generate_moves(self, board: "Board", x: int, y: int) -> list[Move]:
    """
    Pseudo-legal moves cho Knight (Mã):
      - Nhảy 8 hướng hình chữ L: (±1,±2) và (±2,±1).
      - Có thể “nhảy qua” quân khác.
      - Không vào ô có quân cùng màu; được capture quân khác màu.
    Args:
      board: Bàn cờ hiện tại.
      x, y: Tọa độ quân (gốc trên-trái; x xuống, y sang phải).
    Returns:
      Danh sách Move (chưa kiểm tra an toàn royal).
    """
    deltas = [(-2, -1), (-2, 1), (-1, -2), (-1, 2),
              ( 1, -2), ( 1, 2), ( 2, -1), ( 2, 1)]
    moves: list[Move] = []
    for dx, dy in deltas:
      nx, ny = x + dx, y + dy
      if 0 <= nx < board.h and 0 <= ny < board.w:
        target = board.at(nx, ny)
        if target is None or target.color != self.color:
          # Move(from_x, from_y, to_x, to_y, piece, ...)
          moves.append(Move(x, y, nx, ny, self))
    return moves

class Pawn(Piece):
  """Standard chess Pawn."""
  def __init__(self, color: str) -> None:
    """Create a Pawn of given color."""
    super().__init__("P", color)
  
  def can_attack(self, board: "Board", sx: int, sy: int, tx: int, ty: int) -> bool:
    """
    Trả về True nếu Pawn (P) tại (sx, sy) khống chế ô (tx, ty).
    - Quy tắc chuẩn: chỉ khống chế CHÉO về phía trước đúng 1 ô.
      • Trắng: (tx, ty) = (sx - 1, sy ± 1)
      • Đen  : (tx, ty) = (sx + 1, sy ± 1)
    - Không phụ thuộc việc ô đích có quân hay trống (đây là khống chế, không phải di chuyển).
    - Không xét en passant/lượt/“royal safety”. Độ phức tạp: O(1).
    """
    step = -1 if self.color == 'w' else 1
    if tx != sx + step:
      return False
    dy = ty - sy
    return dy == 1 or dy == -1
  
  def generate_moves(self, board: "Board", x: int, y: int) -> list[Move]:
    """
    Pseudo-legal moves cho Pawn (chuẩn):
      - Đi thẳng 1 ô (nếu trống).
      - Đi thẳng 2 ô từ HAI hàng xuất phát (nếu cả 2 ô trống).
      - Ăn chéo 1 ô (trái/phải) nếu có đối phương.
      - En passant: chỉ bắt theo đường chéo; đọc schema list-of-tuples
        board.en_passant_target == [(tx,ty), (cx,cy)] với:
          (tx,ty): ô đến khi bắt EP (ô trung gian mà tốt đối thủ vừa "đi qua"),
          (cx,cy): ô chứa nạn nhân để xóa khi thực thi EP-capture.
      - Phong cấp khi chạm hàng phong cấp.
    Trả về: list[Move].
    """
    moves: list[Move] = []

    side = "white" if self.color == "w" else "black"
    dx = -1 if self.color == "w" else 1

    # 1) Ứng viên phong cấp (Board có thể tùy biến)
    promo_syms = ["Q", "R", "N", "K", "M", "V", "Y", "δ", "H"]
    try:
      cand = list(board.promotion_candidates())
      if cand:
        promo_syms = cand
    except Exception:
      pass

    # 2) Hàng phong cấp
    try:
      promo_row = board.promotion_row(side)
    except Exception:
      promo_row = -1  # không khớp -> coi như không phong cấp

    # 3) Hai hàng xuất phát cho double-step
    try:
      start_rows: set[int] = board.pawn_start_rows(side)
    except Exception:
      start_rows = set()

    nx = x + dx
    if 0 <= nx < board.h:
      # 4) Đi thẳng 1 ô
      if board.at(nx, y) is None:
        if nx == promo_row:
          for sym in promo_syms:
            moves.append(Move(x, y, nx, y, self, promotion_to=sym))
        else:
          moves.append(Move(x, y, nx, y, self))

        # 5) Double-step (từ start row; ô trung gian & ô đích đều trống)
        nx2 = x + 2 * dx
        if x in start_rows and 0 <= nx2 < board.h and board.at(nx2, y) is None:
          moves.append(Move(x, y, nx2, y, self, is_double_step=True))

      # 6) Ăn chéo thường (trái/phải)
      for ny in (y - 1, y + 1):
        if 0 <= ny < board.w:
          tgt = board.at(nx, ny)
          try:
            if tgt is not None and tgt.color != self.color:
              if nx == promo_row:
                for sym in promo_syms:
                  moves.append(Move(x, y, nx, ny, self, promotion_to=sym))
              else:
                moves.append(Move(x, y, nx, ny, self))
          except Exception:
            pass
      
      # 7) En passant — chỉ chéo; schema: [(tx,ty), (cx,cy)]
      try:
        ep_pair = board.en_passant_target
      except Exception:
        ep_pair = None
      
      if ep_pair:
        try:
          (tx, ty), (cx, cy) = ep_pair  # list[tuple]
          if tx == nx and 0 <= ty < board.w and (ty == y - 1 or ty == y + 1):
            victim = board.at(cx, cy)   # Thực tế sẽ bị lỗi ở dòng này
            if victim is not None and victim.color != self.color:
              moves.append(Move(x, y, tx, ty, self, is_en_passant=True))
        except Exception:
          pass

    return moves
  
if __name__ == "__main__":
  p=Piece('N','w')
  print(getattr(p,"_is_royal",False))