# Key frames of scene 1: scene state + camera for each KF. In the editor:
#   import q_shots; q_shots.setup('KF1')      -> then shoot from camera 'KF1_mirror'
import unreal, math, random, importlib, s1u, l_keys, p_props, f_wave_mesh as fw
importlib.reload(l_keys); importlib.reload(p_props); importlib.reload(fw)
from s1u import *
from l_keys import state, camera, footsteps, wave_x, set_mpc_defaults
EAL = unreal.EditorAssetLibrary
TAN10 = 0.17633
PENUMBRA_M = 12.0     # half-width of the wave shadow edge on the ground (artistic; the physical one is ~320 m)
EYE = (5.20, 0.0, 2.78)          # eye_pilot in ship space, metres
HELMET_CAM = (4.60, 0.0, 2.90)   # wide "helmet camera": 0.6 m behind the eyes so that the gloves on the controls are in frame


def crest(t, y_m):
    """occluding crest point for the 10 deg sun at lateral position y: (x_cm, h_cm)"""
    sc, lean, xo = fw.col_params(y_m)
    return wave_x(t) + (xo - 18.0 * lean) * 100.0, 2097.0 * sc * 100.0


def shadow_edge_x(t, y_m):
    cx, ch = crest(t, y_m)
    return cx - ch / TAN10          # cm


def time_for_edge(x_edge_m, y_m):
    """time when the shadow edge on the ground is at x_edge (m) for lateral y"""
    cx0, ch = crest(0.0, y_m)
    return (cx0 - ch / TAN10 - x_edge_m * 100.0) / 15000.0


def time_for_crest_elevation(deg, cam_m):
    """time when the crest is seen at this elevation from the camera"""
    cx0, ch = crest(0.0, cam_m[1])
    dist = (ch - cam_m[2] * 100.0) / math.tan(math.radians(deg))
    return (cx0 - cam_m[0] * 100.0 - dist) / 15000.0


def apply(t, cam_y_m, rings=(), penumbra_m=PENUMBRA_M):
    wx, z = state(t, rings=rings)
    cx, ch = crest(t, cam_y_m)
    # SunDir carries the light-function data (crest x, crest h, penumbra); WaveX is shifted so that the
    # "glow in shadow" edge of the water material coincides with the light-function edge
    set_mpc_defaults({'WaveX': cx - ch / TAN10 + 1191000.0}, {'SunDir': (cx, ch, penumbra_m * 100.0, 0.0)})
    return wx, z


def hide(label, on=True):
    a = find(label)
    if a:
        a.set_actor_hidden_in_game(on)
        a.set_is_temporarily_hidden_in_editor(on)


def cabin_light(candela, color=(1.0, 0.40, 0.16)):
    """lamps above and behind the pilot: amber = emergency (0 = off)"""
    root = find('ChaikaCockpit')
    for lb, y in [('CabinEmergency_L', -0.36), ('CabinEmergency_R', 0.36)]:
        a = find(lb)
        if a is None:
            a = EAS.spawn_actor_from_class(unreal.PointLight, unreal.Vector(0, 0, 0), R())
            a.set_actor_label(lb); a.set_folder_path('Chaika')
            c = a.point_light_component
            c.set_mobility(unreal.ComponentMobility.MOVABLE)
            c.set_editor_property('intensity_units', unreal.LightUnits.CANDELAS)
            c.set_editor_property('attenuation_radius', 450.0)
            c.set_editor_property('source_radius', 3.0)
            c.set_editor_property('cast_shadows', True)
            c.set_light_color(unreal.LinearColor(1.0, 0.40, 0.16))
            a.attach_to_actor(root, '', unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, False)
        ship_point(a, (4.72, y, 3.20))
        a.point_light_component.set_light_color(unreal.LinearColor(*color))
        a.point_light_component.set_intensity(candela)
        a.point_light_component.set_visibility(candela > 0.0)


def exposure(bias):
    """exposure compensation of the shot (auto exposure stays on)"""
    ppv = find('PPV_Global'); st = ppv.get_editor_property('settings')
    st.set_editor_property('override_auto_exposure_bias', True); st.set_editor_property('auto_exposure_bias', bias)
    ppv.set_editor_property('settings', st)


def tune_cockpit(screens=7.0):
    """brightness of the cockpit screens (imported material instances: re-applied after every re-import)"""
    for i in range(1, 7):
        for p in EAL.list_assets('/Game/Scene1/Chaika/Cockpit', recursive=True):
            if p.endswith('/screen_%d.screen_%d' % (i, i)):
                unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(EAL.load_asset(p), 'EmissiveStrength', screens)


_SHIP = [(0.0, 0.0, 0.0), (0.0, 0.0, 0.0)]


def ship(loc_m=(0, 0, 0), pyr=(0, 0, 0)):
    _SHIP[0], _SHIP[1] = loc_m, pyr
    for lb in ['Chaika', 'ChaikaCockpit', 'PilotGloves']:
        a = find(lb)
        if a:
            a.set_actor_location(unreal.Vector(loc_m[0] * 100.0, loc_m[1] * 100.0, loc_m[2] * 100.0), False, False)
            a.set_actor_rotation(R(pyr[0], pyr[1] - 90.0, pyr[2]), False)


def ship_point(actor, p_m):
    """put an actor at a point given in ship space (ship at rest: world = ship space)"""
    actor.set_actor_location(unreal.Vector((_SHIP[0][0] + p_m[0]) * 100.0, (_SHIP[0][1] + p_m[1]) * 100.0, (_SHIP[0][2] + p_m[2]) * 100.0), False, False)


def flag_ship():
    """custom stencil 1 on everything that belongs to the ship: the underwater post-process leaves it dry"""
    for a in EAS.get_all_level_actors():
        if str(a.get_folder_path()).startswith('Chaika'):
            for c in a.get_components_by_class(unreal.PrimitiveComponent):
                c.set_editor_property('render_custom_depth', True)
                c.set_editor_property('custom_depth_stencil_value', 1)


def underwater(on):
    find('PPV_Underwater').set_editor_property('blend_weight', 1.0 if on else 0.0)
    sun = find('Sun').light_component
    sl = find('SkyLight').get_component_by_class(unreal.SkyLightComponent)
    if on:      # only a dim blue-green fill from the water outside; the cabin is lit by the emergency lamps and screens
        sun.set_editor_property('intensity', 0.0)
        sl.set_editor_property('real_time_capture', False)
        sl.set_editor_property('intensity', 0.0)
    else:
        sun.set_editor_property('intensity', 10.0); sun.set_light_color(unreal.LinearColor(1.0, 1.0, 1.0))
        sl.set_editor_property('real_time_capture', True)
        sl.set_editor_property('intensity', 1.0); sl.set_light_color(unreal.LinearColor(1.0, 1.0, 1.0))


def water_fill(candela):
    """soft blue-green light coming through the canopy from the water (KF5)"""
    a = find('WaterFill')
    if a is None:
        a = EAS.spawn_actor_from_class(unreal.PointLight, unreal.Vector(0, 0, 0), R())
        a.set_actor_label('WaterFill'); a.set_folder_path('Chaika')
        c = a.point_light_component
        c.set_mobility(unreal.ComponentMobility.MOVABLE)
        c.set_editor_property('intensity_units', unreal.LightUnits.CANDELAS)
        c.set_editor_property('attenuation_radius', 900.0)
        c.set_editor_property('source_radius', 60.0)
        c.set_editor_property('cast_shadows', True)
        c.set_light_color(unreal.LinearColor(0.25, 0.80, 0.78))
    ship_point(a, (8.6, 0.6, 5.2))          # ahead of and above the canopy
    a.point_light_component.set_intensity(candela)
    a.point_light_component.set_visibility(candela > 0.0)


def irregular_steps(start_m, dir_deg, n, t_now, seed, step=0.75, dt=0.62, amp=2.0):
    """footstep rings with uneven strength, timing and placement, plus a couple of small splashes"""
    rnd = random.Random(seed)
    out = []
    d = math.radians(dir_deg)
    for i in range(n):
        s = -i * step + rnd.uniform(-0.10, 0.10)
        lat = (0.17 if i % 2 == 0 else -0.17) + rnd.uniform(-0.07, 0.07)
        x = start_m[0] + s * math.cos(d) - lat * math.sin(d)
        y = start_m[1] + s * math.sin(d) + lat * math.cos(d)
        out.append((x * 100.0, y * 100.0, t_now - 0.35 - i * dt + rnd.uniform(-0.22, 0.22), amp * rnd.uniform(0.45, 1.25)))
    for j in range(2):      # drops falling from the boots a little aside
        k = rnd.randrange(0, n)
        out.append((out[k][0] + rnd.uniform(-45, 45), out[k][1] + rnd.uniform(-45, 45), t_now - rnd.uniform(0.3, 1.1), amp * 0.45))
    return out


def quality(n=3):
    """render quality: 3 for shots (Lumen, full textures), 1 for work. The editor starts at 1 (-dpcvars)."""
    w = world()
    for grp in ['ViewDistance', 'AntiAliasing', 'Shadow', 'GlobalIllumination', 'Reflection', 'PostProcess', 'Texture', 'Effects', 'Foliage', 'Shading']:
        unreal.SystemLibrary.execute_console_command(w, 'sg.%sQuality %d' % (grp, n))
    unreal.SystemLibrary.execute_console_command(w, 'r.SSR.Quality 0')          # SSR would override the planar reflection
    unreal.SystemLibrary.execute_console_command(w, 'r.LightFunctionAtlas 0')   # the wave shadow needs world-space light functions


def setup(kf):
    quality(3)
    a = find('CAM_Test')
    if a: EAS.destroy_actor(a)
    EAS.set_selected_level_actors([])
    LES.editor_set_game_view(True)
    underwater(False)
    ship()
    exposure(1.0)       # Unreal's default compensation
    tune_cockpit()
    cabin_light(0.0)
    water_fill(0.0)
    hide('ck_seat', False)
    for lb in ['ext_cockpit_proxy', 'ck_hatch_proxy']:
        hide(lb, True)
    if kf == 'KF1':      # 2:05, look back at the ship; giant above it, drone waits, our steps on the water
        t = 125.0
        cam = (12.5, 9.4, 1.70)
        dr = (10.87, 5.75)
        rings = irregular_steps((9.7, 8.3), 21.0, 5, t - 2.0, seed=7, amp=1.9)
        rings += [(dr[0] * 100.0, dr[1] * 100.0, t - 0.9, 0.7)]
        apply(t, cam[1], rings)
        p_props.place('svetlyak', loc=(dr[0], dr[1], 0.97), yaw=125.0, pose={'sv_head': (0.0, -30.0, 0.0)})
        camera('KF1_mirror', cam, (10.0, 216.0, 0.0), focal=14.0)
    elif kf == 'KF2':    # 3:40, wave 36 km away under the sun: must read as a mountain range
        t = 220.0
        cam = (90.0, 107.0, 1.70)
        apply(t, cam[1], irregular_steps((92.5, 107.8), 50.0, 5, t - 1.5, seed=3, amp=1.6))
        p_props.place('svetlyak', loc=(110.0, 131.0, 1.0), yaw=-40.0)
        camera('KF2_far_wave', cam, (3.5, 0.0, 0.0), focal=40.0)
    elif kf == 'KF3':    # ~6:22: the crest takes the sun; the shadow has just reached us and climbs up the hull (1 m per 5.7 m)
        cam = (-14.0, 9.0, 1.70)
        t = time_for_edge(-9.5, cam[1])
        rings = irregular_steps((-9.3, 7.3), -160.0, 4, t - 0.5, seed=11, step=1.3, dt=0.33, amp=1.3)
        apply(t, cam[1], rings, penumbra_m=1.5)
        p_props.place('svetlyak', loc=(-8.2, 2.6, 1.75), yaw=110.0, pose={'sv_head': (0.0, 20.0, 0.0)})
        camera('KF3_near_wave', cam, (2.5, -13.0, 0.0), focal=16.0)
        print('KF3 time %.1f s (%d:%04.1f), wave %.0f m' % (t, t // 60, t % 60, wave_x(t) / 100.0))
    elif kf == 'KF4':    # ~7:26, cockpit: the wall of water fills the canopy up to +46 deg, a strip of sky above the crest
        cam = HELMET_CAM
        t = time_for_crest_elevation(45.5, cam)
        apply(t, 0.0)
        set_mpc_defaults({'RippleAmp': 4.0}, {})      # the drained water streams toward the wave: broken reflection
        exposure(-1.0)
        cabin_light(0.22, (1.0, 0.86, 0.72))
        hide('ck_seat', True)
        p_props.place('svetlyak', loc=(-1.45, 1.08, 2.705), yaw=-90.0)    # in its cradle (drone_cradle)
        camera('KF4_cockpit', cam, (4.0, 0.0, 0.0), focal=10.5)
        print('KF4 time %.1f s (%d:%04.1f), wave %.0f m' % (t, t // 60, t % 60, wave_x(t) / 100.0))
    elif kf == 'KF5':    # 7:45, under water after the impact: the ship is inside the body of the wave
        t = 465.0
        up = 400.0
        apply(t, 0.0)
        ship((0.0, 0.0, up))
        underwater(True)
        exposure(-1.5)
        cabin_light(0.8)
        water_fill(40.0)
        hide('ck_seat', True)
        p_props.place('svetlyak', loc=(-1.45, 1.08, 2.705 + up), yaw=-90.0)
        camera('KF5_underwater', (HELMET_CAM[0], HELMET_CAM[1], HELMET_CAM[2] + up), (1.0, 0.0, -12.0), focal=10.5)
    flag_ship()
    save()
    # the viewport must redraw continuously, otherwise a screenshot waits for the next forced redraw (autosave, 10 min)
    LES.editor_set_viewport_realtime(True)
    keep_drawing(True)
    return kf


def shoot(camera_label, path, w=1920, h=1080):
    """Request a high-res screenshot from a camera and keep the viewport redrawing (the request alone switches realtime off,
    and the frame is then taken only at the next forced redraw). Call 15-20 s after setup(); the file appears a few seconds later."""
    import os
    cam = find(camera_label)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        os.remove(path)
    unreal.AutomationLibrary.take_high_res_screenshot(w, h, path, camera=cam)
    LES.editor_set_viewport_realtime(True)
    LES.editor_invalidate_viewports()
    return path


def keep_drawing(on=True):
    """The editor in the background does not redraw its viewport by itself, and a high-res screenshot needs several
    consecutive frames (r.HighResScreenshotDelay). While this is on, the viewport is invalidated on every editor tick.
    Switch it off after the shots: it keeps the GPU busy."""
    import builtins
    h = getattr(builtins, '_s1_draw_handle', None)
    if h is not None:
        unreal.unregister_slate_post_tick_callback(h)
        builtins._s1_draw_handle = None
    if on:
        builtins._s1_draw_handle = unreal.register_slate_post_tick_callback(lambda dt: LES.editor_invalidate_viewports())
    return on
