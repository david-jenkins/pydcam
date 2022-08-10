

from socket import IP_TOS
import zmq
import orjson
import struct
from functools import partial
import numpy
import time

from pydcam.utils.cb_thread import CallbackThread

CHARLEN = struct.calcsize('!B')
pack_char = partial(struct.pack, '!B')
unpack_char = partial(struct.unpack, '!B')

DOUBLELEN = struct.calcsize('!d')
pack_double = partial(struct.pack, '!d')
unpack_double = partial(struct.unpack, '!d')

def pack_numpy(array):
    header = orjson.dumps((str(array.dtype),array.shape))
    message = pack_char(len(header)) + header + array.tobytes()
    return message

def unpack_numpy(msg):
    raw_msglen = msg[:CHARLEN]
    msglen = unpack_char(raw_msglen)[0]
    array_info = orjson.loads(msg[CHARLEN:CHARLEN+msglen])
    array = numpy.frombuffer(msg[CHARLEN+msglen:],dtype=array_info[0])
    array.shape = array_info[1]
    return array

def extend_timestamp(buffer):
    return buffer + pack_double(time.time())

def prepend_timestamp(buffer):
    return pack_double(time.time())+buffer

def strip_timestamp(buffer):
    return buffer[DOUBLELEN:], unpack_double(buffer[:DOUBLELEN])[0]

class zmq_publisher():
    def __init__(self, ip="127.0.0.1", port=5556, topic='orca'):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PUB)
        self.socket.bind(f"tcp://{ip}:{port}")
        self.topic = topic.encode()

    def publish(self, data):
        to_send = self.topic + pack_double(time.time()) + pack_numpy(data)
        self.socket.send(to_send)
        
    def close(self):
        self.socket.close()

class zmq_reader(CallbackThread):
    def __init__(self, ip="127.0.0.1", port=5556, topic='orca', ratelimit=0):
        super().__init__(ratelimit=ratelimit)

        self.ip = ip
        self.port = port
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)

        self.topicfilter = topic.encode()
        self.socket.setsockopt(zmq.SUBSCRIBE, self.topicfilter)
        self.socket.setsockopt(zmq.CONFLATE, 1)
        self.socket.connect(f"tcp://{ip}:{port}")
        self.socket.RCVTIMEO = 5000

        self.this_time = 0

    def get_data(self):
        timeouts = 0
        while(True):
            try:
                message = self.socket.recv()
            except zmq.error.Again as e:
                print("timeout")
                timeouts+=1
                if timeouts > 3:
                    return None
            except zmq.error.ZMQError as e:
                print(e)
                return None
            else:
                buffer = message[len(self.topicfilter):]
                buffer, self.this_time = strip_timestamp(buffer)
                return unpack_numpy(buffer)

    def stop(self):
        print("Stopping reader")
        super().stop()
        self.socket.close()

    def __enter__(self):
        self.start()

    def __exit__(self,*args):
        self.stop()


# class zmq_reader(threading.Thread):
#     def __init__(self, ip="127.0.0.1", port=5556, topic='orca'):
#         super().__init__()

#         self.context = zmq.Context()
#         self.socket = self.context.socket(zmq.SUB)

#         self.topicfilter = topic.encode()
#         self.socket.setsockopt(zmq.SUBSCRIBE, self.topicfilter)
#         self.socket.setsockopt(zmq.CONFLATE, 1)
#         self.socket.connect(f"tcp://{ip}:{port}")
#         self.socket.RCVTIMEO = 10000

#         self.callbacks = deque()
#         self.ratelimit = 0

#         self.go = 1
#         self.this_time = 0

#     def register(self, func, value=True):
#         if value:
#             if callable(func):
#                 if func not in self.callbacks:
#                     self.callbacks.append(func)
#         else:
#             if func in self.callbacks:
#                 self.callbacks.remove(func)
    
#     # def init(self):
#     #     while 1:
#     #         try:
#     #             message = self.socket.recv()
#     #             break
#     #         except zmq.error.Again as e:
#     #             print(e)
#     #             print("timeout")
#     #         except KeyboardInterrupt as e:
#     #             print("Killed by ctrl-c")
#     #             sys.exit(0)

#     #     buffer = message[len(self.topicfilter):]
#     #     buffer, this_time = strip_timestamp(buffer)
#     #     self.data = numpy.squeeze(unpack_numpy(buffer))

#     #     self.call_callbacks()
#     #     self.go = 1
#     #     self.this_time = 0

#     def call_callbacks(self):
#         for func in list(self.callbacks):
#             func(self.data)
    
#     def stop(self):
#         self.go = 0
        
#     def run(self):
#         timeouts = 0
#         self.now = 0
#         while self.go:
#             try:
#                 message = self.socket.recv()
#             except KeyboardInterrupt as e:
#                 print("quit with ctrl-c")
#             except zmq.error.Again as e:
#                 print("timeout")
#                 timeouts+=1
#                 if timeouts > 10:
#                     return
#                 continue
#             buffer = message[len(self.topicfilter):]
#             buffer, this_time = strip_timestamp(buffer)
#             self.this_time = this_time
#             self.data = unpack_numpy(buffer)
#             if self.ratelimit:
#                 if time.time()-self.now > self.ratelimit:
#                     self.now = time.time()
#                 else:
#                     continue
#             self.call_callbacks()

#     def oneshot(self):
#         ready = threading.Event()
#         def func(data):
#             self.oneshot_data = data
#             ready.set()
#         self.oneshot_callback(func)
#         ready.wait()
#         return self.oneshot_data

#     def oneshot_callback(self,func):
#         def wrapper(data):
#             self.register(wrapper,False)
#             func(data)
#         self.register(wrapper,True)

#     def multishot(self,n):
#         ready = threading.Event()
#         self.multishot_return = []
#         def func(data,done):
#             self.multishot_return.append(data)
#             if done:
#                 ready.set()
#         self.multishot_callback(func,n)
#         ready.wait()
#         return numpy.array(self.multishot_return)

#     def multishot_callback(self,func,n):
#         cnt = [0]
#         def wrapper(data):
#             test = cnt[0] >= n - 1
#             func(data,test)
#             if test:
#                 self.register(wrapper,False)
#             cnt[0]+=1
#         self.register(wrapper,True)
