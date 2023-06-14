

import threading
import time

class CallbackQueue(dict):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.lock = threading.Lock()

    def pop(self, key):
        """Like dict.pop but always returns None if key doesn't exist"""
        with self.lock:
            return super().pop(key, None)
    
    def __setitem__(self, __k, __v):
        """Locking setitem"""
        with self.lock:
            super().__setitem__(__k, __v)

    def __call__(self, cb_data):
        """iterate through dict with lock"""
        poplater = []
        with self.lock:
            for fid,cb in self.items():
                try:
                    cb(cb_data)
                except:
                    poplater.append(fid)
        for key in poplater:
            super().pop(key, None)

class CallbackThread:
    def __init__(self, startpaused=False, ratelimit=0):
        super().__init__()

        self.ratelimit = ratelimit
        self.now = time.perf_counter()

        self.callbacks = CallbackQueue()
        self._go = True
        self._pause = startpaused

        self.wait_while_paused = threading.Event()
        self.wait_while_paused.clear()
        self.wait_until_paused = threading.Event()
        self.wait_until_paused.set()
        
        self.thread = None

    def set_ratelimit(self, ratelimit):
        self.ratelimit = ratelimit

    def get_data(self):
        """Needs reimplementing in subclass"""
        pass

    def run(self):
        while(self._go):
            if self._pause:
                self.wait_until_paused.set()
                self.wait_while_paused.wait()
                self.wait_until_paused.clear()
            if not self._go:
                return
            cb_data = self.get_data()
            if cb_data is not None:
                if self.ratelimit:
                    if time.perf_counter()-self.now > self.ratelimit:
                        self.now = time.perf_counter()
                    else:
                        continue
                self.callbacks(cb_data)

    def pause(self):
        self.wait_while_paused.clear()
        self._pause = True
        self.wait_until_paused.wait()

    def unpause(self):
        self.wait_while_paused.set()
        
    def start_cb_thread(self):
        if self.thread is None:
            self.thread = threading.Thread(target=self.run)
            self.thread.start()

    def stop_cb_thread(self):
        if self.thread is not None:
            self._go = False
            self.unpause()
            self.thread.join()
            self.thread = None

    def register(self, func):
        fid = str(id(func))
        self.callbacks[fid] = func
        return fid

    def deregister(self, fid):
        self.callbacks.pop(fid)

    def oneshot(self):
        ready = threading.Event()
        def func(data):
            self.oneshot_data = data
            ready.set()
        self.oneshot_callback(func)
        ready.wait()
        return self.oneshot_data

    def oneshot_callback(self, func):
        def wrapper(data):
            func(data)
            raise Exception()
        self.register(wrapper)

    def multishot(self, n):
        ready = threading.Event()
        self.multishot_return = []
        def func(data, done):
            self.multishot_return.append(data)
            if done:
                ready.set()
        self.multishot_callback(func, n)
        ready.wait()
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

    def __enter__(self):
        self.start_cb_thread()

    def __exit__(self,*args):
        self.stop_cb_thread()