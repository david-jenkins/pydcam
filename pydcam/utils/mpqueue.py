

"""

Doesn't really work...

"""


import time
import numpy

import threading

from pydcam.utils.cb_thread import CallbackThread

from multiprocessing.managers import BaseManager
from queue import Empty, Full, Queue

class QueueManager(BaseManager): pass

HDR_SIZE = 64
INFO_SIZE = 16

queue = Queue(maxsize=10)

def get_queue():
    return queue

class mpqueue_publisher():
    def __init__(self, ip:str="127.0.0.1", port:int=5556, name:str='hama1234'):
        QueueManager.register('get_queue', callable=get_queue)
        self.manager = QueueManager(address=(ip, port), authkey=name.encode())
        self.server = self.manager.get_server()
        self.serve_thread = threading.Thread(target=self.server.serve_forever)
        self.serve_thread.start()

    def publish(self, data:numpy.ndarray):
        try:
            queue.put_nowait(data)
        except Full as e:
            print(e)

    def close(self):
        self.server.stop_event.set()

class mpqueue_reader(CallbackThread):
    def __init__(self, ip:str="127.0.0.1", port:int=5556, name:str='hama1234', ratelimit=1):
        super().__init__(ratelimit=ratelimit)
        QueueManager.register('get_queue')
        self.ip = ip
        self.port = port
        self.name = name
        self.connect()
        self.queue_go = True

    def connect(self):
        print("Trying to connect")
        self.manager = QueueManager(address=(self.ip, self.port), authkey=self.name.encode())
        try:
            self.manager.connect()
        except Exception as e:
            print(e)
            self.connected = False
        else:
            self.queue:Queue = self.manager.get_queue()
            self.connected = True

    def get_data(self):
        while not self.connected and self.queue_go:
            time.sleep(1)
            self.connect()
        while self.queue_go:
            try:
                return self.queue.get(timeout=1)
            except Empty as e:
                print(e)
            except Exception as e:
                print(e)
                self.connected = False
                break

    def stop(self):
        super().stop()
        self.queue_go = False
