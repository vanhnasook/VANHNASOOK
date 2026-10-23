"""Build "Nong Lanxang" (ນ້ອງ ລ້ານຊ້າງ), the Lanexang Assurance baby-elephant mascot.

Everything is generated procedurally with Blender's Python API, so the same
code works from the command line, from Blender's Scripting tab, or when sent
through a Blender MCP server's "execute code" tool.

    blender --background --python build_mascot.py -- --out nong_lanxang.blend --render renders

or, with the `bpy` module from PyPI:

    python build_mascot.py --out nong_lanxang.blend --render renders

Coordinates: metres-ish units, the character stands on z = 0, is 2 units
tall and faces -Y (Blender's front view). Her right side is -X.
"""
import argparse
import math
import os
import sys
from pathlib import Path

import bpy  # must precede bmesh/mathutils when using the PyPI bpy module
import bmesh
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

try:
    HERE = Path(__file__).resolve().parent
except NameError:  # run from a text block / MCP exec
    HERE = Path(os.getcwd())

HEAD_C = Vector((0.0, 0.0, 1.42))
TORSO_C = Vector((0.0, 0.0, 0.84))

PALETTE = {
    "skin": "#D8D9DE",
    "skin_dark": "#BDBEC5",
    "ear_pink": "#F5C4CA",
    "blush": "#F7A9B4",
    "yellow": "#FFC20E",
    "navy": "#123F86",
    "white": "#F7F7F4",
    "dark": "#2B231F",
    "iris": "#6B3A1E",
    "bow": "#F58BB4",
    "mouth": "#8C2633",
    "tongue": "#F07F8A",
    "backdrop": "#F1F2F5",
}


# --------------------------------------------------------------------------
# scene + generic helpers
# --------------------------------------------------------------------------

def reset_scene():
    """Start clean. Headless runs get a fresh empty file; in a live session (for
    example one driven by a Blender MCP add-on) only what an earlier run of this
    script created is removed, because a factory reset would unload the add-ons."""
    if bpy.app.background:
        bpy.ops.wm.read_factory_settings(use_empty=True)
    else:
        clear_previous_build()


def clear_previous_build():
    for name in ("Nong_LanXang", "Studio"):
        coll = bpy.data.collections.get(name)
        if coll is None:
            continue
        family = [coll, *coll.children_recursive]
        for c in family:
            for obj in list(c.objects):
                bpy.data.objects.remove(obj, do_unlink=True)
        for c in reversed(family):
            bpy.data.collections.remove(c)
    bpy.data.orphans_purge(do_recursive=True)


def srgb(hex_colour, alpha=1.0):
    h = hex_colour.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return (*lin, alpha)


def new_collection(name, parent=None):
    coll = bpy.data.collections.new(name)
    (parent or bpy.context.scene.collection).children.link(coll)
    return coll


def frame(normal, up=Vector((0, 0, 1))):
    """3x3 rotation whose Z axis is `normal` and whose Y axis leans to `up`."""
    z = Vector(normal).normalized()
    x = Vector(up).cross(z)
    if x.length < 1e-6:
        x = Vector((1, 0, 0))
    x.normalize()
    y = z.cross(x)
    return Matrix((x, y, z)).transposed()


def finish_mesh(name, bm, coll, mat=None, matrix=None, subsurf=0, smooth=True):
    me = bpy.data.meshes.new(name)
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    if smooth:
        me.shade_smooth()
    if mat:
        me.materials.append(mat)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    if matrix is not None:
        obj.matrix_world = matrix
    if subsurf:
        mod = obj.modifiers.new("Subdivision", "SUBSURF")
        mod.levels = mod.render_levels = subsurf
    return obj


def ellipsoid(name, coll, mat, center, radii, rot=None, deform=None,
              seg=48, rings=24, subsurf=1, scale_in_object=False):
    """Unit UV sphere, optionally reshaped by `deform(unit_co)`, scaled to radii."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=1.0, calc_uvs=True)
    for v in bm.verts:
        u = v.co.copy()
        if deform:
            u = deform(u)
        v.co = u if scale_in_object else Vector((u.x * radii[0], u.y * radii[1], u.z * radii[2]))
    rot = rot if rot is not None else Matrix.Identity(3)
    m = Matrix.Translation(Vector(center)) @ rot.to_4x4()
    if scale_in_object:
        m = m @ Matrix.Diagonal((*radii, 1.0))
    return finish_mesh(name, bm, coll, mat, m, subsurf)


def tube(name, coll, mat, points, radii, cyclic=False, caps=True, res=16, bevel_res=6):
    """Smooth Bezier tube through `points` with a per-point radius, baked to a mesh."""
    cu = bpy.data.curves.new(name + "_curve", "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = 1.0
    cu.bevel_resolution = bevel_res
    cu.resolution_u = res
    cu.use_fill_caps = caps
    cu.twist_mode = "MINIMUM"
    sp = cu.splines.new("BEZIER")
    sp.bezier_points.add(len(points) - 1)
    for bp, co, r in zip(sp.bezier_points, points, radii):
        bp.co = Vector(co)
        bp.radius = r
        bp.handle_left_type = bp.handle_right_type = "AUTO"
    sp.use_cyclic_u = cyclic
    sp.use_smooth = True
    tmp = bpy.data.objects.new(name + "_tmp", cu)
    coll.objects.link(tmp)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg))
    bpy.data.objects.remove(tmp)
    bpy.data.curves.remove(cu)
    me.name = name
    me.shade_smooth()
    if mat:
        me.materials.append(mat)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    return obj


def bvh_of(obj):
    """BVH of the evaluated mesh, in the object's local space."""
    dg = bpy.context.evaluated_depsgraph_get()
    return BVHTree.FromObject(obj, dg)


def hide_helper(obj):
    obj.hide_render = True
    obj.display_type = "WIRE"
    obj.hide_set(True)


# --------------------------------------------------------------------------
# materials
# --------------------------------------------------------------------------

def _nodes(mat):
    if bpy.app.version < (5, 0, 0):  # node trees are always on from 5.0
        mat.use_nodes = True
    nt = mat.node_tree
    return nt, nt.nodes.get("Principled BSDF")


def principled(name, colour, rough=0.5, **inputs):
    mat = bpy.data.materials.new(name)
    nt, bsdf = _nodes(mat)
    bsdf.inputs["Base Color"].default_value = srgb(colour)
    bsdf.inputs["Roughness"].default_value = rough
    for key, value in inputs.items():
        bsdf.inputs[key.replace("_", " ")].default_value = value
    mat.diffuse_color = srgb(colour)
    return mat


def node(nt, kind, loc, **props):
    n = nt.nodes.new(kind)
    n.location = loc
    for k, v in props.items():
        setattr(n, k, v)
    return n


def sock(sockets, name, kind="RGBA"):
    """Mix nodes carry float/vector/colour sockets that share a name."""
    return next(s for s in sockets if s.name == name and s.type == kind)


def mix_rgba(nt, loc, a=None, b=None, blend="MIX"):
    mix = node(nt, "ShaderNodeMix", loc, data_type="RGBA", blend_type=blend)
    if a is not None:
        sock(mix.inputs, "A").default_value = a
    if b is not None:
        sock(mix.inputs, "B").default_value = b
    return mix, sock(mix.inputs, "A"), sock(mix.inputs, "B"), sock(mix.outputs, "Result")


def add_fabric_bump(nt, bsdf, scale=380.0, strength=0.12):
    tc = node(nt, "ShaderNodeTexCoord", (-1100, -500))
    noise = node(nt, "ShaderNodeTexNoise", (-900, -500))
    noise.inputs["Scale"].default_value = scale
    noise.inputs["Detail"].default_value = 3.0
    bump = node(nt, "ShaderNodeBump", (-500, -500))
    bump.inputs["Strength"].default_value = strength
    bump.inputs["Distance"].default_value = 0.002
    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return bump


def fabric(name, colour, rough=0.78):
    mat = principled(name, colour, rough, Sheen_Weight=0.35, Sheen_Roughness=0.45)
    nt, bsdf = _nodes(mat)
    add_fabric_bump(nt, bsdf)
    return mat


def add_decal(mat, projector, image_path, depth=1.5):
    """Project an RGBA image along the projector empty's Z axis onto `mat`."""
    if not Path(image_path).is_file():
        print(f"warning: decal {image_path} not found, skipping (see --textures)")
        return None
    nt, bsdf = _nodes(mat)
    base = bsdf.inputs["Base Color"]
    base_rgba = tuple(base.default_value)
    tc = node(nt, "ShaderNodeTexCoord", (-1300, 200), object=projector)
    mapping = node(nt, "ShaderNodeMapping", (-1100, 200))
    mapping.inputs["Location"].default_value = (0.5, 0.5, 0.0)
    mapping.inputs["Scale"].default_value = (0.5, 0.5, 1.0)
    tex = node(nt, "ShaderNodeTexImage", (-900, 200), extension="CLIP")
    tex.image = bpy.data.images.load(str(image_path), check_existing=True)
    sep = node(nt, "ShaderNodeSeparateXYZ", (-1100, -50))
    facing = node(nt, "ShaderNodeMath", (-900, -50), operation="GREATER_THAN")
    facing.inputs[1].default_value = -depth
    mask = node(nt, "ShaderNodeMath", (-650, 0), operation="MULTIPLY")
    mix, _, mix_b, mix_out = mix_rgba(nt, (-400, 150), a=base_rgba)
    nt.links.new(tc.outputs["Object"], mapping.inputs["Vector"])
    nt.links.new(mapping.outputs["Vector"], tex.inputs["Vector"])
    nt.links.new(tc.outputs["Object"], sep.inputs["Vector"])
    nt.links.new(sep.outputs["Z"], facing.inputs[0])
    nt.links.new(tex.outputs["Alpha"], mask.inputs[0])
    nt.links.new(facing.outputs["Value"], mask.inputs[1])
    nt.links.new(mask.outputs["Value"], mix.inputs["Factor"])
    nt.links.new(tex.outputs["Color"], mix_b)
    nt.links.new(mix_out, base)
    return mix


def add_cap_seams(mat):
    """Six stitched panel seams converging on the crown (object space of the dome)."""
    nt, bsdf = _nodes(mat)
    tc = node(nt, "ShaderNodeTexCoord", (-1700, -900))
    sep = node(nt, "ShaderNodeSeparateXYZ", (-1500, -900))
    atan = node(nt, "ShaderNodeMath", (-1300, -900), operation="ARCTAN2")
    times = node(nt, "ShaderNodeMath", (-1100, -900), operation="MULTIPLY")
    times.inputs[1].default_value = 3.0
    sine = node(nt, "ShaderNodeMath", (-950, -900), operation="SINE")
    absv = node(nt, "ShaderNodeMath", (-800, -900), operation="ABSOLUTE")
    seam = node(nt, "ShaderNodeMapRange", (-650, -900), interpolation_type="SMOOTHSTEP")
    seam.inputs["From Min"].default_value = 0.0
    seam.inputs["From Max"].default_value = 0.035
    seam.inputs["To Min"].default_value = 1.0
    seam.inputs["To Max"].default_value = 0.0
    nt.links.new(tc.outputs["Object"], sep.inputs["Vector"])
    nt.links.new(sep.outputs["Y"], atan.inputs[0])
    nt.links.new(sep.outputs["X"], atan.inputs[1])
    nt.links.new(atan.outputs["Value"], times.inputs[0])
    nt.links.new(times.outputs["Value"], sine.inputs[0])
    nt.links.new(sine.outputs["Value"], absv.inputs[0])
    nt.links.new(absv.outputs["Value"], seam.inputs["Value"])
    # feed the seam into the existing fabric bump as a groove
    bump = next(n for n in nt.nodes if n.bl_idname == "ShaderNodeBump")
    noise_link = bump.inputs["Height"].links[0]
    noise_out = noise_link.from_socket
    nt.links.remove(noise_link)
    groove = node(nt, "ShaderNodeMath", (-650, -650), operation="MULTIPLY_ADD")
    groove.inputs[1].default_value = 1.0
    neg = node(nt, "ShaderNodeMath", (-500, -900), operation="MULTIPLY")
    neg.inputs[1].default_value = -6.0
    nt.links.new(seam.outputs["Result"], neg.inputs[0])
    nt.links.new(noise_out, groove.inputs[0])
    nt.links.new(neg.outputs["Value"], groove.inputs[2])
    nt.links.new(groove.outputs["Value"], bump.inputs["Height"])


def skin_with_blush(name, cheeks):
    mat = principled(name, PALETTE["skin"], 0.42, Subsurface_Weight=0.12,
                     Subsurface_Scale=0.02, Coat_Weight=0.15, Coat_Roughness=0.3)
    nt, bsdf = _nodes(mat)
    tc = node(nt, "ShaderNodeTexCoord", (-1300, 300))
    fac = None
    for i, c in enumerate(cheeks):
        dist = node(nt, "ShaderNodeVectorMath", (-1100, 300 - i * 200), operation="DISTANCE")
        dist.inputs[1].default_value = c
        rng = node(nt, "ShaderNodeMapRange", (-900, 300 - i * 200), interpolation_type="SMOOTHSTEP")
        rng.inputs["From Min"].default_value = 0.015
        rng.inputs["From Max"].default_value = 0.068
        rng.inputs["To Min"].default_value = 0.85
        rng.inputs["To Max"].default_value = 0.0
        nt.links.new(tc.outputs["Object"], dist.inputs[0])
        nt.links.new(dist.outputs["Value"], rng.inputs["Value"])
        if fac is None:
            fac = rng.outputs["Result"]
        else:
            mx = node(nt, "ShaderNodeMath", (-700, 200), operation="MAXIMUM")
            nt.links.new(fac, mx.inputs[0])
            nt.links.new(rng.outputs["Result"], mx.inputs[1])
            fac = mx.outputs["Value"]
    mix, _, _, mix_out = mix_rgba(nt, (-450, 300), srgb(PALETTE["skin"]), srgb(PALETTE["blush"]))
    nt.links.new(fac, mix.inputs["Factor"])
    nt.links.new(mix_out, bsdf.inputs["Base Color"])
    return mat


def eye_material():
    """Glossy eye: black pupil, brown iris lighter at the bottom, dark rim.
    Expects object coordinates on a unit sphere whose +Z looks out of the face."""
    mat = principled("Eye", PALETTE["dark"], 0.2, Coat_Weight=1.0, Coat_Roughness=0.03)
    nt, bsdf = _nodes(mat)
    tc = node(nt, "ShaderNodeTexCoord", (-1300, 300))
    sep = node(nt, "ShaderNodeSeparateXYZ", (-1100, 300))
    flat = node(nt, "ShaderNodeCombineXYZ", (-950, 300))
    length = node(nt, "ShaderNodeVectorMath", (-800, 300), operation="LENGTH")
    nt.links.new(tc.outputs["Object"], sep.inputs["Vector"])
    nt.links.new(sep.outputs["X"], flat.inputs["X"])
    nt.links.new(sep.outputs["Y"], flat.inputs["Y"])
    nt.links.new(flat.outputs["Vector"], length.inputs[0])
    ramp = node(nt, "ShaderNodeValToRGB", (-600, 300))
    els = ramp.color_ramp.elements
    els[0].position, els[0].color = 0.0, srgb("#120c0a")
    els[1].position, els[1].color = 0.5, srgb("#120c0a")
    for pos, col in ((0.62, "#2e1b11"), (0.82, PALETTE["iris"]), (0.9, "#140d0a")):
        e = els.new(pos)
        e.color = srgb(col)
    nt.links.new(length.outputs["Value"], ramp.inputs["Fac"])
    # brighten the lower half of the iris
    lower = node(nt, "ShaderNodeMapRange", (-800, 0))
    lower.inputs["From Min"].default_value = 0.1
    lower.inputs["From Max"].default_value = -0.8
    lower.inputs["To Min"].default_value = 0.0
    lower.inputs["To Max"].default_value = 0.4
    nt.links.new(sep.outputs["Y"], lower.inputs["Value"])
    iris_band = node(nt, "ShaderNodeMapRange", (-800, -200), interpolation_type="SMOOTHSTEP")
    for k, v in (("From Min", 0.45), ("From Max", 0.6), ("To Min", 0.0), ("To Max", 1.0)):
        iris_band.inputs[k].default_value = v
    nt.links.new(length.outputs["Value"], iris_band.inputs["Value"])
    amt = node(nt, "ShaderNodeMath", (-600, -100), operation="MULTIPLY")
    nt.links.new(lower.outputs["Result"], amt.inputs[0])
    nt.links.new(iris_band.outputs["Result"], amt.inputs[1])
    mix, mix_a, _, mix_out = mix_rgba(nt, (-350, 200), b=srgb("#c98a52"), blend="SCREEN")
    nt.links.new(amt.outputs["Value"], mix.inputs["Factor"])
    nt.links.new(ramp.outputs["Color"], mix_a)
    nt.links.new(mix_out, bsdf.inputs["Base Color"])
    return mat


def emissive(name, colour, strength=2.0):
    return principled(name, colour, 0.2, Emission_Color=srgb(colour), Emission_Strength=strength)


def shoe_upper_material():
    """Yellow canvas with a white rubber toe cap (object space of the shoe)."""
    mat = fabric("Shoe_Canvas", PALETTE["yellow"], 0.7)
    nt, bsdf = _nodes(mat)
    tc = node(nt, "ShaderNodeTexCoord", (-1300, 300))
    mapping = node(nt, "ShaderNodeMapping", (-1100, 300))
    mapping.inputs["Location"].default_value = (0.0, 0.28, -0.03)
    mapping.inputs["Scale"].default_value = (1.0, 1.0, 1.5)
    dist = node(nt, "ShaderNodeVectorMath", (-900, 300), operation="LENGTH")
    rng = node(nt, "ShaderNodeMapRange", (-700, 300), interpolation_type="SMOOTHSTEP")
    for k, v in (("From Min", 0.15), ("From Max", 0.16), ("To Min", 1.0), ("To Max", 0.0)):
        rng.inputs[k].default_value = v
    nt.links.new(tc.outputs["Object"], mapping.inputs["Vector"])
    nt.links.new(mapping.outputs["Vector"], dist.inputs[0])
    nt.links.new(dist.outputs["Value"], rng.inputs["Value"])
    mix, _, _, mix_out = mix_rgba(nt, (-450, 300), srgb(PALETTE["yellow"]), srgb(PALETTE["white"]))
    nt.links.new(rng.outputs["Result"], mix.inputs["Factor"])
    nt.links.new(mix_out, bsdf.inputs["Base Color"])
    rough = node(nt, "ShaderNodeMapRange", (-450, 0))
    rough.inputs["To Min"].default_value = 0.72
    rough.inputs["To Max"].default_value = 0.35
    nt.links.new(rng.outputs["Result"], rough.inputs["Value"])
    nt.links.new(rough.outputs["Result"], bsdf.inputs["Roughness"])
    return mat


def sole_material():
    """White rubber sole with a thin navy foxing stripe."""
    mat = principled("Shoe_Sole", PALETTE["white"], 0.4)
    nt, bsdf = _nodes(mat)
    tc = node(nt, "ShaderNodeTexCoord", (-1100, 300))
    sep = node(nt, "ShaderNodeSeparateXYZ", (-900, 300))
    lo = node(nt, "ShaderNodeMath", (-700, 350), operation="GREATER_THAN")
    lo.inputs[1].default_value = 0.012
    hi = node(nt, "ShaderNodeMath", (-700, 200), operation="LESS_THAN")
    hi.inputs[1].default_value = 0.022
    band = node(nt, "ShaderNodeMath", (-550, 300), operation="MULTIPLY")
    mix, _, _, mix_out = mix_rgba(nt, (-350, 300), srgb(PALETTE["white"]), srgb(PALETTE["navy"]))
    nt.links.new(tc.outputs["Object"], sep.inputs["Vector"])
    nt.links.new(sep.outputs["Z"], lo.inputs[0])
    nt.links.new(sep.outputs["Z"], hi.inputs[0])
    nt.links.new(lo.outputs["Value"], band.inputs[0])
    nt.links.new(hi.outputs["Value"], band.inputs[1])
    nt.links.new(band.outputs["Value"], mix.inputs["Factor"])
    nt.links.new(mix_out, bsdf.inputs["Base Color"])
    return mat


# --------------------------------------------------------------------------
# the character
# --------------------------------------------------------------------------

class Mascot:
    def __init__(self, textures):
        self.textures = Path(textures)
        self.root_coll = new_collection("Nong_LanXang")
        self.colls = {n: new_collection(n, self.root_coll) for n in
                      ("Head", "Face", "Cap", "Body", "Limbs", "Shoes", "Helpers")}
        m = {}
        m["skin"] = principled("Skin", PALETTE["skin"], 0.42, Subsurface_Weight=0.12,
                               Subsurface_Scale=0.02, Coat_Weight=0.15, Coat_Roughness=0.3)
        m["ear_pink"] = principled("Ear_Inner", PALETTE["ear_pink"], 0.5, Subsurface_Weight=0.1,
                                   Subsurface_Scale=0.02)
        m["trunk_tip"] = principled("Trunk_Tip", PALETTE["skin_dark"], 0.5)
        m["dark"] = principled("Lash_Brow", PALETTE["dark"], 0.35)
        m["eye"] = eye_material()
        m["highlight"] = emissive("Eye_Highlight", "#FFFFFF", 3.0)
        m["mouth"] = principled("Mouth_Inside", PALETTE["mouth"], 0.5)
        m["tongue"] = principled("Tongue", PALETTE["tongue"], 0.3, Subsurface_Weight=0.2,
                                 Subsurface_Scale=0.01)
        m["cap"] = fabric("Cap", PALETTE["yellow"])
        m["brim"] = fabric("Cap_Brim", PALETTE["yellow"])
        m["shirt"] = fabric("Shirt", PALETTE["yellow"])
        m["shirt_trim"] = fabric("Shirt_Trim", PALETTE["yellow"])
        m["skirt"] = fabric("Skirt", PALETTE["navy"], 0.7)
        m["bow"] = principled("Bow_Satin", PALETTE["bow"], 0.38, Sheen_Weight=0.6,
                              Sheen_Roughness=0.3, Coat_Weight=0.2)
        m["canvas"] = shoe_upper_material()
        m["sole"] = sole_material()
        m["lace"] = principled("Lace", PALETTE["white"], 0.6)
        m["tuft"] = principled("Tail_Tuft", "#3a2c25", 0.6)
        m["helper"] = principled("Helper", "#ff00ff", 0.5)
        self.mat = m
        self.parts = []

    def add(self, obj):
        self.parts.append(obj)
        return obj

    # ---------------- head ----------------
    def build_head(self):
        def head_shape(u):
            cheek = 1.0 + 0.07 * math.exp(-((u.z + 0.35) / 0.38) ** 2)
            x = u.x * 0.41 * cheek
            y = u.y * 0.385
            if u.y < 0:  # gentle muzzle where the trunk starts
                y -= 0.045 * (-u.y) * math.exp(-(u.x ** 2) / 0.12 - ((u.z + 0.22) ** 2) / 0.10)
            z = u.z * 0.40
            if u.z < 0:
                z *= 1.0 - 0.06 * (-u.z) * max(0.0, -u.y)
            return Vector((x, y, z))

        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=64, v_segments=32, radius=1.0, calc_uvs=True)
        for v in bm.verts:
            v.co = head_shape(v.co)
        # cheeks are placed after the BVH exists; material is attached below
        self.head = self.add(finish_mesh("Head", bm, self.colls["Head"], None,
                                         Matrix.Translation(HEAD_C), subsurf=2))
        self.head_bvh = bvh_of(self.head)

    def head_hit(self, direction):
        """World-space point + normal where a ray from the head centre exits."""
        loc, nrm, _, _ = self.head_bvh.ray_cast(Vector((0, 0, 0)), Vector(direction).normalized())
        return HEAD_C + loc, nrm

    def on_head(self, world_point, lift=0.0):
        loc, nrm = self.head_hit(Vector(world_point) - HEAD_C)
        return loc + nrm * lift, nrm

    def build_skin_material(self):
        cheeks = []
        for s in (-1, 1):
            p, _ = self.head_hit((s * 0.255, -0.28, -0.135))
            cheeks.append(p - HEAD_C)
        self.mat["head"] = skin_with_blush("Head_Skin", cheeks)
        self.head.data.materials.append(self.mat["head"])

    def build_ears(self):
        for s, name in ((-1, "Ear.R"), (1, "Ear.L")):
            cup = 0.1925  # how far the ear rim curls forward

            def outer(u):
                widen = 1.0 + 0.12 * u.z
                return Vector((u.x * widen, u.y, u.z))

            rot = Matrix.Rotation(math.radians(42 * s), 3, "Z") @ Matrix.Rotation(
                math.radians(-10 * s), 3, "Y")
            center = Vector((s * 0.54, 0.10, 1.38))
            ear = ellipsoid(name, self.colls["Head"], self.mat["skin"], center,
                            (0.205, 0.045, 0.315), rot, outer, seg=56, rings=28)
            inner = ellipsoid(name + "_Inner", self.colls["Head"], self.mat["ear_pink"], center,
                              (0.205 * 0.82, 0.02, 0.315 * 0.82), rot, outer, seg=56, rings=28)
            for obj, offset in ((ear, 0.0), (inner, -0.028)):
                for v in obj.data.vertices:
                    co = v.co
                    co.y += offset - cup * (co.x ** 2 + co.z ** 2)
                obj.data.update()
                self.add(obj)
            # tuck the inner edge of the ear (local -s*X points at the skull) backwards
            for obj in (ear, inner):
                for v in obj.data.vertices:
                    edge = -s * v.co.x
                    if edge > 0.12:
                        v.co.y += (edge - 0.12) * 0.25
                obj.data.update()

    def build_trunk(self):
        pts = [(0.00, -0.25, 1.31), (0.005, -0.39, 1.27), (0.03, -0.485, 1.195),
               (0.095, -0.545, 1.125), (0.19, -0.575, 1.10), (0.28, -0.575, 1.13),
               (0.34, -0.56, 1.20), (0.36, -0.55, 1.275), (0.362, -0.548, 1.30)]
        radii = [0.115, 0.106, 0.094, 0.083, 0.074, 0.067, 0.063, 0.065, 0.07]
        self.add(tube("Trunk", self.colls["Head"], self.mat["skin"], pts, radii))
        tip, prev = Vector(pts[-1]), Vector(pts[-2])
        axis = (tip - prev).normalized()
        rot = frame(axis, up=Vector((0, -1, 0)))
        self.add(ellipsoid("Trunk_Tip", self.colls["Head"], self.mat["trunk_tip"],
                           tip + axis * 0.002, (0.058, 0.058, 0.012), rot, subsurf=1))
        for s, side in ((-1, "R"), (1, "L")):
            off = rot @ Vector((s * 0.022, 0.0, 0.0))
            self.add(ellipsoid("Nostril." + side, self.colls["Head"], self.mat["dark"],
                               tip + off + axis * 0.009, (0.011, 0.015, 0.006), rot, subsurf=1))

    def build_mouth(self):
        p, n = self.head_hit((-0.085, -0.29, -0.275))
        rot = frame(n) @ Matrix.Rotation(math.radians(-8), 3, "Z")
        cutter = ellipsoid("Mouth_Cutter", self.colls["Helpers"], self.mat["mouth"], p - n * 0.004,
                           (0.082, 0.062, 0.075), rot,
                           deform=lambda u: Vector((u.x, u.y if u.y < 0 else u.y * 0.45, u.z)),
                           subsurf=1)
        hide_helper(cutter)
        mod = self.head.modifiers.new("Mouth", "BOOLEAN")
        mod.operation = "DIFFERENCE"
        mod.object = cutter
        mod.solver = "EXACT"
        if hasattr(mod, "material_mode"):
            mod.material_mode = "TRANSFER"
        self.head.data.materials.append(self.mat["mouth"])
        self.add(ellipsoid("Tongue", self.colls["Face"], self.mat["tongue"],
                           p - n * 0.032 + rot @ Vector((0.004, -0.028, 0)), (0.055, 0.03, 0.04), rot))

    def build_eyes(self):
        for s, name in ((-1, "Eye.R"), (1, "Eye.L")):
            p, n = self.head_hit((s * 0.155, -0.36, -0.055))
            rot = frame(n)
            radii = (0.068, 0.086, 0.032)
            center = p - n * 0.012
            eye = ellipsoid(name, self.colls["Face"], self.mat["eye"], center, radii, rot,
                            seg=48, rings=24, scale_in_object=True)
            self.add(eye)

            def on_eye(u, v, lift=0.001):
                w = math.sqrt(max(0.0, 1 - u * u - v * v))
                return center + rot @ Vector((u * radii[0], v * radii[1], w * radii[2] + lift))

            for size, (u, v), r in (("Big", (0.32, 0.36), (0.024, 0.03)),
                                    ("Small", (-0.33, -0.38), (0.011, 0.013))):
                self.add(ellipsoid(f"{name}_Highlight_{size}", self.colls["Face"], self.mat["highlight"],
                                   on_eye(u, v), (*r, 0.004), rot, subsurf=1))

            # upper lash line: hugs the top of the eye, thicker at the outer corner
            line, rads = [], []
            for i in range(9):
                t = i / 8
                ang = math.radians(165 - 150 * t)
                local = Vector((s * math.cos(ang) * radii[0] * 0.98,
                                math.sin(ang) * radii[1] * 0.98 + 0.004, 0))
                q, _ = self.on_head(center + rot @ local, lift=0.004)
                line.append(q)
                rads.append(0.0045 + 0.006 * t ** 1.5)
            self.add(tube(name + "_LashLine", self.colls["Face"], self.mat["dark"], line, rads))
            for k, ang in enumerate((18, 36, 54)):
                a = math.radians(ang)
                base_r, length = 0.95, 0.38 + 0.06 * (k == 1)
                pts, lifts = [], (0.004, 0.012, 0.022)
                for j, f in enumerate((base_r, base_r + length * 0.55, base_r + length)):
                    aa = a + math.radians(14) * (j / 2)
                    local = Vector((s * math.cos(aa) * radii[0] * f, math.sin(aa) * radii[1] * f, 0))
                    q, _ = self.on_head(center + rot @ local, lift=lifts[j])
                    pts.append(q)
                self.add(tube(f"{name}_Lash{k + 1}", self.colls["Face"], self.mat["dark"], pts,
                              (0.0065, 0.004, 0.0005)))

            # eyebrow
            brow = []
            for bx, by in ((-0.55, 1.62), (0.05, 1.82), (0.75, 1.68)):
                local = Vector((s * bx * radii[0], by * radii[1], 0))
                q, _ = self.on_head(center + rot @ local, lift=0.004)
                brow.append(q)
            self.add(tube(name + "_Brow", self.colls["Face"], self.mat["dark"], brow,
                          (0.004, 0.0085, 0.0035)))

    # ---------------- cap ----------------
    def build_cap(self):
        gap = 0.006
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=72, v_segments=36, radius=1.0, calc_uvs=True)
        for v in bm.verts:
            d = v.co.normalized()
            loc, _, _, dist = self.head_bvh.ray_cast(Vector((0, 0, 0)), d)
            crown = 0.11 * max(0.0, d.z) ** 2 + 0.03 * max(0.0, -d.y) * max(0.0, d.z)
            v.co = d * (dist + gap + crown)
        dome_bvh = BVHTree.FromBMesh(bm)
        # crown edge: a plane from rim_front above the brows down to rim_back at the nape
        rim_front, rim_back = 0.245, 0.06
        slope = (rim_front - rim_back) / 0.8
        rim_mid = (rim_front + rim_back) / 2
        plane_no = Vector((0, slope, 1)).normalized()
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:],
                               plane_co=(0, 0, rim_mid), plane_no=plane_no, clear_inner=True)
        dome = finish_mesh("Cap_Crown", bm, self.colls["Cap"], self.mat["cap"],
                           Matrix.Translation(HEAD_C))
        sol = dome.modifiers.new("Thickness", "SOLIDIFY")
        sol.thickness = 0.022
        sol.offset = 1.0
        sol.use_even_offset = True
        sub = dome.modifiers.new("Subdivision", "SUBSURF")
        sub.levels = sub.render_levels = 2
        self.add(dome)

        # adjustable-strap opening at the back
        cut = ellipsoid("Cap_Back_Cutter", self.colls["Helpers"], self.mat["helper"],
                        Vector((0, 0.42, HEAD_C.z + 0.055)), (0.125, 0.25, 0.10), Matrix.Identity(3),
                        seg=48, rings=24, subsurf=0)
        hide_helper(cut)
        mod = dome.modifiers.new("Back_Opening", "BOOLEAN")
        mod.operation = "DIFFERENCE"
        mod.object = cut
        mod.solver = "EXACT"
        # strap band across the bottom of the opening
        strap = []
        for i in range(7):
            a = math.radians(-30 + 60 * i / 6)
            d = Vector((math.sin(a), math.cos(a), -slope * math.cos(a))).normalized()
            loc, _, _, _ = dome_bvh.ray_cast(Vector((0, 0, rim_mid + 0.014)), d)
            strap.append(HEAD_C + loc + Vector((d.x, d.y, 0)).normalized() * 0.014)
        self.add(tube("Cap_Strap", self.colls["Cap"], self.mat["cap"], strap,
                      [0.014] * len(strap)))

        # brim: a fan of quads from the crown edge forward
        rows, cols = 10, 61
        a_max = math.radians(84)
        bm = bmesh.new()
        grid = []
        for j in range(cols):
            a = -a_max + 2 * a_max * j / (cols - 1)
            d = Vector((math.sin(a), -math.cos(a), slope * math.cos(a))).normalized()
            hit, _, _, _ = dome_bvh.ray_cast(Vector((0, 0, rim_mid)), d)
            inner = hit - Vector((d.x, d.y, 0)).normalized() * 0.03
            # outer edge is an ellipse: about as wide as the crown, ~0.28 deeper in front
            outer = Vector((0.40 * math.sin(a), -(0.67 * math.cos(a)), 0.0))
            col = []
            for i in range(rows):
                t = i / (rows - 1)
                p = inner.lerp(Vector((outer.x, outer.y, inner.z)), t)
                p.z += -0.04 * t - 0.09 * t * t - 0.04 * math.sin(a) ** 2 * t ** 1.5
                col.append(bm.verts.new(p))
            grid.append(col)
        for j in range(cols - 1):
            for i in range(rows - 1):
                bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
        brim = finish_mesh("Cap_Brim", bm, self.colls["Cap"], self.mat["brim"],
                           Matrix.Translation(HEAD_C))
        sol = brim.modifiers.new("Thickness", "SOLIDIFY")
        sol.thickness = 0.026
        sol.offset = 0.0
        sub = brim.modifiers.new("Subdivision", "SUBSURF")
        sub.levels = sub.render_levels = 2
        self.add(brim)

        # crown button
        top, nrm, _, _ = dome_bvh.ray_cast(Vector((0, 0, 0)), Vector((0, 0.05, 1)).normalized())
        self.add(ellipsoid("Cap_Button", self.colls["Cap"], self.mat["cap"],
                           HEAD_C + top + nrm * 0.03, (0.04, 0.04, 0.022), frame(nrm)))

        # logo decal on the front panel
        hit, nrm, _, _ = dome_bvh.ray_cast(
            Vector((0, 0, 0)), Vector((0, -math.cos(math.radians(47)), math.sin(math.radians(47)))))
        proj = bpy.data.objects.new("Cap_Logo_Projector", None)
        proj.empty_display_type = "CIRCLE"
        self.colls["Helpers"].objects.link(proj)
        proj.matrix_world = (Matrix.Translation(HEAD_C + hit + nrm * 0.03)
                             @ frame(nrm).to_4x4() @ Matrix.Diagonal((0.185, 0.185, 0.185, 1)))
        proj.parent = dome
        proj.matrix_parent_inverse = dome.matrix_world.inverted()
        add_decal(self.mat["cap"], proj, self.textures / "logo_cap.png")
        add_cap_seams(self.mat["cap"])

        # pink bow on her right side
        hit, nrm, _, _ = dome_bvh.ray_cast(Vector((0, 0, 0)), Vector((-1, -0.32, 0.36)).normalized())
        base = HEAD_C + hit + nrm * 0.055
        rot = frame(nrm) @ Matrix.Rotation(math.radians(-18), 3, "Z")
        coll, mat = self.colls["Cap"], self.mat["bow"]

        def lobe(sign):
            def deform(u):
                t = min(1.0, max(0.0, (sign * u.x + 1) / 2))  # 0 at the knot, 1 at the far end
                f = 0.35 + 0.65 * t ** 0.55
                return Vector((u.x, u.y * f, u.z * f))
            return deform

        for sign in (-1, 1):
            lr = rot @ Matrix.Rotation(math.radians(14 * sign), 3, "Z")
            end = "Front" if sign < 0 else "Back"
            self.add(ellipsoid("Bow_Loop." + end, coll, mat, base + lr @ Vector((sign * 0.078, 0, 0)),
                               (0.09, 0.07, 0.036), lr, lobe(sign)))
            tr = rot @ Matrix.Rotation(math.radians(200 + 28 * sign), 3, "Z")
            self.add(ellipsoid("Bow_Tail." + end, coll, mat, base + tr @ Vector((0, 0.06, -0.008)),
                               (0.022, 0.05, 0.014), tr))
        self.add(ellipsoid("Bow_Knot", coll, mat, base + rot @ Vector((0, 0, 0.01)),
                           (0.032, 0.04, 0.032), rot))

    # ---------------- body ----------------
    def torso_shape(self, u):
        fat = 1.0 + 0.08 * max(0.0, -u.z) - 0.09 * max(0.0, u.z) ** 2
        return Vector((u.x * 0.29 * fat, u.y * 0.255 * fat, u.z * 0.31))

    def build_body(self):
        torso = ellipsoid("Shirt_Body", self.colls["Body"], self.mat["shirt"], TORSO_C,
                          (1, 1, 1), deform=self.torso_shape, seg=64, rings=32, subsurf=2)
        self.add(torso)
        bvh = bvh_of(torso)
        hit, nrm, _, _ = bvh.ray_cast(Vector((0, 0, 0.72 - TORSO_C.z)), Vector((0, -1, 0)))
        proj = bpy.data.objects.new("Shirt_Logo_Projector", None)
        proj.empty_display_type = "CIRCLE"
        self.colls["Helpers"].objects.link(proj)
        proj.matrix_world = (Matrix.Translation(TORSO_C + hit + nrm * 0.03)
                             @ frame(nrm).to_4x4() @ Matrix.Diagonal((0.125, 0.125, 0.125, 1)))
        proj.parent = torso
        proj.matrix_parent_inverse = torso.matrix_world.inverted()
        add_decal(self.mat["shirt"], proj, self.textures / "logo_shirt.png")

        # polo collar: a rolled band plus two flaps
        band = []
        for i in range(24):
            a = 2 * math.pi * i / 24
            band.append((0.165 * math.sin(a), 0.15 * -math.cos(a) + 0.01, 1.075 - 0.02 * math.cos(a)))
        self.add(tube("Collar_Band", self.colls["Body"], self.mat["shirt_trim"], band,
                      [0.024] * 24, cyclic=True))
        for s, side in ((-1, "R"), (1, "L")):
            hit, n, _, _ = bvh.ray_cast(Vector((s * 0.08, 0, 1.03 - TORSO_C.z)), Vector((0, -1, 0)))
            p = TORSO_C + hit
            r = frame(n) @ Matrix.Rotation(math.radians(-40 * s), 3, "Z")

            def flap(u):
                taper = 0.4 + 0.6 * (u.y + 1) / 2
                return Vector((u.x * taper, u.y, u.z))
            self.add(ellipsoid("Collar_Flap." + side, self.colls["Body"], self.mat["shirt_trim"],
                               p + n * 0.012, (0.06, 0.05, 0.012), r, flap))

        # pleated skirt
        waist_z, hem_z = 0.665, 0.32
        n_around, n_down, pleats = 200, 26, 22
        bm = bmesh.new()
        rings = []
        for i in range(n_down + 1):
            t = i / n_down
            z = waist_z + (hem_z - waist_z) * t
            flare = 1 - (1 - t) ** 1.6
            rx = 0.262 + (0.50 - 0.262) * flare
            ry = 0.232 + (0.44 - 0.232) * flare
            amp = 0.026 * t ** 0.8
            ring = []
            for j in range(n_around):
                a = 2 * math.pi * j / n_around
                phase = (pleats * a / (2 * math.pi)) % 1.0
                wave = abs(phase - 0.5) * 4 - 1  # triangle wave in [-1, 1]
                r = 1 + amp * wave / 0.45
                ring.append(bm.verts.new((rx * r * math.sin(a), -ry * r * math.cos(a), z)))
            rings.append(ring)
        for i in range(n_down):
            for j in range(n_around):
                k = (j + 1) % n_around
                bm.faces.new((rings[i][j], rings[i][k], rings[i + 1][k], rings[i + 1][j]))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        skirt = finish_mesh("Skirt", bm, self.colls["Body"], self.mat["skirt"])
        sol = skirt.modifiers.new("Thickness", "SOLIDIFY")
        sol.thickness = 0.014
        sol.offset = 1.0
        sub = skirt.modifiers.new("Subdivision", "SUBSURF")
        sub.levels = sub.render_levels = 1
        self.add(skirt)
        self.add(tube("Skirt_Waistband", self.colls["Body"], self.mat["skirt"],
                      [(0.27 * math.sin(2 * math.pi * i / 32), -0.24 * math.cos(2 * math.pi * i / 32),
                        waist_z) for i in range(32)], [0.018] * 32, cyclic=True))

        # tail with a dark tuft peeking under the skirt
        pts = [(0, 0.18, 0.52), (0, 0.33, 0.43), (0, 0.405, 0.32), (0, 0.415, 0.25)]
        self.add(tube("Tail", self.colls["Body"], self.mat["skin"], pts, (0.04, 0.036, 0.03, 0.024)))

        def tuft(u):
            point = 1.0 if u.z > 0 else 1.0 + 0.9 * u.z * 0.6
            return Vector((u.x * point, u.y * point, u.z))
        self.add(ellipsoid("Tail_Tuft", self.colls["Body"], self.mat["tuft"],
                           (0, 0.416, 0.205), (0.034, 0.032, 0.058), deform=tuft))

    def build_arms(self):
        for s, side in ((-1, "R"), (1, "L")):
            S = Vector((s * 0.235, 0.0, 0.995))
            E = Vector((s * 0.305, -0.105, 0.80))
            W = Vector((s * 0.075, -0.33, 0.875))
            pts = [S, (S + E) / 2 + Vector((s * 0.025, 0, 0)), E,
                   (E + W) / 2 + Vector((s * 0.02, -0.02, -0.035)), W]
            self.add(tube("Arm." + side, self.colls["Limbs"], self.mat["skin"], pts,
                          (0.074, 0.071, 0.068, 0.064, 0.06)))
            # puffy short sleeve
            d = (E - S).normalized()
            sleeve = [S - d * 0.05, S + d * 0.04, S + d * 0.115]
            self.add(tube("Sleeve." + side, self.colls["Body"], self.mat["shirt"], sleeve,
                          (0.098, 0.104, 0.1)))
            self.add(tube("Sleeve_Hem." + side, self.colls["Body"], self.mat["shirt_trim"],
                          [S + d * 0.118 + frame(d) @ Vector((0.098 * math.cos(a), 0.098 * math.sin(a), 0))
                           for a in [2 * math.pi * i / 20 for i in range(20)]],
                          [0.012] * 20, cyclic=True))

            # hands pressed together (nop / wai greeting), fingers up
            tilt = Matrix.Rotation(math.radians(-14), 3, "X")

            def mitten(u):
                taper = 1.0 - 0.28 * max(0.0, u.z) ** 1.5
                return Vector((u.x * (1 - 0.35 * max(0.0, u.z)), u.y * taper, u.z))
            hand_c = Vector((s * 0.033, -0.365, 0.955))
            self.add(ellipsoid("Hand." + side, self.colls["Limbs"], self.mat["skin"], hand_c,
                               (0.036, 0.06, 0.1), tilt, mitten))
            thumb_r = tilt @ Matrix.Rotation(math.radians(-25), 3, "X")
            self.add(ellipsoid("Thumb." + side, self.colls["Limbs"], self.mat["skin"],
                               hand_c + tilt @ Vector((s * 0.018, 0.055, -0.01)),
                               (0.022, 0.024, 0.045), thumb_r))

    def build_legs_and_shoes(self):
        for s, side in ((-1, "R"), (1, "L")):
            self.add(tube("Leg." + side, self.colls["Limbs"], self.mat["skin"],
                          [(s * 0.15, 0.0, 0.55), (s * 0.158, -0.005, 0.36), (s * 0.165, -0.015, 0.16)],
                          (0.088, 0.085, 0.08)))
            origin = Vector((s * 0.172, -0.02, 0.0))
            rot = Matrix.Rotation(math.radians(8 * s), 3, "Z")
            m = Matrix.Translation(origin) @ rot.to_4x4()
            coll = self.colls["Shoes"]

            bm = bmesh.new()
            bmesh.ops.create_uvsphere(bm, u_segments=48, v_segments=24, radius=1.0, calc_uvs=True)
            for v in bm.verts:
                u = v.co
                x, y, z = u.x * 0.125, u.y * 0.215 - 0.05, u.z * 0.12
                if z > 0:  # low toe box, taller heel collar
                    z *= 0.62 + 0.38 * min(1.0, max(0.0, (y + 0.10) / 0.2))
                v.co = Vector((x, y, max(z, -0.03) + 0.075))
            upper = finish_mesh("Shoe." + side, bm, coll, self.mat["canvas"], m, subsurf=2)
            self.add(upper)

            bm = bmesh.new()
            bmesh.ops.create_uvsphere(bm, u_segments=48, v_segments=16, radius=1.0, calc_uvs=True)
            for v in bm.verts:
                u = v.co
                v.co = Vector((u.x * 0.138, u.y * 0.232 - 0.05, max(u.z * 0.034, -0.026) + 0.03))
            self.add(finish_mesh("Shoe_Sole." + side, bm, coll, self.mat["sole"], m, subsurf=2))

            ubvh = bvh_of(upper)
            collar = [Vector((0.075 * math.sin(a), 0.03 + 0.085 * math.cos(a), 0.19 - 0.012 * math.cos(a)))
                      for a in [2 * math.pi * i / 24 for i in range(24)]]
            self.add(tube("Shoe_Collar." + side, coll, self.mat["sole"], [m @ c for c in collar],
                          [0.016] * 24, cyclic=True))
            for k, yy in enumerate((-0.135, -0.09, -0.045)):
                bar = []
                for xx in (-0.052, 0.0, 0.052):
                    hit, nn, _, _ = ubvh.ray_cast(Vector((xx, yy, 0.5)), Vector((0, 0, -1)))
                    bar.append(m @ (hit + nn * 0.008))
                self.add(tube(f"Shoe_Lace{k + 1}.{side}", coll, self.mat["lace"], bar, (0.009,) * 3))
            hit, nn, _, _ = ubvh.ray_cast(Vector((0, -0.005, 0.5)), Vector((0, 0, -1)))
            knot = m @ (hit + nn * 0.012)
            for sign, end in ((-1, "In"), (1, "Out")):
                loop = [knot + rot @ Vector((sign * 0.008, 0, 0)),
                        knot + rot @ Vector((sign * 0.04, -0.016, 0.012)),
                        knot + rot @ Vector((sign * 0.05, 0.014, 0.006))]
                self.add(tube(f"Shoe_Bow_{end}.{side}", coll, self.mat["lace"], loop, (0.007,) * 3,
                              cyclic=True))
                self.add(tube(f"Shoe_Lace_End_{end}.{side}", coll, self.mat["lace"],
                              [knot, knot + rot @ Vector((sign * 0.02, -0.04, -0.012)),
                               knot + rot @ Vector((sign * 0.03, -0.065, -0.03))], (0.007, 0.007, 0.006)))

    def build(self):
        self.build_head()
        self.build_skin_material()
        self.build_ears()
        self.build_trunk()
        self.build_eyes()
        self.build_mouth()
        self.build_cap()
        self.build_body()
        self.build_arms()
        self.build_legs_and_shoes()
        root = bpy.data.objects.new("Nong_LanXang_Root", None)
        root.empty_display_type = "ARROWS"
        root.empty_display_size = 0.5
        self.root_coll.objects.link(root)
        for coll in self.colls.values():
            for obj in coll.objects:
                if obj.parent is None:
                    obj.parent = root
        self.root = root
        return root


# --------------------------------------------------------------------------
# studio
# --------------------------------------------------------------------------

def build_studio(samples, resolution):
    scene = bpy.context.scene
    coll = new_collection("Studio")

    # seamless cyclorama backdrop
    bm = bmesh.new()
    prof = []
    for i in range(40):
        t = i / 39
        if t < 0.6:
            prof.append((-9 + 13 * t / 0.6, 0.0))
        else:
            a = (t - 0.6) / 0.4 * (math.pi / 2)
            prof.append((4 + 3.5 * math.sin(a), 3.5 * (1 - math.cos(a))))
    prof.append((7.5, 12.0))
    rows = []
    for x in (-10, 10):
        rows.append([bm.verts.new((x, y, z)) for y, z in prof])
    for i in range(len(prof) - 1):
        bm.faces.new((rows[0][i], rows[1][i], rows[1][i + 1], rows[0][i + 1]))
    backdrop = finish_mesh("Backdrop", bm, coll, principled("Backdrop", PALETTE["backdrop"], 0.9))
    backdrop.data.materials[0].diffuse_color = srgb(PALETTE["backdrop"])

    world = bpy.data.worlds.new("Studio_World")
    scene.world = world
    if bpy.app.version < (5, 0, 0):
        world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = srgb("#e9edf5")
    bg.inputs["Strength"].default_value = 0.35

    def area(name, loc, target, power, size, colour="#FFFFFF"):
        light = bpy.data.lights.new(name, "AREA")
        light.energy = power
        light.size = size
        light.color = srgb(colour)[:3]
        obj = bpy.data.objects.new(name, light)
        coll.objects.link(obj)
        obj.location = loc
        obj.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        return obj

    area("Key", (-3.2, -4.6, 4.6), (0, 0, 1.0), 650, 4.0, "#FFF6EC")
    area("Fill", (4.6, -3.4, 2.2), (0, 0, 1.0), 260, 4.5, "#EEF3FF")
    area("Rim", (2.2, 4.0, 4.2), (0, 0, 1.3), 700, 3.0)
    area("Top", (0.0, -1.0, 6.5), (0, 0, 1.0), 150, 4.0)

    cam_data = bpy.data.cameras.new("Camera")
    cam_data.lens = 100
    cam = bpy.data.objects.new("Camera", cam_data)
    coll.objects.link(cam)
    target = Vector((0, 0, 1.0))
    cam.location = (0, -7.4, 1.32)
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam

    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 8
    scene.render.resolution_x, scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.exposure = -1.25
    return cam


VIEWS = {"front": 0, "three_quarter": 35, "side": 90, "back": 180}


def render_views(root, out_dir, views):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    for name in views:
        root.rotation_euler = (0, 0, math.radians(VIEWS[name]))
        scene.render.filepath = str(out_dir / f"{name}.png")
        bpy.ops.render.render(write_still=True)
        print("rendered", scene.render.filepath, flush=True)
    root.rotation_euler = (0, 0, 0)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    default_out = str(HERE / "nong_lanxang.blend") if bpy.app.background else ""
    ap.add_argument("--out", default=default_out, help="save the .blend here ('' to skip)")
    ap.add_argument("--textures", default=str(HERE / "textures"))
    ap.add_argument("--render", default=None, help="directory for turnaround renders")
    ap.add_argument("--views", default=",".join(VIEWS))
    ap.add_argument("--samples", type=int, default=128)
    ap.add_argument("--res", default="1000x1200")
    args, _ = ap.parse_known_args(argv)

    reset_scene()
    mascot = Mascot(args.textures)
    root = mascot.build()
    build_studio(args.samples, tuple(int(v) for v in args.res.split("x")))
    if args.render:
        render_views(root, args.render, [v for v in args.views.split(",") if v])
    if args.out:
        for img in bpy.data.images:
            if img.filepath and not img.packed_file:
                img.pack()
        bpy.ops.wm.save_as_mainfile(filepath=str(Path(args.out).resolve()), compress=True)
        print("saved", args.out, flush=True)


if __name__ == "__main__":
    main()
