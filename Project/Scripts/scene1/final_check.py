# Check of the final frames before assembly: nothing missing, nothing broken, no jumps of brightness that are not cuts.
#   python -I final_check.py [folder, default Renders\scene1\final_1080] [first] [last]
# Prints the missing frames (to feed back into T.render(frames=[...])), suspiciously small files, and every jump of the
# mean brightness over 6 levels with its time - compare the list with the known cuts and events of the scene.
import sys, os
import numpy as np
from PIL import Image
D = sys.argv[1] if len(sys.argv) > 1 else r'C:\UnrealScenes\Renders\scene1\final_1080'
F0 = int(sys.argv[2]) if len(sys.argv) > 2 else 0
F1 = int(sys.argv[3]) if len(sys.argv) > 3 else 13200
# brightness may jump here by design: camera cuts of the montage, the blackout of the blow, flashes, water breaking on the glass
KNOWN = [(49.4, 50.1, 'cut'), (52.0, 52.2, 'cut'), (61.9, 62.1, 'cut'), (67.9, 68.0, 'cut'), (75.8, 75.9, 'cut'), (79.3, 79.4, 'cut'),
         (96.1, 96.7, 'cut'), (389.5, 390.5, 'into the airlock'), (410.9, 411.9, 'flash 1'), (433.4, 434.4, 'flash 2'), (448.9, 449.9, 'flash 3'),
         (458.8, 460.6, 'the blow, blackout'), (499.5, 500.5, 'surfacing')]
missing = []; small = []; lum = np.full(F1 - F0 + 1, np.nan)
for i in range(F0, F1 + 1):
    p = os.path.join(D, 'f_%05d.png' % i)
    if not os.path.exists(p): missing.append(i); continue
    if os.path.getsize(p) < 30000: small.append(i)
    try:
        im = Image.open(p).convert('L'); im.draft('L', (240, 135)); lum[i - F0] = np.asarray(im.resize((64, 36))).mean()
    except Exception as e:
        small.append(i)
print('frames %d-%d: missing %d, tiny or unreadable %d' % (F0, F1, len(missing), len(small)))
if missing: print('missing:', missing[:60], '...' if len(missing) > 60 else '')
if small: print('tiny (black frames of the blow are expected at 11040-11052):', small[:60])
np.save(os.path.join(D, '_lum.npy'), lum)
d = np.diff(lum); idx = np.flatnonzero(np.abs(d) > 6.0)
ev = []
for i in idx:
    if ev and i - ev[-1][1] <= 6: ev[-1][1] = i
    else: ev.append([i, i])
unknown = 0
for a, b in ev:
    t0, t1 = (a + 1 + F0) / 24.0, (b + 1 + F0) / 24.0
    why = next((k[2] for k in KNOWN if t0 <= k[1] and t1 >= k[0]), None)
    if why is None: unknown += 1
    print('  %6.2f-%6.2f s  frames %5d-%5d  %5.1f -> %5.1f  %s' % (t0, t1, a + 1 + F0, b + 1 + F0, lum[a], lum[b + 1], why or '<<< NOT EXPECTED'))
print('jumps over 6 levels: %d, of them not expected: %d' % (len(ev), unknown))
