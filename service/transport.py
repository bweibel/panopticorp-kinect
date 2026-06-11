import asyncio
import json
import struct
import numpy as np
import websockets
from websockets.server import ServerConnection

PORT = 8765
_clients: set[ServerConnection] = set()


def pack_cloud(frame_id: int, points: np.ndarray) -> bytes:
    """Binary frame: [uint32 frameId][uint16 numPoints][int16 x,y,z * N]"""
    n = len(points)
    header = struct.pack(">IH", frame_id, n)
    body = points.astype(np.int16).tobytes() if n > 0 else b""
    return header + body


def make_meta(frame_id: int, motion_energy: float, blobs: list) -> str:
    return json.dumps({
        "frameId": frame_id,
        "motionEnergy": round(motion_energy, 4),
        "blobs": [
            {
                "id": b.id,
                "cx": round(b.cx, 1),
                "cy": round(b.cy, 1),
                "wx": round(b.wx, 3),
                "wz": round(b.wz, 3),
                "w": b.w,
                "h": b.h,
                "area": b.area,
                "vx": round(b.vx, 4),
                "vz": round(b.vz, 4),
            }
            for b in blobs
        ],
    })


async def _handler(ws: ServerConnection):
    _clients.add(ws)
    try:
        await ws.wait_closed()
    finally:
        _clients.discard(ws)


async def broadcast(frame_id: int, points: np.ndarray, motion_energy: float, blobs: list):
    if not _clients:
        return
    binary = pack_cloud(frame_id, points)
    meta = make_meta(frame_id, motion_energy, blobs)
    results = await asyncio.gather(
        *[_send(ws, binary, meta) for ws in list(_clients)],
        return_exceptions=True,
    )
    return results


async def _send(ws: ServerConnection, binary: bytes, meta: str):
    try:
        await ws.send(binary)
        await ws.send(meta)
    except websockets.exceptions.ConnectionClosed:
        pass


async def serve():
    async with websockets.serve(_handler, "localhost", PORT):
        print(f"WebSocket server listening on ws://localhost:{PORT}")
        await asyncio.Future()
