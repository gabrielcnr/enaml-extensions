from collections.abc import Callable
from typing import Any

from qtpy.QtCore import QCoreApplication, QEvent, QObject, Qt

_CALL_EVENT_TYPE = QEvent.Type(QEvent.registerEventType())


class _CallEvent(QEvent):
    def __init__(self, callback: Callable[..., Any], args: tuple[Any, ...]) -> None:
        super().__init__(_CALL_EVENT_TYPE)
        self.callback = callback
        self.args = args


class MainThreadCaller(QObject):
    """
    Runs callbacks on the QApplication's thread. Can be created and used from any thread.

    Calls still queued when the QApplication is destroyed never run;
    on_application_destroyed is then called, on the thread destroying it.
    """

    def __init__(self, on_application_destroyed: Callable[[], None]) -> None:
        super().__init__()
        qapp: QCoreApplication | None = QCoreApplication.instance()
        if qapp is None:
            raise RuntimeError('QApplication instance does not exist')
        self.moveToThread(qapp.thread())
        # Direct: a queued connection would wait for an event loop on the connecting thread,
        # and a worker thread may never run one.
        # Any: the stubs of PyQt6 6.11 do not declare connect()'s connection type.
        destroyed: Any = qapp.destroyed
        destroyed.connect(lambda *_: on_application_destroyed(), Qt.ConnectionType.DirectConnection)

    def post(self, callback: Callable[..., Any], *args: Any) -> None:
        QCoreApplication.postEvent(self, _CallEvent(callback, args))

    def customEvent(self, event: QEvent | None) -> None:
        if isinstance(event, _CallEvent):
            event.callback(*event.args)
