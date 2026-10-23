"""Compose the model sheet from the renders, laid out like the 2D reference.

    python make_sheet.py --renders renders --out renders/model_sheet.png

Writes sheet/model_sheet.html (fonts embedded, images in sheet/img/) and, when a
Chrome/Chromium binary is found (or given with --browser), screenshots it to
--out. A browser is used because it shapes the Lao title correctly. Needs Pillow
and numpy.
"""
import argparse
import base64
import glob
import html
import os
import shutil
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
SHEET = HERE / "sheet"
W, H = 2400, 1800

TURNAROUND = [("front", "Front"), ("three_quarter", "3/4"), ("side", "Side"), ("back", "Back")]
EXPRESSIONS = [("wink", "Wink / Cute"), ("happy", "Happy"), ("sweet", "Sweet")]
DETAILS = [("detail_cap", "Cap Logo<br>(Front)"), ("detail_shirt", "Shirt Logo<br>(Front)"),
           ("detail_bow", "Bow Detail<br>(Right Side)"), ("detail_shoe", "Shoe Detail")]
PALETTE = ["#D8D9DE", "#F5C4CA", "#FFC20E", "#123F86", "#F7F7F4", "#2B231F", "#F58BB4", "#F7A9B4"]
FONTS = [("Lao Looped", f"noto-sans-lao-looped-lao-{w}-normal.woff2", w) for w in (400, 700, 900)] + \
        [("Nunito", f"nunito-latin-{w}-normal.woff2", w) for w in (400, 600, 700, 800, 900)]
ABOUT = ("A cheerful, kind and friendly baby elephant who brings happiness and trust. "
         "She represents Lanexang Assurance with warmth, care and a positive spirit for everyone.")

ICONS = {
    "heart": '<path d="M12 20s-7-4.4-7-9.6A3.9 3.9 0 0 1 12 8a3.9 3.9 0 0 1 7 2.4C19 15.6 12 20 12 20z" fill="#fff"/>',
    "shield": '<path d="M12 4l6.5 2.5v5c0 4.2-2.8 7.4-6.5 8.5-3.7-1.1-6.5-4.3-6.5-8.5v-5z" '
              'fill="none" stroke="#fff" stroke-width="2.2" stroke-linejoin="round"/>',
    "smile": '<circle cx="12" cy="12" r="7.5" fill="none" stroke="#fff" stroke-width="2"/>'
             '<circle cx="9.3" cy="10.4" r="1.1" fill="#fff"/><circle cx="14.7" cy="10.4" r="1.1" fill="#fff"/>'
             '<path d="M8.6 13.6c1.8 2.3 5 2.3 6.8 0" fill="none" stroke="#fff" stroke-width="1.8" '
             'stroke-linecap="round"/>',
}
TRAITS = [("heart", "#FFC20E", "Friendly"), ("shield", "#123F86", "Trustworthy"), ("smile", "#FFC20E", "Positive")]


def contact_shadow(img):
    """The shadow catcher also records the wide, soft shadows of the big area
    lights. Keep only an elliptical contact shadow under the feet."""
    a = np.asarray(img).astype(np.float32)
    rgb_max, alpha = a[..., :3].max(axis=2), a[..., 3]
    ys, xs = np.nonzero((alpha > 200) & (rgb_max > 12))
    feet, cx = ys.max(), (xs.min() + xs.max()) / 2
    half_w, height = (xs.max() - xs.min()) / 2, ys.max() - ys.min()
    yy, xx = np.mgrid[:a.shape[0], :a.shape[1]]
    d = ((xx - cx) / (half_w * 0.8)) ** 2 + ((yy - feet) / (half_w * 0.16)) ** 2
    falloff = np.clip(1 - d, 0, 1) ** 1.5
    # shadow pixels: dark, semi-transparent, and on the floor (low in the frame)
    shadow = (alpha < 245) & (rgb_max <= 12) & (yy > feet - 0.3 * height)
    a[..., 3] = np.where(shadow, alpha * falloff, alpha)
    return Image.fromarray(a.clip(0, 255).astype(np.uint8), "RGBA")


def alpha_box(img, threshold=24):
    return img.getchannel("A").point(lambda a: 255 if a > threshold else 0).getbbox()


def crop_group(names, src, pad, floor=False):
    """Crop a group of renders to one shared box so they keep a common scale."""
    imgs = {n: Image.open(src / f"{n}.png").convert("RGBA") for n in names}
    if floor:
        imgs = {n: contact_shadow(im) for n, im in imgs.items()}
    boxes = [alpha_box(im) for im in imgs.values()]
    x0, y0 = min(b[0] for b in boxes) - pad, min(b[1] for b in boxes) - pad
    x1, y1 = max(b[2] for b in boxes) + pad, max(b[3] for b in boxes) + pad
    for n, im in imgs.items():
        im.crop((max(0, x0), max(0, y0), min(im.width, x1), min(im.height, y1))).save(SHEET / "img" / f"{n}.png")


def font_faces():
    rules = []
    for family, file, weight in FONTS:
        data = base64.b64encode((SHEET / "fonts" / file).read_bytes()).decode()
        rules.append(f"@font-face{{font-family:'{family}';font-weight:{weight};"
                     f"src:url(data:font/woff2;base64,{data}) format('woff2');}}")
    return "\n".join(rules)


def figure(name, label, cls):
    return f'<figure class="{cls}"><div class="pic"><img src="img/{name}.png" alt=""></div>' \
           f'<figcaption>{label}</figcaption></figure>'


def build_html():
    traits = "".join(
        f'<li><span class="ic" style="background:{bg}"><svg viewBox="0 0 24 24">{ICONS[icon]}</svg></span>'
        f'{label}</li>' for icon, bg, label in TRAITS)
    turn = "".join(f'<figure class="view"><img src="img/{n}.png" alt=""><figcaption>{l}</figcaption></figure>'
                   for n, l in TURNAROUND)
    expr = "".join(figure(n, l, "expr") for n, l in EXPRESSIONS)
    details = "".join(f'<figure class="detail"><div class="disc"><img src="img/{n}.png" alt=""></div>'
                      f'<figcaption>{l}</figcaption></figure>' for n, l in DETAILS)
    swatches = "".join(f'<span class="sw" style="background:{c}"></span>' for c in PALETTE)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Nong Lanxang model sheet</title>
<style>
{font_faces()}
:root {{ --navy:#123F86; --yellow:#FFC20E; --ink:#2F3A4F; --chip:#DCE7F5; --panel:#EEF2F8; }}
* {{ box-sizing:border-box; margin:0; padding:0; }}
body {{ width:{W}px; height:{H}px; overflow:hidden; font-family:'Nunito','Lao Looped',sans-serif;
       color:var(--ink); background:radial-gradient(circle at 50% 40%, #ffffff 0%, #f4f6fa 70%); }}
.sheet {{ position:relative; width:{W}px; height:{H}px; padding:44px 60px 40px; }}
header {{ display:flex; align-items:flex-start; height:300px; }}
.brand {{ width:1060px; position:relative; }}
h1 {{ display:inline-block; position:relative; font-family:'Lao Looped'; font-weight:900; font-size:140px;
     line-height:1.12; color:var(--navy); letter-spacing:2px; }}
.spark {{ position:absolute; right:-104px; top:-4px; width:96px; }}
h2 {{ font-weight:900; font-size:56px; color:var(--navy); margin-top:4px; letter-spacing:1px; }}
.tag {{ display:inline-block; margin-top:14px; background:var(--yellow); color:var(--navy); font-weight:800;
       font-size:40px; padding:6px 34px 8px; border-radius:40px; }}
.about {{ width:770px; margin-left:auto; background:#E8EFF8; border-radius:36px; padding:38px 46px;
         font-size:33px; line-height:1.5; font-weight:600; }}
.traits {{ list-style:none; margin-left:46px; padding-left:46px; border-left:3px solid #D5DDE9;
          display:flex; flex-direction:column; gap:22px; padding-top:6px; }}
.traits li {{ display:flex; align-items:center; gap:22px; font-size:38px; font-weight:800; color:var(--navy); }}
.ic {{ width:72px; height:72px; border-radius:50%; display:flex; align-items:center; justify-content:center; }}
.ic svg {{ width:48px; height:48px; }}
.turn {{ display:grid; grid-template-columns:repeat(4, 1fr); gap:30px; height:740px; margin-top:6px; }}
.view {{ display:flex; flex-direction:column; align-items:center; justify-content:flex-end; }}
.view img {{ height:660px; max-width:100%; object-fit:contain; }}
figcaption {{ margin-top:12px; background:var(--chip); color:var(--navy); font-weight:800; font-size:34px;
             padding:4px 44px 6px; border-radius:30px; text-align:center; line-height:1.25; }}
.bottom {{ display:grid; grid-template-columns:1290px 1fr; gap:30px; margin-top:22px; height:648px; }}
.panel {{ position:relative; background:var(--panel); border-radius:40px; padding:84px 30px 28px; }}
.panel > .pill {{ position:absolute; left:30px; top:24px; background:var(--chip); color:var(--navy);
                 font-weight:800; font-size:32px; padding:4px 26px 6px; border-radius:26px; }}
.exprs {{ display:grid; grid-template-columns:repeat(3, minmax(0, 1fr)); gap:14px; height:100%; }}
.expr {{ display:flex; flex-direction:column; align-items:center; min-width:0; }}
.expr .pic {{ width:100%; height:450px; }}
.expr img {{ width:100%; height:100%; object-fit:contain; object-position:center bottom; }}
.expr figcaption {{ background:none; font-size:36px; padding:0; margin-top:10px; color:var(--ink); }}
.right {{ display:flex; flex-direction:column; gap:22px; }}
.right .panel {{ flex:1; }}
.details {{ display:grid; grid-template-columns:repeat(4, 1fr); gap:12px; }}
.detail {{ display:flex; flex-direction:column; align-items:center; }}
.disc {{ width:206px; height:206px; border-radius:50%; overflow:hidden; background:#fff;
        box-shadow:0 0 0 5px #fff, 0 6px 18px rgba(18,63,134,.12); }}
.disc img {{ width:100%; height:100%; object-fit:cover; }}
.detail figcaption {{ background:none; font-size:26px; font-weight:700; padding:0; color:var(--ink);
                     margin-top:14px; }}
.palette {{ flex:0 0 124px; padding:0 30px; display:flex; align-items:center; gap:16px; }}
.palette .pill {{ position:static; margin-right:14px; white-space:nowrap; }}
.sw {{ flex:none; width:58px; height:58px; border-radius:50%;
      box-shadow:0 0 0 3px #fff, 0 2px 8px rgba(0,0,0,.12); }}
</style></head>
<body><div class="sheet">
<header>
  <div class="brand">
    <h1 lang="lo">ນ້ອງ ລ້ານຊ້າງ<svg class="spark" viewBox="0 0 100 100"><g stroke="#FFC20E"
      stroke-width="11" stroke-linecap="round"><path d="M22 44 L34 6"/><path d="M48 58 L80 34"/>
      <path d="M54 84 L94 80"/></g></svg></h1>
    <h2>Lanexang Assurance Mascot</h2>
    <span class="tag">3D Character Model Sheet</span>
  </div>
  <p class="about">{html.escape(ABOUT)}</p>
  <ul class="traits">{traits}</ul>
</header>
<section class="turn">{turn}</section>
<section class="bottom">
  <div class="panel"><span class="pill">Expressions &amp; Poses</span><div class="exprs">{expr}</div></div>
  <div class="right">
    <div class="panel"><span class="pill">Details</span><div class="details">{details}</div></div>
    <div class="panel palette"><span class="pill">Color Palette</span>{swatches}</div>
  </div>
</section>
</div></body></html>
"""


def find_browser(explicit):
    if explicit:
        return explicit
    for name in ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable", "chrome"):
        if shutil.which(name):
            return shutil.which(name)
    found = sorted(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome"))
    return found[-1] if found else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--renders", default=str(HERE / "renders"))
    ap.add_argument("--out", default=str(HERE / "renders" / "model_sheet.png"))
    ap.add_argument("--browser", default=None, help="Chrome/Chromium executable")
    args = ap.parse_args()

    src = Path(args.renders)
    (SHEET / "img").mkdir(parents=True, exist_ok=True)
    crop_group([n for n, _ in TURNAROUND], src, pad=12, floor=True)
    crop_group([n for n, _ in EXPRESSIONS], src, pad=8)
    for n, _ in DETAILS:
        shutil.copy(src / f"{n}.png", SHEET / "img" / f"{n}.png")
    page = SHEET / "model_sheet.html"
    page.write_text(build_html(), encoding="utf-8")
    print("wrote", page)

    browser = find_browser(args.browser)
    if not browser:
        print("no Chrome/Chromium found; open the HTML and screenshot it at", W, "x", H)
        return
    # headless Chrome's viewport is shorter than --window-size, so shoot a taller
    # window and crop back to the sheet
    out = Path(args.out).resolve()
    cmd = [browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
           f"--window-size={W},{H + 300}", "--virtual-time-budget=5000",
           f"--screenshot={out}", page.resolve().as_uri()]
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        cmd.insert(1, "--no-sandbox")  # Chrome refuses to sandbox as root
    subprocess.run(cmd, check=True, capture_output=True)
    Image.open(out).convert("RGB").crop((0, 0, W, H)).save(out)
    print("wrote", out)


if __name__ == "__main__":
    main()
