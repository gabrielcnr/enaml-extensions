from atom.api import Atom, Value
from enaml.widgets.api import Form, Label
from enaml.core.declarative import d_
from enamlext.widgets import Field


def connect(model, model_attr, view, view_attr):
    assert isinstance(model, Atom)
    assert isinstance(view, Atom)

    model.observe(model_attr,
                  lambda change: setattr(view, view_attr, change['value']))
    view.observe(view_attr,
                 lambda change: setattr(model, model_attr, change['value']))

    # Initially the view should be sync'd with the model
    setattr(view, view_attr, getattr(model, model_attr))


def create_editor(obj, form=None):
    assert isinstance(obj, Atom)

    klass = obj.__class__

    form = form or Form()

    # get the members
    for member_name, member_descriptor in klass.members().iteritems():
        m = member_descriptor.metadata or {}
        if m.get('exclude', False):
            continue

        label_text = m.get('label', member_name)
        label = Label(text=label_text)

        field = Field()
        form.insert_children(None, [label, field])

        connect(obj, member_name, field, 'text')

    return form


class Editor(Form):
    obj = d_(Value())

    def __init__(self, *args, **kwargs):
        super(Editor, self).__init__(*args, **kwargs)
        create_editor(self.obj, self)
