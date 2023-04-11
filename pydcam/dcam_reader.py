#!/usr/bin/env python3

"""
    Hamamatsu DCAM_API ctypes python interface
    ================
    A ctypes based interface to Hamamatsu cameras using the DCAM API.

    This imports some common functions, makes some common defines and implements some of
    the C++ examples from the DCAM SDK4.
"""
import asyncio
from pathlib import Path
import sys
import pydcam
import time
import threading
import numpy

from pydcam.api.dcam import *
import pydcam.api.dcam_extra as dapi

from pydcam.utils.asyncio_circ_buf import asyncio_buf
from pydcam.utils.cb_thread import CallbackThread
from pydcam.utils.cb_asyncio import CallbackCoroutine



async def my_wait(secs,start_time=None):
    if start_time is None:
        await asyncio.sleep(secs)
    else:
        waittime = secs-(time.time()-start_time)
        if waittime > 0.01:
            await asyncio.sleep(waittime)
        else:
            return

def busy_wait(secs,start_time=None):
    if start_time is None:
        # time.sleep(secs)
        start_time = time.time()
    while time.time() < start_time + secs:
        pass

class pub_worker(CallbackCoroutine):
    def __init__(self, src_buf:asyncio_buf, ratelimit=0):
        super().__init__(startpaused=True, ratelimit=ratelimit)
        self.src_buf = src_buf

    async def get_data(self):
        return await self.src_buf.get_latest(block=1, copy=1)

    async def pause(self):
        self.wait_while_paused.clear()
        self._pause = True
        self.src_buf.cancel_wait()
        await self.wait_until_paused.wait()

    def stop(self):
        super().stop()
        self.src_buf.cancel_wait()

class cam_worker:
    def __init__(self, dcam:Dcam, dst_buf:asyncio_buf):
        super().__init__()
        self.dcam = dcam
        self.dst_buf = dst_buf

        self.go = True
        self._pause = True

        # wait start param
        # self.dcam.wait_init(DCAMWAIT_CAPEVENT.FRAMEREADY, 3000)

        self.fps_cb = None

        self.wait_while_paused = asyncio.Event()
        self.wait_while_paused.clear()
        self.wait_until_paused = asyncio.Event()
        self.wait_until_paused.set()
    
    def set_fps_cb(self,func):
        if callable(func):
            self.fps_cb = func

    async def run(self):

        if self.dcam is None:
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
                break
            # retval = self.dcam.wait_again()
            loop = asyncio.get_event_loop()
            retval = await loop.run_in_executor(None, self.dcam.wait_capevent_frameready, 3000)
            if retval is False:
                if self.dcam.lasterr() == DCAMERR.ABORT:
                    print("received the abort signal")
                else:
                    print(f"ERROR in wait_again() -> {self.dcam.lasterr().name}")
                continue
        
            # get frame by grabbing numpy array and copying into dst_buf
            # arr = self.dcam.buf_getlastframedata()
            # if arr is False:
            #     print(f"Error in buf_getlastframedata() - > {self.dcam.lasterr().name}")
            #     continue
            # self.dst_buf.copy_numpy(arr)

            # get frame by copying directly into buffer
            # try:
            #     self.dcam.buf_getframe_withnp(-1, self.dst_buf.get_to_fill())
            # except Exception as e:
            #     print(e)
            # else:
            #     self.dst_buf.inc_last_filled()

            # get frame with dcam lockframe
            arr = self.dcam.buf_getpointer(-1)
            if arr is False:
                print(f"Error in buf_getlastframedata() - > {self.dcam.lasterr().name}")
                continue
            try:
                self.dst_buf.copy_from_address(arr.buf, arr.rowbytes*arr.height)
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
        self.dcam.wait_abort()
        await self.wait_until_paused.wait()

    def unpause(self):
        self._pause = False
        self.wait_while_paused.set()

    def stop(self):
        self.go = False
        self.unpause()
        self.dcam.wait_abort()

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
            
            print("waiting for exp time")
            # if self.exptime > 0.02:
            await my_wait(self.exptime, lastupdate)
            # now = time.time()
            # print("got frame...")
            temp = self.temp[cnt%100]
            # temp[:,(cnt)%self.imsize[1]] = 2500
            # self.dst_buf.copy_numpy(temp)
            print("copying buf")
            # try:
            self.dst_buf.copy_from_address(temp.ctypes.data_as(c_void_p), temp.nbytes)
            # except Exception as e:
            #     print(e)
            print("buf copied")
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
        self.dcam.wait_abort()
        await self.wait_until_paused.wait()

    def unpause(self):
        self._pause = False
        self.wait_while_paused.set()

    def stop(self):
        self.go = False
        self.unpause()

    def resize(self,imdim,n=100):
        self.imsize = imdim
        self.temp = ((numpy.random.random(n*numpy.prod(self.imsize))+0.1)*2000).astype(numpy.int16).reshape((n,*self.imsize))


class DCamReader():
    def __init__(self, dcam:Dcam):

        self.dcam = dcam

        # show device information
        self.dcamdev_info = dapi.dcamcon_show_dcamdev_info( self.dcam )

        print(self.dcamdev_info)

        self.thread_buffer_init()

        self.running = 0

    def thread_buffer_init(self):
        framebytes = self.dcam.prop_getvalue(DCAM_IDPROP.BUFFER_FRAMEBYTES)
        width = self.dcam.prop_getvalue(DCAM_IDPROP.IMAGE_WIDTH)
        height = self.dcam.prop_getvalue(DCAM_IDPROP.IMAGE_HEIGHT)
        pxltype = self.dcam.prop_getvalue(DCAM_IDPROP.IMAGE_PIXELTYPE)
        shape = (int(height),int(width))
        if framebytes != width*height*pxltype:
            print(f"ERROR in buffer init -> {framebytes} != {width*height*pxltype}")
            sys.exit()
        dtype = "uint16" if pxltype == 2 else "uint8"
        print("dtype = ",dtype,pxltype)
        self.buffers = asyncio_buf(shape, 10, dtype)
        self.publisher = pub_worker(self.buffers)
        self.camera = cam_worker(self.dcam, self.buffers)

        # self.event_loop = asyncio.new_event_loop()
        # asyncio.set_event_loop(self.event_loop)
        # self.event_loop.run_forever()
        # asyncio.run()
        # self.event_thread = threading.Thread(target=self.event_loop.run_until_complete, args=(self.run_coros(),))
        # self.event_thread.start()
        asyncio.run_coroutine_threadsafe(self.publisher.run(), pydcam.EVENT_LOOP)
        asyncio.run_coroutine_threadsafe(self.camera.run(), pydcam.EVENT_LOOP)

    def resize_thread_buffer(self):

        framebytes = self.dcam.prop_getvalue(DCAM_IDPROP.BUFFER_FRAMEBYTES)
        width = self.dcam.prop_getvalue(DCAM_IDPROP.IMAGE_WIDTH)
        height = self.dcam.prop_getvalue(DCAM_IDPROP.IMAGE_HEIGHT)
        pxltype = self.dcam.prop_getvalue(DCAM_IDPROP.IMAGE_PIXELTYPE)
        shape = (int(height),int(width))
        if framebytes != width*height*pxltype:
            print(f"ERROR in buffer init -> {framebytes} != {width*height*pxltype}")
            return 
        dtype = "uint16" if pxltype == 2 else "uint8"
        print("dtype = ",dtype,pxltype)

        self.buffers.resize(shape, None, dtype)

    def open_camera(self):
        # start capture
        err = self.dcam.buf_alloc(3)

        if err is False:
            print(f"ERROR in buf_alloc() -> {self.dcam.lasterr().name}" )
            return

        self.resize_thread_buffer()

        bufinfo = self.dcam.buf_get_info()
        print("BUFINFO:",bufinfo.width,bufinfo.height)
        err = self.dcam.cap_start()
        if err is False:
            print(f"Error in cap_start() -> {self.dcam.lasterr().name}")
        else:
            print( "Start Capture" )
            pydcam.EVENT_LOOP.call_soon_threadsafe(self.publisher.unpause)
            pydcam.EVENT_LOOP.call_soon_threadsafe(self.camera.unpause)
            self.running = 1

    def close_camera(self):

        asyncio.run_coroutine_threadsafe(self.publisher.pause(), pydcam.EVENT_LOOP)
        asyncio.run_coroutine_threadsafe(self.camera.pause(), pydcam.EVENT_LOOP)

        # stop capture
        self.dcam.cap_stop()

        self.dcam.buf_release()

        self.running = 0

        print( "PROGRAM PAUSE" )


    def quit(self):
        print("Stopping publisher thread...")
        pydcam.EVENT_LOOP.call_soon_threadsafe(self.publisher.stop)
        print("Stopping camera thread...")
        pydcam.EVENT_LOOP.call_soon_threadsafe(self.camera.stop)

        # print("Joining publisher thread...")
        # self.publisher.join()
        # print("Joining camera thread...")
        # self.camera.join()

        # release buffer
        print("Releasing buffer...")
        self.dcam.buf_release()

        print( "PROGRAM END\n" )

    def get_info(self):
        return dapi.dcamcon_show_dcamdev_info( self.dcam )

    def get_info_detail(self):
        return dapi.dcamcon_show_dcamdev_info_detail( self.dcam )

    def set_exposure(self, exp_time):
        idprop = DCAM_IDPROP.EXPOSURETIME
        fValue = exp_time
        ret = self.dcam.prop_setgetvalue(idprop, fValue, verbose=True)

    def get_exposure(self):
        return self.dcam.prop_getvalue(DCAM_IDPROP.EXPOSURETIME)

    def set_subarray_pos(self, hpos, vpos):

        ret = self.dcam.prop_getvalue(DCAM_IDPROP.SUBARRAYMODE)

        if ret is False:
            print(f"Error in prop_getvalue(DCAM_IDPROP.SUBARRAYMODE) -> {self.dcam.lasterr().name}")
            return
        elif ret == 1.0:
            print("Not in subarray mode, can't change pos anyway")
            return

        ret = self.dcam.prop_setgetvalue(DCAM_IDPROP.SUBARRAYHPOS, hpos, verbose=True)
        ret = self.dcam.prop_setgetvalue(DCAM_IDPROP.SUBARRAYVPOS, vpos, verbose=True)


    def set_subarray_size(self, hsize, vsize):

        was_running = self.get_running()

        ret = self.dcam.prop_getvalue(DCAM_IDPROP.SUBARRAYMODE)
        
        if ret is False:
            print(f"Error in prop_getvalue(DCAM_IDPROP.SUBARRAYMODE) -> {self.dcam.lasterr().name}")
            return
        elif ret == DCAMPROP.MODE.OFF:
            ret = self.dcam.prop_setgetvalue(DCAM_IDPROP.SUBARRAYMODE, DCAMPROP.MODE.ON, verbose=True)
            if ret is False: return

        self.close_camera()

        ret = self.dcam.prop_setgetvalue(DCAM_IDPROP.SUBARRAYHSIZE, hsize, verbose=True)
        ret = self.dcam.prop_setgetvalue(DCAM_IDPROP.SUBARRAYVSIZE, vsize, verbose=True)

        if was_running: self.open_camera()


    def set_subarray(self, hsize, vsize, hpos, vpos):

        was_running = self.get_running()

        value_min_max = self.get_window_info_dict()

        self.close_camera()

        ret = self.dcam.prop_setgetvalue(DCAM_IDPROP.SUBARRAYMODE, DCAMPROP.MODE.ON, verbose=True)

        if ret is False:
            if was_running: self.open_camera()
            return
        else:
            print("Subarray mode on")

        try:
            print(f"Setting window to {hsize}x{vsize} at {hpos},{vpos}")
            print(f"value_min_max {value_min_max['SUBARRAYHSIZE'][0]}x{value_min_max['SUBARRAYVSIZE'][0]} at {value_min_max['SUBARRAYHPOS'][0]},{value_min_max['SUBARRAYVPOS'][0]}")
            print(f"Min {value_min_max['SUBARRAYHSIZE'][1]}x{value_min_max['SUBARRAYVSIZE'][1]} at {value_min_max['SUBARRAYHPOS'][1]},{value_min_max['SUBARRAYVPOS'][1]}")
            print(f"Max {value_min_max['SUBARRAYHSIZE'][2]}x{value_min_max['SUBARRAYVSIZE'][2]} at {value_min_max['SUBARRAYHPOS'][2]},{value_min_max['SUBARRAYVPOS'][2]}")


            if value_min_max["SUBARRAYHSIZE"][0] + hpos > value_min_max["SUBARRAYHSIZE"][2]:
                print("Doing hsize first")
                width = self.dcam.prop_setgetvalue(DCAM_IDPROP.SUBARRAYHSIZE, hsize)
                horiz = self.dcam.prop_setgetvalue(DCAM_IDPROP.SUBARRAYHPOS, hpos)

            else:
                print("Doing hpos first")
                horiz = self.dcam.prop_setgetvalue(DCAM_IDPROP.SUBARRAYHPOS, hpos)
                width = self.dcam.prop_setgetvalue(DCAM_IDPROP.SUBARRAYHSIZE, hsize)
            
            if value_min_max["SUBARRAYVSIZE"][0] + vpos > value_min_max["SUBARRAYVSIZE"][2]:
                print("Doing vsize first")
                height = self.dcam.prop_setgetvalue(DCAM_IDPROP.SUBARRAYVSIZE, vsize)
                vert = self.dcam.prop_setgetvalue(DCAM_IDPROP.SUBARRAYVPOS, vpos)
        
            else:
                print("Doing vpos first")
                vert = self.dcam.prop_setgetvalue(DCAM_IDPROP.SUBARRAYVPOS, vpos)
                height = self.dcam.prop_setgetvalue(DCAM_IDPROP.SUBARRAYVSIZE, vsize)
        finally:
            print(f"Set window to {width}x{height} at {horiz},{vert}")

            if was_running: self.open_camera()

            value_min_max = self.get_window_info_dict()

            print(f"Now {value_min_max['SUBARRAYHSIZE'][0]}x{value_min_max['SUBARRAYVSIZE'][0]} at {value_min_max['SUBARRAYHPOS'][0]},{value_min_max['SUBARRAYVPOS'][0]}")

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
        ids = [ DCAM_IDPROP.SUBARRAYHSIZE, DCAM_IDPROP.SUBARRAYHPOS, DCAM_IDPROP.SUBARRAYVSIZE, DCAM_IDPROP.SUBARRAYVPOS, DCAM_IDPROP.EXPOSURETIME ]
        values = []
        for idprop in ids:
            value, vmin, vmax = self.dcam.prop_getvalueminmax(idprop)
            values.append((value,vmin,vmax))
        return values

    def get_window_info_dict(self):
        ids = [ DCAM_IDPROP.SUBARRAYHSIZE, DCAM_IDPROP.SUBARRAYHPOS, DCAM_IDPROP.SUBARRAYVSIZE, DCAM_IDPROP.SUBARRAYVPOS, DCAM_IDPROP.EXPOSURETIME ]
        values = {}
        for idprop in ids:
            value, vmin, vmax = self.dcam.prop_getvalueminmax(idprop)
            values[idprop.name] = [value,vmin,vmax]
        return values

    def get_running(self):
        return self.running

    def reset_buffer_head(self):
        self.buffers.reset_head()

class DCamSim():
    def __init__(self):

        # set these as default values
        self.exposure = 1.0
        self.hsize = 1024
        self.vsize = 1024
        self.hpos = 512
        self.vpos = 512

        self.mode = 2.0

        self.thread_buffer_init()

        self.running = 0

    # def thread_buffer_init(self, imdim):

    #     buf_size = int(imdim[0]*imdim[1]*2)

    #     self.buffers = asyncio_buf(imdim, 10, "uint16")
    #     self.publisher = pub_worker(self.buffers)
    #     self.camera = cam_sim(self.buffers,im_size=imdim)

    #     asyncio.run_coroutine_threadsafe(self.publisher.run(), pydcam.EVENT_LOOP)
    #     asyncio.run_coroutine_threadsafe(self.camera.run(), pydcam.EVENT_LOOP)
        
    def thread_buffer_init(self):

        width = self.hsize
        height = self.vsize
        shape = (int(height),int(width))
        dtype = "uint16"

        self.buffers = asyncio_buf(shape, 10, dtype)
        self.publisher = pub_worker(self.buffers)
        self.camera = cam_sim(self.buffers, im_size=shape)

        self.pubfut = asyncio.run_coroutine_threadsafe(self.publisher.run(), pydcam.EVENT_LOOP)
        self.pubfut.add_done_callback(print)
        self.camfut = asyncio.run_coroutine_threadsafe(self.camera.run(), pydcam.EVENT_LOOP)
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
        
        pydcam.EVENT_LOOP.call_soon_threadsafe(self.publisher.unpause)
        pydcam.EVENT_LOOP.call_soon_threadsafe(self.camera.unpause)

        self.running = 1

    def close_camera(self):
        # abort signal to dcamwait_start

        asyncio.run_coroutine_threadsafe(self.publisher.pause(), pydcam.EVENT_LOOP)
        asyncio.run_coroutine_threadsafe(self.camera.pause(), pydcam.EVENT_LOOP)

        self.running = 0

        print( "PROGRAM PAUSE" )

    def quit(self):
        print("Stopping publisher thread...")
        pydcam.EVENT_LOOP.call_soon_threadsafe(self.publisher.stop)
        print("Stopping camera thread...")
        pydcam.EVENT_LOOP.call_soon_threadsafe(self.camera.stop)

        # self.publisher.join()
        # self.camera.join()

        self.running = 0

        print("PROGRAM END")

    def get_info(self):
        info = {"MODEL":"Sim Camera","CAMERAID":"Version 1","BUS":"This information is unnecessary"}
        return info

    def get_info_detail(self):
        return self.get_info()

    def set_exposure(self,exp_time):
        self.camera.exptime = exp_time

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
        keys = ["SUBARRAY HSIZE","SUBARRAY HPOS","SUBARRAY VSIZE","SUBARRAY VPOS","EXPOSURE TIME"]
        values = [(self.camera.imsize[0],0,2000),(2,1,3),(self.camera.imsize[1],0,2000),(2,1,3),(self.camera.exptime,0,10)]
        return values

    def get_window_info_dict(self):
        keys = ["SUBARRAYHSIZE","SUBARRAYHPOS","SUBARRAYVSIZE","SUBARRAYVPOS","EXPOSURETIME"]
        values = [(self.camera.imsize[0],0,2000),(2,1,3),(self.camera.imsize[1],0,2000),(2,1,3),(self.camera.exptime,0,10)]
        return dict(zip(keys,values))

    def get_running(self):
        return self.running

    def reset_buffer_head(self):
        self.buffers.reset_head()



if __name__ == "__main__":
    from pydcam import open_config
    from pydcam.api import OpenCamera
    from pydcam.utils.zmq_pubsub import zmq_publisher
    iDevice = 0

    fname = None
    if len(sys.argv) > 1:
        fname = Path(sys.argv[1]).resolve()

    with OpenCamera(iDevice) as dcam:

        dcam.prop_setdefaults()

        dcam.prop_setvalue(DCAM_IDPROP.EXPOSURETIME,1.0)

        if fname is not None:
            init_dict = open_config(fname)
            if init_dict: dcam.prop_setfromdict(init_dict)

        camreader = DCamReader(dcam)
        this_zmq = zmq_publisher()
        camreader.register_callback(this_zmq.publish)
        # camreader.register_callback(print)

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
        camreader.quit()
