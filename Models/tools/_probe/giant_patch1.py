# правка giant_tex.py: спокойнее полосы, быстрее шум
p = r'C:\UnrealScenes\Models\tools\giant_tex.py'
s = open(p, encoding='utf-8').read()


def rep(a, b):
    global s
    assert a in s, a[:70]
    s = s.replace(a, b)


a = s.index("            i = i.astype(np.int64)\n")
b = s.index("            fx, fy, fz = f[:, 0], f[:, 1], f[:, 2]")
s = s[:a] + """            i = (i.astype(np.int64) & 0xFFFFFFFF).astype(np.uint32)
            f = f * f * (3 - 2 * f)
            kx, ky, kz = np.uint32(73856093), np.uint32(19349663), np.uint32(83492791)
            ix, iy, iz = i[:, 0] * kx, i[:, 1] * ky, i[:, 2] * kz
            sd = np.uint32(((seed * 1013 + o * 7919 + 1) * 2654435761) & 0xFFFFFFFF)

            def h(dx, dy, dz):
                n = (ix + kx * np.uint32(dx)) ^ (iy + ky * np.uint32(dy)) ^ (iz + kz * np.uint32(dz)) ^ sd
                n = (n ^ (n >> np.uint32(15))) * np.uint32(2246822519)
                n = (n ^ (n >> np.uint32(13))) * np.uint32(3266489917)
                n = n ^ (n >> np.uint32(16))
                return (n >> np.uint32(8)).astype(np.float32) * np.float32(1 / 16777215)

""" + s[b:]
rep("AMP = {'belt': 1.0, 'zone': 0.38, 'cap': 0.75}", "AMP = {'belt': 1.0, 'zone': 0.32, 'cap': 0.50}")
rep("('zone', (0.68, 0.74, 0.78)), ('belt', (0.55, 0.62, 0.68))", "('zone', (0.70, 0.75, 0.78)), ('belt', (0.58, 0.64, 0.68))")
rep("('belt', (0.70, 0.60, 0.47))", "('belt', (0.74, 0.65, 0.53))")
rep("('belt', (0.73, 0.60, 0.44))", "('belt', (0.76, 0.64, 0.49))")
rep("('belt', (0.68, 0.54, 0.40))", "('belt', (0.72, 0.59, 0.45))")
rep("('belt', (0.59, 0.66, 0.72)), ('zone', (0.71, 0.77, 0.81)), ('cap', (0.50, 0.58, 0.66))",
    "('belt', (0.61, 0.67, 0.71)), ('zone', (0.72, 0.77, 0.80)), ('cap', (0.52, 0.59, 0.66))")
rep("0.050 * (noise1d(LAT, 0.55, 1)", "0.060 * (noise1d(LAT, 0.55, 1)")
rep("0.030 * (noise1d(LAT, 1.7, 2)", "0.042 * (noise1d(LAT, 1.7, 2)")
rep("0.016 * (noise1d(LAT, 4.5, 3)", "0.024 * (noise1d(LAT, 4.5, 3)")
rep("np.array((0.030, 0.006, -0.026))", "np.array((0.040, 0.008, -0.034))")
rep("    u = 0.55 * np.exp(-(lat / 7.5) ** 2)", "    u = 0.75 * np.exp(-(lat / 7.5) ** 2)")
rep("        u = u + s * 0.45 * np.exp(", "        u = u + s * 0.62 * np.exp(")
rep("BIG = dict(lat=-25.6, lon=200.0, sl=5.6, sp=3.1, turns=2.4)", "BIG = dict(lat=-25.6, lon=200.0, sl=6.6, sp=3.5, turns=2.2)")
rep("    for k in range(34):", "    for k in range(14):")
rep("sl=s, sp=s, turns=rng.uniform(0.9, 1.7)))", "sl=s, sp=s, turns=rng.uniform(0.6, 1.2)))")
rep("DYES.append((la, VORT[-1]['lon'], s, s, c, rng.uniform(0.35, 0.6)))", "DYES.append((la, VORT[-1]['lon'], s, s, c, rng.uniform(0.2, 0.4)))")
rep("            a = rng.uniform(0.0025, 0.0055) / (1 + k)", "            a = rng.uniform(0.0015, 0.0035) / (1 + k)")
rep("        t = 0.011 * (vnoise3(Pa, 13, seed, 2) - 0.5) * 2 + 0.0035 * (vnoise3(Pa, 36, seed + 5, 1) - 0.5) * 2",
    "        t = 0.0065 * (vnoise3(Pa, 13, seed, 2) - 0.5) * 2 + 0.0020 * (vnoise3(Pa, 36, seed + 5, 1) - 0.5) * 2")
a = s.index("        wv = (vnoise3(P0 * np.array((1, 1, 2), np.float32), 30, 31, 3) - 0.5) * 2")
b = s.index("        dx, dy = (x0.ravel() + 0.5) * DW / W - 0.5")
s = s[:a] + """        wv = (vnoise3(P0 * np.array((1, 1, 4), np.float32), 22, 31, 2) - 0.5) * 2
        latp = lat0 + amp * wv * 0.5 + (vnoise3(P0, 110, 37, 1) - 0.5) * 0.2
        col = np.stack([np.interp(latp, LAT, LUT[:, k]) for k in range(3)], -1).astype(np.float32)
        n1 = vnoise3(P0 * np.array((1, 1, 3), np.float32), 7, 41, 3)
        n2 = vnoise3(P0 * np.array((1, 1, 2), np.float32), 48, 43, 2)
        n3 = vnoise3(P0, 4.5, 47, 2)
        n4 = vnoise3(P0 * np.array((0.35, 0.35, 6), np.float32), 30, 49, 1)       # тонкие длинные полоски
        col *= (1 + (0.04 + 0.07 * amp) * (n1 - 0.5) * 2)[:, None]
        col *= (1 + 0.04 * (n2 - 0.5) * 2 + 0.05 * (n4 - 0.5) * 2)[:, None]
        col += ((n3 - 0.5) * 2 * 0.035)[:, None] * np.array((1.0, 0.1, -1.0), np.float32)
""" + s[b:]
open(p, 'w', encoding='utf-8').write(s)
print('ok')
