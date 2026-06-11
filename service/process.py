import numpy as np
import cv2
from dataclasses import dataclass
from typing import Optional

Z_MIN = 500     # mm — near clip
Z_MAX = 3500    # mm — far clip
STRIDE = 3      # pixel decimation; 3 -> ~5k-15k points per frame
FX, FY = 594.21, 591.04   # Kinect v1 depth intrinsics
CX, CY = 339.5, 242.7
MIN_BLOB_AREA = 400        # px² — drops hand-wave noise specks
MAX_AGE = 5                # frames an unmatched blob survives before eviction


@dataclass
class Blob:
    id: int
    cx: float    # pixel centroid x
    cy: float    # pixel centroid y
    wx: float    # world x, meters
    wz: float    # world z (depth), meters
    w: int       # bbox width, px
    h: int       # bbox height, px
    area: int
    vx: float = 0.0   # world velocity x, m/frame
    vz: float = 0.0   # world velocity z, m/frame


class BlobTracker:
    def __init__(self):
        self._next_id = 0
        self._active: dict[int, dict] = {}   # id -> {"blob": Blob, "age": int}

    def update(self, depth_mm: np.ndarray, fg_mask: np.ndarray) -> list[Blob]:
        n, labels, stats, centroids = cv2.connectedComponentsWithStats(
            fg_mask.astype(np.uint8), connectivity=8
        )

        candidates: list[Blob] = []
        for i in range(1, n):
            area = int(stats[i, cv2.CC_STAT_AREA])
            if area < MIN_BLOB_AREA:
                continue

            cx_px, cy_px = centroids[i]
            bw = int(stats[i, cv2.CC_STAT_WIDTH])
            bh = int(stats[i, cv2.CC_STAT_HEIGHT])

            blob_depths = depth_mm[labels == i]
            valid = blob_depths[(blob_depths >= Z_MIN) & (blob_depths <= Z_MAX)]
            if len(valid) == 0:
                continue
            mean_d = valid.mean() / 1000.0   # mm -> m

            candidates.append(Blob(
                id=-1,
                cx=float(cx_px), cy=float(cy_px),
                wx=(cx_px - CX) * mean_d / FX,
                wz=mean_d,
                w=bw, h=bh, area=area,
            ))

        # greedy nearest-centroid match in world space
        prev = {bid: d["blob"] for bid, d in self._active.items()}
        matched_new: set[int] = set()
        matched_prev: set[int] = set()

        pairs = []
        for ni, nb in enumerate(candidates):
            for pid, pb in prev.items():
                dx, dz = nb.wx - pb.wx, nb.wz - pb.wz
                pairs.append((dx * dx + dz * dz, ni, pid))
        pairs.sort()

        for _, ni, pid in pairs:
            if ni in matched_new or pid in matched_prev:
                continue
            nb = candidates[ni]
            pb = prev[pid]
            nb.id = pid
            nb.vx = nb.wx - pb.wx
            nb.vz = nb.wz - pb.wz
            matched_new.add(ni)
            matched_prev.add(pid)

        for ni, nb in enumerate(candidates):
            if ni not in matched_new:
                nb.id = self._next_id
                self._next_id += 1

        new_active: dict[int, dict] = {}
        for nb in candidates:
            new_active[nb.id] = {"blob": nb, "age": 0}
        for pid, d in self._active.items():
            if pid not in matched_prev:
                d["age"] += 1
                if d["age"] <= MAX_AGE:
                    new_active[pid] = d

        self._active = new_active
        return candidates


def process_frame(
    depth_mm: np.ndarray,
    tracker: BlobTracker,
    prev_fg: Optional[np.ndarray] = None,
) -> tuple[np.ndarray, list[Blob], float, np.ndarray]:
    """
    Returns (points_int16, blobs, motion_energy, fg_mask).
    points_int16: Nx3 int16 array, (x, y, z) in mm, y-up convention.
    motion_energy: 0.0-1.0 fraction of frame that changed foreground state.
    """
    fg_mask = (depth_mm >= Z_MIN) & (depth_mm <= Z_MAX)

    if prev_fg is not None:
        motion_energy = float(np.count_nonzero(fg_mask != prev_fg)) / fg_mask.size
    else:
        motion_energy = 0.0

    rows, cols = np.where(fg_mask[::STRIDE, ::STRIDE])
    rows = rows * STRIDE
    cols = cols * STRIDE

    if len(rows) == 0:
        points = np.empty((0, 3), dtype=np.int16)
    else:
        d_m = depth_mm[rows, cols] / 1000.0
        x_mm = ((cols - CX) * d_m / FX * 1000).astype(np.int16)
        y_mm = (-(rows - CY) * d_m / FY * 1000).astype(np.int16)   # y-up
        z_mm = (d_m * 1000).astype(np.int16)
        points = np.stack([x_mm, y_mm, z_mm], axis=1)

    blobs = tracker.update(depth_mm, fg_mask)
    return points, blobs, motion_energy, fg_mask
