from operator import itemgetter
from typing import List

import numpy as np
import pandas as pd
from qtpy.QtWidgets import QApplication

from enamlext.qt.qt_table import Column, Alignment, QTable


def generate_columns_for_dataframe(df: pd.DataFrame) -> List[Column]:
    columns = []
    for i, (name, dtype) in enumerate(df.dtypes.items()):
        if np.issubdtype(dtype, np.number):
            align = Alignment.RIGHT
        else:
            align = Alignment.LEFT

        key = itemgetter(i)
        column = Column(key, name, align=align)
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

    display_dataframe(df)
