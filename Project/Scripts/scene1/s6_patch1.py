# S6 (real-time version), step 1. One-off patch, run once outside Unreal:  python -I s6_patch1.py
# The parameters that Python animated on material INSTANCES of the two post-process materials cannot be animated in a game.
# They move to a second parameter collection, /Game/Scene1/MPC_OtlivFX (Rain, Dust, Glass, Rainbow, Flash, Flood, Amounts):
# a Level Sequence can key a collection, and in the editor Python now sets the collection instead of the instances
# (which also spares the graphics driver: no material instance is rebuilt every frame any more).
import os, re
D = os.path.dirname(os.path.abspath(__file__))


def rep(s, old, new, count=1):
    assert old in s, old[:80]
    return s.replace(old, new, count)


# ---------------------------------------------------------------- weather material
p = os.path.join(D, 's3_mood_build.py'); s = open(p, encoding='utf-8').read()
s = rep(s, "mpc = EAL.load_asset('/Game/Scene1/MPC_Otliv')\n",
        "mpc = EAL.load_asset('/Game/Scene1/MPC_Otliv')\n"
        "mpcfx = EAL.load_asset('/Game/Scene1/MPC_OtlivFX')          # animated parameters of the post-process materials (made once by s6_fx_collection.py)\n")
s = re.sub(r"rain = g\.vec\('Rain',[^\n]*\n", "rain = g.mpc(mpcfx, 'Rain')            # amount, slant, speed\n", s)
s = re.sub(r"dust = g\.vec\('Dust',[^\n]*\n", "dust = g.mpc(mpcfx, 'Dust')            # horizontal water dust: amount, speed\n", s)
s = re.sub(r"glass = g\.vec\('Glass',[^\n]*\n", "glass = g.mpc(mpcfx, 'Glass')          # drops on the glass: amount, speed, direction of the flow (x, y)\n", s)
s = re.sub(r"bow = g\.vec\('Rainbow',[^\n]*\n", "bow = g.mpc(mpcfx, 'Rainbow')          # rainbow amount\n", s)
s = re.sub(r"flash = g\.vec\('Flash',[^\n]*\n", "flash = g.mpc(mpcfx, 'Flash')          # flash inside the wall: level, sideways, up\n", s)
s = rep(s, "('Rn', rain, 'RGBA'), ('Ds', dust, 'RGBA'),", "('Rn', rain), ('Ds', dust),")
s = rep(s, "('Gl', glass, 'RGBA'), ('Rb', bow, 'RGBA'), ('Fx', flash, 'RGBA')", "('Gl', glass), ('Rb', bow), ('Fx', flash)")
assert "g.vec('Rain'" not in s and "g.vec('Flash'" not in s
open(p, 'w', encoding='utf-8').write(s)

# ---------------------------------------------------------------- underwater material
p = os.path.join(D, 'n_underwater.py'); s = open(p, encoding='utf-8').read()
s = re.sub(r"amt = g\.vec\('Amounts',[^\n]*\n", "mpcfx = EAL.load_asset('/Game/Scene1/MPC_OtlivFX')\namt = g.mpc(mpcfx, 'Amounts')          # particles, bubbles, big bubbles at the glass, rivulets\n", s)
s = re.sub(r"flood = g\.vec\('Flood',[^\n]*\n", "flood = g.mpc(mpcfx, 'Flood')           # r: how high the water has risen over the glass (1 = fully under water), g: blackout\n", s)
s = rep(s, "('Am', amt, 'RGBA')", "('Am', amt)")
s = rep(s, "('Fd', flood, 'RGBA')", "('Fd', flood)")
assert "g.vec('Flood'" not in s
open(p, 'w', encoding='utf-8').write(s)

# ---------------------------------------------------------------- the mood layer writes the collection
p = os.path.join(D, 's3_mood.py'); s = open(p, encoding='utf-8').read()
s = rep(s, "def _set(key, val, fn):",
        "def _fx(name, v):\n"
        "    \"\"\"an animated parameter of the post-process materials: lives in the collection MPC_OtlivFX (a sequence can key it)\"\"\"\n"
        "    v = list(v) + [0.0] * (4 - len(v))\n"
        "    unreal.MaterialLibrary.set_vector_parameter_value(s1u.world(), _S['mpcfx'], name, unreal.LinearColor(v[0], v[1], v[2], v[3]))\n\n\n"
        "def _set(key, val, fn):")
a = s.index("        _S['wx'] = w; mi = _S['mi_wx']\n"); b = s.index("    flc = A('FlashLight')")
s = s[:a] + ("        _S['wx'] = w\n"
             "        _fx('Rain', (w[0], w[1], 1.0, 0.0)); _fx('Dust', (w[2], 2.2, 0.0, 0.0)); _fx('Glass', (w[3], w[6], w[7], w[8]))\n"
             "        _fx('Rainbow', (w[4], 0.0, 0.0, 0.0)); _fx('Flash', (w[5] * 0.7, w[9], w[10], 0.0))\n") + s[b:]
s = rep(s, "lambda v: _mi_vec(_S['mi_uw'], 'Amounts', (0.10, 0.60 * v, 0.0, 0.22))", "lambda v: _fx('Amounts', (0.10, 0.60 * v, 0.0, 0.22))")
s = rep(s, "        _mi_vec(_S['mi_uw'], 'Flood', (round(ks, 3), 0.0, 0.0, 0.0))\n", "        _fx('Flood', (round(ks, 3), 0.0, 0.0, 0.0)); _S['flood'] = None\n")
s = rep(s, "        _mi_vec(_S['mi_uw'], 'Flood', (1.0, 0.0, 0.0, 0.0))\n", "        _S['flood'] = None\n")
# the water rising over the glass before the blow and the blackout were written by the v2 layer into the instance: take over
s = rep(s, "    if _S.get('uw_prev') and not uw:",
        "    if not surf:\n"
        "        if 458.8 <= t < T.T_UP - 0.4:\n"
        "            dk = 0.0\n"
        "            if t >= 460.0: dk = 1.0 if t < 460.5 else 1.0 - sstep((t - 460.5) / 0.7)\n"
        "            fl2 = (round(sstep((t - 459.0) / 1.0), 3), round(dk, 3))\n"
        "        else:\n"
        "            fl2 = (1.0, 0.0)\n"
        "        _set('flood', fl2, lambda v: _fx('Flood', (v[0], v[1], 0.0, 0.0)))\n"
        "    if _S.get('uw_prev') and not uw:")
s = rep(s, "    _S['mi_uw'] = EAL.load_asset(M + 'MI_PP_Underwater');",
        "    _S['mpcfx'] = EAL.load_asset('/Game/Scene1/MPC_OtlivFX'); V._S['uw_mi'] = None      # the v2 layer no longer writes Flood into the instance\n"
        "    _S['mi_uw'] = EAL.load_asset(M + 'MI_PP_Underwater');")
assert "'Flood', unreal.LinearColor" not in s
open(p, 'w', encoding='utf-8').write(s)

# ---------------------------------------------------------------- the bake records every collection
p = os.path.join(D, 'rt_bake.py'); s = open(p, encoding='utf-8').read()
s = rep(s, "    mpc = EAL.load_asset('/Game/Scene1/MPC_Otliv')\n    j = {'f0': f0, 'f1': f1, 'name': name, 'actors': actors, 'mpc': mpc,",
        "    mpcs = [m for m in (EAL.load_asset('/Game/Scene1/MPC_Otliv'), EAL.load_asset('/Game/Scene1/MPC_OtlivFX')) if m is not None]\n"
        "    j = {'f0': f0, 'f1': f1, 'name': name, 'actors': actors, 'mpcs': mpcs,")
s = rep(s, "    j['sc'], j['ve'] = _mpc_params(mpc)\n",
        "    j['sc'] = [(m, n) for m in mpcs for n in _mpc_params(m)[0]]; j['ve'] = [(m, n) for m in mpcs for n in _mpc_params(m)[1]]\n")
s = rep(s, "                    for n in j['sc']: j['data']['S|' + str(n)] = []\n                    for n in j['ve']: j['data']['C|' + str(n)] = []\n",
        "                    for m, n in j['sc']: j['data']['S|' + str(n)] = []\n                    for m, n in j['ve']: j['data']['C|' + str(n)] = []\n")
s = rep(s, "                for n in j['sc']: d['S|' + str(n)].append(float(ML.get_scalar_parameter_value(w, j['mpc'], n)))\n"
           "                for n in j['ve']: d['C|' + str(n)].append(tuple(ML.get_vector_parameter_value(w, j['mpc'], n).to_tuple()))\n",
        "                for m, n in j['sc']: d['S|' + str(n)].append(float(ML.get_scalar_parameter_value(w, m, n)))\n"
        "                for m, n in j['ve']: d['C|' + str(n)].append(tuple(ML.get_vector_parameter_value(w, m, n).to_tuple()))\n")
a = s.index("    # the material parameter collection\n"); b = s.index("    # the view: the film camera for the whole range\n")
s = s[:a] + '''    # the material parameter collections: one track each
    for m in j['mpcs']:
        try:
            tr = seq.add_track(unreal.MovieSceneMaterialParameterCollectionTrack); tr.set_editor_property('mpc', m)
            sec = tr.add_section(); sec.set_range(f0, f1 + 1)
            for mm, n in j['sc']:
                if mm != m: continue
                rows = d['S|' + str(n)]
                for i, v in enumerate(rows):
                    if 0 < i < len(rows) - 1 and v == rows[i - 1] and v == rows[i + 1]: continue
                    sec.add_scalar_parameter_key(n, unreal.FrameNumber((f0 + i) * tick), float(v)); nk += 1
            for mm, n in j['ve']:
                if mm != m: continue
                rows = d['C|' + str(n)]
                for i, v in enumerate(rows):
                    if 0 < i < len(rows) - 1 and v == rows[i - 1] and v == rows[i + 1]: continue
                    sec.add_color_parameter_key(n, unreal.FrameNumber((f0 + i) * tick), unreal.LinearColor(*v)); nk += 1
        except Exception as e:
            notes.append('collection track %s: %s' % (m.get_name(), e))
''' + s[b:]
s = rep(s, "    return 'started: %d actors, %d property channels, %d + %d collection parameters' % (len(actors), len(j['props']), len(j['sc']), len(j['ve']))",
        "    return 'started: %d actors, %d property channels, %d + %d parameters in %d collections' % (len(actors), len(j['props']), len(j['sc']), len(j['ve']), len(mpcs))")
open(p, 'w', encoding='utf-8').write(s)
import ast
for f in ('s3_mood_build.py', 'n_underwater.py', 's3_mood.py', 'rt_bake.py'): ast.parse(open(os.path.join(D, f), encoding='utf-8').read())
print('patched')
