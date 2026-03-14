import re

ROW_AE = "abcde"
ROW_FJ = "fghij"

def wokwi_node_to_logical(node: str):
    """
    Returns a tuple describing your logical LED section coordinates:
      ("T", row, col)   top rail      (row 0..1, col 0..24)
      ("B", row, col)   bottom rail   (row 0..1, col 0..24)
      ("M1", row, col)  middle1       (row 0..4, col 0..29)
      ("M2", row, col)  middle2       (row 0..4, col 0..29)
    Or None if not a breadboard hole/rail node.
    """

    node = node.strip()

    # Rails: bb1:tp.1, bb1:tn.2, bb1:bp.25, bb1:bn.1
    m = re.match(r"^bb1:(tp|tn|bp|bn)\.(\d+)$", node)
    if m:
        rail = m.group(1)
        n = int(m.group(2))       # 1..25
        col = n - 1               # 0..24

        if rail == "tp": return ("T", 0, col)  # top positive row0
        if rail == "tn": return ("T", 1, col)  # top negative row1
        if rail == "bp": return ("B", 0, col)  # bottom positive row0
        if rail == "bn": return ("B", 1, col)  # bottom negative row1

    # Terminal strips: bb1:2t.c , bb1:22t.a , bb1:29b.j
    m = re.match(r"^bb1:(\d+)([tb])\.([a-j])$", node)
    if m:
        col_num = int(m.group(1))   # 1..30
        side = m.group(2)           # t or b
        rowL = m.group(3)           # a..j
        col = col_num - 1           # 0..29

        # Middle 1: top half a..e
        if side == "t" and rowL in ROW_AE:
            row = ROW_AE.index(rowL)   # a=0..e=4
            return ("M1", row, col)

        # Middle 2: bottom half f..j
        if side == "b" and rowL in ROW_FJ:
            row = ROW_FJ.index(rowL)   # f=0..j=4
            return ("M2", row, col)

    return None

def fmt_logical(l):
    if l is None:
        return "UNMAPPED"
    sec, r, c = l
    return f"{sec}({r},{c})"