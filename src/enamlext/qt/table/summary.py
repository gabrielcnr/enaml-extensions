from dataclasses import dataclass
from typing import Optional

from enamlext.qt.qtable import SelectionContext


@dataclass
class TableSelectionSummary:
    sum: float
    count_numbers: int
    min: float
    max: float
    values: list

    @classmethod
    def from_selection_context(cls, selection_context: SelectionContext) -> "TableSelectionSummary":
        return compute_summary([v for _, v in selection_context.selected_values])

    @property
    def count(self) -> int:
        return len(self.values)

    @property
    def avg(self) -> Optional[float]:
        if self.count_numbers:
            return self.sum / self.count_numbers

    @property
    def diff(self) -> Optional[float]:
        """ Returns the absolute difference/distance between 2 selected numbers
        when all is selected are those 2 numbers and nothing else.
        """
        if self.count == self.count_numbers == 2:
            v1, v2 = self.values
            return abs(v1 - v2)

    def __str__(self) -> str:
        parts = [f'Count: {self.count}']
        if self.count_numbers:
            parts += [
                f'Average: {self.avg}',
                f'Sum: {self.sum}',
                f'CountNumbers: {self.count_numbers}',
                f'Min: {self.min}',
                f'Max: {self.max}',
            ]
        if (diff := self.diff) is not None:
            parts.append(f'Diff: {diff}')

        return '   '.join(parts)


# TODO: Qt selection model has a better/more clever way to compute the summary
#       based on what's been deselected and selected since "last time"
def compute_summary(selected_values: list) -> TableSelectionSummary:
    sum_ = 0.0
    count_numbers = 0
    min_value = float('inf')
    max_value = -float('inf')

    for value in selected_values:
        try:
            sum_ += value
        except TypeError:
            pass
        else:
            count_numbers += 1
            min_value = min(min_value, value)
            max_value = max(max_value, value)

    return TableSelectionSummary(sum=sum_, count_numbers=count_numbers,
                                 min=min_value, max=max_value, values=selected_values)