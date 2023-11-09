



import asyncio
import time
from pydcam.api import REGIONINFO
from pydcam.api.microgate import MGCam
from pydcam.dcam_reader import pub_worker
from pydcam.utils import LoopRunner, ParamInfo
from pydcam.utils.asyncio_circ_buf import asyncio_buf


class cam_worker:
    def __init__(self, camera:MGCam, dest_buf:asyncio_buf) -> None:
        self.camera = camera
        self.dst_buf = dest_buf

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

        if self.camera is None:
            return
        print("starting cam run")
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

            buf = await LoopRunner.run_in_executor(self.camera.get_data)
            if buf is None:
                continue

            try:
                # self.dst_buf.frombuffer(buf, copy=True)
                self.dst_buf.copy_numpy(buf,)
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
        # self.camera.cancel_get()
        await self.wait_until_paused.wait()
        print("cam now paused...")

    def unpause(self):
        self._pause = False
        self.wait_while_paused.set()

    async def stop(self):
        print("pausing cam")
        await self.pause()
        self.go = False
        self.unpause()
        print("cam stopped") 
        
        
class MGReader:
    def __init__(self, mgcam:MGCam):
        self.cam_handle = mgcam
        
        self.thread_buffer_init()
        
        self.running = False
        
    def thread_buffer_init(self):
        width, height = self.cam_handle.get_region()
        dtype = self.cam_handle.get_dtype()

        shape = (int(height),int(width))
                
        self.buffers = asyncio_buf(shape, 10, dtype)
        
        self.publisher = pub_worker(self.buffers)
        self.camera = cam_worker(self.cam_handle, self.buffers)

        self.pubfut = LoopRunner.run_coroutine(self.publisher.run())
        self.camfut = LoopRunner.run_coroutine(self.camera.run())
        
    def resize_thread_buffer(self):

        width, height = self.cam_handle.get_region()
        dtype = self.cam_handle.get_dtype()
        
        shape = (int(height),int(width))

        self.buffers.resize(shape, None, dtype)
        
    def open_camera(self):

        self.resize_thread_buffer()
        
        err = self.cam_handle.capture_start()
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
        self.cam_handle.capture_stop()
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
            
        self.cam_handle.capture_stop()

        print( "PROGRAM END\n" )
        
    def get_info(self):
        return self.cam_handle.get_info() 

    def get_info_detail(self):
        return self.get_info()
        
    async def get_image(self):
        return await self.publisher.oneshot()

    async def get_images(self,n=1):
        return await self.publisher.multishot(n,ndarray=True)
    
    def get_running(self):
        return bool(self.running)
    
    def get_exposure(self):
        return 0
        """In seconds"""
        return self.cam_handle.get_exposure_time()
    
    def set_exposure(self, exp_time):
        return
        """In seconds"""
        return self.cam_handle.set_exposure(exp_time)
        
    def set_frame_rate(self, fr):
        return
        return self.cam_handle.set_frame_rate(fr)
    
    def set_gain(self, ga):
        return
        return self.cam_handle.set_gain(ga)
        
    def set_subarray(self, width, height, xoff, yoff):
        return
        self.close_camera()
        self.cam_handle.set_region(xoff,yoff,width,height)
        self.open_camera()
        
    def set_subarray_pos(self, hpos, vpos):
        region = self.cam_handle.get_region()
        self.set_subarray(region.width,region.height,hpos,vpos)
        
    def set_publish(self,value=True):
        self.publisher.set_zmq(value)
    
    def get_window_info_dict(self):
        values = {
            REGIONINFO.Width : ParamInfo(self.cam_handle.config['width']),
            REGIONINFO.OffsetX : ParamInfo(),
            REGIONINFO.Height : ParamInfo(self.cam_handle.config['height']),
            REGIONINFO.OffsetY : ParamInfo(),
            REGIONINFO.Exposure : ParamInfo(),
            REGIONINFO.FrameRate : ParamInfo(),
        }
        return values
    
    def get_window_info(self):
        return list(self.get_window_info_dict().values())
    
    def register_callback(self, func):
        return self.publisher.register(func)

    def deregister_callback(self, fid):
        self.publisher.deregister(fid)