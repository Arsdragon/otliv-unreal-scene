# S8 (2026-11-28): a friend of the user ran build v1.1 on his PC (Review\scene1\feedback_2026-11-28). Fixes:
#   1. black gas giant in orbit: since the sun moved to -X (S7) the giant (azimuth ~210 deg) shows us its night side and
#      only the rings were seen. The giant and its rings get back their own light from +X, as on the approved KF1
#      (artistic licence: nobody compares the giant's light with the sun of the planet below).
#   2. "black cloud" over the crest: the dark roll cloud ribbon WaveRoll. Removed from the scene: its track in the sequence
#      is deleted and the actor is hidden; over the crest only the sky, the water dust and the spray remain.
#   3. rain streaks across half the screen: each streak 4x shorter and half as thin (the falling speed on screen stays),
#      a little brighter so the rain does not get weaker overall.
#   python -I s8_feedback.py            -> patches the builder scripts (idempotent)
#   in the editor: import s8_feedback; s8_feedback.editor()   -> patches the materials, the level and the sequence, saves
import os

S7_L = 'float3 L = float3(-0.9848, 0.0, 0.1736);'
GIANT_L = 'float3 L = float3(0.9848, 0.0, 0.1736);'      # no comment here: in k_giant one line holds several statements
BAD_L = 'float3 L = float3(0.9848, 0.0, 0.1736);       // 2026-11-28: the giant keeps the light of KF1 (sun moved, the giant did not)'
R_LEN_OLD = 'float len = 0.09 + 0.20*u.h1(col*1.7 + 9.0*fi);'
R_LEN_NEW = 'float len = 0.36 + 0.80*u.h1(col*1.7 + 9.0*fi);        // 2026-11-28: streaks 4x shorter'
R_SPD_OLD = '- T*Rn.b*(6.0 + 3.5*fi)*(0.7 + 0.6*hr)'
R_SPD_NEW = '- T*Rn.b*4.0*(6.0 + 3.5*fi)*(0.7 + 0.6*hr)'
R_W_OLD = 'smoothstep(0.13 - 0.02*fi, 0.0, xin)'
R_W_NEW = 'smoothstep(0.07 - 0.012*fi, 0.0, xin)'
R_B_OLD = 'outc += float3(0.70, 0.76, 0.82) * streak * 0.20 *'
R_B_NEW = 'outc += float3(0.70, 0.76, 0.82) * streak * 0.28 *'
RAIN = [(R_LEN_OLD, R_LEN_NEW), (R_SPD_OLD, R_SPD_NEW), (R_W_OLD, R_W_NEW), (R_B_OLD, R_B_NEW)]
MATS = [('/Game/Scene1/Materials/M_Giant', [(BAD_L, GIANT_L), (S7_L, GIANT_L)]),
        ('/Game/Scene1/Materials/M_GiantRings', [(BAD_L, GIANT_L), (S7_L, GIANT_L)]),
        ('/Game/Scene1/Materials/M_PP_Weather', RAIN)]
FILES = {'k_giant.py': [(BAD_L, GIANT_L), (S7_L, GIANT_L)], 's3_mood_build.py': RAIN}
SEQ = '/Game/Scene1/Seq/SEQ_Otliv_RT'
GONE = ['WaveRoll']


def files():
    d = os.path.dirname(os.path.abspath(__file__)); out = []
    for f, reps in FILES.items():
        p = os.path.join(d, f); s = open(p, encoding='utf-8').read(); n = 0
        for old, new in reps:
            if old in s: s = s.replace(old, new); n += 1
        open(p, 'w', encoding='utf-8').write(s); out.append((f, n))
    return out


def editor(save=True):
    import unreal, s1u
    MEL = unreal.MaterialEditingLibrary; EAL = unreal.EditorAssetLibrary; out = []
    for path, reps in MATS:
        m = EAL.load_asset(path); n = 0
        for e in MEL.get_material_expressions(m):
            if not isinstance(e, unreal.MaterialExpressionCustom): continue
            code = e.get_editor_property('code'); c2 = code
            for old, new in reps:
                if old in c2: c2 = c2.replace(old, new)
            if c2 != code:
                e.set_editor_property('code', c2); n += 1
        if n:
            MEL.recompile_material(m)
            if save: EAL.save_loaded_asset(m)
        out.append((path.rsplit('/', 1)[1], n))
    seq = unreal.load_asset(SEQ + '.' + SEQ.rsplit('/', 1)[1])
    for lb in GONE:
        a = s1u.find(lb)
        for b in seq.get_bindings():
            if b.get_display_name() == lb or (a and b.get_name() == lb):
                b.remove(); out.append(('binding removed', lb))
        if a:
            a.set_actor_hidden_in_game(True); a.set_is_temporarily_hidden_in_editor(True)
            a.root_component.set_visibility(False, True)
            out.append(('hidden', lb))
    if save:
        EAL.save_loaded_asset(seq); s1u.save()
    return out


if __name__ == '__main__':
    print(files())
