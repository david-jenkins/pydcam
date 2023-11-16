#!/usr/bin/env python3

"""
    Hamamatsu DCAM_API ctypes python interface
    ================
    A ctypes based interface to Hamamatsu cameras using the DCAM API.

    This imports some common functions, makes some common defines and implements some of
    the C++ examples from the DCAM SDK4.
"""
import asyncio
import time
import numpy
from pydcam import LoopRunner
from pydcam.utils import ParamInfo, LoopRunner
from pydcam.api import REGIONINFO
# from pydcam.api.dcam import *

from pydcam.utils.asyncio_circ_buf import asyncio_buf
from pydcam.utils.cb_thread import CallbackThread
from pydcam.utils.cb_asyncio import CallbackCoroutine

from pydcam.dcam_reader import pub_worker, my_wait

from ctypes import c_void_p

class cam_sim:
    def __init__(self, dst_buf:asyncio_buf, im_size=(200,200)):
        super().__init__()

        self.dst_buf = dst_buf

        self.go = True
        self._pause = True

        self.fps_cb = None

        self.exptime = 1

        self.imsize = im_size

        self.wait_while_paused = asyncio.Event()
        self.wait_while_paused.clear()
        self.wait_until_paused = asyncio.Event()
        self.wait_until_paused.set()
        
        self.wait_task = None
    
    def set_fps_cb(self,func):
        if callable(func):
            self.fps_cb = func

    async def run(self):

        self.resize(self.imsize)
        cnt = 0
        lastupdate = time.time()
        while(self.go):
            # wait image
            if self._pause:
                self.wait_until_paused.set()
                print("paused cam coro")
                await self.wait_while_paused.wait()
                print("unpaused cam coro")
                self.wait_until_paused.clear()
            if not self.go:
                break
            
            # print("waiting for exp time")
            # if self.exptime > 0.02:
            self.wait_task = asyncio.create_task(my_wait(self.exptime, lastupdate))
            try:
                await self.wait_task
            except asyncio.CancelledError:
                print("Wait cancelled in camera run")
            # now = time.time()
            # print("got frame...")
            temp = self.temp[cnt%100]
            # temp[:,(cnt)%self.imsize[1]] = 2500
            # self.dst_buf.copy_numpy(temp)
            # print("copying buf")
            # try:
            self.dst_buf.copy_from_address(temp.ctypes.data_as(c_void_p), temp.nbytes)
            # except Exception as e:
            #     print(e)
            # print("buf copied")
            # try:
            #     self.dcam.buf_getframe_withnp(-1,self.dst_buf.get_to_fill())
            # except Exception as e:
            #     print(e)
            # else:
            #     self.dst_buf.inc_last_filled()

            now = time.time()
            try:
                self.fps = 1/(now-lastupdate)
            except ZeroDivisionError as e:
                print(e)
            else:
                if self.fps_cb is not None:
                    self.fps_cb(self.fps)
            lastupdate = now
            cnt += 1
        print("camsin run ended")

    async def pause(self):
        self.wait_while_paused.clear()
        self._pause = True
        if self.wait_task is not None:
            self.wait_task.cancel()
        await self.wait_until_paused.wait()

    def unpause(self):
        self._pause = False
        self.wait_while_paused.set()

    async def stop(self):
        await self.pause()
        self.go = False
        self.unpause()

    def resize(self,imdim,n=100):
        self.imsize = imdim
        self.temp = ((numpy.random.random(n*numpy.prod(self.imsize))+0.1)*2000).astype(numpy.int16).reshape((n,*self.imsize))


class OpenSim():
    def __init__(self, config):
        self.config = config

    def __enter__(self):
        return self.config

    def __exit__(self, exc_type, exc_value, traceback):
        return False

class DCamSim():
    def __init__(self, config:dict):

        # set these as default values
        self.exposure = config['exposure']
        self.hsize = config['hsize']
        self.vsize = config['vsize']
        self.hpos = config['hpos']
        self.vpos = config['vpos']

        self.mode = config['mode']

        self.thread_buffer_init()

        self.running = 0

    # def thread_buffer_init(self, imdim):

    #     buf_size = int(imdim[0]*imdim[1]*2)

    #     self.buffers = asyncio_buf(imdim, 10, "uint16")
    #     self.publisher = pub_worker(self.buffers)
    #     self.camera = cam_sim(self.buffers,im_size=imdim)

    #     asyncio.LoopRunner.run_coroutine(self.publisher.run(), get_event_loop())
    #     asyncio.LoopRunner.run_coroutine(self.camera.run(), get_event_loop())
    
    
    def thread_buffer_init(self):

        width = self.hsize
        height = self.vsize
        shape = (int(height),int(width))
        dtype = "uint16"

        self.buffers = asyncio_buf(shape, 10, dtype)
        self.publisher = pub_worker(self.buffers)
        self.camera = cam_sim(self.buffers, im_size=shape)
        
        self.camera.exptime = self.exposure

        self.pubfut = LoopRunner.run_coroutine(self.publisher.run())
        self.pubfut.add_done_callback(print)
        self.camfut = LoopRunner.run_coroutine(self.camera.run())
        self.camfut.add_done_callback(print)
        
    def resize_thread_buffer(self):

        width = self.hsize
        height = self.vsize
        shape = (int(height),int(width))
        dtype = "uint16"

        self.buffers.resize(shape, None, dtype)

    def open_camera(self):
        # start capture
        
        self.resize_thread_buffer()
        
        LoopRunner.call_soon(self.publisher.unpause)
        LoopRunner.call_soon(self.camera.unpause)

        self.running = 1

    def close_camera(self):
        # abort signal to dcamwait_start

        LoopRunner.run_coroutine(self.publisher.pause())
        LoopRunner.run_coroutine(self.camera.pause())

        self.running = 0

        print( "PROGRAM PAUSE" )

    def quit(self):
        print("Stopping publisher thread...")
        pubfut = LoopRunner.run_coroutine(self.publisher.stop())
        print("Stopping camera thread...")
        camfut = LoopRunner.run_coroutine(self.camera.stop())

        # self.publisher.join()
        # self.camera.join()
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

        self.running = 0

        print("PROGRAM END")

    def get_info(self):
        info = {"DeviceModelName":"Sim Camera","DeviceSerialNumber":"Version 1","DeviceBus":"This information is unnecessary"}
        return info

    def get_info_detail(self):
        return self.get_info()

    def set_exposure(self,exp_time):
        self.camera.exptime = exp_time
        
    def set_frame_rate(self, fps):
        self.camera.exptime = 1/fps

    def get_exposure(self):
        return self.camera.exptime

    def set_subarray_pos(self, hpos, vpos):
        self.set_subarray(self.hsize,self.vsize,hpos,vpos)

    def set_subarray_size(self,hsize,vsize):
        self.set_subarray(hsize,vsize,self.hpos,self.vpos)

    def set_subarray(self, hsize, vsize, hpos, vpos):

        self.hsize = hsize
        self.vsize = vsize

        self.close_camera()

        self.camera.resize((vsize,hsize))
        
        self.open_camera()

    def set_publish(self,value=True):
        self.publisher.set_zmq(value)

    def register_callback(self, func):
        return self.publisher.register(func)

    def deregister_callback(self, fid):
        self.publisher.deregister(fid)

    async def get_image(self):
        return await self.publisher.oneshot()

    async def get_images(self,n=1):
        return await self.publisher.multishot(n)

    def get_window_info(self):
        values = [(self.camera.imsize[0],0,2000,1),(2,1,3,1),(self.camera.imsize[1],0,2000,1),(2,1,3,1),(self.camera.exptime,0,10,0.001),(1/self.camera.exptime,0.1,10000,1)]
        values = [ParamInfo(*val) for val in values]
        return values

    def get_window_info_dict(self):
        keys = [ REGIONINFO.Width, REGIONINFO.OffsetX, REGIONINFO.Height, REGIONINFO.OffsetY, REGIONINFO.Exposure, REGIONINFO.FrameRate ]
        # keys = ["SUBARRAYHSIZE","SUBARRAYHPOS","SUBARRAYVSIZE","SUBARRAYVPOS","EXPOSURETIME"]
        values = self.get_window_info()
        return dict(zip(keys,values))

    def get_running(self):
        return self.running

    def reset_buffer_head(self):
        self.buffers.reset_head()
