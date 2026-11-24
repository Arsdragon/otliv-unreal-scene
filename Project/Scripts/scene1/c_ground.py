# Seabed + water as 20 km tiles (objects >~40 km lose reflections), parented to roots
import unreal, s1u
from s1u import *
EAL = unreal.EditorAssetLibrary
plane = EAL.load_asset('/Engine/BasicShapes/Plane')
T = 20000.0 * 100  # tile 20 km in cm
XS = range(-3, 5)   # x centers: -50..+90 km
YS = range(-4, 4)   # y centers: -70..+70 km
for l in ['Seabed', 'Water']:
    a = find(l)
    if a: EAS.destroy_actor(a)
def layer(name, z, mat):
    root = spawn(unreal.StaticMeshActor, name + 'Root', loc=(0, 0, z), folder='Ground')
    root.static_mesh_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    m = EAL.load_asset(mat)
    for ix in XS:
        for iy in YS:
            lb = '%s_%d_%d' % (name, ix, iy)
            a = spawn(unreal.StaticMeshActor, lb, loc=((ix + 0.5) * T, (iy + 0.5) * T, z), folder='Ground/' + name)
            c = a.static_mesh_component
            c.set_static_mesh(plane)
            c.set_mobility(unreal.ComponentMobility.MOVABLE)
            a.set_actor_scale3d(unreal.Vector(20000, 20000, 1))
            c.set_material(0, m)
            c.set_editor_property('cast_shadow', False)
            c.set_editor_property('affect_distance_field_lighting', False)
            a.attach_to_actor(root, '', unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, False)
    return root
layer('Seabed', 0.0, '/Game/Scene1/Materials/M_Seabed')
layer('Water', 45.0, '/Game/Scene1/Materials/M_Water')
save()
print('ok')
