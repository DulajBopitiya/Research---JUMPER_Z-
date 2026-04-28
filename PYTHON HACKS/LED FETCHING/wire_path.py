# wire_path.py
import re

ROW_AE = "abcde"
ROW_FJ = "fghij"

def parse_bb_hole(node: str):
    """
    bb1:<1..30>t.<a..e>  -> mid1
    bb1:<1..30>b.<f..j>  -> mid2
    returns: (half, col0_29, rowIndex0_4)
    """
    node = node.strip()
    m = re.match(r"^bb1:(\d+)([tb])\.([a-j])$", node)
    if not m:
        return None

    col = int(m.group(1)) - 1
    side = m.group(2)
    rowL = m.group(3)

    if side == "t" and rowL in ROW_AE:
        return ("mid1", col, ROW_AE.index(rowL))
    if side == "b" and rowL in ROW_FJ:
        return ("mid2", col, ROW_FJ.index(rowL))

    return None

def _mk_node(half: str, col: int, row: int):
    side = "t" if half == "mid1" else "b"
    rows = ROW_AE if half == "mid1" else ROW_FJ
    return f"bb1:{col+1}{side}.{rows[row]}"

def expand_manhattan(a: str, b: str, order: str = "vh"):
    """
    Returns list of bb nodes INCLUDING endpoints along an L path.
    order:
      "hv" = horizontal then vertical (corner at (bx, ay))
      "vh" = vertical then horizontal (corner at (ax, by))
    """
    pa = parse_bb_hole(a)
    pb = parse_bb_hole(b)
    if not pa or not pb:
        return None
    if pa[0] != pb[0]:
        return None

    half, ax, ay = pa
    _,    bx, by = pb

    nodes = []

    if order.lower() == "hv":
        # (ax,ay) -> (bx,ay) then (bx,ay) -> (bx,by)
        step_x = 1 if bx >= ax else -1
        for x in range(ax, bx + step_x, step_x):
            nodes.append(_mk_node(half, x, ay))

        step_y = 1 if by >= ay else -1
        for y in range(ay + step_y, by + step_y, step_y):
            nodes.append(_mk_node(half, bx, y))

    else:  # "vh"
        # (ax,ay) -> (ax,by) then (ax,by) -> (bx,by)
        step_y = 1 if by >= ay else -1
        for y in range(ay, by + step_y, step_y):
            nodes.append(_mk_node(half, ax, y))

        step_x = 1 if bx >= ax else -1
        for x in range(ax + step_x, bx + step_x, step_x):
            nodes.append(_mk_node(half, x, by))

    return nodes


def expand_logical_path(a_log, b_log):
    """
    Generate a list of [section, row, col] logical points for cross-section paths.
    Rail↔M1 and Rail↔M2 paths: the rail col maps 1:1 to the M1/M2 col (no offset).
    All intermediate rows at the junction column are filled to avoid visual gaps.

      T  → M1  T(r_a,c_a) → M1(0..r_b, c_a) → horizontal M1(r_b, c_a..c_b)
      M1 → T   horizontal M1(r_a, c_a..c_b) → M1(r_a..0, c_b) → T(r_b, c_b)
      M2 → B   horizontal M2(r_a, c_a..c_b) → M2(r_a..4, c_b) → B(r_b, c_b)
      B  → M2  B(r_a,c_a) → M2(4..r_b, c_a) → horizontal M2(r_b, c_a..c_b)

    Rail columns: 0-24.  M1/M2 columns: 0-29.
    Returns None if the pair is not a supported cross-section combination.
    """
    sec_a, r_a, c_a = a_log
    sec_b, r_b, c_b = b_log
    pts = []

    # ── T → M1 ──────────────────────────────────────────────────────────────────
    # Rail at T col c_a sits above M1 col c_a (1:1 column alignment).
    # Drop through M1 rows 0..r_b at that column, then go horizontal to c_b.
    if sec_a == "T" and sec_b == "M1":
        pts.append(["T", r_a, c_a])
        for r in range(0, r_b + 1):           # rows 0 … r_b at c_a
            pts.append(["M1", r, c_a])
        if c_b != c_a:
            step = 1 if c_b > c_a else -1
            for c in range(c_a + step, c_b + step, step):
                pts.append(["M1", r_b, c])
        return pts

    # ── M1 → T ──────────────────────────────────────────────────────────────────
    # Go horizontal in M1 from c_a to c_b, then rise through rows r_a..0, then rail.
    if sec_a == "M1" and sec_b == "T":
        if c_a != c_b:
            step = 1 if c_b > c_a else -1
            for c in range(c_a, c_b, step):   # up to but not including c_b
                pts.append(["M1", r_a, c])
        for r in range(r_a, -1, -1):          # rows r_a … 0 at c_b
            pts.append(["M1", r, c_b])
        pts.append(["T", r_b, c_b])
        return pts

    # ── M2 → B ──────────────────────────────────────────────────────────────────
    # Go horizontal in M2 from c_a to c_b, then descend through rows r_a..4, then rail.
    if sec_a == "M2" and sec_b == "B":
        if c_a != c_b:
            step = 1 if c_b > c_a else -1
            for c in range(c_a, c_b, step):   # up to but not including c_b
                pts.append(["M2", r_a, c])
        for r in range(r_a, 5):               # rows r_a … 4 at c_b
            pts.append(["M2", r, c_b])
        pts.append(["B", r_b, c_b])
        return pts

    # ── B → M2 ──────────────────────────────────────────────────────────────────
    # Rail at B col c_a sits below M2 col c_a (1:1 column alignment).
    # Rise through M2 rows 4..r_b at that column, then go horizontal to c_b.
    if sec_a == "B" and sec_b == "M2":
        pts.append(["B", r_a, c_a])
        for r in range(4, r_b - 1, -1):       # rows 4 … r_b at c_a
            pts.append(["M2", r, c_a])
        if c_b != c_a:
            step = 1 if c_b > c_a else -1
            for c in range(c_a + step, c_b + step, step):
                pts.append(["M2", r_b, c])
        return pts

    return None