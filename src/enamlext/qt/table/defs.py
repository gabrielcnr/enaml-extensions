from enum import Enum
from typing import TypedDict, Optional, Callable

from PyQt5.QtGui import QColor


class CellStyle(TypedDict, total=False):
    color: Optional[QColor]
    background: Optional[QColor]


CellStyleCallback = Callable[['TableContext'], CellStyle]


class ColumnSize(str, Enum):
    AUTO = 'auto'
    JUST = 'just'  # based on the font metrics of the table view
