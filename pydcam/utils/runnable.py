from PyQt5 import QtCore as QtC

class MyRunnable(QtC.QRunnable):
    def __init__(self,run):
        super().__init__()
        self.run = run