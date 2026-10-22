import os
import subprocess
import sys


def test_widgets_import_without_pandas():
    # pandas is an optional extra; the core Table must work with plain Python items.
    code = 'import sys; sys.modules["pandas"] = None; import enamlext.widgets; from enamlext.qt.qtable import QTable'
    env = {**os.environ, 'QT_QPA_PLATFORM': 'offscreen'}
    result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, env=env, check=False)
    assert result.returncode == 0, result.stderr
