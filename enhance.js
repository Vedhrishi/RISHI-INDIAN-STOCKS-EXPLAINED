// Scroll-driven engagement: progress bar, reveal-on-scroll, count-up, rotating headline, spotlight, follow bar.
const $ = s => document.querySelector(s), $$ = s => [...document.querySelectorAll(s)];
const bar = $('#progress'), follow = $('#follow');
addEventListener('scroll', () => {
  const h = document.documentElement;
  bar.style.width = (h.scrollTop / (h.scrollHeight - h.clientHeight) * 100) + '%';
  follow.classList.toggle('show', h.scrollTop > 700);
}, { passive: true });

const io = new IntersectionObserver(es => es.forEach(e => {
  if (!e.isIntersecting) return;
  e.target.classList.add('in'); io.unobserve(e.target);
  if (e.target.dataset.count) countUp(e.target);
}), { threshold: .12 });
function reveal(root = document) {
  root.querySelectorAll('section h2, section > p, .card:not(.in), .course, .spot, .stat').forEach((el, i) => {
    if (el.classList.contains('reveal')) return;
    el.classList.add('reveal'); el.style.setProperty('--d', (i % 6) * .07 + 's'); io.observe(el);
  });
  $$('[data-count]').forEach(b => io.observe(b));
}
function countUp(el) {
  const n = +el.dataset.count, t0 = performance.now();
  (function f(t) { const p = Math.min((t - t0) / 1400, 1); el.textContent = Math.round(n * (1 - Math.pow(1 - p, 3))); if (p < 1) requestAnimationFrame(f); })(t0);
}
// cards are rendered by app.js later and on search/show-more, so watch the grids
new MutationObserver(() => reveal()).observe(document.body, { childList: true, subtree: true });
reveal();

const words = ['saving', 'tax', 'scams', 'insurance', 'investing', 'your family'], r = $('#rotator');
let wi = 0, ci = 0, del = false;
(function type() {
  const w = words[wi]; ci += del ? -1 : 1; r.textContent = w.slice(0, ci);
  let wait = del ? 45 : 90;
  if (!del && ci === w.length) { del = true; wait = 1300; }
  else if (del && ci === 0) { del = false; wi = (wi + 1) % words.length; wait = 300; }
  setTimeout(type, wait);
})();

// "Latest episode" spotlight once cards exist
const t = setInterval(() => {
  const c = $('#grid .card'); if (!c) return; clearInterval(t);
  const img = c.querySelector('img'), links = c.querySelector('.links').outerHTML;
  $('#spot').innerHTML = `<div class="spot"><img src="${img.getAttribute('src')}" alt=""><div>
    <span class="live">NEW</span><h2 style="margin:10px 0 4px">${c.querySelector('h3').textContent}</h2>
    <p class="muted">${c.querySelector('.ep').textContent} · fresh out, watch it first</p>${links}</div></div>`;
}, 300);

// ---- countdown to next episode + opt-in notifications ----
(async () => {
  const d = await fetch('data/videos.json?v=' + Date.now()).then(r => r.json());
  const ist = () => new Date(new Date().toLocaleString('en-US', { timeZone: 'Asia/Kolkata' }));
  const at = e => new Date(e.publish.replace(' ', 'T'));
  const upcoming = () => d.episodes.filter(e => at(e) > ist()).sort((a, b) => at(a) - at(b))[0];
  let nxt = upcoming(), announced = null;
  function paint() {
    if (!nxt) { $('#nextTitle').textContent = 'More stories are on the way'; return; }
    if (at(nxt) - ist() <= 0) {
      if ('Notification' in window && Notification.permission === 'granted' && announced !== nxt.publish) {
        announced = nxt.publish;
        new Notification('New RISHI episode is out!', { body: nxt.title, icon: 'assets/profile.png' });
      }
      nxt = upcoming(); if (!nxt) return paint();
    }
    const s = Math.max(0, Math.floor((at(nxt) - ist()) / 1000));
    $('#nextTitle').textContent = 'Episode ' + nxt.ep + ' - Part ' + nxt.part + ': ' + nxt.title;
    $('#nextWhen').textContent = 'Drops ' + at(nxt).toLocaleString('en-IN', { weekday: 'long', day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' }) + ' IST';
    $('#cd').textContent = Math.floor(s / 86400); $('#ch').textContent = String(Math.floor(s % 86400 / 3600)).padStart(2, '0');
    $('#cm').textContent = String(Math.floor(s % 3600 / 60)).padStart(2, '0'); $('#cs').textContent = String(s % 60).padStart(2, '0');
  }
  paint(); setInterval(paint, 1000);
  const nb = $('#notify');
  const sync = () => { nb.textContent = !('Notification' in window) ? 'Notifications not supported here' : Notification.permission === 'granted' ? 'Notifications on' : 'Notify me when it drops'; };
  nb.addEventListener('click', async () => { if ('Notification' in window) { await Notification.requestPermission(); sync(); } });
  sync();
})();

// ---- background push (works when the site is closed) ----
(() => {
  const cfg = window.RISHI_CONFIG || {};
  const b64 = s => Uint8Array.from(atob((s + '='.repeat((4 - s.length % 4) % 4)).replace(/-/g, '+').replace(/_/g, '/')), c => c.charCodeAt(0));
  const btn = document.getElementById('notify');
  if (!('serviceWorker' in navigator) || !('PushManager' in window) || !cfg.VAPID_PUBLIC_KEY) return;
  navigator.serviceWorker.register('/sw.js');
  btn.addEventListener('click', async () => {
    try {
      const reg = await navigator.serviceWorker.ready;
      if (await Notification.requestPermission() !== 'granted') return;
      const sub = (await reg.pushManager.getSubscription()) || await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: b64(cfg.VAPID_PUBLIC_KEY) });
      await fetch(cfg.SUPABASE_URL + '/rest/v1/push_subscriptions', { method: 'POST',
        headers: { apikey: cfg.SUPABASE_ANON_KEY, Authorization: 'Bearer ' + cfg.SUPABASE_ANON_KEY, 'Content-Type': 'application/json', Prefer: 'resolution=ignore-duplicates' },
        body: JSON.stringify({ endpoint: sub.endpoint, sub: sub.toJSON() }) });
      btn.textContent = "You're subscribed. We'll ping you on every new episode.";
    } catch (e) { btn.textContent = 'Could not turn on notifications'; }
  });
  navigator.serviceWorker.ready.then(r => r.pushManager.getSubscription()).then(s => { if (s) btn.textContent = "You're subscribed. We'll ping you on every new episode."; });
})();
