"""
Sliding time windows over a sorted alert stream.

Fixed, non-overlapping windows risk splitting one incident's alerts across a
boundary (root cause at 12:59:58, symptoms starting 13:00:02 would land in
two different windows and never get compared to each other). Overlapping
sliding windows fix this: every pair of alerts within WINDOW_SECONDS of each
other is guaranteed to co-occur in at least one window, so HDBSCAN gets a
chance to cluster them together somewhere. The cross-window merge in
clustering.py then unions any local clusters that share alerts.
"""
import numpy as np


def sliding_windows(timestamps: np.ndarray, window_seconds: float, step_seconds: float):
    """Return a list of windows, each a list of indices into `timestamps`
    (which must be sorted ascending). Every index appears in at least one
    window; indices near a window's edge also appear in the neighboring
    overlapping window.
    """
    n = len(timestamps)
    if n == 0:
        return []
    if n == 1:
        return [[0]]

    t_min, t_max = float(timestamps[0]), float(timestamps[-1])
    windows = []
    start = t_min
    while start <= t_max:
        end = start + window_seconds
        idx = np.where((timestamps >= start) & (timestamps < end))[0]
        if len(idx) > 0:
            windows.append(idx.tolist())
        start += step_seconds

    return windows
