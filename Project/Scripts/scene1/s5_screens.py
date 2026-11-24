# S5: the screens of the cockpit follow the story. Pictures and manifest come from the models chat:
#   C:\UnrealScenes\Models\export\cockpit_screens\<state>\T_Screen_1..5.png, manifest.json (states with from_s / to_s).
# screen_6 (the airlock display) is not in the sets and keeps its picture. The manifest has no pictures for 7:40-8:20
# (the blow, under water): there the set "failure" is shown from the moment the blackout ends - the engines are dead already.
# In "failure" the fifth screen flickers: its second frame flashes for 0.08-0.2 s at uneven gaps (the hint of the manifest).
import os, json, math
import unreal

SRC = r'C:\UnrealScenes\Models\export\cockpit_screens'
DST = '/Game/Scene1/Chaika/Cockpit/Screens'
MI = '/Game/Scene1/Chaika/Cockpit/chaika_cockpit/Materials/screen_%d'
T_AFTER_BLOW = 460.5
MEL = unreal.MaterialEditingLibrary; EAL = unreal.EditorAssetLibrary
_S = {'states': None, 'cur': None, 'params': None}


def available(): return os.path.exists(os.path.join(SRC, 'manifest.json'))


def _import(rel, name, folder):
    dest = '%s/%s' % (DST, folder)
    if not EAL.does_asset_exist('%s/%s' % (dest, name)):
        task = unreal.AssetImportTask()
        task.set_editor_property('filename', os.path.join(SRC, rel.replace('/', os.sep))); task.set_editor_property('destination_path', dest)
        task.set_editor_property('destination_name', name); task.set_editor_property('automated', True)
        task.set_editor_property('replace_existing', True); task.set_editor_property('save', True)
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    return EAL.load_asset('%s/%s' % (dest, name))


def load():
    """imports the pictures (once) and remembers the states: [(from, to, folder, {slot: texture}, second frame of slot 5 or None)]"""
    if not available(): return None
    man = json.load(open(os.path.join(SRC, 'manifest.json'), encoding='utf-8'))
    out = []
    for st in man['states']:
        folder = st['folder']; tex = {}
        for rel in st['files']:
            idx = int(os.path.basename(rel).split('_')[-1].split('.')[0])
            t = _import(rel, 'T_Scr_%s_%d' % (folder, idx), folder)
            if t is not None: tex[idx] = t
        alt = None; fl = st.get('flicker')
        if fl and len(fl.get('frames', [])) > 1:
            alt = (int(fl['slot'].split('_')[-1]), _import(fl['frames'][1], 'T_Scr_%s_%s_b' % (folder, fl['slot'].split('_')[-1]), folder))
        out.append((float(st['from_s']), float(st['to_s']) if st.get('to_s') is not None else 1.0e9, folder, tex, alt))
    out.sort(key=lambda s: s[0])
    _S['states'] = out; _S['cur'] = None
    # which texture parameters of the screen materials hold the picture now (the glb import filled them)
    mi = EAL.load_asset(MI % 1); _S['params'] = []
    for prm in ('EmissiveTexture', 'BaseColorTexture'):
        cur = MEL.get_material_instance_texture_parameter_value(mi, prm)
        if cur is not None and 'screen' in cur.get_name().lower(): _S['params'].append(prm)
    if not _S['params']: _S['params'] = ['EmissiveTexture']
    return [(s[2], sorted(s[3])) for s in out], _S['params']


def _h(x): return (math.sin(x * 127.1) * 43758.5453) % 1.0


def burst(t):
    """the fifth screen breaks up: every half second there is a one-in-three chance of a flash 0.08-0.2 s long"""
    k = math.floor(t / 0.5); u = t - k * 0.5
    if _h(k * 1.37 + 5.0) > 0.36: return False
    s = 0.28 * _h(k * 2.11 + 1.0)
    return s <= u < s + 0.08 + 0.12 * _h(k * 3.7 + 9.0)


def state_at(t):
    st = _S['states']; cur = st[0]
    for s in st:
        if t >= s[0]: cur = s
    if T_AFTER_BLOW <= t and cur[2] != st[-1][2]: cur = st[-1]          # no pictures for the time under water: the last set, early
    return cur


def apply(t):
    """puts the pictures of the current state on the screens (only when something changes)"""
    if not _S['states']: return
    s = state_at(t); alt = s[4]
    b = bool(alt) and burst(t)
    key = (s[2], b)
    if key == _S['cur']: return
    full = _S['cur'] is None or _S['cur'][0] != s[2]
    _S['cur'] = key
    for idx, tex in s[3].items():
        if alt and idx == alt[0]: tex = alt[1] if b else tex
        elif not full: continue
        mi = EAL.load_asset(MI % idx)
        if mi is None or tex is None: continue
        for prm in _S['params']: MEL.set_material_instance_texture_parameter_value(mi, prm, tex)
        MEL.update_material_instance(mi)
