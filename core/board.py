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
  _pieces: dict[str,list[tuple[Piece,int,int]]]

  def __init__(self, w: int = 10, h: int = 10) -> None:
    """Tạo bàn rỗng w×h (mặc định 10×10), mỗi ô là Square(None)."""
    self.w = w
    self.h = h
    self.grid = [[Square() for _ in range(w)] for _ in range(h)]
    self._royal_pos = {"w": set(), "b": set()}
    self.en_passant_target = None   # Chứa 2 tuple, vị trí EP và quân có thể bị bắt EP
    self._pieces = {'w': [], 'b': []}  # list[tuple[Piece,int,int]]
  
  def is_checkmated(self, color: str) -> bool:
    """
    Trả về True nếu bên `color` đang bị chiếu và KHÔNG còn nước đi hợp lệ nào.
    Định nghĩa:
      - Mate khi: is_in_check(color) == True và len(legal_moves_for(color)) == 0.
    Ghi chú:
      - Giả định legal_moves_for(...) đã lọc tự-chiếu chính xác (EP, promotion, v.v.).
      - Dùng cho phán định kết thúc ván, UI thông báo chiếu bí, và kiểm thử perft.
    Độ phức tạp: O(M·C) với M = số pseudo-moves sau cắt tỉa, C = chi phí causes_self_check.
    """
    if not self.is_in_check(color):
      return False
    return len(self.legal_moves_for(color)) == 0
  
  def legal_moves_for(self, color: str) -> "list[Move]":
    """
    Trả về danh sách nước đi hợp lệ cho bên `color` với cắt tỉa theo trạng thái chiếu.
    Ý tưởng:
      - Tìm ô Vua (từ cache hoàng gia) và liệt kê kẻ chiếu hiện tại.
      - Nếu double-check: chỉ cho phép nước đi của Vua sang ô không bị tấn công.
      - Nếu single-check: chỉ giữ (a) Vua chạy; (b) bắt kẻ chiếu; (c) chặn đường (nếu kẻ chiếu đi theo tia).
      - Chỉ những ứng viên đã qua cắt tỉa mới kiểm tra `causes_self_check(mv)`.
    Lợi ích: giảm đáng kể số lần mô phỏng/unmake move, đặc biệt trong positions đang bị chiếu.
    """
    legal: list[Move] = []
    opp = 'b' if color == 'w' else 'w'

    # 1) Lấy vị trí vua từ cache (giả định đúng 1 vua).
    rps = self._royal_pos.get(color)
    if not rps:
      return legal
    kx, ky = next(iter(rps))

    # 2) Tìm danh sách kẻ chiếu hiện tại (rẻ hơn mô phỏng hàng loạt).
    attackers: list[tuple[int,int,"Piece"]] = []
    opp_pos = self._pieces.get(opp) or set()
    for (ax, ay) in opp_pos:
      ap = self.at(ax, ay)
      if ap and ap.can_attack(self, ax, ay, kx, ky):
        attackers.append((ax, ay, ap))

    # 3) Nếu double-check: chỉ duyệt nước đi của Vua → ô không bị tấn công.
    if len(attackers) >= 2:
      # Tìm ô vua (lại) vì có thể nhiều vua trong biến thể; ta lọc đúng ô chứa King.
      kp = self.at(kx, ky)
      if kp is None or kp.color != color:
        return legal
      for mv in self.collect_moves(kx, ky):
        # Chỉ nhận nước đi của vua tới ô không bị tấn công bởi đối thủ.
        if mv.tx == mv.fx and mv.ty == mv.fy:
          continue
        if not self.is_square_attacked(mv.tx, mv.ty, opp) and not self.causes_self_check(mv):
          legal.append(mv)
      return legal

    # 4) Single-check hoặc không bị chiếu: chuẩn bị tập chặn/bắt để cắt tỉa.
    capture_targets: set[tuple[int,int]] = set()
    block_squares: set[tuple[int,int]] = set()
    if len(attackers) == 1:
      ax, ay, ap = attackers[0]
      capture_targets.add((ax, ay))
      # Nếu kẻ chiếu là quân đi theo tia (B/R/Q; Archbishop 'H' có tia chéo), tính các ô chặn giữa vua và kẻ chiếu.
      ray_kinds = {'B', 'R', 'Q', 'H'}
      if getattr(ap, "kind", None) in ray_kinds:
        dx = (ax - kx)
        dy = (ay - ky)
        stepx = (0 if dx == 0 else (1 if dx > 0 else -1))
        stepy = (0 if dy == 0 else (1 if dy > 0 else -1))
        cx, cy = kx + stepx, ky + stepy
        while (cx, cy) != (ax, ay):
          block_squares.add((cx, cy))
          cx += stepx
          cy += stepy

    # 5) Duyệt theo index của bên mình + cắt tỉa trước khi mô phỏng.
    my_pos = self._pieces.get(color) or set()
    for (x, y) in list(my_pos):
      p = self.at(x, y)
      if p is None or p.color != color:
        continue
      is_king = getattr(p, "kind", None) == 'K'

      for mv in self.collect_moves(x, y):
        # CẮT TỈA NHANH:
        if len(attackers) == 1 and not is_king:
          # Không phải vua: chỉ cho phép (bắt kẻ chiếu) hoặc (chặn đường).
          if (mv.tx, mv.ty) not in capture_targets and (mv.tx, mv.ty) not in block_squares:
            continue
        elif len(attackers) >= 2 and not is_king:
          # Double-check đã return ở trên; phòng hờ:
          continue
        # Nếu là nước đi của vua: đích phải không bị tấn công.
        if is_king and self.is_square_attacked(mv.tx, mv.ty, opp):
          continue

        # Kiểm tra cuối cùng bằng mô phỏng không tạo self-check.
        if not self.causes_self_check(mv):
          legal.append(mv)

    return legal
  
  def causes_self_check(self, mv: "Move") -> bool:
    """
    Trả về True nếu thực hiện mv xong thì bên của mv.piece.color vẫn/đang bị chiếu
    (nước đi KHÔNG hợp lệ về an toàn hoàng gia).
    Cách làm: mô phỏng apply_move trên chính bàn cờ rồi HOÀN TÁC ngay (không deepcopy).
    Bảo toàn:
      - Tự phục hồi index & royal-cache khi khôi phục các ô đã đổi (không dùng put()).
      - Hỗ trợ: ăn thường, en passant, promotion, double-step.
    """
    # 1) Lấy thông tin bên đi + snapshot tối thiểu
    side_piece = mv.piece if getattr(mv, "piece", None) is not None else self.at(mv.fx, mv.fy)
    if side_piece is None:
      raise ValueError("causes_self_check: no piece at source.")
    side = side_piece.color
    prev_ep = getattr(self, "en_passant_target", None)

    src_piece = self.at(mv.fx, mv.fy)
    dst_piece_before = self.at(mv.tx, mv.ty)

    ep_victim_pos = None
    ep_victim_piece = None
    if mv.is_en_passant:
      ep = self.en_passant_target
      if not ep:
        raise ValueError("causes_self_check: EP flagged but no EP target.")
      (etx, ety), (cx, cy) = ep
      if (etx, ety) != (mv.tx, mv.ty):
        raise ValueError("causes_self_check: EP destination mismatch.")
      ep_victim_pos = (cx, cy)
      ep_victim_piece = self.at(cx, cy)

    # 2) Mô phỏng và kiểm tra
    in_check = True
    try:
      self.apply_move(mv)
      in_check = self.is_in_check(side)
    finally:
      # 3) HOÀN TÁC — khôi phục theo thứ tự ngược

      # 3.1) Khôi phục EP marker
      self.en_passant_target = prev_ep

      # 3.2) Xóa quân tại đích (kể cả promoted)
      self.clear(mv.tx, mv.ty)

      # 3.3) Nếu là ăn thường (không EP) và đích vốn có quân -> khôi phục đúng instance cũ
      if (not mv.is_en_passant) and (dst_piece_before is not None):
        cell = self.grid[mv.tx][mv.ty]
        try:
          cell.set_piece(dst_piece_before)
        except Exception:
          try:
            cell.piece = dst_piece_before
          except Exception:
            self.grid[mv.tx][mv.ty] = dst_piece_before
        if hasattr(self, "_index_add"):
          self._index_add(mv.tx, mv.ty)
        is_royal = getattr(dst_piece_before, "is_royal", getattr(dst_piece_before, "_is_royal", False))
        if is_royal:
          try:
            self._royal_pos[dst_piece_before.color].add((mv.tx, mv.ty))
          except Exception:
            pass

      # 3.4) Nếu là EP, khôi phục nạn nhân ở (cx,cy)
      if mv.is_en_passant and ep_victim_pos is not None and ep_victim_piece is not None:
        cx, cy = ep_victim_pos
        cell = self.grid[cx][cy]
        try:
          cell.set_piece(ep_victim_piece)
        except Exception:
          try:
            cell.piece = ep_victim_piece
          except Exception:
            self.grid[cx][cy] = ep_victim_piece
        if hasattr(self, "_index_add"):
          self._index_add(cx, cy)
        is_royal = getattr(ep_victim_piece, "is_royal", getattr(ep_victim_piece, "_is_royal", False))
        if is_royal:
          try:
            self._royal_pos[ep_victim_piece.color].add((cx, cy))
          except Exception:
            pass

      # 3.5) Đặt lại quân nguồn về vị trí cũ (đúng instance gốc)
      cell = self.grid[mv.fx][mv.fy]
      try:
        cell.set_piece(src_piece)
      except Exception:
        try:
          cell.piece = src_piece
        except Exception:
          self.grid[mv.fx][mv.fy] = src_piece
      if hasattr(self, "_index_add"):
        self._index_add(mv.fx, mv.fy)
      is_royal = getattr(src_piece, "is_royal", getattr(src_piece, "_is_royal", False))
      if is_royal:
        try:
          self._royal_pos[src_piece.color].add((mv.fx, mv.fy))
        except Exception:
          pass

    return in_check
  
  def is_in_check(self, color: str) -> bool:
    """
    Kiểm tra bên `color` ('w' hoặc 'b') có đang bị chiếu không.
    Tương thích cache: self._royal_pos: dict[str, set[tuple[int,int]]]
    (có thể có 0, 1, hoặc nhiều ô 'royal' cho mỗi màu).
    Trả về:
      - True nếu ít nhất một ô royal của `color` đang bị tấn công.
      - False nếu không ô nào bị tấn công (hoặc set rỗng).
    Raises:
      ValueError: nếu self._royal_pos không tồn tại/không phải dict hoặc thiếu key `color`.
    """
    rp = getattr(self, "_royal_pos", None)
    if not isinstance(rp, dict) or color not in rp:
      raise ValueError("Thiếu cache royal cho màu yêu cầu.")

    positions = rp[color]

    # Chuẩn hoá phòng khi triển khai khác: tuple đơn → bọc thành set một phần tử
    if isinstance(positions, tuple) and len(positions) == 2 and all(isinstance(v, int) for v in positions):
      positions = {positions}

    if not isinstance(positions, set):
      raise ValueError("Định dạng cache royal không hợp lệ (kỳ vọng set[(x,y)]).")

    opponent = 'b' if color == 'w' else 'w'
    for rx, ry in positions:
      if self.is_square_attacked(rx, ry, opponent):
        return True
    return False
  
  def is_square_attacked(self, x: int, y: int, by_color: str) -> bool:
    """
    Trả về True nếu ô (x,y) đang bị bên `by_color` khống chế.

    Hiệu năng:
      - Duyệt CHỈ các quân của `by_color` từ chỉ mục self._pieces → O(P) với P ≈ số quân màu đó.
      - Thoát sớm ngay khi có 1 quân tấn công tới (x,y).
      - Dựa vào Piece.can_attack(...) nên KHÔNG sinh list Move; EP mặc nhiên bị bỏ qua.

    Ghi chú:
      - Yêu cầu các quân đã có can_attack tối ưu (N,K,M,δ,Y,V,H,R,B,Q,P…).
      - An toàn trước mục chỉ mục “lỗi thời” bằng cách đối chiếu lại p tại (i,j).
    """
    at = self.at
    bucket = self._pieces.get(by_color, ())
    for p, i, j in bucket:
      if at(i, j) is not p:
        continue
      if p.can_attack(self, i, j, x, y):
        return True
    return False
  
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
      self.clear(cx, cy)  # clear(...) nên đã tự xử lý royal-cache nếu nạn nhân là royal

    # 2) Ăn thường (khi không phải EP)
    dst_piece = self.at(mv.tx, mv.ty)
    if dst_piece is not None and dst_piece.color == piece.color:
      raise ValueError("Destination occupied by same-color piece.")
    if dst_piece is not None and not mv.is_en_passant:
      # Gỡ mục index của quân bị ăn ở đích trước khi xóa
      if hasattr(self, "_index_remove"):
        self._index_remove(mv.tx, mv.ty)
      self.clear(mv.tx, mv.ty)  # clear(...) cũng xử lý royal-cache nếu cần

    # 3) Di chuyển quân (nguồn -> đích) mà KHÔNG thay thế ô (Square)
    #    - clear ô nguồn (đặt piece=None)
    #    - đặt piece vào ô đích qua thuộc tính .piece
    self.clear(mv.fx, mv.fy)  # nếu piece là royal, cache nguồn (nếu có) sẽ được unset tại đây
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

    # >>> ROYAL-CACHE: cập nhật vị trí mới nếu quân đến đích (sau promote) là royal
    occupant = promoted if promoted is not None else piece
    is_royal = getattr(occupant, "is_royal", None)
    if is_royal is None:
      # fallback nếu chưa có property is_royal
      is_royal = getattr(occupant, "_is_royal", False)
    if is_royal:
      setter = getattr(self, "_royal_cache_set", None)
      if callable(setter):
        setter(occupant.color, (mv.tx, mv.ty))
      else:
        # fallback an toàn nếu helper chưa sẵn sàng
        try:
          if not isinstance(getattr(self, "_royal_pos", None), dict):
            self._royal_pos = {'w': None, 'b': None}
          self._royal_pos[occupant.color] = (mv.tx, mv.ty)
        except Exception:
          pass
    # <<< ROYAL-CACHE

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
  # --- Mock test: checkmate vs non-mate ---
  print("\n[MockTest] Checkmate & Non-mate smoke test")

  b = Board(10, 10)  # bảng trống nếu không gọi setup_from_layout()
  # TH1: Mate đơn giản
  # Vua trắng ở góc (0,0); Hậu đen (1,1) chiếu; Vua đen (2,2) bảo vệ ô (1,1)
  b.put(0, 0, 'K', 'w')
  b.put(1, 1, 'Q', 'b')
  b.put(2, 2, 'K', 'b')
  b.set_royal(0,0)
  print(b.as_ascii())
  print("In-check (w):", b.is_in_check('w'))
  print("Legal moves (w):", len(b.legal_moves_for('w')))
  # print("Is checkmated (w):", b.is_checkmated('w'))

  # # TH2: Không còn là mate (đưa Vua đen ra xa để K trắng bắt được Q)
  # b2 = Board(10, 10)
  # b2.put(0, 0, 'K', 'w')
  # b2.put(1, 1, 'Q', 'b')
  # b2.put(3, 3, 'K', 'b')  # xa hơn, ô (1,1) không còn bị vua đen khống chế
  # print("In-check (w) #2:", b2.is_in_check('w'))
  # print("Legal moves (w) #2:", len(b2.legal_moves_for('w')))
  # print("Is checkmated (w) #2:", b2.is_checkmated('w'))
