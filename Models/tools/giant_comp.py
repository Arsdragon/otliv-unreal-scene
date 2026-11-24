# giant_comp.py — кадр «с поверхности»: рендер гиганта с прозрачным фоном (shots/_tmp/giant_v3_raw.png) складывается
# с дневным небом так, как это делает атмосфера: небо + ослабленный свет планеты (ночная сторона тонет в небе).
#   python tools/giant_comp.py
import numpy as np, os
from PIL import Image

ROOT = r'C:\UnrealScenes\Models'
raw = np.asarray(Image.open(os.path.join(ROOT, 'shots', '_tmp', 'giant_v3_raw.png')).convert('RGBA')).astype(np.float32) / 255
lin = lambda c: np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
enc = lambda c: np.where(c <= 0.0031308, c * 12.92, 1.055 * np.clip(c, 0, None) ** (1 / 2.4) - 0.055)
h, w = raw.shape[:2]
t = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
sky = lin(np.array((0.30, 0.46, 0.70), np.float32)) * (1 - t) + lin(np.array((0.58, 0.69, 0.80), np.float32)) * t
planet = lin(raw[..., :3]) * raw[..., 3:4]
out = enc(sky + 0.62 * planet)
Image.fromarray((np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)).save(os.path.join(ROOT, 'shots', 'E_giant_view3.png'))
print('saved shots/E_giant_view3.png')
