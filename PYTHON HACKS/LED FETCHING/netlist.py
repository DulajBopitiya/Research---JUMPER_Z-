from collections import defaultdict
from jz_map import wokwi_node_to_jz_name

class DSU:
    def __init__(self):
        self.p = {}

    def find(self, x):
        self.p.setdefault(x, x)
        if self.p[x] != x:
            self.p[x] = self.find(self.p[x])
        return self.p[x]

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[rb] = ra

def normalize_pin(pin: str) -> str:
    # Keep the Wokwi node exactly (bb1:2t.c etc.)
    return pin.strip()

def build_nets(connections):
    """
    connections items look like:
      [ "bb1:tp.1", "bb1:2t.c", "red", [ "v0" ] ]
    We union endpoints (index 0 and 1).
    Returns list of nets, each net is a sorted list of node strings.
    """
    dsu = DSU()
    nodes = set()

    for c in connections:
        if len(c) < 2:
            continue
        a = normalize_pin(c[0])
        b = normalize_pin(c[1])
        dsu.union(a, b)
        nodes.add(a)
        nodes.add(b)

    groups = defaultdict(list)
    for n in nodes:
        groups[dsu.find(n)].append(n)

    nets = [sorted(v) for v in groups.values()]
    nets.sort(key=len, reverse=True)  # biggest nets first
    return nets


def build_jz_nets(connections):
    """
    Build nets from Wokwi connections and convert to JumperZ 'connect' format.

    Returns a list of dicts ready to use as the 'nets' array in:
      {"cmd": "connect", "nets": [...]}

    Each dict:  {"nodes": ["TOP_5", "BOTTOM_3", ...], "color": "#ff0000"}

    Nets with fewer than 2 mappable JumperZ nodes are silently dropped.
    """
    dsu = DSU()
    all_nodes = set()
    net_colors = {}   # dsu-root → first color seen for this net

    for c in connections:
        if len(c) < 2:
            continue
        a = normalize_pin(c[0])
        b = normalize_pin(c[1])
        color = c[2] if len(c) > 2 else ""

        dsu.union(a, b)
        all_nodes.add(a)
        all_nodes.add(b)

        root = dsu.find(a)
        if root not in net_colors and color:
            net_colors[root] = color

    # After all unions are done, re-derive roots (they may have changed)
    for node in list(all_nodes):
        root = dsu.find(node)
        # propagate colors: if this node's connection had a color, keep it
    # Re-scan connections to fix net_colors with final roots
    net_colors_final = {}
    for c in connections:
        if len(c) < 2:
            continue
        root = dsu.find(normalize_pin(c[0]))
        color = c[2] if len(c) > 2 else ""
        if root not in net_colors_final and color:
            net_colors_final[root] = color

    # Group wokwi nodes by net
    groups = defaultdict(set)
    for n in all_nodes:
        groups[dsu.find(n)].add(n)

    jz_nets = []
    for root, wokwi_nodes in groups.items():
        jz_names = []
        seen = set()
        for wn in sorted(wokwi_nodes):        # sort for determinism
            jz = wokwi_node_to_jz_name(wn)
            if jz and jz not in seen:
                seen.add(jz)
                jz_names.append(jz)

        if len(jz_names) < 2:
            continue                           # need at least 2 nodes to connect

        color = net_colors_final.get(root, "#ffffff")
        jz_nets.append({"nodes": jz_names, "color": color})

    return jz_nets