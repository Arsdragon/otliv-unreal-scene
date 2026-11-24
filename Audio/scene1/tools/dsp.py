# Small synthesis toolkit for the scene-1 soundtrack. Everything is rendered in chunks of a few seconds, so memory stays
# low (the PC is short of RAM): layers keep their filter states and phases between chunks and must be rendered in order.
import os, math, wave
import numpy as np
from scipy import signal

SR = 48000
DUR = 550.0
N = int(SR * DUR)
CHUNK = 6 * SR
F32 = np.float32
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))          # ...\Audio\scene1
WORK = os.path.join(ROOT, 'work')

_TAB = np.random.default_rng(20261122).random(8192).astype(F32)


def tt(i0, n):
    """time of every sample of a chunk, seconds (float64: 26 million samples do not fit float32 precisely)"""
    return (i0 + np.arange(n, dtype=np.float64)) / SR


def curve(pts):
    """piecewise-linear curve by (time, value) points -> function of a time array"""
    xs = np.array([p[0] for p in pts], dtype=np.float64); ys = np.array([p[1] for p in pts], dtype=np.float64)
    return lambda t: np.interp(t, xs, ys).astype(F32)


def vnoise(t, rate, seed=0):
    """smooth value noise 0..1 of absolute time: needs no state, so gusts and wobbles are the same on every run"""
    x = np.asarray(t, dtype=np.float64) * rate
    i = np.floor(x).astype(np.int64); f = (x - i).astype(F32); f = f * f * (3.0 - 2.0 * f)
    a = _TAB[(i * 7 + seed * 131) & 8191]; b = _TAB[((i + 1) * 7 + seed * 131) & 8191]
    return a + (b - a) * f


def db(x): return 10.0 ** (x / 20.0)


def bp(lo, hi, order=2): return signal.butter(order, [lo, hi], btype='band', fs=SR, output='sos')
def lp(fc, order=2): return signal.butter(order, fc, btype='low', fs=SR, output='sos')
def hp(fc, order=2): return signal.butter(order, fc, btype='high', fs=SR, output='sos')


def reson(fc, q):
    """two-pole resonator: an impulse through it rings and dies away (ticks, drops, bubbles, metal)"""
    b, a = signal.iirpeak(fc, q, fs=SR)
    return np.array([[b[0], b[1], b[2], 1.0, a[1], a[2]]])


class Filt:
    """a filter that remembers its state from chunk to chunk"""
    def __init__(self, sos, ch=2):
        self.sos = np.asarray(sos, dtype=np.float64)
        self.zi = np.zeros((self.sos.shape[0], 2, ch)) if ch else np.zeros((self.sos.shape[0], 2))
    def __call__(self, x):
        y, self.zi = signal.sosfilt(self.sos, x, axis=0, zi=self.zi)
        return y.astype(F32)


class Noise:
    """white, pink or brown noise, mono or stereo (independent channels), continuous between chunks"""
    PB = [0.049922035, -0.095993537, 0.050612699, -0.004408786]; PA = [1.0, -2.494956002, 2.017265875, -0.522189400]
    def __init__(self, seed, color='white', ch=2):
        self.r = np.random.default_rng(seed); self.color = color; self.ch = ch
        self.zi = np.zeros((3, ch)) if ch else np.zeros(3)
        self.zb = np.zeros((1, ch)) if ch else np.zeros(1)
    def __call__(self, n):
        x = self.r.standard_normal((n, self.ch) if self.ch else n, dtype=F32)
        if self.color == 'pink':
            x, self.zi = signal.lfilter(self.PB, self.PA, x, axis=0, zi=self.zi); x = x * 6.0
        elif self.color == 'brown':
            x, self.zb = signal.lfilter([0.02], [1.0, -0.997], x, axis=0, zi=self.zb); x = x * 3.5
        return x.astype(F32)


def pan2(mono, p):
    """equal-power pan: p = -1 left ... +1 right (number or array)"""
    a = (np.clip(p, -1.0, 1.0) + 1.0) * (math.pi / 4.0)
    out = np.empty((len(mono), 2), dtype=F32)
    out[:, 0] = mono * np.cos(a); out[:, 1] = mono * np.sin(a)
    return out


class Phase:
    """phase accumulator for an oscillator whose frequency changes in time"""
    def __init__(self): self.p = 0.0
    def __call__(self, freq):
        ph = self.p + np.cumsum(np.asarray(freq, dtype=np.float64)) * (2.0 * math.pi / SR)
        self.p = float(ph[-1] % (2.0 * math.pi)) if len(ph) else self.p
        return ph


class Events:
    """one-shot sounds placed on the timeline; each is generated when its chunk comes (and cached while it lasts)"""
    def __init__(self):
        self.ev = []; self.cache = {}; self.done = set()
    def add(self, t, fn, gain=1.0, pan=0.0, **kw):
        self.ev.append((int(round(t * SR)), fn, gain, pan, kw)); return self
    def prepare(self):
        self.ev.sort(key=lambda e: e[0]); self.starts = np.array([e[0] for e in self.ev], dtype=np.int64); self.maxlen = 0
    def render(self, buf, i0, n):
        if not hasattr(self, 'starts'): self.prepare()
        lo = np.searchsorted(self.starts, i0 - 30 * SR); hi = np.searchsorted(self.starts, i0 + n)
        for k in range(lo, hi):
            if k in self.done: continue
            s, fn, gain, pan, kw = self.ev[k]
            a = self.cache.get(k)
            if a is None:
                a = np.asarray(fn(np.random.default_rng(1000 + k), **kw), dtype=F32)
                if a.ndim == 1: a = pan2(a, pan)
                a = a * gain
                self.cache[k] = a
            e = s + len(a)
            b0 = max(s, i0); b1 = min(e, i0 + n)
            if b1 > b0: buf[b0 - i0:b1 - i0] += a[b0 - s:b1 - s]
            if e <= i0 + n:
                self.cache.pop(k, None); self.done.add(k)


class Reverb:
    """convolution with decaying noise: a room, a hull, an open distance. Stereo, the tail carries over between chunks"""
    def __init__(self, seconds, seed=1, lo=150.0, hi=6000.0, pre=0.012):
        r = np.random.default_rng(seed); m = int(seconds * SR); t = np.arange(m) / SR
        ir = r.standard_normal((m, 2)) * np.exp(-6.9 * t / seconds)[:, None]
        ir = signal.sosfilt(bp(lo, hi, 1), ir, axis=0)
        ir[:int(pre * SR)] = 0.0
        ir /= np.sqrt((ir ** 2).sum(axis=0)).max()
        self.ir = ir.astype(F32); self.tail = np.zeros((m, 2), dtype=F32)
    def __call__(self, x):
        n = len(x); m = len(self.ir)
        y = np.stack([signal.fftconvolve(x[:, c], self.ir[:, c]) for c in (0, 1)], axis=1).astype(F32)   # n + m - 1
        k = min(m, len(y)); y[:k] += self.tail[:k]
        out = y[:n].copy()
        nt = np.zeros((m, 2), dtype=F32)
        rest = y[n:]
        nt[:len(rest)] = rest                 # the old tail beyond this chunk is already inside y
        self.tail = nt
        return out


class RawOut:
    """intermediate stem: raw float32 stereo on disk (no clipping, no headroom worries); peak and rms are tracked"""
    def __init__(self, name):
        os.makedirs(WORK, exist_ok=True)
        self.path = os.path.join(WORK, name + '.f32'); self.f = open(self.path, 'wb'); self.peak = 0.0; self.sq = 0.0; self.n = 0
    def write(self, buf):
        b = np.ascontiguousarray(buf, dtype=F32)
        self.peak = max(self.peak, float(np.abs(b).max()) if len(b) else 0.0); self.sq += float((b.astype(np.float64) ** 2).sum()); self.n += b.size
        self.f.write(b.tobytes())
    def close(self):
        self.f.close()
        return self.peak, 10.0 * math.log10(max(self.sq / max(self.n, 1), 1e-20))


def raw_reader(name, chunk=CHUNK):
    p = os.path.join(WORK, name + '.f32')
    with open(p, 'rb') as f:
        while True:
            b = f.read(chunk * 8)
            if not b: break
            yield np.frombuffer(b, dtype=F32).reshape(-1, 2)


def render(name, layers, post=None, t0=0.0, t1=DUR, verbose=True):
    """layers: objects with render(buf, i0, n) adding into a stereo float32 buffer. Always starts at 0 (states), t0/t1 only limit writing."""
    out = RawOut(name)
    for i0 in range(0, N, CHUNK):
        n = min(CHUNK, N - i0)
        buf = np.zeros((n, 2), dtype=F32)
        if (i0 + n) / SR > t0 and i0 / SR < t1:
            for L in layers: L.render(buf, i0, n)
            if post is not None: buf = post(buf, i0, n)
        out.write(buf)
    pk, rms = out.close()
    if verbose: print('%s: peak %.3f (%.1f dBFS), rms %.1f dB' % (name, pk, 20 * math.log10(max(pk, 1e-9)), rms))
    return pk, rms


def write_wav24(path, chunks, gain=1.0):
    """stereo float chunks -> 24-bit PCM WAV; returns (peak after gain, number of clipped samples)"""
    w = wave.open(path, 'wb'); w.setnchannels(2); w.setsampwidth(3); w.setframerate(SR)
    peak = 0.0; clipped = 0
    for c in chunks:
        x = c.astype(np.float64) * gain
        peak = max(peak, float(np.abs(x).max()) if len(x) else 0.0)
        clipped += int((np.abs(x) > 1.0).sum())
        v = np.clip(np.round(x * 8388607.0), -8388608, 8388607).astype('<i4')
        w.writeframes(v.view(np.uint8).reshape(-1, 4)[:, :3].tobytes())
    w.close()
    return peak, clipped


def read_wav(path):
    """whole WAV (16/24-bit PCM) -> (float32 array (n, ch), rate). For short files: voice lines."""
    w = wave.open(path, 'rb'); ch, sw, rate, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
    raw = w.readframes(n); w.close()
    if sw == 2: x = np.frombuffer(raw, dtype='<i2').astype(F32) / 32768.0
    elif sw == 3:
        b = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3)
        x = ((b[:, 0].astype(np.int32) | (b[:, 1].astype(np.int32) << 8) | (b[:, 2].astype(np.int8).astype(np.int32) << 16))).astype(F32) / 8388608.0
    else: raise ValueError('unsupported sample width %d' % sw)
    return x.reshape(-1, ch), rate
