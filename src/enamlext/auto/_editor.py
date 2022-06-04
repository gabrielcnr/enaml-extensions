from atom.api import Atom, Value, Typed
from enaml.widgets.api import Form, Label, DatetimeSelector
from enaml.core.declarative import d_
from enamlext.widgets import Field
import datetime
import enaml
with enaml.imports():
    from enaml.stdlib.fields import IntField


def connect(model, model_attr, view, view_attr):
    assert isinstance(model, Atom)
    assert isinstance(view, Atom)

    model.observe(model_attr,
                  lambda change: setattr(view, view_attr, change['value']))
    view.observe(view_attr,
                 lambda change: setattr(model, model_attr, change['value']))

    # Initially the view should be sync'd with the model
    try:
        setattr(view, view_attr, getattr(model, model_attr))
    except Exception as ex:
        #import pdb ;pdb.set_trace()
        raise


def create_editor(obj, form=None):
    assert isinstance(obj, Atom)

    klass = obj.__class__

    form = form or Form()

    # get the members
    for member_name, member_descriptor in klass.members().iteritems():
        # by default we are skipping members starting with _
        if member_name.startswith('_'):
            continue

        m = member_descriptor.metadata or {}
        if m.get('exclude', False):
            continue

        label_text = m.get('label', member_name)
        label = Label(text=label_text)

        widget = Field()
        model_attr = 'text'
        if isinstance(member_descriptor, Typed):
            type_ = member_descriptor.validate_mode[1]
            if issubclass(type_, datetime.date):
                widget = DatetimeSelector(calendar_popup=True)
                model_attr = 'datetime'
            elif issubclass(type_, int):
                widget = IntField()
                model_attr = 'value'

        form.insert_children(None, [label, widget])

        connect(obj, member_name, widget, model_attr)

    return form


class Editor(Form):
    obj = d_(Value())

    def __init__(self, *args, **kwargs):
        super(Editor, self).__init__(*args, **kwargs)
        create_editor(self.obj, self)
