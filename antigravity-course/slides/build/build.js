// Builds the Antigravity course decks (Basic, Advanced) as .pptx.
// Usage: NODE_PATH=<dir with pptxgenjs, react, react-dom, react-icons, sharp, jszip> node build.js [outDir]
// Optional: PPTX_SKILL_DIR=<pptx skill dir> to apply the theme with its apply_theme.js helper.
const path = require('path');
const fs = require('fs');
const pptxgen = require('pptxgenjs');
const React = require('react');
const ReactDOMServer = require('react-dom/server');
const sharp = require('sharp');
const JSZip = require('jszip');
const lu = require('react-icons/lu');

const THEME = {
  name: 'Antigravity Course',
  headFontFace: 'Noto Sans Lao Looped',
  bodyFontFace: 'Noto Sans Lao',
  colors: {
    dk1: '0E2A2F', lt1: 'FFFFFF', dk2: '25474D', lt2: 'EEF2F1',
    accent1: '1F55D6', accent2: 'FFD54A', accent3: '137A55', accent4: 'B9402C',
    accent5: '4C6265', accent6: 'E3EBFC', hlink: '1F55D6', folHlink: '4C6265',
  },
};
// Hex copies for images and hex-only options (icons, borders, chart colors).
const HEX = { ink: '0E2A2F', deep: '25474D', paper: 'EEF2F1', white: 'FFFFFF', cobalt: '1F55D6', yellow: 'FFD54A',
  green: '137A55', red: 'B9402C', muted: '4C6265', soft: 'E3EBFC', line: 'D2DDDB', mist: 'A6BDBA' };

const W = 13.333, X0 = 0.6, CW = 12.133, Y0 = 1.95, AVAIL = 4.7;
const LANG = 'lo-LA';

let pres, C, iconCache = {};

async function icon(name, hex) {
  const key = name + hex;
  if (iconCache[key]) return iconCache[key];
  const Comp = lu[name];
  if (!Comp) throw new Error('Unknown icon: ' + name);
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(Comp, { color: '#' + hex, size: '256' }));
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  return (iconCache[key] = 'image/png;base64,' + buf.toString('base64'));
}

// ---------- primitives ----------
function txt(s, text, o) {
  s.addText(text, Object.assign({ isTextBox: true, margin: 0, valign: 'top', lang: LANG, fontSize: 16, color: C.text1, paraSpaceAfter: 0 }, o));
}
function box(s, o) {
  const opts = Object.assign({ rectRadius: 0.12 }, o);
  if (o.shadow) opts.shadow = { type: 'outer', color: HEX.ink, opacity: 0.12, blur: 10, offset: 2, angle: 90 };
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, opts);
}
async function iconDot(s, name, x, y, d, fill, iconHex) {
  s.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: fill } });
  const pad = d * 0.24;
  s.addImage({ data: await icon(name, iconHex), x: x + pad, y: y + pad, w: d - 2 * pad, h: d - 2 * pad });
}
function numDot(s, n, x, y, d, fill, color, fontSize) {
  s.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: fill } });
  txt(s, String(n), { x, y, w: d, h: d, align: 'center', valign: 'middle', bold: true, fontSize: fontSize || 16, color });
}
function pill(s, text, x, y, w, h, fill, color, fontSize, extra) {
  box(s, Object.assign({ x, y, w, h, fill: { color: fill }, rectRadius: h / 2 }, extra || {}));
  txt(s, text, { x, y, w, h, align: 'center', valign: 'middle', fontSize: fontSize || 12, color, bold: true });
}
function bullets(items, o) {
  return items.map((t, i) => ({ text: t, options: Object.assign({ bullet: { indent: 18 }, breakLine: i < items.length - 1, paraSpaceAfter: 12 }, o || {}) }));
}
const surface = (sp) => (sp.layout === 'WORKSHOP' ? C.background1 : C.background2);
async function note(s, text, y, ic) {
  await iconDot(s, ic || 'LuInfo', X0, y, 0.42, HEX.soft, HEX.cobalt);
  txt(s, text, { x: X0 + 0.6, y, w: CW - 0.6, h: 0.42, valign: 'middle', fontSize: 15 });
}

// ---------- layouts ----------
function defineLayouts(label) {
  const ph = (name, type, o) => ({ placeholder: { options: Object.assign({ name, type, margin: 0, valign: 'top', bullet: false }, o), text: '' } });
  const footer = { text: { text: label, options: { x: X0, y: 6.95, w: 9, h: 0.3, fontSize: 10, color: C.accent5, margin: 0, lang: LANG } } };
  const num = { x: 11.93, y: 6.95, w: 0.8, h: 0.3, fontSize: 10, color: HEX.muted, align: 'right' };
  const head = [
    ph('kicker', 'body', { x: X0, y: 0.45, w: 10.2, h: 0.4, fontSize: 14, bold: true, color: C.accent1 }),
    ph('title', 'title', { x: X0, y: 0.85, w: CW, h: 0.85, align: 'left', fontSize: 30, bold: true, color: C.text1 }),
  ];
  pres.defineSlideMaster({ title: 'TITLE', background: { color: C.text1 }, objects: [
    ph('title', 'title', { x: X0, y: 2.3, w: 7.4, h: 1.15, align: 'left', fontSize: 46, bold: true, color: C.background1 }),
    ph('body', 'body', { x: X0, y: 3.55, w: 7.0, h: 1.4, fontSize: 22, color: C.accent2 }),
    ph('meta', 'body', { x: X0, y: 5.7, w: 7.4, h: 0.8, fontSize: 14, color: C.background2 }),
  ] });
  pres.defineSlideMaster({ title: 'SECTION', background: { color: C.text1 }, slideNumber: Object.assign({}, num, { color: HEX.mist }), objects: [
    ph('num', 'body', { x: X0, y: 0.95, w: 4, h: 1.6, fontSize: 88, bold: true, color: C.accent2 }),
    ph('label', 'body', { x: X0, y: 2.75, w: 5.9, h: 0.45, fontSize: 16, color: C.background2 }),
    ph('title', 'title', { x: X0, y: 3.3, w: 5.9, h: 2.4, align: 'left', fontSize: 34, bold: true, color: C.background1 }),
  ] });
  pres.defineSlideMaster({ title: 'CONTENT', background: { color: C.background1 }, slideNumber: num, objects: [...head, footer] });
  pres.defineSlideMaster({ title: 'WORKSHOP', background: { color: C.background2 }, slideNumber: num, objects: [...head, footer,
    { text: { text: 'WORKSHOP', options: { shape: pres.shapes.ROUNDED_RECTANGLE, rectRadius: 0.2, x: 11.03, y: 0.42, w: 1.7, h: 0.4,
      fill: { color: C.accent2 }, color: C.text1, fontSize: 11, bold: true, align: 'center', valign: 'middle', charSpacing: 2, margin: 0 } } },
  ] });
}

// ---------- renderers ----------
const R = {};

R.title = async (s, sp) => {
  txt(s, 'ຫຼັກສູດ Google Antigravity', { x: X0, y: 1.7, w: 7, h: 0.45, fontSize: 15, bold: true, color: C.background2, charSpacing: 1 });
  s.addText(sp.title, { placeholder: 'title', lang: LANG });
  s.addText(sp.subtitle, { placeholder: 'body', lang: LANG, bullet: false });
  s.addText(sp.meta, { placeholder: 'meta', lang: LANG, bullet: false });
  // Motif: claim files lifting off the desk inside an orbit.
  s.addShape(pres.shapes.OVAL, { x: 8.15, y: 1.0, w: 4.7, h: 5.5, line: { color: HEX.deep, width: 1.5, dashType: 'dash' } });
  const cards = sp.cards || [
    ['CLM-2026-0142', 'ໃບສະເໜີລາຄາອູ່ · 8,450,000 ກີບ', -4],
    ['ລາຍງານເຄລມ.xlsx', 'ລົດ 42 · ສຸຂະພາບ 31 · ຊັບສິນ 9', 3],
    ['Agent · Task List', 'ກວດເອກະສານ 12/12 ໄຟລ໌ ແລ້ວ', -1.5],
  ];
  const pos = [[8.3, 1.55], [9.0, 3.05], [8.5, 4.55]];
  for (let i = 0; i < cards.length; i++) {
    const [h, d, rot] = cards[i], [x, y] = pos[i];
    box(s, { x, y, w: 3.9, h: 1.15, fill: { color: i === 2 ? C.accent6 : C.background1 }, rotate: rot, shadow: true });
    txt(s, h, { x: x + 0.25, y: y + 0.17, w: 3.4, h: 0.35, fontSize: 12, bold: true, color: C.accent5, rotate: rot });
    txt(s, d, { x: x + 0.25, y: y + 0.55, w: 3.5, h: 0.4, fontSize: 14, bold: true, color: C.text1, rotate: rot });
  }
};

R.section = async (s, sp) => {
  s.addText(sp.num, { placeholder: 'num', lang: LANG, bullet: false });
  s.addText(sp.label, { placeholder: 'label', lang: LANG, bullet: false });
  s.addText(sp.title, { placeholder: 'title', lang: LANG });
  const x = 7.1, w = 5.63, rowH = 1.2;
  let y = 1.25;
  sp.blocks.forEach((b, i) => {
    if (i) s.addShape(pres.shapes.LINE, { x, y: y - 0.2, w, h: 0, line: { color: HEX.deep, width: 1 } });
    pill(s, b[0] + ' ນາທີ', x, y, 1.3, 0.42, b[2] ? C.accent2 : C.text2, b[2] ? C.text1 : C.background1, 13);
    txt(s, b[1], { x: x + 1.55, y: y - 0.02, w: w - 1.55, h: 0.85, fontSize: 18, bold: true, color: C.background1 });
    y += rowH;
  });
};

R.agenda = async (s, sp) => {
  const n = sp.days.length, two = n === 2;
  const gap = 0.3, cw = (CW - gap) / 2;
  const ch = two ? AVAIL : (AVAIL + 0.1 - gap) / 2;
  sp.days.forEach((d, i) => {
    const x = X0 + (i % 2) * (cw + gap), y = Y0 - (two ? 0 : 0.05) + Math.floor(i / 2) * (ch + gap);
    box(s, { x, y, w: cw, h: ch, fill: { color: C.background2 } });
    txt(s, d.label, { x: x + 0.35, y: y + (two ? 0.3 : 0.18), w: cw - 0.7, h: 0.35, fontSize: 13, bold: true, color: C.accent1 });
    txt(s, d.title, { x: x + 0.35, y: y + (two ? 0.68 : 0.5), w: cw - 0.7, h: 0.5, fontSize: two ? 19 : 16, bold: true });
    const top = y + (two ? 1.45 : 1.0), rh = two ? 0.78 : 0.31;
    d.blocks.forEach((b, j) => {
      const ry = top + j * rh;
      pill(s, b[0] + ' ນາທີ', x + 0.35, ry, two ? 1.2 : 1.05, two ? 0.4 : 0.28, b[2] ? C.accent2 : C.background1, C.text1, two ? 12 : 11);
      txt(s, b[1], { x: x + (two ? 1.75 : 1.6), y: ry - (two ? 0.02 : 0.03), w: cw - (two ? 2.1 : 1.95), h: two ? 0.7 : 0.34, fontSize: two ? 16 : 14, valign: two ? 'top' : 'middle' });
    });
  });
};

R.files = async (s, sp) => {
  const n = sp.files.length, cols = 3, rows = Math.ceil(n / cols), gap = 0.3;
  const cw = (CW - gap * (cols - 1)) / cols;
  const ch = rows === 1 ? 2.75 : 1.95;
  for (let i = 0; i < n; i++) {
    const f = sp.files[i], x = X0 + (i % cols) * (cw + gap), y = Y0 + Math.floor(i / cols) * (ch + gap);
    const star = f.star;
    box(s, { x, y, w: cw, h: ch, fill: { color: star ? C.accent6 : C.background2 }, line: star ? { color: C.accent1, width: 1.25 } : undefined });
    await iconDot(s, f.icon, x + 0.3, y + 0.3, 0.62, star ? HEX.cobalt : HEX.white, star ? HEX.white : HEX.cobalt);
    txt(s, f.name, { x: x + 0.3, y: y + (rows === 1 ? 1.2 : 1.05), w: cw - 0.6, h: 0.5, fontSize: rows === 1 ? 20 : 18, bold: true });
    txt(s, f.d, { x: x + 0.3, y: y + (rows === 1 ? 1.78 : 1.52), w: cw - 0.6, h: rows === 1 ? 0.85 : 0.4, fontSize: rows === 1 ? 17 : 15, color: C.accent5 });
  }
  if (sp.strip) {
    const y = Y0 + 2.75 + 0.4;
    box(s, { x: X0, y, w: CW, h: 1.0, fill: { color: C.text1 } });
    txt(s, sp.strip[0], { x: X0 + 0.4, y, w: 2.0, h: 1.0, valign: 'middle', fontSize: 15, bold: true, color: C.accent2 });
    txt(s, sp.strip[1], { x: X0 + 2.4, y, w: CW - 2.8, h: 1.0, valign: 'middle', fontSize: 17, color: C.background1 });
  }
};

async function asidePanel(s, a, x, y, w, h) {
  box(s, { x, y, w, h, fill: { color: C.text1 } });
  await iconDot(s, a.icon || 'LuLightbulb', x + 0.35, y + 0.35, 0.55, HEX.yellow, HEX.ink);
  txt(s, a.head, { x: x + 0.35, y: y + 1.1, w: w - 0.7, h: 0.5, fontSize: 19, bold: true, color: C.accent2 });
  const lines = [].concat(a.text);
  s.addText(lines.map((t, i) => ({ text: t, options: { breakLine: i < lines.length - 1, paraSpaceAfter: 10 } })),
    { isTextBox: true, margin: 0, valign: 'top', lang: LANG, x: x + 0.35, y: y + 1.7, w: w - 0.7, h: h - 1.95, fontSize: 16, color: C.background1 });
}

R.checklist = async (s, sp) => {
  const w = sp.aside ? 7.35 : CW;
  const rh = sp.rowH || Math.min(0.95, AVAIL / sp.items.length);
  for (let i = 0; i < sp.items.length; i++) {
    const y = Y0 + i * rh;
    if (sp.numbered) numDot(s, i + 1, X0, y + 0.05, 0.46, C.accent1, C.background1, 15);
    else await iconDot(s, 'LuCheck', X0, y + 0.05, 0.46, HEX.green, HEX.white);
    txt(s, sp.items[i], { x: X0 + 0.7, y: y + 0.02, w: w - 0.7, h: rh - 0.1, fontSize: 19, valign: 'top' });
    if (i < sp.items.length - 1) s.addShape(pres.shapes.LINE, { x: X0 + 0.7, y: y + rh - 0.12, w: w - 0.7, h: 0, line: { color: HEX.line, width: 0.75 } });
  }
  if (sp.aside) await asidePanel(s, sp.aside, X0 + 7.8, Y0, CW - 7.8, Math.min(AVAIL, sp.asideH || AVAIL));
};

async function card(s, c, x, y, w, h, tone, onWorkshop) {
  const tones = {
    plain: { fill: onWorkshop ? C.background1 : C.background2, dot: onWorkshop ? HEX.soft : HEX.white, ic: HEX.cobalt, head: C.text1, body: C.text1 },
    accent: { fill: C.accent6, dot: HEX.cobalt, ic: HEX.white, head: C.accent1, body: C.text1 },
    good: { fill: onWorkshop ? C.background1 : C.background2, dot: HEX.green, ic: HEX.white, head: C.accent3, body: C.text1 },
    warn: { fill: onWorkshop ? C.background1 : C.background2, dot: HEX.red, ic: HEX.white, head: C.accent4, body: C.text1 },
    dark: { fill: C.text1, dot: HEX.yellow, ic: HEX.ink, head: C.accent2, body: C.background1 },
  };
  const t = tones[tone || 'plain'];
  box(s, { x, y, w, h, fill: { color: t.fill } });
  return t;
}

R.compare = async (s, sp) => {
  const gap = 0.4, cw = (CW - gap) / 2, ch = sp.note ? AVAIL - 0.75 : AVAIL;
  const ws = sp.layout === 'WORKSHOP';
  for (const [i, c] of [sp.left, sp.right].entries()) {
    const x = X0 + i * (cw + gap), y = Y0;
    const t = await card(s, c, x, y, cw, ch, c.tone, ws);
    await iconDot(s, c.icon, x + 0.35, y + 0.35, 0.6, t.dot, t.ic);
    txt(s, c.head, { x: x + 1.15, y: y + 0.35, w: cw - 1.5, h: 0.6, fontSize: 21, bold: true, color: t.head, valign: 'middle' });
    let top = y + 1.2;
    if (c.quote) {
      const qh = c.quoteH || 1.1;
      box(s, { x: x + 0.35, y: top, w: cw - 0.7, h: qh, fill: { color: c.tone === 'dark' ? C.text2 : C.background1 }, rectRadius: 0.08 });
      txt(s, c.quote, { x: x + 0.55, y: top + 0.15, w: cw - 1.1, h: qh - 0.3, fontSize: 16, italic: true, color: t.body });
      top += qh + 0.3;
    }
    if (c.items && c.items.length)
      s.addText(bullets(c.items), { isTextBox: true, margin: 0, valign: 'top', lang: LANG, x: x + 0.35, y: top, w: cw - 0.7, h: y + ch - top - 0.25, fontSize: 19, color: t.body });
  }
  if (sp.note) await note(s, sp.note, Y0 + ch + 0.33, sp.noteIcon);
};

R.flow = async (s, sp) => {
  const n = sp.steps.length, gap = 0.34, cw = (CW - gap * (n - 1)) / n;
  const hasEx = sp.steps.some((st) => st.ex);
  const ch = sp.h || (sp.note ? AVAIL - 0.85 : AVAIL - 0.2);
  const ws = sp.layout === 'WORKSHOP';
  for (let i = 0; i < n; i++) {
    const st = sp.steps[i], x = X0 + i * (cw + gap), y = Y0;
    box(s, { x, y, w: cw, h: ch, fill: { color: ws ? C.background1 : C.background2 } });
    if (st.icon) await iconDot(s, st.icon, x + 0.28, y + 0.3, 0.62, HEX.cobalt, HEX.white);
    else numDot(s, st.n || i + 1, x + 0.28, y + 0.3, 0.62, C.accent1, C.background1, 18);
    if (st.tag) txt(s, st.tag, { x: x + 1.0, y: y + 0.3, w: cw - 1.2, h: 0.62, fontSize: 13, bold: true, color: C.accent1, valign: 'middle' });
    txt(s, st.h, { x: x + 0.28, y: y + 1.15, w: cw - 0.5, h: 0.8, fontSize: n > 4 ? 18 : 21, bold: true });
    txt(s, st.d, { x: x + 0.28, y: y + 1.9, w: cw - 0.5, h: hasEx ? ch - 3.1 : ch - 2.1, fontSize: n > 4 ? 16 : 17, color: C.accent5 });
    if (st.ex) {
      box(s, { x: x + 0.2, y: y + ch - 1.15, w: cw - 0.4, h: 0.95, fill: { color: ws ? C.background2 : C.background1 }, rectRadius: 0.08 });
      txt(s, st.ex, { x: x + 0.35, y: y + ch - 1.08, w: cw - 0.7, h: 0.82, fontSize: 15, italic: true, valign: 'middle' });
    }
    if (i < n - 1) s.addShape(pres.shapes.ISOSCELES_TRIANGLE,
      { x: x + cw + 0.08, y: y + 0.48, w: 0.18, h: 0.26, rotate: 90, fill: { color: C.accent5 } });
  }
  if (sp.note) await note(s, sp.note, Y0 + ch + 0.4, sp.noteIcon);
};

R.cards = async (s, sp) => {
  const n = sp.cards.length, cols = sp.cols || n, rows = Math.ceil(n / cols), gap = 0.3;
  const cw = (CW - gap * (cols - 1)) / cols;
  let top = Y0;
  if (sp.lead) {
    txt(s, sp.lead, { x: X0, y: top, w: CW, h: 0.8, fontSize: 20 });
    top += 0.95;
  }
  const avail = Y0 + AVAIL - top - (sp.note ? 0.8 : 0);
  const ch = rows === 1 ? Math.min(avail, sp.h || 3.8) : (avail - gap * (rows - 1)) / rows;
  const ws = sp.layout === 'WORKSHOP';
  for (let i = 0; i < n; i++) {
    const c = sp.cards[i], x = X0 + (i % cols) * (cw + gap), y = top + Math.floor(i / cols) * (ch + gap);
    const t = await card(s, c, x, y, cw, ch, c.tone, ws);
    const compact = rows > 1 && ch < 2.2, big = rows === 1;
    const dd = big ? 0.72 : 0.6;
    if (c.icon) await iconDot(s, c.icon, x + 0.3, y + 0.3, dd, t.dot, t.ic);
    else numDot(s, c.n, x + 0.3, y + 0.3, dd, C.accent1, C.background1, 17);
    if (compact) {
      txt(s, c.h, { x: x + 1.1, y: y + 0.3, w: cw - 1.4, h: 0.6, fontSize: 18, bold: true, color: t.head, valign: 'middle' });
      txt(s, c.d, { x: x + 1.1, y: y + 0.95, w: cw - 1.4, h: ch - 1.1, fontSize: 15, color: t.body });
    } else {
      txt(s, c.h, { x: x + 0.3, y: y + (big ? 1.25 : 1.08), w: cw - 0.6, h: big ? 0.7 : 0.55, fontSize: big ? 22 : 19, bold: true, color: t.head });
      txt(s, c.d, { x: x + 0.3, y: y + (big ? 2.0 : 1.65), w: cw - 0.6, h: ch - (big ? 2.2 : 1.85), fontSize: big ? 18 : 16, color: t.body });
    }
  }
  if (sp.note) await note(s, sp.note, Y0 + AVAIL - 0.45, sp.noteIcon);
};

R.prompt = async (s, sp) => {
  const lw = 4.35;
  txt(s, sp.stepsHead || 'ຂັ້ນຕອນ', { x: X0, y: Y0, w: lw, h: 0.4, fontSize: 14, bold: true, color: C.accent1 });
  sp.steps.forEach((t, i) => {
    const y = Y0 + 0.55 + i * 0.82;
    numDot(s, i + 1, X0, y, 0.44, C.accent1, C.background1, 14);
    txt(s, t, { x: X0 + 0.62, y: y - 0.02, w: lw - 0.62, h: 0.78, fontSize: 16 });
  });
  if (sp.tip) {
    const y = Y0 + AVAIL - 0.95;
    await iconDot(s, 'LuLightbulb', X0, y + 0.05, 0.44, HEX.yellow, HEX.ink);
    txt(s, sp.tip, { x: X0 + 0.62, y, w: lw - 0.62, h: 0.95, fontSize: 14, color: C.accent5 });
  }
  const px = X0 + lw + 0.4, pw = CW - lw - 0.4;
  box(s, { x: px, y: Y0, w: pw, h: AVAIL, fill: { color: C.text1 } });
  txt(s, sp.label || 'PROMPT', { x: px + 0.4, y: Y0 + 0.3, w: 3, h: 0.35, fontSize: 12, bold: true, color: C.accent2, charSpacing: 3 });
  const lines = sp.prompt.split('\n');
  s.addText(lines.map((t, i) => ({ text: t || ' ', options: { breakLine: i < lines.length - 1 } })),
    { isTextBox: true, margin: 0, valign: 'top', lang: LANG, x: px + 0.4, y: Y0 + 0.8, w: pw - 0.8, h: AVAIL - 1.05, fontSize: sp.promptSize || 16, color: C.background1, lineSpacingMultiple: 1.05 });
};

R.table = async (s, sp) => {
  const ws = sp.layout === 'WORKSHOP';
  const hdr = sp.head.map((h) => ({ text: h, options: { bold: true, color: C.background1, fill: { color: C.text1 }, lang: LANG } }));
  const body = sp.rows.map((r, ri) => r.map((c, ci) => {
    const last = sp.highlightLast && ri === sp.rows.length - 1;
    const o = { lang: LANG, color: C.text1, fill: { color: last ? C.accent2 : ri % 2 ? (ws ? C.background2 : C.background2) : C.background1 }, bold: last || (sp.boldFirst && ci === 0) };
    if (sp.align && sp.align[ci]) o.align = sp.align[ci];
    return { text: c, options: o };
  }));
  const rowH = sp.rowH || 0.5;
  s.addTable([hdr, ...body], { x: X0, y: Y0, w: CW, colW: sp.colW, rowH, fontSize: sp.fontSize || 15, valign: 'middle', margin: [4, 8, 4, 8],
    border: { type: 'solid', pt: 0.75, color: HEX.line } });
  if (sp.note) await note(s, sp.note, Math.min(Y0 + rowH * (sp.rows.length + 1) + 0.35, 6.25), sp.noteIcon);
};

R.chart = async (s, sp) => {
  const cw = 7.3;
  box(s, { x: X0, y: Y0, w: cw, h: AVAIL, fill: { color: C.background1 } });
  s.addChart(pres.charts.BAR, [{ name: sp.seriesName, labels: sp.labels, values: sp.values }], {
    x: X0 + 0.2, y: Y0 + 0.15, w: cw - 0.4, h: AVAIL - 0.3, barDir: 'col', chartColors: [HEX.cobalt], barGapWidthPct: 60,
    showTitle: true, title: sp.chartTitle, titleFontSize: 15, titleColor: HEX.ink, titleFontFace: '+mn-lt',
    showValue: true, dataLabelPosition: 'outEnd', dataLabelColor: HEX.ink, dataLabelFontSize: 15, dataLabelFontFace: '+mn-lt',
    catAxisLabelColor: HEX.muted, catAxisLabelFontSize: 15, catAxisLabelFontFace: '+mn-lt', catAxisLineShow: false,
    valAxisHidden: true, valGridLine: { style: 'none' }, catGridLine: { style: 'none' }, showLegend: false,
  });
  const x = X0 + cw + 0.35, w = CW - cw - 0.35;
  let y = Y0;
  for (const st of sp.stats) {
    box(s, { x, y, w, h: 1.25, fill: { color: st.dark ? C.text1 : C.background1 } });
    txt(s, st.v, { x: x + 0.3, y: y + 0.12, w: w - 0.6, h: 0.65, fontSize: 32, bold: true, color: st.dark ? C.accent2 : st.color || C.text1 });
    txt(s, st.l, { x: x + 0.3, y: y + 0.78, w: w - 0.6, h: 0.4, fontSize: 15, color: st.dark ? C.background1 : C.accent5 });
    y += 1.4;
  }
  for (const k of sp.keys || []) {
    s.addShape(pres.shapes.RECTANGLE, { x, y: y + 0.08, w: 0.3, h: 0.3, fill: { color: k.c } });
    txt(s, k.l, { x: x + 0.45, y, w: w - 0.45, h: 0.45, fontSize: 15, valign: 'middle' });
    y += 0.5;
  }
};

R.tree = async (s, sp) => {
  const w = 7.35;
  for (let i = 0; i < sp.rows.length; i++) {
    const [lvl, kind, name, cmt] = sp.rows[i], y = Y0 + i * 0.66, x = X0 + lvl * 0.5;
    s.addImage({ data: await icon(kind === 'dir' ? 'LuFolder' : 'LuFileSpreadsheet', kind === 'dir' ? HEX.cobalt : HEX.muted), x, y: y + 0.06, w: 0.36, h: 0.36 });
    txt(s, name, { x: x + 0.5, y, w: 3.4 - lvl * 0.5, h: 0.5, fontSize: 17, bold: kind === 'dir', valign: 'middle' });
    if (cmt) txt(s, cmt, { x: X0 + 3.9, y, w: w - 3.9, h: 0.5, fontSize: 15, color: C.accent5, valign: 'middle' });
  }
  if (sp.aside) await asidePanel(s, sp.aside, X0 + 7.8, Y0, CW - 7.8, AVAIL);
};

R.ui = async (s, sp) => {
  const folder = await icon('LuFolder', HEX.cobalt);
  const x = X0, y = Y0, w = 7.9, h = AVAIL;
  box(s, { x, y, w, h, fill: { color: C.background1 }, line: { color: HEX.line, width: 1 }, rectRadius: 0.1, shadow: true });
  s.addShape(pres.shapes.RECTANGLE, { x: x + 0.02, y: y + 0.42, w: w - 0.04, h: 0.01, fill: { color: HEX.line } });
  ['B9402C', 'FFD54A', '137A55'].forEach((c, i) => s.addShape(pres.shapes.OVAL, { x: x + 0.22 + i * 0.25, y: y + 0.14, w: 0.15, h: 0.15, fill: { color: c } }));
  pill(s, 'Agent Manager', x + w - 2.05, y + 0.07, 1.85, 0.3, C.accent6, C.accent1, 11);
  // Explorer
  const ex = { x: x + 0.15, y: y + 0.6, w: 1.85, h: h - 0.75 };
  box(s, Object.assign({ fill: { color: C.background2 }, rectRadius: 0.06 }, ex));
  ['data/', 'templates/', 'output/', 'demo/'].forEach((t, i) => {
    s.addImage({ data: folder, x: ex.x + 0.15, y: ex.y + 0.2 + i * 0.45, w: 0.26, h: 0.26 });
    txt(s, t, { x: ex.x + 0.5, y: ex.y + 0.16 + i * 0.45, w: 1.3, h: 0.35, fontSize: 13, valign: 'middle' });
  });
  // Editor grid
  const ed = { x: x + 2.15, y: y + 0.6, w: 3.35, h: h - 0.75 };
  box(s, Object.assign({ fill: { color: C.background1 }, line: { color: HEX.line, width: 0.75 }, rectRadius: 0.06 }, ed));
  for (let r = 0; r < 7; r++) for (let c = 0; c < 3; c++)
    s.addShape(pres.shapes.RECTANGLE, { x: ed.x + 0.2 + c * 1.02, y: ed.y + 0.25 + r * 0.45, w: 0.9, h: 0.22, fill: { color: r === 0 ? HEX.deep : HEX.paper } });
  // Agent panel
  const ag = { x: x + 5.65, y: y + 0.6, w: 2.1, h: h - 0.75 };
  box(s, Object.assign({ fill: { color: C.accent6 }, rectRadius: 0.06 }, ag));
  box(s, { x: ag.x + 0.5, y: ag.y + 0.25, w: 1.45, h: 0.7, fill: { color: C.accent1 }, rectRadius: 0.08 });
  txt(s, 'ລວມ Excel 5 ສາຂາ', { x: ag.x + 0.6, y: ag.y + 0.3, w: 1.3, h: 0.6, fontSize: 11, color: C.background1, valign: 'middle' });
  box(s, { x: ag.x + 0.15, y: ag.y + 1.15, w: 1.8, h: 1.2, fill: { color: C.background1 }, rectRadius: 0.08 });
  txt(s, 'ແຜນງານ 4 ຂັ້ນຕອນ ພ້ອມແລ້ວ. ກວດ ແລະ ອະນຸມັດໄດ້ເລີຍ', { x: ag.x + 0.25, y: ag.y + 1.22, w: 1.6, h: 1.05, fontSize: 11 });
  box(s, { x: ag.x + 0.15, y: ag.y + ag.h - 0.6, w: 1.8, h: 0.45, fill: { color: C.background1 }, line: { color: C.accent1, width: 1 }, rectRadius: 0.08 });
  txt(s, 'ພິມຄຳສັ່ງ...', { x: ag.x + 0.28, y: ag.y + ag.h - 0.6, w: 1.6, h: 0.45, fontSize: 11, color: C.accent5, valign: 'middle' });
  // Badges
  [[ex.x + ex.w - 0.25, ex.y - 0.2], [ed.x + ed.w - 0.25, ed.y - 0.2], [ag.x + ag.w - 0.25, ag.y - 0.2]].forEach(([bx, by], i) =>
    numDot(s, i + 1, bx, by, 0.42, C.accent2, C.text1, 14));
  numDot(s, 4, x + w - 2.3, y + 0.02, 0.38, C.accent2, C.text1, 13);
  // Legend
  const lx = x + w + 0.45, lw = CW - w - 0.45;
  sp.callouts.forEach((c, i) => {
    const ly = Y0 + 0.1 + i * 1.15;
    numDot(s, i + 1, lx, ly, 0.46, C.accent2, C.text1, 15);
    txt(s, c[0], { x: lx + 0.65, y: ly - 0.02, w: lw - 0.65, h: 0.45, fontSize: 18, bold: true });
    txt(s, c[1], { x: lx + 0.65, y: ly + 0.42, w: lw - 0.65, h: 0.65, fontSize: 15, color: C.accent5 });
  });
};

R.exercise = async (s, sp) => {
  box(s, { x: X0, y: Y0, w: CW, h: 1.35, fill: { color: C.background1 }, line: { color: C.accent4, width: 1.5 } });
  txt(s, sp.label, { x: X0 + 0.4, y: Y0 + 0.18, w: 5, h: 0.35, fontSize: 13, bold: true, color: C.accent4 });
  txt(s, sp.weak, { x: X0 + 0.4, y: Y0 + 0.55, w: CW - 0.8, h: 0.65, fontSize: 24, bold: true });
  const n = sp.qs.length, gap = 0.25, cw = (CW - gap * (n - 1)) / n, y = Y0 + 1.75;
  txt(s, sp.qHead, { x: X0, y: y - 0.05, w: CW, h: 0.4, fontSize: 15, bold: true, color: C.accent1 });
  sp.qs.forEach((q, i) => {
    const x = X0 + i * (cw + gap);
    box(s, { x, y: y + 0.45, w: cw, h: 1.65, fill: { color: C.background1 } });
    numDot(s, i + 1, x + 0.25, y + 0.68, 0.46, C.accent1, C.background1, 15);
    txt(s, q, { x: x + 0.25, y: y + 1.25, w: cw - 0.5, h: 0.8, fontSize: 16, bold: true });
  });
  if (sp.note) await note(s, sp.note, Y0 + AVAIL - 0.45, 'LuTimer');
};

R.extract = async (s, sp) => {
  const dw = 4.7, d = sp.doc;
  box(s, { x: X0, y: Y0, w: dw, h: AVAIL, fill: { color: C.background1 }, line: { color: HEX.line, width: 1 }, rectRadius: 0.06, shadow: true });
  txt(s, d.head, { x: X0 + 0.35, y: Y0 + 0.3, w: dw - 0.7, h: 0.45, fontSize: 18, bold: true });
  txt(s, d.sub, { x: X0 + 0.35, y: Y0 + 0.78, w: dw - 0.7, h: 0.35, fontSize: 12, color: C.accent5 });
  s.addShape(pres.shapes.LINE, { x: X0 + 0.35, y: Y0 + 1.25, w: dw - 0.7, h: 0, line: { color: HEX.line, width: 1, dashType: 'dash' } });
  d.lines.forEach((l, i) => {
    const y = Y0 + 1.4 + i * 0.55, total = i === d.lines.length - 1;
    if (total) s.addShape(pres.shapes.LINE, { x: X0 + 0.35, y: y - 0.06, w: dw - 0.7, h: 0, line: { color: HEX.ink, width: 1 } });
    txt(s, l[0], { x: X0 + 0.35, y, w: 2.5, h: 0.45, fontSize: 15, bold: total, valign: 'middle' });
    txt(s, l[1], { x: X0 + 2.6, y, w: dw - 2.95, h: 0.45, fontSize: 15, bold: total, align: 'right', valign: 'middle' });
  });
  txt(s, d.foot, { x: X0 + 0.35, y: Y0 + AVAIL - 0.6, w: dw - 0.7, h: 0.4, fontSize: 12, color: C.accent5, italic: true });
  await iconDot(s, 'LuArrowRight', X0 + dw + 0.2, Y0 + AVAIL / 2 - 0.3, 0.6, HEX.cobalt, HEX.white);
  const tx = X0 + dw + 1.0, tw = CW - dw - 1.0;
  const hdr = sp.head.map((h) => ({ text: h, options: { bold: true, color: C.background1, fill: { color: C.text1 }, lang: LANG } }));
  const body = sp.rows.map((r, ri) => r.map((c, ci) => ({ text: c, options: { lang: LANG, color: C.text1, bold: ri === sp.rows.length - 1,
    align: ci === 1 ? 'right' : 'left', fill: { color: ri % 2 ? C.background2 : C.background1 } } })));
  s.addTable([hdr, ...body], { x: tx, y: Y0, w: tw, colW: [tw * 0.5, tw * 0.5], rowH: 0.5, fontSize: 15, valign: 'middle', margin: [4, 8, 4, 8],
    border: { type: 'solid', pt: 0.75, color: HEX.line } });
  if (sp.check) {
    const y = Y0 + 0.5 * (sp.rows.length + 1) + 0.3;
    box(s, { x: tx, y, w: tw, h: AVAIL - (y - Y0), fill: { color: C.accent6 } });
    await iconDot(s, 'LuCheck', tx + 0.3, y + 0.3, 0.46, HEX.green, HEX.white);
    txt(s, sp.check, { x: tx + 0.95, y: y + 0.25, w: tw - 1.25, h: AVAIL - (y - Y0) - 0.4, fontSize: 16 });
  }
};

R.kpi = async (s, sp) => {
  const n = sp.tiles.length, gap = 0.3, tw = (CW - gap * (n - 1)) / n;
  sp.tiles.forEach((t, i) => {
    const x = X0 + i * (tw + gap);
    box(s, { x, y: Y0, w: tw, h: 1.35, fill: { color: C.background1 } });
    txt(s, t[0], { x: x + 0.3, y: Y0 + 0.18, w: tw - 0.6, h: 0.35, fontSize: 14, color: C.accent5 });
    txt(s, t[1], { x: x + 0.3, y: Y0 + 0.55, w: tw - 0.6, h: 0.7, fontSize: 34, bold: true, color: t[2] ? C.accent4 : C.text1 });
  });
  const y = Y0 + 1.65, h = AVAIL - 1.65, cw = 7.2;
  box(s, { x: X0, y, w: cw, h, fill: { color: C.background1 } });
  s.addChart(pres.charts.BAR, [{ name: sp.seriesName, labels: sp.labels, values: sp.values }], {
    x: X0 + 0.15, y: y + 0.1, w: cw - 0.3, h: h - 0.2, barDir: 'bar', chartColors: [HEX.cobalt], barGapWidthPct: 50,
    showTitle: true, title: sp.chartTitle, titleFontSize: 14, titleColor: HEX.ink, titleFontFace: '+mn-lt',
    showValue: true, dataLabelPosition: 'outEnd', dataLabelColor: HEX.ink, dataLabelFontSize: 14, dataLabelFontFace: '+mn-lt',
    catAxisLabelColor: HEX.muted, catAxisLabelFontSize: 14, catAxisLabelFontFace: '+mn-lt', catAxisOrientation: 'maxMin', catAxisLineShow: false,
    valAxisHidden: true, valGridLine: { style: 'none' }, catGridLine: { style: 'none' }, showLegend: false,
  });
  const lx = X0 + cw + 0.3, lw = CW - cw - 0.3;
  box(s, { x: lx, y, w: lw, h, fill: { color: C.background1 } });
  txt(s, sp.listHead, { x: lx + 0.3, y: y + 0.2, w: lw - 0.6, h: 0.4, fontSize: 15, bold: true });
  sp.list.forEach((r, i) => {
    const ry = y + 0.65 + i * 0.62;
    txt(s, r[0], { x: lx + 0.3, y: ry, w: lw - 1.6, h: 0.3, fontSize: 13, bold: true });
    txt(s, r[1], { x: lx + 0.3, y: ry + 0.3, w: lw - 1.6, h: 0.3, fontSize: 13, color: C.accent5 });
    pill(s, r[2], lx + lw - 1.3, ry + 0.08, 1.0, 0.4, C.accent4, C.background1, 12);
  });
  if (sp.caption) txt(s, sp.caption, { x: lx + 0.3, y: y + h - 0.38, w: lw - 0.6, h: 0.28, fontSize: 11, italic: true, color: C.accent5 });
};

R.parallel = async (s, sp) => {
  const yc = Y0 + 1.75;
  box(s, { x: X0, y: yc - 0.9, w: 2.1, h: 1.8, fill: { color: C.text1 } });
  await iconDot(s, 'LuUser', X0 + 0.7, yc - 0.65, 0.7, HEX.yellow, HEX.ink);
  txt(s, sp.you, { x: X0 + 0.1, y: yc + 0.2, w: 1.9, h: 0.5, fontSize: 17, bold: true, color: C.accent2, align: 'center' });
  const lx = X0 + 2.9, lw = CW - 2.9, lh = 1.0, gap = 0.2;
  for (let i = 0; i < sp.lanes.length; i++) {
    const [name, task, status, st] = sp.lanes[i], y = Y0 + i * (lh + gap);
    s.addShape(pres.shapes.LINE, { x: X0 + 2.1, y: yc, w: 0.8, h: y + lh / 2 - yc, line: { color: HEX.muted, width: 1.25, dashType: 'dash' }, flipV: y + lh / 2 < yc });
    box(s, { x: lx, y, w: lw, h: lh, fill: { color: C.background2 } });
    await iconDot(s, 'LuBot', lx + 0.25, y + 0.2, 0.6, HEX.cobalt, HEX.white);
    txt(s, name, { x: lx + 1.05, y: y + 0.14, w: 4, h: 0.32, fontSize: 13, bold: true, color: C.accent1 });
    txt(s, task, { x: lx + 1.05, y: y + 0.46, w: lw - 3.6, h: 0.45, fontSize: 17, bold: true });
    const fill = { done: C.accent3, run: C.accent1, wait: C.accent2 }[st];
    pill(s, status, lx + lw - 2.35, y + 0.3, 2.1, 0.42, fill, st === 'wait' ? C.text1 : C.background1, 13);
  }
  if (sp.note) await note(s, sp.note, Y0 + AVAIL - 0.45, 'LuUsers');
};

R.recap = async (s, sp) => {
  const lw = 6.3;
  for (let i = 0; i < sp.items.length; i++) {
    const y = Y0 + i * 0.82;
    await iconDot(s, 'LuCheck', X0, y + 0.04, 0.46, HEX.green, HEX.white);
    txt(s, sp.items[i], { x: X0 + 0.7, y, w: lw - 0.7, h: 0.75, fontSize: 18 });
  }
  const fx = X0 + lw + 0.4, fw = CW - lw - 0.4;
  txt(s, sp.filesHead, { x: fx, y: Y0, w: fw, h: 0.4, fontSize: 14, bold: true, color: C.accent1 });
  for (let i = 0; i < sp.files.length; i++) {
    const f = sp.files[i], y = Y0 + 0.55 + i * 0.95;
    box(s, { x: fx, y, w: fw, h: 0.8, fill: { color: C.background2 } });
    await iconDot(s, f[0], fx + 0.2, y + 0.15, 0.5, HEX.white, HEX.cobalt);
    txt(s, f[1], { x: fx + 0.9, y, w: fw - 1.1, h: 0.8, fontSize: 16, bold: true, valign: 'middle' });
  }
};

// ---------- deck ----------
async function patchTheme(file) {
  const zip = await JSZip.loadAsync(fs.readFileSync(file));
  for (const name of Object.keys(zip.files).filter((n) => /^ppt\/theme\/theme\d+\.xml$/.test(n))) {
    let xml = await zip.file(name).async('string');
    if (!process.env.PPTX_SKILL_DIR) {
      const c = THEME.colors, el = (k) => `<a:${k}><a:srgbClr val="${c[k]}"/></a:${k}>`;
      xml = xml.replace(/<a:clrScheme name="[^"]*">[\s\S]*?<\/a:clrScheme>/,
        `<a:clrScheme name="${THEME.name}">${['dk1', 'lt1', 'dk2', 'lt2', 'accent1', 'accent2', 'accent3', 'accent4', 'accent5', 'accent6', 'hlink', 'folHlink'].map(el).join('')}</a:clrScheme>`);
    }
    // Lao is a complex script: point the cs slot and the Laoo script font at the Lao faces.
    const fix = (block, face) => block
      .replace(/<a:cs typeface="[^"]*"\s*\/>/, `<a:cs typeface="${face}"/>`)
      .replace(/<a:font script="Laoo" typeface="[^"]*"\s*\/>/, `<a:font script="Laoo" typeface="${face}"/>`);
    xml = xml.replace(/<a:majorFont>[\s\S]*?<\/a:majorFont>/, (m) => fix(m, THEME.headFontFace))
      .replace(/<a:minorFont>[\s\S]*?<\/a:minorFont>/, (m) => fix(m, THEME.bodyFontFace));
    zip.file(name, xml);
  }
  fs.writeFileSync(file, await zip.generateAsync({ type: 'nodebuffer', compression: 'DEFLATE' }));
}

async function buildDeck(deck, outDir) {
  pres = new pptxgen();
  pres.layout = 'LAYOUT_WIDE';
  pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
  pres.title = deck.title;
  pres.author = deck.author || 'Antigravity Workshop';
  pres.lang = LANG;
  C = pres.SchemeColor;
  defineLayouts(deck.footer);
  for (const sec of deck.sections) {
    pres.addSection({ title: sec.title });
    for (const sp of sec.slides) {
      const layout = sp.layout || ({ title: 'TITLE', section: 'SECTION' }[sp.type]) || 'CONTENT';
      sp.layout = layout;
      const s = pres.addSlide({ masterName: layout, sectionTitle: sec.title });
      if (layout === 'CONTENT' || layout === 'WORKSHOP') {
        if (sp.kicker) s.addText(sp.kicker, { placeholder: 'kicker', lang: LANG, bullet: false });
        s.addText(sp.title, { placeholder: 'title', lang: LANG });
      }
      if (!R[sp.type]) throw new Error('No renderer for ' + sp.type);
      await R[sp.type](s, sp);
      if (sp.notes) s.addNotes(sp.notes);
    }
  }
  const file = path.join(outDir, deck.file);
  await pres.writeFile({ fileName: file });
  if (process.env.PPTX_SKILL_DIR) {
    const { applyTheme } = require(path.join(process.env.PPTX_SKILL_DIR, 'scripts/apply_theme.js'));
    await applyTheme(file, THEME);
  }
  await patchTheme(file);
  console.log('wrote', file);
}

(async () => {
  const outDir = path.resolve(process.argv[2] || path.join(__dirname, '..'));
  const which = process.argv[3];
  for (const name of ['basic', 'advanced']) {
    if (which && which !== name) continue;
    await buildDeck(require('./' + name + '.js'), outDir);
  }
})().catch((e) => { console.error(e); process.exit(1); });
