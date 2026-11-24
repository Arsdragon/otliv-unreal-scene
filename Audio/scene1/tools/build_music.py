# Music stem of scene 1 "Otliv": an original quiet ambient made of sine partials only - no samples, no borrowed themes.
#   0:30  a low tone enters in orbit           1:45  light, rare glass-like notes over a soft major chord
#   3:45  a low note appears under them        5:10  a pulse and a tightening cluster for the flight back
#   7:20  everything rises with the wall, cut by the blow; under water only a sub tone
#   8:52  after "Fixing the second one" - a low note for the title, then a cut into silence
#   python -I build_music.py  ->  work\music.f32
import sys, os, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np
import dsp
from dsp import SR, F32, curve, vnoise, tt, Phase, Events, Reverb

D1, D2, A2, D3, Eb3, F3, Fs3, A3 = 36.71, 73.42, 110.0, 146.83, 155.56, 174.61, 185.0, 220.0
D4, A4, B4, D5, E5, Fs5, A5, Bb5, B5, D6 = 293.66, 440.0, 493.88, 587.33, 659.26, 739.99, 880.0, 932.33, 987.77, 1174.66
CUT = 548.70                                   # the cut into silence (the picture is fading to black)


class Pad:
    """sustained voices: (frequency, level, pan); each breathes slowly on its own, two partials above keep it soft"""
    def __init__(self, voices, gain, seed=0, breath=0.35, rate=0.05, bright=0.25):
        self.v = voices; self.gain = curve(gain); self.t0, self.t1 = gain[0][0], gain[-1][0]
        self.seed = seed; self.breath = breath; self.rate = rate; self.bright = bright
    def render(self, buf, i0, n):
        if (i0 + n) / SR <= self.t0 or i0 / SR >= self.t1: return
        t = tt(i0, n); g = self.gain(t)
        for k, (f, a, p) in enumerate(self.v):
            w = (1.0 - self.breath) + self.breath * 2.0 * vnoise(t, self.rate, self.seed * 17 + k)
            ph = 2.0 * math.pi * f * t + k * 1.7
            s = (np.sin(ph) + self.bright * np.sin(2 * ph + 0.5) + 0.4 * self.bright * np.sin(3 * ph + 1.1)).astype(F32) * (a * g * w)
            buf[:, 0] += s * math.cos((p + 1) * math.pi / 4); buf[:, 1] += s * math.sin((p + 1) * math.pi / 4)


def bell(rng, f=880.0, dur=7.0):
    """a glass-like note: a soft attack and partials that die one after another; two copies slightly apart give it width"""
    n = int(dur * SR); t = np.arange(n) / SR; out = np.zeros((n, 2), dtype=F32)
    for c, det in ((0, 0.9985), (1, 1.0015)):
        x = np.zeros(n)
        for m, a, d in ((1.0, 1.0, dur / 2.2), (2.0, 0.35, dur / 4.0), (3.0, 0.12, dur / 6.0), (4.2, 0.06, dur / 9.0)):
            x += a * np.sin(2 * math.pi * f * det * m * t + rng.random() * 6.28) * np.exp(-t / d)
        out[:, c] = x * np.minimum(1.0, t / 0.03) * np.minimum(1.0, (dur - t) / 0.3)
    return out


class Pulse:
    """a low pulse whose tempo follows a curve (the heartbeat of the flight back): every beat is a note that closes quickly"""
    def __init__(self, bpm, gain, f=D2):
        self.bpm = curve(bpm); self.gain = curve(gain); self.t0, self.t1 = gain[0][0], gain[-1][0]; self.beat = Phase(); self.f = f; self.count = 0.0
    def render(self, buf, i0, n):
        if (i0 + n) / SR <= self.t0 or i0 / SR >= self.t1: return
        t = tt(i0, n); bpm = self.bpm(t).astype(np.float64)
        b = self.count + np.cumsum(bpm / 60.0) / SR; self.count = float(b[-1])
        fr = b - np.floor(b); k = np.floor(b).astype(np.int64)
        sec = fr * 60.0 / bpm                                           # seconds since the beat began
        acc = np.where(k % 4 == 0, 1.0, 0.62) * np.where(k % 8 == 7, 0.0, 1.0)      # an accent on one, a breath before the bar
        f = np.where(k % 16 == 15, self.f * 0.5, self.f)
        x = np.zeros(n)
        for h in range(1, 7):
            x += (h ** -1.3) * np.sin(2 * math.pi * f * h * sec) * np.exp(-sec * (3.0 + 2.2 * h))
        x *= np.minimum(1.0, sec / 0.006) * acc
        m = (x * self.gain(t)).astype(F32)
        buf[:, 0] += m; buf[:, 1] += m


class Gliss:
    """a tone that climbs with the wall of water"""
    def __init__(self, freq, gain):
        self.freq = curve(freq); self.gain = curve(gain); self.t0, self.t1 = gain[0][0], gain[-1][0]; self.ph = Phase()
    def render(self, buf, i0, n):
        if (i0 + n) / SR <= self.t0 or i0 / SR >= self.t1: return
        t = tt(i0, n); ph = self.ph(self.freq(t))
        x = (np.sin(ph) + 0.5 * np.sin(2 * ph) + 0.35 * np.sin(0.5 * ph)) * self.gain(t)
        buf[:, 0] += x.astype(F32); buf[:, 1] += x.astype(F32)


L = []
# orbit and entry: the low tone; a minor second rubs against it through the fire; a shimmer on the quiet glide
L.append(Pad([(D2, 1.0, 0.0), (A2, 0.35, -0.3), (D3, 0.3, 0.3)], [(28, 0), (40, .020), (52, .028), (57, .036), (68, .030), (72, .026), (96, .022), (106, .012), (118, 0)], seed=1))
L.append(Pad([(Eb3, 1.0, 0.2), (Eb3 * 2.003, 0.3, -0.2)], [(52, 0), (58, .012), (64, .012), (69, 0)], seed=2, breath=0.6, rate=0.4))
L.append(Pad([(D5, 1.0, -0.5), (A5, 0.7, 0.5), (D5 * 1.003, 0.6, 0.3)], [(68, 0), (73, .007), (92, .007), (100, 0)], seed=3, breath=0.8, rate=0.3, bright=0.05))

# the walk: a soft major chord far away and rare glass notes
L.append(Pad([(D3, 1.0, -0.3), (A3, 0.8, 0.3), (Fs3 * 2, 0.45, 0.0), (D4, 0.3, 0.1)], [(104, 0), (118, .011), (215, .011), (260, .007), (300, 0)], seed=4, breath=0.5, rate=0.04))
E = Events(); r = np.random.default_rng(11)
t = 113.0
bright = [A4, B4, D5, E5, Fs5, A5, B5, D6]
while t < 300.0:
    if t < 222.0:
        E.add(t, bell, gain=float(r.uniform(0.016, 0.028)), f=float(bright[int(r.integers(0, 8))]), dur=float(r.uniform(6.0, 9.0)))
        if r.random() < 0.35: E.add(t + float(r.uniform(0.4, 1.2)), bell, gain=0.012, f=float(bright[int(r.integers(2, 8))]), dur=6.0)
        t += float(r.uniform(5.0, 12.0))
    else:                                           # at the wreck: rarer and lower, the major third is gone
        E.add(t, bell, gain=float(r.uniform(0.012, 0.020)), f=float([D4, A4, D5, E5, A5][int(r.integers(0, 5))]), dur=float(r.uniform(7.0, 10.0)))
        t += float(r.uniform(9.0, 16.0))
for ts, f in ((513.5, A5), (521.0, D6), (526.5, E5)): E.add(ts, bell, gain=0.014, f=f, dur=8.0)      # after the wave: three notes of the calm
L.append(E)

# the wreck: a low note comes in; then the chord turns minor
L.append(Pad([(D1, 0.55, 0.0), (D2, 0.8, 0.0), (D3, 0.12, 0.0)], [(222, 0), (235, .030), (300, .040), (331, .050), (400, .050), (459.9, .070), (460.0, 0)], seed=5, breath=0.25, rate=0.06, bright=0.15))
L.append(Pad([(D3, 1.0, -0.3), (F3, 0.8, 0.2), (A3, 0.7, 0.4)], [(262, 0), (290, .012), (331, .018), (370, .016), (440, .012), (459.9, .030), (460.0, 0)], seed=6, breath=0.5, rate=0.07))

# the flight back and the storm: a pulse that speeds up, a tight high cluster, a tone that climbs with the wall
L.append(Pulse([(308, 96), (331, 104), (370, 124), (440, 132), (460, 140)], [(308, 0), (318, .020), (331, .036), (370, .046), (400, .040), (440, .040), (455, .050), (459.9, .060), (460.0, 0)]))
L.append(Pad([(A5, 1.0, -0.4), (Bb5, 0.8, 0.4), (A5 * 0.5, 0.4, 0.0)], [(313, 0), (331, .006), (370, .011), (430, .013), (452, .028), (459.9, .045), (460.0, 0)], seed=7, breath=0.5, rate=0.25, bright=0.1))
L.append(Pad([(Eb3, 1.0, 0.3), (D3 * 1.004, 0.9, -0.3)], [(331, 0), (370, .011), (440, .018), (459.9, .036), (460.0, 0)], seed=8, breath=0.4, rate=0.15))
L.append(Gliss([(440, 220.0), (452, 330.0), (460, 660.0)], [(440, 0), (450, .010), (459.9, .036), (460.0, 0)]))

# under water: only a sub tone and a dark fifth far away
L.append(Pad([(D1, 1.0, 0.0), (D2, 0.5, 0.0)], [(461, 0), (466, .030), (495, .030), (500, 0)], seed=9, breath=0.3, rate=0.05, bright=0.1))
L.append(Pad([(D3, 1.0, -0.3), (A3, 0.6, 0.3)], [(463, 0), (472, .006), (494, .006), (500, 0)], seed=10, breath=0.8, rate=0.08, bright=0.05))

# afterwards: a thin light; then the second wave is named - the low note for the title and the cut
L.append(Pad([(D4, 1.0, -0.3), (A4, 0.7, 0.3)], [(506, 0), (514, .006), (529, .006), (531.5, 0)], seed=11, breath=0.7, rate=0.1, bright=0.05))
L.append(Pad([(D1, 0.7, 0.0), (D2, 1.0, 0.0), (A2, 0.5, -0.3), (D3, 0.25, 0.0), (F3, 0.22, 0.3), (Eb3, 0.12, -0.2)],
             [(532.2, 0), (534.0, .060), (541.0, .090), (547.0, .100), (CUT, .100), (CUT + 0.02, 0)], seed=12, breath=0.15, rate=0.08, bright=0.3))

HALL = Reverb(3.2, seed=21, lo=120.0, hi=5000.0, pre=0.03)


def post(buf, i0, n):
    return buf + 0.55 * HALL(buf)


if __name__ == '__main__':
    dsp.render('music', L, post)
