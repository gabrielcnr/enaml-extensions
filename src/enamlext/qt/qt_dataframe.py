from operator import itemgetter
from typing import List

import numpy as np
import pandas as pd
from qtpy.QtWidgets import QApplication

from enamlext.qt.qtable import QTable, get_cell_style_for_negative_numbers
from enamlext.qt.table.column import Column, Alignment


def generate_columns_for_dataframe(df: pd.DataFrame) -> List[Column]:
    columns = []
    for i, (name, dtype) in enumerate(df.dtypes.items()):
        if not isinstance(dtype, pd.core.dtypes.dtypes.CategoricalDtype) and np.issubdtype(dtype, np.number):
            align = Alignment.RIGHT
            style = get_cell_style_for_negative_numbers
        else:
            align = Alignment.LEFT
            style = None

        key = itemgetter(i)
        column = Column(key, name, align=align, cell_style=style)
        columns.append(column)
    return columns


def display_dataframe(df: pd.DataFrame):
    # Making Ctrl+C work
    import signal

    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # Fixing PyQt issue on MacOS BigSur
    import os

    os.environ["QT_MAC_WANTS_LAYER"] = "1"

    app = QApplication([])

    columns = generate_columns_for_dataframe(df)
    items = df.to_numpy()

    table = QTable(columns, items)
    table.show()

    app.exec_()


if __name__ == '__main__':
    df = pd.DataFrame()

    df["name"] = ["John", "Pam", "Jess"]
    df["age"] = [23, 34, 45]
    df["enabled"] = [True, False, True]
    df["balance"] = [1000, -250.2, 223.45]

    display_dataframe(df)
