from collections import deque

class DependencyGraph:
    def __init__(self, objects):
        self.nodes = set(objects)
        self._parent_objects = {}  # Maps child objects to their parent objects for CLASS inheritance
        self._child_to_parent = {}  # Maps child objects to parent objects for FK synchronization

    def add_object(self, obj):
        self.nodes.add(obj)

    def _create_parent_object_for_class_inheritance(self, child_obj):
        """Create a parent object from child data for CLASS inheritance."""
        child_mapper = child_obj._mapper
        
        # Check if this child needs a parent object
        if not (child_mapper.inheritance and 
                child_mapper.inheritance.strategy.name == "CLASS" and 
                child_mapper.parent):
            return None
        
        # Check if parent object already exists for this child
        if child_obj in self._parent_objects:
            return self._parent_objects[child_obj]
        
        # Create parent object from child's data
        parent_cls = child_mapper.parent.cls
        parent_obj = parent_cls()
        
        # Copy parent columns from child to parent
        parent_mapper = child_mapper.parent
        for col_name in parent_mapper.local_columns.keys():
            if hasattr(child_obj, col_name):
                value = getattr(child_obj, col_name)
                object.__setattr__(parent_obj, col_name, value)
            else:
                # If child doesn't have the value, try to get default or None
                col = parent_mapper.local_columns[col_name]
                default_value = getattr(col, 'default', None)
                if default_value is not None:
                    object.__setattr__(parent_obj, col_name, default_value)
                elif getattr(col, 'nullable', True):
                    object.__setattr__(parent_obj, col_name, None)
        
        # Mark parent as PENDING (will be inserted)
        from states import ObjectState
        object.__setattr__(parent_obj, '_orm_state', ObjectState.PENDING)
        object.__setattr__(parent_obj, '_session', getattr(child_obj, '_session', None))
        object.__setattr__(parent_obj, '_mapper', parent_mapper)
        
        # Store the mappings
        self._parent_objects[child_obj] = parent_obj
        self._child_to_parent[child_obj] = parent_obj
        
        # Also store reverse mapping for easy lookup
        if not hasattr(parent_obj, '_class_inheritance_children'):
            object.__setattr__(parent_obj, '_class_inheritance_children', [])
        parent_obj._class_inheritance_children.append(child_obj)
        
        self.nodes.add(parent_obj)
        
        return parent_obj

    def sort(self):
        adj = {obj: [] for obj in self.nodes}
        in_degree = {obj: 0 for obj in self.nodes}

        # First, create parent objects for CLASS inheritance children
        for obj in list(self.nodes):
            parent_obj = self._create_parent_object_for_class_inheritance(obj)
            if parent_obj:
                # Child depends on parent
                adj[parent_obj].append(obj)
                in_degree[obj] += 1

        # Then, handle relationship dependencies (many-to-one, one-to-one)
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
    
    def get_parent_object(self, child_obj):
        """Get the parent object for a CLASS inheritance child, if it exists."""
        return self._parent_objects.get(child_obj)
    
    def get_child_objects(self, parent_obj):
        """Get child objects for a CLASS inheritance parent, if they exist."""
        return getattr(parent_obj, '_class_inheritance_children', [])