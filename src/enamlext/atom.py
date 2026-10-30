import functools
import threading
from typing import Any

from atom.api import Atom as BaseAtom
from enaml.application import Application, deferred_call

_pending_lock = threading.Lock()
# Holding obj here keeps its id from being reused while its set is queued.
_pending: dict[tuple[int, str], tuple[Any, Any]] = {}


class Atom(BaseAtom):
    def safe_set(self, attr, value):
        app = Application.instance()
        if app is None or app.is_main_thread():
            setattr(self, attr, value)
        else:
            deferred_call(setattr, self, attr, value)


def conflated_setattr(obj: Any, name: str, value: Any) -> None:
    """
    Set ``obj.<name> = value`` on the main thread, keeping only the latest value.

    Safe to call from any thread. While a set for the same object and member is still
    queued, further calls just replace its value, so a burst of updates costs one
    setattr on the main thread instead of one per update.
    """
    key = (id(obj), name)
    with _pending_lock:
        apply_queued = key in _pending
        _pending[key] = (obj, value)
    # A queued _apply_pending carries only the key and reads _pending when it runs, so it
    # picks up any value set while it waits; queueing another would apply that value twice.
    if not apply_queued:
        deferred_call(_apply_pending, key)


def _apply_pending(key: tuple[int, str]) -> None:
    # Popping under the lock means a set arriving after this finds no key and queues afresh.
    with _pending_lock:
        obj, value = _pending.pop(key)
    setattr(obj, key[1], value)


def on_thread(func):
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        thread = threading.Thread(target=func, args=args, kwargs=kwargs, daemon=True)
        thread.daemon = True
        thread.start()

    return wrapped
