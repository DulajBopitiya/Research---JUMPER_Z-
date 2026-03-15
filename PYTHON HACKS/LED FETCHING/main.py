from wokwi_fetch import fetch_diagram_json
from netlist import build_nets, build_jz_nets
from format_out import (
    print_connections,
    print_connections_logical,
    print_nets,
    connections_to_logical_wires,
)

SEND_TO_BOARD = True   # set False for terminal-only output

# "wires"   → wokwi_wires command (LED visualisation only, no switching)
# "netlist" → connect command (closes real CH446Q switches + lights endpoints)
SEND_MODE = "netlist"


def main():
    # wokwi_url = "https://wokwi.com/projects/456400671658046465"
    wokwi_url = "https://wokwi.com/projects/458453134358605825"
    
    diagram = fetch_diagram_json(wokwi_url)

    connections = diagram.get("connections", [])
    print(f"Fetched diagram.json from: {wokwi_url}")
    print(f"Connections: {len(connections)}")

    print_connections(connections, limit=80)
    print_connections_logical(connections)

    nets = build_nets(connections)
    print(f"\nTotal nets found: {len(nets)}")
    print_nets(nets, max_nets=30)

    # Always build wire paths (needed for both modes)
    wires = connections_to_logical_wires(connections, drop_unmapped=True, path_order="vh")
    print(f"\nLogical wires ready to send: {len(wires)}")
    for w in wires:
        a = w["a"]
        b = w["b"]
        pts = w.get("points", [])
        cross = (a[0] != b[0])  # cross-section if sections differ
        print(f"- {w['raw'][0]:12s} -> {w['raw'][1]:12s}  color={w['color']:6s}  "
              f"{a[0]}({a[1]},{a[2]}) -> {b[0]}({b[1]},{b[2]})  points={len(pts)}"
              + ("  [CROSS]" if cross else ""))
        if cross or len(pts) <= 2:
            print(f"    points: {pts}")

    if SEND_MODE == "netlist":
        # ── connect mode: real CH446Q switching + full LED paths ──────────────
        jz_nets = build_jz_nets(connections)
        print(f"\nJumperZ nets ready to connect: {len(jz_nets)}")
        for jn in jz_nets:
            print(f"  color={jn['color']:8s}  nodes={jn['nodes']}")

        if SEND_TO_BOARD:
            try:
                from bridge_send import send_connect_then_wires
                port = send_connect_then_wires(jz_nets, wires, prefer_bridge=True)
                print(f"\nSent 'connect' + 'wokwi_wires' to: {port}")
            except Exception as e:
                print("\nERROR: could not send to board:")
                print(e)

    else:
        # ── wires mode: LED-only visualisation (no switching) ─────────────────
        if SEND_TO_BOARD:
            try:
                from bridge_send import send_wokwi_wires
                port = send_wokwi_wires(wires, prefer_bridge=True)
                print(f"\nSent 'wokwi_wires' to: {port}")
            except Exception as e:
                print("\nERROR: could not send to board:")
                print(e)


if __name__ == "__main__":
    main()