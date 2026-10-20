"""Music tempo and beat-aligned cut planning (senso-01 v3, 20 Oct 2026)."""
from __future__ import annotations

import wave

import numpy as np


def load_mono(path: str) -> tuple[np.ndarray, int]:
    w = wave.open(path)
    sr, ch = w.getframerate(), w.getnchannels()
    a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32)
    return (a.reshape(-1, ch).mean(1) if ch > 1 else a) / 32768, sr


def tempo(a: np.ndarray, sr: int, lo_bpm: float = 70, hi_bpm: float = 180, hop: int = 256) -> tuple[float, float]:
    """(bpm, first beat in seconds) from onset strength autocorrelation."""
    n = len(a) // hop
    e = np.array([np.sum(a[i * hop:(i + 1) * hop] ** 2) for i in range(n)])
    on = np.maximum(0, np.diff(np.log(e + 1e-9)))
    fps = sr / hop
    x = on - on.mean()
    ac = np.correlate(x, x, "full")[len(x) - 1:]
    lo, hi = int(fps * 60 / hi_bpm), int(fps * 60 / lo_bpm)
    lag = lo + int(np.argmax(ac[lo:hi]))
    bpm = 60 * fps / lag
    period = lag
    phase = max(range(period), key=lambda p: sum(on[p + k * period] for k in range((len(on) - p) // period)))
    return bpm, phase / fps


def plan_cuts(clips: list[dict], speech: list[tuple[float, float] | None], beat: float, lead: float = 0.9,
              tail: float = 0.15, max_len: float = 4.0) -> list[dict]:
    """New start/end per clip: trim dead air before the line to `lead` s, end each clip so the cumulative cut lands on a beat.
    speech[i] = (first word start, last word end) in the clip's own time, or None. A clip's "max_end" (its take's length) is never
    passed: the senso test (21 Oct 2026) planned 4.11 s on a 4.0 s take and every caption after it drifted by 0.11 s."""
    out, acc = [], 0.0
    for c, sp in zip(clips, speech):
        start, end0 = c.get("start", 0.0), c["end"]
        if sp:
            first, last = sp
            if first - start > lead:
                start = round(first - lead, 2)
            end_min = last + tail
        else:
            end_min = start + 1.0
        end_max = min(end0 + 0.25, max_len, c.get("max_end", max_len))
        cands = [k * beat - acc + start for k in range(1, 400)]
        good = [e for e in cands if end_min <= e <= end_max]
        end = min(good, key=lambda e: abs(e - end0)) if good else max(end_min, min(end0, end_max))
        end = min(end, c.get("max_end", end))
        out.append(dict(c, start=start, end=round(end, 3)))
        acc += end - start
    return out


def punch_window(words: list[tuple[str, float, float]], start: float, end: float, zoom: float = 1.18) -> list[list[float]]:
    """Punch-in from the clip's punchline: the first word after the biggest pause (or the second half of the words)."""
    inside = [w for w in words if w[1] >= start]
    if len(inside) < 2:
        return [[round((end - start) / 2, 2), round(end - start + 1, 2), zoom]]
    gaps = [(inside[i + 1][1] - inside[i][2], i + 1) for i in range(len(inside) - 1)]
    gap, k = max(gaps)
    if gap <= 0.15:
        k = max(1, len(inside) // 2)
    p0 = max(0.0, inside[k][1] - start - 0.05)
    return [[round(p0, 2), round(end - start + 1, 2), zoom]]
