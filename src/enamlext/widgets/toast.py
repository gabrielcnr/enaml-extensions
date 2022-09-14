import enaml

with enaml.imports():
    from ark.live.components.ui.views.notifications import COLOR_SCHEMES, NotificationPopup
import textwrap

from enaml.application import deferred_call
from functools import partialmethod


class Notifications:
    _default_header = ''

    @classmethod
    def set_default_header(cls, header):
        cls._default_header = header

    @classmethod
    def show(cls, kind, title, message, header=None, timeout=5):
        header = header or cls._default_header
        bgcolor, fgcolor = COLOR_SCHEMES[kind].values()
        message = '\n'.join(textwrap.wrap(message, width=80, replace_whitespace=False))

        def defer_show():
            NotificationPopup(background=bgcolor, foreground=fgcolor, timeout=timeout,
                              header=header, title=title, text=message).show()

        deferred_call(defer_show)

    info = partialmethod(show, 'INFO')
    debug = partialmethod(show, 'DEBUG')
    neutral = partialmethod(show, 'NEUTRAL')
    warning = partialmethod(show, 'WARNING')
    success = partialmethod(show, 'SUCCESS')
    error = critical = partialmethod(show, 'CRITICAL')

