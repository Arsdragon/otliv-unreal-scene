import unreal, s1u, mu
from s1u import *
EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
def mi(name, parent):
    p = '/Game/Scene1/Materials/' + name
    if EAL.does_asset_exist(p): return EAL.load_asset(p)
    x = mu.AT.create_asset(name, '/Game/Scene1/Materials', unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    x.set_editor_property('parent', EAL.load_asset(parent)); EAL.save_loaded_asset(x); return x
def setp(m, **kw):
    for k, v in kw.items():
        if isinstance(v, tuple): MEL.set_material_instance_vector_parameter_value(m, k, unreal.LinearColor(*(list(v) + [1.0] * (4 - len(v)))))
        else: MEL.set_material_instance_scalar_parameter_value(m, k, float(v))
    MEL.update_material_instance(m); EAL.save_loaded_asset(m)
