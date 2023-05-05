#!/home/alascartc/djenkins/pytest/bin/python

import sys
import time
from PyQt5 import QtWidgets as QtW
from pathlib import Path
from pydcam import CamSaver, DCamReader, LoopRunner, DCamSim
from pydcam.dcam_gui import ControlWindow, ConsoleLog
from pydcam.api import OpenCamera, OpenAravis
from pydcam.api.dcamapi4 import DCAM_IDPROP
from pydcam import open_config
from pydcam.dcam_display import ImageUpdater
from pydcam.utils.zmq_pubsub import zmq_reader, zmq_publisher
from pydcam.utils.shmem import shmem_publisher, shmem_reader

from pydcam.aravis_reader import AravisReader

MAX_SIZE = 2304*2304*2

def gui():
    with LoopRunner() as EL:
        iDevice = 0

        fname = None
        if len(sys.argv) > 1:
            fname = Path(sys.argv[1]).resolve()

        app = QtW.QApplication(sys.argv)

        log = None

        log = ConsoleLog()
        log.set_as_stdout()
        log.set_as_stderr()
        log.show()

        print("Looking for Camera, please wait....")

        with OpenCamera(iDevice) as dcam:
            print("Got camera ", dcam)
            if dcam is None:
                print("No camera found, please connect")
                if log:
                    sys.exit(app.exec())
                sys.exit()
            dcam.prop_setdefaults()
            if fname is not None:
                init_dict = open_config(fname)
                if init_dict: dcam.prop_setfromdict(init_dict)

            reader = DCamReader(dcam)

            try:
                # this_zmq = zmq_publisher()
                this_zmq = shmem_publisher(size=MAX_SIZE)
                # this_zmq = dfhs
            except Exception as e:
                print(e)
                this_zmq = None
            else:
                reader.register_callback(this_zmq.publish)

            try:
                controlWin = ControlWindow(reader)
            except Exception as e:
                print(e)
            else:
                controlWin.register_atclose(log.close)
                controlWin.show()

            ret = app.exec()

        if this_zmq: this_zmq.close()
    sys.exit(ret)

def arvgui():
    with LoopRunner() as EL:
        iDevice = "EVT-HB-1800SM-640002"

        # fname = None
        # if len(sys.argv) > 1:
        #     fname = Path(sys.argv[1]).resolve()

        app = QtW.QApplication(sys.argv)

        log = None

        print("Looking for Camera, please wait....")

        with OpenAravis(iDevice) as dcam:
            print("Got camera ", dcam)
            if dcam is None:
                print("No camera found, please connect")
                if log:
                    sys.exit(app.exec())
                sys.exit()
            # dcam.prop_setdefaults()
            # if fname is not None:
            #     init_dict = open_config(fname)
            #     if init_dict: dcam.prop_setfromdict(init_dict)

            reader = AravisReader(dcam)

            this_zmq = zmq_publisher()
            # this_zmq = shmem_publisher(size=MAX_SIZE)

            reader.register_callback(this_zmq.publish)
    
            controlWin = ControlWindow(reader)
            
            log = ConsoleLog()
            log.set_as_stdout()
            log.set_as_stderr()
            
            controlWin.register_atclose(log.close)

            controlWin.show()
            log.show()
            
            ret = app.exec()

        if this_zmq: this_zmq.close()
    sys.exit(ret)

def simgui():
    with LoopRunner() as EL:
        iDevice = 0

        fname = None
        if len(sys.argv) > 1:
            fname = Path(sys.argv[1]).resolve()

        app = QtW.QApplication(sys.argv)

        log = None

        # log = ConsoleLog()
        # log.set_as_stdout()
        # log.set_as_stderr()
        # log.show()

        # reader = DCamReader(dcam)
        reader = DCamSim()
        print("DCAM sim made")
        try:
            print("Making publisher")
            # this_zmq = zmq_publisher()
            print("Publisher made")
            this_zmq = shmem_publisher(size=MAX_SIZE)
            # this_zmq = dfhs
        except Exception as e:
            print(e)
            this_zmq = None
        else:
            print("registering callback")
            reader.register_callback(this_zmq.publish)
            print("Callback registered")

        # try:
        print("making control win")
        controlWin = ControlWindow(reader)
        print("Control win made")
        # except Exception as e:
        #     print("Control win failed")
        #     print(e)
        # else:
        #     # controlWin.register_atclose(log.close)
        #     print("shwoign control win")
        controlWin.show()
        print("execing app")
        ret = app.exec()
        print("app is execed")
        if this_zmq: this_zmq.close()
    sys.exit(ret)

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
        try:
            # this_zmq = zmq_publisher()
            this_zmq = shmem_publisher(size=MAX_SIZE)
        except Exception as e:
            print(e)
            this_zmq = None
        else:
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
        if this_zmq: this_zmq.close()

def saver():

    # read_zmq = zmq_reader()
    read_zmq = shmem_reader()

    app = QtW.QApplication(sys.argv)
    this = CamSaver(read_zmq.oneshot,read_zmq.multishot)
    this.show()

    with read_zmq:
        sys.exit(app.exec())

def display():

    # this_zmq = zmq_reader(ratelimit=0.01)
    this_zmq = shmem_reader(ratelimit=0.01)

    app = QtW.QApplication(sys.argv)
    this = ImageUpdater()
    this.show()

    this_zmq.register(this.update_trigger)

    with this_zmq:
        sys.exit(app.exec())


def test():
    import pydcam
    with LoopRunner() as EL:
        print(EL)
        try:
            print(pydcam.get_event_loop())
        except Exception as e:
            print(e)

if __name__ == "__main__":
    simgui()
    # arvgui()
    # test()
    # gui()