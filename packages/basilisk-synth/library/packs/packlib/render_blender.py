"""Blender (4.2, headless) renders for one pack. Run by make_packs.py:

    blender -b --factory-startup -P render_blender.py -- job.json

job.json: type (bigbox | jewel | dvd | mailer), mm [w, h, d], tex (folder with front.png back.png spine.png
spine2.png top.png sticker.png inlay_front.png inlay_tray.png label.png [obi.png]), out_box, out_disc, disc_base,
disc_style (silk | cdr | full), obi.

Box: the package with its printed faces, inside a shrink-wrap film (a thin glossy shell with wrinkles from
stretched noise in its bump and roughness), a price sticker on top of the film, on a shadow-catcher floor
(transparent PNG). Disc: the disc, printed side up, lying on its jewel-case inlay and tray card."""
import json
import math
import os
import sys

import bpy
from mathutils import Vector

job = json.load(open(sys.argv[sys.argv.index('--') + 1]))
TEX = job['tex']
MM = 0.001 * 10          # scene unit: 1 = 100 mm


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = int(os.environ.get('PACK_SAMPLES', '96'))
    sc.cycles.use_denoising = True
    sc.render.film_transparent = True
    sc.view_settings.view_transform = 'Standard'
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGBA'
    sc.render.threads_mode = 'AUTO'
    w = bpy.data.worlds.new('w')
    sc.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes['Background']
    bg.inputs[0].default_value = (0.9, 0.92, 0.95, 1)
    bg.inputs[1].default_value = 0.35
    return sc


def img(name):
    p = os.path.join(TEX, name)
    im = bpy.data.images.load(p)
    im.colorspace_settings.name = 'sRGB'
    return im


def mat_image(name, rough=0.55, alpha=False, interp='Closest'):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes['Principled BSDF']
    t = nt.nodes.new('ShaderNodeTexImage')
    t.image = img(name)
    t.interpolation = interp       # printed pixels stay square: no smoothing of the art
    nt.links.new(t.outputs['Color'], b.inputs['Base Color'])
    if alpha:
        nt.links.new(t.outputs['Alpha'], b.inputs['Alpha'])
    b.inputs['Roughness'].default_value = rough
    return m


def mat_color(name, rgba, rough=0.5, metal=0.0, alpha=1.0, transmission=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = rgba
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    b.inputs['Alpha'].default_value = alpha
    b.inputs['Transmission Weight'].default_value = transmission
    return m


def hexc(h, a=1.0):
    h = h.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    c = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return (*c, a)


def cuboid(name, w, h, d, mats, center=(0, 0, 0)):
    """A box w (x) by d (y, depth) by h (z) with one material per face and full-face UVs.
    mats: dict front back left right top bottom -> material. Front faces -y."""
    import bmesh
    me = bpy.data.meshes.new(name)
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    bm = bmesh.new()
    x0, x1, y0, y1, z0, z1 = -w / 2, w / 2, -d / 2, d / 2, -h / 2, h / 2
    V = lambda x, y, z: bm.verts.new((x + center[0], y + center[1], z + center[2]))
    faces = {  # corner order: bottom-left, bottom-right, top-right, top-left as seen from outside
        'front': [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)],
        'back': [(x1, y1, z0), (x0, y1, z0), (x0, y1, z1), (x1, y1, z1)],
        'left': [(x0, y1, z0), (x0, y0, z0), (x0, y0, z1), (x0, y1, z1)],
        'right': [(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)],
        'top': [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)],
        'bottom': [(x0, y1, z0), (x1, y1, z0), (x1, y0, z0), (x0, y0, z0)],
    }
    order = list(faces)
    for k in order:
        ob.data.materials.append(mats.get(k) or mats['default'])
    uv = bm.loops.layers.uv.new()
    for i, k in enumerate(order):
        f = bm.faces.new([V(*c) for c in faces[k]])
        f.material_index = i
        for loop, co in zip(f.loops, [(0, 0), (1, 0), (1, 1), (0, 1)]):
            loop[uv].uv = co
    bm.to_mesh(me)
    bm.free()
    return ob


def wrap_film(w, h, d, center=(0, 0, 0), seed=1):
    """The shrink-wrap: a slightly bigger shell, subdivided and displaced a little, with a film shader:
    mostly transparent, a glossy layer whose strength follows the viewing angle, and wrinkles as bump."""
    ob = cuboid('wrap', w * 1.006, h * 1.006, d * 1.03, {'default': None}, center)
    ob.data.materials.clear()
    m = bpy.data.materials.new('film')
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    gl = nt.nodes.new('ShaderNodeBsdfGlossy')
    mix = nt.nodes.new('ShaderNodeMixShader')
    lw = nt.nodes.new('ShaderNodeLayerWeight')
    lw.inputs['Blend'].default_value = 0.25
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mp = nt.nodes.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (3.0, 3.0, 14.0)      # stretched: wrinkles run along the box
    mp.inputs['Rotation'].default_value = (0.3, 0.2, 0.15 * seed)
    nz = nt.nodes.new('ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = 2.6
    nz.inputs['Detail'].default_value = 8.0
    nz.inputs['Roughness'].default_value = 0.65
    bump = nt.nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = 0.22
    bump.inputs['Distance'].default_value = 0.02
    ramp = nt.nodes.new('ShaderNodeMapRange')
    ramp.inputs['To Min'].default_value = 0.02
    ramp.inputs['To Max'].default_value = 0.18
    add = nt.nodes.new('ShaderNodeMath')
    add.operation = 'MULTIPLY_ADD'
    add.inputs[1].default_value = 0.8
    add.inputs[2].default_value = 0.035
    L = nt.links.new
    L(tc.outputs['Object'], mp.inputs['Vector'])
    L(mp.outputs['Vector'], nz.inputs['Vector'])
    L(nz.outputs['Fac'], bump.inputs['Height'])
    L(nz.outputs['Fac'], ramp.inputs['Value'])
    L(ramp.outputs['Result'], gl.inputs['Roughness'])
    L(bump.outputs['Normal'], gl.inputs['Normal'])
    L(bump.outputs['Normal'], lw.inputs['Normal'])
    L(lw.outputs['Facing'], add.inputs[0])
    L(add.outputs['Value'], mix.inputs['Fac'])
    L(tr.outputs[0], mix.inputs[1])
    L(gl.outputs[0], mix.inputs[2])
    L(mix.outputs[0], out.inputs['Surface'])
    ob.data.materials.append(m)
    # a little geometry: subdivide and push the faces in and out (the film is never flat)
    bpy.context.view_layer.objects.active = ob
    sub = ob.modifiers.new('sub', 'SUBSURF')
    sub.subdivision_type = 'SIMPLE'
    sub.levels = sub.render_levels = 5
    tex = bpy.data.textures.new('wr', 'CLOUDS')
    tex.noise_scale = 0.35
    dsp = ob.modifiers.new('dsp', 'DISPLACE')
    dsp.texture = tex
    dsp.strength = 0.004
    dsp.mid_level = 0.5
    ob.visible_shadow = False
    return ob


def sticker(pos, size, rot=0):
    """Price sticker plane on top of the film. pos in scene units on the front plane (x, y, z)."""
    bpy.ops.mesh.primitive_plane_add(size=1, location=pos)
    ob = bpy.context.active_object
    ob.scale = (size[0], size[1], 1)
    ob.rotation_euler = (math.radians(90), 0, math.radians(rot))
    ob.rotation_euler[1] = 0
    m = mat_image('sticker.png', rough=0.25, alpha=True, interp='Linear')
    ob.data.materials.append(m)
    ob.rotation_mode = 'XYZ'
    ob.rotation_euler = (math.radians(90), math.radians(rot), 0)
    return ob


def floor():
    bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, 0))
    f = bpy.context.active_object
    f.is_shadow_catcher = True
    return f


def lights(target):
    def area(name, loc, energy, size, color=(1, 1, 1)):
        d = bpy.data.lights.new(name, 'AREA')
        d.energy = energy
        d.size = size
        d.color = color
        o = bpy.data.objects.new(name, d)
        o.location = loc
        bpy.context.collection.objects.link(o)
        dirv = Vector(target) - Vector(loc)
        o.rotation_euler = dirv.to_track_quat('-Z', 'Y').to_euler()
    k = float(os.environ.get('PACK_LIGHT', '1.0'))
    area('key', (-6, -7, 8), 260 * k, 5)
    area('fill', (7, -5, 3), 70 * k, 6, (0.92, 0.95, 1))
    area('rim', (2, 6, 7), 160 * k, 3)
    area('glint', (3, -9, 4.5), 220 * k, 1.2)     # a hard, small source for the film's highlight streak     # a hard, small source for the film's highlight streak


def camera(target, dist, elev, azim, lens=70):
    cam = bpy.data.cameras.new('cam')
    cam.lens = lens
    o = bpy.data.objects.new('cam', cam)
    bpy.context.collection.objects.link(o)
    t = Vector(target)
    a, e = math.radians(azim), math.radians(elev)
    o.location = t + Vector((dist * math.sin(a) * math.cos(e), -dist * math.cos(a) * math.cos(e), dist * math.sin(e)))
    o.rotation_euler = (t - o.location).to_track_quat('-Z', 'Y').to_euler()
    bpy.context.scene.camera = o
    return o


def render(path, rx, ry):
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = rx, ry
    sc.render.resolution_percentage = 100
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


# ------------------------------------------------------------------------------------------------ the box

def box_scene():
    reset()
    w, h, d = (v * MM for v in job['mm'])
    t = job['type']
    face = lambda n, r=0.55: mat_image(n, r)
    if t == 'bigbox':
        cuboid('box', w, h, d, {'front': face('front.png', .45), 'back': face('back.png'), 'left': face('spine.png'), 'right': face('spine2.png'),
                                'top': face('top.png'), 'bottom': face('top.png'), 'default': face('top.png')}, (0, 0, h / 2))
        wrap_film(w, h, d, (0, 0, h / 2))
    elif t == 'dvd':
        cuboid('box', w, h, d, {'front': face('front.png', .2), 'back': face('back.png', .2), 'left': face('spine.png', .2),
                                'right': mat_color('case', hexc('#101010'), .3), 'top': mat_color('case2', hexc('#101010'), .3),
                                'bottom': mat_color('case3', hexc('#101010'), .3), 'default': face('top.png')}, (0, 0, h / 2))
        if job.get('obi'):
            ow = 26 * MM
            cuboid('obi', ow, h * 1.0, d * 1.04, {'front': mat_image('obi.png', .5), 'left': mat_image('obi.png', .5), 'back': mat_image('obi.png', .5),
                                                   'default': mat_color('obiw', (1, 1, 1, 1), .5)}, (-w / 2 + ow / 2 - 0.0005, 0, h / 2))
        wrap_film(w, h, d, (0, 0, h / 2), 2)
    elif t == 'jewel':
        # the paper insert behind the clear lid, the tray card's spine on the hinge side, the clear case around it
        cuboid('paper', 120 * MM, 120 * MM, d * 0.7, {'front': face('inlay_front.png', .6), 'left': face('spine.png'), 'back': face('inlay_tray.png'),
                                                     'default': mat_color('tray', hexc('#1a1a1a'), .4)}, (w / 2 - 60 * MM - 1 * MM, 0, h / 2))
        cuboid('hinge', w - 120 * MM - 2 * MM, h * 0.995, d * 0.72, {'default': mat_color('hin', hexc('#202020'), .35)},
               (-w / 2 + (w - 122 * MM) / 2, 0, h / 2))
        case = cuboid('case', w, h, d, {'default': mat_color('plastic', (1, 1, 1, 1), .03, transmission=1.0)}, (0, 0, h / 2))
        for m in case.data.materials:
            m.node_tree.nodes['Principled BSDF'].inputs['IOR'].default_value = 1.05
        wrap_film(w, h, d, (0, 0, h / 2), 3)
    elif t == 'mailer':
        kraft = mat_color('kraft', hexc('#b08a5a'), .85)
        cuboid('mailer', w, h, d, {'default': kraft}, (0, 0, h / 2))
        lw = 112 * MM
        cuboid('label', lw, lw, 0.2 * MM, {'front': face('front.png', .7), 'default': mat_color('lw', (1, 1, 1, 1))}, (0, -d / 2 - 0.1 * MM, h / 2 + 4 * MM))
        # the 3.5" floppy, leaning in front
        fl = cuboid('floppy', 90 * MM, 94 * MM, 3.3 * MM, {'front': face('floppy.png', .3), 'default': mat_color('fpl', hexc('#20304a'), .35)},
                    (0, 0, 47 * MM))
        fl.location = (w * 0.36, -d / 2 - 22 * MM, 0)
        fl.rotation_euler = (math.radians(-11), 0, math.radians(-14))
        wrap_film(w, h, d, (0, 0, h / 2), 4)
    # price sticker on the film, top left of the front
    fw = 120 * MM if t == 'jewel' else 112 * MM if t == 'mailer' else w
    fx0 = (w / 2 - fw - 1 * MM) if t == 'jewel' else -fw / 2
    sp = job.get('sticker_pos') or [0.17, 0.08]
    sx, sz = fx0 + sp[0] * fw, h - sp[1] * (h if t != 'mailer' else 112 * MM) - (0 if t != 'mailer' else 15 * MM)
    sticker((sx, -d / 2 * 1.03 - 0.6 * MM, sz), (40 * MM, 22 * MM), rot=-6)
    floor()
    lights((0, 0, h / 2))
    tall = h > w
    dist = max(w, h) * (3.3 if tall else 3.1)
    camera((0, 0, h / 2 * 0.95), dist, 14, 28, 70)
    if t == 'dvd':
        dist = max(w, h) * 2.9
    rx, ry = (560, 700) if tall else (720, 600)
    render(job['out_box'], rx, ry)


# ------------------------------------------------------------------------------------------------ the disc

def disc_scene():
    reset()
    D = 120 * MM
    # inlay booklet and tray card on the floor
    cuboid('booklet', D, 0.4 * MM, D, {'top': mat_image('inlay_front.png', .6), 'default': mat_color('pw', (1, 1, 1, 1), .6)}, (-0.35 * D, 0.1 * D, 0.2 * MM))
    obs = bpy.context.scene.objects['booklet']
    obs.rotation_euler = (0, 0, math.radians(-8))
    cuboid('tray', 151 * MM, 0.4 * MM, 118 * MM, {'top': mat_image('inlay_tray.png', .6), 'default': mat_color('pw2', (1, 1, 1, 1), .6)}, (0.55 * D, 0.25 * D, 0.75 * MM))
    bpy.context.scene.objects['tray'].rotation_euler = (0, 0, math.radians(6))
    # the disc: a ring mesh (outer 60 mm, hole 7.5 mm), UVs from x/y so the label lands as printed
    import bmesh
    me = bpy.data.meshes.new('disc')
    dob = bpy.data.objects.new('disc', me)
    bpy.context.collection.objects.link(dob)
    bm = bmesh.new()
    N = 160
    R0, R1 = 60 * MM, 7.5 * MM
    zt = 2.6 * MM
    outer = [bm.verts.new((R0 * math.cos(2 * math.pi * i / N), R0 * math.sin(2 * math.pi * i / N), zt)) for i in range(N)]
    inner = [bm.verts.new((R1 * math.cos(2 * math.pi * i / N), R1 * math.sin(2 * math.pi * i / N), zt)) for i in range(N)]
    uv = bm.loops.layers.uv.new()
    for i in range(N):
        j = (i + 1) % N
        f = bm.faces.new([inner[i], outer[i], outer[j], inner[j]])
        for loop in f.loops:
            co = loop.vert.co
            loop[uv].uv = (co.x / (2 * R0) + .5, co.y / (2 * R0) + .5)
    bm.to_mesh(me)
    bm.free()
    sol = dob.modifiers.new('sol', 'SOLIDIFY')
    sol.thickness = 1.2 * MM
    dob.location = (0.05 * D, -0.15 * D, 0)
    m = bpy.data.materials.new('disc')
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes['Principled BSDF']
    metal = nt.nodes.new('ShaderNodeBsdfPrincipled')
    metal.inputs['Base Color'].default_value = hexc(job.get('disc_base', '#d8d8d8'))
    metal.inputs['Metallic'].default_value = 1.0
    metal.inputs['Roughness'].default_value = 0.15
    metal.inputs['Anisotropic'].default_value = 0.6
    t = nt.nodes.new('ShaderNodeTexImage')
    t.image = img('label.png')
    t.interpolation = 'Closest'
    b.inputs['Roughness'].default_value = 0.45
    nt.links.new(t.outputs['Color'], b.inputs['Base Color'])
    mix = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(t.outputs['Alpha'], mix.inputs['Fac'])
    nt.links.new(metal.outputs[0], mix.inputs[1])
    nt.links.new(b.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], nt.nodes['Material Output'].inputs['Surface'])
    dob.data.materials.append(m)
    floor()
    lights((0, 0, 0))
    camera((0.1 * D, 0.02 * D, 0), 4.2 * D, 58, 10, 50)
    render(job['out_disc'], 720, 560)


box_scene()
disc_scene()
