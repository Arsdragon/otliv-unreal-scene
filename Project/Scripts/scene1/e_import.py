# Import a glb into the level with Interchange (scene import keeps part hierarchy and pivots)
import unreal
def import_glb(path, dest):
    src = unreal.InterchangeManager.create_source_data(path)
    p = unreal.ImportAssetParameters()
    p.is_automated = True
    p.replace_existing = True
    mgr = unreal.InterchangeManager.get_interchange_manager_scripted()
    r = mgr.import_scene(dest, src, p)
    mgr.wait_until_all_tasks_done(False)
    return r
