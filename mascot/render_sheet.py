"""Render every picture on the model sheet from nong_lanxang.blend.

Each shot applies one of the rig's stored pose actions (Pose_Nop, Pose_Wave, ...),
turns the character and frames the camera, then renders a transparent PNG.

    blender --background nong_lanxang.blend --python render_sheet.py -- --out renders
    python render_sheet.py --blend nong_lanxang.blend --out renders      # PyPI bpy

Options: --shots front,wink  --samples 96  --scale 50 (percent, for quick tests)
"""
import argparse
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

RIG = "Nong_LanXang_Rig"
FOV_HALF = math.atan(18 / 100)  # 100 mm lens, 36 mm sensor across the longer side

# name: (pose, turn in degrees, framing, resolution)
# framing is "full", "bust", or (object to look at, frame size, view direction or None)
SHOTS = {
    "front": ("Nop", 0, "full", (1000, 1200)),
    "three_quarter": ("Wave", 35, "full", (1000, 1200)),
    "side": ("Relaxed", 90, "full", (1000, 1200)),
    "back": ("Relaxed", 180, "full", (1000, 1200)),
    "wink": ("Wink", 15, "bust", (900, 900)),
    "happy": ("Happy", 0, "bust", (900, 900)),
    "sweet": ("Sweet", 15, "bust", (900, 900)),
    "detail_cap": ("Relaxed", 0, ("Cap_Logo_Projector", 0.5, None), (700, 700)),
    "detail_shirt": ("Relaxed", 0, ("Shirt_Logo_Projector", 0.36, None), (700, 700)),
    "detail_bow": ("Relaxed", 0, ("Bow_Knot", 0.36, None), (700, 700)),
    "detail_shoe": ("Relaxed", 0, ("Shoe.R", 0.44, (-0.65, -1.0, 0.5)), (700, 700)),
}


def set_pose(rig, name):
    act = bpy.data.actions[f"Pose_{name}"]
    rig.animation_data.action = act
    if getattr(rig.animation_data, "action_slot", None) is None and getattr(act, "slots", None):
        rig.animation_data.action_slot = act.slots[0]
    bpy.context.scene.frame_set(1)


def aim_camera(cam, target, direction, size):
    """Place the camera along `direction` from `target` so `size` units fill the frame."""
    dist = size / 2 / math.tan(FOV_HALF)
    cam.location = target + direction.normalized() * dist
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()


def frame_shot(cam, framing):
    if framing == "full":
        aim_camera(cam, Vector((0, 0, 1.0)), Vector((0, -1, 0.043)), 2.66)
    elif framing == "bust":
        aim_camera(cam, Vector((0, 0, 1.42)), Vector((0, -1, 0.05)), 1.5)
    else:
        name, size, direction = framing
        obj = bpy.data.objects[name]
        mw = obj.matrix_world
        if direction is None:  # projectors and the bow knot look out of the surface (+Z)
            direction = mw.to_3x3() @ Vector((0, 0, 1))
            target = mw.translation.copy()
        else:  # shoe: aim at the middle of the shoe, not its floor origin
            target = mw @ Vector((0, -0.06, 0.09))
        aim_camera(cam, target, Vector(direction), size)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--blend", default=None, help="file to open (omit when Blender already has it open)")
    ap.add_argument("--out", default="renders")
    ap.add_argument("--shots", default=",".join(SHOTS))
    ap.add_argument("--samples", type=int, default=96)
    ap.add_argument("--scale", type=int, default=100, help="resolution percentage")
    args, _ = ap.parse_known_args(argv)

    if args.blend:
        bpy.ops.wm.open_mainfile(filepath=str(Path(args.blend).resolve()))
    scene = bpy.context.scene
    rig = bpy.data.objects[RIG]
    cam = scene.camera
    floor = bpy.data.objects["Floor_Shadow"]
    scene.cycles.samples = args.samples
    scene.render.resolution_percentage = args.scale
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    for shot in [s for s in args.shots.split(",") if s]:
        pose, turn, framing, res = SHOTS[shot]
        set_pose(rig, pose)
        rig.rotation_euler = (0, 0, math.radians(turn))
        # the shadow-catcher floor only belongs in full-body shots; close-ups would
        # pick up a faint band of distant floor behind her
        floor.hide_render = framing != "full"
        bpy.context.view_layer.update()
        frame_shot(cam, framing)
        scene.render.resolution_x, scene.render.resolution_y = res
        scene.render.filepath = str((out / f"{shot}.png").resolve())
        bpy.ops.render.render(write_still=True)
        print("rendered", shot, flush=True)

    rig.rotation_euler = (0, 0, 0)
    floor.hide_render = False
    set_pose(rig, "Nop")
    rig.animation_data.action = None


if __name__ == "__main__":
    main()
