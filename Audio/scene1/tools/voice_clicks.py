# Which lines of a voice folder have clicks (isolated 1-2 ms spikes in the 4-7.5 kHz band)? Prints their numbers, comma
# separated, or nothing. Piper's synthesis is a little different on every run, so a line with a click is simply made again.
#   python -I voice_clicks.py <folder>
import sys, os, glob
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
folder = os.path.abspath(sys.argv[1]); sys.argv = sys.argv[:1]
import numpy as np
import voice_process as vp, voice_probe as pr
bad = []
for f in sorted(glob.glob(os.path.join(folder, 'bort_??.wav'))):
    x, _ = vp.pick_take(vp.load(f), '1')
    if pr.clicks(x.astype(np.float64)) > 0: bad.append(os.path.basename(f)[5:7])
print(','.join(bad))
