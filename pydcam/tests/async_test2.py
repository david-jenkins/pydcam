



import asyncio
import threading
import time

go = True

class LoopRunner:
    def __enter__(self):
        self.EVENT_LOOP = asyncio.new_event_loop()
        event_thread = threading.Thread(target=self.EVENT_LOOP.run_forever)
        event_thread.start()
        return self.EVENT_LOOP

    def __exit__(self, *args):
        for task in asyncio.all_tasks(self.EVENT_LOOP):
            task.cancel()
        self.EVENT_LOOP.call_soon_threadsafe(self.EVENT_LOOP.stop)

class pub_worker:
    def __init__(self) -> None:
        self.cnt = 0
    async def run(self):
        while go:
            await asyncio.sleep(1)
            print("Doing pub work")
            self.cnt+=1
    async def get_cnt(self):
        await asyncio.sleep(2)
        return self.cnt

async def cam_worker():
    while go:
        await asyncio.sleep(1)
        print("Doing cam work")

async def work_loop(event:asyncio.Event):
    pw = pub_worker()
    # EVENT_LOOP.create_task(pw.run())
    # asyncio.run_coroutine_threadsafe(pw.run(), EVENT_LOOP)
    asyncio.create_task(pw.run())
    # asyncio.run(pw.run())
    time.sleep(1.)
    # EVENT_LOOP.create_task(cam_worker())
    asyncio.create_task(cam_worker())
    print("Hello")

    time.sleep(2)

    retval = asyncio.create_task(pw.get_cnt())
    # print(retval.result())
    retval = asyncio.create_task(pw.get_cnt())
    # print(retval.result())
    
    await event.wait()

if __name__ == "__main__":

    # with LoopRunner() as EVENT_LOOP:
    event = asyncio.Event()
    
    asyncio.create_task(work_loop(event))

    try:
        input("Enter to stop\n")
    except KeyboardInterrupt as e:
        print(e)
    print("Stopping")
    event.set()
        # go = False
        # for task in asyncio.all_tasks(EVENT_LOOP):
        #     task.cancel()
        # EVENT_LOOP.call_soon_threadsafe(EVENT_LOOP.stop)

