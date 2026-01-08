from collections import deque

class DependencyGraph:
    def __init__(self, objects):
        self.nodes = set(objects)

    def add_object(self, obj):
        self.nodes.add(obj)

    def sort(self):
        adj = {obj: [] for obj in self.nodes}
        in_degree = {obj: 0 for obj in self.nodes}

        for obj in self.nodes:
            mapper = obj._mapper
            for rel_name, rel in mapper.relationships.items():
                if rel.r_type in ("many-to-one", "one-to-one"):
                    parent = getattr(obj, rel_name, None)
                    if parent and parent in self.nodes:
                        adj[parent].append(obj)
                        in_degree[obj] += 1

        # algorytm Kahna
        queue = deque([obj for obj in self.nodes if in_degree[obj] == 0])
        sorted_list = []

        while queue:
            u = queue.popleft()
            sorted_list.append(u)
            for v in adj[u]:
                in_degree[v] -= 1
                if in_degree[v] == 0:
                    queue.append(v)

        if len(sorted_list) != len(self.nodes):
            cyclic_nodes = [obj for obj in self.nodes if in_degree[obj] > 0]
            raise RuntimeError(f"Wykryto cykl w zależnościach obiektów: {cyclic_nodes}")
            
        return sorted_list