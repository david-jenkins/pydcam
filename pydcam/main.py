

import argparse
import sys
from pydcam.api import OpenAravis, OpenCamera, OpenMG
from pydcam.aravis_reader import AravisReader
from pydcam.dcam_gui import ConsoleLog, ControlWindow
from pydcam.dcam_reader import DCamReader
from pydcam.sim_reader import DCamSim, OpenSim
from pydcam.mg_reader import MGReader
from pydcam.utils import LoopRunner
from pydcam.utils.shmem import shmem_publisher
from pydcam.utils.zmq_pubsub import zmq_publisher
import pydcam.config
from PyQt5 import QtCore as QtC
from PyQt5 import QtWidgets as QtW
from PyQt5 import QtGui as QtG

import pyqtgraph as pg

pg.setConfigOption("imageAxisOrder",'row-major')

from pathlib import Path

HERE = Path(__file__).parent

api_funcs = {
    "aravis": (OpenAravis, AravisReader),
    "hamamatsu": (OpenCamera, DCamReader),
    "simulation": (OpenSim, DCamSim),
    "microgate": (OpenMG, MGReader)
}

pub_funcs = {
    'zmq' : zmq_publisher,
    'shm' : shmem_publisher,
}

def open_camera(filename):
    config = pydcam.config.read_config(filename)
    print(config)
    gui(config)

def open_config():
    app = QtW.QApplication(sys.argv)
    config = QtW.QFileDialog.getOpenFileName(None, "Choose camera", str(HERE/".."/"cameras"), "Toml file (*.toml)")
    print(config)
    open_camera(config)
    # app.exec(sys.exit())
    
def reader(config:dict):
    
    device_id = config['camera']
    
    OpenCam, CamReader = api_funcs[config['api']]
    Publisher = pub_funcs[config.get('publisher','zmq')]
    
    pub = None
    
    with LoopRunner() as EL:

        print("Looking for Camera, please wait....")

        with OpenCam(device_id) as cam_handle:
            print("Got camera ", cam_handle)
            if cam_handle is None:
                print("No camera found, please connect")
                sys.exit()

            reader = CamReader(cam_handle)

            pub = Publisher()

            reader.register_callback(pub.publish)
            
            reader.open_camera()

        if pub: pub.close()

def gui(config:dict):
    
    device_id = config['camera']
    
    OpenCam, CamReader = api_funcs[config['api']]
    Publisher = pub_funcs[config.get('publisher','zmq')]
    
    app = QtW.QApplication(sys.argv)

    log = None
    pub = None

    with LoopRunner() as EL:
        
        print("Looking for Camera, please wait....")

        with OpenCam(config) as cam_handle:
            print("Got camera ", cam_handle)
            if cam_handle is None:
                print("No camera found, please connect")
                sys.exit()
            # dcam.prop_setdefaults()
            # if fname is not None:
            #     init_dict = open_config(fname)
            #     if init_dict: dcam.prop_setfromdict(init_dict)

            reader = CamReader(cam_handle)

            pub = Publisher()
            # this_zmq = shmem_publisher(size=MAX_SIZE)

            reader.register_callback(pub.publish)
    
            controlWin = ControlWindow(reader)
            
            # log = ConsoleLog()
            # log.show()
            # log.set_as_stdout()
            # log.set_as_stderr()
            # controlWin.register_atclose(log.close)
            
            controlWin.show()
            ret = app.exec()

        if pub: pub.close()

    sys.exit(ret)

def cli():
    parser = argparse.ArgumentParser(
                    prog='PyCamReader',
                    description='Reads from cameras',
                    epilog='Text at the bottom of help')
    parser.add_argument("config",default=HERE/"../cameras/sim.toml",nargs='?')
    
    args = parser.parse_args()
    
    if args.config is not None:
        open_camera(args.config)
    else:
        open_config()
        
if __name__ == "__main__":
    # gui()
    cli()