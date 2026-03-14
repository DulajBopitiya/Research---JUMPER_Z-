from src.logic.wokwi_pipeline.wokwi_fetch import fetch_diagram_json
from src.logic.wokwi_pipeline.netlist import build_nets
from src.logic.wokwi_pipeline.format_out import (
    print_connections,
    print_connections_logical,
    print_nets,
    connections_to_logical_wires,
)
from src.logic.wokwi_pipeline.bridge_send import send_wokwi_wires

import io
import contextlib


class WokwiHandler:
    def __init__(self):
        self.project_url = None

    def _open_wokwi(self):
        import webbrowser
        webbrowser.open("https://wokwi.com")

    def sync(self, project_url: str | None = None, send_to_board: bool = True):
        """
        Main entry point called by UI.
        Returns dict with display-ready text + metadata.
        """

        if project_url:
            self.project_url = project_url

        if not self.project_url:
            raise RuntimeError("No Wokwi project URL provided")

        # --- capture all prints into a string ---
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):

            diagram = fetch_diagram_json(self.project_url)
            connections = diagram.get("connections", [])

            print(f"Fetched diagram.json")
            print(f"Connections: {len(connections)}\n")

            print_connections(connections, limit=40)
            print_connections_logical(connections)

            nets = build_nets(connections)
            print_nets(nets, max_nets=20)

            wires = connections_to_logical_wires(connections)
            print(f"\nLogical wires: {len(wires)}")

            if send_to_board:
                port = send_wokwi_wires(wires)
                print(f"\nSent to board on {port}")

        return {
            "diagram_text": buffer.getvalue(),
            "connections": len(connections),
            "nets": len(nets),
            "wires": len(wires),
        }