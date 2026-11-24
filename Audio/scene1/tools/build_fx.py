# Effects stem of scene 1 "Otliv": everything tied to an event of the timeline - breathing, electronics, engines, the
# touchdown, hatch and ramp, steps in the water, the drone (pan and Doppler from its real track), the beacon, the cutter,
# the cover falling, rain drops, thunder, alarm, creaks of the hull, the blow, bubbles, heartbeat, surfacing.
# All of it is synthesized. Times come from timeline.json (extract_timeline.py) and from the timeline scripts.
#   python -I build_fx.py  ->  work\fx.f32
import sys, os, math, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np
from scipy import signal
import dsp
from dsp import SR, F32, curve, vnoise, tt, bp, lp, hp, reson, Filt, Noise, Phase, Events, Reverb, pan2
from build_ambience import Bed

TL = json.load(open(os.path.join(HERE, 'timeline.json'), encoding='utf-8'))
TRK = np.array([r[:4] for r in TL['track']], dtype=np.float64)                 # t, listener x, y, yaw
DRN = np.array([r for r in TL['track'] if len(r) > 4], dtype=np.float64)       # + distance, bearing, height of the drone
PANEL = (128.29, 152.83); BEACON = (128.01, 153.32)


def where(t, x, y):
    """distance (m) and pan (-1..1) of a point of the world for the listener at time t"""
    px = np.interp(t, TRK[:, 0], TRK[:, 1]); py = np.interp(t, TRK[:, 0], TRK[:, 2]); yaw = np.interp(t, TRK[:, 0], TRK[:, 3])
    d = math.hypot(x - px, y - py)
    b = math.radians(math.degrees(math.atan2(y - py, x - px)) - yaw)
    return d, 0.85 * math.sin(b)


def near(d, ref=3.0, p=1.0): return min(1.0, (ref / max(d, 0.3)) ** p)
def depth_cm(t): return float(np.interp(t, [0, 280, 310, 370, 440, 470], [45, 45, 25, 10, 5, 5]))


# ------------------------------------------------------------------ one-shot sounds (all take a random generator first)
def env(n, a, d):
    t = np.arange(n) / SR
    return ((1.0 - np.exp(-t / max(a, 1e-4))) * np.exp(-t / d)).astype(F32)


def nz(rng, n, sos): return signal.sosfilt(sos, rng.standard_normal(n)).astype(F32)
def norm(x, peak=1.0): return (x * (peak / max(float(np.abs(x).max()), 1e-9))).astype(F32)
def fade(x, a=0.005, b=0.02):
    n = len(x); ka = min(int(a * SR), n // 2); kb = min(int(b * SR), n // 2)
    x[:ka] *= np.linspace(0, 1, ka, dtype=F32); x[n - kb:] *= np.linspace(1, 0, kb, dtype=F32); return x


def splash(rng, size=1.0, bright=1.0):
    n = int((0.5 + 0.7 * size) * SR); t = np.arange(n) / SR
    x = nz(rng, n, bp(350.0 / size ** 0.5, min(5500.0 * bright, 9000.0), 1)) * env(n, 0.004 + 0.006 * size, 0.10 + 0.16 * size)
    x += 0.7 * nz(rng, n, bp(150.0, 1200.0, 1)) * env(n, 0.02 * size, 0.18 + 0.25 * size)                     # the body of water
    x += (0.8 * size * np.sin(2 * np.pi * (95.0 / size ** 0.3) * t * (1 - 0.3 * np.minimum(t, 1.0))) * np.exp(-t / 0.06)).astype(F32)   # the plunge
    for k in range(int(3 + 5 * size)):                                                                         # drops falling back
        s = int((0.08 + rng.random() * (0.25 + 0.4 * size)) * SR); f = 1500.0 + rng.random() * 3500.0; m = int(0.03 * SR)
        if s + m < n:
            u = np.arange(m) / SR; x[s:s + m] += (0.25 * rng.random() * np.sin(2 * np.pi * f * u * (1 + 2 * u)) * np.exp(-u / 0.006)).astype(F32)
    return fade(norm(x))


def step_water(rng, depth=45.0, run=False, k=1.0):
    deep = min(1.0, depth / 45.0)
    x = splash(rng, size=(0.28 + 0.34 * deep) * (1.15 if run else 1.0), bright=1.25 - 0.4 * deep)
    if not run and deep > 0.4:                                   # the leg comes out: a second, softer slosh
        y = splash(rng, size=0.3, bright=0.6) * 0.45; d = int((0.24 + 0.08 * rng.random()) * SR)
        z = np.zeros(max(len(x), d + len(y)), dtype=F32); z[:len(x)] = x; z[d:d + len(y)] += y; x = z
    return x * k


def modal(rng, modes, dur, strike=0.3):
    """a struck object: decaying partials (frequency, decay time, level) and the short noise of the strike"""
    n = int(dur * SR); t = np.arange(n) / SR; x = np.zeros(n)
    for f, d, a in modes:
        x += a * np.sin(2 * np.pi * f * (1 + 0.01 * rng.standard_normal()) * t + rng.random() * 6.28) * np.exp(-t / d)
    x += strike * nz(rng, n, bp(300, 6000, 1)) * np.exp(-t / 0.012)
    return fade(norm(x), 0.001, 0.03)


def clunk(rng): return modal(rng, [(180, .09, 1), (410, .07, .6), (960, .05, .4), (1900, .03, .25)], 0.4)
def clank(rng): return modal(rng, [(72, .30, 1), (215, .35, .8), (540, .28, .6), (1310, .20, .45), (2480, .12, .3), (3900, .07, .2)], 1.6, 0.5)
def thud(rng): return modal(rng, [(62, .12, 1), (118, .08, .5), (300, .03, .2)], 0.5, 0.15)
def step_metal(rng): return modal(rng, [(140, .05, 1), (520, .04, .35), (1250, .025, .2)], 0.25, 0.35)
def click(rng): return modal(rng, [(2400, .008, 1), (4100, .005, .6)], 0.05, 0.5)


def pip(rng, f=1500.0, d=0.06, h2=0.0):
    t = np.arange(int(d * SR)) / SR
    return ((np.sin(2 * np.pi * f * t) + h2 * np.sin(4 * np.pi * f * t)) * np.sin(np.pi * t / d) ** 2).astype(F32)


def blip(rng):
    """quiet electronics of the cockpit: one to three short tones"""
    notes = [1320.0, 1760.0, 2093.0, 2637.0]; k = 1 + int(rng.random() * 3); gap = int(0.09 * SR)
    parts = []
    for i in range(k): parts += [pip(rng, notes[int(rng.random() * 4)], 0.04 + 0.03 * rng.random()), np.zeros(gap, dtype=F32)]
    return np.concatenate(parts)


def beeps(rng, f=1900.0, count=2, d=0.07, gap=0.09, h2=0.3):
    one = pip(rng, f, d, h2); g = np.zeros(int(gap * SR), dtype=F32)
    return np.concatenate([one, g] * count)


def servo(rng, dur=1.0, f0=200.0):
    n = int(dur * SR); t = np.arange(n) / SR
    ramp = np.minimum(1, t / 0.15) * np.minimum(1, (dur - t) / 0.2)
    ph = 2 * np.pi * np.cumsum(f0 * (0.6 + 0.4 * ramp) * (1 + 0.01 * np.sin(2 * np.pi * 7 * t))) / SR
    x = sum(np.sin(h * ph) / h ** 1.2 for h in range(1, 9)) * 0.5
    x = x + 0.35 * nz(rng, n, bp(f0 * 2, min(f0 * 12, 9000.0), 1))
    return fade(norm(x * ramp), 0.03, 0.06)


def hiss(rng, dur=1.6):
    n = int(dur * SR)
    return fade(norm(nz(rng, n, hp(1500, 2)) * env(n, 0.015, dur / 3.5)), 0.002, 0.05)


def breath(rng, period=4.0, heavy=0.0):
    """one breath inside a helmet: a brighter inhale, a short pause, a longer and duller exhale"""
    n1 = int(period * (0.36 - 0.06 * heavy) * SR); n2 = int(period * (0.44 + 0.04 * heavy) * SR); g = int(period * 0.05 * SR)
    t1 = np.arange(n1) / n1; t2 = np.arange(n2) / n2
    a = nz(rng, n1, bp(650 + 250 * heavy, 2900 + 900 * heavy, 1)) * np.sin(np.pi * t1 ** 0.8) ** 2 * (0.75 + 0.25 * heavy)
    b = nz(rng, n2, bp(300 + 150 * heavy, 1500 + 700 * heavy, 1)) * (t2 ** 0.35) * (1 - t2) ** 1.4 * 2.2
    x = np.concatenate([a, np.zeros(g), b]).astype(F32)
    x = x + 0.4 * signal.sosfilt(reson(680, 2.5), x).astype(F32)
    return (x * (0.3 / max(float(np.sqrt((x ** 2).mean())), 1e-9))).astype(F32)


def thunder(rng, dur=7.0):
    """a dull roll far inside the cloud of water: no crack, only the low rolling"""
    n = int(dur * SR); t = np.arange(n) / SR
    x = signal.lfilter([0.02], [1.0, -0.997], rng.standard_normal(n)); x = signal.sosfilt(lp(140, 2), x)
    m = int(dur * 3) + 1; roll = np.interp(t, np.linspace(0, dur, m), rng.random(m))
    x = x * (1 - np.exp(-t / 0.3)) * np.exp(-t / 2.4) * (0.5 + roll)
    y = signal.sosfilt(lp(60, 2), signal.lfilter([0.02], [1.0, -0.997], rng.standard_normal(n)))
    d = int(0.8 * SR); x[d:] += 0.5 * (y * (1 - np.exp(-t / 1.0)) * np.exp(-t / 3.5))[:n - d]
    return fade(norm(x), 0.05, 0.6)


def creak(rng, dur=1.4):
    """the hull under load: stick-slip pulses that speed up and slow down, ringing in the structure"""
    n = int(dur * SR); t = np.arange(n) / SR
    rate = 22.0 + 55.0 * np.interp(t, np.linspace(0, dur, 6), rng.random(6))
    ph = np.cumsum(rate) / SR; imp = np.zeros(n); idx = np.flatnonzero(np.diff(np.floor(ph)) > 0)
    imp[idx] = 0.5 + rng.random(len(idx))
    x = np.zeros(n)
    for f, q in ((240, 18), (610, 24), (1180, 28), (2300, 22)):
        x += signal.sosfilt(reson(f * (0.9 + 0.2 * rng.random()), q), imp)
    return fade(norm(x * np.sin(np.pi * t / dur) ** 0.7), 0.01, 0.1)


def groan(rng, dur=3.2):
    """the hull deep under water: a slow moan that bends in pitch"""
    n = int(dur * SR); t = np.arange(n) / SR
    f = np.interp(t, np.linspace(0, dur, 5), 52.0 + 30.0 * rng.random(5)) * (1 + 0.012 * np.sin(2 * np.pi * 4.3 * t))
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) + 0.5 * np.sin(2 * ph + 1.0) + 0.33 * np.sin(3 * ph + 2.0) + 0.2 * np.sin(5 * ph)
    x = signal.sosfilt(lp(420, 2), x + 0.15 * rng.standard_normal(n))
    return fade(norm(x * np.sin(np.pi * t / dur) ** 1.5), 0.05, 0.2)


def whoosh(rng, dur=1.1, f0=250.0, f1=5000.0):
    """water rushing over the glass: a band of noise that sweeps upward"""
    n = int(dur * SR); t = np.arange(n) / SR; x = rng.standard_normal(n); out = np.zeros(n)
    bands = np.geomspace(f0, f1, 7)
    for k, f in enumerate(bands):
        c = k / 6.0 * dur * 0.85
        out += signal.sosfilt(bp(f * 0.75, f * 1.3, 1), x) * np.exp(-((t - c) / (dur * 0.22)) ** 2)
    return fade(norm(out * np.minimum(1, t / 0.08)), 0.01, 0.05)


def impact(rng):
    """the blow of the wall of water: a boom that falls in pitch, a crush of the structure, a burst of noise"""
    n = int(3.2 * SR); t = np.arange(n) / SR
    f = 26.0 + 70.0 * np.exp(-t / 0.35)
    x = 1.0 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.9)
    x += 0.8 * signal.sosfilt(lp(500, 2), rng.standard_normal(n)) * np.exp(-t / 0.35)
    x += 0.35 * signal.sosfilt(bp(500, 4000, 1), rng.standard_normal(n)) * np.exp(-t / 0.07)
    for fm, d in ((180, .25), (370, .22), (820, .16), (1500, .10)):
        x += 0.25 * np.sin(2 * np.pi * fm * t + rng.random() * 6.28) * np.exp(-t / d)
    return fade(norm(x), 0.001, 0.3)


def heart(rng, soft=0.0):
    n = int(0.6 * SR); t = np.arange(n) / SR; x = np.zeros(n)
    for t0, f, a in ((0.0, 58.0, 1.0), (0.26 + 0.02 * soft, 72.0, 0.7)):
        u = np.maximum(t - t0, 0.0); x += a * np.sin(2 * np.pi * f * u) * np.exp(-u / 0.07) * (t >= t0)
    return fade(x.astype(F32), 0.002, 0.05)


def slap(rng):
    """the swell slapping the floating hull"""
    n = int(1.1 * SR); t = np.arange(n) / SR
    x = np.sin(2 * np.pi * (70 + 40 * rng.random()) * t) * np.exp(-t / 0.12) + 0.6 * signal.sosfilt(lp(1200, 1), rng.standard_normal(n)) * env(n, 0.03, 0.25)
    return fade(norm(x), 0.005, 0.1)


def surface(rng):
    """the ship breaks the surface: the dull world opens up"""
    n = int(3.5 * SR); t = np.arange(n) / SR
    x = signal.sosfilt(bp(250, 7000, 1), rng.standard_normal(n)) * (1 - np.exp(-t / 0.15)) * np.exp(-t / 1.1)
    x += 0.8 * np.sin(2 * np.pi * (60 + 50 * np.exp(-t / 0.2)) * t) * np.exp(-t / 0.35)
    return fade(norm(x), 0.005, 0.3)


# ------------------------------------------------------------------ continuous layers
class Ticks:
    """a rain of tiny impacts: random impulses through ringing filters (drops on a helmet or a canopy, babble of running
    water, bubbles, rattle of the airframe, sparks). The curve `rate` is impacts per second, `gain` their level."""
    def __init__(self, seed, freqs, q, rate, gain):
        self.r = np.random.default_rng(seed); self.rate = curve(rate); self.gain = curve(gain)
        self.t0 = min(rate[0][0], gain[0][0]); self.t1 = max(rate[-1][0], gain[-1][0])
        self.f = []
        for fc in freqs:
            sos = reson(fc, q); imp = np.zeros(4096); imp[0] = 1.0
            self.f.append((Filt(sos), 1.0 / float(np.abs(signal.sosfilt(sos, imp)).max())))
    def render(self, buf, i0, n):
        if (i0 + n) / SR <= self.t0 or i0 / SR >= self.t1: return
        t = tt(i0, n); p = self.rate(t) / (SR * len(self.f)); g = self.gain(t)
        out = np.zeros((n, 2), dtype=F32)
        for flt, k in self.f:
            idx = np.flatnonzero(self.r.random(n, dtype=F32) < p)
            x = np.zeros((n, 2), dtype=F32)
            if len(idx):
                a = (0.25 + 0.75 * self.r.random(len(idx)) ** 2) * k; th = self.r.random(len(idx)) * (math.pi / 2)
                x[idx, 0] = a * np.cos(th); x[idx, 1] = a * np.sin(th)
            out += flt(x)
        buf += out * g[:, None]


class Whine:
    """a turbine or a starter: a tone whose pitch follows a curve, with a few partials and a slight unsteadiness"""
    def __init__(self, freq, gain, partials=((1, 1.0), (2, 0.5), (3.01, 0.3), (4.03, 0.18)), wob=0.006, pan=0.0):
        self.freq = curve(freq); self.gain = curve(gain); self.partials = partials; self.wob = wob; self.pan = pan
        self.t0, self.t1 = gain[0][0], gain[-1][0]; self.ph = Phase()
    def render(self, buf, i0, n):
        if (i0 + n) / SR <= self.t0 or i0 / SR >= self.t1: return
        t = tt(i0, n); f = self.freq(t) * (1.0 + self.wob * (2.0 * vnoise(t, 5.0, 77) - 1.0))
        ph = self.ph(f); x = np.zeros(n)
        for m, a in self.partials: x += a * np.sin(m * ph)
        buf += pan2((x * self.gain(t)).astype(F32), self.pan)


class Drone:
    """the quadcopter 'Svetlyak': four rotors slightly out of tune; loudness, side and Doppler come from its real track"""
    def __init__(self):
        self.t = DRN[:, 0]; k = np.ones(11) / 11.0
        self.d = np.convolve(np.pad(DRN[:, 4], 5, mode='edge'), k, mode='valid')
        self.b = np.unwrap(np.radians(DRN[:, 5]))
        self.v = np.gradient(self.d, self.t)                      # radial speed, m/s (+ = flying away)
        self.ph = [Phase() for _ in range(4)]; self.noise = Noise(301, 'white', ch=0); self.flt = Filt(bp(900, 6000, 1), ch=0)
        self.spin = curve([(106.0, 0.5), (108.5, 1.0), (394.5, 1.0), (397.0, 0.45)])
        self.lvl = curve([(106.0, 0.0), (106.6, 1.0), (396.4, 1.0), (397.0, 0.0)])
    def render(self, buf, i0, n):
        if (i0 + n) / SR <= 106.0 or i0 / SR >= 397.0: return
        t = tt(i0, n); d = np.interp(t, self.t, self.d); b = np.interp(t, self.t, self.b); v = np.interp(t, self.t, self.v)
        dop = 1.0 / (1.0 + np.clip(v, -30, 30) / 343.0)
        # work harder when it moves fast or carries the storage (after 4:54)
        load = 1.0 + 0.012 * np.abs(v) + 0.05 * (t > 294.0) * (t < 397.0)
        x = np.zeros(n)
        for k, f0 in enumerate((188.0, 197.0, 206.5, 215.0)):
            f = f0 * dop * self.spin(t) * load * (1.0 + 0.012 * (vnoise(t, 1.7, 100 + k) - 0.5))
            ph = self.ph[k](f)
            for h in range(1, 8):
                x += np.sin(h * ph + k + h) * (h ** -1.0) * np.exp(-0.035 * h * np.minimum(d, 20.0))
        amp = 0.05 * np.minimum(1.0, 1.6 / np.maximum(d, 0.8)) * self.lvl(t)
        mono = (x * 0.25 + 0.35 * self.flt(self.noise(n))) * amp
        mono = mono * (0.8 + 0.2 * np.cos(b))                     # a little duller and quieter from behind
        buf += pan2(mono.astype(F32), 0.85 * np.sin(b))


class Cutter:
    """the drone's cutter on the cover of the niche: a sputtering arc - bursts of hiss over a harsh mains-like buzz"""
    def __init__(self):
        self.noise = Noise(401, 'white', ch=0); self.hp = Filt(hp(1800, 2), ch=0); self.bpf = Filt(bp(300, 3200, 1), ch=0); self.ph = Phase()
    def render(self, buf, i0, n):
        if (i0 + n) / SR <= 250.0 or i0 / SR >= 272.2: return
        t = tt(i0, n)
        gate = np.clip((vnoise(t, 17.0, 61) - 0.35) * 6.0, 0, 1) * np.clip((vnoise(t, 1.3, 62) - 0.15) * 5.0, 0.15, 1)
        gate = gate * (t > 250.0) * (t < 272.0)
        ph = self.ph(np.full(n, 100.0)); buzz = sum(np.sin(h * ph) / h for h in range(1, 24))
        x = 0.9 * self.hp(self.noise(n)) + 0.5 * self.bpf(buzz.astype(F32))
        d, p = where(float(t[n // 2]), *PANEL)
        buf += pan2((x * gate * 0.030 * near(d, 3.3)).astype(F32), p)


class Alarm:
    """master caution of the panel: two notes and a pause, over and over; under water only its dull ghost is left"""
    def __init__(self, gain, dull=False):
        self.gain = curve(gain); self.t0, self.t1 = gain[0][0], gain[-1][0]; self.dull = dull
    def render(self, buf, i0, n):
        if (i0 + n) / SR <= self.t0 or i0 / SR >= self.t1: return
        t = tt(i0, n); u = (t - 402.0) % 1.2
        a = (u < 0.22); b = (u >= 0.26) & (u < 0.48)
        e = np.where(a, np.sqrt(np.clip(np.sin(np.pi * u / 0.22), 0, 1)), 0.0) + np.where(b, np.sqrt(np.clip(np.sin(np.pi * (u - 0.26) / 0.22), 0, 1)), 0.0)
        f = np.where(a, 932.0, 740.0)
        x = np.sin(2 * np.pi * f * u)
        if not self.dull: x = x + 0.4 * np.sin(4 * np.pi * f * u) + 0.2 * np.sin(6 * np.pi * f * u)
        m = (x * e * self.gain(t)).astype(F32)
        buf[:, 0] += m * 0.8; buf[:, 1] += m * 1.0                 # the panel is a little to the right


# ------------------------------------------------------------------ the score of events
E = Events()
r0 = np.random.default_rng(5)

# cockpit electronics: sparse tones; the probe's "all is well" ticking on the monitor while in orbit
t = 2.5
while t < 548.0:
    if t < 50 or 86 < t < 100 or 399 < t < 458 or 503 < t < 546:
        E.add(t, blip, gain=0.011 if t < 100 else 0.008, pan=float(r0.uniform(-0.6, 0.6)))
    t += float(r0.uniform(3.0, 8.0)) if t < 100 else float(r0.uniform(6.0, 14.0))
for k in range(2, 32): E.add(k * 1.6, pip, gain=0.006, pan=0.3, f=880.0, d=0.06)

# breathing: calm in orbit and on the walk, heavy on the run back, held under water, a gasp after surfacing
RATE = curve([(0, 13), (50, 14), (56, 20), (96, 20), (104, 16), (215, 17), (300, 18), (331, 22), (338, 40), (350, 50), (386, 52), (392, 46),
              (399, 38), (410, 28), (430, 24), (459, 28), (466, 22), (499, 22), (500.5, 32), (510, 24), (522, 17), (548, 15)])
BLVL = curve([(0, .010), (50, .012), (56, .006), (100, .010), (112, .016), (300, .018), (331, .024), (345, .045), (388, .050), (392, .045),
              (399, .035), (410, .022), (430, .020), (459.5, .020), (466, .012), (498, .014), (500.5, .034), (506, .030), (515, .018),
              (540, .012), (547, .0)])
t = 1.0
while t < 546.0:
    per = 60.0 / float(RATE(np.array([t]))[0])
    if not (459.6 < t < 466.0):                                    # the breath is held through the blow
        heavy = float(np.clip((float(RATE(np.array([t]))[0]) - 18.0) / 30.0, 0, 1))
        E.add(t, breath, gain=float(BLVL(np.array([t]))[0]) / 0.3, period=per * 0.92, heavy=heavy)
    t += per * (1.0 + 0.06 * float(r0.standard_normal()))

# touchdown
E.add(100.42, splash, gain=0.20, size=2.2, bright=0.8); E.add(100.45, thud, gain=0.16)
E.add(100.60, splash, gain=0.12, size=1.6, bright=0.7, pan=-0.5); E.add(100.62, splash, gain=0.12, size=1.6, bright=0.7, pan=0.5)

# leaving: cockpit door, airlock, hatch, ramp; steps inside
E.add(105.0, servo, gain=0.016, dur=2.8, f0=240.0); E.add(107.0, clunk, gain=0.035); E.add(107.05, hiss, gain=0.050, dur=1.8)
E.add(107.4, servo, gain=0.010, dur=3.5, f0=200.0); E.add(106.0, servo, gain=0.014, dur=6.0, f0=150.0)
E.add(112.0, clunk, gain=0.045); E.add(112.05, splash, gain=0.030, size=0.6)
for k, ts in enumerate(np.arange(104.6, 118.6, 0.78)):
    E.add(float(ts), step_metal, gain=0.022 if ts < 112 else 0.03, pan=0.2 * (1 if k % 2 else -1))

# steps in the water (and the last ones on the ramp)
for ts, v, side, rnd in TL['steps']:
    if ts > 386.6:
        E.add(ts, step_metal, gain=0.045, pan=0.2 * side); continue
    run = v > 3.0
    E.add(ts, step_water, gain=(0.062 if run else 0.042) * (0.75 + 0.5 * rnd), pan=0.25 * side, depth=depth_cm(ts), run=run)

# the drone speaks: a chirp when it sets off, alarm beeps on the way back
def at_drone(ts):
    i = int(np.argmin(np.abs(DRN[:, 0] - ts))); return DRN[i, 4], 0.85 * math.sin(math.radians(DRN[i, 5]))
for ts, f in ((108.6, 1568.0), (108.78, 2093.0), (131.5, 1760.0), (131.68, 2349.0), (166.0, 2093.0)):
    d, p = at_drone(ts); E.add(ts, pip, gain=0.020 * near(d, 3.0), pan=p, f=f, d=0.09, h2=0.2)
ts = 331.5
while ts < 392.0:
    d, p = at_drone(ts); E.add(ts, beeps, gain=0.030 * near(d, 4.0, 0.8), pan=p, f=1900.0, count=2)
    ts += 1.9

# the beacon of the wreck blinks every 1.6 s and beeps with it
for k in range(int(150 / 1.6), int(389.5 / 1.6)):
    ts = k * 1.6; d, p = where(ts, *BEACON)
    g = 0.030 * near(d, 8.0, 1.2)
    if g > 0.0006: E.add(ts, pip, gain=g, pan=p, f=2960.0, d=0.11, h2=0.15)

# the niche: the arm, the cutter, the cover pops and falls, the storage comes out, the drone takes it
d, p = where(243.0, *PANEL); E.add(240.0, servo, gain=0.008 * near(d, 4.0), pan=p, dur=6.0, f0=320.0)
d, p = where(272.0, *PANEL); E.add(272.0, clunk, gain=0.06 * near(d, 3.3), pan=p)
d, p = where(273.4, *PANEL); E.add(273.42, splash, gain=0.11 * near(d, 3.3), pan=p, size=1.1, bright=0.9)
E.add(273.1, pip, gain=0.010, pan=p, f=880.0, d=0.12); E.add(273.28, pip, gain=0.010, pan=p, f=1320.0, d=0.16)
E.add(278.0, servo, gain=0.006, pan=p, dur=14.0, f0=95.0)
E.add(294.6, click, gain=0.030, pan=p); E.add(295.2, click, gain=0.022, pan=p)

# thunder: a far roll before the rain, then one after each flash inside the cloud of water (6:51, 7:13.5, 7:29)
E.add(376.0, thunder, gain=0.10, pan=0.3, dur=6.0)
E.add(412.2, thunder, gain=0.20, pan=-0.2); E.add(434.7, thunder, gain=0.26, pan=0.2); E.add(450.2, thunder, gain=0.30, pan=0.0)

# coming back: steps inside, the ramp goes up, the hatch slams, the seal hisses, the cockpit door, the seat
for k, ts in enumerate(np.arange(390.5, 398.4, 0.62)): E.add(float(ts), step_metal, gain=0.035, pan=0.2 * (1 if k % 2 else -1))
E.add(393.0, servo, gain=0.012, dur=5.0, f0=150.0); E.add(394.0, servo, gain=0.012, dur=3.0, f0=200.0)
E.add(397.0, clank, gain=0.34); E.add(397.0, thud, gain=0.14); E.add(397.3, hiss, gain=0.045, dur=1.2)
E.add(398.0, servo, gain=0.014, dur=2.9, f0=240.0); E.add(400.9, thud, gain=0.06); E.add(399.3, thud, gain=0.03); E.add(400.4, click, gain=0.02, pan=0.3)

# the wall: the hull creaks, water climbs over the glass, the blow
for ts, g in ((441.0, .05), (446.4, .06), (451.0, .10), (454.2, .08), (457.6, .10), (459.3, .12)):
    E.add(ts, creak, gain=g, pan=float(r0.uniform(-0.5, 0.5)), dur=float(r0.uniform(1.0, 1.8)))
E.add(458.9, whoosh, gain=0.22, dur=1.15)
E.add(460.0, impact, gain=0.85)

# under water: the hull moans, the heart beats
for ts, g in ((462.5, .10), (468.5, .07), (476.0, .07), (485.0, .06), (493.5, .06)):
    E.add(ts, groan, gain=g, pan=float(r0.uniform(-0.4, 0.4)), dur=float(r0.uniform(2.6, 3.8)))
BPM = curve([(462, 116), (475, 104), (490, 92), (499, 88)])
ts = 462.0
while ts < 499.0:
    E.add(ts, heart, gain=float(np.interp(ts, [462, 464, 490, 499], [0.0, 0.11, 0.10, 0.05])))
    ts += 60.0 / float(BPM(np.array([ts]))[0])

# surfacing and afterwards: the swell slaps the hull, one beep of the panel that is still alive
E.add(499.95, surface, gain=0.34); E.add(502.4, creak, gain=0.04, dur=1.2)
ts = 503.5
while ts < 546.0:
    E.add(ts, slap, gain=float(r0.uniform(0.03, 0.05)), pan=float(r0.uniform(-0.7, 0.7))); ts += float(r0.uniform(3.5, 6.0))
E.add(507.5, pip, gain=0.02, pan=0.3, f=932.0, d=0.22)

L = [E, Drone(), Cutter()]
# engines: thrust for the landing and the wind-down; the purge, the starter, the spin-up cut by the blow
L.append(Whine([(84, 300), (90, 900), (96, 1250), (100.5, 1250), (102, 700), (104, 520), (108, 260), (112, 90)],
               [(84, 0), (90, .010), (96, .014), (100.5, .014), (104, .008), (110, .003), (112.5, 0)]))
L.append(Bed(501, 'pink', bp(120, 2200, 1), [(84, 0), (90, .05), (96, .10), (100.5, .10), (102, .045), (104, .030), (109, .008), (112.5, 0)], mods=[(4.0, 0.2, 81)]))
L.append(Bed(502, 'brown', lp(140, 2), [(84, 0), (96, .10), (100.5, .10), (103, .03), (110, 0)]))
L.append(Bed(503, 'pink', bp(400, 3000, 1), [(411.5, 0), (413, .028), (448, .032), (452, .020), (459.9, .020), (460.03, 0)], mods=[(2.2, 0.9, 82)]))
L.append(Whine([(412, 110), (430, 260), (448, 420), (452, 700), (459.9, 1500)], [(412, 0), (414, .008), (448, .012), (455, .020), (459.9, .030), (460.03, 0)], wob=0.03))
L.append(Bed(504, 'pink', bp(150, 2500, 1), [(448, 0), (452, .03), (459.9, .10), (460.03, 0)]))
# spray of the skis on the water
L.append(Bed(505, 'white', bp(800, 6000, 1), [(96, 0), (99.6, .02), (100.4, .05), (100.9, .11), (102.5, .05), (105.5, 0)], mods=[(7.0, 0.4, 83)]))
# rattle of the airframe: entry, the slide, the wave lifting the ship
L.append(Ticks(601, [310, 730, 1420, 2650], 16, [(52, 0), (57, 26), (63.5, 32), (68, 18), (72, 0)], [(52, 0), (57, .05), (63.5, .06), (68, .03), (72, 0)]))
L.append(Ticks(602, [310, 730, 1420, 2650], 16, [(99.5, 0), (100.6, 30), (103, 0)], [(99.5, 0), (100.6, .05), (103, 0)]))
L.append(Ticks(603, [260, 640, 1300, 2400], 16, [(450, 0), (453, 18), (459.9, 34), (460.05, 0)], [(450, 0), (453, .03), (459.9, .08), (460.05, 0)]))
# sparks of the cutter
L.append(Ticks(604, [3200, 4300, 5600, 7000], 8, [(250, 0), (250.3, 25), (272, 25), (272.1, 0)], [(250, 0), (250.3, .006), (272, .006), (272.1, 0)]))
# running water babbles
L.append(Ticks(605, [520, 700, 930, 1200, 1500, 1850, 2300, 2800, 3300, 3800], 14, [(280, 0), (300, 40), (331, 110), (389.6, 160), (397.1, 160)],
               [(280, 0), (300, .006), (331, .012), (370, .018), (389.6, .020), (390.0, .008), (396.95, .008), (397.1, 0)]))
# rain: drops on the helmet, then on the canopy, the last of it after the wave
L.append(Ticks(606, [1800, 2400, 3100, 4000, 5200], 9, [(336, 0), (345, 6), (370, 30), (389.6, 55), (389.8, 0)], [(336, 0), (345, .012), (389.6, .020), (389.9, 0)]))
L.append(Ticks(607, [900, 1300, 1700, 2300, 3000], 7, [(389.8, 0), (391, 25), (399, 60), (430, 120), (458, 130), (460.0, 0)], [(389.8, 0), (391, .010), (430, .018), (458, .020), (460.02, 0)]))
L.append(Ticks(608, [900, 1300, 1700, 2300, 3000], 7, [(500.4, 0), (501, 60), (512, 12), (525, 0)], [(500.4, 0), (501, .012), (512, .008), (525, 0)]))
# alarm of the panel, and its ghost under water
L.append(Alarm([(402.0, 0), (402.2, .022), (459.9, .026), (460.0, 0)]))
L.append(Alarm([(460.2, 0), (460.6, .012), (497, .006), (499, 0)], dull=True))
# bubbles
L.append(Ticks(609, [240, 330, 450, 610, 820, 1100], 10, [(460.05, 0), (460.2, 90), (464, 40), (470, 14), (498, 6), (500.0, 30), (500.4, 0)],
               [(460.05, 0), (460.3, .05), (465, .03), (498, .016), (500.4, 0)]))
# water running off the canopy after surfacing
L.append(Ticks(610, [1200, 1700, 2400, 3300, 4300], 10, [(500.2, 0), (500.4, 160), (504, 60), (510, 14), (520, 2), (530, 0)], [(500.2, 0), (500.4, .030), (504, .020), (510, .010), (530, 0)]))
L.append(Bed(506, 'white', bp(2000, 8000, 1), [(500.2, 0), (500.6, .03), (504, .01), (509, 0)], mods=[(3.0, 0.4, 84)]))

# the space around: a metal room inside the ship, almost nothing in the open, a long dull tail under water
ROOM = Reverb(0.55, seed=3, lo=200.0, hi=5000.0)
SEND = curve([(0, .22), (104, .22), (112, .25), (113.5, .03), (389.6, .03), (390.0, .25), (459.9, .22), (460.1, .35), (499.9, .35), (500.2, .20), (549, .20)])


def post(buf, i0, n):
    return buf + ROOM(buf * SEND(tt(i0, n))[:, None])


if __name__ == '__main__':
    dsp.render('fx', L, post)
