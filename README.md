# enaml-extensions
Extra widgets for Enaml

The flagship widget here is the `Table` widget which aims for providing
an easy way to display tabular data in a grid in the UI. It was designed
to support working with list of dicts, list of namedtuples, list of tuples,
or even pandas DataFrame.

An example:

```python
from enaml.widgets.api import *
from enamlext.widgets import Table, Column

enamldef Main(Window):
    Container:
        Table:
            items = [{'name': 'Joe', 'age': 30},
                     {'name': 'Jane', 'age': 31}]
            columns = [
                Column('name'),
                Column('age'),
            ]
```