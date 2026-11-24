# Voice of the ship through Piper (a neural synthesizer that runs on the processor, no internet): reads the table of
# voice_lines.md and writes bort_NN.wav into a folder. Needs piper_get.sh to have been run (with the user's consent).
#   python -I voice_piper.py <denis|dmitri> <out folder> [--only=03,10,11] [--length=1.08] [--noise=0.5] [--noisew=0.333]
#                            [--pause=0.35] [--pitch=-1.5]
#   --length: > 1 = slower.   --pitch: semitones, done afterwards by ffmpeg (rubberband, formants kept).
#   --phonemes: no synthesis, only the texts and phonemes.txt for the chosen lines (run it without --only for the full record).
# Stress: Piper shows the stress it is going to use (phonemes), so every word of the 16 lines was read by eye.
# Three words were wrong and carry a stress mark here; the phonemes of the final text are saved to phonemes.txt.
import sys, os, re, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
PIPER = r'C:\UnrealScenes\Downloads\audio\piper'
PY = os.path.join(PIPER, 'venv', 'Scripts', 'python.exe')
A = chr(0x301)                                  # combining acute: the stress mark, understood by Piper's phonemizer
STRESS = {'сорок': 'со' + A + 'рок',            # was "sʌrˈok"  (lines 03, 10, 12)
          'воды': 'воды' + A,                   # was "vˈody"   (line 09: the level OF the water)
          'замер': 'заме' + A + 'р'}            # was "zˈɑmʲir" (line 10: the measurement, not "froze")
args = [a for a in sys.argv[1:] if not a.startswith('--')]
opt = dict(a[2:].split('=', 1) for a in sys.argv[1:] if a.startswith('--') and '=' in a)
voice, out = args[0], os.path.abspath(args[1])
model = os.path.join(PIPER, 'voices', 'ru_RU-%s-medium.onnx' % voice)
only = set(opt['only'].split(',')) if 'only' in opt else None
pitch = float(opt.get('pitch', 0.0))
if not os.path.exists(PY) or not os.path.exists(model):
    print('Piper is not here: run piper_get.sh first (only after the user has agreed)'); sys.exit(1)
os.makedirs(out, exist_ok=True)
n = 0; texts = []
for line in open(os.path.join(ROOT, 'voice_lines.md'), encoding='utf-8'):
    m = re.match(r'^\|\s*(\d\d)\s*\|[^|]*\|\s*(.+?)\s*\|\s*$', line)
    if not m or (only and m.group(1) not in only): continue
    text = m.group(2).replace('«', '').replace('»', '')
    for w, s in STRESS.items(): text = re.sub(r'(?<![А-Яа-яЁё])' + w + r'(?![А-Яа-яЁё])', s, text)
    txt = os.path.join(out, 'bort_%s.txt' % m.group(1)); open(txt, 'w', encoding='utf-8').write(text + '\n'); texts.append((m.group(1), txt))
    if '--phonemes' in sys.argv: continue                 # only write the texts and phonemes.txt, no synthesis
    wav = os.path.join(out, 'bort_%s.wav' % m.group(1)); raw = wav[:-4] + '.raw.wav' if pitch else wav
    cmd = [PY, '-I', '-m', 'piper', '-m', model, '-f', raw, '--input-file', txt,
           '--length-scale', opt.get('length', '1.08'), '--noise-scale', opt.get('noise', '0.5'), '--noise-w-scale', opt.get('noisew', '0.333'),
           '--sentence-silence', opt.get('pause', '0.35')]
    p = subprocess.run(cmd, capture_output=True)
    if p.returncode != 0:
        print(p.stderr.decode('utf-8', 'ignore')[-1500:]); sys.exit(1)
    if pitch:
        k = 2.0 ** (pitch / 12.0)
        p = subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', raw, '-af', 'rubberband=pitch=%.5f:formant=preserved:pitchq=quality' % k, wav], capture_output=True)
        if p.returncode != 0:
            print(p.stderr.decode('utf-8', 'ignore')[-800:]); sys.exit(1)
        os.remove(raw)
    n += 1
# the record of how every line will be pronounced
code = ("import sys, io\nsys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')\nfrom piper import PiperVoice\n"
        "v = PiperVoice.load(sys.argv[1])\n"
        "for a in sys.argv[2:]:\n    k, f = a.split('=', 1)\n    print(k, ' | '.join(''.join(s) for s in v.phonemize(open(f, encoding='utf-8').read().strip())))\n")
p = subprocess.run([PY, '-I', '-c', code, model] + ['%s=%s' % (k, f) for k, f in texts], capture_output=True)
if p.returncode == 0: open(os.path.join(out, 'phonemes.txt'), 'wb').write(p.stdout)
print('piper voice %s: %d files -> %s (pitch %+.1f st)' % (voice, n, out, pitch))
