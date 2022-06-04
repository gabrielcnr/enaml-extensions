from collections import namedtuple
from dataclasses import dataclass

from enamlext.qt.table.summary import TableSelectionSummary, compute_summary
from enamlext.qt.table.column import Column, Alignment, AUTO_ALIGN, generate_columns
from enamlext.qt.table.filtering import TableFilters, Filter


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


############################
# Filter
############################


def test_filter():
    column = Column('age', use_getitem=True)

    filter = Filter(column, '> 25')

    assert filter({'age': 30})
    assert not filter({'age': 25})
    assert not filter({'age': 20})


def test_filter_assumes_equality_by_default():
    column = Column('age', use_getitem=True)

    filter = Filter(column, '25')

    assert filter({'age': 25})
    assert not filter({'age': 30})
    assert not filter({'age': 20})


def test_filter_str():
    filter = Filter(None, '> 15')
    assert str(filter) == '> 15'


def test_filters():
    col_age = Column('age', use_getitem=True)
    col_name = Column('name', use_getitem=True)

    filters = TableFilters([
        Filter(col_age, '> 12'),
        Filter(col_name, 'Leo'),
    ])

    items = [
        {'name': 'Leo', 'age': 13},
        {'name': 'Leo', 'age': 11},
        {'name': 'Leo', 'age': 18},
        {'name': 'Joe', 'age': 11},
        {'name': 'Joe', 'age': 14},
        {'name': 'Joe', 'age': 20},
        {'name': 'Leo', 'age': 19},
    ]

    expected = [
        {'name': 'Leo', 'age': 13},
        {'name': 'Leo', 'age': 18},
        {'name': 'Leo', 'age': 19},
    ]

    assert expected == list(filters.filter_items(items))


def test_get_filter_for_column():
    col_1 = Column('a')
    col_2 = Column('b')

    filters = TableFilters([Filter(col_1, '> 10'), Filter(col_2, '<= 12')])

    assert str(filters.get(col_1)) == '> 10'
    assert str(filters.get(col_2)) == '<= 12'


###########
# Summary
###########

def test_compute_summary():
    values = [1, 2, 'foo', 'bar', -3, -4, -1]
    summary = compute_summary(values)
    expected_summary = TableSelectionSummary(sum=-5, values=values, min=-4, max=2,
                                             count_numbers=5)
    assert expected_summary == summary

    assert 7 == summary.count
    assert -1 == summary.avg


def test_compute_summary_diff():
    values = [-4, 11]
    summary = compute_summary(values)
    expected_summary = TableSelectionSummary(sum=7, values=values, min=-4, max=11,
                                             count_numbers=2)
    assert expected_summary == summary

    assert 2 == summary.count
    assert 3.5 == summary.avg
    assert 15 == summary.diff


def test_summary_string_text():
    summary = TableSelectionSummary(sum=5, values=[...] * 7, min=-4.5, max=12.25, count_numbers=4)
    assert 'Count: 7   Average: 1.25   Sum: 5   CountNumbers: 4   Min: -4.5   Max: 12.25' == str(summary)


def test_summary_string_text_with_diff():
    summary = TableSelectionSummary(sum=4, values=[1, 3], min=1, max=3, count_numbers=2)
    assert 'Count: 2   Average: 2.0   Sum: 4   CountNumbers: 2   Min: 1   Max: 3   Diff: 2' == str(summary)
