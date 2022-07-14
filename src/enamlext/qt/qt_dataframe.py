import pandas as pd
from qtpy.QtWidgets import QApplication


class DataFrameProxy:
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.__d = self.df.to_dict('records')

    def __getitem__(self, item):
        return self.__d[item]

    def __len__(self):
        return len(self.df)

    def update_inplace(self) -> None:
        self.__d[:] = self.df.to_dict('records')


def _display_dataframe(df: pd.DataFrame):
    from enamlext.qt.qtable import QTable
    from enamlext.qt.table.column import generate_columns

    # Making Ctrl+C work
    import signal

    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # Fixing PyQt issue on MacOS BigSur
    import os

    os.environ["QT_MAC_WANTS_LAYER"] = "1"

    app = QApplication([])

    items = DataFrameProxy(df)
    columns = generate_columns(items)

    table = QTable(columns, items)
    table.show()

    app.exec_()


if __name__ == '__main__':
    df = pd.DataFrame()

    df["name"] = ["John", "Pam", "Jess"]
    df["age"] = [23, 34, 45]
    df["enabled"] = [True, False, True]
    df["balance"] = [1000, -250.2, 223.45]

    _display_dataframe(df)
