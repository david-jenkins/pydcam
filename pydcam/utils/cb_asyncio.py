

import asyncio
import threading
import time

class CallbackQueue_async(dict):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.lock = asyncio.Lock()

    async def pop(self, key):
        """Like dict.pop but always returns None if key doesn't exist"""
        async with self.lock:
            return super().pop(key, None)
    
    async def __setitem__(self, __k, __v):
        """Locking setitem"""
        async with self.lock:
            super().__setitem__(__k, __v)

    async def __call__(self, cb_data):
        """iterate through dict with lock"""
        poplater = []
        async with self.lock:
            for fid,cb in self.items():
                try:
                    cb(cb_data)
                except:
                    poplater.append(fid)
        for key in poplater:
            super().pop(key, None)

class CallbackQueue(dict):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)

    def pop(self, key):
        """Like dict.pop but always returns None if key doesn't exist"""
        return super().pop(key, None)

    def __call__(self, cb_data):
        """iterate through dict"""
        poplater = []
        for fid,cb in self.items():
            try:
                cb(cb_data)
            except:
                poplater.append(fid)
        for key in poplater:
            super().pop(key, None)

class CallbackCoroutine:
    def __init__(self, startpaused=False, ratelimit=0):
        super().__init__()

        self.ratelimit = ratelimit
        self.now = time.perf_counter()

        self.callbacks = CallbackQueue()
        self._go = True
        self._pause = startpaused

        self.wait_while_paused = asyncio.Event()
        self.wait_while_paused.clear()
        self.wait_until_paused = asyncio.Event()
        self.wait_until_paused.set()

    def set_ratelimit(self, ratelimit):
        self.ratelimit = ratelimit

    def get_data(self):
        """Needs reimplementing in subclass"""
        pass

    async def run(self):
        while(self._go):
            if self._pause:
                self.wait_until_paused.set()
                await self.wait_while_paused.wait()
                self.wait_until_paused.clear()
            if not self._go:
                break
            cb_data = await self.get_data()
            if cb_data is not None:
                if self.ratelimit:
                    if time.perf_counter()-self.now > self.ratelimit:
                        self.now = time.perf_counter()
                    else:
                        continue
                self.callbacks(cb_data)
        self.wait_until_paused.set()
        print("Callback Coro ended")

    async def pause(self):
        self.wait_while_paused.clear()
        self._pause = True
        await self.wait_until_paused.wait()

    def unpause(self):
        self._pause = False
        self.wait_while_paused.set()

    async def stop(self):
        await self.pause()
        self._go = False
        self.unpause()

    def register(self, func):
        fid = str(id(func))
        self.callbacks[fid] = func
        return fid

    def deregister(self, fid):
        self.callbacks.pop(fid)

    async def oneshot(self):
        ready = asyncio.Event()
        def func(data):
            self.oneshot_data = data
            ready.set()
        self.oneshot_callback(func)
        await ready.wait()
        return self.oneshot_data

    def oneshot_callback(self, func):
        def wrapper(data):
            func(data)
            raise Exception()
        self.register(wrapper)

    async def multishot(self, n):
        ready = asyncio.Event()
        self.multishot_return = []
        def func(data, done):
            self.multishot_return.append(data)
            if done:
                ready.set()
        self.multishot_callback(func, n)
        await ready.wait()
        return self.multishot_return

    def multishot_callback(self, func, n):
        cnt = [0]
        def wrapper(data):
            test = (cnt[0] >= n - 1)
            func(data, test)
            if test:
                raise Exception()
            cnt[0] += 1
        self.register(wrapper)

    async def start(self):
        await self.run()

    def __enter__(self):
        self.thread = threading.Thread(target=asyncio.run,args=(self.start(),))
        self.thread.start()

    def __exit__(self,*args):
        self.stop()
        self.thread.join()