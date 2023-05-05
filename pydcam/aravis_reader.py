
import asyncio
from pydcam import LoopRunner
from pydcam.utils import ParamInfo
from pydcam.api import REGIONINFO
from pydcam.api.aravis import ArvCam, print_info
from pydcam.utils.asyncio_circ_buf import asyncio_buf

from pydcam.dcam_reader import pub_worker
import time

class cam_worker:
    def __init__(self, acam:ArvCam, dst_buf:asyncio_buf):
        super().__init__()
        self.acam = acam
        self.dst_buf = dst_buf

        self.go = True
        self._pause = True
        self._future = None

        self.fps_cb = None

        self.wait_while_paused = asyncio.Event()
        self.wait_while_paused.clear()
        self.wait_until_paused = asyncio.Event()
        self.wait_until_paused.set()
    
    def set_fps_cb(self,func):
        if callable(func):
            self.fps_cb = func

    async def run(self):

        if self.acam is None:
            return
        print("satrting cam run")
        lastupdate = time.time()

        while(self.go):
            
            # check for pause flag
            if self._pause:
                self.wait_until_paused.set()
                print("paused cam coro")
                await self.wait_while_paused.wait()
                print("unpaused cam coro")
                self.wait_until_paused.clear()

            if not self.go:
                print("ending cam thread")
                return None
            
            buf = await LoopRunner.run_in_executor(self.acam.get_data)
            if buf is None:
                continue

            try:
                self.dst_buf.frombuffer(buf)
            except Exception as e:
                print(e)

            now = time.time()
            try:
                self.fps = 1/(now-lastupdate)
            except ZeroDivisionError as e:
                print(e)
            else:
                if self.fps_cb is not None:
                    self.fps_cb(self.fps)
            lastupdate = now
        print("ending cam run")

    async def pause(self):
        self.wait_while_paused.clear()
        self._pause = True
        self.acam.cancel_get()
        await self.wait_until_paused.wait()
        print("cam now paused...")

    def unpause(self):
        self._pause = False
        self.wait_while_paused.set()

    async def stop(self):
        print("pauing cam")
        await self.pause()
        self.go = False
        self.unpause()
        print("cam stopped")

class AravisReader:
    def __init__(self, arvcam:ArvCam) -> None:
        self.acam = arvcam
        
        print_info(self.acam)
        
        self.thread_buffer_init()
        
        self.running = False
        
    def thread_buffer_init(self):
        xoff, yoff, width, height = self.acam.get_region()
        payload = self.acam.get_payload()
        pxltype = self.acam.get_pixel_format()
        exptime = self.acam.get_exposure_time()
        frate = self.acam.get_frame_rate()
        
        shape = (int(height),int(width))
        
        dtype = "uint8" if pxltype == "Mono8" else "uint12"
        
        self.buffers = asyncio_buf(shape, 10, dtype)
        
        self.publisher = pub_worker(self.buffers)
        self.camera = cam_worker(self.acam, self.buffers)

        self.pubfut = LoopRunner.run_coroutine(self.publisher.run())
        self.camfut = LoopRunner.run_coroutine(self.camera.run())
        
    def resize_thread_buffer(self):

        xoff, yoff, width, height = self.acam.get_region()
        pxltype = self.acam.get_pixel_format()
        shape = (int(height),int(width))

        dtype = "uint8" if pxltype == "Mono8" else "uint12"

        self.buffers.resize(shape, None, dtype)
        
    def open_camera(self):

        self.resize_thread_buffer()

        err = self.acam.cap_start()
        if err is False:
            print(f"Error in cap_start()")
        else:
            print( "Start Capture" )
            LoopRunner.call_soon(self.publisher.unpause)
            LoopRunner.call_soon(self.camera.unpause)
            self.running = True
            print("CAPSTARTED")

    def close_camera(self):

        print("CLOSING")

        pubfut = LoopRunner.run_coroutine(self.publisher.pause())
        camfut = LoopRunner.run_coroutine(self.camera.pause())

        try:
            pubfut.result()
        except Exception as e:
            print(e)
        try:
            camfut.result()
        except Exception as e:
            print(e)
        # stop capture
        self.acam.cap_stop()

        self.running = False

        print( "PROGRAM PAUSE" )
        
    def quit(self):
                
        print("Stopping publisher thread...")
        pubfut = LoopRunner.run_coroutine(self.publisher.stop())
        print("Stopping camera thread...")
        camfut = LoopRunner.run_coroutine(self.camera.stop())
        
        print("waiting for threads")
        pubfut.result()
        camfut.result()

        try:
            res = self.pubfut.result()
        except asyncio.CancelledError as e:
            print("Cancelled: ",e)
        except Exception as e:
            print(e)
        else:
            print(res)
        finally:
            print("pub finished")
        try:
            res = self.camfut.result()
        except asyncio.CancelledError as e:
            print("Cancelled: ",e)
        except Exception as e:
            print(e)
        else:
            print(res)
        finally:
            print("cam finished")

        # release buffer
        print("Releasing buffer...")
        self.acam.cap_stop()

        print( "PROGRAM END\n" )
        
    def get_info(self):
        return self.acam.get_info() 

    def get_info_detail(self):
        return self.acam.get_info_detail()
        
    async def get_image(self):
        return await self.publisher.oneshot()

    async def get_images(self,n=1):
        return await self.publisher.multishot(n,ndarray=True)
    
    def get_running(self):
        return bool(self.running)
    
    def get_exposure(self):
        """In seconds"""
        return self.acam.get_exposure_time()
    
    def set_exposure(self, exp_time):
        """In seconds"""
        return self.acam.set_exposure(exp_time)
        
    def set_frame_rate(self, fr):
        return self.acam.set_frame_rate(fr)
        
    def set_subarray(self, width, height, xoff, yoff):
        self.close_camera()
        self.acam.set_region(xoff,yoff,width,height)
        self.open_camera()
        
    def set_subarray_pos(self, hpos, vpos):
        region = self.acam.get_region()
        self.set_subarray(region.width,region.height,hpos,vpos)
        
    def set_publish(self,value=True):
        self.publisher.set_zmq(value)
    
    def get_window_info_dict(self):
        keys = [ REGIONINFO.Width, REGIONINFO.OffsetX, REGIONINFO.Height, REGIONINFO.OffsetY, REGIONINFO.Exposure, REGIONINFO.FrameRate]
        ids = [ "Width", "OffsetX", "Height", "OffsetY", "Exposure", "FrameRate"]
        values = {}
        for tid,key in zip(ids,keys):
            value = self.acam.get_integer(tid)
            vmin, vmax = self.acam.get_integer_bounds(tid)
            step = self.acam.get_integer_step(tid)
            values[key] = ParamInfo(value,vmin,vmax,step)
        exp = values[REGIONINFO.Exposure]
        values[REGIONINFO.Exposure] = ParamInfo(exp.value/1e6, exp.min/1e6, exp.max/1e6, exp.step/1e6)
        return values
    
    def get_window_info(self):
        return list(self.get_window_info_dict().values())
    
    def register_callback(self, func):
        return self.publisher.register(func)

    def deregister_callback(self, fid):
        self.publisher.deregister(fid)
        
        
        
if __name__ == "__main__":
    import sys
    from pydcam import LoopRunner
    from pathlib import Path
    from pydcam import open_config
    from pydcam.api import OpenAravis
    from pydcam.utils.zmq_pubsub import zmq_publisher
    from pydcam.utils.shmem import shmem_publisher
    iDevice = "EVT-HB-1800SM-640002"

    fname = None
    if len(sys.argv) > 1:
        fname = Path(sys.argv[1]).resolve()


    with LoopRunner() as EL:
        with OpenAravis(iDevice) as dcam:


            dcam.prop_set_defaults()

            camreader = AravisReader(dcam)
            # this_zmq = zmq_publisher()
            this_zmq = shmem_publisher(size=1600*1096)
            fid = camreader.register_callback(this_zmq.publish)

            camreader.open_camera()

            while 1:
                try:
                    x = input("Type exp X, where X is the exposure time:\nor type config to configure from file:\n")
                    if x[:3] == "exp":
                        try:
                            et = float(x[4:])
                        except Exception as e:
                            print("wrong type for exposure time")
                            continue
                        camreader.set_exposure(et)
                    elif x[:6] == "config":
                        init_dict = open_config()
                        if init_dict: dcam.prop_setfromdict(init_dict)
                except KeyboardInterrupt as e:
                    print("Finished with ctrl-C")
                    break

            print("closing")
            camreader.deregister_callback(fid)
            camreader.quit()
            this_zmq.close()
            
    print("EXITING")