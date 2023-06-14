




"""
The interface to the Arvais API for my cam reader program
"""

import threading
import time
try:
    import gi
    gi.require_version ('Aravis', '0.8')
    from gi.repository import Aravis
except Exception as e:
    print(e)
    print("No Aravis available")


def get_gc_features(genicam, name):
    node = genicam.get_node(name)
    if isinstance(node, Aravis.GcCategory):
        retval = {}
        features = node.get_features()
        for f in features:
            retval[f] = get_gc_features(genicam, f)
        return retval
    elif isinstance(node, (Aravis.GcStringRegNode,Aravis.GcIntegerNode,Aravis.GcBoolean,Aravis.GcEnumeration)):
        return node.get_value()
    
def get_features(camera, name):
    device = camera.get_device ()
    genicam = device.get_genicam ()
    return get_gc_features(genicam,name)

def set_feature(camera, name, value):
    device = camera.get_device ()
    genicam = device.get_genicam ()
    node = genicam.get_node(name)
    node.set_value(value)
    
def set_feature_from_string(camera, name, value):
	device = camera.get_device ()
	genicam = device.get_genicam ()
	node = genicam.get_node(name)
	node.set_value_from_string(value)

class ArvCam:
    def __init__(self, iDevice=None):
        self.iDevice = iDevice
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

    def dev_open(self, iDevice=None):
        if iDevice is not None:
            self.iDevice = iDevice
        
        try:
            self.camhandle = Aravis.Camera.new (self.iDevice)
            self.camhandle.set_integer("FrameRate",10)
            self.camhandle.set_region (336,428,400,400)
            self.camhandle.set_integer ("Exposure", 5000)
            self.camhandle.set_pixel_format (Aravis.PIXEL_FORMAT_MONO_8)
            self.camhandle.gv_auto_packet_size()
            self.camhandle.gv_set_packet_size(9000)
            self.camhandle.gv_set_stream_options(Aravis.GvStreamOption.NONE)
            self.camhandle.gv_select_stream_channel(-1)
            self.camhandle.gv_set_packet_delay(-1)
        except Exception as e:
            print(e)
            return False
        
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

    def prop_set_defaults(self):
        cmds = {
            # "GevSCPSPacketSize" : 9000,
            "FrameRate" : 10,
            "Exposure" : 5000,
            "PixelFormat" : "Mono8",
            "Gain" : 500,
            "TriggerMode" : "Off",
            "OffsetX": 0,
            "OffsetY": 0,
            "Width": 600,
            "Height": 600,
        }

        for name,value in cmds.items():
            if isinstance(value,int):
                print(f"setting {name} to {value}")
                self.camhandle.set_integer(name,value)
            elif isinstance(value, str):
                print(f"setting {name} to {value}")
                set_feature_from_string(self.camhandle,name,value)
            
    def prop_setfromdict(self, pdict:dict):
        for key,value in pdict.items():
            self.prop_setvalue(key,value)
        
    def prop_setvalue(self, name, value):
        if self.is_opened():
            set_feature(self.camhandle, name, value)
            
    def get_info(self):
        keys = ['DeviceVendorName','DeviceModelName','DeviceVersion','DeviceSerialNumber','DeviceFirmwareVersion','DeviceUserName']
        details = self.get_info_detail()
        return {key:details[key] for key in keys}

    def get_info_detail(self):
        return get_features(self.camhandle, "DeviceInformation")
    
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
    
    def set_region(self, x, y, width, height):
        if self.check_integer("Width",width) and self.check_integer("Height",height) and self.check_integer("OffsetX",x) and self.check_integer("OffsetY",y):
            self.camhandle.set_region(x,y,width,height)
            print("setting region to ",x,y,width,height)
        else:
            print("Region Error")
    
    def get_payload(self):
        return self.camhandle.get_payload()
    
    def get_pixel_format(self):
        return self.camhandle.get_pixel_format_as_string()
    
    def get_exposure_time(self):
        return float(self.camhandle.get_integer("Exposure"))/1e6
    
    def set_exposure(self, exp_time):
        bounds = self.camhandle.get_integer_bounds("Exposure")
        mus = int(exp_time*1e6)
        if mus < bounds.min or mus > bounds.max:
            print("exp time error")
            return
        print("setting aravis exp time to ", mus)
        return self.camhandle.set_integer("Exposure", int(exp_time*1e6))
    
    def get_frame_rate(self):
        return self.camhandle.get_integer("FrameRate")
    
    def set_frame_rate(self, fr):
        self.camhandle.set_integer("FrameRate", int(fr))

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
        for i in range(0,10):
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
        if self.stream is not None: self.stream.stop_thread(True)
    
def print_info(arvcam:ArvCam):
    keys = ['DeviceVendorName','DeviceModelName','DeviceVersion','DeviceSerialNumber','DeviceFirmwareVersion','DeviceUserName']
    if arvcam.is_opened:
        features = get_features(arvcam.camhandle,"DeviceInformation")
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
    print(acam.get_exposure_time())
    print(acam.get_frame_rate())
    
    acam.cap_start()
    
    for i in range(5):
        buffer = acam.get_data()
        print("got data len ", len(buffer), acam.get_status())

    acam.cap_stop()

    
if __name__ == "__main__":
    # test()
    print("Starting camera")
    acam = ArvCam("EVT-HB-1800SM-640002")
    acam.dev_open()
    
    camera = acam.camhandle
    features = get_features(camera,"Root")