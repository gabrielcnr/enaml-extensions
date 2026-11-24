import pytest
from atom.api import Atom, Bool, Float, Int, Str
from enaml.widgets.api import Field

from enamlext.auto import create_editor
from enamlext.auto._editor import Editor, connect


class Person(Atom):
    name = Str()


def test_simple_editor():
    person = Person()
    editor = create_editor(person)

    assert len(editor.children) == 2


def test_exclude():
    class Person2(Atom):
        name = Str().tag(exclude=True)

    person = Person2()
    editor = create_editor(person)

    assert len(editor.children) == 0


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
        name = Str().tag(label='Full Name')

    p = Person2()
    editor = create_editor(p)

    label, _ = editor.children
    assert label.text == 'Full Name'


def test_create_editor_control():
    person = Person(name='George')
    editor = Editor(obj=person)
    assert editor.obj is person
    assert len(editor.children) == 2


@pytest.mark.parametrize(
    ('member', 'shown', 'typed', 'value'),
    [(Int(3), '3', '42', 42), (Float(1.5), '1.5', '2.25', 2.25)],
)
def test_number_member_is_edited_as_a_number(member, shown, typed, value):
    class Order(Atom):
        amount = member

    order = Order()
    _, field = create_editor(order).children
    assert field.text == shown

    field.text = typed
    assert order.amount == value

    order.amount = 7
    assert float(field.text) == 7


def test_bool_member_is_edited_with_a_check_box():
    class Order(Atom):
        filled = Bool(True)

    order = Order()
    _, check_box = create_editor(order).children
    assert check_box.checked

    check_box.checked = False
    assert not order.filled

    order.filled = True
    assert check_box.checked
