# enaml-extensions

[![CI](https://github.com/gabrielcnr/enaml-extensions/actions/workflows/main.yml/badge.svg)](https://github.com/gabrielcnr/enaml-extensions/actions/workflows/main.yml)
[![PyPI](https://img.shields.io/pypi/v/enaml-extensions)](https://pypi.org/project/enaml-extensions/)
[![Python versions](https://img.shields.io/pypi/pyversions/enaml-extensions)](https://pypi.org/project/enaml-extensions/)
[![License](https://img.shields.io/pypi/l/enaml-extensions)](https://github.com/gabrielcnr/enaml-extensions/blob/main/LICENSE)

Extra widgets for Enaml

The flagship widget here is the `Table` widget which aims for providing
an easy way to display tabular data in a grid in the UI. It was designed
to support working with list of dicts, list of namedtuples, list of tuples,
or even pandas DataFrame.

## Installation

enaml-extensions supports Python 3.11 to 3.14 and works with PyQt6, PySide6 or
PyQt5 (through [QtPy](https://github.com/spyder-ide/qtpy)). Install it together
with the Qt binding of your choice:

```bash
pip install "enaml-extensions[pyqt6]"    # or [pyside6], or [pyqt5]
```

Optional extras:

| Extra | Enables |
|-------|---------|
| `dataframe` | the `DataFrame` widget (pandas) |
| `scintilla-pyqt6` / `scintilla-pyqt5` | the JSON/SQL editors (QScintilla; not available for PySide6) |
| `ipython` | the `IPythonConsole` widget (qtconsole) |

Python 3.15 is not supported yet: enaml does not have a release that builds on it.

## Example

```python
from enaml.widgets.api import *
from enamlext.widgets import Table, Column

enamldef Main(Window):
    Container:
        Table:
            items = [{'name': 'Joe', 'age': 30},
                     {'name': 'Jane', 'age': 31}]
            columns = [
                Column('name', use_getitem=True),
                Column('age', use_getitem=True),
            ]
```

Use `use_getitem=True` for items accessed by key (dicts); leave it off for
objects accessed by attribute (dataclasses, namedtuples).

## Updating models from worker threads

```python
import pandas as pd
from atom.api import Typed
from enamlext.atom import Atom


class Model(Atom):
    frame = Typed(pd.DataFrame).tag(conflate=True)
```

Assigning `model.frame` from a worker thread queues the set for the main thread and
keeps only the latest value, so a burst of updates refreshes the view once. On the main
thread the assignment is immediate. For objects that do not derive from
`enamlext.atom.Atom`, call `conflated_setattr(obj, 'frame', value)`.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).
