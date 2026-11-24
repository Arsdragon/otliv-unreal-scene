# Voice of the ship: takes a folder with bort_01 ... bort_16 (wav, m4a, mp3 - anything ffmpeg reads), makes every line
# sound like an on-board computer over the radio and puts it at its marker of the master sequence.
#   python -I voice_process.py                      -> the temporary synthetic voice from ..\voice_tts
#   python -I voice_process.py ..\voice_raw         -> the user's recordings (the same names), nothing else changes
# Result: work\voice.f32 (the voice stem before mastering) and a table of the lines in the console.
# A recording may hold two takes in a row: the script takes the LAST take (the part after the longest pause).
import sys, os, json, math, subprocess, tempfile, glob
import numpy as np
from scipy import signal
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)                             # python -I does not add the script's folder
import dsp
from dsp import SR, F32

ARGS = [a for a in sys.argv[1:] if not a.startswith('--')]
SRC = os.path.abspath(ARGS[0]) if ARGS else os.path.join(dsp.ROOT, 'voice_tts')
# --takes=1 | 2 | auto: the synthetic voice never has second takes; for recordings the default is auto
# --pause-cap=0.6: pauses inside a line are cut to this length (a synthetic voice waits almost a second on every full stop);
# on by default for the synthetic folders (voice_tts*), off for recordings
CAP = float(([a.split('=')[1] for a in sys.argv[1:] if a.startswith('--pause-cap=')] or ['0.6' if os.path.basename(SRC).startswith('voice_tts') else '0'])[0])
TAKES = ([a.split('=')[1] for a in sys.argv[1:] if a.startswith('--takes=')] or ['1' if os.path.basename(SRC).startswith('voice_tts') else 'auto'])[0]
TL = json.load(open(os.path.join(HERE, 'timeline.json'), encoding='utf-8'))
LINES = TL['lines']                                  # [time, text] x 16
GAP = 0.6                                            # a line must end this long before the next one starts
LINE_RMS = 0.10                                      # every line gets the same loudness


def load(path, tempo=1.0):
    """any audio file -> mono float32 at 48 kHz (through ffmpeg; tempo > 1 makes it faster without changing the pitch)"""
    af = 'aresample=%d' % SR
    if abs(tempo - 1.0) > 0.005: af = 'atempo=%.4f,' % tempo + af
    p = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-af', af, '-ac', '1', '-f', 'f32le', '-'], capture_output=True)
    if p.returncode != 0: raise RuntimeError(p.stderr.decode('utf-8', 'ignore'))
    return np.frombuffer(p.stdout, dtype=F32).copy()


def envelope(x, win=0.02):
    k = int(win * SR); e = np.sqrt(np.convolve(x.astype(np.float64) ** 2, np.ones(k) / k, mode='same'))
    return e


def speech_runs(x):
    """-> list of (start, end) samples where somebody speaks (pauses shorter than 0.25 s are kept inside a run)"""
    e = envelope(x); thr = max(e.max() * 0.045, 1e-4)
    on = e > thr
    idx = np.flatnonzero(np.diff(np.concatenate([[0], on.view(np.int8), [0]])))
    runs = [(idx[i], idx[i + 1]) for i in range(0, len(idx), 2)]
    merged = []
    for a, b in runs:
        if merged and a - merged[-1][1] < int(0.25 * SR): merged[-1] = (merged[-1][0], b)
        else: merged.append((a, b))
    return [(a, b) for a, b in merged if b - a > int(0.08 * SR)]


def pick_take(x, takes_mode):
    """two takes in one file -> the last one. A pause of a second also stands between two SENTENCES of one line, so in
    'auto' mode the file counts as two takes only if it falls into exactly two blocks of nearly the same length."""
    runs = speech_runs(x)
    if not runs: return x, 1
    blocks = [[runs[0][0], runs[0][1]]]
    for a1, b1 in runs[1:]:
        if a1 - blocks[-1][1] > int(0.9 * SR): blocks.append([a1, b1])
        else: blocks[-1][1] = b1
    two = False
    if takes_mode == '2': two = len(blocks) >= 2
    elif takes_mode == 'auto' and len(blocks) == 2:
        d0 = blocks[0][1] - blocks[0][0]; d1 = blocks[1][1] - blocks[1][0]
        two = 0.75 < d0 / max(d1, 1) < 1.33
    if two: runs = [r for r in runs if r[0] >= blocks[-1][0]]
    a = max(0, runs[0][0] - int(0.03 * SR)); b = min(len(x), runs[-1][1] + int(0.08 * SR))
    return x[a:b], (2 if two else 1)


def squeeze_pauses(x, keep):
    """shortens the pauses inside a line to `keep` seconds (the text has many full stops, a synthetic voice waits long on each)"""
    runs = speech_runs(x)
    if len(runs) < 2: return x
    out = []; fade = int(0.01 * SR)
    for i, (a, b) in enumerate(runs):
        a0 = max(0, a - int(0.02 * SR)); b0 = min(len(x), b + int(0.04 * SR))
        seg = x[a0:b0].copy()
        seg[:fade] *= np.linspace(0, 1, fade, dtype=F32); seg[-fade:] *= np.linspace(1, 0, fade, dtype=F32)
        out.append(seg)
        if i < len(runs) - 1:
            pause = (runs[i + 1][0] - b) / SR
            out.append(np.zeros(int(min(pause, keep) * SR), dtype=F32))
    return np.concatenate(out)


def radio(x, rng):
    """on-board computer over the radio: narrow band, light compression and saturation, a little hiss while it speaks,
    a short tone at the start and at the end"""
    x = x / max(np.sqrt(np.mean(x.astype(np.float64) ** 2)), 1e-6) * 0.08
    # a dull voice loses its consonants in the narrow radio band: if the band of consonants (1-3.3 kHz) stands lower than
    # -5 dB against the band of vowels (0.3-1 kHz), lift everything above 1 kHz by the difference (6 dB at most)
    lo = np.sqrt(np.mean(signal.sosfilt(dsp.bp(300.0, 1000.0, 3), x) ** 2)); hi = np.sqrt(np.mean(signal.sosfilt(dsp.bp(1000.0, 3300.0, 3), x) ** 2))
    lift = min(6.0, max(0.0, -5.0 - 20.0 * math.log10(max(hi, 1e-9) / max(lo, 1e-9))))
    if lift > 0.2: x = (x + (10 ** (lift / 20.0) - 1.0) * signal.sosfilt(dsp.hp(1000.0, 1), x)).astype(F32)
    x = signal.sosfilt(dsp.bp(380.0, 3300.0, 3), x).astype(F32)
    x = x + 0.5 * signal.sosfilt(dsp.reson(1900.0, 1.4), x).astype(F32)                 # small-speaker presence
    env = envelope(x, 0.012).astype(F32) + 1e-5                                          # compression 3:1 above the threshold
    g = np.minimum(1.0, (0.09 / env) ** 0.67).astype(F32)
    x = np.tanh(x * g * 9.0) / 9.0 * 1.25
    pre = int(0.16 * SR); post = int(0.22 * SR)
    y = np.zeros(pre + len(x) + post, dtype=F32)
    y[pre:pre + len(x)] = x
    hiss = signal.sosfilt(dsp.bp(900.0, 3000.0, 1), rng.standard_normal(len(y))).astype(F32) * 0.0035   # the open channel
    t = np.arange(len(y)) / SR
    hiss *= np.minimum(1.0, t / 0.02) * np.minimum(1.0, (t[-1] - t) / 0.03)
    y += hiss
    def pip(f, d, a):
        tp = np.arange(int(d * SR)) / SR
        return (a * np.sin(2 * math.pi * f * tp) * np.sin(math.pi * tp / d) ** 2).astype(F32)
    p0 = pip(1480.0, 0.055, 0.035); y[int(0.03 * SR):int(0.03 * SR) + len(p0)] += p0                      # channel opens
    p1 = pip(1180.0, 0.050, 0.030); s = pre + len(x) + int(0.07 * SR); y[s:s + len(p1)] += p1             # channel closes
    y = signal.sosfilt(dsp.bp(300.0, 4200.0, 2), y).astype(F32)
    core = y[pre:pre + len(x)]
    return y * (LINE_RMS / max(np.sqrt(np.mean(core.astype(np.float64) ** 2)), 1e-6))


def main():
    out = np.zeros(dsp.N, dtype=F32)
    rng = np.random.default_rng(7)
    rows = []
    for i, (t0, text) in enumerate(LINES, 1):
        fs = sorted(f for f in glob.glob(os.path.join(SRC, 'bort_%02d.*' % i))
                    if f.rsplit('.', 1)[-1].lower() in ('wav', 'm4a', 'mp3', 'flac', 'ogg', 'opus', 'aac', 'wma', 'mp4', 'amr', '3gp'))
        if not fs:
            rows.append((i, t0, None, None, None, 'NO FILE')); continue
        room = (LINES[i][0] - GAP - t0) if i < len(LINES) else 15.0
        x, takes = pick_take(load(fs[0]), TAKES)
        note = 'last of 2 takes' if takes == 2 else ''
        d0 = len(x) / SR; tempo = 1.0
        if CAP > 0: x = squeeze_pauses(x, CAP)
        if len(x) / SR + 0.4 > room:
            x = squeeze_pauses(x, 0.28); note += ' pauses shortened'
            if len(x) / SR + 0.4 > room:
                tempo = min(1.3, (len(x) / SR + 0.4) / room)
                x2, _ = pick_take(load(fs[0], tempo), TAKES); x = squeeze_pauses(x2, 0.28 / tempo); note += ' tempo x%.2f' % tempo
        y = radio(x, rng)
        s = int(t0 * SR)
        e = min(dsp.N, s + len(y)); out[s:e] += y[:e - s]
        fits = (len(y) / SR <= room + 0.4)
        rows.append((i, t0, d0, len(y) / SR, room, (note.strip() + ('' if fits else '  !!! DOES NOT FIT')).strip()))
    o = dsp.RawOut('voice')
    for a in range(0, dsp.N, dsp.CHUNK):
        m = out[a:a + dsp.CHUNK]; o.write(np.stack([m, m], axis=1))
    pk, rms = o.close()
    print('source:', SRC, '| takes mode:', TAKES, '| pause cap:', CAP)
    print(' no  start   raw s  final s  room s  notes')
    for i, t0, d0, d1, room, note in rows:
        if d0 is None: print('%3d  %5.1f   %s' % (i, t0, note))
        else: print('%3d  %5.1f  %6.2f  %7.2f  %6.1f  %s' % (i, t0, d0, d1, room, note))
    print('voice stem: peak %.3f, rms %.1f dB' % (pk, rms))


if __name__ == '__main__':
    main()
