
from pathlib import Path
import toml
from pydcam.utils.tomlencoder import MyTomlEncoder

CONF_DIR = Path(__file__).resolve().parent.parent/"config"

CONF_FILE = "orca_config1.toml"

def open_config(file_name):
    if ".toml" in file_name:
        with open(CONF_DIR/file_name,"r") as cf:
            ret = toml.load(cf)
        return ret
    else:
        raise Exception("Cannot open file")

def save_config(indict, file_name):
    if ".toml" in file_name:
        print("saving config to ", CONF_DIR/file_name)
        with open(CONF_DIR/file_name,"w") as cf:
            toml.dump(indict, cf, MyTomlEncoder())
    else:
        raise Exception("Cannot save file")