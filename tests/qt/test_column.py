from enamlext.qt.table.column import Column


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
