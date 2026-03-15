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
    Matches Wokwi v0 routing (vertical first from the first endpoint).

    Supported pairs (both directions):
      T  → M1  — rail drops at rail col, then horizontal in M1
      M1 → T  — vertical up from M1 col to rail, then horizontal in rail
      M2 → B  — vertical drop in M2, then horizontal in B
      B  → M2 — horizontal in B to M2 col, then vertical up in M2

    Rail columns are 0-24; M1/M2 columns are 0-29.

    Returns None if the pair is not a supported cross-section combination.
    """
    sec_a, r_a, c_a = a_log
    sec_b, r_b, c_b = b_log

    pts = []

    # ── T → M1 (rail is first endpoint) ──────────────────────────────────────
    # v0: vertical from rail col c_a down into M1, then horizontal in M1 to c_b
    if sec_a == "T" and sec_b == "M1":
        pts.append(["T", r_a, c_a])
        # If on positive rail, also cross negative rail row at same col
        if r_a == 0:
            pts.append(["T", 1, c_a])
        # Drop into M1 at c_a from row 0 down to r_b
        for r in range(0, r_b + 1):
            pts.append(["M1", r, c_a])
        # Horizontal in M1 at r_b from c_a to c_b
        step = 1 if c_b >= c_a else -1
        for c in range(c_a + step, c_b + step, step):
            pts.append(["M1", r_b, c])
        return pts

    # ── M1 → T (M1 is first endpoint) ────────────────────────────────────────
    # v0: vertical from M1 col c_a up through M1 to rail, then horizontal in rail
    if sec_a == "M1" and sec_b == "T":
        # Rise from r_a up to row 0 in M1 at c_a
        for r in range(r_a, -1, -1):
            pts.append(["M1", r, c_a])
        # Enter negative rail at c_a
        pts.append(["T", 1, c_a])
        # If destination is positive rail, also cross to positive
        if r_b == 0:
            pts.append(["T", 0, c_a])
        # Horizontal in T at r_b from c_a to c_b
        step = 1 if c_b >= c_a else -1
        for c in range(c_a + step, c_b + step, step):
            pts.append(["T", r_b, c])
        return pts

    # ── M2 → B (M2 is first endpoint) ────────────────────────────────────────
    # v0: vertical down in M2 at c_a (capped to rail range), then horizontal in B
    if sec_a == "M2" and sec_b == "B":
        c_rail = min(c_a, 24)
        if c_a > 24:
            for c in range(c_a, c_rail - 1, -1):
                pts.append(["M2", r_a, c])
        else:
            pts.append(["M2", r_a, c_a])
        for r in range(r_a + 1, 5):
            pts.append(["M2", r, c_rail])
        for r in range(0, r_b + 1):
            pts.append(["B", r, c_rail])
        step2 = 1 if c_b >= c_rail else -1
        for c in range(c_rail + step2, c_b + step2, step2):
            pts.append(["B", r_b, c])
        return pts

    # ── B → M2 (B is first endpoint) ─────────────────────────────────────────
    # v0: horizontal in B from c_a to M2 col (capped), then vertical up in M2
    if sec_a == "B" and sec_b == "M2":
        c_rail = min(c_b, 24)
        step = 1 if c_rail >= c_a else -1
        for c in range(c_a, c_rail + step, step):
            pts.append(["B", r_a, c])
        if r_a == 0:
            pts.append(["B", 1, c_rail])
        for r in range(4, r_b - 1, -1):
            pts.append(["M2", r, c_rail])
        if c_b > 24:
            for c in range(c_rail + 1, c_b + 1):
                pts.append(["M2", r_b, c])
        return pts

    return None