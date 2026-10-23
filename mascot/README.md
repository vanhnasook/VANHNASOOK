# Nong Lanxang (ນ້ອງ ລ້ານຊ້າງ) – 3D mascot

A Blender model of the Lanexang Assurance baby-elephant mascot, built from the
2D character model sheet: grey elephant in the yellow logo cap with a pink bow,
yellow polo with the shirt logo, navy pleated skirt and yellow canvas sneakers,
greeting with a *nop* (hands pressed together).

![Model sheet](renders/model_sheet.png)

| File | What it is |
| --- | --- |
| `nong_lanxang.blend` | The model, with studio lights and camera. Textures are packed in. Saved with Blender 5.2. |
| `build_mascot.py` | Builds the whole scene with Blender's Python API. |
| `make_decals.py` | Turns `brochure/assets/logo.png` into the transparent cap and shirt decals in `textures/`. |
| `make_sheet.py` | Lays the four renders out as `renders/model_sheet.png`. |
| `renders/` | Front, 3/4, side and back renders (Cycles, 1000×1200). |

## Rebuilding

Headless with Blender installed:

```sh
blender --background --python build_mascot.py -- --out nong_lanxang.blend --render renders
python make_sheet.py renders renders/model_sheet.png   # needs Pillow
```

Or with the `bpy` module from PyPI (`pip install bpy pillow`, Python 3.13):

```sh
python build_mascot.py --out nong_lanxang.blend --render renders --samples 96
```

Options: `--views front,side`, `--samples N`, `--res 1000x1200`, `--textures DIR`.

## Using it with a Blender MCP server

The script only uses `bpy`, so it can also be sent to a live Blender session
through a Blender MCP server's "execute code" tool, or run from Blender's
**Scripting** tab. In a live session it doesn't reset the file. It only removes
the `Nong_LanXang` and `Studio` collections from an earlier run, so the MCP add-on
stays loaded, and it saves only when `--out` is given. Keep the `textures/` folder
next to the script, or edit `--textures`. Without the decal images the build still
runs, just without the logos.

## Scene layout

- `Nong_LanXang_Root` is the empty that everything is parented to. Rotate or move
  it to place the character. The renders turn it 0°, 35°, 90° and 180°.
- Collections: `Head` (head, ears, trunk), `Face` (eyes, lashes, brows,
  tongue), `Cap` (crown, brim, button, strap, bow), `Body` (shirt, collar,
  sleeves, skirt, tail), `Limbs`, `Shoes`, and `Helpers` (hidden boolean
  cutters and the two logo projectors).
- The character is 2 units tall, stands on z = 0 and faces −Y.

## Editing notes

- **Shapes** are plain numbers in `build_mascot.py`. The trunk path and radii
  are in `build_trunk`, the arm pose in `build_arms`, the cap rim height in
  `build_cap` (`rim_front` / `rim_back`), and the colours in `PALETTE`.
- **Logos** are projected by the `Cap_Logo_Projector` and
  `Shirt_Logo_Projector` empties. Move or scale them to reposition a logo.
- **Blush, cap seams, eye iris and the shoe toe cap** are procedural shader
  nodes. They render in Cycles/EEVEE, but exporting to glTF/FBX for a game
  engine or the web needs them baked to textures first.
- The mouth is a boolean cut (`Mouth_Cutter`) on the head, and so is the opening
  at the back of the cap (`Cap_Back_Cutter`).
- There is no rig yet. The model is built in the nop pose shown on the front of
  the sheet. The waving 3/4 pose and the wink/happy/sweet expressions would need
  an armature and face shape keys.
