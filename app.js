const cfg = window.RISHI_CONFIG || {};
let supabase = null;
if (cfg.SUPABASE_URL && cfg.SUPABASE_ANON_KEY) {
  const { createClient } = await import('https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.45.4/+esm');
  supabase = createClient(cfg.SUPABASE_URL, cfg.SUPABASE_ANON_KEY);
}

const data = await fetch('data/videos.json?v=' + Date.now()).then(r => r.json());
const now = new Date(new Date().toLocaleString('en-US', { timeZone: 'Asia/Kolkata' }));
const released = e => new Date(e.publish.replace(' ', 'T')) <= now;

let episodes = data.episodes.filter(released);
// episode list comes from data/videos.json (single source of truth)
episodes = episodes.slice().reverse(); // newest first

document.querySelectorAll('[data-link]').forEach(a => a.href = data.links[a.dataset.link]);

const fmt = s => new Date(s.replace(' ', 'T')).toLocaleString('en-IN', { day: 'numeric', month: 'short', year: 'numeric', hour: 'numeric', minute: '2-digit' });
const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

const grid = document.getElementById('grid'), more = document.getElementById('more'), search = document.getElementById('search');
let shown = 24, list = episodes;
function render() {
  grid.innerHTML = list.slice(0, shown).map(e => `
    <article class="card">
      <img loading="lazy" src="${e.thumb}" alt="${esc(e.title)}">
      <div class="body">
        <span class="ep">Episode ${e.ep} · Part ${e.part}</span>
        <h3>${esc(e.title)}</h3>
        <span class="date">${fmt(e.publish)}</span>
        <div class="links">
          <a class="ig" href="${e.instagram}" target="_blank" rel="noopener">Instagram</a>
          ${e.youtube ? `<a class="yt" href="${e.youtube}" target="_blank" rel="noopener">YouTube</a>` : ''}
          <a class="fb" href="${e.facebook}" target="_blank" rel="noopener">Facebook</a>
        </div>
      </div>
    </article>`).join('') || '<p class="muted">No episodes match that search yet.</p>';
  more.style.display = list.length > shown ? 'block' : 'none';
  document.getElementById('count').textContent = `${episodes.length} episodes released so far`;
}
search.addEventListener('input', () => {
  const q = search.value.trim().toLowerCase();
  list = !q ? episodes : episodes.filter(e => (e.title + ' ' + e.series_title + ' ' + (e.tags || []).join(' ')).toLowerCase().includes(q));
  shown = 24; render();
});
more.addEventListener('click', () => { shown += 24; render(); });
render();

const weekly = data.weekly.filter(released);
const wg = document.getElementById('weeklyGrid');
if (wg) wg.innerHTML = (weekly.length ? weekly : data.weekly.slice(0, 3)).map(w => `
  <article class="card">
    <img loading="lazy" src="${w.thumb}" alt="${esc(w.title)}">
    <div class="body"><span class="ep">Week ${w.week} · ${w.minutes} min</span><h3>${esc(w.title)}</h3>
    <span class="date">${released(w) ? 'Out now' : 'Premieres ' + fmt(w.publish)}</span>
    <div class="links"><a class="yt" href="${data.links.youtube}" target="_blank" rel="noopener">Watch on YouTube</a></div></div>
  </article>`).join('');

document.getElementById('bonusGrid').innerHTML = data.bonus.map(b => `
  <article class="card"><video src="${b.file}" controls preload="metadata" playsinline></video>
  <div class="body"><span class="ep">Bonus ${b.ep - 900} · Part ${b.part}</span></div></article>`).join('');

const form = document.getElementById('waitlist'), msg = document.getElementById('waitmsg');
form.addEventListener('submit', async ev => {
  ev.preventDefault();
  const email = form.querySelector('input').value.trim();
  if (supabase) {
    const { error } = await supabase.from('course_waitlist').insert({ email });
    msg.textContent = error ? 'Something went wrong, please try again.' : "You're on the list! We'll email you when the course opens.";
  } else {
    msg.textContent = "Thanks! The waitlist opens once the site is connected to Supabase.";
  }
  if (!msg.textContent.startsWith('Something')) form.reset();
});
