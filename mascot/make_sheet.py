"""Lay the four turnaround renders out as a model sheet, like the 2D reference.

Run after build_mascot.py --render renders:

    python make_sheet.py renders model_sheet.png
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

NAVY = (18, 63, 134)
YELLOW = (255, 194, 14)
INK = (40, 48, 66)
PANEL = (232, 238, 247)
BG = (247, 248, 250)

FONT_DIRS = ["/usr/share/fonts/truetype/dejavu", "/Library/Fonts", "C:/Windows/Fonts"]

VIEWS = [("front", "Front"), ("three_quarter", "3/4"), ("side", "Side"), ("back", "Back")]
SWATCHES = [("Skin", "#D8D9DE"), ("Ear", "#F5C4CA"), ("Yellow", "#FFC20E"), ("Navy", "#123F86"),
            ("White", "#F7F7F4"), ("Brown", "#2B231F"), ("Bow", "#F58BB4"), ("Blush", "#F7A9B4")]


def font(bold, size):
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    for d in FONT_DIRS:
        p = Path(d) / name
        if p.is_file():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default(size)


def pill(draw, centre, text, fnt, fill, colour, pad=(26, 10), left=None):
    """Rounded label centred on `centre`, or starting at x=`left` when given."""
    w = draw.textlength(text, font=fnt)
    h = fnt.size
    cx = left + pad[0] + w / 2 if left is not None else centre[0]
    x0, y0 = cx - w / 2 - pad[0], centre[1] - h / 2 - pad[1]
    draw.rounded_rectangle((x0, y0, x0 + w + 2 * pad[0], y0 + h + 2 * pad[1] + 4),
                           radius=(h + 2 * pad[1]) // 2, fill=fill)
    draw.text((cx, centre[1] + 2), text, font=fnt, fill=colour, anchor="mm")


def main(render_dir, out):
    render_dir = Path(render_dir)
    W, H = 2400, 1400
    sheet = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(sheet)

    d.text((90, 70), "Nong Lanxang", font=font(True, 92), fill=NAVY)
    d.text((94, 180), "Lanexang Assurance Mascot", font=font(True, 44), fill=NAVY)
    pill(d, (0, 268), "3D Character Model  ·  Blender", font(True, 32), YELLOW, NAVY, left=90)

    box = (1180, 70, 2310, 270)
    d.rounded_rectangle(box, radius=28, fill=PANEL)
    blurb = ("A cheerful, kind and friendly baby elephant who brings\n"
             "happiness and trust. She greets everyone with a nop,\n"
             "wearing the Lanexang Assurance cap, polo and skirt.")
    d.multiline_text((box[0] + 40, box[1] + 36), blurb, font=font(False, 32), fill=INK, spacing=14)

    cell_w, top = 560, 320
    gap = (W - 4 * cell_w) // 5
    for i, (key, label) in enumerate(VIEWS):
        img = Image.open(render_dir / f"{key}.png").convert("RGB")
        w, h = img.size
        crop = img.crop((int(w * 0.1), int(h * 0.05), int(w * 0.9), int(h * 0.95)))
        crop = crop.resize((cell_w, int(cell_w * crop.height / crop.width)), Image.LANCZOS)
        x = gap + i * (cell_w + gap)
        mask = Image.new("L", crop.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, *crop.size), radius=32, fill=255)
        sheet.paste(crop, (x, top), mask)
        pill(d, (x + cell_w // 2, top + crop.height + 44), label, font(True, 34), PANEL, NAVY)

    y = H - 110
    pill(d, (0, y), "Color Palette", font(True, 32), PANEL, NAVY, left=90)
    sx = 420
    for name, hexc in SWATCHES:
        rgb = tuple(int(hexc[i:i + 2], 16) for i in (1, 3, 5))
        d.ellipse((sx, y - 38, sx + 76, y + 38), fill=rgb, outline=(210, 214, 222), width=3)
        d.text((sx + 38, y + 62), hexc, font=font(False, 22), fill=INK, anchor="mm")
        sx += 150
    sheet.save(out)
    print("wrote", out)


if __name__ == "__main__":
    main(*sys.argv[1:3])
