from PyQt5 import QtCore as QtC

class Signals(QtC.QObject):
    finished = QtC.pyqtSignal()

class MyRunnable(QtC.QRunnable):
    def __init__(self, run, *args, **kwargs):
        super().__init__()
        self.func = run
        self.args = args
        self.kwargs = kwargs
        self.signal = Signals()

    def run(self):
        self.func(*self.args, **self.kwargs)
        self.signal.finished.emit()

def run_in_background(func, args=[], kwargs={}, callback=None):
    event_runnable = MyRunnable(func, *args, **kwargs)
    if callback is not None:
        event_runnable.signal.finished.connect(callback)
    QtC.QThreadPool.globalInstance().start(event_runnable)