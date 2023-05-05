

from collections import deque, namedtuple
import asyncio
import threading
import datetime
from typing import Union

import numpy

ParamInfo = namedtuple("ParamInfo", ["value", "min", "max", "step"])

def get_datetime_stamp(microseconds=False, split=False) -> Union[str,tuple]:
    """This function should be used for generating all text timestamps to ensure consistency

    Args:
        microseconds (bool, optional): Whether to include ms in timestamp. Defaults to False.
        split (bool, optional): Whether to return date and time seperately. Defaults to False.

    Returns:
        str or tuple: Returns str timestamp or tuple (date_ts,time_ts) if split==True
    """
    if not microseconds:
        now = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%S")
    else:
        now = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%S-%f")
    if not split:
        return now
    else:
        return now.split("T")

class LoopRunner:
    EVENT_LOOP = None

    def __enter__(self) -> asyncio.BaseEventLoop:
        self.__class__.EVENT_LOOP = asyncio.new_event_loop()
        self.event_thread = threading.Thread(target=self.__class__.EVENT_LOOP.run_forever)
        self.event_thread.start()
        return self.__class__.EVENT_LOOP

    def __exit__(self, *args):
        for task in asyncio.all_tasks(self.EVENT_LOOP):
            task.cancel()
            # if not task.done(): task.set_result(None)
        self.EVENT_LOOP.call_soon_threadsafe(self.EVENT_LOOP.stop)
        print(args)
        self.event_thread.join()
        return False
    
    @classmethod
    def call_soon(cls, func):
        return cls.EVENT_LOOP.call_soon_threadsafe(func)
    
    @classmethod
    def get_event_loop(cls):
        return cls.EVENT_LOOP
    
    @classmethod
    def run_coroutine(cls, coro):
        return asyncio.run_coroutine_threadsafe(coro, cls.EVENT_LOOP)
    
    @classmethod
    def run_in_executor(cls, func):
        return cls.EVENT_LOOP.run_in_executor(None, func)
    
# def get_event_loop():
#     return LoopRunner.EVENT_LOOP

# def run_coroutine_threadsafe(coro):
#     return asyncio.run_coroutine_threadsafe(coro, LoopRunner.EVENT_LOOP)

# def call_soon_threadsafe(func):
#     return LoopRunner.EVENT_LOOP.call_soon_threadsafe(func)

def list_to_numpy(in_data):
    if isinstance(in_data, numpy.ndarray):
        return in_data
    elif isinstance(in_data, (list,deque,tuple)):
        if len(in_data) == 1:
            return in_data[0]
        x = numpy.zeros((len(in_data),*(in_data[0].shape)),dtype=in_data[0].dtype)
        for i,img in enumerate(in_data):
            x[i] = img
        return x
    else:
        raise TypeError("list_to_numpy: Type not understood")