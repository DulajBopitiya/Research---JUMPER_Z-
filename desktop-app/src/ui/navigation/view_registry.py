# src/ui/navigation/view_registry.py`

class ViewRegistry:

    def __init__(self):
        self._registry = {}

    def register(self, name: str, cls):
        self._registry[name] = cls

    def create(self, name: str, parent):

        cls = self._registry.get(name)

        if not cls:
            raise ValueError(f"View not registered: {name}")

        return cls(parent)


view_registry = ViewRegistry()