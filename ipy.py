from PyQt5.QtCore import pyqtRemoveInputHook
from PyQt5.QtWidgets import QApplication
from ipykernel.kernelapp import IPKernelApp
from qtconsole.client import QtKernelClient
from qtconsole.inprocess import QtInProcessKernelManager
from qtconsole.manager import QtKernelManager
from qtconsole.rich_jupyter_widget import RichJupyterWidget

pyqtRemoveInputHook()


app = QApplication([])

# IPKernelApp
def g():
    w = RichJupyterWidget()

    kernel_manager = QtInProcessKernelManager()
    kernel_manager.start_kernel(show_banner=True)

    kernel = kernel_manager.kernel
    kernel.gui = 'qt'

    kernel_client = kernel_manager.client()
    kernel_client.start_channels()

    w.kernel_manager = kernel_manager
    w.kernel_client = kernel_client

    w.show()
    yield


def g2():
    kernel_manager = QtKernelManager(kernel_name='python3')
    kernel_manager.start_kernel()
    kernel_client = kernel_manager.client()
    kernel_client.start_channels()


    ipython_widget = RichJupyterWidget()
    ipython_widget.kernel_manager = kernel_manager
    ipython_widget.kernel_client = kernel_client
    # By default, iPython adds a blank line between inputs. Per Monika's request, this eliminates the extra line. See https://qtconsole.readthedocs.io/en/latest/config_options.html#options; this fix was based on info from https://stackoverflow.com/questions/38652671/ipython-5-0-remove-spaces-between-input-lines.
    ipython_widget.input_sep = ''
    ipython_widget.show()
    import pdb; pdb.set_trace()
    yield


g1 = g2()
g2 = g2()

next(g1)
next(g2)

app.exec_()

