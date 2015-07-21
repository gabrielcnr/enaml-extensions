from atom.api import Atom
from enaml.widgets.api import Form, Label, Field


def connect(model, model_attr, view, view_attr):
    assert isinstance(model, Atom)
    assert isinstance(view, Atom)

    model.observe(model_attr,
                  lambda change: setattr(view, view_attr, change['value']))
    view.observe(view_attr,
                 lambda change: setattr(model, model_attr, change['value']))

    # Initially the view should be sync'd with the model
    setattr(view, view_attr, getattr(model, model_attr))


def create_editor(obj):
    assert isinstance(obj, Atom)
    klass = obj.__class__

    form = Form()

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
