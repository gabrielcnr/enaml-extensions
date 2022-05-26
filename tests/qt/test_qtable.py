from collections import namedtuple
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from numbers import Number
from operator import itemgetter

from enamlext.qt.qtable import Column, Alignment, AUTO_ALIGN


def make_title(title: str):
    return title.replace('_', ' ').title()


def is_namedtuple(obj):
    return isinstance(obj, tuple) and hasattr((T := type(obj)), '_fields') and hasattr(T, '_asdict')


def generate_columns(items: Sequence):
    first_row = items[0]
    columns = []
    if isinstance(first_row, tuple):
        if is_namedtuple(first_row):
            fields = type(first_row)._fields
        else:
            fields = None
        for i, value in enumerate(first_row):
            kwargs = {}
            if isinstance(value, Number):
                kwargs['align'] = Alignment.RIGHT
            if fields is not None:
                title = make_title(fields[i])
            else:
                title = str(i)
            column = Column(itemgetter(i), title, **kwargs)
            columns.append(column)

    elif isinstance(first_row, Mapping):
        for key, value in first_row.items():
            if isinstance(key, str):
                title = make_title(key)
            else:
                title = str(key)

            kwargs = {}
            if isinstance(value, Number):
                kwargs['align'] = Alignment.RIGHT

            column = Column(itemgetter(key), title, **kwargs)
            columns.append(column)

    elif hasattr(type(first_row), '__dataclass_fields__'):
        fields = type(first_row).__dataclass_fields__
        for field in fields:
            value = getattr(first_row, field)
            title = make_title(field)
            kwargs = {}
            if isinstance(value, Number):
                kwargs['align'] = Alignment.RIGHT

            column = Column(field, title, **kwargs)
            columns.append(column)

    return columns


def test_generate_columns_from_list_of_tuples():
    items = [('John', 10), ('Paul', 20)]
    col_1, col_2 = generate_columns(items)

    assert ['0', '1'] == [col_1.title, col_2.title]

    assert col_1.align == AUTO_ALIGN
    assert col_2.align == Alignment.RIGHT

    assert ['John', 'Paul'] == [col_1.get_value(item) for item in items]
    assert [10, 20] == [col_2.get_value(item) for item in items]


def test_generate_columns_from_list_of_dicts():
    items = [{'name': 'George', 'age': 30}, {'name': 'Ringo', 'age': 45}]
    col_1, col_2 = generate_columns(items)

    assert ['Name', 'Age'] == [col_1.title, col_2.title]

    assert col_1.align == AUTO_ALIGN
    assert col_2.align == Alignment.RIGHT

    assert ['George', 'Ringo'] == [col_1.get_value(item) for item in items]
    assert [30, 45] == [col_2.get_value(item) for item in items]


def test_generate_columns_from_list_of_dataclass_instances():
    @dataclass
    class Person:
        name: str
        age: int

    items = [Person(name='Alice', age=6), Person(name='Sophie', age=12)]
    col_1, col_2 = generate_columns(items)

    assert ['Name', 'Age'] == [col_1.title, col_2.title]

    assert col_1.align == AUTO_ALIGN
    assert col_2.align == Alignment.RIGHT

    assert ['Alice', 'Sophie'] == [col_1.get_value(item) for item in items]
    assert [6, 12] == [col_2.get_value(item) for item in items]


def test_generate_columns_from_list_of_namedtuples():
    Person = namedtuple('Person', ['age', 'name'])

    items = [Person(age=66, name='Bob'), Person(age=99, name='Charlie')]
    col_1, col_2 = generate_columns(items)

    assert ['Age', 'Name'] == [col_1.title, col_2.title]

    assert col_1.align == Alignment.RIGHT
    assert col_2.align == AUTO_ALIGN

    assert [66, 99] == [col_1.get_value(item) for item in items]
    assert ['Bob', 'Charlie'] == [col_2.get_value(item) for item in items]
