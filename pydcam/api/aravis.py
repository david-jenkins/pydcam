




"""
The interface to the Arvais API for my cam reader program
"""

from collections import namedtuple
from pathlib import Path
import threading
import time
try:
    import gi
    gi.require_version ('Aravis', '0.8')
    from gi.repository import Aravis
except Exception as e:
    print(e)
    print("No Aravis available")
    class FakeClass:
        """Allows importing on linux/mac where no library is available"""
        def __getattr__(self, name):
            return FakeClass()
    Aravis = FakeClass()
    print("No Hamamatsu driver available")

def EVT_HB_1800SM_640002_SETUP(arvcam):
    print("setting values for EVT_HB_1800SM_640002")
    arvcam.camhandle.gv_auto_packet_size()
    arvcam.camhandle.gv_set_packet_size(9000)
    arvcam.camhandle.gv_set_stream_options(Aravis.GvStreamOption.NONE)
    arvcam.camhandle.gv_select_stream_channel(-1)
    arvcam.camhandle.gv_set_packet_delay(-1)

device_specific_config = {
    "EVT-HB-1800SM-640002" : EVT_HB_1800SM_640002_SETUP,
}

Feature = namedtuple('Feature', ['name', 'value', 'min', 'max', 'inc', 'unit', 'description'])

def Feature_from_node(node):
    return Feature(node.get_name(),node.get_value(),node.get_min(),node.get_max(),node.get_inc(),node.get_unit(),node.get_description())

def get_gc_features(genicam, name):
    node = genicam.get_node(name)
    if node is None: return None
    if isinstance(node, Aravis.GcCategory):
        retval = {}
        features = node.get_features()
        for f in features:
            retval[f] = get_gc_features(genicam, f)
        return retval
    elif isinstance(node, (Aravis.GcStringRegNode,Aravis.GcIntegerNode,Aravis.GcBoolean,Aravis.GcEnumeration,Aravis.GcFloatNode)):
        try:
            return node.get_value()
        except Exception as e:
            return None
    elif isinstance(node, (Aravis.GcSwissKnifeNode, Aravis.GcIntSwissKnifeNode)):
        try:
            return node.get_value()
        except Exception as e:
            return None
    elif isinstance(node, (Aravis.GcCommand)):
        return node.get_name()
    elif isinstance(node, (Aravis.GcRegisterNode)):
        return node.get_name()
    else:
        print(f"unknown node type: {name} = {type(node)}")
        return node.get_value()
    
def get_features(camera, name):
    device = camera.get_device ()
    genicam = device.get_genicam ()
    return get_gc_features(genicam, name)

def _check_feature(feature:Feature, value):
    value = feature.min + round((value-feature.min)/feature.inc)*feature.inc
    if value < feature.min or value > feature.max:
        return None
    return value

def check_feature(camera, name, value):
    device = camera.get_device()
    genicam = device.get_genicam()
    node = genicam.get_node(name)
    if isinstance(node, (Aravis.GcIntegerNode,Aravis.GcFloatNode,Aravis.GcSwissKnifeNode,Aravis.GcIntSwissKnifeNode)):
        feature = Feature_from_node(node)
        if _check_feature(feature, value) is None:
            return False
    return True

def get_feature(camera, name):
    device = camera.get_device()
    genicam = device.get_genicam()
    node = genicam.get_node(name)
    if node is not None:
        if isinstance(node, (Aravis.GcIntegerNode,Aravis.GcFloatNode,Aravis.GcSwissKnifeNode,Aravis.GcIntSwissKnifeNode)):
            return Feature_from_node(node)
        return node.get_value()
    else:
        raise KeyError(f"{name} not found")

def set_feature(camera, name, value):
    device = camera.get_device ()
    genicam = device.get_genicam ()
    node = genicam.get_node(name)
    if node is not None:
        if isinstance(node, (Aravis.GcIntegerNode,Aravis.GcFloatNode,Aravis.GcSwissKnifeNode,Aravis.GcIntSwissKnifeNode)):
            feature = Feature_from_node(node)
            value = _check_feature(feature, value)
            if value is None:
                raise ValueError("Invalid value")
        node.set_value(value)
        return get_feature(camera, name)
    else:
        raise KeyError(f"{name} not found")

def set_feature_from_string(camera, name, value):
	device = camera.get_device ()
	genicam = device.get_genicam ()
	node = genicam.get_node(name)
	node.set_value_from_string(value)

class ArvCam:
    def __init__(self, device_config):
        self.device_config = device_config
        self.iDevice = self.device_config['camera']
        self.camhandle = None
        self.popped_buffers = []
        self.stream = None
        self.data = None
        self.status = None
        self.newdata = threading.Event()
        self.newdata.clear()
        self.not_cancelled = True
        
    def is_opened(self):
        return bool(self.camhandle)

    def dev_open(self):

        try:
            self.camhandle = Aravis.Camera.new (self.iDevice)
        except Exception as e:
            print(e)
            return False

        for name,value in self.device_config['configuration'].items():
            print(f"Here I set {name} to {value}")
            if isinstance(value,int):
                print(f"setting {name} to {value}")
                self.camhandle.set_integer(name,value)
            elif isinstance(value, str):
                print(f"setting {name} to {value}")
                set_feature_from_string(self.camhandle,name,value)
        
        if self.iDevice in device_specific_config:
            device_specific_config[self.iDevice](self)
        
        payload = self.camhandle.get_payload ()

        [x,y,width,height] = self.camhandle.get_region ()
        
        print ("Camera vendor : %s" %(self.camhandle.get_vendor_name ()))
        print ("Camera model  : %s" %(self.camhandle.get_model_name ()))
        print ("ROI           : %dx%d at %d,%d" %(width, height, x, y))
        print ("Payload       : %d" %(payload))
        print ("Pixel format  : %s" %(self.camhandle.get_pixel_format_as_string ()))
        
        print(f"{self.camhandle.gv_get_packet_size()=}")
        print(f"{self.camhandle.gv_get_packet_delay()=}")
        print(f"{self.camhandle.gv_get_n_stream_channels()=}")
        
        return True

    # def prop_set_defaults(self):
    #     cmds = {
    #         # "GevSCPSPacketSize" : 9000,
    #         "FrameRate" : 10,
    #         "Exposure" : 5000,
    #         "PixelFormat" : "Mono8",
    #         "Gain" : 500,
    #         "TriggerMode" : "Off",
    #         "OffsetX": 0,
    #         "OffsetY": 0,
    #         "Width": 600,
    #         "Height": 600,
    #     }

    #     for name,value in cmds.items():
    #         if isinstance(value,int):
    #             print(f"setting {name} to {value}")
    #             self.camhandle.set_integer(name,value)
    #         elif isinstance(value, str):
    #             print(f"setting {name} to {value}")
    #             set_feature_from_string(self.camhandle,name,value)
            
    def prop_setfromdict(self, pdict:dict):
        for key,value in pdict.items():
            self.prop_setvalue(key,value)
        
    def prop_setvalue(self, name, value):
        if self.is_opened():
            set_feature(self.camhandle, name, value)
            
    def get_info(self):
        keys = ['DeviceVendorName','DeviceModelName','DeviceVersion','DeviceSerialNumber','DeviceFirmwareVersion','DeviceUserName']
        details = self.get_info_detail()
        if details is not None:
            return {key:details.get(key,None) for key in keys}

    def get_info_detail(self):
        feature_categories = ["deviceInformation","DeviceControl"]
        for category in feature_categories:
            features = get_features(self.camhandle, category)
            if features is not None:
                return features

    def get_feature(self, name):
        if self.is_opened():
            return get_feature(self.camhandle, name)
        
    def check_feature(self, name, value):
        return check_feature(self.camhandle, name, value)
    
    def set_feature(self, name, value):
        if self.is_opened():
            return set_feature(self.camhandle, name, value)
    
    def get_region(self):
        return self.camhandle.get_region()
    
    def get_integer(self, name):
        return self.camhandle.get_integer(name)

    def get_integer_bounds(self, name):
        return self.camhandle.get_integer_bounds(name)
    
    def get_integer_step(self, name):
        return self.camhandle.get_integer_increment(name)
    
    def check_integer(self, name, value):
        bounds = self.get_integer_bounds(name)
        step = self.get_integer_step(name)
        print("Checking ", name)
        print(f"{value=}, {bounds.min=}, {bounds.max=}, {step}")
        print(f"{value<bounds.min=} or {value>bounds.max=} or {(value-bounds.min)%step=}")
        if value<bounds.min or value>bounds.max or (value-bounds.min)%step:
            return False
        else:
            return True
    
    def set_region(self, offx, offy, width, height):
        width_now = self.get_feature("Width")
        offx_now = self.get_feature("OffsetX")
        if _check_feature(width_now, width) is not None:
            width = self.set_feature("Width", width)
            if _check_feature(offx_now, offx) is not None:
                offx = self.set_feature("OffsetX", offx)
                print(f"Width set to {width.value}, OffsetX set to {offx.value}")
            else:
                print("width/offsetX error: None set")
                width = self.set_feature("Width", width_now.value)
        elif _check_feature(offx_now, offx) is not None:
            offx = self.set_feature("OffsetX", offx)
            if _check_feature(width_now, width) is not None:
                width = self.set_feature("Width", width)
                print(f"Width set to {width.value}, OffsetX set to {offx.value}")
            else:
                print("width/offsetX error: None set")
                offx = self.set_feature("OffsetX", offx_now.value)
        else:
            print("width/offsetx error: None set")

        height_now = self.get_feature("Height")
        offy_now = self.get_feature("OffsetY")
        if _check_feature(height_now, height) is not None:
            height = self.set_feature("Height", height)
            if _check_feature(offy_now, offy) is not None:
                offy = self.set_feature("OffsetY", offy)
                print(f"Height set to {height.value}, OffsetY set to {offy.value}")
            else:
                print("height/offsetY error: None set")
                height = self.set_feature("Height", height_now.value)
        elif _check_feature(offy_now, offy) is not None:
            offy = self.set_feature("OffsetY", offy)
            if _check_feature(height_now, height) is not None:
                height = self.set_feature("Height", height)
                print(f"Height set to {height.value}, OffsetY set to {offy.value}")
            else:
                print("height/offsetY error: None set")
                offy = self.set_feature("OffsetY", offy_now.value)
    
    def get_payload(self):
        return self.camhandle.get_payload()
    
    def get_pixel_format(self):
        return self.camhandle.get_pixel_format_as_string()

    def get_exposure_time_us(self) -> int:
        names = ["Exposure", "ExposureTime"]
        for name in names:
            try:
                feature = get_feature(self.camhandle, name)
            except:
                continue
            else:
                if feature.unit == 'us':
                    return feature.value
                else:
                    print(f"{name} warning: unknown units")
                    return int(feature.value*1000000)
        raise ValueError("Exposure not found")

    def set_exposure_us(self, exp_time:int):
        names = ["Exposure", "ExposureTime"]
        for name in names:
            try:
                feature = self.get_feature(name)
            except:
                continue
            else:
                if feature.unit == "us":
                    return self.set_feature(name, exp_time)
                else:
                    print(f"{name} warning: unknown units")
                    return self.set_feature(name, exp_time/1e6)
        raise ValueError("Exposure not found")
        

    def get_frame_rate_hz(self):
        names = ["FrameRate", "AcquisitionFrameRate"]
        for name in names:
            try:
                feature = get_feature(self.camhandle, name)
            except:
                continue
            else:
                if feature.unit == 'Hz':
                    return feature.value
                elif feature.unit == 'mHz':
                    return feature.value*1000
                elif feature.unit == 'uHz':
                    return feature.value*1000000
                else:
                    print(f"{name} warning: unknown units")
                    return feature.value
        raise ValueError("Frame Rate not found")
    
    def set_frame_rate_hz(self, fr):
        names = ["FrameRate", "AcquisitionFrameRate"]
        for name in names:
            try:
                feature = get_feature(self.camhandle, name)
            except:
                continue
            else:
                if feature.unit == 'Hz':
                    return self.set_feature(name, fr)
                elif feature.unit == 'mHz':
                    return self.set_feature(name, fr/1000)
                elif feature.unit == 'uHz':
                    return self.set_feature(name, fr/1000000)
                else:
                    print(f"{name} warning: unknown units")
                    return self.set_feature(name, fr)
        raise ValueError("Frame Rate not found")

    def set_gain(self, ga):
        self.set_feature("Gain", ga)

    def get_data(self, timeout=5):
        retval = self.newdata.wait(timeout)
        self.newdata.clear()
        if retval and self.not_cancelled:
            return self.data
        else:
            self.not_cancelled = True
            return None
        
    def get_status(self):
        return self.status

    def cancel_get(self):
        self.not_cancelled = False
        self.newdata.set()

    def buffer_callback(self, user_data, cb_type, buffer):
        if buffer is not None:
            self.data = buffer.get_image_data()
            self.status = buffer.get_status()
            self.newdata.set()
            self.stream.push_buffer(buffer)
    
    def cap_start(self):

        had_stream = True
        if self.stream is None:
            had_stream = False
            print("creating stream")
            self.stream = self.camhandle.create_stream (self.buffer_callback, None)

        payload = self.camhandle.get_payload()
        print("payload is ", payload)
        for i in range(0,4):
            print("pusing buffer ",i," of size ", payload)
            self.stream.push_buffer (Aravis.Buffer.new_allocate (payload))

        if had_stream:
            self.stream.start_thread()
        print("START ACQUISITION")
        self.camhandle.start_acquisition()
        return True

    def cap_stop(self):
        print("STOPPING CAP")
        self.camhandle.stop_acquisition()
        if self.stream is not None:
            print("stopping")
            self.stream.stop_thread(True)
            print("stopped")

def print_info(arvcam:ArvCam):
    keys = ['DeviceVendorName','DeviceModelName','DeviceVersion','DeviceSerialNumber','DeviceFirmwareVersion','DeviceUserName']
    feature_categories = ["DeviceInformation","DeviceControl"]
    if arvcam.is_opened:
        for category in feature_categories:
            features = get_features(arvcam.camhandle, category)
            if features is None: continue
            for key,value in features.items():
                if key in keys:
                    tabs = ["\t"]*(2)
                    tabs = ["\t"]*(2-len(key)//15)
                    print(key,"".join(tabs),": ",value)

def print_info_detail(arvcam:ArvCam):
    if arvcam.is_opened:
        features = get_features(arvcam.camhandle,"DeviceInformation")
        for key,value in features.items():
            tabs = ["\t"]*(2)
            tabs = ["\t"]*(2-len(key)//15)
            print(key,"".join(tabs),": ",value)
            
            
def test():
    acam = ArvCam("EVT-HB-1800SM-640002")
    acam.dev_open()
    
    print(acam.get_region())
    print(acam.get_payload())
    print(acam.get_pixel_format())
    print(acam.get_exposure_time_us())
    print(acam.get_frame_rate_hz())
    
    acam.cap_start()
    
    for i in range(5):
        buffer = acam.get_data()
        print("got data len ", len(buffer), acam.get_status())

    acam.cap_stop()

    
if __name__ == "__main__":
    # test()
    import pydcam.config
    from pydcam.utils.print import print_dict
    HERE = Path(__file__).parent
    # config = pydcam.config.read_config(HERE/"../../cameras/Teledyne-Nano.toml")
    config = pydcam.config.read_config(HERE/"../../cameras/EVT_canapy.toml")
    print("Starting camera")
    # acam = ArvCam("EVT-HB-1800SM-640002")
    acam = ArvCam(config)
    acam.dev_open()
    
    camera = acam.camhandle
    # features = get_features(camera,"Root")
    # print_dict(features)
    
    # exp = get_feature(camera, "ExposureTime")
    exp = get_feature(camera, "Exposure")
    # fr = get_feature(camera, "AcquisitionFrameRate")
    fr = get_feature(camera, "FrameRate")
    wdt = get_feature(camera, "Width")
    hgt = get_feature(camera, "Height")
    xoff = get_feature(camera, "OffsetX")
    yoff = get_feature(camera, "OffsetY")
    gain = get_feature(camera, "Gain")
    
    print(exp)
    print(fr)
    print(wdt)
    print(hgt)
    print(xoff)
    print(yoff)
    print(gain)
    
    wdth = set_feature(camera, "Width", 1920)
    hgt = set_feature(camera, "Height", 1080)
    fr = set_feature(camera, "AcquisitionFrameRate", 30)
    exp = set_feature(camera, "ExposureTime", 15000)
    
    print(wdth)
    print(hgt)
    print(fr)
    print(exp)