

import sys
from PyQt5 import QtWidgets as QtW
from pydcam.dcam_reader import DCamReader, zmq_publisher
from pydcam.dcam_gui import ControlWindow
from pydcam.api import OpenCamera
from pydcam import open_config

CONF_FILE = "orca_config1.toml"

def gui():
    with OpenCamera(0) as dcam:

        dcam.prop_setdefaults()
        init_dict = open_config(CONF_FILE)
        print("Setting from config file")
        dcam.prop_setfromdict(init_dict)

        app = QtW.QApplication(sys.argv)
        reader = DCamReader(dcam)
        this_zmq = zmq_publisher()
        reader.register_callback(this_zmq.publish)

        controlWin = ControlWindow(reader)
        controlWin.show()

        sys.exit(app.exec())

if __name__ == "__main__":
    gui()