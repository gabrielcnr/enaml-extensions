from collections import namedtuple
from dataclasses import dataclass

from enamlext.qt.table.column import AUTO_ALIGN, Alignment, Column, generate_columns
from enamlext.qt.table.filtering import Filter, TableFilters
from enamlext.qt.table.summary import TableSelectionSummary, compute_summary


def test_generate_columns_from_list_of_tuples():
    items = [('John', 10), ('Paul', 20)]
    col_1, col_2 = generate_columns(items)

    assert [col_1.title, col_2.title] == ['0', '1']

    assert col_1.align == Alignment.LEFT
    assert col_2.align == Alignment.RIGHT

    assert [col_1.get_value(item) for item in items] == ['John', 'Paul']
    assert [col_2.get_value(item) for item in items] == [10, 20]


def test_generate_columns_from_list_of_dicts():
    items = [{'name': 'George', 'age': 30}, {'name': 'Ringo', 'age': 45}]
    col_1, col_2 = generate_columns(items)

    assert [col_1.title, col_2.title] == ['Name', 'Age']

    assert col_1.align == Alignment.LEFT
    assert col_2.align == Alignment.RIGHT

    assert [col_1.get_value(item) for item in items] == ['George', 'Ringo']
    assert [col_2.get_value(item) for item in items] == [30, 45]


def test_generate_columns_from_list_of_dataclass_instances():
    @dataclass
    class Person:
        name: str
        age: int

    items = [Person(name='Alice', age=6), Person(name='Sophie', age=12)]
    col_1, col_2 = generate_columns(items)

    assert [col_1.title, col_2.title] == ['Name', 'Age']

    assert col_1.align == Alignment.LEFT
    assert col_2.align == Alignment.RIGHT

    assert [col_1.get_value(item) for item in items] == ['Alice', 'Sophie']
    assert [col_2.get_value(item) for item in items] == [6, 12]


def test_generate_columns_from_list_of_namedtuples():
    Person = namedtuple('Person', ['age', 'name'])

    items = [Person(age=66, name='Bob'), Person(age=99, name='Charlie')]
    col_1, col_2 = generate_columns(items)

    assert [col_1.title, col_2.title] == ['Age', 'Name']

    assert col_1.align == Alignment.RIGHT
    assert col_2.align == Alignment.LEFT

    assert [col_1.get_value(item) for item in items] == [66, 99]
    assert [col_2.get_value(item) for item in items] == ['Bob', 'Charlie']


############################
# Filter
############################


def test_filter():
    column = Column('age', use_getitem=True)

    age_filter = Filter(column, '> 25')

    assert age_filter({'age': 30})
    assert not age_filter({'age': 25})
    assert not age_filter({'age': 20})


def test_filter_assumes_equality_by_default():
    column = Column('age', use_getitem=True)

    age_filter = Filter(column, '25')

    assert age_filter({'age': 25})
    assert not age_filter({'age': 30})
    assert not age_filter({'age': 20})


def test_filter_str():
    column_filter = Filter(None, '> 15')
    assert str(column_filter) == '> 15'


def test_filters():
    col_age = Column('age', use_getitem=True)
    col_name = Column('name', use_getitem=True)

    filters = TableFilters(
        [
            Filter(col_age, '> 12'),
            Filter(col_name, 'Leo'),
        ]
    )

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
    expected_summary = TableSelectionSummary(sum=-5, values=values, min=-4, max=2, count_numbers=5)
    assert expected_summary == summary

    assert summary.count == 7
    assert summary.avg == -1


def test_compute_summary_diff():
    values = [-4, 11]
    summary = compute_summary(values)
    expected_summary = TableSelectionSummary(sum=7, values=values, min=-4, max=11, count_numbers=2)
    assert expected_summary == summary

    assert summary.count == 2
    assert summary.avg == 3.5
    assert summary.diff == 15


def test_summary_string_text():
    summary = TableSelectionSummary(sum=5, values=[...] * 7, min=-4.5, max=12.25, count_numbers=4)
    assert str(summary) == 'Count: 7   Average: 1.25   Sum: 5   CountNumbers: 4   Min: -4.5   Max: 12.25'


def test_summary_string_text_with_diff():
    summary = TableSelectionSummary(sum=4, values=[1, 3], min=1, max=3, count_numbers=2)
    assert str(summary) == 'Count: 2   Average: 2.0   Sum: 4   CountNumbers: 2   Min: 1   Max: 3   Diff: 2'


###################################
# Alignment fast-path + memoisation
###################################


def test_get_align_quick_returns_fixed_alignment_without_an_item():
    column = Column('age', use_getitem=True, align=Alignment.RIGHT)
    assert column.get_align_quick() == Alignment.RIGHT


def test_get_align_quick_returns_none_for_unresolved_auto_align():
    column = Column('age', use_getitem=True)
    assert column.align is AUTO_ALIGN
    assert column.get_align_quick() is None


def test_get_align_resolves_auto_align_on_first_non_none_value_and_memoises():
    column = Column('age', use_getitem=True)
    assert column.get_align({'age': 30}) == Alignment.RIGHT
    assert column.get_align_quick() == Alignment.RIGHT
    # Subsequent rows reuse the cached resolution even when their type would
    # have resolved differently in isolation.
    assert column.get_align({'age': 'forty'}) == Alignment.RIGHT


def test_get_align_does_not_memoise_a_none_value():
    column = Column('age', use_getitem=True)
    assert column.get_align({'age': None}) == Alignment.LEFT
    # Cache was not populated by the None row.
    assert column.get_align_quick() is None
    # Next non-None row resolves and caches.
    assert column.get_align({'age': 30}) == Alignment.RIGHT
    assert column.get_align_quick() == Alignment.RIGHT


###################################
# Batched cell refresh
###################################


def test_refresh_cells_groups_by_row_and_emits_one_range_per_row():
    # Simulate enough of QTable.refresh_cells to exercise the grouping
    # logic without requiring a live Qt event loop.
    from enamlext.qt.qtable import QTable

    emits = []

    class FakeIndex:
        def __init__(self, row, col):
            self.row, self.col = row, col

        def __repr__(self):
            return f'({self.row},{self.col})'

    class FakeModel:
        def index(self, row, col):
            return FakeIndex(row, col)

        class _Sig:
            def __init__(self, sink):
                self.sink = sink

            def emit(self, top_left, bottom_right):
                self.sink.append(((top_left.row, top_left.col), (bottom_right.row, bottom_right.col)))

        def __init__(self, sink):
            self.dataChanged = self._Sig(sink)

    fake_model = FakeModel(emits)

    class _T:
        def model(self):
            return fake_model

    # Same-row clustered: cols 1, 3, 5 in row 7 collapse to one range (7,1)→(7,5)
    QTable.refresh_cells(_T(), [7, 7, 7], [1, 3, 5])
    # Two rows: emits one range each
    QTable.refresh_cells(_T(), [2, 2, 9], [4, 6, 1])

    assert emits == [
        ((7, 1), (7, 5)),
        ((2, 4), (2, 6)),
        ((9, 1), (9, 1)),
    ]


def test_refresh_cells_no_op_on_empty_input():
    from enamlext.qt.qtable import QTable

    emits = []

    class _T:
        def model(self):
            class M:
                class S:
                    def emit(self, *a):
                        emits.append(a)

                dataChanged = S()

            return M()

    QTable.refresh_cells(_T(), [], [])
    assert emits == []


def test_debug_trace_hands_the_current_frame_to_pdb(mocker):
    from enamlext.qt.qtable import debug_trace

    interaction = mocker.patch('pdb.Pdb.interaction')
    mocker.patch('pdb.Pdb.do_next')

    def caller():
        debug_trace()

    caller()

    frame = interaction.call_args.args[0]
    assert frame.f_code.co_name == 'caller'


def test_summary_constructors_return_the_subclass_they_are_called_on():
    class LabelledSummary(TableSelectionSummary):
        pass

    class FakeSelection:
        selected_values = (((0, 0), 4), ((0, 1), 'x'), ((1, 0), 10))

    from_values = LabelledSummary.from_values([4, 'x', 10])
    from_selection = LabelledSummary.from_selection_context(FakeSelection())

    assert type(from_values) is LabelledSummary
    assert type(from_selection) is LabelledSummary
    assert (from_selection.sum, from_selection.count_numbers, from_selection.min, from_selection.max) == (14, 2, 4, 10)
