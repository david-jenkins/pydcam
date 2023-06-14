

import asyncio
from distutils.log import info
from multiprocessing import resource_tracker

def remove_shm_from_resource_tracker():
    """Monkey-patch multiprocessing.resource_tracker so SharedMemory won't be tracked

    More details at: https://bugs.python.org/issue38119
    """

    def fix_register(name, rtype):
        if rtype == "shared_memory":
            return
        return resource_tracker._resource_tracker.register(self, name, rtype)
    resource_tracker.register = fix_register

    def fix_unregister(name, rtype):
        if rtype == "shared_memory":
            return
        return resource_tracker._resource_tracker.unregister(self, name, rtype)
    resource_tracker.unregister = fix_unregister

    if "shared_memory" in resource_tracker._CLEANUP_FUNCS:
        del resource_tracker._CLEANUP_FUNCS["shared_memory"]

remove_shm_from_resource_tracker()

from multiprocessing import shared_memory as shmem
import time
import orjson
import numpy
from pathlib import Path

from pydcam.utils.cb_thread import CallbackThread
from pydcam.utils.cb_asyncio import CallbackCoroutine

HDR_SIZE = 64
INFO_SIZE = 16

class shmem_publisher():
    def __init__(self, size, name='hama1234'):
        try:
            self.shmem_header = shmem.SharedMemory(name=name+"_info", size=HDR_SIZE+INFO_SIZE, create=True)
            Path(f"/dev/shm/{name+'_info'}").chmod(0o666)
            created = True
        except Exception as e:
            print(e)
            self.shmem_header = shmem.SharedMemory(name=name+"_info", size=HDR_SIZE+INFO_SIZE, create=False)
            created = False
        self.info = numpy.ndarray(shape=(INFO_SIZE//4,), dtype=numpy.int32, buffer=self.shmem_header.buf[:INFO_SIZE])
        self.header = self.shmem_header.buf[INFO_SIZE:HDR_SIZE+INFO_SIZE]

        if created:
            self.info[3] = 1
            self.info[0] = -1
        else:
            self.info[3] = self.info[3] + 1
        
        self.shmem_block = shmem.SharedMemory(name=name, size=size, create=True)
        Path(f"/dev/shm/{name}").chmod(0o666)
        self.info[2] = size
        self.fno = 0

    def publish(self, data:numpy.ndarray):
        hdr = orjson.dumps((data.nbytes,str(data.dtype),data.shape))
        self.header[:len(hdr)] = hdr
        tmp_array = numpy.ndarray(shape=data.shape, dtype=data.dtype, buffer=self.shmem_block.buf[:data.nbytes])
        tmp_array[:] = data[:]
        self.info[1] = len(hdr)
        self.info[0] = self.fno
        self.fno+=1
        del tmp_array

    def close(self):
        cnt = self.info[3]
        print(f"{cnt} users")
        if cnt == 1:
            print("Last user so closing")
            self.shmem_header.unlink()
            self.shmem_block.unlink()
        else:
            self.info[3] = cnt-1
        del self.info
        del self.header

        self.shmem_header.close()
        self.shmem_block.close()

class _shmem_reader_mixin:
    def __init__(self, name='hama1234'):
        try:
            self.shmem_header = shmem.SharedMemory(name=name+"_info", size=HDR_SIZE+INFO_SIZE, create=False)
            created = False
        except FileNotFoundError as e:
            print(e)
            self.shmem_header = shmem.SharedMemory(name=name+"_info", size=HDR_SIZE+INFO_SIZE, create=True)
            Path(f"/dev/shm/{name+'_info'}").chmod(0o666)
            created = True
        self.info = numpy.ndarray(shape=(INFO_SIZE//4,), dtype=numpy.int32, buffer=self.shmem_header.buf[:INFO_SIZE])
        self.header = self.shmem_header.buf[INFO_SIZE:HDR_SIZE+INFO_SIZE]

        if created:
            self.info[3] = 1
            self.info[0] = -1
        else:
            self.info[3] = self.info[3] + 1

        self.name = name
        self.shm_go = True
        self.size = 0
        self.shmem_block:shmem.SharedMemory = None
        self.fno = -1

    def stop_shmem_reader(self, *args):
        print("Stopping reader")
        self.shm_go = False

    def close_shmem_reader(self):
        cnt = self.info[3]
        print(f"{cnt} users connected")
        if cnt == 1:
            print("Last user so unlinking")
            self.shmem_header.unlink()
            if self.shmem_block is not None:
                self.shmem_block.unlink()
        else:
            self.info[3] = cnt-1
        self.shm_go = False
        del self.info
        del self.header
        # print("Closing shmem blocks")
        # self.shmem_header.close()
        # if self.shmem_block is not None:
        #     self.shmem_block.close()

class shmem_reader(_shmem_reader_mixin, CallbackThread):
    def get_data(self):
        if self.info is not None and self.shm_go: 
            while self.shm_go and self.info[0] <= self.fno:
                time.sleep(0.0001)
            if not self.shm_go: return
            size = self.info[2]
            hdr_size = self.info[1]
            if size>self.size:
                if self.shmem_block is not None:
                    self.shmem_block.close()
                    self.shmem_block = None
                self.size = size
                self.shmem_block = shmem.SharedMemory(name=self.name, size=size)
            nbytes, dtype, shape = orjson.loads(self.header[:hdr_size])
            arr = numpy.ndarray(shape=shape, dtype=dtype, buffer=self.shmem_block.buf[:nbytes]).copy()
            self.fno = self.info[0]
            return arr

    def stop(self):
        self.stop_shmem_reader()
        self.stop_cb_thread()

class shmem_reader_async(_shmem_reader_mixin, CallbackCoroutine):
    def __init__(self, ratelimit=0.0):
        _shmem_reader_mixin.__init__(self)
        CallbackCoroutine.__init__(self, ratelimit=ratelimit)
        self.arr = None

    async def get_data(self):
        if self.info is not None and self.shm_go: 
            while self.shm_go and self.info[0] <= self.fno:
                await asyncio.sleep(0.0001)
            if not self.shm_go: return
            size = self.info[2]
            hdr_size = self.info[1]
            if size>self.size:
                if self.shmem_block is not None:
                    self.shmem_block.close()
                    self.shmem_block = None
                self.size = size
                self.shmem_block = shmem.SharedMemory(name=self.name, size=size)
            nbytes, dtype, shape = orjson.loads(self.header[:hdr_size])
            self.arr = numpy.ndarray(shape=shape, dtype=dtype, buffer=self.shmem_block.buf[:nbytes])
            self.fno = self.info[0]
            return self.arr.copy()

    def __exit__(self, *args):
        retval = CallbackCoroutine.__exit__(self, *args)
        del self.arr
        self.close_shmem_reader()
        return retval
