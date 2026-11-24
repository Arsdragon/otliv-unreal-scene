# Import / re-import of models from Models\export (Interchange, glb) with placement and poses.
# Re-run after the models chat updates a model:  import p_props; p_props.run('svetlyak')  (or 'probe_wreck', 'all')
# Assets are replaced in place; old actors are removed and the new hierarchy gets the same label, place and pose.
import unreal, importlib, s1u, e_import
importlib.reload(e_import)
from s1u import *
EXPORT = r'C:\UnrealScenes\Models\export'

# world placement: location in metres, yaw of the imported root (model nose -Y(Blender) = +Y(UE) at yaw 0)
PROPS = {
    'svetlyak':    dict(label='Svetlyak',   dest='/Game/Scene1/Props/Svetlyak',   loc=(13.6, 9.3, 0.95), yaw=95.0,
                        pose={'sv_head': (0.0, -25.0, 0.0)}),
    # wreck axes = scene axes (Blender): Blender (128.6, -153.2) -> UE (128.6, +153.2): 200 m, bearing 50 deg right of +X
    'probe_wreck': dict(label='ProbeWreck', dest='/Game/Scene1/Props/ProbeWreck', loc=(128.6, 153.2, 0.0), yaw=0.0, pose={}),
    # gloves share the cockpit origin and axes: they follow the ship (see q_shots.ship)
    'pilot_gloves': dict(label='PilotGloves', dest='/Game/Scene1/Chaika/Gloves', loc=(0.0, 0.0, 0.0), yaw=-90.0, pose={}, folder='Chaika'),
}


def kids(a):
    out = []
    for c in a.get_attached_actors():
        out += [c] + kids(c)
    return out


def run(name='all'):
    for key in (PROPS if name == 'all' else [name]):
        p = PROPS[key]
        old = find(p['label'])
        before = set(a.get_name() for a in EAS.get_all_level_actors())
        ok = e_import.import_glb(EXPORT + '\\' + key + '\\' + key + '.glb', p['dest'])
        new = [a for a in EAS.get_all_level_actors() if a.get_name() not in before]
        roots = [a for a in new if a.get_attach_parent_actor() is None]
        if roots:
            if old:
                for k in kids(old) + [old]:
                    EAS.destroy_actor(k)
            root = roots[0]
            root.set_actor_label(p['label'])
        else:
            root = old
        if root is None:
            print(key, 'IMPORT FAILED', ok); continue
        place(key)
        print(key, 'imported:', len(new), 'new actors;', 'root', root.get_actor_label())
    save()
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)   # imported assets live in memory until saved


def place(key, loc=None, yaw=None, pose=None):
    p = PROPS[key]
    root = find(p['label'])
    loc = loc or p['loc']; yaw = p['yaw'] if yaw is None else yaw
    root.set_actor_location(unreal.Vector(loc[0] * 100.0, loc[1] * 100.0, loc[2] * 100.0), False, False)
    root.set_actor_rotation(R(0.0, yaw, 0.0), False)
    fold = p.get('folder', 'Props')
    root.set_folder_path(fold)
    ks = kids(root)
    for k in ks:
        k.set_folder_path(fold + '/' + p['label'])
    by = {k.get_actor_label(): k for k in ks}
    for part, pyr in (pose if pose is not None else p['pose']).items():
        if part in by:
            by[part].root_component.set_relative_rotation(R(*pyr), False, False)
    return root
