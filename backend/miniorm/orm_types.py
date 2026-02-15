class AssociationTable:
    def __init__(self, name, local_key, remote_key, local_table=None, remote_table=None):
        self.name = name
        self.local_key = local_key
        self.remote_key = remote_key
        self.local_table = local_table
        self.remote_table = remote_table

    def __repr__(self):
        return f"<AssociationTable {self.name}({self.local_key}, {self.remote_key})>"


class Relationship:
    def __init__(self, target, r_type="many-to-one", pk=False, backref=None, cascade_delete=True):
        self.target_table = target
        self.r_type = r_type
        self.pk = pk
        self.backref = backref
        self.cascade_delete = cascade_delete
        self.local_table = None
        self.remote_table = None
        self._resolved_target = None
        self._resolved_fk_name = None
        self.association_table = None

    def __repr__(self):
        target = getattr(self._resolved_target, "__name__", self.target_table)
        parts = [f"{self.r_type}", f"target={target}"]
        if self.local_table:
            parts.append(f"local_table={self.local_table}")
        if self.remote_table:
            parts.append(f"remote_table={self.remote_table}")
        if self.association_table:
            parts.append(f"association_table={self.association_table.name}")
        return f"<Relationship {', '.join(parts)}>"

class Column:
    def __init__(self, dtype, pk=False, nullable=True, unique=False, default=None):
        self.dtype = dtype
        self.pk = pk
        self.nullable = nullable
        self.unique = unique
        self.default = default

    def __eq__(self, other):
        return FilterExpr(self, '=', other)
    def __ne__(self, other):
        return FilterExpr(self, '!=', other)
    def __lt__(self, other):
        return FilterExpr(self, '<', other)
    def __le__(self, other):
        return FilterExpr(self, '<=', other)
    def __gt__(self, other):
        return FilterExpr(self, '>', other)
    def __ge__(self, other):
        return FilterExpr(self, '>=', other)

class FilterExpr:
    def __init__(self, column, op, value):
        self.column = column
        self.op = op
        self.value = value
        self.is_subquery = isinstance(value, (SubqueryExpr, QueryExpr))

class QueryExpr:
    def __init__(self, sql, params=None):
        self.sql = sql
        self.params = params or []
    def __repr__(self):
        return f"<QueryExpr {self.sql} params={self.params}>"

class SubqueryExpr:
    def __init__(self, query, params=None):
        self.query = query
        self.params = params or []
    def __repr__(self):
        return f"<SubqueryExpr {self.query} params={self.params}>"
    def __and__(self, other):
        return CombinedFilterExpr(self, 'AND', other)
    def __or__(self, other):
        return CombinedFilterExpr(self, 'OR', other)
    def __repr__(self):
        return f"<FilterExpr {self.column} {self.op} {self.value}>"

class CombinedFilterExpr:
    def __init__(self, left, op, right):
        self.left = left
        self.op = op
        self.right = right
    def __and__(self, other):
        return CombinedFilterExpr(self, 'AND', other)
    def __or__(self, other):
        return CombinedFilterExpr(self, 'OR', other)
    def __repr__(self):
        return f"<CombinedFilterExpr {self.left} {self.op} {self.right}>"
    
class Text(Column):
    def __init__(self, pk=False, nullable=True, unique=False, default=None):
        super().__init__(str, pk, nullable, unique, default)

class Number(Column):
    def __init__(self, pk=False, nullable=True, unique=False, default=None):
        super().__init__(int, pk, nullable, unique, default)

class ForeignKey(Column):
    def __init__(self, target_table, target_column, pk=False, nullable=True, unique=True, on_delete_cascade=True):
        super().__init__(int, pk=pk, nullable=nullable, unique=unique)
        self.target_table = target_table
        self.target_column = target_column
        self.on_delete_cascade = on_delete_cascade