import re

TOP_BASE = 0
TOP_ROWS = 2
TOP_COLS = 25
TOP_BLOCK_WIDTH = 5

MID1_BASE = 50
MID1_ROWS = 5
MID1_COLS = 30

MID2_BASE = 200
MID2_ROWS = 5
MID2_COLS = 30

BOTTOM_BASE = 350
BOTTOM_ROWS = 2
BOTTOM_COLS = 25
BOTTOM_BLOCK_WIDTH = 5

ROW_AE = "abcde"
ROW_FJ = "fghij"

def topRailIndex(row: int, col: int):
    if not (0 <= row < TOP_ROWS and 0 <= col < TOP_COLS):
        return None
    block = col // TOP_BLOCK_WIDTH
    local = col % TOP_BLOCK_WIDTH
    blockBase = TOP_BASE + block * 10
    return blockBase + local if row == 0 else blockBase + (9 - local)

def bottomRailIndex(row: int, col: int):
    if not (0 <= row < BOTTOM_ROWS and 0 <= col < BOTTOM_COLS):
        return None
    block = col // BOTTOM_BLOCK_WIDTH
    local = col % BOTTOM_BLOCK_WIDTH
    blockBase = BOTTOM_BASE + block * 10
    return blockBase + local if row == 0 else blockBase + (9 - local)

def mid1Index(row: int, col: int):
    if not (0 <= row < MID1_ROWS and 0 <= col < MID1_COLS):
        return None
    return MID1_BASE + col * MID1_ROWS + row

def mid2Index(row: int, col: int):
    if not (0 <= row < MID2_ROWS and 0 <= col < MID2_COLS):
        return None
    return MID2_BASE + col * MID2_ROWS + row

def wokwi_node_to_led(node: str):
    """
    Supports:
      bb1:tp.1 .. bb1:tp.25  -> top rail row0 col
      bb1:tn.1 .. bb1:tn.25  -> top rail row1 col
      bb1:bp.1 .. bb1:bp.25  -> bottom rail row0 col
      bb1:bn.1 .. bb1:bn.25  -> bottom rail row1 col

      bb1:<1..30>t.<a..e>    -> MID1 (50..199)
      bb1:<1..30>b.<f..j>    -> MID2 (200..349)
    """
    node = node.strip()

    # rails: tp.1 / tn.25 / bp.1 / bn.25
    m = re.match(r"^bb1:(tp|tn|bp|bn)\.(\d+)$", node)
    if m:
        rail = m.group(1)
        n = int(m.group(2))  # 1..25
        col = n - 1
        if rail == "tp": return topRailIndex(0, col)
        if rail == "tn": return topRailIndex(1, col)
        if rail == "bp": return bottomRailIndex(0, col)
        if rail == "bn": return bottomRailIndex(1, col)

    # terminal strips: 2t.c / 15t.a / 7b.f
    m = re.match(r"^bb1:(\d+)([tb])\.([a-j])$", node)
    if m:
        col_num = int(m.group(1))  # 1..30
        side = m.group(2)          # t/b
        row_letter = m.group(3)    # a..j
        col = col_num - 1          # 0..29

        if side == "t" and row_letter in ROW_AE:
            row = ROW_AE.index(row_letter)  # a=0..e=4
            return mid1Index(row, col)

        if side == "b" and row_letter in ROW_FJ:
            row = ROW_FJ.index(row_letter)  # f=0..j=4
            return mid2Index(row, col)

    return None