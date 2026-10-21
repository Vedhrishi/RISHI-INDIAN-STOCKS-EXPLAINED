// Motion layer: refresh-rate-independent smooth scroll, frame-pacing governor, pointer tilt.
// Everything is time-based (seconds, not frames), so 60, 144 and 240 Hz displays feel identical, just finer.
// Only transform/opacity are animated, so the work stays on the compositor.
(() => {
const root = document.documentElement;
const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
const finePointer = matchMedia('(hover: hover) and (pointer: fine)').matches;
const clamp = (v, a, b) => Math.min(b, Math.max(a, v));

// ---- 1. Display refresh-rate probe + frame-pacing governor ------------------------------------
const stats = { hz: 60, budget: 1000 / 60, slow: 0, frames: 0 };
window.__motion = stats;
const RATES = [30, 48, 60, 75, 90, 120, 144, 165, 240];
function probe() {
  const dts = []; let last = 0;
  requestAnimationFrame(function f(t) {
    if (last) dts.push(t - last); last = t;
    if (dts.length < 90) return requestAnimationFrame(f);
    dts.sort((a, b) => a - b);
    const hz = 1000 / dts[dts.length >> 1];                       // median frame time, robust to hiccups
    const snapped = RATES.reduce((p, c) => Math.abs(c - hz) < Math.abs(p - hz) ? c : p);
    if (snapped > stats.hz || !root.dataset.hz) { stats.hz = snapped; stats.budget = 1000 / snapped; root.dataset.hz = snapped; }
  });
}
probe(); setTimeout(probe, 5000); setTimeout(probe, 12000);       // load-time jank can under-read the display rate, so re-probe and keep the best
setTimeout(governor, 6000);
// If frames keep missing twice their budget, drop to a lighter visual mode (cinematic.js reads data-perf too).
function governor() {
  let last = performance.now(), bad = 0, n = 0;
  (function f(t) {
    const dt = t - last; last = t; n++;
    if (dt > stats.budget * 2.2 && dt < 250) bad++;
    if (n === 120) { root.dataset.perf = bad > 18 ? 'low' : 'high'; n = 0; bad = 0; }
    requestAnimationFrame(f);
  })(last);
}

// ---- 2. Inertial smooth scroll (mouse wheel only; touch and keyboard stay native) -------------
if (!reduce && finePointer) {
  let target = scrollY, cur = scrollY, active = false, last = 0;
  const max = () => root.scrollHeight - innerHeight;
  const stop = () => { active = false; target = cur = scrollY; };
  const insideScroller = el => {
    for (let n = el; n && n !== document.body; n = n.parentElement) {
      const s = getComputedStyle(n);
      if (/(auto|scroll)/.test(s.overflowY) && n.scrollHeight > n.clientHeight) return true;
    }
    return false;
  };
  function tick(t) {
    const dt = Math.min((t - last) / 1000, 0.05); last = t;
    cur += (target - cur) * (1 - Math.exp(-dt * 10));    // exponential ease, independent of frame rate
    if (Math.abs(target - cur) < 0.4) { cur = target; active = false; }
    scrollTo(0, cur);
    if (active) requestAnimationFrame(tick);
  }
  const go = y => {
    target = clamp(y, 0, max());
    if (!active) { cur = scrollY; active = true; last = performance.now(); requestAnimationFrame(tick); }
    clearTimeout(go.guard);                                   // safety net: if frames are being withheld, scroll natively instead of stalling
    go.guard = setTimeout(() => { if (active && Math.abs(scrollY - cur) < 1 && cur !== target) { active = false; cur = target; scrollTo(0, target); } }, 250);
  };
  addEventListener('wheel', e => {
    if (e.ctrlKey || e.metaKey || e.shiftKey || document.querySelector('dialog[open]') || insideScroller(e.target)) return;
    e.preventDefault();
    const dy = e.deltaMode === 1 ? e.deltaY * 34 : e.deltaMode === 2 ? e.deltaY * innerHeight : e.deltaY;
    go((active ? target : scrollY) + dy);
  }, { passive: false });
  addEventListener('scroll', () => { if (!active) target = cur = scrollY; }, { passive: true });
  addEventListener('keydown', () => { if (active) stop(); });
  addEventListener('pointerdown', e => { if (e.clientX > innerWidth - 20 && active) stop(); });   // grabbing the scrollbar
  document.addEventListener('click', e => {
    const a = e.target.closest('a[href^="#"]'); if (!a || a.getAttribute('href') === '#') return;
    const el = document.querySelector(a.getAttribute('href')); if (!el) return;
    e.preventDefault(); go(el.getBoundingClientRect().top + scrollY - 12); history.replaceState(null, '', a.getAttribute('href'));
  });
}

// ---- 3. Pointer tilt + light on cards (hover devices only) ------------------------------------
if (!reduce && finePointer) {
  let card = null, rx = 0, ry = 0, tx = 0, ty = 0, raf = 0, lt = 0;
  function loop(t) {
    const dt = Math.min((t - lt) / 1000, 0.05); lt = t; const k = 1 - Math.exp(-dt * 14);
    rx += (tx - rx) * k; ry += (ty - ry) * k;
    if (card) card.style.transform = `perspective(900px) rotateX(${rx}deg) rotateY(${ry}deg) translate3d(0,${-Math.abs(rx + ry) * 0.4}px,0)`;
    if (card && !tx && !ty && Math.abs(rx) < 0.02 && Math.abs(ry) < 0.02) { card.style.transform = ''; card = null; raf = 0; return; }
    raf = requestAnimationFrame(loop);
  }
  document.addEventListener('pointermove', e => {
    if (root.dataset.perf === 'low') return;
    const c = e.target.closest?.('.card, .cine-card, .stat, .biz, .edu');
    if (!c) { if (card) { tx = ty = 0; } return; }
    if (card && card !== c) { card.style.transform = ''; rx = ry = 0; }
    card = c; const r = c.getBoundingClientRect(), px = (e.clientX - r.left) / r.width, py = (e.clientY - r.top) / r.height;
    ty = (px - 0.5) * 7; tx = (0.5 - py) * 7;
    c.style.setProperty('--mx', px * 100 + '%'); c.style.setProperty('--my', py * 100 + '%');
    if (!raf) { lt = performance.now(); raf = requestAnimationFrame(loop); }
  }, { passive: true });
  document.addEventListener('pointerout', e => { if (e.target === card) { tx = ty = 0; } }, { passive: true });
}

// ---- 4. Hide the intro's fixed logo once the pinned intro is over (the glass nav takes over) ---
const cine = document.getElementById('cine');
if (cine) {
  let queued = false;
  const upd = () => { queued = false; root.classList.toggle('past-cine', scrollY > cine.offsetHeight - innerHeight * 0.6); };
  addEventListener('scroll', () => { if (!queued) { queued = true; requestAnimationFrame(upd); } }, { passive: true });
  upd();
}
})();
