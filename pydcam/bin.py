

import sys
from PyQt5 import QtWidgets as QtW
from pathlib import Path
from pydcam.dcam_reader import DCamReader
from pydcam.dcam_gui import ControlWindow, ConsoleLog
from pydcam.api import OpenCamera
from pydcam.api.dcamapi4 import DCAM_IDPROP
from pydcam import open_config
from pydcam.dcam_display import ImageUpdater
from pydcam.dcam_saver import CamSaver
from pydcam.utils.zmq_pubsub import zmq_reader, zmq_publisher

def gui():
    iDevice = 0

    fname = None
    if len(sys.argv) > 1:
        fname = Path(sys.argv[1]).resolve()

    print("Showing log window")

    app = QtW.QApplication(sys.argv)

    log = ConsoleLog()
    log.set_as_stdout()
    log.set_as_stderr()
    log.show()

    print("Looking for Camera, please wait....")

    with OpenCamera(iDevice) as dcam:

        dcam.prop_setdefaults()
        if fname is not None:
            init_dict = open_config(fname)
            if init_dict: dcam.prop_setfromdict(init_dict)

        reader = DCamReader(dcam)
        this_zmq = zmq_publisher()
        reader.register_callback(this_zmq.publish)

        controlWin = ControlWindow(reader)
        controlWin.show()

        controlWin.register_atclose(log.close)
        controlWin.register_atclose(this_zmq.close)
        sys.exit(app.exec())

    print("No camera found, please connect")
    sys.exit(app.exec())

def reader():
    iDevice = 0

    fname = None
    if len(sys.argv) > 1:
        fname = Path(sys.argv[1]).resolve()

    with OpenCamera(iDevice) as dcam:

        dcam.prop_setdefaults()
        dcam.prop_setvalue(DCAM_IDPROP.EXPOSURETIME,1.0)

        if fname is not None:
            init_dict = open_config(fname)
            if init_dict: dcam.prop_setfromdict(init_dict)

        camreader = DCamReader(dcam)
        this_zmq = zmq_publisher()
        camreader.register_callback(this_zmq.publish)

        camreader.open_camera()

        while 1:
            try:
                x = input("Type exp X, where X is the exposure time:\nor type config to configure from file:\n")
                if x[:3] == "exp":
                    try:
                        et = float(x[4:])
                    except Exception as e:
                        print("wrong type for exposure time")
                        continue
                    camreader.set_exposure(et)
                elif x[:6] == "config":
                    init_dict = open_config()
                    if init_dict: dcam.prop_setfromdict(init_dict)
            except KeyboardInterrupt as e:
                print("Finished with ctrl-C")
                break

        print("closing")
        camreader.quit()

def saver():

    read_zmq = zmq_reader()

    app = QtW.QApplication(sys.argv)
    this = CamSaver(read_zmq.oneshot,read_zmq.multishot)
    this.show()

    with read_zmq:
        sys.exit(app.exec())

def display():

    this_zmq = zmq_reader(ratelimit=0.01)

    app = QtW.QApplication(sys.argv)
    this = ImageUpdater()
    this.show()

    this_zmq.register(this.update_trigger)

    with this_zmq:
        sys.exit(app.exec())


if __name__ == "__main__":
    gui()