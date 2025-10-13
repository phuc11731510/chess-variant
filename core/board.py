# chess-variant\core\board.py
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from typing import List,TYPE_CHECKING
from core.piece import Piece
from core.piece_factory import create
from core.coords import from_alg,to_alg
from core.move import Move

class Square:
  """Ô vuông: chứa Piece hoặc None."""
  __slots__ = ("piece",)
  piece: Piece | None

  def __init__(self, piece: Piece | None = None) -> None:
    """Mặc định trống (None)."""
    self.piece = piece

  def set_piece(self, piece: Piece | None) -> None:
    """Đặt/xóa quân (None để xóa)."""
    self.piece = piece

  def glyph(self) -> str:
    """Glyph 2 ký tự; trống là '..'."""
    return self.piece.glyph() if self.piece is not None else ".."


class Board:
  """
  Bàn cờ mặc định 10×10.

  Hệ trục:
    - Gốc (0,0) ở góc trên–trái.
    - trục x: tăng xuống dưới (0..h-1).
    - trục y: tăng sang phải (0..w-1).

  Lưu ý: grid[x][y] (hàng = x, cột = y).
  """
  __slots__ = ("w", "h", "grid", "_royal_pos", "en_passant_target",
               "_pieces")
  w: int
  h: int
  grid: List[List[Square]]  # grid[x][y]
  _roayal_pos: dict[str, set[tuple[int,int]]]
  en_passant_target: list[tuple[int, int]] | None
  _pieces: dict[str,list[tuple[Piece,int,int]]]

  def __init__(self, w: int = 10, h: int = 10) -> None:
    """Tạo bàn rỗng w×h (mặc định 10×10), mỗi ô là Square(None)."""
    self.w = w
    self.h = h
    self.grid = [[Square() for _ in range(w)] for _ in range(h)]
    self._royal_pos = {"w": set(), "b": set()}
    self.en_passant_target = None   # Chứa 2 tuple, vị trí EP và quân có thể bị bắt EP
    self._pieces = {'w': [], 'b': []}  # list[tuple[Piece,int,int]]
  
  def _index_remove(self, x: int, y: int) -> None:
    """Gỡ quân tại (x,y) khỏi chỉ mục (nếu đang có). An toàn với ô trống."""
    p = self.at(x, y)
    if p is None:
      return
    bucket = self._pieces[p.color]
    for k, (q, i, j) in enumerate(bucket):
      if q is p and i == x and j == y:
        bucket.pop(k)
        break
  
  def _index_add(self, x: int, y: int) -> None:
    """Đưa quân tại (x,y) vào chỉ mục theo màu. Bỏ qua nếu ô trống."""
    p = self.at(x, y)
    if p is not None:
      self._pieces[p.color].append((p, x, y))
  
  def compute_en_passant_target(self, mv: "Move", piece: "Piece") -> list[tuple[int, int]] | None:
    """
    Tính EP target sau một nước double-step (Pawn/Sergeant).

    Trả về (schema dùng *list of tuple*):
      [(tx_target, ty_target), (cx, cy)], trong đó:
        - (tx_target, ty_target): ô mà quân đối phương sẽ "đi đến" khi bắt EP
                                  (chính là ô trung gian mà quân vừa "đi qua").
        - (cx, cy): ô chứa nạn nhân để xóa khi thực thi EP-capture
                    (chính là ô đích hiện tại của nước double-step).

    Yêu cầu:
      - mv.is_double_step == True (giả định đã do generator đảm bảo).
      - Không kiểm tra royal/check tại đây.
    """
    if not getattr(mv, "is_double_step", False):
      return None

    # Ô trung gian giữa nguồn và đích (bao quát cả thẳng và chéo 2 ô)
    midx = (mv.fx + mv.tx) // 2
    midy = (mv.fy + mv.ty) // 2

    # Nạn nhân là quân vừa đứng ở ô đích của nước double-step
    return [(midx, midy), (mv.tx, mv.ty)]

  def apply_move(self, mv: "Move") -> None:
    """
    Thực thi một pseudo-legal Move trên bàn cờ.

    Hỗ trợ:
      - Nước đi thường & ăn thường.
      - En passant: đọc self.en_passant_target == [(tx,ty),(cx,cy)],
        yêu cầu (tx,ty) == (mv.tx,mv.ty); xóa quân tại (cx,cy) rồi di chuyển.
      - Set/Reset EP: mặc định reset; nếu mv.is_double_step thì gọi
        compute_en_passant_target(mv, piece) (nếu có) để gán EP mới.
      - Promotion: nếu mv.promotion_to khác None.

    Ghi chú:
      - Không kiểm tra “royal safety”.
      - Không đổi lượt/không ghi lịch sử tại đây.
    """
    # 0) Kiểm tra cơ bản & lấy quân nguồn
    self._check_bounds(mv.fx, mv.fy)
    self._check_bounds(mv.tx, mv.ty)

    piece = self.at(mv.fx, mv.fy)
    if piece is None:
      raise ValueError(f"No piece at source ({mv.fx},{mv.fy}).")

    if getattr(mv, "piece", None) is not None and mv.piece is not piece:
      # Có thể raise để siết chặt, hiện tạm bỏ qua
      pass

    # === CẬP NHẬT CHỈ MỤC: chuẩn bị gỡ các mục liên quan trước khi sửa lưới ===
    # Gỡ nguồn
    if hasattr(self, "_index_remove"):
      self._index_remove(mv.fx, mv.fy)

    # 1) EN PASSANT: xoá nạn nhân trước khi di chuyển
    if mv.is_en_passant:
      ep = getattr(self, "en_passant_target", None)
      if not ep:
        raise ValueError("EN PASSANT move but no en_passant_target set.")
      (etx, ety), (cx, cy) = ep
      if (etx, ety) != (mv.tx, mv.ty):
        raise ValueError("EN PASSANT destination mismatch.")
      victim = self.at(cx, cy)
      if victim is None or victim.color == piece.color:
        raise ValueError("Invalid EN PASSANT victim square.")
      # Gỡ nạn nhân EP khỏi index trước khi xóa
      if hasattr(self, "_index_remove"):
        self._index_remove(cx, cy)
      self.clear(cx, cy)

    # 2) Ăn thường (khi không phải EP)
    dst_piece = self.at(mv.tx, mv.ty)
    if dst_piece is not None and dst_piece.color == piece.color:
      raise ValueError("Destination occupied by same-color piece.")
    if dst_piece is not None and not mv.is_en_passant:
      # Gỡ mục index của quân bị ăn ở đích trước khi xóa
      if hasattr(self, "_index_remove"):
        self._index_remove(mv.tx, mv.ty)
      self.clear(mv.tx, mv.ty)

    # 3) Di chuyển quân (nguồn -> đích) mà KHÔNG thay thế ô (Square)
    #    - clear ô nguồn (đặt piece=None)
    #    - đặt piece vào ô đích qua thuộc tính .piece
    self.clear(mv.fx, mv.fy)
    dst_cell = self.grid[mv.tx][mv.ty]
    try:
      dst_cell.piece = piece
    except AttributeError:
      self.grid[mv.tx][mv.ty] = piece

    # 4) Promotion (nếu có): thay quân trong ô đích
    promoted = None
    if mv.promotion_to:
      try:
        from .piece_factory import create
        promoted = create(mv.promotion_to, piece.color)
        try:
          dst_cell.piece = promoted
        except AttributeError:
          self.grid[mv.tx][mv.ty] = promoted
      except Exception:
        # Nếu promote lỗi, giữ nguyên quân hiện tại
        promoted = None

    # Sau khi đặt xong (đã tính cả promotion), bổ sung index cho ô đích
    if hasattr(self, "_index_add"):
      self._index_add(mv.tx, mv.ty)

    # 5) Reset EP mặc định; nếu double-step thì set EP mới (schema: list-of-tuples)
    self.en_passant_target = None
    if mv.is_double_step:
      compute = getattr(self, "compute_en_passant_target", None)
      if callable(compute):
        try:
          ep_pair = compute(mv, piece)
          if ep_pair and isinstance(ep_pair, list) and len(ep_pair) == 2:
            self.en_passant_target = ep_pair
        except Exception:
          pass

    return
      
  def collect_moves(self, x: int, y: int) -> list[Move]:
    """Trả về list[Move] cho quân ở (x,y); nếu quân còn trả (tx,ty) thì bọc thành Move."""
    self._check_bounds(x, y)
    piece = self.at(x, y)  # luôn trả Piece | None từ Square
    if piece is None:
      return []
    res = piece.generate_moves(self, x, y)
    if not res:
      return []
    res_list = list(res)  # hỗ trợ iterator/generator
    if not res_list:
      return []
    if isinstance(res_list[0], Move):
      return res_list
    out: list[Move] = []
    for (tx, ty) in res_list:
      out.append(Move(x, y, tx, ty, piece))
    return out
  
  def promotion_candidates(self):
    """Return iterable of allowed promotion symbols for `side`."""
    return ["Q", "R", "N", "K", "M", "V", "Y", "δ", "H"]
  
  def pawn_start_rows(self, side: str) -> set[int]:
    """Return the set of x-indices (0-based) where Pawn/Sergeant may double-step.
    Quy ước dự án:
    - White: rows 2 & 3 (1-based) -> {1, 2}
    - Black: rows 9 & 8 (1-based) -> {8, 7}
    """
    return {7, 8} if side == "white" else {1, 2}
    
  def promotion_row(self, side: str) -> int:
    """Return the x-index (0-based) of the promotion row for `side`.
    Quy ước dự án:
    - White: hàng thứ 9 (1-based) -> x = 8
    - Black: hàng thứ 2 (1-based) -> x = 1
    """
    return 1 if side == "white" else 8
  
  def set_royal(self, x: int, y: int, flag: bool = True) -> None:
    """
    Gán/cởi cờ 'royal' cho quân tại (x,y) và cập nhật cache vị trí royal.
    Raises:
      ValueError: nếu ô trống.
    """
    p = self.at(x, y)
    if p is None:
      raise ValueError(f"Không có quân tại (x={x}, y={y}) để gán royal.")
    # Bỏ (x,y) khỏi cả hai set phòng trường hợp đổi màu/di chuyển trước đó
    self._royal_pos["w"].discard((x, y))
    self._royal_pos["b"].discard((x, y))
    p.set_royal(flag)
    if flag:
      self._royal_pos[p.color].add((x, y))
  
  def royal_positions(self) -> dict[str, list[tuple[int, int]]]:
    """Trả về vị trí các quân 'royal' theo màu từ cache (O(1))."""
    return {
      "w": list(self._royal_pos["w"]),
      "b": list(self._royal_pos["b"]),
    }

  def setup_from_layout(self) -> None:
    """
    Khởi tạo bàn cờ 10×10 từ một chuỗi bố cục có padding.

    Quy ước chuỗi:
      - Các hàng ngăn bởi dấu '/'.
      - Trong mỗi hàng, các mục ngăn bởi ','.
      - 'x' là padding: bỏ qua.
      - '10' nghĩa là 10 ô trống liên tiếp (chỉ giá trị này, không hỗ trợ số khác).
      - Token quân có dạng '<c><k>' với:
          c ∈ {'r','y'} (r→white, y→black),
          k là mã quân (K,Q,R,B,N,P,M,V,Y,δ,H,...).
      - Sau khi bỏ padding, **mỗi hàng nội dung phải có đúng 10 ô**.
      - Tổng số hàng nội dung sau khi bỏ padding phải đúng bằng 10.

    Hệ trục:
      - Góc trên-trái là (x=0, y=0); x tăng xuống dưới, y tăng sang phải.

    Raises:
      ValueError: Khi token không hợp lệ, số ô một hàng ≠ 10, hoặc số hàng nội dung ≠ 10.
      (Thông báo lỗi nêu rõ hàng/cột gây lỗi khi có thể.)
    """
    layout="""
          x,x,x,x,x,x,x,x,x,x,x,x,x,x/
          x,x,x,x,x,x,x,x,x,x,x,x,x,x/
          x,x,yV,yY,yR,yH,yQ,yK,yH,yR,yY,yV,x,x/
          x,x,yM,yδ,yN,yδ,yY,yY,yδ,yN,yδ,yM,x,x/
          x,x,yK,yP,yP,yP,yP,yP,yP,yP,yP,yK,x,x/
          x,x,10,x,x/
          x,x,10,x,x/
          x,x,10,x,x/
          x,x,10,x,x/
          x,x,rK,rP,rP,rP,rP,rP,rP,rP,rP,rK,x,x/
          x,x,rM,rδ,rN,rδ,rY,rY,rδ,rN,rδ,rM,x,x/
          x,x,rV,rY,rR,rH,rQ,rK,rH,rR,rY,rV,x,x/
          x,x,x,x,x,x,x,x,x,x,x,x,x,x/
          x,x,x,x,x,x,x,x,x,x,x,x,x,x
          """.strip()
    for x in range(self.h):
      for y in range(self.w):
        self.grid[x][y].set_piece(None)

    color_map = {"r": "w", "y": "b"}
    rows = [r.strip() for r in layout.strip().split("/") if r.strip()]

    board_x = 0  # chỉ số hàng thực (0..9) sau khi loại padding

    for src_row_index, row in enumerate(rows):
      tokens = [t.strip() for t in row.split(",") if t.strip()]
      cells: list[tuple[str, str] | None] = []

      # 2) Parse từng token trong hàng
      for tok in tokens:
        if tok == "x":
          # padding - bỏ qua
          continue
        if tok == "10":
          # đúng 10 ô trống liên tiếp
          cells.extend([None] * 10)
          continue
        # token quân: 'rK', 'yP', 'yδ', ...
        if len(tok) >= 2 and tok[0] in color_map:
          clr = color_map[tok[0]]
          kind = tok[1:]  # hỗ trợ cả ký tự nhiều byte như 'δ'
          cells.append((kind, clr))
          continue

        # Nếu vào đây là token không hợp lệ
        raise ValueError(f"Token không hợp lệ ở hàng nguồn {src_row_index}: '{tok}'")

      # Bỏ qua hàng toàn padding (không có '10' và cũng không có quân)
      if not cells:
        continue

      # 3) Mỗi hàng nội dung phải có đúng self.w ô
      if len(cells) != self.w:
        raise ValueError(
          f"Hàng nội dung thứ {board_x} sau khi bỏ padding không có đúng {self.w} ô (thực tế: {len(cells)})."
        )

      # 4) Đặt quân lên lưới
      for y, cell in enumerate(cells):
        if cell is None:
          # ô trống
          self.grid[board_x][y].set_piece(None)
        else:
          kind, clr = cell
          try:
            self.grid[board_x][y].set_piece(create(kind, clr))
          except Exception as e:
            # Nêu rõ vị trí hàng/cột sau khi chuẩn hóa
            raise ValueError(
              f"Token không hợp lệ ở (hàng={board_x}, cột={y}): '{clr[0]}{kind}'. Lỗi gốc: {e}"
            ) from e

      board_x += 1
      if board_x > self.h:
        raise ValueError(
          f"Số hàng nội dung vượt quá {self.h} (đã thấy > {self.h} hàng sau khi loại padding)."
        )

    # 5) Tổng kết: phải có đúng self.h hàng nội dung
    if board_x != self.h:
      raise ValueError(f"Số hàng nội dung ≠ {self.h} (thực tế: {board_x}).")
    
    self.set_royal_alg('f',1)
    self.set_royal_alg('f',10)

  def set_royal(self, x: int, y: int, flag: bool = True) -> None:
    """
    Gán/cởi cờ 'royal' cho quân tại (x,y) và đồng bộ cache.
    Raises:
      ValueError: nếu ô trống.
    """
    self._check_bounds(x, y)
    p = self.at(x, y)
    if p is None:
      raise ValueError(f"Không có quân tại (x={x}, y={y}) để gán royal.")

    # Loại khỏi cache ở vị trí hiện tại (dù màu nào) để tránh dư thừa
    self._royal_pos["w"].discard((x, y))
    self._royal_pos["b"].discard((x, y))

    # Cập nhật cờ royal trên quân cờ (ưu tiên method công khai)
    if hasattr(p, "set_royal"):
      p.set_royal(flag)
    else:
      p._is_royal = flag  # fallback nếu chưa có API

    # Nếu bật royal → thêm lại vào cache theo màu hiện tại
    if flag:
      self._royal_pos[p.color].add((x, y))
  
  def set_royal_alg(self, file: str, rank: int, flag: bool = True) -> None:
    """
    Gán/cởi cờ 'royal' theo ký hiệu file-rank CHUẨN CỜ (rank 1 ở dưới).
    Ví dụ: set_royal_alg('E', 1, True)
    Raises:
      ValueError: nếu ô trống hoặc ký hiệu ngoài biên.
    """
    x, y = from_alg(f"{(file or '').strip()}{rank}", self.h, self.w)
    self.set_royal(x, y, flag)
  
  def put(self, x: int, y: int, kind: str, color: str) -> None:
    """
    Đặt/ghi-đè quân tại (x,y):
      - Kiểm tra biên.
      - Nếu ô đang có quân royal → loại khỏi cache trước.
      - Cập nhật chỉ mục quân theo màu (_pieces): gỡ entry cũ, thêm entry mới.
      - Tạo quân bằng factory rồi đặt vào ô.
      - Nếu quân mới là royal → thêm vào cache.
    Raises:
      ValueError: nếu không tạo được quân (kind/color không hợp lệ).
    """
    self._check_bounds(x, y)

    # Nếu đang có quân (đặc biệt là royal) thì gỡ khỏi cache & chỉ mục trước khi ghi đè
    old = self.at(x, y)
    if old is not None:
      if getattr(old, "is_royal", False):
        self._royal_pos[old.color].discard((x, y))
      # Giữ chỉ mục đúng
      self._index_remove(x, y)

    # Tạo quân mới
    try:
      piece = create(kind, color)
    except Exception as e:
      raise ValueError(
        f"Không tạo được quân tại (x={x}, y={y}) với kind='{kind}', color='{color}'. Lỗi gốc: {e}"
      ) from e

    # Đặt quân
    self.grid[x][y].set_piece(piece)

    # Cập nhật chỉ mục và cache royal cho quân mới
    self._index_add(x, y)
    if getattr(piece, "is_royal", False):
      self._royal_pos[piece.color].add((x, y))

  def as_ascii(self) -> str:
    """
    Chuỗi ASCII của bàn cờ.
    In từ hàng trên xuống dưới: x = 0..h-1, mỗi ô rộng 3 ký tự.
    """
    lines: List[str] = []
    for x in range(self.h):                       # hàng: trên → dưới
      row = "".join(self.grid[x][y].glyph().ljust(3) for y in range(self.w))
      lines.append(row.rstrip())
    return "\n".join(lines)
  
  def clear(self, x: int, y: int) -> None:
    """
    Xóa quân tại (x,y) → None và cập nhật chỉ mục/index:
      - Kiểm tra biên.
      - Nếu ô có quân royal → loại khỏi cache self._royal_pos.
      - Gỡ quân khỏi chỉ mục màu self._pieces[...] (nếu đang có).
      - Đặt None vào ô (idempotent nếu đã trống).
    """
    self._check_bounds(x, y)

    p = self.at(x, y)
    if p is None:
      return  # idempotent: không có gì để cập nhật

    if getattr(p, "is_royal", False):
      self._royal_pos[p.color].discard((x, y))

    # Gỡ khỏi index trước khi mutate ô
    self._index_remove(x, y)

    # Xóa quân tại ô
    self.grid[x][y].set_piece(None)
  
  def put_alg(self, file: str, rank: int, kind: str, color: str) -> None:
    """
    Đặt quân theo 'file-rank' với hệ trục gốc trên–trái:
      - file: 'a'..'j'  → y = ord(file) - ord('a') (trái→phải)
      - rank: 1..10     → x = rank - 1            (trên→dưới)
    """
    x,y=from_alg(file+str(rank),self.h,self.w)
    return self.put(x,y,kind,color)

  def clear_alg(self, file: str, rank: int) -> None:
    """
    Xóa quân theo ký hiệu file-rank CHUẨN CỜ (rank 1 ở dưới).
    - file: 'A'.. (không phân biệt hoa/thường)
    - rank: 1..h
    Raises:
      ValueError: nếu ký hiệu ngoài biên/không hợp lệ.
    """
    x, y = from_alg(f"{(file or '').strip()}{rank}", self.h, self.w)
    self.clear(x, y)

  def at(self, x: int, y: int) -> Piece | None:
    """Trả về Piece tại (x,y) hoặc None nếu ô trống."""
    self._check_bounds(x, y)
    return self.grid[x][y].piece
  
  def at_alg(self, file: str, rank: int) -> "Piece | None":
    """
    Lấy quân ở ô ký hiệu file-rank CHUẨN CỜ (rank 1 ở dưới):
      - file: 'A'.. (không phân biệt hoa/thường), tăng từ trái → phải.
      - rank: 1..h (1 ở hàng dưới cùng).
    Trả về:
      - Piece nếu có quân; None nếu ô trống.
    Raises:
      ValueError: nếu ký hiệu ngoài biên hay không hợp lệ.
    """
    x, y = from_alg(f"{(file or '').strip()}{rank}", self.h, self.w)
    return self.at(x, y)

  def _check_bounds(self, x: int, y: int) -> None:
    """Kiểm tra (x,y) nằm trong bàn; ném IndexError nếu vượt biên."""
    if not (0 <= x < self.h and 0 <= y < self.w):
      raise IndexError(f"out of board bounds: (x={x}, y={y})")

if __name__ == "__main__":
  b = Board(10, 10)
  b.put(5,5,'M','w')
  print(b.as_ascii()+'\n\n')
  b.apply_move(b.collect_moves(5,5)[13])
  print(b.as_ascii())
  print(b._pieces)