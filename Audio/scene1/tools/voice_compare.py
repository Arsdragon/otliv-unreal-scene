# One file to compare voices by ear: the same lines one after another in every voice, with the same "radio" treatment
# as in the mix. Before each take a signal tells which voice it is: one short tone = the first folder, two = the second...
#   python -I voice_compare.py <out.mp3> <folder1> <folder2> [<folder3> ...] [--lines=03,11]
import sys, os, subprocess, glob, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
sys.argv, ARGV = sys.argv[:1], sys.argv[1:]                    # voice_process reads sys.argv on import: give it nothing
import numpy as np
import dsp, voice_process as vp
SR = dsp.SR
args = [a for a in ARGV if not a.startswith('--')]
lines = ([a.split('=')[1] for a in ARGV if a.startswith('--lines=')] or ['03,11'])[0].split(',')
out, folders = os.path.abspath(args[0]), [os.path.abspath(a) for a in args[1:]]
rng = np.random.default_rng(3)


def tones(k):
    t = np.arange(int(0.07 * SR)) / SR
    one = (0.05 * np.sin(2 * math.pi * 880.0 * t) * np.sin(math.pi * t / 0.07) ** 2).astype(np.float32)
    gap = np.zeros(int(0.11 * SR), dtype=np.float32)
    return np.concatenate([one, gap] * k + [np.zeros(int(0.45 * SR), dtype=np.float32)])


parts = [np.zeros(int(0.3 * SR), dtype=np.float32)]; table = []; t = 0.3
for ln in lines:
    for k, d in enumerate(folders, 1):
        fs = sorted(f for f in glob.glob(os.path.join(d, 'bort_%s.*' % ln)) if f.rsplit('.', 1)[-1].lower() in ('wav', 'm4a', 'mp3', 'flac', 'ogg'))
        if not fs: print('no line', ln, 'in', d); sys.exit(1)
        x, _ = vp.pick_take(vp.load(fs[0]), '1'); x = vp.squeeze_pauses(x, 0.6)
        seg = np.concatenate([tones(k), vp.radio(x, rng), np.zeros(int(1.0 * SR), dtype=np.float32)])
        table.append((ln, os.path.basename(d), t, t + len(seg) / SR)); t += len(seg) / SR; parts.append(seg)
    parts.append(np.zeros(int(1.2 * SR), dtype=np.float32)); t += 1.2
y = np.concatenate(parts).astype(np.float32)          # radio() returns float64; ffmpeg is fed float32
p = subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'f32le', '-ar', str(SR), '-ac', '1', '-i', '-', '-ac', '2', '-c:a', 'libmp3lame', '-b:a', '160k', out],
                   input=y.tobytes(), capture_output=True)
if p.returncode != 0: print(p.stderr.decode('utf-8', 'ignore')); sys.exit(1)
for ln, nm, a, b in table: print('line %s  %-18s %5.1f - %5.1f s' % (ln, nm, a, b))
print(out, '%.1f s, peak %.2f' % (len(y) / SR, float(np.abs(y).max())))
