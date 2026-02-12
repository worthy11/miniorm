class IdentityMap:
    def __init__(self):
        self._map = {}

    def get(self, model_class, pk):
        return self._map.get((model_class, pk))

    def add(self, model_class, pk, instance):
        self._map[(model_class, pk)] = instance

    def remove(self, model_class, pk):
        self._map.pop((model_class, pk), None)

    def clear(self):
        self._map.clear()