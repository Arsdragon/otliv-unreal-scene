# Contact sheet with time codes: python -I sheet.py <dir> <out.jpg> [cols] [cell_w] [first] [count]
# Frame files: s_<tenths of a second>.png (stills) or f_<frame>.png (24 fps).
import sys, os, glob
from PIL import Image, ImageDraw, ImageFont
d, out = sys.argv[1], sys.argv[2]
cols = int(sys.argv[3]) if len(sys.argv) > 3 else 5
cw = int(sys.argv[4]) if len(sys.argv) > 4 else 384
first = int(sys.argv[5]) if len(sys.argv) > 5 else 0
count = int(sys.argv[6]) if len(sys.argv) > 6 else 10 ** 6
files = sorted(glob.glob(os.path.join(d, '*.png')))[first:first + count]
ch = cw * 9 // 16
rows = (len(files) + cols - 1) // cols
sheet = Image.new('RGB', (cols * cw, rows * ch), (0, 0, 0))
try: font = ImageFont.truetype('C:/Windows/Fonts/consola.ttf', 18)
except Exception: font = ImageFont.load_default()
dr = ImageDraw.Draw(sheet)
for i, f in enumerate(files):
    im = Image.open(f).convert('RGB').resize((cw, ch), Image.LANCZOS)
    x, y = (i % cols) * cw, (i // cols) * ch
    sheet.paste(im, (x, y))
    n = os.path.splitext(os.path.basename(f))[0]
    t = int(n[2:]) / 10.0 if n.startswith('s_') else int(n[2:]) / 24.0
    lab = '%d:%04.1f' % (int(t) // 60, t % 60)
    dr.rectangle([x + 4, y + 4, x + 84, y + 26], fill=(0, 0, 0))
    dr.text((x + 8, y + 5), lab, fill=(255, 255, 255), font=font)
sheet.save(out, quality=85)
print(out, len(files), 'frames')
