# Create level /Game/Scene1/L_Otliv (no World Partition) + sky and light
import unreal, s1u
from s1u import *
LP = '/Game/Scene1/L_Otliv'
if world().get_path_name().split('.')[0] != LP:
    if unreal.EditorAssetLibrary.does_asset_exist(LP):
        LES.load_level(LP)
    else:
        LES.new_level(LP, False)
F = 'Sky'
sun = spawn(unreal.DirectionalLight, 'Sun', rot=(-10, 180, 0), folder=F)
lc = sun.light_component
lc.set_mobility(unreal.ComponentMobility.MOVABLE)
lc.set_editor_property('atmosphere_sun_light', True)
lc.set_editor_property('intensity', 10.0)
lc.set_editor_property('light_source_angle', 0.53)
lc.set_editor_property('dynamic_shadow_distance_movable_light', 20000.0)
lc.set_editor_property('dynamic_shadow_cascades', 4)
atm = spawn(unreal.SkyAtmosphere, 'SkyAtmosphere', folder=F)
sl = spawn(unreal.SkyLight, 'SkyLight', folder=F)
slc = sl.get_component_by_class(unreal.SkyLightComponent)
slc.set_mobility(unreal.ComponentMobility.MOVABLE)
slc.set_editor_property('real_time_capture', True)
cl = spawn(unreal.VolumetricCloud, 'Clouds', folder=F)
cc = cl.get_component_by_class(unreal.VolumetricCloudComponent)
cc.set_editor_property('layer_bottom_altitude', 1.2)
cc.set_editor_property('layer_height', 0.6)
fog = spawn(unreal.ExponentialHeightFog, 'HeightFog', folder=F)
ppv = spawn(unreal.PostProcessVolume, 'PPV_Global', folder=F)
ppv.set_editor_property('unbound', True)
save()
print('level', world().get_path_name())
