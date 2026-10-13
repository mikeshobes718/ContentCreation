"""Procedural Blender scenes ("plates") for the Gemini video.

Run headless (Eevee needs a display, so wrap in xvfb-run):
  xvfb-run -a -s "-screen 0 1920x1080x24" blender -b --python blender/plates.py -- <name> <outdir> [--still]

Every plate is 8 s at 24 fps. The video renderer time-stretches a plate when a
scene runs longer, so camera moves are kept slow.
"""
import math
import os
import sys

import bpy

FPS = 24
SECONDS = 5
FRAMES = FPS * SECONDS

GREEN = (0.17, 1.0, 0.53)
BG = (0.006, 0.01, 0.02)


# ----------------------------------------------------------------- setup
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.resolution_x, sc.render.resolution_y = 960, 540
    sc.render.fps = FPS
    sc.frame_start, sc.frame_end = 1, FRAMES
    ee = sc.eevee
    ee.taa_render_samples = 8
    ee.use_bloom = True
    ee.bloom_intensity = 0.08
    ee.bloom_threshold = 0.9
    ee.use_gtao = True
    ee.gtao_distance = 1.2
    ee.use_soft_shadows = False
    ee.shadow_cube_size = "1024"
    ee.shadow_cascade_size = "2048"
    sc.view_settings.view_transform = "Filmic"
    sc.view_settings.look = "Medium High Contrast"
    w = bpy.data.worlds.new("world")
    sc.world = w
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (*BG, 1)
    w.node_tree.nodes["Background"].inputs[1].default_value = 1.0
    return sc


def mat(name, color, rough=0.55, emit=None, strength=0.0, metal=0.0):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit:
        key = "Emission Color" if "Emission Color" in b.inputs else "Emission"
        b.inputs[key].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = strength
    return m


def assign(obj, m):
    obj.data.materials.clear()
    obj.data.materials.append(m)


def smooth(obj):
    for p in obj.data.polygons:
        p.use_smooth = True


def floor(color=(0.02, 0.028, 0.045), rough=0.35, size=200):
    bpy.ops.mesh.primitive_plane_add(size=size)
    f = bpy.context.object
    assign(f, mat("floor", color, rough))
    return f


def camera(loc, look_at, lens=35):
    bpy.ops.object.camera_add(location=loc)
    cam = bpy.context.object
    cam.data.lens = lens
    bpy.ops.object.empty_add(location=look_at)
    tgt = bpy.context.object
    c = cam.constraints.new("TRACK_TO")
    c.target = tgt
    c.track_axis = "TRACK_NEGATIVE_Z"
    c.up_axis = "UP_Y"
    bpy.context.scene.camera = cam
    return cam, tgt


def key(obj, path, frame, value, index=None):
    if index is None:
        setattr(obj, path, value)
        obj.keyframe_insert(path, frame=frame)
    else:
        getattr(obj, path)[index] = value
        obj.keyframe_insert(path, index=index, frame=frame)


def ease_all():
    for a in bpy.data.actions:
        for fc in a.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"
                kp.easing = "EASE_IN_OUT"


def area(loc, energy, size, color=(1, 1, 1), rot=(0, 0, 0)):
    bpy.ops.object.light_add(type="AREA", location=loc, rotation=rot)
    l = bpy.context.object
    l.data.energy = energy
    l.data.size = size
    l.data.color = color
    return l


def spot(loc, target, energy, angle=0.5, color=(1, 1, 1)):
    bpy.ops.object.light_add(type="SPOT", location=loc)
    l = bpy.context.object
    l.data.energy = energy
    l.data.spot_size = angle
    l.data.spot_blend = 0.4
    l.data.color = color
    c = l.constraints.new("TRACK_TO")
    bpy.ops.object.empty_add(location=target)
    c.target = bpy.context.object
    c.track_axis = "TRACK_NEGATIVE_Z"
    c.up_axis = "UP_Y"
    return l


# ----------------------------------------------------------------- mannequin
def person(loc=(0, 0, 0), rot_z=0.0, sit=False, m=None, seg=16, name="person"):
    """Faceless Fern-style mannequin, joined into one smooth mesh. Origin at the feet."""
    parts = []
    def sph(p, s):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=max(6, seg // 2), location=p)
        o = bpy.context.object
        o.scale = s
        parts.append(o)
    def cyl(p, r, d, rot=(0, 0, 0)):
        bpy.ops.mesh.primitive_cylinder_add(vertices=max(8, seg // 2), radius=r, depth=d, location=p, rotation=rot)
        parts.append(bpy.context.object)
    hip = 0.5 if sit else 0.95
    sph((0, 0, hip + 0.42), (0.21, 0.13, 0.33))           # torso
    sph((0, 0, hip + 0.06), (0.17, 0.12, 0.13))           # pelvis
    cyl((0, 0, hip + 0.8), 0.05, 0.1)                     # neck
    sph((0, 0, hip + 0.97), (0.105, 0.115, 0.13))         # head
    for sx in (-1, 1):
        if sit:
            cyl((sx * 0.09, -0.22, hip), 0.065, 0.45, (math.pi / 2, 0, 0))     # thigh forward
            cyl((sx * 0.09, -0.45, hip / 2), 0.055, hip, (0, 0, 0))            # shin down
            cyl((sx * 0.25, -0.15, hip + 0.42), 0.045, 0.5, (math.radians(55), 0, 0))  # arm reaching forward
        else:
            cyl((sx * 0.09, 0, hip / 2), 0.065, hip)                          # leg
            cyl((sx * 0.26, 0, hip + 0.38), 0.045, 0.62, (0, sx * 0.08, 0))   # arm
    for o in parts:
        o.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    bpy.ops.object.join()
    o = bpy.context.object
    o.name = name
    smooth(o)
    o.location = loc
    o.rotation_euler = (0, 0, rot_z)
    if m is not None:
        assign(o, m)
    bpy.ops.object.select_all(action="DESELECT")
    return o


def skin():
    return mat("skin", (0.78, 0.8, 0.84), rough=0.45)


# ================================================================= plates
def plate_vault():
    reset()
    floor((0.015, 0.02, 0.035), rough=0.2)
    core_m = mat("core", (0.05, 0.4, 0.2), emit=GREEN, strength=3.5)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=0.7, location=(0, 0, 1.6))
    core = bpy.context.object
    assign(core, core_m)
    # cage
    bpy.ops.mesh.primitive_cube_add(size=2.6, location=(0, 0, 1.6))
    cage = bpy.context.object
    wf = cage.modifiers.new("wf", "WIREFRAME")
    wf.thickness = 0.03
    assign(cage, mat("cage", (0.3, 0.35, 0.45), rough=0.3, metal=0.8))
    # plinth
    bpy.ops.mesh.primitive_cylinder_add(radius=1.6, depth=0.3, location=(0, 0, 0.15))
    assign(bpy.context.object, mat("plinth", (0.04, 0.05, 0.08), rough=0.4))
    # defenders standing around
    sk = skin()
    for k in range(5):
        a = k / 5 * 2 * math.pi + 0.3
        person((3.2 * math.cos(a), 3.2 * math.sin(a), 0), rot_z=a + math.pi / 2, m=sk)
    bpy.ops.object.light_add(type="POINT", location=(0, 0, 1.6))
    bpy.context.object.data.energy = 250
    bpy.context.object.data.color = GREEN
    area((0, 0, 7), 300, 8, (0.6, 0.7, 1.0))
    cam, tgt = camera((7, -7, 3.2), (0, 0, 1.3), lens=40)
    tgt.location.z = 1.3
    # slow orbit
    for f, ang in ((1, -0.78), (FRAMES, -0.35)):
        cam.location = (9.2 * math.cos(ang), 9.2 * math.sin(ang), 3.0 if f == 1 else 2.4)
        cam.keyframe_insert("location", frame=f)
    key(core, "rotation_euler", 1, 0.0, 2)
    key(core, "rotation_euler", FRAMES, 1.2, 2)
    ease_all()


def plate_eight():
    reset()
    floor((0.03, 0.035, 0.05), rough=0.3)
    sk = skin()
    n = 8
    people = []
    for i in range(n):
        x = (i - (n - 1) / 2) * 1.0
        p = person((x, 0, 0), rot_z=0, m=sk, name=f"author{i}")
        people.append(p)
        l = spot((x, -1.5, 6), (x, 0, 0.8), 900, angle=0.45)
        start = int(FPS * (0.8 + i * 0.75))
        turn = start + int(FPS * 0.6)
        gone = turn + int(FPS * 1.4)
        key(p, "rotation_euler", start, 0.0, 2)
        key(p, "rotation_euler", turn, math.pi, 2)
        key(p, "location", turn, 0.0, 1)
        key(p, "location", gone, 6.0, 1)
        key(l.data, "energy", turn, 900)
        key(l.data, "energy", gone, 40)
    area((0, -6, 4), 120, 10, (0.5, 0.6, 1.0), rot=(math.radians(60), 0, 0))
    cam, tgt = camera((0, -11, 2.6), (0, 0, 1.0), lens=38)
    key(cam, "location", 1, -11.0, 1)
    key(cam, "location", FRAMES, -9.5, 1)
    ease_all()


def desk_row(sk, rows, cols, sx=2.4, sy=2.2, screen_m=None, desk_m=None, sit=True):
    for r in range(rows):
        for c in range(cols):
            x = (c - (cols - 1) / 2) * sx
            y = (r - (rows - 1) / 2) * sy
            bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y - 0.55, 0.74))
            d = bpy.context.object
            d.scale = (1.4, 0.7, 0.04)
            assign(d, desk_m)
            bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y - 0.8, 1.05))
            s = bpy.context.object
            s.scale = (0.6, 0.03, 0.36)
            assign(s, screen_m)
            person((x, y, 0), rot_z=0, sit=sit, m=sk, seg=12)


def plate_codered():
    reset()
    floor((0.03, 0.03, 0.04), rough=0.4)
    sk = skin()
    desk_row(sk, 4, 5, screen_m=mat("screen", (0.1, 0.1, 0.1), emit=(0.85, 0.9, 1.0), strength=3),
             desk_m=mat("desk", (0.12, 0.13, 0.16), rough=0.5))
    red = area((0, 0, 6), 1500, 14, (1.0, 0.08, 0.06))
    for k in range(0, FRAMES + 1, 12):
        key(red.data, "energy", k + 1, 2200 if (k // 12) % 2 == 0 else 300)
    area((-8, -8, 6), 150, 6, (0.5, 0.6, 1.0), rot=(math.radians(50), 0, math.radians(-45)))
    cam, tgt = camera((7, -9, 4), (0, 0, 0.9), lens=32)
    key(cam, "location", 1, 9.0, 0)
    key(cam, "location", FRAMES, 5.0, 0)
    key(cam, "location", 1, 4.0, 2)
    key(cam, "location", FRAMES, 3.2, 2)
    ease_all()


def plate_datacenter():
    reset()
    floor((0.02, 0.025, 0.035), rough=0.15)
    rack_m = bpy.data.materials.new("rack")
    rack_m.use_nodes = True
    nt = rack_m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.03, 0.035, 0.05, 1)
    b.inputs["Roughness"].default_value = 0.35
    brick = nt.nodes.new("ShaderNodeTexBrick")
    brick.inputs["Scale"].default_value = 14
    brick.inputs["Mortar Size"].default_value = 0.035
    brick.inputs["Color1"].default_value = (*GREEN, 1)
    brick.inputs["Color2"].default_value = (0.1, 0.5, 1.0, 1)
    brick.inputs["Mortar"].default_value = (0, 0, 0, 1)
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 40
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.55
    ramp.color_ramp.elements[1].position = 0.6
    mul = nt.nodes.new("ShaderNodeMixRGB")
    mul.blend_type = "MULTIPLY"
    mul.inputs[0].default_value = 1.0
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(brick.outputs["Color"], mul.inputs[1])
    nt.links.new(ramp.outputs["Color"], mul.inputs[2])
    key_in = "Emission Color" if "Emission Color" in b.inputs else "Emission"
    nt.links.new(mul.outputs["Color"], b.inputs[key_in])
    b.inputs["Emission Strength"].default_value = 4.0
    for i in range(-14, 15):
        for side in (-1, 1):
            bpy.ops.mesh.primitive_cube_add(size=1, location=(side * 1.6, i * 1.25, 1.2))
            r = bpy.context.object
            r.scale = (0.9, 1.15, 2.4)
            assign(r, rack_m)
    # ceiling light strips
    strip = mat("strip", (1, 1, 1), emit=(0.8, 0.9, 1.0), strength=6)
    for i in range(-14, 15, 2):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(0, i * 1.25, 3.1))
        s = bpy.context.object
        s.scale = (0.6, 0.08, 0.02)
        assign(s, strip)
    area((0, 0, 3.0), 400, 4, (0.6, 0.75, 1.0))
    cam, tgt = camera((0.2, -18, 1.5), (0, 10, 1.3), lens=28)
    key(cam, "location", 1, -18.0, 1)
    key(cam, "location", FRAMES, -11.0, 1)
    key(noise, "inputs", 1, 0.0) if False else None
    # flicker LEDs by sliding the noise
    mp = nt.nodes.new("ShaderNodeMapping")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], noise.inputs["Vector"])
    mp.inputs["Location"].default_value[2] = 0.0
    mp.inputs["Location"].keyframe_insert("default_value", index=2, frame=1)
    mp.inputs["Location"].default_value[2] = 0.6
    mp.inputs["Location"].keyframe_insert("default_value", index=2, frame=FRAMES)
    ease_all()


def crowd(phones=False):
    reset()
    floor((0.02, 0.025, 0.04), rough=0.5, size=400)
    sk = skin()
    p = person((0, 0, 0), m=sk, seg=10)
    nx, ny = 46, 46
    a1 = p.modifiers.new("ax", "ARRAY")
    a1.count = nx
    a1.use_relative_offset = False
    a1.use_constant_offset = True
    a1.constant_offset_displace = (0.95, 0, 0)
    a2 = p.modifiers.new("ay", "ARRAY")
    a2.count = ny
    a2.use_relative_offset = False
    a2.use_constant_offset = True
    a2.constant_offset_displace = (0, 1.05, 0)
    p.location = (-nx * 0.95 / 2, -2, 0)
    if phones:
        glow = mat("phone", (0.1, 0.1, 0.1), emit=GREEN, strength=40)
        bpy.ops.mesh.primitive_cube_add(size=1, location=(0, -0.28, 1.25))
        ph = bpy.context.object
        ph.scale = (0.05, 0.01, 0.09)
        assign(ph, glow)
        for m in (a1, a2):
            mm = ph.modifiers.new(m.name, "ARRAY")
            mm.count = m.count
            mm.use_relative_offset = False
            mm.use_constant_offset = True
            mm.constant_offset_displace = m.constant_offset_displace
        ph.location = (p.location.x, p.location.y - 0.28, 1.25)
    else:
        # a few lit-up people scattered through the crowd
        glow = mat("lit", (0.1, 0.4, 0.2), emit=GREEN, strength=6)
        import random
        rnd = random.Random(5)
        for _ in range(40):
            gx, gy = rnd.randrange(nx), rnd.randrange(ny)
            person((p.location.x + gx * 0.95, p.location.y + gy * 1.05 + 0.01, 0.001), m=glow, seg=10)
    area((0, 20, 30), 20000, 80, (0.7, 0.8, 1.0))
    area((-30, -10, 12), 3000, 20, (0.4, 0.5, 1.0), rot=(math.radians(60), 0, math.radians(-60)))
    return p


def plate_crowd():
    crowd(phones=False)
    cam, tgt = camera((0, -6, 1.7), (0, 4, 1.4), lens=30)
    key(cam, "location", 1, -6.0, 1)
    key(cam, "location", FRAMES, -16.0, 1)
    key(cam, "location", 1, 1.7, 2)
    key(cam, "location", FRAMES, 16.0, 2)
    key(tgt, "location", 1, 4.0, 1)
    key(tgt, "location", FRAMES, 20.0, 1)
    ease_all()


def plate_crowd2():
    crowd(phones=True)
    bpy.context.scene.world.node_tree.nodes["Background"].inputs[1].default_value = 0.4
    for l in [o for o in bpy.data.objects if o.type == "LIGHT"]:
        l.data.energy *= 0.35
    cam, tgt = camera((-14, -4, 9), (0, 18, 0.5), lens=32)
    key(cam, "location", 1, -14.0, 0)
    key(cam, "location", FRAMES, 10.0, 0)
    ease_all()


PLATES = {k[6:]: v for k, v in globals().items() if k.startswith("plate_")}


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    name, outdir = argv[0], argv[1]
    still = "--still" in argv
    PLATES[name]()
    sc = bpy.context.scene
    os.makedirs(outdir, exist_ok=True)
    if still:
        sc.frame_set(int(FRAMES * 0.6))
        sc.render.filepath = os.path.join(outdir, f"{name}_still.png")
        bpy.ops.render.render(write_still=True)
    else:
        sc.render.filepath = os.path.join(outdir, name, "f_")
        sc.render.image_settings.file_format = "PNG"
        bpy.ops.render.render(animation=True)


if __name__ == "__main__":
    main()
