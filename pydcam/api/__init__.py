
from pydcam.api.dcam import Dcamapi, Dcam

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
        pass
        # load the ARAVIS driver
        # get a camera handle using name self.iDevice
        # retrurn cam handle

    def __exit__(self, exc_type, exc_value, traceback):
        pass
        # close the camera handle
        # unload the aravis driver