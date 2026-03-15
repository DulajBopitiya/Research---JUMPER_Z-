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