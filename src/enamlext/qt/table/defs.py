from typing import TypedDict, Optional

from PyQt5.QtGui import QColor


class CellStyle(TypedDict, total=False):
    color: Optional[QColor]
    background: Optional[QColor]
