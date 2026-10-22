import os
import subprocess
import sys


def test_widgets_import_without_pandas():
    # pandas is an optional extra; the core Table must work with plain Python items.
    code = 'import sys; sys.modules["pandas"] = None; import enamlext.widgets; from enamlext.qt.qtable import QTable'
    env = {**os.environ, 'QT_QPA_PLATFORM': 'offscreen'}
    result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, env=env, check=False)
    assert result.returncode == 0, result.stderr


def test_library_modules_do_not_import_test_tools():
    # pytest is a dev dependency; importing a widget must not require it.
    code = (
        'import sys; sys.modules["pytest"] = None; '
        'from enamlext.widgets.multi_select_model import MultiSelectModel; '
        'assert MultiSelectModel(items=[1, 2], selected_items=[2]).available_items == [1]'
    )
    env = {**os.environ, 'QT_QPA_PLATFORM': 'offscreen'}
    result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, env=env, check=False)
    assert result.returncode == 0, result.stderr


def test_readme_example_imports():
    from enamlext.widgets import Alignment, Column, Table

    assert Column('age', align=Alignment.RIGHT).align is Alignment.RIGHT
    assert Table is not None


def test_missing_qt_binding_explains_how_to_install_one():
    code = (
        'import sys\n'
        'for name in ("PyQt5", "PyQt6", "PySide2", "PySide6"):\n'
        '    sys.modules[name] = None\n'
        'import enamlext.widgets\n'
    )
    env = {k: v for k, v in os.environ.items() if k not in ('QT_API', 'PYTEST_QT_API')}
    result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, env=env, check=False)
    assert result.returncode != 0
    assert 'pip install "enaml-extensions[pyqt6]"' in result.stderr
