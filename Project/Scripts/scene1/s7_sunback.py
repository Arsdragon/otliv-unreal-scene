# S7 (user's edit 2026-11-27): the sun moves behind the viewer. It was at +X, 10 deg high, right behind the wave, and its
# glare hid the wave; now it is at -X, 10 deg high: the wave is lit from the front (slope, foam streams, crest).
# What depended on "the sun behind the wave" and how it changes:
#   - the Sun itself: yaw 180 -> 0 (light travels toward +X);
#   - the wave shadow (light function M_LF_WaveShadow): the crest no longer shades the viewer, so no function on the Sun.
#     The moment "the crest swallows the sun" (6:20) becomes the sun fading in the overcast and the water dust: SUN_I in
#     s3_mood goes down smoothly instead of a shadow edge passing over the ship;
#   - wave material: turquoise only in the thin lip of the crest (side light through thin water), full only when one looks
#     toward the sun (the departing wave after surfacing is backlit);
#   - water dust ribbons, gas giant and its rings: the sun vector in their shaders;
#   - the rainbow: 42 degrees around the antisolar point, which is now on the +X side.
# Physically, after surfacing the ship would stay in the shadow of the departed wave for ~40 s (2 km wall, 10 deg sun);
# the mood table wants pale washed light there, so the wave casts no shadow at all (same artistic licence as before).
#   python -I s7_sunback.py           -> patches the builder scripts (run once; idempotent)
#   in the editor: import s7_sunback; s7_sunback.editor()   -> patches the existing materials and the light, saves
import os

OLD_L = 'float3 L = float3(0.9848, 0.0, 0.1736);'
NEW_L = 'float3 L = float3(-0.9848, 0.0, 0.1736);'
OLD_A = 'float3 A = float3(-0.9848, 0.0, -0.1736);'
NEW_A = 'float3 A = float3(0.9848, 0.0, -0.1736);'
OLD_TQ = 'float ph = pow(cosv, max(Ph, 1.0));'
NEW_TQ = 'float ph = smoothstep(0.80, 0.97, zf) * (0.35 + 0.65 * pow(cosv, max(Ph, 1.0)));'
# (material, [(old, new)]) - the code of the Custom nodes inside the existing materials
MATS = [('/Game/Scene1/Materials/M_Wave', [(OLD_L, NEW_L), (OLD_TQ, NEW_TQ)]),
        ('/Game/Scene1/Materials/M_Spray', [(OLD_L, NEW_L)]),
        ('/Game/Scene1/Materials/M_Giant', [(OLD_L, NEW_L)]),
        ('/Game/Scene1/Materials/M_GiantRings', [(OLD_L, NEW_L)]),
        ('/Game/Scene1/Materials/M_PP_Weather', [(OLD_A, NEW_A)])]
FILES = {'g_wave_mat.py': [(OLD_L, NEW_L), (OLD_TQ, NEW_TQ),
                           ('# No glowing rim: turquoise appears only as a soft band where the water is thin AND the sun is right behind it.',
                            '# No glowing rim: turquoise only in the thin lip of the crest (2026-11-27: the sun is behind the viewer).')],
         'm_spray.py': [(OLD_L, NEW_L)], 'k_giant.py': [(OLD_L, NEW_L)], 's3_mood_build.py': [(OLD_A, NEW_A)],
         'a_level.py': [("rot=(-10, 180, 0)", "rot=(-10, 0, 0)")],
         's3_mood.py': [('SUN_I = [(215, 10.0), (310, 6.5), (370, 3.2), (430, 1.6), (460, 1.2), (500, 5.5), (545, 8.0)]',
                         'SUN_I = [(215, 10.0), (310, 6.5), (350, 3.8), (380, 1.3), (405, 0.30), (430, 0.14), (460, 0.10), (500, 5.5), (545, 8.0)]'
                         '      # 2026-11-27: the sun behind us fades in the overcast and water dust (no crest shadow any more)')],
         'o_lightfn.py': [("sun.set_editor_property('light_function_material', m)",
                           "sun.set_editor_property('light_function_material', None)      # 2026-11-27: sun behind the viewer, the crest shades nothing we see")]}


def files():
    d = os.path.dirname(os.path.abspath(__file__)); out = []
    for f, reps in FILES.items():
        p = os.path.join(d, f); s = open(p, encoding='utf-8').read(); n = 0
        for old, new in reps:
            if new in s: continue
            assert old in s, (f, old[:60])
            s = s.replace(old, new); n += 1
        open(p, 'w', encoding='utf-8').write(s); out.append((f, n))
    return out


def editor():
    import unreal, s1u
    MEL = unreal.MaterialEditingLibrary; EAL = unreal.EditorAssetLibrary; out = []
    for path, reps in MATS:
        m = EAL.load_asset(path); n = 0
        for e in MEL.get_material_expressions(m):
            if not isinstance(e, unreal.MaterialExpressionCustom): continue
            code = e.get_editor_property('code'); c2 = code
            for old, new in reps:
                if new not in c2: c2 = c2.replace(old, new)
            if c2 != code:
                e.set_editor_property('code', c2); n += 1
        if n:
            MEL.recompile_material(m); EAL.save_loaded_asset(m)
        out.append((path.rsplit('/', 1)[1], n))
    sun = s1u.find('Sun')
    sun.set_actor_rotation(unreal.Rotator(pitch=-10.0, yaw=0.0, roll=0.0), False)
    lc = sun.light_component; lc.set_editor_property('light_function_material', None)
    s1u.save()
    return out, sun.get_actor_rotation()


if __name__ == '__main__':
    print(files())
