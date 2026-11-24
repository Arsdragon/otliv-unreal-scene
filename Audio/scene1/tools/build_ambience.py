# Ambience stem of scene 1 "Otliv": everything continuous - the hum of the ship, the roar of the entry, air on the glide,
# wind, the far rumble of the wave growing into a roar, rain beds, flowing water, the muffled deep, the swell afterwards.
# All of it is synthesized (filtered noise and a few sine tones), nothing is downloaded.
#   python -I build_ambience.py  ->  work\ambience.f32
import sys, os, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np
import dsp
from dsp import SR, F32, curve, vnoise, tt, bp, lp, hp, reson, Filt, Noise


class Bed:
    """filtered noise with a gain curve (the curve gives the RMS level), optional gusts, stereo width"""
    def __init__(self, seed, color, sos, gain, mods=(), width=1.0):
        self.noise = Noise(seed, color); self.filt = Filt(sos); self.gain = curve(gain); self.mods = mods; self.width = width
        self.t0, self.t1 = gain[0][0], gain[-1][0]
        cal = Filt(sos)(Noise(seed + 9000, color)(SR * 4))                       # calibrate: unit RMS before the gain
        self.k = 1.0 / max(float(np.sqrt((cal[SR:] ** 2).mean())), 1e-9)
    def render(self, buf, i0, n):
        if (i0 + n) / SR <= self.t0 or i0 / SR >= self.t1: return
        t = tt(i0, n); g = self.gain(t)
        for rate, depth, seed in self.mods:
            g = g * ((1.0 - depth) + depth * 2.0 * vnoise(t, rate, seed))
        x = self.filt(self.noise(n)) * self.k
        if self.width < 1.0:
            mid = x.mean(axis=1, keepdims=True); x = mid + self.width * (x - mid)
        buf += x * g[:, None]


class Tones:
    """a few steady sine partials (hum of machinery) with a gain curve; a slow wobble keeps them alive"""
    def __init__(self, partials, gain, wob=(0.07, 0.3, 5)):
        self.partials = partials; self.gain = curve(gain); self.t0, self.t1 = gain[0][0], gain[-1][0]; self.wob = wob
    def render(self, buf, i0, n):
        if (i0 + n) / SR <= self.t0 or i0 / SR >= self.t1: return
        t = tt(i0, n); g = self.gain(t) * ((1.0 - self.wob[1]) + self.wob[1] * 2.0 * vnoise(t, self.wob[0], self.wob[2]))
        for k, (f, a, p) in enumerate(self.partials):
            s = (a * np.sin(2.0 * math.pi * f * t + k)).astype(F32) * g
            buf[:, 0] += s * (1.0 - 0.5 * max(p, 0.0)); buf[:, 1] += s * (1.0 + 0.5 * min(p, 0.0))


L = []
# --- a floor of air through the whole film: no digital silence anywhere except the very end
L.append(Bed(1, 'pink', bp(120, 5000, 1), [(0, .0012), (549.5, .0012)]))

# --- the ship: steady hum (cockpit 0-1:44, again from 6:30), deeper and duller under water, almost dead afterwards
SHIP = [(0, .020), (50, .022), (56, .034), (100, .034), (104, .022), (108, .010), (113, .0), (389.6, .0), (391, .012), (399, .018),
        (410, .020), (459.9, .022), (460.2, .016), (499.8, .012), (501, .007), (548, .006), (549.5, 0)]
L.append(Tones([(48.0, 1.0, 0.0), (96.4, 0.55, -0.4), (97.1, 0.45, 0.4), (144.2, 0.30, 0.2), (192.6, 0.14, -0.2), (241.0, 0.08, 0.0)], SHIP))
L.append(Bed(2, 'brown', bp(140, 620, 1), [(t, v * 0.42) for t, v in SHIP], mods=[(0.11, 0.25, 7)], width=0.6))
L.append(Bed(3, 'white', bp(2200, 6500, 1), [(t, v * 0.085) for t, v in SHIP if t < 460] + [(460.1, 0)], width=0.8))   # air system hiss

# --- entry: rumble, roar and the hiss of plasma; then the sudden quiet of the glide
L.append(Bed(10, 'brown', lp(170, 2), [(50, 0), (52, .02), (57, .27), (63.5, .31), (67, .22), (69.5, .05), (72, 0)], mods=[(2.3, 0.3, 11)]))
L.append(Bed(11, 'pink', bp(150, 1800, 1), [(51, 0), (57, .17), (63.5, .21), (67, .14), (69.5, .03), (72, 0)], mods=[(3.1, 0.3, 12)]))
L.append(Bed(12, 'white', bp(3500, 9000, 2), [(52, 0), (58, .05), (63.5, .06), (68, 0)], mods=[(9.0, 0.5, 13), (0.8, 0.3, 14)]))
L.append(Bed(13, 'pink', bp(250, 3500, 1), [(66, 0), (70, .036), (86, .030), (96, .040), (100.5, .030), (103, 0)], mods=[(0.4, 0.4, 15)]))
L.append(Bed(14, 'white', reson(2100, 16), [(68, 0), (71, .011), (84, .009), (96, .005), (100, 0)], mods=[(0.6, 0.7, 16)], width=0.5))
L.append(Bed(15, 'white', reson(2850, 22), [(69, 0), (73, .006), (88, .005), (97, 0)], mods=[(0.45, 0.8, 17)], width=0.5))
L.append(Bed(16, 'pink', lp(900, 1), [(70, 0), (73, .04), (84, .04), (86, 0)], mods=[(0.25, 0.9, 18)]))               # through the cloud layer

# --- outside: a great silence with a light wind that grows into a gale. Coming back: in the airlock the storm still comes
#     through the open hatch (6:30-6:37); the hatch slams at 6:37 - and only then everything is dulled by the hull
L.append(Bed(20, 'pink', bp(80, 700, 1), [(108, 0), (113, .006), (215, .007), (240, .012), (310, .030), (345, .060), (370, .100), (389.6, .130),
                                           (390.0, .075), (396.95, .080), (397.15, .035), (430, .060), (458, .090), (460.02, 0)], mods=[(0.35, 0.6, 21), (1.3, 0.25, 22)]))
L.append(Bed(21, 'pink', bp(700, 4500, 1), [(113, 0), (215, .001), (240, .004), (310, .012), (345, .030), (370, .050), (389.6, .070),
                                             (390.0, .030), (396.95, .032), (397.15, .004), (458, .008), (460.02, 0)], mods=[(0.5, 0.8, 23), (2.1, 0.3, 24)]))
L.append(Bed(22, 'white', reson(1350, 9), [(240, 0), (310, .004), (370, .016), (389.6, .022), (390.0, .008), (396.95, .008), (397.1, 0)], mods=[(0.3, 0.95, 25)], width=0.4))  # whistle of gusts

# --- water that starts to run toward the wave (the babble itself is in the effects stem)
L.append(Bed(30, 'white', bp(600, 5000, 1), [(280, 0), (300, .006), (331, .016), (370, .030), (389.6, .035), (390.0, .014), (396.95, .014), (397.1, 0)], mods=[(6.0, 0.5, 31), (0.4, 0.3, 32)]))

# --- the wave: a hum of 30-60 Hz from far away, then a roar that fills everything; cut by the blow
L.append(Bed(40, 'brown', bp(25, 70, 2), [(285, 0), (310, .03), (331, .07), (370, .14), (400, .20), (440, .30), (455, .42), (459.9, .50), (460.05, 0)], mods=[(0.5, 0.25, 41)], width=0.5))
L.append(Bed(41, 'brown', bp(70, 180, 2), [(300, 0), (331, .02), (370, .06), (400, .09), (440, .16), (459.9, .30), (460.05, 0)], mods=[(0.8, 0.3, 42)], width=0.7))
L.append(Bed(42, 'pink', bp(180, 2500, 1), [(350, 0), (370, .020), (389.6, .050), (390.0, .035), (396.95, .040), (397.15, .020), (420, .050), (440, .100), (452, .200), (459.9, .400), (460.05, 0)], mods=[(0.7, 0.35, 43)]))
L.append(Bed(43, 'white', bp(2500, 9000, 1), [(425, 0), (445, .020), (459.9, .120), (460.05, 0)], mods=[(1.1, 0.4, 44)]))

# --- rain: a hiss on the helmet outside, a dull roar on the hull inside, the last of it after the wave
L.append(Bed(50, 'white', bp(2500, 9000, 1), [(328, 0), (345, .004), (370, .016), (389.6, .026), (389.9, 0)], mods=[(0.6, 0.6, 51)]))
L.append(Bed(51, 'pink', bp(500, 3500, 1), [(389.7, 0), (390.2, .016), (396.95, .018), (397.2, .013), (399, .022), (430, .040), (458, .045), (460.02, 0)], mods=[(0.55, 0.55, 52)]))
L.append(Bed(52, 'pink', bp(500, 3500, 1), [(500.3, 0), (501.5, .020), (512, .006), (525, 0)], mods=[(0.55, 0.5, 53)]))

# --- under water: everything is far and dull
L.append(Bed(60, 'brown', lp(220, 2), [(459.98, 0), (460.3, .30), (463, .16), (480, .10), (498, .08), (500.0, .03), (500.6, 0)], mods=[(0.3, 0.4, 61)], width=0.6))
L.append(Bed(61, 'pink', bp(200, 700, 1), [(460.0, 0), (460.5, .030), (470, .020), (499.5, .016), (500.3, 0)], mods=[(0.2, 0.5, 62)]))

# --- afterwards: the heavy swell, the roar going away, a gentle wind on the hull
L.append(Bed(70, 'pink', lp(500, 1), [(500.3, 0), (502, .050), (548, .045), (549.5, 0)], mods=[(0.14, 0.95, 71)]))
L.append(Bed(71, 'brown', bp(25, 120, 2), [(500.2, 0), (501, .16), (515, .08), (535, .03), (549, .015), (549.5, 0)], width=0.5))
L.append(Bed(72, 'pink', bp(150, 900, 1), [(500.5, 0), (503, .012), (548, .010), (549.5, 0)], mods=[(0.3, 0.6, 73)]))

if __name__ == '__main__':
    dsp.render('ambience', L)
