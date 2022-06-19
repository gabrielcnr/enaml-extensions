from collections import namedtuple
from dataclasses import dataclass
from decimal import Decimal

import pandas as pd
import pytest

from enamlext.qt.qt_dataframe import DataFrameProxy
from enamlext.qt.table.column import Column, generate_columns, Alignment


def test_get_displayed_value():
    class Foo:
        def __str__(self) -> str:
            return 'string for Foo'

        def __format__(self, spec: str) -> str:
            s = str(self)
            if spec == 'u':
                s = s.upper()
            else:
                s = format(s, spec)
            return s

    foo = Foo()

    item = {'foo': foo}

    column = Column('foo', use_getitem=True)

    assert foo is column.get_value(item)
    assert 'string for Foo' == column.get_displayed_value(item)

    column2 = Column('foo', use_getitem=True, fmt='u')
    assert 'STRING FOR FOO' == column2.get_displayed_value(item)


def test_giving_fmt_as_callback():
    def uppercase_mirrored(value):
        return str(value)[::-1].upper()

    class InterestingClass:
        def __str__(self): return 'TextForUsers'

    obj = InterestingClass()
    item = {'obj': obj, 'foo': None}

    column = Column('obj', fmt=uppercase_mirrored, use_getitem=True)

    assert 'SRESUROFTXET' == column.get_displayed_value(item)



def test_generate_columns_with_hints():
    @dataclass
    class Trade:
        symbol: str
        price: Decimal
        quantity: int

    items = [
        t1 := Trade(symbol='FOO', price=15.2, quantity=500),
        t2 := Trade(symbol='BAR', price=22.3, quantity=800),
        t3 := Trade(symbol='FOO', price=16.1, quantity=100),
    ]

    hints = {
        'symbol': {
            'title': 'Ticker',
        },
        'price': {
            'fmt': ',.2f',
        }
    }
    generated_columns = generate_columns(items, hints=hints, exclude=['quantity'])

    column_symbol, column_price = generated_columns

    assert column_symbol.title == 'Ticker'

    assert column_price.title == 'Price'
    assert column_price.fmt == ',.2f'

    assert '22.30' == column_price.get_displayed_value(t2)


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

dicts = [{'symbol': 'A', 'price': 10.25, 'currency': 'EUR'},
         {'symbol': 'B', 'price': 12.0, 'currency': 'GBP'}, ]

@pytest.mark.parametrize(
    ['items', 'include', 'hints'],
    [
        (DataFrameProxy(df), ['currency', 'price'], {}),
        (named_tuples, ['currency', 1], {}),
        (tuples, [2, 1], {2: {'title': 'Currency'}, 1: {'title': 'Price'}}),
        (records, ['currency', 'price'], {}),
        (dicts, ['currency', 'price'], {}),
    ]
)
def test_generate_columns_include(items, include, hints):
    col_1, col_2 = generate_columns(items, include=include, hints=hints)

    def assert_column(column, title, align):
        assert title == column.title
        assert align == column.align

    assert_column(col_1, 'Currency', Alignment.LEFT)
    assert_column(col_2, 'Price', Alignment.RIGHT)


@pytest.mark.parametrize(
    ['items', 'exclude', 'hints'],
    [
        (DataFrameProxy(df), ['price'], {}),
        (named_tuples, ['price'], {}),
        (tuples, [1], {0: {'title': 'Symbol'}, 2: {'title': 'Currency'}}),
        (records, ['price'], {}),
        (dicts, ['price'], {}),
    ]
)
def test_generate_columns_exclude(items, exclude, hints):
    col_1, col_2 = generate_columns(items, exclude=exclude, hints=hints)

    def assert_column(column, title, align):
        assert title == column.title
        assert align == column.align

    assert_column(col_1, 'Symbol', Alignment.LEFT)
    assert_column(col_2, 'Currency', Alignment.LEFT)
