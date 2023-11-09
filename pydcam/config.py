

import tomli

def read_config(filename):
    with open(filename, 'rb') as tf:
        config = tomli.load(tf)
    return config