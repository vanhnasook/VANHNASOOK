#!/usr/bin/env node
// Render index.html frame by frame with headless Chromium and encode with ffmpeg.
//
//   node tools/render.mjs                 full video -> build/video.mp4 (+ build/sfx.json)
//   node tools/render.mjs --stills 3,20.5 PNG stills at those seconds -> build/stills/
//   node tools/render.mjs --workers 3     parallel browser workers (default 3)
import { chromium } from 'playwright';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const argv = process.argv.slice(2);
const opt = (name, def) => { const i = argv.indexOf(`--${name}`); return i >= 0 ? argv[i + 1] : def; };

const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.css': 'text/css', '.json': 'application/json',
  '.woff2': 'font/woff2', '.woff': 'font/woff', '.jpg': 'image/jpeg', '.png': 'image/png', '.svg': 'image/svg+xml', '.wav': 'audio/wav' };

function serve() {
  const server = http.createServer((req, res) => {
    const p = path.join(ROOT, decodeURIComponent(new URL(req.url, 'http://x').pathname));
    if (!p.startsWith(ROOT) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); res.end(); return; }
    res.writeHead(200, { 'Content-Type': MIME[path.extname(p)] || 'application/octet-stream' });
    fs.createReadStream(p).pipe(res);
  });
  return new Promise((r) => server.listen(0, '127.0.0.1', () => r(server)));
}

async function openPage(browser, port) {
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  page.on('pageerror', (e) => { console.error('page error:', e.message); process.exitCode = 1; });
  page.on('console', (m) => { if (m.type() === 'error') console.error('console:', m.text()); });
  await page.goto(`http://127.0.0.1:${port}/index.html?render`);
  await page.evaluate(() => window.__ready);
  return page;
}

async function renderChunk(browser, port, from, to, fps, out, progress) {
  const page = await openPage(browser, port);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'mjpeg', '-i', '-',
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-pix_fmt', 'yuv420p', '-r', String(fps), out], { stdio: ['pipe', 'inherit', 'inherit'] });
  for (let f = from; f < to; f++) {
    await page.evaluate((t) => window.__seek(t), f / fps);
    const buf = await page.screenshot({ type: 'jpeg', quality: 94 });
    if (!ff.stdin.write(buf)) await once(ff.stdin, 'drain');
    progress();
  }
  ff.stdin.end();
  const [code] = await once(ff, 'close');
  if (code) throw new Error(`ffmpeg exited ${code}`);
  await page.close();
}

const server = await serve();
const port = server.address().port;
const browser = await chromium.launch({ args: ['--font-render-hinting=none', '--disable-lcd-text'] });
try {
  if (opt('stills')) {
    const page = await openPage(browser, port);
    fs.mkdirSync(path.join(ROOT, 'build/stills'), { recursive: true });
    for (const t of opt('stills').split(',').map(Number)) {
      await page.evaluate((x) => window.__seek(x), t);
      const file = path.join(ROOT, `build/stills/t${t.toFixed(2).padStart(6, '0')}.png`);
      await page.screenshot({ path: file });
      console.log(file);
    }
  } else {
    const probe = await openPage(browser, port);
    const { duration, sfx } = await probe.evaluate(() => ({ duration: window.__duration, sfx: window.__sfx }));
    await probe.close();
    fs.writeFileSync(path.join(ROOT, 'build/sfx.json'), JSON.stringify(sfx, null, 1));
    const fps = 30, total = Math.round(duration * fps), workers = +opt('workers', 3);
    const segDir = path.join(ROOT, 'build/segments');
    fs.rmSync(segDir, { recursive: true, force: true });
    fs.mkdirSync(segDir, { recursive: true });
    let done = 0;
    const t0 = Date.now();
    const tick = () => {
      if (++done % 150 === 0 || done === total) {
        const el = (Date.now() - t0) / 1000;
        console.log(`frames ${done}/${total}  ${el.toFixed(0)}s elapsed, ~${((total - done) * el / done).toFixed(0)}s left`);
      }
    };
    const size = Math.ceil(total / workers);
    const segs = [];
    await Promise.all(Array.from({ length: workers }, (_, k) => {
      const out = path.join(segDir, `seg${k}.mp4`);
      segs.push(out);
      return renderChunk(browser, port, k * size, Math.min(total, (k + 1) * size), fps, out, tick);
    }));
    fs.writeFileSync(path.join(segDir, 'list.txt'), segs.map((s) => `file '${s}'`).join('\n'));
    const cat = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', path.join(segDir, 'list.txt'), '-c', 'copy',
      path.join(ROOT, 'build/video.mp4')], { stdio: 'inherit' });
    const [code] = await once(cat, 'close');
    if (code) throw new Error('concat failed');
    console.log(`build/video.mp4 (${total} frames, ${duration}s)`);
  }
} finally {
  await browser.close();
  server.close();
}
