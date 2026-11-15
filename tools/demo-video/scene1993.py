"""The establishing shot: an early-90s desk, built in Blender from code (simple boxes, flat Phong-like materials, hard
shadows), the camera pushing in to the CRT, which shows the real capture. Our own scene: generic shapes, no badges.

    Blender -b -P scene1993.py -- --screen DIR --out DIR [--night] [--frames 210] [--res 640x360] [--reverse]

DIR (--screen): PNG frames of the capture (dump_frames.py), one per video frame, 1024x768. The wall clock shows the
local time when this runs. --night: the lamp on, the window dark. --reverse: the camera pulls back instead.
"""
import datetime, math, os, sys
import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
def arg(name, default=None):
    return argv[argv.index(name) + 1] if name in argv else default
SCREEN = arg('--screen'); OUT = arg('--out', '/tmp/scene1993'); NIGHT = '--night' in argv; REVERSE = '--reverse' in argv
NF = int(arg('--frames', 210)); RW, RH = (int(v) for v in arg('--res', '960x540').split('x'))

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene


def mat(name, rgb, rough=0.45, spec=0.5, emit=None, strength=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*rgb, 1)
    b.inputs['Roughness'].default_value = rough
    for k in ('Specular IOR Level', 'Specular'):
        if k in b.inputs: b.inputs[k].default_value = spec
    if emit is not None:
        b.inputs['Emission Color'].default_value = (*emit, 1)
        b.inputs['Emission Strength'].default_value = strength
    return m


def box(name, x0, x1, y0, y1, z0, z1, m):
    bpy.ops.mesh.primitive_cube_add(location=((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    o = bpy.context.object
    o.name = name
    o.scale = ((x1 - x0) / 2, (y1 - y0) / 2, (z1 - z0) / 2)
    o.data.materials.append(m)
    return o


def cyl(name, x, y, z, r, d, m, rot=(0, 0, 0), verts=24):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=d, location=(x, y, z), rotation=rot)
    o = bpy.context.object; o.name = name; o.data.materials.append(m)
    return o


BEIGE = mat('beige', (0.62, 0.58, 0.48), 0.35)
BEIGE_D = mat('beige_dark', (0.42, 0.39, 0.32), 0.4)
DARK = mat('dark', (0.03, 0.03, 0.035), 0.3)
WALL = mat('wall', (0.55, 0.52, 0.47), 0.8, 0.2)
WOOD = mat('wood', (0.30, 0.13, 0.04), 0.25, 0.7)
FLOOR = mat('floor', (0.18, 0.16, 0.15), 0.7)
WHITE = mat('white', (0.8, 0.8, 0.78), 0.4)
PAPER = mat('paper', (0.85, 0.84, 0.8), 0.7, 0.2)
YELLOW = mat('sticky', (0.9, 0.85, 0.15), 0.7, 0.2)
ORANGE = mat('pencil', (0.85, 0.35, 0.05), 0.4)
PURPLE = mat('purple', (0.25, 0.05, 0.6), 0.5)
SHADE = mat('shade', (0.55, 0.1, 0.75), 0.3, 0.6, emit=(1.0, 0.6, 1.0) if NIGHT else None, strength=2.0)
GREEN_LED = mat('led', (0.0, 0.5, 0.0), 0.3, emit=(0.1, 1.0, 0.1), strength=4.0)
SKY = mat('sky', (0, 0, 0), 1.0, 0.0, emit=(0.02, 0.03, 0.09) if NIGHT else (0.85, 0.92, 1.0), strength=1.0 if NIGHT else 6.0)

# the room: floor, a wall with a window opening (x -1.5..-0.35, z 1.15..2.05), the sky behind it
box('floor', -4, 4, -4, 2, -0.02, 0, FLOOR)
WY = 0.95
box('wall_l', -4, -1.5, WY, WY + 0.1, 0, 3, WALL)
box('wall_r', -0.35, 4, WY, WY + 0.1, 0, 3, WALL)
box('wall_b', -1.5, -0.35, WY, WY + 0.1, 0, 1.15, WALL)
box('wall_t', -1.5, -0.35, WY, WY + 0.1, 2.05, 3, WALL)
box('sky', -3, 1.5, WY + 1.6, WY + 1.62, 0, 3.5, SKY)
for k in range(15):   # blinds, tilted, letting light through in stripes
    z = 1.17 + k * 0.059
    o = box(f'slat{k}', -1.52, -0.33, WY - 0.04, WY - 0.01, z, z + 0.004, WHITE)
    o.rotation_euler = (math.radians(35), 0, 0)
box('sill', -1.55, -0.3, WY - 0.08, WY + 0.02, 1.12, 1.15, WHITE)
# the desk
box('desk', -1.0, 1.0, -0.05, 0.9, 0.72, 0.76, WOOD)
# the computer: a desktop case under a CRT; blank badge, drive slots, a power LED
box('case', -0.26, 0.26, 0.32, 0.82, 0.76, 0.92, BEIGE)
box('bay1', -0.2, 0.0, 0.315, 0.322, 0.86, 0.875, BEIGE_D)
box('bay2', -0.2, 0.0, 0.315, 0.322, 0.83, 0.845, BEIGE_D)
box('slot', -0.18, -0.02, 0.312, 0.316, 0.865, 0.869, DARK)
box('badge', 0.08, 0.2, 0.316, 0.322, 0.885, 0.9, BEIGE_D)
box('led', 0.17, 0.185, 0.314, 0.32, 0.79, 0.8, GREEN_LED)
box('button', 0.08, 0.13, 0.314, 0.322, 0.785, 0.805, BEIGE_D)
box('mon_body', -0.17, 0.17, 0.5, 0.8, 0.95, 1.24, BEIGE)
# the monitor's front: a bezel with a 4:3 opening; the glass sits in the opening, convex (bulging towards the viewer),
# its edges tucked behind the bezel, its centre just reaching the bezel's front face
BZ0, BZ1 = 0.425, 0.5                      # bezel front and back (y)
SX, SZ, OW, OH = 0.0, 1.10, 0.300, 0.225   # opening centre and size
box('bez_l', -0.215, SX - OW / 2, BZ0, BZ1, 0.93, 1.27, BEIGE)
box('bez_r', SX + OW / 2, 0.215, BZ0, BZ1, 0.93, 1.27, BEIGE)
box('bez_b', SX - OW / 2, SX + OW / 2, BZ0, BZ1, 0.93, SZ - OH / 2, BEIGE)
box('bez_t', SX - OW / 2, SX + OW / 2, BZ0, BZ1, SZ + OH / 2, 1.27, BEIGE)
# the opening's inner walls (a dark recess, so the tube's sides read)
box('recess_l', SX - OW / 2 - 0.002, SX - OW / 2, BZ0, BZ0 + 0.03, SZ - OH / 2, SZ + OH / 2, DARK)
box('recess_r', SX + OW / 2, SX + OW / 2 + 0.002, BZ0, BZ0 + 0.03, SZ - OH / 2, SZ + OH / 2, DARK)
box('recess_b', SX - OW / 2, SX + OW / 2, BZ0, BZ0 + 0.03, SZ - OH / 2 - 0.002, SZ - OH / 2, DARK)
box('recess_t', SX - OW / 2, SX + OW / 2, BZ0, BZ0 + 0.03, SZ + OH / 2, SZ + OH / 2 + 0.002, DARK)
box('mon_stand', -0.08, 0.08, 0.5, 0.7, 0.92, 0.95, BEIGE_D)
box('mon_button', 0.16, 0.19, BZ0 - 0.004, BZ0, 0.945, 0.955, BEIGE_D)
# the glass: built in world coordinates. GW x GH (a little larger than the opening, so the bezel overlaps its edges),
# its rim at y = GY (behind the bezel's front), its centre bulging BULGE towards the camera (-y)
GW, GH, GY, BULGE, N = 0.304, 0.228, BZ0 + 0.018, 0.016, 32
verts, faces, uvs, vig = [], [], [], []
for j in range(N + 1):
    for i in range(N + 1):
        u, v = i / N, j / N
        x = SX + (u - 0.5) * GW; z = SZ + (v - 0.5) * GH
        f = (1 - (2 * u - 1) ** 2) * (1 - (2 * v - 1) ** 2)          # 1 at the centre, 0 on the rim
        verts.append((x, GY - BULGE * f, z))
        r2 = ((2 * u - 1) ** 2 + (2 * v - 1) ** 2) / 2
        vig.append(1.0 - 0.45 * r2 ** 1.5)                             # the tube's darker corners
for j in range(N):
    for i in range(N):
        a = j * (N + 1) + i
        faces.append((a, a + 1, a + N + 2, a + N + 1))                 # wound so the normal faces the camera
me = bpy.data.meshes.new('glass'); me.from_pydata(verts, [], faces); me.update()
uvl = me.uv_layers.new(name='UVMap')
col = me.color_attributes.new(name='vig', type='FLOAT_COLOR', domain='POINT')
for k, c in enumerate(vig): col.data[k].color = (c, c, c, 1)
for poly in me.polygons:
    for li in poly.loop_indices:
        vi = me.loops[li].vertex_index
        uvl.data[li].uv = ((vi % (N + 1)) / N, (vi // (N + 1)) / N)
scr = bpy.data.objects.new('screen', me); sc.collection.objects.link(scr)
sm = bpy.data.materials.new('screen'); sm.use_nodes = True
nt = sm.node_tree; nodes = nt.nodes
bsdf = nodes['Principled BSDF']
bsdf.inputs['Base Color'].default_value = (0.0, 0.0, 0.0, 1)
bsdf.inputs['Roughness'].default_value = 0.06                          # glossy glass: the room reflects in it
for k in ('Specular IOR Level', 'Specular'):
    if k in bsdf.inputs: bsdf.inputs[k].default_value = 0.7
if SCREEN:
    files = sorted(f for f in os.listdir(SCREEN) if f.endswith('.png'))
    img = bpy.data.images.load(os.path.join(SCREEN, files[0]))
    img.source = 'SEQUENCE'
    tex = nodes.new('ShaderNodeTexImage'); tex.image = img
    tex.image_user.frame_duration = len(files); tex.image_user.frame_start = 1; tex.image_user.use_auto_refresh = True
    tex.interpolation = 'Closest'
    uvn = nodes.new('ShaderNodeUVMap'); uvn.uv_map = 'UVMap'
    nt.links.new(uvn.outputs['UV'], tex.inputs['Vector'])
    va = nodes.new('ShaderNodeVertexColor'); va.layer_name = 'vig'
    mul = nodes.new('ShaderNodeMixRGB'); mul.blend_type = 'MULTIPLY'; mul.inputs['Fac'].default_value = 1.0
    nt.links.new(tex.outputs['Color'], mul.inputs['Color1']); nt.links.new(va.outputs['Color'], mul.inputs['Color2'])
    nt.links.new(mul.outputs['Color'], bsdf.inputs['Emission Color'])
    bsdf.inputs['Emission Strength'].default_value = 0.6 if NIGHT else 0.85
scr.data.materials.append(sm)
# a 101-key keyboard (keyboard101.py): a case tilted a little, each cap a box whose top shows its own part of the
# legend texture (kbd_texture.py), beige alphanumerics, darker modifiers
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keyboard101 import keys as kb_keys, WIDTH as KW, DEPTH as KD
KU = 0.0195                                   # one key unit
KX0, KY_BACK, KZ = -KW * KU / 2, 0.06 + KD * KU + 0.02, 0.79
box('kbd', KX0 - 0.012, -KX0 + 0.012, 0.045, KY_BACK + 0.012, 0.76, KZ, BEIGE)
KT = mat('keytops', (1, 1, 1), 0.4)
kimg_path = arg('--kbd', os.path.join(os.path.dirname(SCREEN or '.'), 'kbd.png'))
if os.path.exists(kimg_path):
    kt = KT.node_tree.nodes; kb = kt['Principled BSDF']
    ktex = kt.new('ShaderNodeTexImage'); ktex.image = bpy.data.images.load(kimg_path)
    KT.node_tree.links.new(ktex.outputs['Color'], kb.inputs['Base Color'])
for (x, y, w, h, leg, dark) in kb_keys():
    x0 = KX0 + x * KU + 0.0012; x1 = KX0 + (x + w) * KU - 0.0012
    y1 = KY_BACK - y * KU - 0.0012; y0 = KY_BACK - (y + h) * KU + 0.0012
    tilt = (KD - y - h / 2) * KU * 0.12                                 # the back rows sit a little higher
    o = box(f'key_{x}_{y}', x0, x1, y0, y1, KZ, KZ + 0.008 + tilt, BEIGE_D if dark else BEIGE)
    o.data.materials.append(KT)
    # the top face gets the legend texture, mapped from the keyboard's plan
    for poly in o.data.polygons:
        if poly.normal.z > 0.9:
            poly.material_index = 1
    uvl = o.data.uv_layers.active
    for poly in o.data.polygons:
        for li in poly.loop_indices:
            vco = o.data.vertices[o.data.loops[li].vertex_index].co
            wx = o.location.x + vco.x * o.scale.x; wy = o.location.y + vco.y * o.scale.y
            uvl.data[li].uv = ((wx - KX0) / (KW * KU), (wy - (KY_BACK - KD * KU)) / (KD * KU))
box('pad', 0.34, 0.56, 0.08, 0.28, 0.76, 0.763, PURPLE)
box('mouse', 0.42, 0.48, 0.13, 0.22, 0.763, 0.79, BEIGE)
box('notepad', -0.78, -0.46, 0.08, 0.42, 0.76, 0.775, PAPER)
o = cyl('pencil', -0.62, 0.25, 0.782, 0.006, 0.2, ORANGE, rot=(0, math.radians(90), math.radians(35)), verts=6)
box('sticky1', 0.158, 0.208, BZ0 - 0.002, BZ0, 1.215, 1.265, YELLOW).rotation_euler = (0, math.radians(6), 0)
box('sticky2', -0.25, -0.19, 0.316, 0.318, 0.84, 0.9, YELLOW)
# a puzzle cube (generic, no marks): 3x3 stickers on three faces
cols = [(0.8, 0.05, 0.05), (0.05, 0.4, 0.8), (0.9, 0.85, 0.1), (0.1, 0.6, 0.15), (0.95, 0.45, 0.05), (0.9, 0.9, 0.9)]
cm = [mat(f'cube{k}', c, 0.3) for k, c in enumerate(cols)]
cx0, cy0, cz0, s = -0.42, 0.5, 0.76, 0.066
box('cube', cx0, cx0 + s, cy0, cy0 + s, cz0, cz0 + s, DARK)
k = 0
for i in range(3):
    for j in range(3):
        a, b = cx0 + 0.003 + i * s / 3, cz0 + 0.003 + j * s / 3
        box(f'st_f{i}{j}', a, a + s / 3 - 0.004, cy0 - 0.002, cy0, b, b + s / 3 - 0.004, cm[(i + 2 * j) % 6])
        a2 = cy0 + 0.003 + i * s / 3
        box(f'st_t{i}{j}', cx0 + 0.003 + j * s / 3, cx0 + j * s / 3 + s / 3 - 0.001, a2, a2 + s / 3 - 0.004, cz0 + s, cz0 + s + 0.002, cm[(i * 2 + j + 1) % 6])
# an instant camera (generic)
box('cam', -0.7, -0.56, 0.55, 0.66, 0.76, 0.87, mat('camgrey', (0.12, 0.12, 0.13), 0.4))
cyl('lens', -0.63, 0.545, 0.81, 0.028, 0.02, DARK, rot=(math.radians(90), 0, 0))
box('flash', -0.69, -0.65, 0.547, 0.552, 0.845, 0.865, WHITE)
# the desk lamp
cyl('lampbase', 0.6, 0.55, 0.77, 0.07, 0.02, DARK)
cyl('lamparm', 0.6, 0.55, 0.92, 0.008, 0.3, DARK)
bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=0.09, radius2=0.04, depth=0.12, location=(0.6, 0.5, 1.07), rotation=(math.radians(-20), 0, 0))
bpy.context.object.data.materials.append(SHADE)
# the wall clock, at the local time now
now = datetime.datetime.now()
cyl('clock', 0.75, WY - 0.02, 1.9, 0.16, 0.03, WHITE, rot=(math.radians(90), 0, 0), verts=48)
cyl('rim', 0.75, WY - 0.015, 1.9, 0.172, 0.025, DARK, rot=(math.radians(90), 0, 0), verts=48)
for h in range(12):
    a = math.radians(h * 30)
    o = box(f'tick{h}', -0.005, 0.005, -0.002, 0.002, 0.125, 0.15, DARK)
    o.location = (0.75, WY - 0.037, 1.9); o.rotation_euler = (0, a, 0)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
for name, ang, ln, w in (('hour', (now.hour % 12 + now.minute / 60) * 30, 0.08, 0.008), ('minute', (now.minute + now.second / 60) * 6, 0.125, 0.005)):
    bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
    o = bpy.context.object; o.name = name
    o.scale = (w / 2, 0.002, ln / 2)
    bpy.ops.object.transform_apply(scale=True)
    for v in o.data.vertices: v.co.z += ln / 2
    o.location = (0.75, WY - 0.04, 1.9); o.rotation_euler = (0, math.radians(ang), 0)
    o.data.materials.append(DARK)
box('outlet', 0.72, 0.8, WY - 0.005, WY, 0.9, 1.0, WHITE)

# light: the sun through the blinds (hard shadows), sky fill, the lamp
world = bpy.data.worlds.new('w'); sc.world = world; world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.02, 0.02, 0.04, 1) if NIGHT else (0.32, 0.34, 0.38, 1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.3 if NIGHT else 0.9
if not NIGHT:
    bpy.ops.object.light_add(type='SUN', rotation=(math.radians(36), 0, math.radians(200)))
    sun = bpy.context.object; sun.data.energy = 6.0; sun.data.angle = math.radians(0.5)
bpy.ops.object.light_add(type='POINT', location=(0.6, 0.48, 1.03))
lamp = bpy.context.object; lamp.data.energy = 45 if NIGHT else 4; lamp.data.color = (1.0, 0.75, 0.45); lamp.data.shadow_soft_size = 0.01
bpy.ops.object.light_add(type='AREA', location=(0, 0.3, 1.1), rotation=(math.radians(90), 0, 0))
glow = bpy.context.object; glow.data.energy = 0.6 if NIGHT else 0.1; glow.data.size = 0.3; glow.data.color = (0.6, 0.8, 1.0)

# the camera: a slow push from the room to the glass
bpy.ops.object.camera_add()
cam = bpy.context.object; sc.camera = cam
cam.data.lens = 35
target = bpy.data.objects.new('target', None); sc.collection.objects.link(target)
tr = cam.constraints.new('TRACK_TO'); tr.target = target; tr.track_axis = 'TRACK_NEGATIVE_Z'; tr.up_axis = 'UP_Y'
A = ((-0.95, -1.55, 1.62), (-0.25, 0.55, 1.0)); B = ((0.0, -0.10, 1.10), (0.0, 0.42, 1.10))
if REVERSE: A, B = B, A
MID = ((-0.03, -0.30, 0.99), (0.0, 0.26, 0.83))   # past the keyboard on the way in (its legends read here)
keys_ = ((1, A), (int(NF * 0.55), MID), (NF, B)) if not REVERSE else ((1, A), (NF, B))
for f, (p, t) in keys_:
    cam.location = p; cam.keyframe_insert('location', frame=f)
    target.location = t; target.keyframe_insert('location', frame=f)

sc.frame_start, sc.frame_end = 1, NF
sc.render.fps = 30
sc.render.resolution_x, sc.render.resolution_y = RW, RH
sc.render.resolution_percentage = 100
for eng in ('BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT'):
    try:
        sc.render.engine = eng; break
    except TypeError:
        continue
try:
    sc.eevee.taa_render_samples = 16
    sc.eevee.use_shadows = True
    sc.eevee.use_raytracing = True
except AttributeError:
    pass
sc.view_settings.view_transform = 'Standard'
sc.render.image_settings.file_format = 'PNG'
sc.render.filepath = os.path.join(OUT, '')
bpy.ops.render.render(animation=True)
