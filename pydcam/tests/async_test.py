



import asyncio
import threading
import time

go = True


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

if __name__ == "__main__":
    EVENT_LOOP = asyncio.new_event_loop()
    event_thread = threading.Thread(target=EVENT_LOOP.run_forever)
    event_thread.start()
    pw = pub_worker()
    # EVENT_LOOP.create_task(pw.run())
    asyncio.run_coroutine_threadsafe(pw.run(), EVENT_LOOP)
    time.sleep(1.)
    # EVENT_LOOP.create_task(cam_worker())
    asyncio.run_coroutine_threadsafe(cam_worker(), EVENT_LOOP)
    print("Hello")

    time.sleep(2)

    retval = asyncio.run_coroutine_threadsafe(pw.get_cnt(),EVENT_LOOP)
    print(retval.result())
    retval = asyncio.run_coroutine_threadsafe(pw.get_cnt(),EVENT_LOOP)
    print(retval.result())

    try:
        input("Enter to stop\n")
    except KeyboardInterrupt as e:
        print(e)
    print("Stopping")
    go = False
    for task in asyncio.all_tasks(EVENT_LOOP):
        task.cancel()
    EVENT_LOOP.call_soon_threadsafe(EVENT_LOOP.stop)

