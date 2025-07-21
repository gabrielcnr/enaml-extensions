from typing import Callable

import pandas as pd
from qtpy.QtWidgets import QApplication


def _monitor_df_changes(df_proxy):
    current_values = df_proxy.values
    interval = df_proxy.tick_interval_ms / 1_000

    import time
    import numpy as np
    from enaml.application import deferred_call

    # print('starting monitor thread')
    while df_proxy.is_active():
        time.sleep(interval)
        new_values = df_proxy.df.values.copy()
        row_indexes, col_indexes = np.where(current_values != new_values)
        if len(row_indexes):
            deferred_call(df_proxy.update_values_and_refresh_cells, new_values, row_indexes, col_indexes)
        current_values = new_values
    # print('thread died')


class DataFrameProxy:
    def __init__(self, df: pd.DataFrame, is_ticking: bool,
                 tick_interval_ms: int,
                 refresh_cells_callback: Callable[[list, list], None]):
        self.values = df.values
        self.df = df
        self.is_ticking = is_ticking
        self.tick_interval_ms = tick_interval_ms
        self.refresh_cells_callback = refresh_cells_callback
        self._is_active = True
        if is_ticking:
            import threading
            t = threading.Thread(target=_monitor_df_changes,
                                 args=(self,),
                                 daemon=True)
            t.start()

    def update_values_and_refresh_cells(self, new_values, row_indexes, col_indexes):
        # must be called in the main thread!
        self.values = new_values
        self.refresh_cells_callback(row_indexes, col_indexes)

    def deactivate(self):
        self._is_active = False

    def is_active(self):
        return self._is_active

    def __getitem__(self, item):
        return self.values[item]

    def __len__(self):
        return len(self.values)


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
