
from enum import IntEnum
from pydcam.api.dcam import Dcamapi, Dcam
from pydcam.api.aravis import ArvCam
class OpenCamera:
    def __init__(self, iDevice):
        self.iDevice = iDevice

    def __enter__(self):
        if Dcamapi.init() is None:
            # raise Exception(f"Dcamapi.init() fails with error {Dcamapi.lasterr()}")
            print(f"Dcamapi.init() fails with error {Dcamapi.lasterr()}")
            return None
        self.dcam = Dcam(self.iDevice)
        if self.dcam.dev_open() is False:
            print("No Camera available")
            # raise Exception(f"Dcam.dev_open() fails with error {self.dcam.lasterr().name}")
            print(f"Dcam.dev_open() fails with error {self.dcam.lasterr().name}")
            return None
        return self.dcam

    def __exit__(self, exc_type, exc_value, traceback):
        print("Closing camera handle")
        self.dcam.dev_close()
        print("Closing the Dcamapi")
        Dcamapi.uninit()
        return False


class OpenAravis:
    def __init__(self, iDevice):
        self.iDevice = iDevice

    def __enter__(self):
        self.acam = ArvCam(self.iDevice)
        if self.acam.dev_open() is False:
            print("No Camera available")
            return None
        return self.acam

    def __exit__(self, exc_type, exc_value, traceback):
        return False
    
    
class CAMINFO(IntEnum):
    DeviceVendorName = 0
    DeviceModelName = 1
    DeviceVersion = 2
    DeviceSerialNumber = 3
    DeviceFirmareVersion = 4
    DeviceUserName = 5
    DeviceBus = 6
    
    
class REGIONINFO(IntEnum):
    Width = 0
    Height = 1
    OffsetX = 2
    OffsetY = 3
    Exposure = 4
    FrameRate = 5