import asyncio
import queue
import threading
import time
import numpy as np

from process import BlobTracker, process_frame
import transport

try:
    import freenect
    HAS_KINECT = True
except ImportError:
    HAS_KINECT = False


# ---- fake frame generator (no hardware needed) ----

def _fake_depth_frame(t: float) -> np.ndarray:
    depth = np.zeros((480, 640), dtype=np.uint16)
    # two blobs moving in opposite arcs to exercise tracker ID persistence
    for cx, phase in [(280, 0.0), (400, np.pi)]:
        bx = int(cx + 100 * np.sin(t * 0.4 + phase))
        by = 240
        ys, xs = np.ogrid[:480, :640]
        mask = ((xs - bx) ** 2 / 70 ** 2 + (ys - by) ** 2 / 110 ** 2) < 1
        depth[mask] = np.uint16(1500 + 100 * np.sin(t + phase))
        depth[mask] += np.random.randint(0, 40, int(mask.sum()), dtype=np.uint16)
    return depth


# ---- freenect capture thread ----

_frame_q: queue.SimpleQueue = queue.SimpleQueue()


def _depth_cb(dev, depth, timestamp):
    _frame_q.put(depth.copy())


def _kinect_thread():
    freenect.runloop(depth=_depth_cb)


# ---- main loop ----

async def _run(get_frame):
    tracker = BlobTracker()
    prev_fg = None
    frame_id = 0
    loop = asyncio.get_running_loop()

    while True:
        depth = await loop.run_in_executor(None, get_frame)
        points, blobs, motion_energy, fg = process_frame(depth, tracker, prev_fg)
        await transport.broadcast(frame_id, points, motion_energy, blobs)
        prev_fg = fg
        frame_id += 1


async def main():
    if HAS_KINECT:
        t = threading.Thread(target=_kinect_thread, daemon=True)
        t.start()
        source = _frame_q.get   # blocks until freenect delivers; run_in_executor handles it
        print("Kinect detected — streaming live depth.")
    else:
        print("freenect not available — using synthetic depth frames.")
        start = time.monotonic()

        def source():
            time.sleep(1 / 30)
            return _fake_depth_frame(time.monotonic() - start)

    await asyncio.gather(transport.serve(), _run(source))


if __name__ == "__main__":
    asyncio.run(main())
