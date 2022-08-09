
#!/usr/bin/env python3

import ctypes
import threading
import numpy

class circ_buf():
    """A very simple buffer to be used by single thread only, not thread safe"""
    def __init__(self, shape:tuple, count:int, dtype:str, timeout=2.):
        self.size = None
        self.count = None
        self.dtype = None
        self.shape = None
        self.lock = threading.Lock()
        self.wait = threading.Event()

        self.resize(shape, count, dtype)
        self.last_filled = count-1
        self.last_read = count-1
        self.full_bufs = 0
        self.unread_bufs = 0
        self.timeout = timeout
        self._cancelled = False

    def resize(self, shape:tuple, count:int=None, dtype:str=None):

        self.shape = shape if isinstance(shape,tuple) else (shape,)

        if count is not None:
            self.count = count

        if dtype is not None:
            try:
                self.dtype = numpy.dtype(dtype)
            except TypeError:
                self.dtype = numpy.uint8

        self.size = numpy.product(numpy.array(shape))*self.dtype.itemsize

        buf_dim = (self.count, *self.shape)
        with self.lock:
            self.bufs = numpy.zeros(buf_dim, dtype=numpy.dtype(self.dtype))
            self.full_bufs = 0
            self.unread_bufs = 0
            self.last_filled = self.count-1
            self.last_read = self.count-1

    def copy_from_address(self,address,size):
        if size != self.size:
            print("buf wrong size")
            return None
        with self.lock:
            self.last_filled = (self.last_filled+1)%self.count
            self.full_bufs = min(self.full_bufs + 1,self.count)
            self.unread_bufs = (self.unread_bufs + 1)
            ctypes.memmove(self.bufs[self.last_filled].ctypes.data_as(ctypes.c_void_p), address, self.size)
            self.wait.set()

    def copy_numpy(self, array:numpy.ndarray):
        if array.shape != self.bufs.shape[1:]:
            print("arr wrong shape")
            return None
        with self.lock:
            self.last_filled = (self.last_filled + 1)%self.count
            self.full_bufs = min(self.full_bufs + 1,self.count)
            self.unread_bufs = (self.unread_bufs + 1)
            self.bufs[self.last_filled] = numpy.copy(array)
            self.wait.set()

    def get_to_fill(self):
        return self.bufs[(self.last_filled + 1)%self.count]

    def inc_last_filled(self):
        self.last_filled = (self.last_filled + 1)%self.count
        self.full_bufs = min(self.full_bufs + 1,self.count)
        self.unread_bufs = (self.unread_bufs + 1)
        self.wait.set()

    def get_last_filled(self):
        if self.full_bufs > 0:
            return self.bufs[self.last_filled]

        self.wait.clear()
        self.wait.wait()
        with self.lock:
            return self.bufs[self.last_filled]

    def get_latest(self,block=0,copy=0):
        if self.unread_bufs <= 0:
            self.unread_bufs = 0
            if block:
                self.wait.clear()
                self._cancelled = False
                if not self.wait.wait(self.timeout):
                    print("No buffer available")
                    return None
                if self._cancelled:
                    print("Cancelled")
                    return None
            else:
                print("No buffer available")
                return None
        with self.lock:
            if self.unread_bufs > self.count:
                print(f"Buf overran by {self.unread_bufs-self.count}")
                self.unread_bufs = self.count - 1
                self.last_read = (self.last_filled+1)%self.count
            else:
                self.last_read = (self.last_read+1)%self.count
                self.unread_bufs -= 1
        if copy:
            return numpy.copy(self.bufs[self.last_read])
        else:
            return self.bufs[self.last_read]

    def reset_head(self):
        self.last_read = self.last_filled
        self.unread_bufs = 0

    def cancel_wait(self):
        self._cancelled = True
        self.wait.set()

class thread_buf(circ_buf):
    """A subclass of circ_buf to make thread safe access"""
    def __init__(self, shape:tuple, count:int, dtype:str, timeout=2.):
        super().__init__(shape, count, dtype, timeout)
        self.read_lock = threading.Lock()
        self.write_lock = threading.Lock()

    def get_latest(self,block=1,copy=1):
        return super().get_latest(block,copy)

    def get_at_index(self,index):
        index = index%self.count
        if index < self.last_filled or self.full_bufs > index:
            return numpy.copy(self.bufs[index])
        else:
            self.wait.clear()
            self.wait.wait()
            self.get_at_index(index)

    def wait_for(self, N):
        for i in range(N):
            self.wait.clear()
            self.wait.wait()

    def wrap_copy(self,start,end):
        start = start%self.count
        end = end%self.count
        N = end-start if end > start else self.count + end - start
        out_array = numpy.empty((N,*self.shape),dtype=self.dtype)
        if end > start:
            out_array[:] = self.bufs[start:end]
        elif start >= end:
            out_array[0:self.count-start] = self.bufs[start:]
            out_array[self.count-start:] = self.bufs[:end]
        return out_array

    def get(self, N):
        if N > self.count:
            ret_array = numpy.empty((N,*self.shape),dtype=self.dtype)
            this_count = self.count - 1
            full = (N//this_count)
            left = N%this_count
            for f in range(full):
                ret_array[this_count*f:this_count*(f+1)] = self.get(this_count)
            if left: ret_array[this_count*full:] = self.get(left)
            return ret_array
        else:
            with self.read_lock:
                if self.unread_bufs > self.count:
                    print(f"Buf overran by {self.unread_bufs-self.count}")
                    self.last_read = self.last_filled
                    self.unread_bufs = self.count
                if self.unread_bufs >= N:
                    self.unread_bufs -= N
                    arr = self.wrap_copy(self.last_read+1,self.last_read+1+N)
                    self.last_read = (self.last_read+N)%self.count
                    return arr
                self.wait_for(N-self.unread_bufs)
            return self.get(N)


# a simple thread buf for testing

# class thread_buf:
#     def __init__(self, shape:tuple, count:int, dtype:str, timeout=2.):
#         self.bufs = None
#         self.wait = threading.Event()
#         self.got = True

#     def copy_numpy(self, array):
#         self.bufs[0] = array.copy()
#         self.got = False
#         self.wait.set()

#     def get_latest(self,block=1,copy=1):
#         if self.got:
#             if not self.wait.wait(2000):
#                 print("timed out")
#                 return None
#         data = self.bufs[0]
#         self.got = True
#         self.wait.clear()
#         # print("Returning data")
#         print(data)
#         return data

#     def get_to_fill(self):
#         return self.bufs[0]

#     def inc_last_filled(self):
#         # self.last_filled = (self.last_filled + 1)%self.count
#         # self.full_bufs = min(self.full_bufs + 1,self.count)
#         # self.unread_bufs = (self.unread_bufs + 1)
#         self.wait.set()
#         self.got = False

#     def resize(self, shape:tuple, count:int=None, dtype:str=None):
#         self.shape = shape
#         self.count = count
#         self.dtype = dtype
#         self.bufs = numpy.zeros((1,*self.shape),dtype=numpy.dtype(self.dtype))

#     def reset_head(self):
#         pass

#     def cancel_wait(self):
#         self._cancelled = True
#         self.wait.set()