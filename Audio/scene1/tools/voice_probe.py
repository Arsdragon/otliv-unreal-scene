# Compares probes of the ship's voice by instruments (there are no ears here): pitch, tempo, pauses, clicks, how much of
# the energy sits where consonants live, how deeply the level swings at the rate of syllables.
#   python -I voice_probe.py [<folder with sub-folders, each holding bort_NN.wav>] [--lines=03,10,11]
import sys, os, glob, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np
from scipy import signal
import dsp, voice_process as vp
SR = dsp.SR


def db(x): return 20 * math.log10(max(float(x), 1e-9))
def band(x, lo, hi): return float(np.sqrt((signal.sosfilt(dsp.bp(lo, hi, 3), x) ** 2).mean()))


def f0_median(x):
    """median pitch of the voiced frames, by autocorrelation (60-350 Hz)"""
    y = signal.sosfilt(dsp.bp(60, 900, 2), x); n = int(0.04 * SR); hop = int(0.02 * SR); out = []
    lo, hi = int(SR / 350), int(SR / 60); e = np.sqrt((y ** 2).mean())
    for i in range(0, len(y) - n, hop):
        f = y[i:i + n]
        if np.sqrt((f ** 2).mean()) < 0.5 * e: continue
        f = f - f.mean(); ac = np.correlate(f, f, mode='full')[n - 1:]
        if ac[0] <= 0: continue
        k = lo + int(np.argmax(ac[lo:hi]))
        if ac[k] / ac[0] > 0.45: out.append(SR / k)
    return float(np.median(out)) if out else 0.0


def clicks(x):
    """isolated spikes: 1 ms frames of the 4-7.5 kHz band that stand 18 dB above their surroundings (20 ms) for no longer than 2 ms"""
    y = signal.sosfilt(dsp.bp(4000, 7500, 3), x); m = int(0.001 * SR); k = len(y) // m
    e = 10 * np.log10((y[:k * m].reshape(k, m) ** 2).mean(axis=1) + 1e-14)
    med = signal.medfilt(e, 21); peak = e.max()
    c = np.flatnonzero((e - med > 18.0) & (e > peak - 35.0))
    groups = np.split(c, np.flatnonzero(np.diff(c) > 1) + 1) if len(c) else []
    return sum(1 for g in groups if len(g) <= 2)


def edges(x):
    """the hardest step of the waveform at the start or the end of a phrase, relative to the level of speech (a cut = a click)"""
    runs = vp.speech_runs(x); r = float(np.sqrt((x ** 2).mean())); worst = 0.0
    for a, b in runs:
        for s in (x[max(a - 240, 0):a + 240], x[b - 240:b + 240]):
            if len(s) > 2: worst = max(worst, float(np.abs(np.diff(s)).max()) / max(r, 1e-9))
    return worst


def modulation(x):
    """depth of the level swings at 2-8 Hz (the rate of syllables) relative to the mean level: the higher, the more distinct"""
    env = np.abs(signal.sosfilt(dsp.bp(300, 3300, 2), x)); d = 100
    e = signal.resample_poly(env, 1, SR // d); e = e - 0 * e.mean()
    spec = np.abs(np.fft.rfft((e - e.mean()) * np.hanning(len(e)))) ; fr = np.fft.rfftfreq(len(e), 1.0 / d)
    return float(np.sqrt((spec[(fr >= 2) & (fr <= 8)] ** 2).sum()) / (e.mean() * len(e) / 2))


def syllables(x):
    env = signal.sosfilt(signal.butter(2, 12.0, fs=SR, output='sos'), np.abs(signal.sosfilt(dsp.bp(300, 3300, 2), x)))
    pk, _ = signal.find_peaks(env, distance=int(0.11 * SR), prominence=env.max() * 0.08)
    return len(pk)


LINES = ([a.split('=')[1] for a in sys.argv[1:] if a.startswith('--lines=')] or ['03,11'])[0].split(',')


def main(root):
    rng = np.random.default_rng(1)
    print('проба                реплика  длит с  слогов/с  пауз  макс.пауза  тон Гц  щелчки  стык   1-3,3к отн. 0,3-1к   модуляция   после радио: пик/RMS')
    for d in sorted(glob.glob(os.path.join(root, '*'))):
        if not os.path.isdir(d): continue
        for ln in LINES:
            f = os.path.join(d, 'bort_%s.wav' % ln)
            if not os.path.exists(f): continue
            x, _ = vp.pick_take(vp.load(f), '1'); x = x.astype(np.float64)
            runs = vp.speech_runs(x.astype(np.float32)); speech = sum(b - a for a, b in runs) / SR
            pauses = [(runs[i + 1][0] - runs[i][1]) / SR for i in range(len(runs) - 1)]
            y = vp.radio(x.astype(np.float32), rng).astype(np.float64); core = y[int(0.16 * SR):-int(0.22 * SR)]
            print('%-20s   %s    %5.2f    %5.2f     %d     %5.2f     %5.0f    %3d    %4.1f       %+5.1f дБ          %5.3f        %4.1f дБ' % (
                os.path.basename(d), ln, len(x) / SR, syllables(x) / max(speech, 0.1), len(pauses), max(pauses) if pauses else 0.0, f0_median(x),
                clicks(x), edges(x), db(band(x, 1000, 3300)) - db(band(x, 300, 1000)), modulation(x), db(np.abs(core).max()) - db(np.sqrt((core ** 2).mean()))))


if __name__ == '__main__':
    pos = [a for a in sys.argv[1:] if not a.startswith('--')]
    main(pos[0] if pos else os.path.join(dsp.WORK, 'probe'))
