"""
Advanced filter expressions for miniorm, similar to SQLAlchemy.
Supports complex filtering without raw SQL.
"""


class FilterExpression:
    """Base class for all filter expressions"""
    
    def __invert__(self):
        """Negate a filter using the ~ operator"""
        return NotFilter(self)


class ColumnFilter(FilterExpression):
    """Represents a column that can be used in filter expressions"""
    def __init__(self, column_name, model_class=None):
        self.column_name = column_name
        self.model_class = model_class
    
    def __eq__(self, other):
        """Equality comparison"""
        return ComparisonFilter(self.column_name, '=', other, self.model_class)
    
    def __ne__(self, other):
        """Not equal comparison"""
        return ComparisonFilter(self.column_name, '!=', other, self.model_class)
    
    def __lt__(self, other):
        """Less than comparison"""
        return ComparisonFilter(self.column_name, '<', other, self.model_class)
    
    def __le__(self, other):
        """Less than or equal comparison"""
        return ComparisonFilter(self.column_name, '<=', other, self.model_class)
    
    def __gt__(self, other):
        """Greater than comparison"""
        return ComparisonFilter(self.column_name, '>', other, self.model_class)
    
    def __ge__(self, other):
        """Greater than or equal comparison"""
        return ComparisonFilter(self.column_name, '>=', other, self.model_class)
    
    def __invert__(self):
        """Negate this column filter"""
        return NotFilter(ComparisonFilter(self.column_name, '__placeholder__', None, self.model_class))
    
    def in_(self, values):
        """IN operator - filter by list of values"""
        return InFilter(self.column_name, values, self.model_class)
    
    def not_in(self, values):
        """NOT IN operator"""
        return NotInFilter(self.column_name, values, self.model_class)
    
    def like(self, pattern):
        """LIKE operator for pattern matching"""
        return LikeFilter(self.column_name, pattern, self.model_class)
    
    def ilike(self, pattern):
        """Case-insensitive LIKE operator"""
        return ILikeFilter(self.column_name, pattern, self.model_class)
    
    def is_null(self):
        """Filter for NULL values"""
        return IsNullFilter(self.column_name, self.model_class)
    
    def is_not_null(self):
        """Filter for NOT NULL values"""
        return IsNotNullFilter(self.column_name, self.model_class)
    
    def between(self, lower, upper):
        """BETWEEN operator"""
        return BetweenFilter(self.column_name, lower, upper, self.model_class)


class ComparisonFilter(FilterExpression):
    """Represents a comparison filter (=, !=, <, >, <=, >=)"""
    def __init__(self, column_name, operator, value, model_class=None):
        self.column_name = column_name
        self.operator = operator
        self.value = value
        self.model_class = model_class
        # Check if value is a ColumnFilter (field-to-field comparison)
        self.is_field_comparison = isinstance(value, ColumnFilter)
    
    def __and__(self, other):
        """Combine with AND operator"""
        return CombinedFilter(self, other, logic='AND')
    
    def __or__(self, other):
        """Combine with OR operator"""
        return CombinedFilter(self, other, logic='OR')


class InFilter(FilterExpression):
    """Represents an IN filter"""
    def __init__(self, column_name, values, model_class=None):
        self.column_name = column_name
        self.values = values
        self.model_class = model_class
    
    def __and__(self, other):
        """Combine with AND operator"""
        return CombinedFilter(self, other, logic='AND')
    
    def __or__(self, other):
        """Combine with OR operator"""
        return CombinedFilter(self, other, logic='OR')


class NotInFilter(FilterExpression):
    """Represents a NOT IN filter"""
    def __init__(self, column_name, values, model_class=None):
        self.column_name = column_name
        self.values = values
        self.model_class = model_class
    
    def __and__(self, other):
        """Combine with AND operator"""
        return CombinedFilter(self, other, logic='AND')
    
    def __or__(self, other):
        """Combine with OR operator"""
        return CombinedFilter(self, other, logic='OR')


class LikeFilter(FilterExpression):
    """Represents a LIKE filter (case-sensitive)"""
    def __init__(self, column_name, pattern, model_class=None):
        self.column_name = column_name
        self.pattern = pattern
        self.model_class = model_class
    
    def __and__(self, other):
        """Combine with AND operator"""
        return CombinedFilter(self, other, logic='AND')
    
    def __or__(self, other):
        """Combine with OR operator"""
        return CombinedFilter(self, other, logic='OR')


class ILikeFilter(FilterExpression):
    """Represents a case-insensitive LIKE filter"""
    def __init__(self, column_name, pattern, model_class=None):
        self.column_name = column_name
        self.pattern = pattern
        self.model_class = model_class
    
    def __and__(self, other):
        """Combine with AND operator"""
        return CombinedFilter(self, other, logic='AND')
    
    def __or__(self, other):
        """Combine with OR operator"""
        return CombinedFilter(self, other, logic='OR')


class IsNullFilter(FilterExpression):
    """Represents IS NULL filter"""
    def __init__(self, column_name, model_class=None):
        self.column_name = column_name
        self.model_class = model_class
    
    def __and__(self, other):
        """Combine with AND operator"""
        return CombinedFilter(self, other, logic='AND')
    
    def __or__(self, other):
        """Combine with OR operator"""
        return CombinedFilter(self, other, logic='OR')


class IsNotNullFilter(FilterExpression):
    """Represents IS NOT NULL filter"""
    def __init__(self, column_name, model_class=None):
        self.column_name = column_name
        self.model_class = model_class
    
    def __and__(self, other):
        """Combine with AND operator"""
        return CombinedFilter(self, other, logic='AND')
    
    def __or__(self, other):
        """Combine with OR operator"""
        return CombinedFilter(self, other, logic='OR')


class BetweenFilter(FilterExpression):
    """Represents a BETWEEN filter"""
    def __init__(self, column_name, lower, upper, model_class=None):
        self.column_name = column_name
        self.lower = lower
        self.upper = upper
        self.model_class = model_class
    
    def __and__(self, other):
        """Combine with AND operator"""
        return CombinedFilter(self, other, logic='AND')
    
    def __or__(self, other):
        """Combine with OR operator"""
        return CombinedFilter(self, other, logic='OR')


class NotFilter(FilterExpression):
    """Negates a filter expression (NOT logic)"""
    def __init__(self, filter_expr):
        self.filter_expr = filter_expr
    
    def __and__(self, other):
        """Combine with AND operator"""
        return CombinedFilter(self, other, logic='AND')
    
    def __or__(self, other):
        """Combine with OR operator"""
        return CombinedFilter(self, other, logic='OR')


class CombinedFilter(FilterExpression):
    """Combines multiple filters with AND or OR logic"""
    def __init__(self, *filters, logic='AND'):
        self.filters = filters
        self.logic = logic.upper()
        if self.logic not in ('AND', 'OR'):
            raise ValueError("Logic must be 'AND' or 'OR'")
    
    def __and__(self, other):
        """Combine with AND operator"""
        if isinstance(other, CombinedFilter) and other.logic == 'AND':
            return CombinedFilter(*self.filters, *other.filters, logic='AND')
        return CombinedFilter(self, other, logic='AND')
    
    def __or__(self, other):
        """Combine with OR operator"""
        if isinstance(other, CombinedFilter) and other.logic == 'OR':
            return CombinedFilter(*self.filters, *other.filters, logic='OR')
        return CombinedFilter(self, other, logic='OR')


# Helper functions to easily create filter expressions
def col(column_name, model_class=None):
    """Create a ColumnFilter to start building filter expressions"""
    return ColumnFilter(column_name, model_class)


def and_(*filters):
    """Combine multiple filters with AND logic"""
    return CombinedFilter(*filters, logic='AND')


def or_(*filters):
    """Combine multiple filters with OR logic"""
    return CombinedFilter(*filters, logic='OR')

