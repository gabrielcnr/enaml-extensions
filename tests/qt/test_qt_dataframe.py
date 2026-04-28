import threading

import pandas as pd

from enamlext.qt.qt_dataframe import DataFrameProxy


def test_proxy_has_lock():
    proxy = DataFrameProxy(pd.DataFrame({'a': [1, 2, 3]}))
    assert isinstance(proxy._lock, type(threading.RLock()))


def test_write_runs_callable_under_lock_and_passes_df():
    df = pd.DataFrame({'a': [1, 2, 3]})
    proxy = DataFrameProxy(df)

    seen = []

    def mutate(d):
        seen.append(d)
        d['a'] = [10, 20, 30]

    proxy.write(mutate)

    assert seen == [df]
    assert proxy.df is df
    assert proxy.df['a'].tolist() == [10, 20, 30]


def test_write_lock_is_reentrant():
    # RLock so callers can nest writes (e.g. helper that calls another helper)
    proxy = DataFrameProxy(pd.DataFrame({'a': [1]}))

    def outer(d):
        proxy.write(lambda inner: inner.__setitem__('a', [99]))

    proxy.write(outer)
    assert proxy.df['a'].tolist() == [99]


def test_write_serializes_concurrent_mutations():
    # Two threads hammering write() must not interleave inside fn
    proxy = DataFrameProxy(pd.DataFrame({'a': [0]}))
    inside = 0
    max_inside = 0
    inside_lock = threading.Lock()

    def fn(_d):
        nonlocal inside, max_inside
        with inside_lock:
            inside += 1
            max_inside = max(max_inside, inside)
        # do a touch of work so the race window is real
        for _ in range(1000):
            pass
        with inside_lock:
            inside -= 1

    threads = [threading.Thread(target=lambda: [proxy.write(fn) for _ in range(50)])
               for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert max_inside == 1
