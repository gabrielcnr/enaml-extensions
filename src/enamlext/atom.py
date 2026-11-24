import functools
import threading
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, ClassVar

from atom.api import Atom as BaseAtom
from enaml.application import Application, deferred_call

if TYPE_CHECKING:
    from enamlext.qt.qt_main_thread import MainThreadCaller

# Re-entrant: a finalizer run by the garbage collector while the lock is held may set again.
_pending_lock = threading.RLock()
# Holding obj here keeps its id from being reused while its set is queued.
_pending: dict[tuple[int, str], tuple[Any, Any]] = {}
# Keys stored without an apply posted yet. More than one only when a finalizer sets while a set
# on the same thread is still posting its apply; that set then posts for all of them.
_unposted: list[tuple[int, str]] = []
# Keys whose queued value the main thread is setting right now, innermost last.
_applying: list[tuple[int, str]] = []


class _ThreadState(threading.local):
    def __init__(self) -> None:
        self.gui_thread: tuple[Application, bool] | None = None
        self.under_construction: set[int] = set()


_thread_state = _ThreadState()


class Atom(BaseAtom):
    """
    Atom whose members tagged with conflate=True can be assigned from any thread.

        class Model(Atom):
            frame = Typed(pd.DataFrame).tag(conflate=True)

    On the main thread, before an Application exists, or while the object is being
    constructed or unpickled, the assignment sets the member at once. From any other thread
    it is queued for the main thread and only the latest value is applied (see
    conflated_setattr). Until then that thread reads back the old value, and an invalid
    value raises on the main thread instead of at the assignment.

    A conflated member is applied at the position of its first queued assignment, so it can
    reach the main thread before other members that were set earlier. Assign it directly:
    wrapping the set in deferred_call can apply an older value over a newer one.
    """

    _conflated_members: ClassVar[frozenset[str]] = frozenset()

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        cls._conflated_members = frozenset(
            name for name, member in cls.members().items() if member.metadata and member.metadata.get('conflate')
        )
        inherited = cls.__setattr__
        plain_setattr = getattr(inherited, 'plain_setattr', inherited)
        if cls._conflated_members:
            cls.__setattr__ = _conflating_setattr(cls._conflated_members, plain_setattr)  # type: ignore[method-assign]
            for constructing in ('__init__', '__setstate__'):
                method = getattr(cls, constructing)
                if not hasattr(method, 'sets_members_directly'):
                    setattr(cls, constructing, _setting_members_directly(method))
        elif inherited is not plain_setattr:
            cls.__setattr__ = plain_setattr  # type: ignore[method-assign]

    def safe_set(self, attr, value):
        app = Application.instance()
        if app is None or app.is_main_thread() or attr in self._conflated_members:
            setattr(self, attr, value)
        else:
            deferred_call(setattr, self, attr, value)


def _conflating_setattr(
    conflated: frozenset[str], plain_setattr: Callable[[Any, str, Any], None]
) -> Callable[[Any, str, Any], None]:
    def conflating_setattr(self: Any, name: str, value: Any) -> None:
        if name in conflated and id(self) not in _thread_state.under_construction:
            app = Application.instance()
            if app is not None:
                if not _is_gui_thread(app):
                    conflated_setattr(self, name, value)
                    return
                if _pending:
                    _discard_older_queued_value(self, name)
        plain_setattr(self, name, value)

    conflating_setattr.plain_setattr = plain_setattr  # type: ignore[attr-defined]
    return conflating_setattr


def _setting_members_directly(method: Callable[..., Any]) -> Callable[..., Any]:
    # An object built or unpickled on a worker is not shared yet, and its creator expects to
    # read back what it passed in, so its members are set at once instead of being queued.
    @functools.wraps(method)
    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        under_construction = _thread_state.under_construction
        key = id(self)
        if key in under_construction:
            return method(self, *args, **kwargs)
        under_construction.add(key)
        try:
            return method(self, *args, **kwargs)
        finally:
            under_construction.discard(key)

    wrapper.sets_members_directly = True  # type: ignore[attr-defined]
    return wrapper


def _is_gui_thread(app: Application) -> bool:
    # Cached per thread: app.is_main_thread() takes longer than the rest of a conflated set.
    cached = _thread_state.gui_thread
    if cached is None or cached[0] is not app:
        cached = _thread_state.gui_thread = (app, app.is_main_thread())
    return cached[1]


def _discard_older_queued_value(obj: Any, name: str) -> None:
    key = (id(obj), name)
    # The value being applied is the queued one, and a newer one may already be waiting.
    if _applying and _applying[-1] == key:
        return
    with _pending_lock:
        _pending.pop(key, None)


def conflated_setattr(obj: Any, name: str, value: Any) -> None:
    """
    Set ``obj.<name> = value`` on the main thread, keeping only the latest value.

    Safe to call from any thread. While a set for the same object and member is still
    queued, further calls just replace its value, so a burst of updates costs one
    setattr on the main thread instead of one per update.

    Raises RuntimeError if there is no QApplication.
    """
    key = (id(obj), name)
    entry = (obj, value)
    with _pending_lock:
        replaced = _pending.get(key)
        _pending[key] = entry
        if replaced is None:
            _unposted.append(key)
            if len(_unposted) == 1:
                _post_applies()


def _post_applies() -> None:
    try:
        caller = _main_thread_caller()
        while _unposted:
            # The apply carries only the key and reads the latest value when it runs, so one
            # per key is enough.
            caller.post(_apply_pending, _unposted[0])
            del _unposted[0]
    except BaseException:
        # A key left behind would make later sets wait for an apply that was never queued.
        while _unposted:
            _pending.pop(_unposted.pop(), None)
        raise


def _apply_pending(key: tuple[int, str]) -> None:
    # Popping under the lock means a set arriving after this finds no key and queues afresh.
    with _pending_lock:
        entry = _pending.pop(key, None)
    if entry is not None:
        obj, value = entry
        _applying.append(key)
        try:
            setattr(obj, key[1], value)
        finally:
            _applying.pop()


# enaml's deferred_call creates its receiver lazily without a lock: when several threads make
# the first calls, all but one receiver is dropped with its events. A lost apply would leave
# its key pending for good, so applies go through a receiver created under _pending_lock.
@functools.cache
def _main_thread_caller() -> 'MainThreadCaller':
    # Imported on first use: enamlext.atom must stay importable without a Qt binding.
    from enamlext.qt.qt_main_thread import MainThreadCaller

    return MainThreadCaller(on_application_destroyed=_forget_queued_applies)


def _forget_queued_applies() -> None:
    with _pending_lock:
        _main_thread_caller.cache_clear()
        _pending.clear()


def on_thread(func):
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        thread = threading.Thread(target=func, args=args, kwargs=kwargs, daemon=True)
        thread.daemon = True
        thread.start()

    return wrapped
