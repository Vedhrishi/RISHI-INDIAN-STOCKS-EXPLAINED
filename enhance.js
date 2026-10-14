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
