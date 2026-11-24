# Mixdown of scene 1 "Otliv": four stems from work\ (voice, ambience, fx, music) -> mix_v1.wav and the stems as WAV.
#   - balance of the stems; the bed (ambience + fx + music) ducks under the voice;
#   - every line is "ridden" like a fader: where the bed is loud in the speech band, the line is lifted over it;
#   - the whole mix is brought to -16 LUFS (measured by ffmpeg ebur128) through a limiter with a -2 dBFS ceiling;
#   - the end is cut into silence at 9:08.7 (the picture is fading to black).
#   python -I mix.py [version]          (default version: v1)
import sys, os, re, math, json, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np
from scipy import signal
import dsp
from dsp import SR, F32, curve, tt, bp, Filt

VER = sys.argv[1] if len(sys.argv) > 1 else 'v1'
GAINS = {'voice': 1.0, 'ambience': 0.40, 'fx': 1.25, 'music': 1.0}
DUCK = 0.45                    # the bed under a line: x0.45 (-7 dB)
OVER = 2.2                     # a line must stand this much above the bed in the speech band (+7 dB)
MAXLIFT = 3.2                  # ...but is never lifted more than +10 dB
TARGET = -16.0                 # LUFS
CEIL = 0.794                   # limiter ceiling, -2 dBFS
FADE = curve([(0.0, 0.0), (0.25, 1.0), (548.70, 1.0), (548.85, 0.0), (550.0, 0.0)])
TL = json.load(open(os.path.join(HERE, 'timeline.json'), encoding='utf-8'))
STARTS = [t for t, _ in TL['lines']]
NAMES = ('voice', 'ambience', 'fx', 'music')


class Env:
    """how much the bed must give way right now (0..1), from the level of the voice: quick to open, slow to return"""
    def __init__(self):
        self.a = Filt(signal.butter(1, 12.0, fs=SR, output='sos'), ch=0); self.b = Filt(signal.butter(1, 2.5, fs=SR, output='sos'), ch=0)
    def __call__(self, v):
        e = self.a(np.abs(v)); d = np.clip(e / 0.012, 0.0, 1.0)
        return np.maximum(d, np.clip(self.b(d) * 1.6, 0.0, 1.0)).astype(F32)


def line_index(i0, n):
    """index of the voice line every sample belongs to (lines never overlap; the boundary is the start of the next line)"""
    return np.searchsorted(np.array(STARTS) - 0.5, tt(i0, n), side='right') - 1


def walk(fn):
    """runs fn(i0, voice, bed stems dict, duck) over the film chunk by chunk"""
    rd = {k: dsp.raw_reader(k) for k in NAMES}; env = Env(); i0 = 0
    for v in rd['voice']:
        st = {k: next(rd[k]) * GAINS[k] for k in NAMES[1:]}
        v = v * GAINS['voice']
        d = env(v[:, 0])
        fn(i0, v, st, (1.0 - (1.0 - DUCK) * d)[:, None])
        i0 += len(v)


def measure_lines():
    """speech-band level of every line and of the bed under it -> the lift of every line"""
    fv = Filt(bp(400, 3300, 2)); fb = Filt(bp(400, 3300, 2))
    sv = np.zeros(len(STARTS)); sb = np.zeros(len(STARTS)); cnt = np.zeros(len(STARTS))
    def fn(i0, v, st, duck):
        bed = (st['ambience'] + st['fx'] + st['music']) * duck
        a = fv(v); b = fb(bed); act = np.abs(v[:, 0]) > 0.004; li = line_index(i0, len(v))
        for k in np.unique(li[act]):
            m = act & (li == k)
            sv[k] += float((a[m].astype(np.float64) ** 2).sum()); sb[k] += float((b[m].astype(np.float64) ** 2).sum()); cnt[k] += m.sum() * 2
    walk(fn)
    rv = np.sqrt(sv / np.maximum(cnt, 1)); rb = np.sqrt(sb / np.maximum(cnt, 1))
    lift = np.clip(OVER * rb / np.maximum(rv, 1e-9), 1.0, MAXLIFT)
    return rv, rb, lift


def premix(lift):
    out = dsp.RawOut('premix')
    def fn(i0, v, st, duck):
        g = lift[np.clip(line_index(i0, len(v)), 0, len(lift) - 1)].astype(F32)[:, None]
        f = FADE(tt(i0, len(v)))[:, None]
        out.write((v * g + (st['ambience'] + st['fx'] + st['music']) * duck) * f)
    walk(fn)
    return out.close()


def loud(args):
    """integrated loudness, loudness range and true peak of an input given by ffmpeg arguments"""
    p = subprocess.run(['ffmpeg', '-hide_banner', '-nostats'] + args + ['-af', 'ebur128=peak=true', '-f', 'null', '-'], capture_output=True)
    s = p.stderr.decode('utf-8', 'ignore'); s = s[s.rfind('Summary:'):]
    I = float(re.search(r'I:\s*(-?[\d.]+) LUFS', s).group(1)); lra = float(re.search(r'LRA:\s*(-?[\d.]+) LU', s).group(1))
    tp = float(re.search(r'Peak:\s*(-?[\d.]+) dBFS', s).group(1))
    return I, lra, tp


def main():
    rv, rb, lift = measure_lines()
    print(' line  start   voice dB   bed dB   lift dB')
    for k, t in enumerate(STARTS):
        print('  %2d   %5.1f   %7.1f   %7.1f   %+5.1f' % (k + 1, t, 20 * math.log10(max(rv[k], 1e-9)), 20 * math.log10(max(rb[k], 1e-9)), 20 * math.log10(lift[k])))
    pk, rms = premix(lift)
    raw = ['-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', os.path.join(dsp.WORK, 'premix.f32')]
    I0, lra0, tp0 = loud(raw)
    print('premix: peak %.2f, %.1f LUFS, LRA %.1f LU, true peak %.1f dBFS' % (pk, I0, lra0, tp0))
    out = os.path.join(dsp.ROOT, 'mix_%s.wav' % VER)
    g = 10 ** ((TARGET - I0) / 20.0)
    for attempt in range(3):
        af = 'volume=%.5f,alimiter=level_in=1:level_out=1:limit=%.3f:attack=5:release=200:asc=1:level=0' % (g, CEIL)
        subprocess.run(['ffmpeg', '-y', '-v', 'error'] + raw + ['-af', af, '-c:a', 'pcm_s24le', out], check=True)
        I1, lra1, tp1 = loud(['-i', out])
        print('master gain %+.2f dB -> %.2f LUFS, LRA %.1f LU, true peak %.2f dBFS' % (20 * math.log10(g), I1, lra1, tp1))
        if abs(I1 - TARGET) <= 0.3: break
        g *= 10 ** ((TARGET - I1) / 20.0)
    # the stems as they stand in the mix (balance, ducking, lifts, end cut, master gain), before the limiter;
    # one common trim keeps the loudest of them below full scale
    peaks = {k: 0.0 for k in NAMES}
    def scan(i0, v, st, duck):
        gl = lift[np.clip(line_index(i0, len(v)), 0, len(lift) - 1)].astype(F32)[:, None]; f = FADE(tt(i0, len(v)))[:, None]
        peaks['voice'] = max(peaks['voice'], float(np.abs(v * gl * f).max()))
        for k in NAMES[1:]: peaks[k] = max(peaks[k], float(np.abs(st[k] * duck * f).max()))
    walk(scan)
    trim = min(1.0, 0.98 / (max(peaks.values()) * g))
    import wave
    ws = {}
    for k in NAMES:
        w = wave.open(os.path.join(dsp.ROOT, 'stem_%s_%s.wav' % (k, VER)), 'wb'); w.setnchannels(2); w.setsampwidth(3); w.setframerate(SR); ws[k] = w
    def put(w, x):
        vv = np.clip(np.round(x.astype(np.float64) * (g * trim) * 8388607.0), -8388608, 8388607).astype('<i4')
        w.writeframes(vv.view(np.uint8).reshape(-1, 4)[:, :3].tobytes())
    def fn(i0, v, st, duck):
        gl = lift[np.clip(line_index(i0, len(v)), 0, len(lift) - 1)].astype(F32)[:, None]; f = FADE(tt(i0, len(v)))[:, None]
        put(ws['voice'], v * gl * f)
        for k in NAMES[1:]: put(ws[k], st[k] * duck * f)
    walk(fn)
    for w in ws.values(): w.close()
    info = {'version': VER, 'gains': GAINS, 'duck': DUCK, 'master_gain_db': round(20 * math.log10(g), 2), 'stems_trim_db': round(20 * math.log10(trim), 2),
            'lufs': I1, 'lra': lra1, 'true_peak_dbfs': tp1, 'line_lift_db': [round(20 * math.log10(x), 1) for x in lift]}
    json.dump(info, open(os.path.join(dsp.ROOT, 'mix_%s.json' % VER), 'w', encoding='utf-8'), indent=1)
    print('stems: common trim %.2f dB (sum of stems x %.2f dB = the mix before the limiter)' % (20 * math.log10(trim), -20 * math.log10(trim)))
    print(out)


if __name__ == '__main__':
    main()
