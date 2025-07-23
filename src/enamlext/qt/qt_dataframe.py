import logging
import threading
from typing import Callable

import pandas as pd


logger = logging.getLogger(__name__)


def _monitor_df_changes(df_proxy):
    logger.debug('Starting DataFrameProxy thread for monitoring changes and refreshing ticking cells '
                 f'{threading.current_thread()}')

    import time
    import numpy as np
    from enaml.application import deferred_call

    current_values = df_proxy.values
    interval = df_proxy.tick_interval_ms / 1_000

    while df_proxy.is_active():
        time.sleep(interval)
        t0 = time.perf_counter()
        new_values = df_proxy.df.values.copy()

        # row_indexes, col_indexes = np.where(current_values != new_values)
        # ~
        row_indexes, col_indexes = np.where(~((current_values == new_values) | (pd.isna(current_values) & pd.isna(new_values))))

        if len(row_indexes):
            deferred_call(df_proxy.update_values_and_refresh_cells, new_values, row_indexes, col_indexes)
        current_values = new_values
        t1 = time.perf_counter()
        logger.info(f'It took {t1 -t0:.3f} s inside the thread')

    logger.info(f'Thread died: DataFrameProxy ticking monitor {threading.current_thread()}')


class DataFrameProxy:
    def __init__(self,
                 df: pd.DataFrame,
                 *,
                 tick_interval_ms: int = 0,
                 refresh_cells_callback: Callable[[list, list], None] | None = None):
        if tick_interval_ms > 0 and refresh_cells_callback is None:
            raise ValueError('You must pass a callback to handle refreshing cells when you pass '
                             'a tick_interval_ms > 0.')
        if tick_interval_ms <= 0 and refresh_cells_callback is not None:
            raise ValueError('You should specify a tick_interval_ms refresh interval in miliseconds when you '
                             'pass a refresh_cells_callback.')
        self.values = df.values
        self.df = df
        self.tick_interval_ms = tick_interval_ms
        self.refresh_cells_callback = refresh_cells_callback
        self._is_active = True
        if self.is_ticking:
            import threading
            t = threading.Thread(target=_monitor_df_changes,
                                 args=(self,),
                                 daemon=True)
            t.start()

    def update_values_and_refresh_cells(self, new_values, row_indexes, col_indexes):
        # must be called in the main thread!
        t0 = time.perf_counter()
        self.values = new_values
        self.refresh_cells_callback(row_indexes, col_indexes)
        changed_col_names = {i: self.df.columns[i] for i in set(col_indexes)}
        logger.info(f'It took {time.perf_counter() - t0:.3f} s inside the main thread refreshing {len(row_indexes)} cells - modified cols: {changed_col_names}')

    @property
    def is_ticking(self):
        return self.tick_interval_ms > 0

    def deactivate(self):
        self._is_active = False

    def is_active(self):
        return self._is_active

    def __getitem__(self, item):
        return self.values[item]

    def __len__(self):
        return len(self.values)
