# Contributing

The project uses [uv](https://docs.astral.sh/uv/) for environments and
dependencies.

## Set up

```bash
uv sync --extra pyqt6        # dev tools plus a Qt binding (or --extra pyside6 / --extra pyqt5)
uv run pre-commit install    # run the formatter and linters on every commit
```

## Run the checks

```bash
uv run pytest                               # tests (Qt runs offscreen by default)
uv run coverage run -m pytest               # tests with coverage
uv run coverage combine && uv run coverage report
uv run ruff format && uv run ruff check     # format and lint
uv run mypy                                 # type check
```

To test against another Qt binding, install it and point both QtPy and
pytest-qt at it:

```bash
uv sync --extra pyside6
QT_API=pyside6 PYTEST_QT_API=pyside6 uv run pytest
```

CI runs the same checks on Python 3.11 to 3.14 across Linux, macOS and
Windows.
