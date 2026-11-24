# contact.py — склеить несколько кадров в один уменьшенный лист (чтобы проверять одним взглядом):
#   python tools/contact.py выход.png кадр1.png кадр2.png … [--cols 2] [--w 960]
import sys
from PIL import Image

a = sys.argv[1:]
cols = int(a[a.index('--cols') + 1]) if '--cols' in a else 2
w = int(a[a.index('--w') + 1]) if '--w' in a else 960
files = [f for i, f in enumerate(a[1:], 1) if not f.startswith('--') and not a[i - 1].startswith('--')]
ims = [Image.open(f).convert('RGB') for f in files]
ims = [im.resize((w, int(im.height * w / im.width)), Image.LANCZOS) for im in ims]
h = max(im.height for im in ims)
rows = (len(ims) + cols - 1) // cols
out = Image.new('RGB', (cols * w, rows * h), (30, 30, 32))
for k, im in enumerate(ims):
    out.paste(im, ((k % cols) * w, (k // cols) * h))
out.save(a[0])
print('saved', a[0], out.size)
