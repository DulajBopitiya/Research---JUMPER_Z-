from wokwi_fetch import fetch_diagram_json
from netlist import build_nets
from format_out import (
    print_connections,
    print_connections_logical,
    print_nets,
    connections_to_logical_wires,
)

SEND_TO_BOARD = True  # set False if you only want terminal output


def main():
    wokwi_url = "https://wokwi.com/projects/456400671658046465"
    diagram = fetch_diagram_json(wokwi_url)

    connections = diagram.get("connections", [])
    print(f"Fetched diagram.json from: {wokwi_url}")
    print(f"Connections: {len(connections)}")

    print_connections(connections, limit=80)
    print_connections_logical(connections)

    nets = build_nets(connections)
    print(f"\nTotal nets found: {len(nets)}")
    print_nets(nets, max_nets=30)

    wires = connections_to_logical_wires(connections, drop_unmapped=True, path_order="vh")
    print(f"\nLogical wires ready to send: {len(wires)}")

    for w in wires:
        a = w["a"]
        b = w["b"]
        print(f"- {w['raw'][0]:12s} -> {w['raw'][1]:12s}  color={w['color']:6s}  "
              f"{a[0]}({a[1]},{a[2]}) -> {b[0]}({b[1]},{b[2]})")

    if SEND_TO_BOARD:
        try:
            from bridge_send import send_wokwi_wires
            port = send_wokwi_wires(wires, prefer_bridge=True)
            print(f"\nSent to BRIDGE_PORT: {port}")
        except Exception as e:
            print("\nERROR: could not send to board:")
            print(e)


if __name__ == "__main__":
    main()