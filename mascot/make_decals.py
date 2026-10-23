"""Turn brochure/assets/logo.png into transparent decals for the mascot.

The yellow disc of the logo is keyed out so only the white elephants and the
blue lettering remain; the cap and shirt fabric shows through underneath.
The shirt variant also gets the thin white ring seen on the model sheet.

Run: python make_decals.py <logo.png> <out_dir>
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

SIZE = 1024
LOGO_YELLOW = np.array([255, 195, 20], dtype=float)


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def main(src, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    img = Image.open(src).convert("RGB")
    a = np.asarray(img).astype(float)

    # Locate the yellow disc so the decal is centred on it.
    d = np.linalg.norm(a - LOGO_YELLOW, axis=2)
    ys, xs = np.nonzero(d < 60)
    cx, cy = (xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2
    r = (xs.max() - xs.min()) / 2
    box = (cx - r, cy - r, cx + r, cy + r)
    disc = img.crop(tuple(int(round(v)) for v in box)).resize((SIZE, SIZE), Image.LANCZOS)
    disc = disc.filter(ImageFilter.UnsharpMask(radius=2, percent=80, threshold=2))
    rgb = np.asarray(disc).astype(float)

    yy, xx = np.mgrid[:SIZE, :SIZE]
    rr = np.hypot(xx - SIZE / 2 + 0.5, yy - SIZE / 2 + 0.5) / (SIZE / 2)
    inside = 1.0 - smoothstep(0.90, 0.93, rr)  # drop the anti-aliased rim
    ink = smoothstep(55, 120, np.linalg.norm(rgb - LOGO_YELLOW, axis=2))

    def save(name, alpha, colour):
        out = np.dstack([colour, alpha * 255]).clip(0, 255).astype(np.uint8)
        Image.fromarray(out, "RGBA").save(out_dir / name)

    save("logo_cap.png", ink * inside, rgb)

    ring = smoothstep(0.915, 0.93, rr) * (1 - smoothstep(0.955, 0.97, rr))
    alpha = np.maximum(ink * inside, ring)
    colour = rgb * (1 - ring[..., None]) + 255 * ring[..., None]
    save("logo_shirt.png", alpha, colour)


if __name__ == "__main__":
    main(*sys.argv[1:3])
