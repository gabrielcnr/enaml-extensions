from collections import namedtuple
from dataclasses import dataclass
from decimal import Decimal
from types import SimpleNamespace

import pandas as pd
import pytest

from enamlext.qt.qt_dataframe import DataFrameProxy
from enamlext.qt.qtable import Qt, QTable
from enamlext.qt.table.column import (
    NEGATIVE_NUMBER_CELL_STYLE,
    Alignment,
    Column,
    generate_columns,
    get_cell_style_for_negative_numbers,
)


def test_get_displayed_value():
    class Foo:
        def __str__(self) -> str:
            return 'string for Foo'

        def __format__(self, spec: str) -> str:
            s = str(self)
            return s.upper() if spec == 'u' else format(s, spec)

    foo = Foo()

    item = {'foo': foo}

    column = Column('foo', use_getitem=True)

    assert foo is column.get_value(item)
    assert column.get_displayed_value(item) == 'string for Foo'

    column2 = Column('foo', use_getitem=True, fmt='u')
    assert column2.get_displayed_value(item) == 'STRING FOR FOO'


def test_giving_fmt_as_callback():
    def uppercase_mirrored(value):
        return str(value)[::-1].upper()

    class InterestingClass:
        def __str__(self):
            return 'TextForUsers'

    obj = InterestingClass()
    item = {'obj': obj, 'foo': None}

    column = Column('obj', fmt=uppercase_mirrored, use_getitem=True)

    assert column.get_displayed_value(item) == 'SRESUROFTXET'


def test_generate_columns_with_hints():
    @dataclass
    class Trade:
        symbol: str
        price: Decimal
        quantity: int

    items = [
        Trade(symbol='FOO', price=15.2, quantity=500),
        t2 := Trade(symbol='BAR', price=22.3, quantity=800),
        Trade(symbol='FOO', price=16.1, quantity=100),
    ]

    hints = {
        'symbol': {
            'title': 'Ticker',
        },
        'price': {
            'fmt': ',.2f',
        },
    }
    generated_columns = generate_columns(items, hints=hints, exclude=['quantity'])

    column_symbol, column_price = generated_columns

    assert column_symbol.title == 'Ticker'

    assert column_price.title == 'Price'
    assert column_price.fmt == ',.2f'

    assert column_price.get_displayed_value(t2) == '22.30'


def test_generate_columns_with_pandas_dataframe():
    df = pd.DataFrame()
    df['symbol'] = ['A', 'B']
    df['price'] = [10.25, 12.0]

    generated_columns = generate_columns(DataFrameProxy(df))

    column_symbol, column_price = generated_columns

    assert column_symbol.title == 'Symbol'
    assert column_price.title == 'Price'
    assert column_price.align == Alignment.RIGHT


df = pd.DataFrame()
df['symbol'] = ['A', 'B']
df['price'] = [10.25, 12.0]
df['currency'] = ['EUR', 'GBP']

Record = namedtuple('Record', 'symbol price currency')
named_tuples = [Record('A', 10.25, 'EUR'), Record('B', 12.0, 'GBP')]

tuples = [('A', 10.25, 'EUR'), ('B', 12.0, 'GBP')]


@dataclass
class RecordData:
    symbol: str
    price: float
    currency: str


records = [RecordData('A', 10.25, 'EUR'), RecordData('B', 12.0, 'GBP')]

dicts = [
    {'symbol': 'A', 'price': 10.25, 'currency': 'EUR'},
    {'symbol': 'B', 'price': 12.0, 'currency': 'GBP'},
]


@pytest.mark.parametrize(
    ('items', 'include', 'hints'),
    [
        (DataFrameProxy(df), ['currency', 'price'], {}),
        (named_tuples, ['currency', 1], {}),
        (tuples, [2, 1], {2: {'title': 'Currency'}, 1: {'title': 'Price'}}),
        (records, ['currency', 'price'], {}),
        (dicts, ['currency', 'price'], {}),
    ],
)
def test_generate_columns_include(items, include, hints):
    col_1, col_2 = generate_columns(items, include=include, hints=hints)

    def assert_column(column, title, align):
        assert title == column.title
        assert align == column.align

    assert_column(col_1, 'Currency', Alignment.LEFT)
    assert_column(col_2, 'Price', Alignment.RIGHT)


@pytest.mark.parametrize(
    ('items', 'exclude', 'hints'),
    [
        (DataFrameProxy(df), ['price'], {}),
        (named_tuples, ['price'], {}),
        (tuples, [1], {0: {'title': 'Symbol'}, 2: {'title': 'Currency'}}),
        (records, ['price'], {}),
        (dicts, ['price'], {}),
    ],
)
def test_generate_columns_exclude(items, exclude, hints):
    col_1, col_2 = generate_columns(items, exclude=exclude, hints=hints)

    def assert_column(column, title, align):
        assert title == column.title
        assert align == column.align

    assert_column(col_1, 'Symbol', Alignment.LEFT)
    assert_column(col_2, 'Currency', Alignment.LEFT)


def test_total_cost_sums_cumulative_time_across_roles():
    column = Column('age', collect_stats=True)
    column.record_stats(role=0, elapsed=0.25)
    column.record_stats(role=0, elapsed=0.25)
    column.record_stats(role=6, elapsed=1.0)

    assert column.total_cost() == 1.5
    assert Column('age').total_cost() == 0


@pytest.mark.parametrize(
    ('raw_value', 'expected'),
    [
        (-1, NEGATIVE_NUMBER_CELL_STYLE),
        (-0.5, NEGATIVE_NUMBER_CELL_STYLE),
        (Decimal(-1), NEGATIVE_NUMBER_CELL_STYLE),
        (0, None),
        (1, None),
        (float('nan'), None),
        (None, None),
        (pd.NA, None),
    ],
)
def test_negative_number_cell_style(raw_value, expected):
    context = SimpleNamespace(raw_value=raw_value)
    assert get_cell_style_for_negative_numbers(context) is expected


def test_dataframe_with_missing_numbers_renders_without_style_errors(qtbot, caplog):
    df = pd.DataFrame({'name': ['a', 'b', 'c'], 'qty': pd.array([-1, None, 2], dtype='Int64')})
    table = QTable(columns=[], items=DataFrameProxy(df))
    qtbot.addWidget(table)
    table.columns = generate_columns(table.items)

    model = table.model()
    foreground = [model.data(model.index(row, 1), Qt.ItemDataRole.ForegroundRole) for row in range(3)]

    assert foreground == [NEGATIVE_NUMBER_CELL_STYLE['color'], None, None]
    assert not caplog.records


def test_a_dotted_key_is_a_plain_attribute_name():
    item = SimpleNamespace(**{'a.b': 1, 'a': SimpleNamespace(b=2)})

    assert Column('a.b').get_value(item) == 1


def test_a_subclass_can_override_how_values_are_looked_up():
    class Upper(Column):
        def get_value_by_attribute_lookup(self, item):
            return super().get_value_by_attribute_lookup(item).upper()

    class Doubled(Column):
        def get_value_by_getitem_lookup(self, item):
            return super().get_value_by_getitem_lookup(item) * 2

    assert Upper('name').get_value(SimpleNamespace(name='pam')) == 'PAM'
    assert Doubled('n', use_getitem=True).get_value({'n': 21}) == 42


@pytest.mark.parametrize('key', ['k', 0, ('a', 'b')])
def test_getitem_columns_look_up_the_key_as_given(key):
    assert Column(key, use_getitem=True).get_value({key: 'v'}) == 'v'
