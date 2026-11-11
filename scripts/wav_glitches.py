#!/usr/bin/env python3
"""wav_glitches.py - look for skips and clicks in an audio dump.

    .venv/bin/python scripts/wav_glitches.py mix.wav [--from S] [--to S]

Made for LINDBERGH_AUDIO_DUMP (48 kHz stereo 16-bit). Prints:
  - level: peak, RMS, samples at full scale (clipped), and how many sit in
    the limiter's knee (> 0.8);
  - clicks: samples whose second difference is far outside its
    neighbourhood (a step in the waveform: a block boundary where the
    stream jumps, a loop point that does not join);
  - dropouts: stretches of exact digital silence inside sound (the mixer
    had nothing: a voice stopped, a ring cleared);
  - repeats: 1024-frame blocks that equal (or nearly equal) a block heard
    10 ms - 2 s earlier: the mixer replaying a ring's last lap.
Times are seconds from the start of the file.
"""
import argparse
import sys
import wave

import numpy as np


def load(path):
    with wave.open(path, "rb") as w:
        rate, ch, n = w.getframerate(), w.getnchannels(), w.getnframes()
        data = np.frombuffer(w.readframes(n), dtype="<i2")
    return rate, data.reshape(-1, ch).astype(np.float32) / 32768.0


def clicks(x, rate, k=12.0, win=2048):
    """Second-difference outliers against a running median of |d2|."""
    d2 = np.abs(np.diff(x, 2))
    n = len(d2) // win * win
    if n == 0:
        return np.array([], dtype=int)
    blocks = d2[:n].reshape(-1, win)
    med = np.median(blocks, axis=1)
    floor = np.maximum(med, 2e-4)                  # quiet passages: ignore hiss
    thr = np.repeat(floor * k, win)
    hits = np.nonzero(d2[:n] > thr)[0]
    # one event per 10 ms
    out, last = [], -10**9
    for h in hits:
        if h - last > rate // 100:
            out.append(h)
        last = h
    return np.array(out, dtype=int)


def dropouts(x, rate, min_ms=5.0):
    """Runs of exact zeros at least min_ms long, between non-silent parts."""
    z = (x == 0)
    runs, i, n = [], 0, len(z)
    need = int(rate * min_ms / 1000)
    while i < n:
        if z[i]:
            j = i
            while j < n and z[j]:
                j += 1
            if j - i >= need and i > 0 and j < n:
                runs.append((i, j - i))
            i = j
        else:
            i += 1
    return runs


def repeats(x, rate, block=1024, max_lag_s=2.0, min_rms=0.01):
    """Blocks equal to an earlier block (correlation > 0.999, same level)."""
    nb = len(x) // block
    B = x[: nb * block].reshape(nb, block)
    rms = np.sqrt((B ** 2).mean(axis=1))
    norm = B / np.maximum(rms[:, None], 1e-9) / np.sqrt(block)
    max_lag = int(max_lag_s * rate / block)
    found = []
    for i in range(1, nb):
        if rms[i] < min_rms:
            continue
        lo = max(0, i - max_lag)
        if i - lo < 1:
            continue
        c = norm[lo:i] @ norm[i]
        j = int(np.argmax(c))
        if c[j] > 0.999 and abs(rms[lo + j] / rms[i] - 1) < 0.01:
            found.append((i, i - (lo + j), float(c[j])))
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("wav")
    ap.add_argument("--from", dest="t0", type=float, default=0)
    ap.add_argument("--to", dest="t1", type=float, default=None)
    ap.add_argument("--k", type=float, default=12.0, help="click threshold (x median |d2|)")
    ap.add_argument("--list", type=int, default=12, help="events to list")
    a = ap.parse_args()
    rate, x = load(a.wav)
    s0 = int(a.t0 * rate)
    s1 = int(a.t1 * rate) if a.t1 else len(x)
    x = x[s0:s1]
    dur = len(x) / rate
    print(f"{a.wav}: {dur:.1f} s at {rate} Hz, {x.shape[1]} channels (from {a.t0:.1f} s)")
    if len(x) == 0:
        return 1
    m = x.mean(axis=1)
    peak = float(np.abs(x).max())
    rms = float(np.sqrt((x ** 2).mean()))
    full = int((np.abs(x) >= 32767 / 32768).sum())
    knee = int((np.abs(x) > 0.8).sum())
    print(f"level: peak {peak:.3f}, RMS {rms:.4f} ({20*np.log10(max(rms,1e-9)):.1f} dBFS), "
          f"{full} samples at full scale, {100*knee/x.size:.3f}% over 0.8")
    c = clicks(m, rate, a.k)
    print(f"clicks: {len(c)} ({len(c)/max(dur,1e-9)*60:.1f} per minute)"
          + (": " + ", ".join(f"{(s0+i)/rate:.3f}" for i in c[: a.list]) if len(c) else ""))
    d = dropouts(m, rate)
    print(f"dropouts (exact silence >= 5 ms inside sound): {len(d)}"
          + (": " + ", ".join(f"{(s0+i)/rate:.3f} ({n*1000/rate:.0f} ms)" for i, n in d[: a.list]) if d else ""))
    r = repeats(m, rate)
    print(f"repeated 1024-frame blocks (lag 21 ms - 2 s): {len(r)}"
          + (": " + ", ".join(f"{(s0+i*1024)/rate:.3f} (lag {lag*1024/rate*1000:.0f} ms)" for i, lag, _ in r[: a.list]) if r else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
