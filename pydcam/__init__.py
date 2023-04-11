
import asyncio
import atexit
from enum import Enum
import json
import sys
from pathlib import Path
import threading
import toml
import yaml
from pydcam.utils.tomlencoder import MyTomlEncoder
from PyQt5 import QtWidgets as QtW
from PyQt5 import QtCore as QtC

from pydcam.dcam_reader import DCamReader, DCamSim
from pydcam.dcam_saver import CamSaver
from pydcam.utils.runnable import MyRunnable

class LoopRunner:
    def __enter__(self):
        self.EVENT_LOOP = asyncio.new_event_loop()
        # event_thread = threading.Thread(target=self.EVENT_LOOP.run_forever)
        # event_thread.start()
        event_runnable = MyRunnable(self.EVENT_LOOP.run_forever)
        QtC.QThreadPool.globalInstance().start(event_runnable)
        global EVENT_LOOP
        EVENT_LOOP = self.EVENT_LOOP
        return self.EVENT_LOOP

    def __exit__(self, *args):
        for task in asyncio.all_tasks(self.EVENT_LOOP):
            task.cancel()
        self.EVENT_LOOP.call_soon_threadsafe(self.EVENT_LOOP.stop)

def open_config(file_path=""):
    if not Path(file_path).is_absolute():
        app = QtW.QApplication.instance()
        if app is None:
            app = QtW.QApplication([])
        file_path = QtW.QFileDialog.getOpenFileName(None,"Select Config File",str(Path.home()/file_path),"Config Files (*.toml *.yaml *.json)")[0]
        if file_path == "":
            return None
    file_path = Path(file_path).expanduser().resolve()
    if not file_path.exists():
        print("No file available")
        return None
    if ".toml" in file_path.name:
        with open(file_path, "r") as cf:
            ret = toml.load(cf)
        return ret
    elif ".yaml" in file_path.name:
        with open(file_path, "r") as cf:
            ret = yaml.safe_load(cf)
        return ret
    elif ".json" in file_path.name:
        with open(file_path, "r") as cf:
            ret = json.load(cf)
        return ret
    else:
        print("Wrong file type")
        return None

def save_config(indict, file_path=""):
    if not Path(file_path).is_absolute():
        if QtW.QApplication.instance() is None:
            app = QtW.QApplication([])
        file_path = QtW.QFileDialog.getSaveFileName(None,"Save Config File",str(Path.home()/file_path),"Config Files (*.toml *.yaml *.json)")[0]
        if file_path == "":
            return None
    file_path = Path(file_path)
    if ".toml" in file_path.name:
        with open(file_path, "w") as cf:
            toml.dump(indict, cf, MyTomlEncoder())
    elif ".yaml" in file_path.name:
        with open(file_path, "w") as cf:
            yaml.dump(indict, cf)
    elif ".json" in file_path.name:
        with open(file_path, "w") as cf:
            json.dump(indict, cf, indent=4)
    else:
        print("Wrong file type, not saving file")