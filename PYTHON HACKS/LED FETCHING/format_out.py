from led_map import wokwi_node_to_led
from wire_path import expand_manhattan
from logical_map import wokwi_node_to_logical, fmt_logical

def _nodes_to_logical_points(nodes, drop_unmapped=True):
    """
    Convert a list of wokwi nodes into logical points:
      ["bb1:2t.a", ...] -> [["M1",0,1], ...]
    """
    pts = []
    for n in nodes:
        l = wokwi_node_to_logical(n)
        if l is None:
            if drop_unmapped:
                return None
            else:
                continue
        pts.append([l[0], int(l[1]), int(l[2])])
    return pts


def nodes_to_leds(nodes):
    mapped = []
    unmapped = []
    for n in nodes:
        idx = wokwi_node_to_led(n)
        if idx is None:
            unmapped.append(n)
        else:
            mapped.append((n, idx))
    mapped.sort(key=lambda x: x[1])
    return mapped, unmapped


def print_connections(connections, limit=None):
    print("\n=== RAW CONNECTIONS (WITH PATH) ===")
    shown = 0
    for c in connections:
        if len(c) < 2:
            continue

        a, b = c[0], c[1]
        color = c[2] if len(c) > 2 else ""
        instr = c[3] if len(c) > 3 else []

        path_nodes = expand_manhattan(a, b)

        print(f"\n- {a} -> {b}  color={color}  instr={instr}")

        if path_nodes:
            mapped, unmapped = nodes_to_leds(path_nodes)
            print(f"  Path nodes: {len(path_nodes)}  mapped LEDs: {len(mapped)}  unmapped: {len(unmapped)}")
            print("  LED indices:", [idx for _, idx in mapped])
        else:
            la = wokwi_node_to_led(a)
            lb = wokwi_node_to_led(b)
            print(f"  (no path expansion) LED: {la} -> {lb}")

        shown += 1
        if limit and shown >= limit:
            print(f"\n... (showing first {limit})")
            break


def print_nets(nets, max_nets=20):
    print("\n=== NETS (GROUPED) ===")
    for i, net in enumerate(nets[:max_nets]):
        mapped, unmapped = nodes_to_leds(net)
        print(f"\nNet {i}  nodes={len(net)}  mapped_leds={len(mapped)}  unmapped={len(unmapped)}")
        if mapped:
            print("  Mapped:")
            for n, idx in mapped:
                print(f"    {n:12s} -> LED {idx}")
        if unmapped:
            print("  Unmapped:")
            for n in unmapped:
                print(f"    {n}")
    if len(nets) > max_nets:
        print(f"\n... ({len(nets)-max_nets} more nets not shown)")


def print_connections_logical(connections, limit=None):
    print("\n=== RAW CONNECTIONS (LOGICAL COORDS) ===")
    shown = 0
    for c in connections:
        if len(c) < 2:
            continue
        a, b = c[0], c[1]
        color = c[2] if len(c) > 2 else ""
        la = wokwi_node_to_logical(a)
        lb = wokwi_node_to_logical(b)

        print(f"- {a:12s} -> {b:12s}  color={color:6s}  {fmt_logical(la)} -> {fmt_logical(lb)}")

        shown += 1
        if limit and shown >= limit:
            print(f"... (showing first {limit})")
            break
        
def nodes_to_logical_points(nodes):
    pts = []
    for n in nodes:
        l = wokwi_node_to_logical(n)
        if l is None:
            return None
        pts.append([l[0], int(l[1]), int(l[2])])  # ["M1",row,col]
    return pts

def _expand_cross_m1_m2(a, b):
    """
    Expand an M1↔M2 cross-section wire into a full path.
    Routing uses the SOURCE endpoint's column as the crossing column so the
    visual path matches Wokwi's wire routing:

    M1→M2 (a is M1):
      1. M1: src_row → row 4 at src_col (down to gap)
      2. M2: row 0 → dst_row at src_col (drop into M2)
      3. M2: horizontal at dst_row from src_col to dst_col

    M2→M1 (a is M2):
      1. M2: src_row → row 0 at src_col (up to gap)
      2. M1: row 4 → dst_row at src_col (rise into M1)
      3. M1: horizontal at dst_row from src_col to dst_col

    Both a and b are [section, row, col] lists.
    Returns a list of points, or None if not an M1↔M2 pair.
    """
    if a[0] == 'M1' and b[0] == 'M2':
        src_row, src_col = a[1], a[2]
        dst_row, dst_col = b[1], b[2]

        pts = []
        for r in range(src_row, 5):
            pts.append(['M1', r, src_col])
        for r in range(0, dst_row + 1):
            pts.append(['M2', r, src_col])
        step = 1 if dst_col >= src_col else -1
        for c in range(src_col, dst_col + step, step):
            pts.append(['M2', dst_row, c])
        return pts

    elif a[0] == 'M2' and b[0] == 'M1':
        src_row, src_col = a[1], a[2]
        dst_row, dst_col = b[1], b[2]

        pts = []
        for r in range(src_row, -1, -1):
            pts.append(['M2', r, src_col])
        for r in range(4, dst_row - 1, -1):
            pts.append(['M1', r, src_col])
        step = 1 if dst_col >= src_col else -1
        for c in range(src_col, dst_col + step, step):
            pts.append(['M1', dst_row, c])
        return pts

    else:
        return None  # Not M1↔M2 — caller falls back to endpoint-only


def connections_to_logical_wires(connections, drop_unmapped=True, path_order="vh"):
    wires = []

    for c in connections:
        if len(c) < 2:
            continue

        a_node, b_node = c[0], c[1]
        color = c[2] if len(c) > 2 else ""

        a = wokwi_node_to_logical(a_node)
        b = wokwi_node_to_logical(b_node)

        # Both unmapped (e.g. component-to-component) — nothing to show
        if a is None and b is None:
            continue

        # One endpoint has no LED position (e.g. nano pin) — show only the
        # breadboard endpoint as a blinking dot; no wire path needed
        if a is None:
            a = b
        elif b is None:
            b = a

        w = {
            "color": color,
            "a": [a[0], int(a[1]), int(a[2])],
            "b": [b[0], int(b[1]), int(b[2])],
            "raw": [a_node, b_node],
        }

        # ---- full path (same section only) or endpoints ----
        path_nodes = expand_manhattan(a_node, b_node, order=path_order)
        if path_nodes:
            pts = nodes_to_logical_points(path_nodes)
            if pts:
                w["points"] = pts
            else:
                w["points"] = [w["a"], w["b"]]
        else:
            # Cross-section wire — try to expand M1↔M2 path; fall back to
            # endpoints only for rail↔M1, rail↔M2, or other combinations.
            cross_pts = _expand_cross_m1_m2(w["a"], w["b"])
            w["points"] = cross_pts if cross_pts else [w["a"], w["b"]]

        wires.append(w)

    return wires