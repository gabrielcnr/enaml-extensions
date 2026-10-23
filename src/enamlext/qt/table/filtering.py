from collections.abc import Generator, Iterable
from typing import Any

from enamlext.qt.table.column import Column


class Filter:
    """One filter, bound to one column."""

    def __init__(self, column: Column, expression: str):
        self.column = column
        self.expression = expression.strip()  # as entered by the user
        self._evaluate_filter = self._generate_filter_evaluation_callback()

    def __str__(self):
        return self.expression

    def _expression_startswith_operator(self, expression: str) -> bool:
        operators = {'>', '<', '>=', '<=', '==', '!='}

        return any(expression.startswith(op) for op in operators)

    def _generate_filter_evaluation_callback(self):
        if self._expression_startswith_operator(self.expression):
            try:
                code = compile(f'x {self.expression}', '<filter>', 'eval')
            except SyntaxError:
                return lambda x: False

            def callback(x):
                try:
                    return bool(eval(code, {'x': x}))
                # NameError: '== foo'. The rest: values that can't be compared or have no truth value (text or None
                # against a number, pd.NA, Decimal('NaN'), arrays), which must hide the row rather than raise.
                except (NameError, TypeError, ValueError, ArithmeticError):
                    return False

        else:
            expression = self.expression.lower()

            def callback(x):
                return expression in str(x).lower()

        return callback

    def __call__(self, item: Any) -> bool:
        value = self.column.get_value(item)
        return self._evaluate_filter(value)


# TODO: IDEA
#       we are using the Column's get_value to get the value
#       that is then used to evaluate the filter expression
#       We can have that as default behaviour, but we could also
#       allow for the underlying model to apply their own filters
#       This way it would make possible to use, for example,
#       pandas DataFrame's own filtering capabilities more
#       efficiently.


class TableFilters:
    """Collection of Filters."""

    def __init__(self, filters: list[Filter] | None = None):
        self.filters = {f.column: f for f in filters or []}

    def __len__(self):
        return len(self.filters)

    def __contains__(self, column):
        return column in self.filters

    def filter_items(self, items: Iterable) -> Generator:
        for item in items:
            if self.filter(item):
                yield item

    def filter(self, item: Any) -> bool:
        """Returns True if the given item is included after evaluating all the filters."""
        return all(column_filter(item) for column_filter in self.filters.values())

    def add_filter(self, filter: Filter) -> None:
        if filter.expression:
            self.filters[filter.column] = filter
        else:
            self.filters.pop(filter.column, None)

    def get(self, column: Column) -> Filter | None:
        return self.filters.get(column)

    def clear(self):
        self.filters = {}
