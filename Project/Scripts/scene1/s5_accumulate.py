# S5 test: temporal samples -> one frame. The renderer wrote N sub-frames per frame across the open shutter
# (frame n at 24 fps -> files s_<16n+1>, s_<16n+3>, s_<16n+5>, s_<16n+7> for 4 samples at 180 degrees);
# here they are averaged in linear light, which gives the motion blur and smooths the noise.
#   python -I s5_accumulate.py <sub-frame folder> <out folder> <first frame> <last frame>
import sys, os
import numpy as np
from PIL import Image
src, dst, f0, f1 = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
os.makedirs(dst, exist_ok=True)
lut = (np.arange(256) / 255.0) ** 2.2                      # display -> linear (close enough to sRGB for averaging)
n = 0
for f in range(f0, f1 + 1):
    acc = None; k = 0
    for j in (1, 3, 5, 7):
        p = os.path.join(src, 's_%05d.png' % (f * 16 + j))
        if not os.path.exists(p): continue
        a = lut[np.asarray(Image.open(p).convert('RGB'))]
        acc = a if acc is None else acc + a; k += 1
    if not k: print('no sub-frames for', f); continue
    out = np.clip((acc / k) ** (1.0 / 2.2) * 255.0 + 0.5, 0, 255).astype(np.uint8)
    Image.fromarray(out).save(os.path.join(dst, 'f_%05d.png' % f)); n += 1
print('frames written:', n)
