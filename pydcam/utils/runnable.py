from PyQt5 import QtCore as QtC

class MyRunnable(QtC.QRunnable):
    def __init__(self, run, *args, **kwargs):
        super().__init__()
        self.func = run
        self.args = args
        self.kwargs = kwargs

    def run(self):
        self.func(*self.args, **self.kwargs)