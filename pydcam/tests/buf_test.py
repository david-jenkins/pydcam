import threading
import time
import numpy
import code
from pydcam.dcam_reader import thread_buf

class add_to_buf_thread(threading.Thread):
    def __init__(self):
        super().__init__()
        self.buf = None
        self.go = 1
        self.time = 1
    
    def add_buffer(self,buf):
        self.buf = buf
        self.init_buf = numpy.squeeze(buf.get_latest())
        print(self.init_buf.shape)

    def run(self):
        cnt = 0
        while self.go:
            cnt+=1
            self.init_buf[:] = cnt
            time.sleep(self.time)
            self.buf.copy_numpy(self.init_buf)

    def stop(self):
        self.go = 0

class get_from_buf_thread(threading.Thread):
    def __init__(self,buf,N=10):
        super().__init__()
        self.buf = buf
        self.N = N
        self.data = None

    def run(self):
        self.data = self.buf.get(self.N)
        print(self.data)

def cont(x):
    l = len(x)
    for i in range(l-1):
        if numpy.any(x[i+1] != x[i]+1):
            print("error!")
    print(x)

def get_buf(buf,N):
    t = get_from_buf_thread(buf,N)
    t.start()

x = numpy.zeros((100,100),dtype=numpy.int16)
t = add_to_buf_thread()
b = thread_buf((100,100),4,"int16")
print(b.bufs.shape)
print(x.shape)
b.copy_numpy(x)
t.add_buffer(b)

t.start()

code.interact(local=globals())

t.stop()