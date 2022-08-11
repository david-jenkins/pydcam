
import json
import sys
from pathlib import Path
import toml
import yaml
from pydcam.utils.tomlencoder import MyTomlEncoder
from PyQt5 import QtWidgets as QtW

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