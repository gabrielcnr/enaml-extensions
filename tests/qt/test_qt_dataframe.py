import threading
import time

import numpy as np
import pandas as pd

from enamlext.qt.qt_dataframe import DataFrameProxy


def test_monitor_never_snapshots_a_mutation_in_progress_under_the_proxy_lock(enaml_app, qtbot):
    n = 100
    df = pd.DataFrame({'a': np.zeros(n), 'b': np.zeros(n), 'obj': [object() for _ in range(n)]})
    snapshots = []
    proxy = DataFrameProxy(
        df, tick_interval_ms=10, refresh_cells_callback=lambda rows, cols: snapshots.append(proxy.values)
    )

    def update_a_then_b():
        with proxy.lock:
            df.update(pd.DataFrame({'a': np.ones(n)}))
            time.sleep(0.2)  # spans many ticks, so an unsynchronised monitor would snapshot here
            df.update(pd.DataFrame({'b': np.ones(n)}))

    writer = threading.Thread(target=update_a_then_b)
    writer.start()
    try:
        qtbot.waitUntil(lambda: bool(snapshots) and (snapshots[-1][:, 1] == 1).all(), timeout=2000)
    finally:
        writer.join()
        proxy.deactivate()

    for snapshot in snapshots:
        assert (snapshot[:, 0] == snapshot[:, 1]).all()
