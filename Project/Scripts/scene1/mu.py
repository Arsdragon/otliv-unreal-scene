# Material building helpers
import unreal
MEL = unreal.MaterialEditingLibrary
EAL = unreal.EditorAssetLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()
MP = unreal.MaterialProperty
MATDIR = '/Game/Scene1/Materials'

def new_mat(name, shading=None, blend=None, two_sided=False, path=MATDIR):
    full = path + '/' + name
    if EAL.does_asset_exist(full):
        m = EAL.load_asset(full)
        MEL.delete_all_material_expressions(m)
        for e in list(MEL.get_material_expressions(m)):
            MEL.delete_material_expression(m, e)
    else:
        m = AT.create_asset(name, path, unreal.Material, unreal.MaterialFactoryNew())
    if shading is not None:
        m.set_editor_property('shading_model', shading)
    if blend is not None:
        m.set_editor_property('blend_mode', blend)
    m.set_editor_property('two_sided', two_sided)
    return m

class G:
    """node graph builder for one material"""
    def __init__(self, m):
        self.m = m; self.x = -1600; self.y = 0
    def _n(self, cls):
        self.y += 140
        if self.y > 1400: self.y = 0; self.x += 320
        return MEL.create_material_expression(self.m, cls, self.x, self.y)
    def scalar(self, name, v):
        n = self._n(unreal.MaterialExpressionScalarParameter)
        n.set_editor_property('parameter_name', name); n.set_editor_property('default_value', v); return n
    def vec(self, name, v):
        n = self._n(unreal.MaterialExpressionVectorParameter)
        n.set_editor_property('parameter_name', name)
        n.set_editor_property('default_value', unreal.LinearColor(*(list(v) + [1.0] * (4 - len(v))))); return n
    def const(self, v):
        n = self._n(unreal.MaterialExpressionConstant); n.set_editor_property('r', v); return n
    def wpos(self):
        return self._n(unreal.MaterialExpressionWorldPosition)
    def node(self, cls, **props):
        n = self._n(cls)
        for k, v in props.items(): n.set_editor_property(k, v)
        return n
    def mpc(self, coll, name):
        n = self._n(unreal.MaterialExpressionCollectionParameter)
        n.set_editor_property('collection', coll); n.set_editor_property('parameter_name', name); return n
    def tex(self, path, sampler=None, uv=None):
        n = self._n(unreal.MaterialExpressionTextureSampleParameter2D) if False else self._n(unreal.MaterialExpressionTextureSample)
        n.set_editor_property('texture', EAL.load_asset(path))
        if sampler is not None: n.set_editor_property('sampler_type', sampler)
        if uv is not None: MEL.connect_material_expressions(uv, '', n, 'UVs')
        return n
    def custom(self, code, inputs, out='f3', outs=()):
        """inputs: list of (name, node[, pin]); outs: list of (name, type) extra outputs"""
        T = {'f1': unreal.CustomMaterialOutputType.CMOT_FLOAT1, 'f2': unreal.CustomMaterialOutputType.CMOT_FLOAT2,
             'f3': unreal.CustomMaterialOutputType.CMOT_FLOAT3, 'f4': unreal.CustomMaterialOutputType.CMOT_FLOAT4}
        n = self._n(unreal.MaterialExpressionCustom)
        n.set_editor_property('code', code)
        n.set_editor_property('output_type', T[out])
        ins = []
        for i in inputs:
            ci = unreal.CustomInput(); ci.set_editor_property('input_name', i[0]); ins.append(ci)
        n.set_editor_property('inputs', ins)
        if outs:
            ol = []
            for o in outs:
                co = unreal.CustomOutput(); co.set_editor_property('output_name', o[0]); co.set_editor_property('output_type', T[o[1]]); ol.append(co)
            n.set_editor_property('additional_outputs', ol)
        for i in inputs:
            ok = MEL.connect_material_expressions(i[1], i[2] if len(i) > 2 else '', n, i[0])
            if not ok: print('connect failed', i[0])
        return n
    def link(self, a, apin, b, bpin):
        ok = MEL.connect_material_expressions(a, apin, b, bpin)
        if not ok: print('link failed', bpin)
    def out(self, n, prop, pin=''):
        ok = MEL.connect_material_property(n, pin, prop)
        if not ok: print('prop failed', prop)
    def done(self):
        MEL.layout_material_expressions(self.m)
        MEL.recompile_material(self.m)
        EAL.save_loaded_asset(self.m)

def mpc_asset(path='/Game/Scene1/MPC_Otliv', scalars=(), vectors=()):
    if EAL.does_asset_exist(path):
        c = EAL.load_asset(path)
    else:
        d, n = path.rsplit('/', 1)
        c = AT.create_asset(n, d, unreal.MaterialParameterCollection, unreal.MaterialParameterCollectionFactoryNew())
    sp, vp = [], []
    for k, v in scalars:
        x = unreal.CollectionScalarParameter(); x.set_editor_property('parameter_name', k); x.set_editor_property('default_value', v); sp.append(x)
    for k, v in vectors:
        x = unreal.CollectionVectorParameter(); x.set_editor_property('parameter_name', k); x.set_editor_property('default_value', unreal.LinearColor(*v)); vp.append(x)
    c.set_editor_property('scalar_parameters', sp)
    c.set_editor_property('vector_parameters', vp)
    EAL.save_loaded_asset(c)
    return c
