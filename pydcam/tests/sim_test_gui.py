from pydcam.dcam_reader import DCamSim
from pydcam.utils.zmq_pubsub import zmq_publisher
from PyQt5 import QtWidgets as QtW
import sys
import atexit
from pydcam.dcam_gui import ControlWindow

if __name__ == "__main__":

    camreader = DCamSim()
    this_zmq = zmq_publisher()
    camreader.register_callback(this_zmq.publish)
    camreader.open_camera()

    app = QtW.QApplication(sys.argv)
    controlWin = ControlWindow(camreader)
    controlWin.show()

    atexit.register(this_zmq.close)
    sys.exit(app.exec())
