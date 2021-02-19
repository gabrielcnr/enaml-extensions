import functools
import threading

from atom.api import Atom as BaseAtom
from enaml.application import deferred_call, Application


class Atom(BaseAtom):

    def safe_set(self, attr, value):
        app = Application.instance()
        if app is None or app.is_main_thread():
            setattr(self, attr, value)
        else:
            deferred_call(setattr, self, attr, value)


def on_thread(func):
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        thread = threading.Thread(target=func,
                                  args=args,
                                  kwargs=kwargs,
                                  daemon=True)
        thread.daemon = True
        thread.start()

    return wrapped
