from atom.api import Atom, Unicode
from enaml.widgets.api import Field

from enamlext.auto import create_editor
from enamlext.auto._editor import connect


class Person(Atom):
    name = Unicode()


def test_simple_editor():
    person = Person()
    editor = create_editor(person)

    assert 2 == len(editor.children)


def test_exclude():
    class Person2(Atom):
        name = Unicode().tag(exclude=True)

    person = Person2()
    editor = create_editor(person)

    assert 0 == len(editor.children)


def test_connect():
    person = Person()
    field = Field()
    connect(person, 'name', field, 'text')

    assert field.text == ''
    assert person.name == ''

    # Update the model causes the view to update
    person.name = 'John'
    assert field.text == 'John'

    # Update the view causes the model to update
    field.text = 'Paul'
    assert person.name == 'Paul'


def test_initial_sync():
    person = Person(name='George')
    editor = create_editor(person)

    _, field = editor.children

    assert field.text == 'George'


def test_label():
    class Person2(Atom):
        name = Unicode().tag(label='Full Name')

    p = Person2()
    editor = create_editor(p)

    label, _ = editor.children
    assert label.text == 'Full Name'
