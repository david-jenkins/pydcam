# -*- coding: utf-8 -*-
"""
    Hamamatsu DCAM_API ctypes python interface
    ================
    A ctypes based interface to Hamamatsu cameras using the DCAM API.

    This imports some common functions, makes some common defines and implements some of
    the C++ examples from the DCAM SDK4.
"""

import pydcam.api.dcam_extra as dapi_ex
from pydcam.api import OpenCamera
from pydcam import save_config

def propertylist(iDevice = 0):

    print( "PROGRAM START" )
    with OpenCamera(iDevice) as dcam:
        info = dapi_ex.dcamcon_show_dcamdev_info_detail(dcam)
        props = dapi_ex.dcamcon_show_property_list(dcam)

    return info, props

if __name__ == "__main__":

    info, props = propertylist()

    save_dict = {"DEVICE_INFO":info,**props}

    if info["MODEL"] == "C15440-20UP":
        cameraname = "fusion"
    else:
        cameraname = "flash"

    save_config(save_dict, f"{cameraname}_raw_properties.toml")

