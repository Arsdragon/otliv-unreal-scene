# Prepares the lines of the ship for speech synthesis: reads the table of voice_lines.md and writes bort_NN.ssml files -
# with the pitch and the rate of the voice, with pauses set by hand and with stress marks on the words a machine may
# read wrong.   python -I voice_text.py <out folder> [--rate=-8] [--pitch=-6] [--plain] [--only=03,11]
#   --plain: the text as it is, no pauses and stress marks of ours (for comparison)
import sys, os, re
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
args = [a for a in sys.argv[1:] if not a.startswith('--')]
opt = dict(a[2:].split('=', 1) if '=' in a else (a[2:], '1') for a in sys.argv[1:] if a.startswith('--'))
OUT = os.path.abspath(args[0]); RATE = float(opt.get('rate', -8)); PITCH = float(opt.get('pitch', -6)); PLAIN = 'plain' in opt
ONLY = set(opt['only'].split(',')) if 'only' in opt else None
A = '́'                                   # combining acute: the stress mark
# Stress marks. Measured on "Microsoft Pavel": a mark is honoured, but in some words it BREAKS the word (the mark before
# a final "й" stretched "холостой" by a quarter), and nobody listens here. So a mark is put only where the default
# stress was measured to be wrong and the marked word was measured to stay whole:
#   "замер" - read as "за́мер" (froze) by default; with the mark - "заме́р" (the measurement), +9 % in length, two syllables.
STRESS = {'замер': 'заме' + A + 'р'}
# extra pauses, ms (0 = leave the pause to the voice itself, which sounds more natural; long pauses are capped later
# by voice_process.py)
P_SENT, P_DASH, P_COMMA = 0, 0, 0


def esc(s): return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def ssml(text):
    t = text.replace('«', '').replace('»', '')
    if PLAIN:
        body = esc(t.replace(' — ', ', '))
    else:
        for w, s in STRESS.items(): t = re.sub(r'(?<![А-Яа-яЁё])' + w + r'(?![А-Яа-яЁё])', s, t)
        parts = [p.strip() for p in re.split(r'(?<=[.!?])\s+', t) if p.strip()]
        out = []
        for p in parts:
            p = esc(p)
            if P_DASH: p = p.replace(' — ', '<break time="%dms"/> ' % P_DASH)
            if P_COMMA: p = re.sub(r'([,:])\s+', lambda m: m.group(1) + '<break time="%dms"/> ' % P_COMMA, p)
            out.append(p)
        body = (('<break time="%dms"/> ' % P_SENT) if P_SENT else ' ').join(out)
    return ('<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="ru-RU">'
            '<prosody rate="%+d%%" pitch="%+d%%">%s</prosody></speak>' % (RATE, PITCH, body))


os.makedirs(OUT, exist_ok=True)
n = 0
for line in open(os.path.join(ROOT, 'voice_lines.md'), encoding='utf-8'):
    m = re.match(r'^\|\s*(\d\d)\s*\|[^|]*\|\s*(.+?)\s*\|\s*$', line)
    if not m or (ONLY and m.group(1) not in ONLY): continue
    open(os.path.join(OUT, 'bort_%s.ssml' % m.group(1)), 'w', encoding='utf-8').write(ssml(m.group(2))); n += 1
print('ssml files:', n, '| rate %+d%% pitch %+d%% | %s' % (RATE, PITCH, 'plain' if PLAIN else 'with pauses and stress marks'))
