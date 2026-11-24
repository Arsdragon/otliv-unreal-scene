# Scene state by timeline (seconds) + keyframe cameras
import unreal, math, s1u
from s1u import *
EAL = unreal.EditorAssetLibrary
MPC = EAL.load_asset('/Game/Scene1/MPC_Otliv')
IMPACT = 460.0      # 7:40
SPEED = 150.0       # m/s

def wave_x(t):
    return SPEED * (IMPACT - t) * 100.0   # crest X, cm

def water_depth(t):
    # 0.45 m until 4:40, 0.25 m at 5:10, 0.10 m at 6:10, then ~0.05 m
    pts = [(0, 45.0), (280, 45.0), (310, 25.0), (370, 10.0), (440, 5.0), (470, 5.0)]
    for (a, za), (b, zb) in zip(pts, pts[1:]):
        if a <= t <= b: return za + (zb - za) * (t - a) / (b - a)
    return pts[-1][1]

def flow_speed(t):
    return 0.0 if t < 280 else min(60.0, (t - 280) * 1.2)    # cm/s toward +X

def set_mpc_defaults(scal, vec):
    """Sets MPC values on the editor world's collection instance (takes effect at once, the asset is not touched;
    in the film the same parameters are driven by Sequencer)."""
    ML = unreal.MaterialLibrary
    w = world()
    for n, v in scal.items():
        ML.set_scalar_parameter_value(w, MPC, n, float(v))
    for n, v in vec.items():
        ML.set_vector_parameter_value(w, MPC, n, unreal.LinearColor(*v))


def get_mpc(name, vector=False):
    ML = unreal.MaterialLibrary
    return ML.get_vector_parameter_value(world(), MPC, name) if vector else ML.get_scalar_parameter_value(world(), MPC, name)


def state(t, rings=(), sim_time=None):
    wx = wave_x(t)
    find('Wave').set_actor_location(unreal.Vector(wx, 0, 0), False, False)
    z = water_depth(t)
    wr = find('WaterRoot'); wr.set_actor_location(unreal.Vector(0, 0, z), False, False)
    find('PlanarReflection').set_actor_location(unreal.Vector(0, 0, z), False, False)
    st = t if sim_time is None else sim_time
    scal = {'SimTime': st, 'WaveX': wx, 'FlowSpeed': flow_speed(t), 'RippleAmp': 1.0}
    vec = {'Ring%d' % i: (0.0, 0.0, -100.0, 0.0) for i in range(8)}
    for i, r in enumerate(rings[:8]):
        vec['Ring%d' % i] = r
    set_mpc_defaults(scal, vec)
    return wx, z

def camera(label, loc_m, pyr, focal=24.0):
    cam = spawn(unreal.CineCameraActor, label, loc=tuple(v * 100.0 for v in loc_m), rot=pyr, folder='Cameras')
    cc = cam.get_cine_camera_component()
    fb = cc.filmback; fb.sensor_width = 36.0; fb.sensor_height = 20.25; cc.set_editor_property('filmback', fb)
    cc.set_editor_property('current_focal_length', focal)
    fs = cc.focus_settings; fs.focus_method = unreal.CameraFocusMethod.DISABLE; cc.set_editor_property('focus_settings', fs)
    cc.set_editor_property('current_aperture', 16.0)
    return cam

def footsteps(start_m, dir_deg, n, t_now, step=0.72, dt=0.62, amp=1.0, side=0.16):
    """rings for the last n steps walking from start along dir; newest step at start"""
    out = []
    d = math.radians(dir_deg)
    for i in range(n):
        s = -i * step
        lat = side if i % 2 == 0 else -side
        x = start_m[0] + s * math.cos(d) - lat * math.sin(d)
        y = start_m[1] + s * math.sin(d) + lat * math.cos(d)
        out.append((x * 100.0, y * 100.0, t_now - 0.35 - i * dt, amp))
    return out
