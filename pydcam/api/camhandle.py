

"""
The base class of the camera handle showing the API

Work in progress...
"""

from collections import namedtuple

import numpy

SensorRegion = namedtuple("SensorRegion", ('XOffset', 'YOffset', 'XSize', 'Ysize'))

CameraInfo = namedtuple("CameraInfo", ('DeviceVendorName','DeviceModelName','DeviceVersion','DeviceSerialNumber','DeviceFirmwareVersion','DeviceUserName'))

class CameraHandle:
    
    def __init__(self, device_id=None):
        """Init a camera with device_id"""

    def is_open(self) -> bool:
        """Check if the camera interface is open"""
    
    def cam_open(self, device_id=None):
        """Open the device interface"""
        
    def cam_close(self):
        """Close the device interface"""
    
    def get_info(self) -> CameraInfo:
        """Get camera information"""

    def get_info_detail(self) -> dict:
        """Get detailed camera information"""
        
    def get_region(self) -> SensorRegion:
        """Get current camera region"""
        
    def set_region(self, region:SensorRegion):
        """Set the camera region"""
        
    def check_region(self, region:SensorRegion):
        """Check if the region values are valid"""
        
    def set_region_size(self, XSize:int, YSize:int):
        """Set only the size of the region"""
        
    def set_region_position(self, XOffset:int, YOffset:int):
        """Set only the position of the region"""
        
    def get_integer(self, name:str) -> int:
        """Get an integer value"""

    def get_integer_range(self, name:str) -> tuple[int, int, int]:
        """Get an integer range (min, max, step)"""
        
    def check_integer(self, name:str, value:int):
        """Check if the value is valid"""
        
    def set_integer(self, name:str, value:int):
        """Set an integer"""
    
    def get_string(self, name:str) -> str:
        """Get a string value from the interface"""
    
    def set_string(self, name:str, value:str):
        """Set a string value to the interface"""
        
    def set_defaults(self):
        """Try and reset the camera to default configuration"""
        
    def get_float(self, name:str) -> float:
        """Get a float (or double) value from the camera"""
        
    def check_float(self, name:str, value:float):
        """Check if value is valid decimal value"""
        
    def set_float(self, name:str, value:float):
        """Set afloat value to the camera"""
        
    def get_decimal_range(self, name:str) -> tuple[float, float, float]:
        """Get the range(min,max,step) of an attribute"""
        
    def set_by_dict(self, values:dict):
        """Set a number of values contained in a dictionary"""
        
    def get_framerate(self) -> float:
        """Get the frame rate"""
        
    def set_framerate(self, framerate:float):
        """Set the frame rate"""

    def get_exptime(self) -> float:
        """Get the exposure time"""
        
    def set_exptime(self, exptime:float):
        """Set the exposure time"""
        
    def get_frame(self) -> numpy.ndarray:
        """Get an image frame"""
        
    def start_capture(self):
        """Start capturing continuous images"""
        
    def stop_capture(self):
        """Stop continuous capture"""
        
    def capture_status(self) -> bool:
        """Query if the camera is continuously capturing"""
