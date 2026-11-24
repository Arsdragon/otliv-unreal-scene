# S3: master sequence /Game/Scene1/Seq/SEQ_Otliv_Master (24 fps, 0:00-9:10), baked from s3_timeline:
#  - markers on the times of the on-board voice lines (SCENE1.md) and on the act boundaries;
#  - camera cut + transform and focal length of CAM_Film (keys every 4 frames);
#  - transforms of the ship roots, the drone and both waves (keys every 12 frames, every frame during the ride and the impact).
# Material/collection parameters, water level, lights and post are still driven by s3_timeline.apply_time (to be moved to tracks in S5).
import unreal, importlib, math
import s1u, s3_timeline as T
AT = unreal.AssetToolsHelpers.get_asset_tools()
EAL = unreal.EditorAssetLibrary
PATH, NAME = '/Game/Scene1/Seq', 'SEQ_Otliv_Master'
FULL = PATH + '/' + NAME
END = int(T.T_END * 24)
ACTS = [(0, 'АКТ 1: орбита'), (50, 'АКТ 2: вход в атмосферу, посадка'), (100, 'АКТ 3: выход, путь за дроном'), (220, 'АКТ 4: обломки, накопитель'),
        (310, 'АКТ 5: замер, бег к кораблю'), (370, 'АКТ 6: гребень закрывает солнце'), (430, 'АКТ 7: стена, подъём, удар 7:40'),
        (500, 'АКТ 8: всплытие, вторая волна'), (540, 'ТИТР «ОТЛИВ»')]


def build():
    if EAL.does_asset_exist(FULL):
        EAL.delete_asset(FULL)
    seq = AT.create_asset(NAME, PATH, unreal.LevelSequence, unreal.LevelSequenceFactoryNew())
    seq.set_display_rate(unreal.FrameRate(24, 1))
    seq.set_playback_start(0); seq.set_playback_end(END)
    tps = seq.get_tick_resolution(); tick = int(tps.numerator / tps.denominator / 24)
    # markers
    for t, text in [(a, b) for a, b in T.LINES] + ACTS:
        mf = unreal.MovieSceneMarkedFrame()
        mf.set_editor_property('frame_number', unreal.FrameNumber(int(t * 24) * tick))
        mf.set_editor_property('label', ('%d:%02d ' % (int(t) // 60, int(t) % 60)) + text)
        seq.add_marked_frame(mf)
    # actors
    T.init()
    binds = {}
    for lb in ['CAM_Film', 'Chaika', 'ChaikaCockpit', 'PilotGloves', 'Svetlyak', 'Wave', 'Wave2']:
        b = seq.add_possessable(T.A(lb))
        tr = b.add_track(unreal.MovieScene3DTransformTrack)
        sec = tr.add_section(); sec.set_range(0, END)
        binds[lb] = (b, sec.get_all_channels())
    cam_b = binds['CAM_Film'][0]
    cut = seq.add_track(unreal.MovieSceneCameraCutTrack)
    csec = cut.add_section(); csec.set_range(0, END)
    try:
        cid = unreal.MovieSceneObjectBindingID(); cid.set_editor_property('guid', cam_b.get_id())
        csec.set_camera_binding_id(cid)
    except Exception as e:
        print('camera cut binding skipped:', e)
    # focal length on the camera component
    focal_ch = None
    try:
        comp = seq.add_possessable(T.A('CAM_Film').get_cine_camera_component())
        comp.set_parent(cam_b)
        ft = comp.add_track(unreal.MovieSceneFloatTrack)
        ft.set_property_name_and_path('CurrentFocalLength', 'CurrentFocalLength')
        fs = ft.add_section(); fs.set_range(0, END)
        focal_ch = fs.get_all_channels()[0]
    except Exception as e:
        print('focal track skipped:', e)

    def key(lb, f, loc, rot):
        ch = binds[lb][1]
        fn = unreal.FrameNumber(f)
        vals = [loc.x, loc.y, loc.z, rot.roll, rot.pitch, rot.yaw]
        for i in range(6):
            ch[i].add_key(fn, vals[i])

    n = 0
    f = 0
    while f <= END:
        t = f / 24.0
        T.apply_time(t)
        fast = (T.T_LIFT - 1.0) < t < (T.T_UP + 2.0) or t < 104.0
        if f % 4 == 0 or fast:
            a = T.A('CAM_Film'); key('CAM_Film', f, a.get_actor_location(), a.get_actor_rotation())
            if focal_ch is not None:
                focal_ch.add_key(unreal.FrameNumber(f), float(T.cam_local(t)[6]))
        if f % 12 == 0 or fast:
            for lb in ['Chaika', 'ChaikaCockpit', 'PilotGloves', 'Svetlyak', 'Wave', 'Wave2']:
                a = T.A(lb); key(lb, f, a.get_actor_location(), a.get_actor_rotation())
            n += 1
        f += 1 if fast else 4
    EAL.save_loaded_asset(seq)
    print('sequence ok: markers', len(T.LINES) + len(ACTS), 'key steps', n)
    return seq
