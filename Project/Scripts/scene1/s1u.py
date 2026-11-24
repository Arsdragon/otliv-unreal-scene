# Scene 1 "Otliv" helpers (run inside Unreal Editor Python)
import unreal
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
UES = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
M = 100.0  # metres -> cm

def world():
    return UES.get_editor_world()

def find(label):
    for a in EAS.get_all_level_actors():
        if a.get_actor_label() == label:
            return a
    return None

def R(p=0.0, y=0.0, r=0.0):
    return unreal.Rotator(pitch=p, yaw=y, roll=r)

def spawn(cls, label, loc=(0, 0, 0), rot=(0, 0, 0), folder=None, replace=False):
    """rot = (pitch, yaw, roll) in degrees"""
    a = find(label)
    if a and replace:
        EAS.destroy_actor(a); a = None
    if a is None:
        a = EAS.spawn_actor_from_class(cls, unreal.Vector(*loc), R(*rot))
        a.set_actor_label(label)
    else:
        a.set_actor_location(unreal.Vector(*loc), False, False)
        a.set_actor_rotation(R(*rot), False)
    if folder:
        a.set_folder_path(folder)
    return a

def save():
    LES.save_current_level()
