from collections import defaultdict

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