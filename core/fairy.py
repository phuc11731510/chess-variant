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
    
  def generate_moves(self, board: "Board", x: int, y: int) -> list[Move]:
    """
    Pseudo-legal moves cho Sergeant (δ).

    Quy tắc:
      - 1 bước: có thể đi THẲNG trước mặt hoặc CHÉO (trái/phải) 1 ô.
        • Ô đến có thể trống (đi thường) hoặc có đối phương (ăn thường).
      - 2 bước từ HAI hàng xuất phát (board.pawn_start_rows(side)):
        • Hướng tiến (dx) + có biến thể CHÉO 2 ô (trái/phải).
        • YÊU CẦU: cả ô trung gian và ô đích đều trống.
        • Nước đi gắn cờ is_double_step=True.
      - En passant (schema mới): board.en_passant_target == ((tx, ty), (cx, cy)).
        • (tx, ty): ô đích; (cx, cy): tọa độ quân bị bắt sẽ bị xóa khi thực thi.
        • Generator CHỈ kiểm tra hợp lệ và thêm Move(is_en_passant=True);
          việc xóa nạn nhân để Board.apply_move xử lý.
      - Phong cấp: khi chạm hàng phong cấp (board.promotion_row(side)),
        tạo các nước đi với promotion_to ∈ board.promotion_candidates(side).

    Tham số:
      board: Board — trạng thái bàn cờ hiện tại (có API at(), promotion_row(), …).
      x, y: int — tọa độ hiện tại (gốc trên-trái; x tăng xuống, y tăng sang phải).

    Trả về:
      list[Move]: Danh sách nước đi pseudo-legal (chưa kiểm tra “royal safety”).

    Ghi chú:
      - Hàm này cố tình “chịu lỗi nhẹ” để Board thiếu API vẫn hoạt động tối thiểu.
      - Kiểm tra tự chiếu (self-check) và hợp lệ cuối cùng thuộc về lớp Board.
    """
    
    moves:list[Move]=[]
    
    if self.color=='w':dx=-1
    else:dx=1
    
    if self.color=='w':side="white"
    else:side="black"
    
    start_rows:set[int]=board.pawn_start_rows(side)
    promo_rows:int=board.promotion_row(side)
    promo_syms:list[str]=board.promotion_candidates(side)
    ep=board.en_passant_target
    
    nx=x+dx
    ny=y
    try:
      t=board.at(nx,ny)
      if t==None or (not t.color==self.color):
        if nx==promo_rows:
          for cand in promo_syms:moves.append(Move(x,y,nx,ny,self,promotion_to=cand))
        elif ep and ep[0]==(nx,ny) and board.at(ep[1][0],ep[1][1]).color!=self.color:
          moves.append(Move(x,y,nx,ny,self,is_en_passant=True))
        else:moves.append(Move(x,y,nx,ny,self))
    except:pass
    
    ny=y-1
    try:
      t=board.at(nx,ny)
      if t==None or (not t.color==self.color):
        if nx==promo_rows:
          for cand in promo_syms:moves.append(Move(x,y,nx,ny,self,promotion_to=cand))
        elif ep and ep[0]==(nx,ny) and board.at(ep[1][0],ep[1][1]).color!=self.color:
          moves.append(Move(x,y,nx,ny,self,is_en_passant=True))
        else:moves.append(Move(x,y,nx,ny,self))
    except:pass
    
    ny=y+1
    try:
      t=board.at(nx,ny)
      if t==None or (not t.color==self.color):
        if nx==promo_rows:
          for cand in promo_syms:moves.append(Move(x,y,nx,ny,self,promotion_to=cand))
        elif ep and ep[0]==(nx,ny) and board.at(ep[1][0],ep[1][1]).color!=self.color:
          moves.append(Move(x,y,nx,ny,self,is_en_passant=True))
        else:moves.append(Move(x,y,nx,ny,self))
    except:pass
    
    nx=x+2*dx
    ny=y
    try:
      t=board.at(nx,ny)
      if (x in start_rows) and (board.at(x+dx,y)==None) and (t==None):
        moves.append(Move(x,y,nx,ny,self,is_double_step=True))
    except:pass
    
    ny=y-2
    try:
      t=board.at(nx,ny)
      if (x in start_rows) and (board.at(x+dx,y-1)==None) and (t==None):
        moves.append(Move(x,y,nx,ny,self,is_double_step=True))
    except:pass
      
    ny=y+2
    try:
      t=board.at(nx,ny)
      if (x in start_rows) and (board.at(x+dx,y+1)==None) and (t==None):
        moves.append(Move(x,y,nx,ny,self,is_double_step=True))
    except:pass
    
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
