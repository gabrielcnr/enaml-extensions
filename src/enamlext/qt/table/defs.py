from collections.abc import Callable
from enum import Enum
from typing import TYPE_CHECKING, TypedDict

from qtpy.QtGui import QColor

if TYPE_CHECKING:
    from enamlext.qt.table.table_context import TableContext


class CellStyle(TypedDict, total=False):
    color: QColor | None
    background: QColor | None
    font: str | None
    border: QColor | None


CellStyleCallback = Callable[['TableContext'], CellStyle]


class ColumnSize(str, Enum):
    AUTO = 'auto'
    JUST = 'just'  # based on the font metrics of the table view
