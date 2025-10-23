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
               "_pieces", "_royal_pos")
  w: int
  h: int
  grid: List[List[Square]]  # grid[x][y]
  _royal_pos: dict[str, set[tuple[int,int]]]
  en_passant_target: list[tuple[int, int]] | None
  _pieces: dict[str, dict[Piece, tuple[int, int]]]

  def __init__(self, w: int = 10, h: int = 10) -> None:
    """Tạo bàn rỗng w×h (mặc định 10×10), mỗi ô là Square(None)."""
    self.w = w
    self.h = h
    self.grid = [[Square() for _ in range(w)] for _ in range(h)]
    self._royal_pos = {"w": set(), "b": set()}
    self.en_passant_target = None   # Chứa 2 tuple, vị trí EP và quân có thể bị bắt EP
    self._pieces = {'w': {}, 'b': {}}  # dict[Piece, (x, y)]
  
  def result_if_over(self) -> str | None:
    """
    Trả về kết quả ván cờ nếu đã kết thúc, ngược lại None.
    Quy ước:
      - '1-0'     : Trắng thắng (đen bị chiếu bí).
      - '0-1'     : Đen thắng (trắng bị chiếu bí).
      - '1/2-1/2' : Hòa (stalemate ở bất kỳ bên nào).
    Ghi chú:
      - Dựa trên is_checkmated/is_stalemated (đều đã dùng has_any_legal_move).
      - Các điều kiện hòa khác sẽ bổ sung sau.
    """
    if self.is_checkmated('w'):
      return '0-1'
    if self.is_checkmated('b'):
      return '1-0'
    if self.is_stalemated('w') or self.is_stalemated('b'):
      return '1/2-1/2'
    return None
  
  def has_any_legal_move(self, color: str) -> bool:
    """
    Trả về True nếu tồn tại ÍT NHẤT MỘT nước đi hợp lệ cho bên `color`.
    Tối ưu: duyệt theo index self._pieces[color] và thoát NGAY khi gặp một nước hợp lệ,
    không tạo list đầy đủ như legal_moves_for(...).
    Ghi chú:
      - Dựa vào causes_self_check(mv) để lọc hợp lệ; không xây tập kết quả.
      - An toàn để dùng trong is_checkmated/is_stalemated/result_if_over.
    Độ phức tạp: O(K) với K = số nước phải thử cho tới khi gặp nước hợp lệ đầu tiên (thường nhỏ).
    """
    my_pos = self._pieces.get(color) or {}
    for piece, (x, y) in list(my_pos.items()):
      if self.at(x, y) is not piece or piece.color != color:
        continue
      for mv in self.collect_moves(x, y):
        if not self.causes_self_check(mv):
          return True
    return False
  
  def is_stalemated(self, color: str) -> bool:
    """
    Trả về True nếu bên `color` KHÔNG bị chiếu và KHÔNG còn bất kỳ nước đi hợp lệ nào.
    Tối ưu: dùng has_any_legal_move(color) để early-exit, tránh tạo list lớn.
    """
    if self.is_in_check(color):
      return False
    return not self.has_any_legal_move(color)
  
  def is_checkmated(self, color: str) -> bool:
    """
    Trả về True nếu bên `color` đang bị chiếu và KHÔNG còn bất kỳ nước đi hợp lệ nào.
    Tối ưu: dùng has_any_legal_move(color) để early-exit, tránh tạo list lớn.
    """
    if not self.is_in_check(color):
      return False
    return not self.has_any_legal_move(color)
  
  def legal_moves_for(self, color: str) -> "list[Move]":
    """
    Trả về danh sách nước đi hợp lệ cho bên `color` với cắt tỉa theo trạng thái chiếu.
    Tương thích với index mới: self._pieces[color] là dict[Piece, tuple[int,int]].
    Ý tưởng:
      - Tìm ô Vua (từ cache hoàng gia) và liệt kê kẻ chiếu hiện tại.
      - Double-check: chỉ cho phép nước đi của Vua tới ô không bị tấn công.
      - Single-check: chỉ giữ (a) Vua chạy; (b) bắt kẻ chiếu; (c) chặn tia (nếu kẻ chiếu là quân đi theo tia).
      - Chỉ ứng viên sau cắt tỉa mới kiểm tra `causes_self_check(mv)`.
    """
    legal: list[Move] = []
    opp = 'b' if color == 'w' else 'w'

    # 1) Lấy vị trí vua từ cache (giả định phải có ít nhất 1 ô royal).
    rps = self._royal_pos.get(color)
    if not rps:
      return legal
    kx, ky = next(iter(rps))

    # 2) Tìm danh sách kẻ chiếu hiện tại.
    attackers: list[tuple[int,int,"Piece"]] = []
    opp_pos = self._pieces.get(opp) or {}
    for opp_piece, (ax, ay) in list(opp_pos.items()):
      # Phòng chỉ mục lệch: xác thực lại quân tại (ax,ay)
      if self.at(ax, ay) is not opp_piece:
        continue
      if opp_piece.can_attack(self, ax, ay, kx, ky):
        attackers.append((ax, ay, opp_piece))

    # 3) Nếu double-check: chỉ cho phép nước đi của Vua → ô không bị tấn công.
    if len(attackers) >= 2:
      kp = self.at(kx, ky)
      if kp is None or kp.color != color:
        return legal
      for mv in self.collect_moves(kx, ky):
        if mv.tx == mv.fx and mv.ty == mv.fy:
          continue
        if not self.is_square_attacked(mv.tx, mv.ty, opp) and not self.causes_self_check(mv):
          legal.append(mv)
      return legal

    # 4) Single-check: chuẩn bị tập bắt/chặn để cắt tỉa.
    capture_targets: set[tuple[int,int]] = set()
    block_squares: set[tuple[int,int]] = set()
    if len(attackers) == 1:
      ax, ay, ap = attackers[0]
      capture_targets.add((ax, ay))
      ray_kinds = {'B', 'R', 'Q', 'H'}  # quân đi theo tia
      if getattr(ap, "kind", None) in ray_kinds:
        dx = (ax - kx)
        dy = (ay - ky)
        stepx = 0 if dx == 0 else (1 if dx > 0 else -1)
        stepy = 0 if dy == 0 else (1 if dy > 0 else -1)
        cx, cy = kx + stepx, ky + stepy
        while (cx, cy) != (ax, ay):
          block_squares.add((cx, cy))
          cx += stepx; cy += stepy

    # 5) Duyệt quân bên mình theo index mới (Piece,x,y) và cắt tỉa trước khi mô phỏng.
    my_pos = self._pieces.get(color) or {}
    for piece, (x, y) in list(my_pos.items()):
      if self.at(x, y) is not piece or piece.color != color:
        continue
      is_king = getattr(piece, "kind", None) == 'K'

      for mv in self.collect_moves(x, y):
        if len(attackers) == 1 and not is_king:
          if (mv.tx, mv.ty) not in capture_targets and (mv.tx, mv.ty) not in block_squares:
            continue
        elif len(attackers) >= 2 and not is_king:
          continue
        if is_king and self.is_square_attacked(mv.tx, mv.ty, opp):
          continue
        if not self.causes_self_check(mv):
          legal.append(mv)

    return legal
  
  def causes_self_check(self, mv: "Move") -> bool:
    """Return True if executing mv leaves the mover still in check."""
    def _is_royal(piece: Piece | None) -> bool:
      if piece is None:
        return False
      flag = getattr(piece, "is_royal", None)
      if flag is None:
        flag = getattr(piece, "_is_royal", False)
      return bool(flag)

    side_piece = mv.piece if getattr(mv, "piece", None) is not None else self.at(mv.fx, mv.fy)
    if side_piece is None:
      raise ValueError("causes_self_check: no piece at source.")
    side = side_piece.color
    prev_ep = getattr(self, "en_passant_target", None)

    def _make_move() -> dict[str, object]:
      state: dict[str, object] = {
        "prev_ep": prev_ep,
        "captured_piece": None,
        "captured_pos": None,
        "promoted_piece": None,
      }

      bucket = self._pieces.get(side_piece.color)
      if bucket is not None:
        bucket.pop(side_piece, None)
      if _is_royal(side_piece):
        self._royal_pos[side_piece.color].discard((mv.fx, mv.fy))
      self.grid[mv.fx][mv.fy].set_piece(None)

      captured_piece = None
      captured_pos: tuple[int, int] | None = None
      if mv.is_en_passant:
        ep = prev_ep
        if not ep or not isinstance(ep, (list, tuple)) or len(ep) != 2:
          raise ValueError("causes_self_check: EP flagged but no EP target.")
        (etx, ety), (cx, cy) = ep
        if (etx, ety) != (mv.tx, mv.ty):
          raise ValueError("causes_self_check: EP destination mismatch.")
        captured_piece = self.at(cx, cy)
        captured_pos = (cx, cy)
        if captured_piece is not None:
          bucket_c = self._pieces.get(captured_piece.color)
          if bucket_c is not None:
            bucket_c.pop(captured_piece, None)
          if _is_royal(captured_piece):
            self._royal_pos[captured_piece.color].discard((cx, cy))
          self.grid[cx][cy].set_piece(None)
      else:
        captured_piece = self.at(mv.tx, mv.ty)
        captured_pos = (mv.tx, mv.ty)
        if captured_piece is not None:
          if captured_piece.color == side_piece.color:
            raise ValueError("causes_self_check: destination occupied by same color.")
          bucket_c = self._pieces.get(captured_piece.color)
          if bucket_c is not None:
            bucket_c.pop(captured_piece, None)
          if _is_royal(captured_piece):
            self._royal_pos[captured_piece.color].discard((mv.tx, mv.ty))
          self.grid[mv.tx][mv.ty].set_piece(None)

      state["captured_piece"] = captured_piece
      state["captured_pos"] = captured_pos

      occupant: Piece = side_piece
      if mv.promotion_to:
        try:
          from .piece_factory import create
          promoted = create(mv.promotion_to, side_piece.color)
          occupant = promoted
          state["promoted_piece"] = promoted
        except Exception as exc:
          raise ValueError(f"causes_self_check: failed to promote to {mv.promotion_to!r}") from exc

      self.grid[mv.tx][mv.ty].set_piece(occupant)
      self._pieces.setdefault(occupant.color, {})[occupant] = (mv.tx, mv.ty)
      if _is_royal(occupant):
        self._royal_pos[occupant.color].add((mv.tx, mv.ty))

      self.en_passant_target = None
      if mv.is_double_step:
        compute = getattr(self, "compute_en_passant_target", None)
        if callable(compute):
          try:
            ep_pair = compute(mv, side_piece)
            if ep_pair and isinstance(ep_pair, list) and len(ep_pair) == 2:
              self.en_passant_target = ep_pair
          except Exception:
            pass

      return state

    def _unmake_move(state: dict[str, object]) -> None:
      promoted_piece = state.get("promoted_piece")
      occupant = promoted_piece if promoted_piece is not None else side_piece

      bucket_occ = self._pieces.get(occupant.color)
      if bucket_occ is not None:
        bucket_occ.pop(occupant, None)
      if _is_royal(occupant):
        self._royal_pos[occupant.color].discard((mv.tx, mv.ty))
      self.grid[mv.tx][mv.ty].set_piece(None)

      captured_piece = state.get("captured_piece")
      captured_pos = state.get("captured_pos")
      if isinstance(captured_piece, Piece) and isinstance(captured_pos, tuple):
        cx, cy = captured_pos
        self.grid[cx][cy].set_piece(captured_piece)
        self._pieces.setdefault(captured_piece.color, {})[captured_piece] = (cx, cy)
        if _is_royal(captured_piece):
          self._royal_pos[captured_piece.color].add((cx, cy))

      self.grid[mv.fx][mv.fy].set_piece(side_piece)
      self._pieces.setdefault(side_piece.color, {})[side_piece] = (mv.fx, mv.fy)
      if _is_royal(side_piece):
        self._royal_pos[side_piece.color].add((mv.fx, mv.fy))

      self.en_passant_target = state.get("prev_ep")

    state = _make_move()
    try:
      return self.is_in_check(side)
    finally:
      _unmake_move(state)

  def apply_move(self, mv: "Move") -> None:
    """Apply a pseudo-legal move (including captures, EP, promotion, double-step)."""
    self._check_bounds(mv.fx, mv.fy)
    self._check_bounds(mv.tx, mv.ty)

    piece = self.at(mv.fx, mv.fy)
    if piece is None:
      raise ValueError(f"No piece at source ({mv.fx},{mv.fy}).")

    if getattr(mv, "piece", None) is not None and mv.piece is not piece:
      pass

    if hasattr(self, "_index_remove"):
      self._index_remove(mv.fx, mv.fy)

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
      if hasattr(self, "_index_remove"):
        self._index_remove(cx, cy)
      self.clear(cx, cy)

    dst_piece = self.at(mv.tx, mv.ty)
    if dst_piece is not None and dst_piece.color == piece.color:
      raise ValueError("Destination occupied by same-color piece.")
    if dst_piece is not None and not mv.is_en_passant:
      if hasattr(self, "_index_remove"):
        self._index_remove(mv.tx, mv.ty)
      self.clear(mv.tx, mv.ty)

    self.clear(mv.fx, mv.fy)
    dst_cell = self.grid[mv.tx][mv.ty]
    try:
      dst_cell.piece = piece
    except AttributeError:
      self.grid[mv.tx][mv.ty] = piece

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
        promoted = None

    if hasattr(self, "_index_add"):
      self._index_add(mv.tx, mv.ty)

    occupant = promoted if promoted is not None else piece
    is_royal = getattr(occupant, "is_royal", None)
    if is_royal is None:
      is_royal = getattr(occupant, "_is_royal", False)
    if is_royal:
      setter = getattr(self, "_royal_cache_set", None)
      if callable(setter):
        setter(occupant.color, (mv.tx, mv.ty))
      else:
        try:
          if not isinstance(getattr(self, "_royal_pos", None), dict):
            self._royal_pos = {"w": None, "b": None}
          self._royal_pos[occupant.color] = (mv.tx, mv.ty)
        except Exception:
          pass

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
    Xoá quân khỏi ô (x,y). Đồng thời:
      - Cập nhật chỉ mục tự duy trì (_pieces index).
      - Cập nhật royal-cache: nếu quân bị xoá là 'royal' thì loại (x,y) khỏi cache.
    An toàn với các kiểu lưu trữ tạm thời của _royal_pos[color] (tuple/set/list/None).
    """
    self._check_bounds(x, y)
    p = self.at(x, y)
    if p is None:
      return

    # Cập nhật royal-cache nếu cần
    if getattr(p, "is_royal", False):
      bucket = self._royal_pos.get(p.color)
      # Chuẩn hoá bucket về set để thao tác đồng nhất
      if isinstance(bucket, tuple) and len(bucket) == 2:
        s = {bucket}
        self._royal_pos[p.color] = s
      elif bucket is None:
        s = set()
        self._royal_pos[p.color] = s
      elif not isinstance(bucket, set):
        s = set(bucket)
        self._royal_pos[p.color] = s
      else:
        s = bucket
      s.discard((x, y))

    # Cập nhật index + xoá quân trên lưới
    self._index_remove(x, y)
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

  def __repr__(self):
    return self.as_ascii()+'\n'
  
if __name__ == "__main__":
  # # --- Mock test: checkmate vs non-mate ---
  # print("\n[MockTest] Checkmate & Non-mate smoke test")

  # b = Board(10, 10)  # bảng trống nếu không gọi setup_from_layout()
  # # TH1: Mate đơn giản
  # # Vua trắng ở góc (0,0); Hậu đen (1,1) chiếu; Vua đen (2,2) bảo vệ ô (1,1)
  # b.put(0, 0, 'K', 'w')
  # b.put(1, 1, 'Q', 'b')
  # b.put(2, 2, 'K', 'b')
  # b.set_royal(0,0)
  # print(b.as_ascii())
  # print("In-check (w):", b.is_in_check('w'))
  # print("Legal moves (w):", len(b.legal_moves_for('w')))
  # print("Is checkmated (w):", b.is_checkmated('w'))

  #TH2: Không còn là mate (đưa Vua đen ra xa để K trắng bắt được Q)
  b2 = Board(10, 10)
  b2.put(0, 0, 'K', 'w')
  b2.put(1, 1, 'Q', 'b')
  b2.put(3, 3, 'K', 'b')  # xa hơn, ô (1,1) không còn bị vua đen khống chế
  print(b2)
  b2.set_royal(0,0)
  print("In-check (w) #2:", b2.is_in_check('w'))
  print("Legal moves (w) #2:", len(b2.legal_moves_for('w')))
  print("Is checkmated (w) #2:", b2.is_checkmated('w'))


