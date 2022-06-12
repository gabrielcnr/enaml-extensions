from dataclasses import dataclass
from decimal import Decimal

from enamlext.qt.table.column import Column, generate_columns


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
    generated_columns = generate_columns(items, hints=hints)

    column_symbol, column_price, column_quantity = generated_columns

    assert column_symbol.title == 'Ticker'

    assert column_price.title == 'Price'
    assert column_price.fmt == ',.2f'

    assert column_quantity.title == 'Quantity'
    assert column_quantity.fmt == ''

    assert '22.30' == column_price.get_displayed_value(t2)