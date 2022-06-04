from typing import Iterable, Generator, Any, List, Optional

from enamlext.qt.table.column import Column


class Filter:
    """ One filter, bound to one column.
    """
    def __init__(self, column: Column, expression: str):
        self.column = column
        self.expression = expression.strip()  # as entered by the user
        self._evaluate_filter = self._generate_filter_evaluation_callback()

    def __str__(self):
        return self.expression

    def _expression_startswith_operator(self, expression: str) -> bool:
        operators = {'>', '<', '>=', '<=', '==', '!='}

        for op in operators:
            if expression.startswith(op):
                return True

        return False

    def _generate_filter_evaluation_callback(self):
        if self._expression_startswith_operator(self.expression):
            def callback(x):
                ns = {'x': x}
                return eval(f'x {self.expression}', ns)

        else:
            def callback(x):
                return self.expression.lower() in str(x).lower()

        return callback

    def __call__(self, item: Any) -> bool:
        value = self.column.get_value(item)
        return self._evaluate_filter(value)


class TableFilters:
    """ Collection of Filters.
    """
    def __init__(self, filters: List[Filter] = None):
        if filters is None:
            filters = []
        self.filters = filters

    def filter_items(self, items: Iterable) -> Generator:
        for item in items:
            if self.filter(item):
                yield item

    def filter(self, item: Any) -> bool:
        """ Returns True if the given item is included after evaluating all the filters.
        """
        for filter in self.filters:
            if not filter(item):
                return False
        return True

    def add_filter(self, filter: Filter):
        # First we replace any existing filters referencing the same column
        filters = [f for f in self.filters if f.column != filter.column]
        filters.append(filter)
        self.filters = filters

    def get(self, column: Column) -> Optional[Filter]:
        for f in self.filters:
            if f.column == column:
                return f