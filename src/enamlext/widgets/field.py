from enaml.widgets.api import Field as _Field
from atom.api import Enum, List
from enaml.core.declarative import d_


class Field(_Field):
    submit_triggers = d_(List(
        Enum('lost_focus', 'return_pressed', 'auto_sync'),
        ['lost_focus', 'return_pressed', 'auto_sync']
    ))
