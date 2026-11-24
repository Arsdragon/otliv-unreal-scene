# Instruments instead of ears: levels by act, a spectrogram of the whole film and of every act, silence and clipping.
#   python -I check.py <file.wav | work\name.f32> [more files]      -> check\levels_<name>.txt, spectrum_<name>.png, acts_<name>.png
#   python -I check.py --table <files>                             -> only the table of levels (fast)
import sys, os, math, wave
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np
import dsp
from dsp import SR, F32

ACTS = [(0, 50, 'орбита'), (50, 100, 'вход и посадка'), (100, 220, 'выход и прогулка'), (220, 310, 'обломки'), (310, 370, 'бегство'),
        (370, 430, 'шторм'), (430, 460, 'стена'), (460, 500, 'под водой'), (500, 550, 'всплытие')]
OUT = os.path.join(dsp.ROOT, 'check')
HOP = 4800; NFFT = 8192; NB = 120
EDGES = np.geomspace(20.0, 20000.0, NB + 1)


def chunks(path):
    if path.endswith('.f32'):
        with open(path, 'rb') as f:
            while True:
                b = f.read(dsp.CHUNK * 8)
                if not b: break
                yield np.frombuffer(b, dtype=F32).reshape(-1, 2)
    else:
        w = wave.open(path, 'rb'); ch, sw = w.getnchannels(), w.getsampwidth()
        while True:
            raw = w.readframes(dsp.CHUNK)
            if not raw: break
            if sw == 3:
                b = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3)
                x = (b[:, 0].astype(np.int32) | (b[:, 1].astype(np.int32) << 8) | (b[:, 2].astype(np.int8).astype(np.int32) << 16)).astype(F32) / 8388608.0
            else:
                x = np.frombuffer(raw, dtype='<i2').astype(F32) / 32768.0
            yield x.reshape(-1, ch)
        w.close()


def analyse(path, spectrum=True):
    """-> per-frame (0.1 s) rms and peak, clipped sample count, log-frequency spectrogram (dB)"""
    win = np.hanning(NFFT).astype(F32); freqs = np.fft.rfftfreq(NFFT, 1.0 / SR)
    idx = np.searchsorted(freqs, EDGES)
    rms = []; peak = []; spec = []; clipped = 0; carry = np.zeros((0, 2), dtype=F32); tail = np.zeros(NFFT - HOP, dtype=F32)
    for c in chunks(path):
        clipped += int((np.abs(c) >= 0.9999).sum())
        x = np.concatenate([carry, c]); nfr = len(x) // HOP
        fr = x[:nfr * HOP].reshape(nfr, HOP, 2)
        rms.append(np.sqrt((fr.astype(np.float64) ** 2).mean(axis=(1, 2)))); peak.append(np.abs(fr).max(axis=(1, 2)))
        if spectrum:
            mono = np.concatenate([tail, x[:nfr * HOP].mean(axis=1)])
            for k in range(nfr):
                seg = mono[k * HOP:k * HOP + NFFT]
                if len(seg) < NFFT: break
                p = (np.abs(np.fft.rfft(seg * win)) * (2.0 / win.sum())) ** 2          # a full-scale sine reads 0 dB
                spec.append(np.add.reduceat(p, idx[:-1]) / np.maximum(np.diff(idx), 1))
            tail = mono[nfr * HOP:][-(NFFT - HOP):] if nfr else tail
        carry = x[nfr * HOP:]
    rms = np.concatenate(rms); peak = np.concatenate(peak)
    S = 10.0 * np.log10(np.maximum(np.array(spec).T, 1e-14)) if spectrum and spec else None
    return rms, peak, clipped, S


def dbv(x): return 20.0 * math.log10(max(float(x), 1e-10))


def table(name, rms, peak, clipped):
    lines = ['%s: длина %.1f с, пик %.2f дБFS, отсечённых выборок: %d' % (name, len(rms) * HOP / SR, dbv(peak.max()), clipped),
             '  акт                    время        RMS дБ   пик дБ   самая тихая с   самая громкая с']
    for a, b, nm in ACTS:
        r = rms[int(a * 10):int(b * 10)]; p = peak[int(a * 10):int(b * 10)]
        if not len(r): continue
        sec = np.sqrt(np.convolve(r ** 2, np.ones(10) / 10.0, mode='valid'))
        lines.append('  %-20s %3d:%02d-%d:%02d   %7.1f  %7.1f   %7.1f         %7.1f' % (
            nm, a // 60, a % 60, b // 60, b % 60, dbv(np.sqrt((r ** 2).mean())), dbv(p.max()), dbv(sec.min()), dbv(sec.max())))
    quiet = rms < 10 ** (-75 / 20.0)
    runs = []; s = None
    for i, q in enumerate(quiet):
        if q and s is None: s = i
        if (not q or i == len(quiet) - 1) and s is not None:
            if i - s >= 3: runs.append((s / 10.0, i / 10.0))
            s = None
    lines.append('  тишина ниже -75 дБ дольше 0,3 с: ' + (', '.join('%.1f-%.1f с' % r for r in runs) if runs else 'нет'))
    return '\n'.join(lines)


def pictures(name, rms, S):
    from PIL import Image, ImageDraw, ImageFont
    font = ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', 14)
    lo, hi = -112.0, -38.0
    v = np.clip((S - lo) / (hi - lo), 0, 1)[::-1]                       # high frequencies on top
    stops = np.array([[0, 0, 20], [40, 20, 110], [150, 40, 120], [235, 110, 60], [255, 230, 150]], dtype=np.float64)
    pos = v * (len(stops) - 1); i0 = np.minimum(pos.astype(int), len(stops) - 2); f = (pos - i0)[..., None]
    rgb = (stops[i0] * (1 - f) + stops[i0 + 1] * f).astype(np.uint8)
    full = Image.fromarray(rgb)
    def ticks(d, x0, y0, w, h, t0, t1):
        for fq in (50, 100, 200, 500, 1000, 2000, 5000, 10000):
            y = y0 + h - 1 - int(math.log(fq / 20.0) / math.log(1000.0) * h)
            d.line([x0, y, x0 + 5, y], fill=(255, 255, 255)); d.text((x0 + 8, y - 9), '%d' % fq, fill=(255, 255, 255), font=font)
        step = 10 if t1 - t0 <= 130 else 30
        for tsec in range(int(math.ceil(t0 / step) * step), int(t1) + 1, step):
            x = x0 + int((tsec - t0) / (t1 - t0) * w)
            d.line([x, y0 + h - 8, x, y0 + h], fill=(255, 255, 255)); d.text((x + 3, y0 + h - 20), '%d:%02d' % (tsec // 60, tsec % 60), fill=(255, 255, 255), font=font)
    # the whole film + the level curve
    W, H = 2200, 360
    img = Image.new('RGB', (W, H + 150), (12, 12, 16)); img.paste(full.resize((W, H), Image.BILINEAR), (0, 0)); d = ImageDraw.Draw(img)
    ticks(d, 0, 0, W, H, 0, len(rms) / 10.0)
    for a, b, nm in ACTS:
        x = int(a * 10 / len(rms) * W); d.line([x, 0, x, H + 150], fill=(120, 255, 160)); d.text((x + 4, 4), nm, fill=(120, 255, 160), font=font)
    sec = 20 * np.log10(np.maximum(np.sqrt(np.convolve(rms ** 2, np.ones(10) / 10.0, mode='same')), 1e-6))
    pts = [(int(i / len(sec) * W), H + 150 - int(np.clip((sec[i] + 70.0) / 70.0, 0, 1) * 145)) for i in range(0, len(sec), 2)]
    d.line(pts, fill=(255, 220, 120))
    for lv in (-60, -40, -20, 0):
        y = H + 150 - int((lv + 70.0) / 70.0 * 145); d.line([0, y, W, y], fill=(70, 70, 80)); d.text((4, y - 16), '%d dB' % lv, fill=(170, 170, 180), font=font)
    img.save(os.path.join(OUT, 'spectrum_%s.png' % name))
    # every act stretched to the same width
    W2, H2 = 1800, 170
    sheet = Image.new('RGB', (W2, (H2 + 6) * len(ACTS)), (12, 12, 16)); d = ImageDraw.Draw(sheet)
    for k, (a, b, nm) in enumerate(ACTS):
        part = full.crop((a * 10, 0, min(b * 10, full.width), full.height)).resize((W2, H2), Image.BILINEAR)
        y0 = k * (H2 + 6); sheet.paste(part, (0, y0)); ticks(d, 0, y0, W2, H2, a, b)
        d.text((60, y0 + 3), '%s  %d:%02d-%d:%02d' % (nm, a // 60, a % 60, b // 60, b % 60), fill=(120, 255, 160), font=font)
    sheet.save(os.path.join(OUT, 'acts_%s.png' % name))


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    only = '--table' in sys.argv
    for p in [a for a in sys.argv[1:] if not a.startswith('--')]:
        name = os.path.splitext(os.path.basename(p))[0]
        rms, peak, clipped, S = analyse(p, spectrum=not only)
        txt = table(name, rms, peak, clipped)
        sys.stdout.buffer.write((txt + '\n').encode('utf-8'))
        if not only:
            open(os.path.join(OUT, 'levels_%s.txt' % name), 'w', encoding='utf-8').write(txt + '\n')
            pictures(name, rms, S)
