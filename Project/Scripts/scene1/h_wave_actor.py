import unreal, s1u
from s1u import *
EAL = unreal.EditorAssetLibrary
a = spawn(unreal.StaticMeshActor, 'Wave', loc=(36000 * 100.0, 0, 0), folder='Wave')
c = a.static_mesh_component
c.set_static_mesh(EAL.load_asset('/Game/Scene1/Wave/SM_Wave'))
c.set_mobility(unreal.ComponentMobility.MOVABLE)
c.set_material(0, EAL.load_asset('/Game/Scene1/Materials/MI_Wave'))
c.set_editor_property('cast_shadow', True)
c.set_editor_property('cast_far_shadow', True)
c.set_editor_property('affect_distance_field_lighting', False)
c.set_editor_property('bounds_scale', 1.0)
sun = find('Sun').light_component
sun.set_editor_property('far_shadow_cascade_count', 2)
sun.set_editor_property('far_shadow_distance', 1500000.0)
save()
print('wave actor ok')
