


import os
import threading
import time
import numpy
import mmap

from matplotlib import pyplot

_SC_PAGE_SIZE = 4096
SENSOR_PACKET_WORDS = 512
POLL_NS = 3333
FSN_S_IDX = 6*4


def makeReorderBufCut(sh=False):
    reorderBuf = numpy.zeros(264*242, dtype=numpy.int64)
    for j in range(264*242):
        amp = j%8
        rowpxl = (j//8)%66
        row = j//(2*264)
        if row==0 or row>119:
            continue
        row+=1
        if amp == 0:
            if rowpxl<6:
                x = 0
            else:
                x = 65-rowpxl+row*264
        elif amp == 1:
            if rowpxl<6:
                x = 0
            else:
                x = 66+rowpxl+row*264 - 12
        elif amp == 2:
            if rowpxl<6:
                x = 0
            else:
                x = 197-rowpxl+row*264 - 12
        elif amp == 3:
            if rowpxl<6:
                x = 0
            else:
                x = 198+rowpxl+row*264 - 24
        elif amp == 4:
            if rowpxl<6:
                x = 0
            else:
                x = (264*241+198)+rowpxl-row*264 - 24
        elif amp == 5:
            if rowpxl<6:
                x = 0
            else:
                x = (264*241+197)-rowpxl-row*264 - 12
        elif amp == 6:
            if rowpxl<6:
                x = 0
            else:
                x = (264*241+66)+rowpxl-row*264 - 12
        elif amp == 7:
            if rowpxl<6:
                x = 0
            else:
                x = (264*241+65)-rowpxl-row*264
        if sh and (j+(row-1)*4)<264*242:
            k = j+(row-1)*4
        else:
            k = j
        reorderBuf[k] = x

    return reorderBuf

class MGCam:
    def __init__(self, config:dict):
        self.config = config
        self.device_id = config['camera']
        self.camhandle = None
        self.dmaIdx = config['dmaIdx']
        self.width = config['width']
        self.height = config['height']
        self.bytespp = config['bytespp']
        self.npxls = self.width*self.height
        self.fpga_mem_size = _SC_PAGE_SIZE*((self.npxls*self.bytespp+32+_SC_PAGE_SIZE-1)//_SC_PAGE_SIZE)
        self.sensor_pckts = (self.bytespp*self.npxls+1023)//1024
        self.newdata = threading.Event()
        self.newdata.clear()
        self.not_cancelled = True
        
        self.image = numpy.zeros((self.height,self.width), dtype=numpy.dtype(config['dtype']))
        self.flat_image = self.image.view()
        self.flat_image.shape = numpy.prod(self.image.shape)
        
        self.FSN = numpy.zeros(1, dtype=numpy.int32)
        self.char_FSN = self.FSN.view(numpy.uint8)
        
        self.go = True
        
        if config['name'] == "OCAM1":
            self.LUT = makeReorderBufCut()
        else:
            self.LUT = None
        # self.LUT = None
        
        self.capture_thread = None
        
    def is_opened(self):
        return bool(self.camhandle)
    
    def device_open(self):
        # here we open the memap region
        print("opening file...")
        try:
            self.fd = open("/dev/uXLink_PCIe",mode="rb+",buffering=0)
        except Exception as e:
            print(e)
            return False
        print("Opened file")
        try:
            # self.sensor_region = numpy.memmap("/dev/uXLink_PCIe", dtype=numpy.uint8, mode='r+', offset=_SC_PAGE_SIZE*self.dmaIdx, shape=self.fpga_mem_size)
            self.mmap = mmap.mmap(self.fd.fileno(), self.fpga_mem_size, flags=mmap.MAP_SHARED | mmap.MAP_POPULATE, prot=mmap.PROT_WRITE|mmap.PROT_READ, offset=_SC_PAGE_SIZE*self.dmaIdx)
        except Exception as e:
            print(e)
            self.fd.close()
            return False
        print("opened mmap")
        try:
            # self.sensor_region = numpy.ndarray.__new__(clsshape=(self.fpga_mem_size,), dtype=numpy.uint8, buffer=self.mmap,)
            self.sensor_region = numpy.ndarray(shape=(self.fpga_mem_size,), dtype=numpy.uint8, buffer=self.mmap)
        except Exception as e:
            print(e)
            self.mmap.close()
            self.fd.close()
            return False
        else:
            self.im_data = self.sensor_region[FSN_S_IDX+4+4:].view(numpy.dtype(self.config['dtype']))[:self.npxls]
            # self.im_show = self.im_data[:self.npxls].view()
            # self.im_show.shape = self.height,self.width
            # print(f"{self.im_data[self.npxls-1]=}")
            # print(f"{self.im_show[self.height-1,self.width-1]=}")
            # pyplot.imshow(self.im_show,vmax=5000)
            # pyplot.show()
            return True
        
    def get_region(self):
        return self.width, self.height
    
    def get_bytespp(self):
        return self.config['bytespp']
    
    def get_dtype(self):
        return self.config['dtype']
    
    def get_info(self):
        values = {
            'DeviceVendorName' : "Microgate",
            'DeviceModelName' : "IM",
            'DeviceVersion' : 0.1,
            'DeviceSerialNumber' : '001',
            'DeviceFirmwareVersion' : 0.1,
            'DeviceUserName' : self.config['name']
        }
        return values

    def get_data(self, timeout=5):
        retval = self.newdata.wait(timeout)
        self.newdata.clear()
        if retval and self.not_cancelled:
            return self.image
        else:
            self.not_cancelled = True
            return None

    def sensor_thread(self):
        
        print(f"Max packets for this camera = {self.sensor_pckts}")
        
        print("thread go =", self.go)
        cnt = 0
        
        print(f"{self.im_data[self.npxls-1]=}")
        self.im_data[self.npxls-1] = -1

        while self.go:
            # start getting a new frame

            cnt = 0
            # poll on the memory locations
            while (self.go and self.im_data[self.npxls-1] == -1 and cnt<10000):
                cnt+=1
                time.sleep(0.00000001)

            if cnt>=10000:
                print("Timeout in wait for pixels")
                print(f"{self.im_data[self.npxls-1]=}")
                continue
            if self.go==0: break

            # memcpy(&(camstr->imgdata)[sizeof(unsigned short)*(thread_struct->npxlsCum+imag_idxs[this_chunk])],&im_data[imag_idxs[this_chunk]],sizeof(unsigned short)*(imag_idxs[this_chunk+1]-imag_idxs[this_chunk]));
            if self.LUT is not None:
                self.flat_image[self.LUT] = self.im_data[:]
            else:
                self.flat_image[:] = self.im_data[:]

            self.newdata.set()
            if self.go==0: break
            
            # memcpy(&thread_struct->FSN, &thread_struct->sensor_ptr[FSN_S_IDX], sizeof(unsigned int));
            self.char_FSN[:] = self.sensor_region[FSN_S_IDX:FSN_S_IDX+self.FSN.dtype.itemsize]

            # reset FSN flag
            self.im_data[self.npxls-1] = -1

        print("thread go =",self.go)
        print("Thread ending")

    def capture_start(self):
        if self.capture_thread is None or not self.capture_thread.is_alive():
            self.capture_thread = threading.Thread(target=self.sensor_thread)
            self.go = True
            self.capture_thread.start()
            
    def capture_stop(self):
        if self.capture_thread is not None and self.capture_thread.is_alive():
            self.go = False
            self.capture_thread.join()
    
    # def set_properties_defaults(self):
    #     pass
            
    # def set_properties_fromdict(self, pdict:dict):
    #     pass
        
    # def set_property_value(self, name, value):
    #     pass
            
    # def get_info(self):
    #     pass

    # def get_info_detail(self):
    #     pass
    
    # def get_region(self):
    #     pass
    
    # def get_integer(self, name):
    #     pass

    # def get_integer_bounds(self, name):
    #     pass
    
    # def get_integer_step(self, name):
    #     pass
    
    # def check_integer(self, name, value):
    #     pass
    
    # def set_region(self, x, y, width, height):
    #     pass
    
    # def get_payload(self):
    #     pass
    
    # def get_pixelformat(self):
    #     pass
    
    # def get_exposuretime(self):
    #     pass
    
    # def set_exposure(self, exp_time):
    #     pass
    
    # def get_framerate(self):
    #     pass
    
    # def set_framerate(self, fr):
    #     pass
        
    # def set_gain(self, ga):
    #     pass

    # def get_data(self, timeout=5):
    #     pass
        
    # def get_status(self):
    #     pass

    # def cancel_get(self):
    #     pass

    # def buffer_callback(self, user_data, cb_type, buffer):
    #     pass
    
    # def capture_start(self):
    #     pass
    
    # def capture_stop(self):
    #     pass
        