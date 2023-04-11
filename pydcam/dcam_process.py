
import numpy
import asyncio
import signal
from pydcam.utils.zmq_pubsub import zmq_reader
from pydcam.utils.shmem import shmem_reader, shmem_reader_async


class ImgProcessor:
    def __init__(self):
        pass

    def update_trigger(self, data):
        fno, data = data
        print(fno)
        print(numpy.mean(data))

if __name__ == "__main__":

    # this_zmq = zmq_reader(ratelimit=0.05)
    this_zmq = shmem_reader_async(ratelimit=0.05)

    this = ImgProcessor()

    this_zmq.register(this.update_trigger)

    signal.signal(signal.SIGINT, this_zmq.stop)

    try:
        asyncio.run(this_zmq.start())
    finally:
        this_zmq.close()