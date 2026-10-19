// Motion-graphic tutorial: how to send feedback / report a problem on lap.com.la.
// Everything is driven by one paused GSAP timeline plus "updaters" (pure functions
// of time), so tools/render.mjs can seek to any frame and get the same picture.
import { icon, HAND } from './icons.js';

gsap.registerPlugin(MotionPathPlugin);
gsap.config({ force3D: false }); // keep 2D transforms so zoomed screenshots stay sharp

const T = window.TIMELINE;
const RENDER = new URLSearchParams(location.search).has('render');
const sc = Object.fromEntries(T.scenes.map((s) => [s.id, s]));
const L = (id, i) => sc[id].lines[i];
const $ = (s, root = document) => root.querySelector(s);
const $$ = (s, root = document) => [...root.querySelectorAll(s)];

// Phone geometry: screenshots are 1260x2630, shown 380px wide inside the phone.
const S = 380 / 1260, PX = 316, PY = 92, BZ = 14, SB = 34;
const CX = 560, CY = 455; // where the camera puts its focus point on stage
const local = (ix, iy) => [PX + BZ + ix * S, PY + BZ + SB + iy * S];

const tl = gsap.timeline({ paused: true });
const updaters = [];
const sfxCues = [];
const sfx = (t, name, gain = 1) => sfxCues.push({ t: +t.toFixed(3), name, gain });

// Time at which `sub` is spoken in a caption line (by character position).
function at(line, sub, frac = 0) {
  const i = line.lo.indexOf(sub);
  if (i < 0) throw new Error(`cue "${sub}" not found in "${line.lo}"`);
  return line.start + ((i + frac * sub.length) / line.lo.length) * (line.end - line.start);
}

function rng(seed) { return () => ((seed = (seed * 16807) % 2147483647) - 1) / 2147483646; }
const clamp01 = (x) => Math.max(0, Math.min(1, x));
const esc = (s) => s.replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' })[c]);

/* ------------------------------------------------------------------ DOM */

function buildBackground() {
  $('#bg').innerHTML = `<svg width="1920" height="1080" viewBox="0 0 1920 1080">
    <defs>
      <pattern id="dotp" width="26" height="26" patternUnits="userSpaceOnUse"><circle cx="3" cy="3" r="3" fill="#ffffff"/></pattern>
      <radialGradient id="goldg"><stop offset="0" stop-color="#ffffff" stop-opacity=".55"/><stop offset="1" stop-color="#ffffff" stop-opacity="0"/></radialGradient>
      <radialGradient id="blueg"><stop offset="0" stop-color="#fff3c4" stop-opacity=".8"/><stop offset="1" stop-color="#fff3c4" stop-opacity="0"/></radialGradient>
    </defs>
    <g class="drift" data-a="22" data-s=".11" data-p="0"><circle cx="1400" cy="520" r="620" fill="url(#goldg)"/></g>
    <g class="drift" data-a="18" data-s=".07" data-p="9"><circle cx="1860" cy="1060" r="300" fill="#f0a800" opacity=".35"/></g>
    <g class="drift" data-a="18" data-s=".08" data-p="2"><circle cx="160" cy="140" r="380" fill="url(#blueg)"/></g>
    <g class="drift" data-a="12" data-s=".14" data-p="1"><circle cx="120" cy="330" r="130" fill="none" stroke="#ffffff" stroke-width="4" stroke-dasharray="3 16" stroke-linecap="round" opacity=".9"/></g>
    <g class="drift" data-a="16" data-s=".1" data-p="4"><circle cx="880" cy="980" r="70" fill="none" stroke="#ffffff" stroke-width="3" opacity=".5"/></g>
    <g class="drift" data-a="10" data-s=".12" data-p="3"><rect x="1560" y="760" width="290" height="190" fill="url(#dotp)" opacity=".45"/></g>
    <g class="drift" data-a="10" data-s=".09" data-p="5"><rect x="70" y="560" width="210" height="300" fill="url(#dotp)" opacity=".4"/></g>
    <g class="drift" data-a="20" data-s=".17" data-p="6" stroke="#ffffff" stroke-width="5" stroke-linecap="round"><path d="M920 120v34M903 137h34"/></g>
    <g class="drift" data-a="20" data-s=".15" data-p="7" stroke="#007dc5" stroke-width="4" stroke-linecap="round" opacity=".55"><path d="M1860 560v26M1847 573h26"/></g>
    <g class="drift" data-a="14" data-s=".2" data-p="8"><circle cx="230" cy="1000" r="10" fill="#007dc5" opacity=".6"/></g>
  </svg>`;
  const groups = $$('#bg .drift');
  updaters.push((t) => {
    for (const g of groups) {
      const a = +g.dataset.a, s = +g.dataset.s, p = +g.dataset.p;
      g.setAttribute('transform', `translate(${(Math.sin(t * s * 6.28 * .25 + p) * a).toFixed(2)} ${(Math.cos(t * s * 6.28 * .2 + p) * a * .7).toFixed(2)})`);
    }
  });
}

function buildPhone() {
  const statusIcons = `
    <svg width="20" height="14" viewBox="0 0 20 14" fill="#fff"><rect x="0" y="9" width="3.5" height="5" rx="1"/><rect x="5.5" y="6" width="3.5" height="8" rx="1"/><rect x="11" y="3" width="3.5" height="11" rx="1"/><rect x="16.5" y="0" width="3.5" height="14" rx="1"/></svg>
    <svg width="18" height="14" viewBox="0 0 18 14" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round"><path d="M1.5 5a11 11 0 0 1 15 0M4.5 8.2a6.5 6.5 0 0 1 9 0"/><circle cx="9" cy="11.5" r="1.4" fill="#fff" stroke="none"/></svg>
    <svg width="26" height="14" viewBox="0 0 26 14"><rect x=".8" y=".8" width="21" height="12.4" rx="3" fill="none" stroke="#fff" stroke-width="1.6"/><rect x="3" y="3" width="14" height="8" rx="1.5" fill="#fff"/><rect x="23" y="4.5" width="2.4" height="5" rx="1" fill="#fff"/></svg>`;
  $('#cam').innerHTML = `
    <div id="phone" style="left:${PX}px;top:${PY}px">
      <div class="bezel"></div>
      <div class="btn" style="right:-3px;top:170px;height:66px"></div>
      <div class="btn" style="right:-3px;top:262px;height:110px"></div>
      <div class="screen">
        <div class="statusbar"><span>12:17</span><span class="r">${statusIcons}</span></div>
        <div class="punch"></div>
        <div id="viewport">
          <img id="imgHome" src="assets/screens/home.jpg" alt="">
          <div id="backdrop"></div>
          <img id="imgForm" src="assets/screens/form.jpg" alt="">
          <div class="coord" id="ov" style="transform:scale(${S})">
            <div class="typed" id="tSubject" style="left:105px;top:1531px;width:1052px;height:118px;padding:21px 0 0 38px"></div>
            <div class="typed" id="tDetail" style="left:103px;top:1803px;width:1054px;height:292px;padding:20px 40px 0 40px"></div>
            <svg width="1260" height="2630" viewBox="0 0 1260 2630">
              <defs><mask id="spotMask" maskUnits="userSpaceOnUse" x="0" y="0" width="1260" height="2630">
                <rect width="1260" height="2630" fill="#fff"/><rect id="hole" x="0" y="0" width="1260" height="2630" rx="44" fill="#000"/>
              </mask></defs>
              <rect id="dim" width="1260" height="2630" fill="#06162e" fill-opacity=".62" mask="url(#spotMask)" opacity="0"/>
              <g id="rings"></g>
            </svg>
          </div>
        </div>
      </div>
      <div class="coord" id="fx" style="left:${BZ}px;top:${BZ + SB}px;transform:scale(${S})">
        <svg id="fxsvg" width="1260" height="2630"></svg>
        <div id="hand"><svg viewBox="0 0 24 24"><path d="${HAND}" fill="#fff" stroke="#08355e" stroke-width=".75" stroke-linejoin="round"/></svg></div>
      </div>
    </div>`;
  gsap.set('#phone', { y: 980, rotation: 10, transformOrigin: '50% 100%' });
  gsap.set('#imgForm', { y: 800 });
  gsap.set('#hand', { x: 1500, y: 2900, autoAlpha: 0, transformOrigin: '81px 44px' });
  gsap.set(['#tSubject', '#tDetail'], { opacity: 0 });
}

const head = (n) => `<div class="stepHead in"><div class="num">${n}</div><div class="kick">ຂັ້ນຕອນທີ ${n}<small>Step ${n} of 7</small></div></div>`;
const card = (ic, text, cls = '') => `<div class="card ${cls}"><div class="ci">${icon(ic)}</div><div>${text}</div><div class="tick">${icon('check')}</div></div>`;

function buildPanels() {
  $('#panel').innerHTML = `
  <div class="pnl" id="p-step1">
    ${head(1)}
    <h1 class="ttl in">ເປີດເວັບໄຊ <span class="url">lap.com.la</span></h1>
    <div class="body">
      <div class="browser in"><div class="top"><i></i><i></i><i></i></div>
        <div class="bar">${icon('lock')}<span id="urlTyped"></span></div></div>
      <div class="devices">${card('phone', 'ໂທລະສັບ', 'later dev1')}${card('laptop', 'ຄອມພິວເຕີ', 'later dev2')}</div>
    </div>
  </div>

  <div class="pnl" id="p-step2">
    ${head(2)}
    <h1 class="ttl in">ກົດປຸ່ມ <span class="hl">“ແຈ້ງບັນຫາ / ຄຳເຫັນ”</span></h1>
    <div class="cornerDemo">
      <div class="miniPhone later" id="mini">
        <div class="ln" style="top:30px;width:90px"></div><div class="ln" style="top:54px;width:60px"></div>
        <div class="ln" style="top:96px;width:104px"></div><div class="ln" style="top:120px;width:80px"></div>
        <div class="dot" id="miniDot"></div>
      </div>
      <div class="stack">
        <div class="fab later" id="fab"><div class="ci">${icon('chat')}</div>ແຈ້ງບັນຫາ / ຄຳເຫັນ</div>
        <div class="sub later" id="cornerTxt" style="font-size:34px;font-weight:700;color:var(--ink)">${icon('arrowRight', '', 'style="display:inline;font-size:30px;vertical-align:-4px;color:var(--logo-blue);transform:rotate(45deg)"')} ຢູ່ມຸມຂວາລຸ່ມຂອງໜ້າຈໍ</div>
      </div>
    </div>
  </div>

  <div class="pnl" id="p-form">
    <div class="pill blue in">${icon('chat')} ໜ້າຕ່າງຟອມ</div>
    <h1 class="ttl in" style="font-size:56px;margin-top:22px">ກ່ອງຮັບຄຳຄິດເຫັນ &amp; ແຈ້ງບັນຫາ</h1>
    <div class="sub latin in">Anonymous Feedback &amp; Report</div>
    <div class="body" style="margin-top:28px">
      <div class="anon later" id="anon">
        <div class="bigShield"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
          <path id="shieldPath" pathLength="1" d="M12 2.5l8 3v6c0 5-3.4 8.6-8 10-4.6-1.4-8-5-8-10v-6z" fill="#eaf1ff"/>
          <g id="shieldLock"><rect x="8.5" y="11" width="7" height="5.5" rx="1.2" fill="#225bde" stroke="#225bde"/><path d="M10 11V9.5a2 2 0 0 1 4 0V11" stroke="#225bde"/></g></svg></div>
        <div class="badges"><div class="pill gold later" id="b100">${icon('shieldCheck')} ປອດໄພ 100%</div><div class="pill blue later" id="bAnon">${icon('eyeOff')} ບໍ່ລະບຸຕົວຕົນ</div></div>
      </div>
      <div class="noRec">
        <div class="card later" id="nrName"><div class="ci">${icon('user')}</div><div class="what">ຊື່<div class="strike"></div></div><div class="no">ບໍ່ບັນທຶກ</div></div>
        <div class="card later" id="nrMail"><div class="ci">${icon('mail')}</div><div class="what">ອີເມວ<div class="strike"></div></div><div class="no">ບໍ່ບັນທຶກ</div></div>
      </div>
      <div class="who2">${card('users', 'ລູກຄ້າ', 'later w2a')}${card('badge', 'ພະນັກງານ', 'later w2b')}</div>
    </div>
  </div>

  <div class="pnl" id="p-step3">
    ${head(3)}
    <h1 class="ttl in">ທ່ານແມ່ນໃຜ?</h1>
    <div class="body stack">
      ${card('user', 'ລູກຄ້າ / ຜູ້ໃຊ້ບໍລິການ', 'in o1')}
      ${card('badge', 'ພະນັກງານ LAP', 'in o2')}
      ${card('globe', 'ບຸກຄົນທົ່ວໄປ', 'in o3')}
    </div>
  </div>

  <div class="pnl" id="p-step4">
    ${head(4)}
    <h1 class="ttl in">ເລືອກປະເພດເລື່ອງ <span class="req">*</span></h1>
    <div class="body grid2">
      ${card('bulb', 'ຄຳຕິຊົມ / ສະເໜີແນະ', 'later t1')}
      ${card('warning', 'ແຈ້ງບັນຫາລະບົບ/ບໍລິການ', 'later t2')}
      ${card('megaphone', 'ແຈ້ງຂໍ້ຮ້ອງຮຽນ / ພຶດຕິກຳ', 'later t3')}
      ${card('dots', 'ອື່ນໆ', 'later t4')}
    </div>
  </div>

  <div class="pnl" id="p-step5">
    ${head(5)}
    <h1 class="ttl in">ຂຽນຫົວຂໍ້ ແລະ ລາຍລະອຽດ</h1>
    <div class="body stack">
      ${card('pencil', 'ຫົວຂໍ້ເລື່ອງສັ້ນໆ <span style="color:var(--muted);font-weight:500">(ຖ້າມີ)</span>', 'later d0')}
      <div class="grid2" style="grid-template-columns:1fr 1fr 1fr">
        ${card('calendar', 'ເຫດການ', 'later d1')}${card('pin', 'ສະຖານທີ່', 'later d2')}${card('bulb', 'ຂໍ້ສະເໜີ', 'later d3')}
      </div>
    </div>
    <div class="note later" id="reqNote"><span style="font-size:44px;line-height:0">*</span> ຈຳເປັນຕ້ອງປ້ອນຂໍ້ມູນ</div>
  </div>

  <div class="pnl" id="p-step6">
    ${head(6)}
    <h1 class="ttl in">ແນບຮູບພາບ ຫຼື ເອກະສານ</h1>
    <div class="sub in">ຖ້າມີຫຼັກຖານ (ບໍ່ບັງຄັບ)</div>
    <div class="body">
      <div class="uploadDemo in" id="upDemo">
        ${icon('upload', 'big')}
        <div class="lbl">ຄລິກເພື່ອແນບຮູບພາບ ຫຼື ໄຟລ໌</div>
        <div class="flyFile" id="ff1" style="color:#17a673">${icon('image')}</div>
        <div class="flyFile" id="ff2" style="color:#e5484d">${icon('file')}</div>
      </div>
      <div class="meter later" id="meter"><span>ສູງສຸດ</span><div class="track"><div class="fill" id="meterFill"></div></div><span class="latin">10 MB</span></div>
    </div>
  </div>

  <div class="pnl" id="p-step7">
    ${head(7)}
    <h1 class="ttl in">ກົດປຸ່ມ <span class="hl">“ສົ່ງຂໍ້ມູນ”</span></h1>
    <div class="body">
      <div class="sendBtn in" id="sendBtn">${icon('send')} ສົ່ງຂໍ້ມູນ</div>
      <div class="success later" id="success">
        <div class="circle" id="successCircle">${icon('check')}</div>
        <div><div class="t1">ຂອບໃຈສຳລັບຄຳຄິດເຫັນ!</div><div class="t2">Thank you for your feedback</div></div>
      </div>
    </div>
  </div>`;

  $('#contacts').innerHTML = `
    <h2>ຊ່ອງທາງຕິດຕໍ່ອື່ນ</h2>
    <div class="row">
      <div class="ccard" id="cc1" style="--c:#0b4f8c"><div class="ci">${icon('headset')}</div><div class="k">ສາຍດ່ວນ 24 ຊົ່ວໂມງ</div><div class="v">1819</div></div>
      <div class="ccard" id="cc2" style="--c:#1fb855"><div class="ci">${icon('whatsapp')}</div><div class="k latin">WhatsApp</div><div class="v sm">020 9855 6666</div></div>
      <div class="ccard" id="cc3" style="--c:#f0a800"><div class="ci">${icon('globe')}</div><div class="k">ເວັບໄຊ</div><div class="v sm">lap.com.la</div></div>
    </div>`;

  $('#plane').innerHTML = icon('send');
  $$('.later').forEach((e) => gsap.set(e, { autoAlpha: 0, y: 24, scale: .9 }));
}

function buildHud() {
  const nodes = [1, 2, 3, 4, 5, 6, 7].map((n) => `<div class="n" data-n="${n}"><b>${n}</b>${icon('check')}</div>`).join('<div class="l"><i></i></div>');
  $('#hud').innerHTML = `
    <div id="logoPill"><img src="assets/logo.svg" alt=""></div>
    <div id="tracker">${nodes}</div>`;
  const stepOf = { step1: 1, step2: 2, form: 2, step3: 3, step4: 4, step5: 5, step6: 6, step7: 7, outro: 8 };
  const ns = $$('#tracker .n'), ls = $$('#tracker .l i');
  const done7 = L('step7', 1).start - .1;
  let last = -1;
  updaters.push((t) => {
    const s = T.scenes.filter((x) => t >= x.start - .3).pop();
    let cur = stepOf[s.id] || 0;
    if (t >= done7) cur = 8;
    if (cur === last) return;
    last = cur;
    ns.forEach((n, i) => { n.classList.toggle('done', i + 1 < cur); n.classList.toggle('cur', i + 1 === cur); });
    ls.forEach((l, i) => { l.style.transform = `scaleX(${i + 2 <= cur ? 1 : 0})`; });
  });
}

function buildIntro() {
  const r = rng(7);
  const dots = Array.from({ length: 46 }, () => ({ x: r() * 1920, y: r() * 1080, s: 2 + r() * 5, v: 20 + r() * 50, p: r() * 6 }));
  $('#intro').innerHTML = `
    <svg class="fx" width="1920" height="1080">${[0, 1, 2, 3].map(() => '<circle class="rg" cx="960" cy="320" fill="none" stroke="#ffffff" stroke-width="3"/>').join('')}
      ${dots.map(() => '<circle class="pt" fill="#ffffff"/>').join('')}</svg>
    <div class="logoDisc" id="iLogo" style="top:130px"><img src="assets/logo.svg" alt=""></div>
    <div class="introTitle" id="iTitle" style="top:575px">ວິທີແຈ້ງບັນຫາ <span class="g">ແລະ</span> ສົ່ງຄຳຄິດເຫັນ</div>
    <div class="underline" id="iLine" style="top:700px"></div>
    <div class="urlPill" id="iUrl" style="top:740px">${icon('globe')} ຜ່ານເວັບໄຊ lap.com.la</div>
    <div class="improve">
      <div class="it" id="im1"><div class="c">${icon('chat')}</div>ຄຳຄິດເຫັນ</div>
      <div class="ar" id="ia1">${icon('arrowRight')}</div>
      <div class="it" id="im2"><div class="c">${icon('growth')}</div>ປັບປຸງ</div>
      <div class="ar" id="ia2">${icon('arrowRight')}</div>
      <div class="it" id="im3"><div class="c">${icon('star')}</div>ບໍລິການດີຂຶ້ນ</div>
    </div>`;
  $('#endcard').innerHTML = `
    <svg class="fx" width="1920" height="1080">${[0, 1, 2, 3].map(() => '<circle class="rg" cx="960" cy="320" fill="none" stroke="#ffffff" stroke-width="3"/>').join('')}</svg>
    <div class="logoDisc" id="eLogo" style="top:130px"><img src="assets/logo.svg" alt=""></div>
    <div class="slogan" id="eSlogan" style="top:590px"><div class="lo">ຄຽງຄູ່ທ່ານ ຕະຫຼອດເວລາ</div><div class="en">Always beside you</div></div>
    <div class="endInfo" id="eInfo"><span>${icon('globe')} lap.com.la</span><span>${icon('headset')} ສາຍດ່ວນ 1819</span><span>${icon('whatsapp')} 020 9855 6666</span></div>`;

  // expanding rings + rising sparkles, as pure functions of time
  for (const layer of ['#intro', '#endcard']) {
    const rings = $$(`${layer} .rg`), pts = $$(`${layer} .pt`);
    updaters.push((t) => {
      rings.forEach((c, k) => {
        const f = ((t * .22 + k / rings.length) % 1);
        c.setAttribute('r', (200 + f * 900).toFixed(1));
        c.setAttribute('opacity', ((1 - f) * .35).toFixed(3));
      });
      pts.forEach((c, k) => {
        const d = dots[k];
        const y = ((d.y - t * d.v) % 1080 + 1080) % 1080;
        c.setAttribute('cx', (d.x + Math.sin(t * .8 + d.p) * 14).toFixed(1));
        c.setAttribute('cy', y.toFixed(1));
        c.setAttribute('r', d.s.toFixed(1));
        c.setAttribute('opacity', (.25 + .35 * Math.sin(t * 2 + d.p) ** 2).toFixed(2));
      });
    });
  }
  gsap.set('#iLogo', { scale: 0 });
  gsap.set(['#iTitle', '#iUrl'], { autoAlpha: 0, y: 40 });
  gsap.set('#iUrl', { xPercent: -50, x: 0, left: '50%' });
  gsap.set(['#im1', '#im2', '#im3'], { autoAlpha: 0, scale: .6, y: 30 });
  gsap.set(['#ia1', '#ia2'], { autoAlpha: 0, x: -20 });
  gsap.set('#endcard', { clipPath: 'circle(0% at 50% 50%)' });
  gsap.set('#intro', { clipPath: 'circle(80% at 50% 50%)' });
  gsap.set(['#eLogo'], { scale: 0 });
  gsap.set(['#eSlogan', '#eInfo'], { autoAlpha: 0, y: 40 });
  gsap.set('#contacts', { autoAlpha: 0 });
  gsap.set(['#cc1', '#cc2', '#cc3'], { autoAlpha: 0, y: 60, scale: .9 });
  gsap.set('#plane', { autoAlpha: 0 });
}

function buildCaptions() {
  const cap = $('#captions .cap');
  const lines = T.scenes.flatMap((s) => s.lines);
  // lines closer than 0.7s share one caption box that stays up while the text changes
  const groups = [];
  lines.forEach((l, i) => {
    if (i && l.start - lines[i - 1].end < .7) groups.at(-1).push(l); else groups.push([l]);
  });
  const spans = groups.map((g) => ({ show: g[0].start - .12, hide: g.at(-1).end + .35, g }));
  updaters.push((t) => {
    const sp = spans.find((s) => t >= s.show && t < s.hide);
    if (!sp) { cap.style.opacity = 0; return; }
    const line = sp.g.filter((l) => t >= l.start - .12).pop() || sp.g[0];
    if (cap.textContent !== line.lo) cap.textContent = line.lo;
    const a = clamp01(Math.min((t - sp.show) / .18, (sp.hide - t) / .18));
    cap.style.opacity = a;
    cap.style.transform = `translateY(${((1 - a) * 14).toFixed(1)}px)`;
  });
}

/* ------------------------------------------------------------ helpers */

function camTo(ix, iy, z, t, dur = 1.1) {
  const [lx, ly] = local(ix, iy);
  // keep the zoomed phone clear of the right-hand panel
  const shift = Math.min(0, 930 - (CX + z * (PX + 408 - lx)));
  tl.to('#cam', { x: CX + shift - z * lx, y: CY - z * ly, scale: z, duration: dur, ease: 'power3.inOut' }, t);
  sfx(t, 'whoosh', .55);
  return { ix, iy, z, shift };
}
function camHome(t, dur = 1) {
  tl.to('#cam', { x: 0, y: 0, scale: 1, duration: dur, ease: 'power3.inOut' }, t);
  sfx(t, 'whoosh', .45);
}
// stage position of an image point for a given camera
function onStage(cam, ix, iy) {
  const [lx, ly] = local(ix, iy), [cx, cy] = local(cam.ix, cam.iy);
  return [CX + cam.shift + cam.z * (lx - cx), CY + cam.z * (ly - cy)];
}

function spot([x1, y1, x2, y2], t, dur = .7, rx = 44) {
  tl.to('#hole', { attr: { x: x1, y: y1, width: x2 - x1, height: y2 - y1, rx }, duration: dur, ease: 'power3.inOut' }, t);
  tl.to('#dim', { opacity: 1, duration: .5, ease: 'power1.out' }, t);
}
function spotOff(t) {
  tl.to('#dim', { opacity: 0, duration: .45 }, t);
}

const NS = 'http://www.w3.org/2000/svg';
function svgEl(parent, tag, attrs) {
  const e = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  parent.appendChild(e);
  return e;
}

// Gold outline that draws itself around a box, optionally pulses, then fades.
function ring([x1, y1, x2, y2], t, { hold = 1.6, pad = 10, rx, pulse = true, color = '#fec215' } = {}) {
  const g = svgEl($('#rings'), 'g', {});
  const box = { x: x1 - pad, y: y1 - pad, width: x2 - x1 + 2 * pad, height: y2 - y1 + 2 * pad, rx: rx ?? Math.min(60, (y2 - y1) / 2 + pad) };
  const glow = svgEl(g, 'rect', { ...box, fill: 'none', stroke: color, 'stroke-width': 26, opacity: 0 });
  const line = svgEl(g, 'rect', { ...box, fill: 'none', stroke: color, 'stroke-width': 10, pathLength: 1, 'stroke-dasharray': '1 1', 'stroke-dashoffset': 1, 'stroke-linecap': 'round' });
  tl.to(line, { attr: { 'stroke-dashoffset': 0 }, duration: .55, ease: 'power2.inOut' }, t);
  if (pulse) {
    tl.to(glow, { opacity: .35, duration: .3 }, t + .4);
    tl.to(glow, { opacity: .08, duration: .45, repeat: Math.max(1, Math.round(hold / .45) - 1), yoyo: true, ease: 'sine.inOut' }, t + .7);
  }
  if (hold !== Infinity) tl.to(g, { opacity: 0, duration: .35 }, t + .55 + hold);
  return g;
}
function ringOff(g, t) { tl.to(g, { opacity: 0, duration: .35 }, t); }

function ripple(x, y, t) {
  for (let k = 0; k < 2; k++) {
    const c = svgEl($('#fxsvg'), 'circle', { cx: x, cy: y, r: 10, fill: 'none', stroke: k ? '#ffffff' : '#fec215', 'stroke-width': 12, opacity: 0 });
    tl.set(c, { opacity: 1 }, t + k * .12);
    tl.to(c, { attr: { r: 130 }, opacity: 0, duration: .7, ease: 'power2.out' }, t + k * .12);
  }
}

// Move the finger to (x, y) in screenshot coordinates and tap at time t.
function tap(x, y, t, { from = [x + 260, y + 420], travel = .75 } = {}) {
  tl.set('#hand', { x: from[0] - 81, y: from[1] - 44 }, t - travel - .05);
  tl.to('#hand', { autoAlpha: 1, duration: .25 }, t - travel - .05);
  tl.to('#hand', { x: x - 81, y: y - 44, duration: travel, ease: 'power2.out' }, t - travel);
  tl.to('#hand', { scale: .82, duration: .1, ease: 'power1.in' }, t - .08);
  tl.to('#hand', { scale: 1, duration: .25, ease: 'back.out(3)' }, t + .04);
  ripple(x, y, t);
  sfx(t, 'tap');
}
function handOut(t) {
  tl.to('#hand', { autoAlpha: 0, duration: .3 }, t);
}

function pop(sel, t, { sound = true } = {}) {
  tl.to(sel, { autoAlpha: 1, y: 0, scale: 1, duration: .55, ease: 'back.out(1.7)' }, t);
  if (sound) sfx(t, 'pop', .5);
}
function panelIn(id, t) {
  const p = $(`#p-${id}`);
  tl.set(p, { autoAlpha: 1 }, t);
  tl.fromTo($$('.in', p), { y: 46, autoAlpha: 0 }, { y: 0, autoAlpha: 1, duration: .65, stagger: .1, ease: 'power3.out', immediateRender: false }, t);
  sfx(t, 'swish', .45);
}
function panelOut(id, t) {
  tl.to(`#p-${id}`, { autoAlpha: 0, y: -34, duration: .4, ease: 'power2.in' }, t);
}
// highlight a panel card (gold border + glow) for a while
function cardOn(sel, t, hold = 1.4) {
  tl.to(sel, { boxShadow: '0 18px 40px rgba(0,125,197,.30), inset 0 0 0 5px #007dc5', scale: 1.03, duration: .3 }, t);
  if (hold !== Infinity) tl.to(sel, { boxShadow: '0 14px 34px rgba(150,95,0,.16), inset 0 0 0 2px rgba(255,255,255,0)', scale: 1, duration: .4 }, t + hold);
}
function tick(sel, t) {
  tl.fromTo(`${sel} .tick`, { autoAlpha: 0, scale: 0 }, { autoAlpha: 1, scale: 1, duration: .45, ease: 'back.out(2.5)', immediateRender: false }, t);
}

// Typewriter text driven by time (Lao is split into grapheme clusters).
function typing(elm, text, t0, t1, caretUntil) {
  const g = [...new Intl.Segmenter('lo', { granularity: 'grapheme' }).segment(text)].map((s) => s.segment);
  let last = '';
  updaters.push((t) => {
    const n = t < t0 ? 0 : t >= t1 ? g.length : Math.floor(((t - t0) / (t1 - t0)) * g.length);
    const caret = t >= t0 - .5 && t < caretUntil && ((t >= t0 && t < t1) || Math.floor(t * 2.4) % 2 === 0);
    const key = `${n}|${caret}`;
    if (key !== last) {
      elm.innerHTML = esc(g.slice(0, n).join('')) + (caret ? '<span class="caret"></span>' : '');
      last = key;
    }
  });
  for (let k = 0; k < g.length; k += 2) sfx(t0 + (k / g.length) * (t1 - t0), 'type', .3);
}

/* ------------------------------------------------------------- scenes */

function sceneIntro() {
  const s = sc.intro, l0 = L('intro', 0), l1 = L('intro', 1);
  tl.to('#iLogo', { scale: 1, duration: 1, ease: 'back.out(1.6)' }, .25);
  sfx(.2, 'rise', .8);
  tl.to('#iTitle', { autoAlpha: 1, y: 0, duration: .8, ease: 'power3.out' }, 1.0);
  tl.to('#iLine', { scaleX: 1, duration: .6, ease: 'power2.out' }, 1.45);
  tl.to('#iUrl', { autoAlpha: 1, y: 0, duration: .7, ease: 'power3.out' }, 1.8);
  sfx(1.8, 'pop', .5);
  tl.to(['#iTitle', '#iLine', '#iUrl'], { autoAlpha: 0, y: -40, duration: .5, ease: 'power2.in', stagger: .05 }, l1.start - .55);
  tl.to('#iLogo', { scale: .78, y: -40, duration: .8, ease: 'power3.inOut' }, l1.start - .55);
  pop('#im1', at(l1, 'ທຸກຄຳຄິດເຫັນ'));
  tl.to('#ia1', { autoAlpha: 1, x: 0, duration: .4 }, at(l1, 'ຊ່ວຍ'));
  pop('#im2', at(l1, 'ປັບປຸງ') - .1);
  tl.to('#ia2', { autoAlpha: 1, x: 0, duration: .4 }, at(l1, 'ການບໍລິການ') - .3);
  pop('#im3', at(l1, 'ການບໍລິການ'));
  // iris out to the main stage
  tl.to('#intro', { clipPath: 'circle(0% at 50% 50%)', duration: .9, ease: 'power3.in' }, s.end - .85);
  tl.set('#intro', { autoAlpha: 0 }, s.end + .06);
  sfx(s.end - .85, 'whoosh', .8);
  void l0;
}

function sceneStep1() {
  const s = sc.step1, l = L('step1', 0);
  tl.to('#logoPill', { opacity: 1, x: 0, duration: .6, ease: 'power3.out' }, s.start - .1);
  tl.to('#tracker', { opacity: 1, duration: .6 }, s.start + .1);
  tl.to('#phone', { y: 0, rotation: 0, duration: 1.3, ease: 'back.out(1.1)' }, s.start - .25);
  sfx(s.start - .25, 'whoosh', .7);
  panelIn('step1', s.start + .25);
  const t0 = at(l, 'lap.com.la') - .9;
  typing($('#urlTyped'), 'lap.com.la', t0, t0 + 1.1, s.end);
  const tz = at(l, 'ຜ່ານ') - .3;
  camTo(560, 330, 1.75, tz - .2, 1.1);
  ring([142, 26, 818, 146], tz + .7, { hold: 2.2 });
  pop('.dev1', at(l, 'ໂທລະສັບ'));
  pop('.dev2', at(l, 'ຄອມພິວເຕີ'));
  camHome(s.end - .9, 1);
}

function sceneStep2() {
  const s = sc.step2, l = L('step2', 0);
  panelOut('step1', s.start - .35);
  panelIn('step2', s.start + .1);
  camTo(880, 2330, 2.0, s.start, 1.2);
  spot([672, 2400, 1220, 2568], s.start + .8, .7, 84);
  ring([693, 2419, 1200, 2550], at(l, 'ກົດປຸ່ມ'), { hold: 3.4, pad: 14, rx: 80 });
  pop('#fab', at(l, 'ກົດປຸ່ມ'));
  pop('#mini', at(l, 'ມຸມຂວາລຸ່ມ') - .2);
  pop('#cornerTxt', at(l, 'ມຸມຂວາລຸ່ມ'));
  tl.to('#miniDot', { boxShadow: '0 0 0 18px rgba(0,125,197,0)', duration: .9, repeat: 3, ease: 'power1.out' }, at(l, 'ມຸມຂວາລຸ່ມ'));
  tap(946, 2485, l.end - .35, { travel: .8 });
  tl.to('#fab', { scale: .94, duration: .1, yoyo: true, repeat: 1 }, l.end - .4);
}

function sceneForm() {
  const s = sc.form, [l0, l1, l2] = sc.form.lines;
  handOut(s.start + .1);
  spotOff(s.start - .1);
  camHome(s.start + .05, 1);
  tl.to('#backdrop', { opacity: 1, duration: .4 }, s.start + .2);
  tl.to('#imgForm', { y: 0, duration: .75, ease: 'power3.out' }, s.start + .3);
  sfx(s.start + .3, 'swish', .6);
  panelOut('step2', s.start - .3);
  panelIn('form', s.start + .35);
  camTo(630, 300, 1.75, l0.start + .5, 1.1);
  spot([52, 168, 1208, 392], l0.start + 1.1, .6, 36);
  // anonymity notice
  camTo(630, 560, 1.9, l1.start - .35, 1.0);
  spot([86, 436, 1174, 638], l1.start - .1, .6, 40);
  pop('#anon', l1.start - .1);
  tl.fromTo('#shieldPath', { attr: { 'stroke-dasharray': '1 1', 'stroke-dashoffset': 1 } }, { attr: { 'stroke-dashoffset': 0 }, duration: .8, ease: 'power2.out', immediateRender: false }, l1.start);
  pop('#b100', at(l1, 'ປອດໄພ'));
  pop('#bAnon', at(l1, 'ບໍ່ລະບຸ'));
  pop('#nrName', at(l1, 'ບໍ່ມີການ') - .2);
  pop('#nrMail', at(l1, 'ບໍ່ມີການ') + .1);
  tl.to('#nrName .strike', { scaleX: 1, duration: .4, ease: 'power2.out' }, at(l1, 'ຊື່'));
  tl.to('#nrMail .strike', { scaleX: 1, duration: .4, ease: 'power2.out' }, at(l1, 'ອີເມວ'));
  sfx(at(l1, 'ຊື່'), 'tick', .5);
  sfx(at(l1, 'ອີເມວ'), 'tick', .5);
  pop('.w2a', at(l2, 'ລູກຄ້າ'));
  tick('.w2a', at(l2, 'ລູກຄ້າ') + .3);
  pop('.w2b', at(l2, 'ພະນັກງານ'));
  tick('.w2b', at(l2, 'ພະນັກງານ') + .3);
  ring([750, 546, 839, 592], at(l2, 'ລູກຄ້າ') - .1, { hold: s.end - at(l2, 'ລູກຄ້າ') - .9, pad: 8, pulse: false });
  ring([922, 548, 1087, 593], at(l2, 'ພະນັກງານ') - .1, { hold: s.end - at(l2, 'ພະນັກງານ') - .9, pad: 8, pulse: false });
}

function sceneStep3() {
  const s = sc.step3, [l0, l1] = s.lines;
  panelOut('form', s.start - .35);
  panelIn('step3', s.start + .1);
  camTo(560, 850, 2.05, s.start, 1.1);
  spot([70, 672, 978, 1030], s.start + .5, .7, 40);
  ring([86, 688, 330, 748], at(l0, '“ທ່ານ'), { hold: 1.6, pad: 10, rx: 20, pulse: false });
  const cues = [at(l1, 'ລູກຄ້າ'), at(l1, 'ພະນັກງານ'), at(l1, 'ບຸກຄົນ')];
  ring([97, 769, 552, 876], cues[0], { hold: 1.2 });
  ring([579, 769, 949, 876], cues[1], { hold: 1.2 });
  ring([97, 904, 437, 1008], cues[2], { hold: 1.0 });
  cardOn('#p-step3 .o1', cues[0], 1.3);
  cardOn('#p-step3 .o2', cues[1], 1.3);
  cardOn('#p-step3 .o3', cues[2], 1.0);
  const tt = l1.end + .25;
  tap(324, 822, tt, { travel: .7 });
  cardOn('#p-step3 .o1', tt, Infinity);
  tick('#p-step3 .o1', tt + .1);
  handOut(s.end - .2);
}

function sceneStep4() {
  const s = sc.step4, [l0, l1, l2] = s.lines;
  panelOut('step3', s.start - .35);
  panelIn('step4', s.start + .1);
  camTo(600, 1225, 2.0, s.start, 1.1);
  spot([70, 1048, 1118, 1402], s.start + .5, .7, 40);
  ring([86, 1058, 350, 1126], l0.start + .6, { hold: 1.6, pad: 10, rx: 20, pulse: false });
  const c = [at(l1, 'ຄຳຕິຊົມ'), at(l1, 'ແຈ້ງບັນຫາ'), at(l2, 'ແຈ້ງຂໍ້'), at(l2, 'ອື່ນໆ')];
  ring([97, 1144, 544, 1253], c[0], { hold: 1.4 });
  ring([571, 1144, 1092, 1253], c[1], { hold: 1.4 });
  ring([97, 1283, 627, 1386], c[2], { hold: 1.2 });
  ring([651, 1283, 873, 1386], c[3], { hold: .6 });
  ['.t1', '.t2', '.t3', '.t4'].forEach((k, i) => { pop(`#p-step4 ${k}`, c[i] - .1); cardOn(`#p-step4 ${k}`, c[i] + (i === 3 ? 0 : .3), i === 3 ? .4 : 1.1); });
  const tt = Math.max(l2.end + .5, c[3] + 1.15);
  tap(320, 1198, tt, { travel: .7 });
  cardOn('#p-step4 .t1', tt - .35, Infinity);
  tick('#p-step4 .t1', tt + .1);
  handOut(s.end - .2);
}

function sceneStep5() {
  const s = sc.step5, [l0, l1, l2] = s.lines;
  panelOut('step4', s.start - .35);
  panelIn('step5', s.start + .1);
  camTo(620, 1800, 1.8, s.start, 1.1);
  spot([70, 1428, 1190, 2168], s.start + .5, .7, 40);
  const t1 = at(l0, 'ໃສ່') + .1;
  tap(640, 1592, t1, { travel: .7 });
  tl.set('#tSubject', { opacity: 1 }, t1 + .05);
  typing($('#tSubject'), 'ຂໍ້ສະເໜີແນະການແຈ້ງເຕືອນ', t1 + .3, l0.end + .25, l1.start + .1);
  pop('#p-step5 .d0', t1);
  const t2 = l1.start + .1;
  tap(640, 1900, t2, { travel: .5, from: [700, 1700] });
  tl.set('#tDetail', { opacity: 1 }, t2 + .05);
  typing($('#tDetail'), 'ຢາກໃຫ້ມີການແຈ້ງເຕືອນຜ່ານ SMS ກ່ອນສັນຍາປະກັນໄພໝົດອາຍຸ', t2 + .35, l1.end + .3, s.end);
  handOut(t2 + .6);
  pop('#p-step5 .d1', at(l1, 'ເຫດການ'));
  pop('#p-step5 .d2', at(l1, 'ສະຖານທີ່'));
  pop('#p-step5 .d3', at(l1, 'ຂໍ້ສະເໜີ'));
  ring([380, 1712, 440, 1768], l2.start + .2, { hold: 2.4, pad: 12, rx: 40, color: '#e5484d' });
  pop('#reqNote', at(l2, 'ດາວ'));
}

function sceneStep6() {
  const s = sc.step6, l = L('step6', 0);
  panelOut('step5', s.start - .35);
  panelIn('step6', s.start + .1);
  spotOff(s.start - .1);
  camTo(620, 2330, 2.0, s.start, 1.1);
  spot([84, 2216, 1176, 2430], s.start + .5, .7, 36);
  const tu = at(l, 'ສາມາດແນບ');
  tap(560, 2380, tu, { travel: .7 });
  handOut(tu + .6);
  // two documents fly into the phone's upload box
  const fx = $('#fx');
  [['image', '#17a673', 1500, 2050, 470], ['file', '#e5484d', 1500, 2250, 720]].forEach(([ic, col, x, y, tx], k) => {
    const d = document.createElement('div');
    d.className = 'flyFile';
    d.style.cssText = `width:190px;height:220px;font-size:110px;color:${col};border-radius:30px;left:0;top:0`;
    d.innerHTML = icon(ic);
    fx.appendChild(d);
    gsap.set(d, { x, y, autoAlpha: 0, rotation: 12 });
    const t0 = tu + .5 + k * .35;
    tl.to(d, { autoAlpha: 1, duration: .2 }, t0);
    tl.to(d, { x: tx, y: 2265, rotation: 0, scale: .55, duration: .8, ease: 'power2.inOut' }, t0);
    tl.to(d, { autoAlpha: 0, duration: .25 }, t0 + .75);
  });
  // panel: files drop into the upload area
  gsap.set('#ff1', { x: 40, y: -300, autoAlpha: 0, rotation: -24 });
  gsap.set('#ff2', { x: 610, y: -320, autoAlpha: 0, rotation: 24 });
  [['#ff1', at(l, 'ຮູບພາບ'), -8], ['#ff2', at(l, 'ເອກະສານ'), 8]].forEach(([id, t, rot]) => {
    tl.to(id, { autoAlpha: 1, duration: .15 }, t);
    tl.to(id, { y: 70, rotation: rot, duration: .8, ease: 'bounce.out' }, t);
    sfx(t + .45, 'drop', .5);
  });
  tl.to('#upDemo .big', { scale: 1.18, duration: .2, yoyo: true, repeat: 1, ease: 'power1.out' }, at(l, 'ເອກະສານ') + .5);
  pop('#meter', at(l, 'ສູງສຸດ') - .2);
  tl.to('#meterFill', { scaleX: 1, duration: 1.1, ease: 'power2.out' }, at(l, 'ສູງສຸດ'));
}

function sceneStep7() {
  const s = sc.step7, [l0, l1] = s.lines;
  panelOut('step6', s.start - .35);
  panelIn('step7', s.start + .1);
  const cam = camTo(800, 2330, 2.2, s.start, 1.1);
  spot([826, 2454, 1178, 2610], s.start + .5, .7, 40);
  const tt = at(l0, '“ສົ່ງຂໍ້ມູນ”') + .35;
  ring([837, 2467, 1164, 2597], tt - 1.2, { hold: 1.4, pad: 10, rx: 34 });
  tap(1000, 2532, tt, { travel: .8 });
  tl.to('#sendBtn', { scale: .93, duration: .1, yoyo: true, repeat: 1 }, tt - .05);
  handOut(tt + .5);
  // paper plane flies from the phone button to the success badge
  const [sx, sy] = onStage(cam, 1000, 2532);
  gsap.set('#success', { y: 0, scale: 1 }); // measure the badge where it will land
  const sb = $('#successCircle').getBoundingClientRect(), st = $('#stage').getBoundingClientRect();
  gsap.set('#success', { y: 24, scale: .9 });
  const k = st.width / 1920;
  const ex = (sb.left - st.left) / k + sb.width / k / 2, ey = (sb.top - st.top) / k + sb.height / k / 2;
  const tf = tt + .25;
  tl.set('#plane', { x: sx - 45, y: sy - 45, autoAlpha: 1, scale: .6 }, tf);
  tl.to('#plane', {
    motionPath: { path: [{ x: sx + 120, y: sy - 260 }, { x: (sx + ex) / 2 + 80, y: Math.min(sy, ey) - 300 }, { x: ex - 45, y: ey - 45 }], curviness: 1.3, autoRotate: 45 },
    scale: 1.1, duration: 1.15, ease: 'power1.inOut',
  }, tf);
  tl.to('#plane', { autoAlpha: 0, scale: .4, duration: .2 }, tf + 1.1);
  sfx(tf, 'swoosh', .8);
  pop('#success', tf + 1.05, { sound: false });
  tl.fromTo('#successCircle', { scale: .3 }, { scale: 1, duration: .7, ease: 'elastic.out(1, .5)', immediateRender: false }, tf + 1.05);
  sfx(tf + 1.05, 'chime', .9);
}

function sceneOutro() {
  const s = sc.outro, [l0, l1, l2] = s.lines;
  panelOut('step7', s.start - .35);
  spotOff(s.start - .2);
  camHome(s.start, .8);
  tl.to('#phone', { x: -900, rotation: -8, duration: 1, ease: 'power3.in' }, s.start + .5);
  tl.to('#contacts', { autoAlpha: 1, duration: .5 }, s.start + .9);
  tl.fromTo('#contacts h2', { y: 40, autoAlpha: 0 }, { y: 0, autoAlpha: 1, duration: .6, ease: 'power3.out', immediateRender: false }, s.start + .9);
  pop('#cc1', at(l0, 'ໂທສາຍດ່ວນ') - .3);
  pop('#cc2', at(l1, 'WhatsApp') - .3);
  pop('#cc3', at(l1, 'WhatsApp') + .9);
  // end card
  const te = l2.start - .6;
  tl.to('#endcard', { clipPath: 'circle(80% at 50% 50%)', duration: 1, ease: 'power3.inOut' }, te);
  sfx(te, 'whoosh', .8);
  tl.to(['#hud'], { autoAlpha: 0, duration: .3 }, te + .6);
  tl.to('#eLogo', { scale: 1, duration: 1, ease: 'back.out(1.6)' }, te + .5);
  tl.to('#eSlogan', { autoAlpha: 1, y: 0, duration: .8, ease: 'power3.out' }, te + .9);
  tl.to('#eInfo', { autoAlpha: 1, y: 0, duration: .8, ease: 'power3.out' }, te + 1.3);
  sfx(te + .9, 'chime', .6);
  tl.to('#stage', { opacity: 1, duration: .01 }, T.duration); // pad timeline to full length
}

/* ---------------------------------------------------------------- run */

function build() {
  buildBackground();
  buildPhone();
  buildPanels();
  buildHud();
  buildIntro();
  buildCaptions();
  gsap.set('#logoPill', { x: -30 });
  sceneIntro();
  sceneStep1();
  sceneStep2();
  sceneForm();
  sceneStep3();
  sceneStep4();
  sceneStep5();
  sceneStep6();
  sceneStep7();
  sceneOutro();
  sfxCues.sort((a, b) => a.t - b.t);
}

window.__seek = (t) => {
  tl.seek(t, true);
  for (const u of updaters) u(t);
};
window.__sfx = sfxCues;
window.__duration = T.duration;

async function ready() {
  await document.fonts.ready;
  await Promise.all(['400', '500', '600', '700', '800'].map((w) => document.fonts.load(`${w} 40px "Noto Sans Lao Looped"`, 'ລາວ')));
  await Promise.all(['500', '600', '700', '800'].map((w) => document.fonts.load(`${w} 40px "Poppins"`, 'Ab')));
  await Promise.all([...document.images].map((img) => (img.complete ? null : new Promise((r) => { img.onload = img.onerror = r; }))));
}

window.__ready = ready().then(() => {
  build();
  window.__seek(0);
  if (!RENDER) preview();
  return true;
});

function preview() {
  const stage = $('#stage');
  const fit = () => {
    const k = Math.min(innerWidth / 1920, innerHeight / 1080);
    stage.style.transform = `translate(${(innerWidth - 1920 * k) / 2}px, ${(innerHeight - 1080 * k) / 2}px) scale(${k})`;
  };
  fit();
  addEventListener('resize', fit);
  const q = new URLSearchParams(location.search);
  let t0 = performance.now() / 1000 - (+q.get('t') || 0), paused = false, tp = 0;
  addEventListener('keydown', (e) => {
    if (e.code === 'Space') { paused = !paused; if (!paused) t0 = performance.now() / 1000 - tp; }
  });
  const loop = () => {
    if (!paused) { tp = (performance.now() / 1000 - t0) % T.duration; window.__seek(tp); }
    requestAnimationFrame(loop);
  };
  loop();
}
