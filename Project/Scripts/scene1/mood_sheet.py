# mood_strip.jpg: six stills from one viewpoint with time and a caption. python -I mood_sheet.py [src dir] [out]
import sys, os, glob
from PIL import Image, ImageDraw, ImageFont
src = sys.argv[1] if len(sys.argv) > 1 else 'C:/UnrealScenes/Renders/scene1/mood_strip'
out = sys.argv[2] if len(sys.argv) > 2 else 'C:/UnrealScenes/Review/scene1/animatic/mood_strip.jpg'
CAP = {1500: 'ясно, штиль, зеркало', 2700: 'наползает пелена, первый ветер', 3400: 'облачный вал, сильный ветер, первые капли',
       4000: 'штормовые сумерки, ливень', 4400: 'почти темно, стена воды', 5200: 'позади волны: небо расчищается'}
fs = sorted(glob.glob(os.path.join(src, 's_*.png')))
cw, ch, cols = 640, 360, 3
rows = (len(fs) + cols - 1) // cols
sh = Image.new('RGB', (cols * cw, rows * ch), (0, 0, 0))
font = ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', 20)
dr = ImageDraw.Draw(sh)
for i, f in enumerate(fs):
    k = int(os.path.basename(f)[2:-4]); t = k / 10.0
    x, y = (i % cols) * cw, (i // cols) * ch
    sh.paste(Image.open(f).convert('RGB').resize((cw, ch), Image.LANCZOS), (x, y))
    lab = '%d:%02d  %s' % (int(t) // 60, int(t) % 60, CAP.get(k, ''))
    wtxt = dr.textlength(lab, font=font)
    dr.rectangle([x + 8, y + 8, x + 20 + wtxt, y + 38], fill=(0, 0, 0))
    dr.text((x + 14, y + 10), lab, fill=(255, 255, 255), font=font)
sh.save(out, quality=88)
print(out, len(fs))
