// Story seasons (swipeable shelves) + "continue the story". Loaded after app.js data is ready.
(async () => {
  const data = await fetch('data/videos.json?v=' + Date.now()).then(r => r.json());
  const now = new Date(new Date().toLocaleString('en-US', { timeZone: 'Asia/Kolkata' }));
  const released = e => new Date(e.publish.replace(' ', 'T')) <= now;
  const fmt = s => new Date(s.replace(' ', 'T')).toLocaleString('en-IN', { day: 'numeric', month: 'short' });
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const SEASONS = [
    { key: 's1', from: 1, to: 32, title: "Rishi's Kahani Bag", sub: 'Season 1: a boy, a magic satchel', banner: 'assets/season_s1.jpg' },
    { key: 'kite', from: 33, to: 62, title: 'The Kite Course', sub: 'Grown-up Rishi teaches Priya Zerodha, step by step', banner: 'assets/season_zerodha.jpg' },
    { key: 's2', from: 63, to: 87, title: 'Money Mysteries', sub: 'Season 2: a twist in every story', banner: 'assets/season_s2.jpg' },
    { key: 'arc', from: 88, to: 100, title: 'The Missing Diwali Fund', sub: 'One mystery, 13 clues', banner: 'assets/season_arc.jpg' },
  ];
  const byEp = {};
  data.episodes.forEach(e => { (byEp[e.ep] = byEp[e.ep] || {})[e.part] = e; });
  const link = p => p.youtube || p.instagram;
  let seen = {}; try { seen = JSON.parse(localStorage.getItem('rishi_seen') || '{}'); } catch (e) {}
  const chip = p => !p ? '' : released(p)
    ? `<a class="chip ${seen[p.ep + '_' + p.part] ? 'seen' : ''}" data-ep="${p.ep}" data-part="${p.part}" href="${link(p)}" target="_blank" rel="noopener">&#9654; Part ${p.part}</a>`
    : `<span class="chip soon">Part ${p.part} &middot; ${fmt(p.publish)}</span>`;
  const box = document.getElementById('seasonList');
  box.innerHTML = SEASONS.map(s => {
    const eps = []; for (let n = s.from; n <= s.to; n++) if (byEp[n]) eps.push(byEp[n]);
    const out = eps.filter(x => x[1] && released(x[1])).length;
    const cards = eps.length ? eps.map(x => { const p1 = x[1] || x[2]; return `
      <article class="scard ${released(p1) ? '' : 'locked-card'}">
        <img loading="lazy" src="${p1.thumb}" alt="${esc(p1.series_title)}">
        <div class="sbody"><span class="ep">Episode ${p1.ep}</span><h3>${esc(p1.series_title)}</h3>
        <div class="chips">${chip(x[1])}${chip(x[2])}</div></div></article>`; }).join('')
      : `<div class="soon-box">Scripts are written. A new clue every day, coming soon. &#128269;</div>`;
    return `<div class="season" id="season-${s.key}">
      <div class="sbanner" style="background-image:url('${s.banner}')"><div><h3>${esc(s.title)}</h3><p>${esc(s.sub)}</p>
      <span class="pill">${eps.length ? out + ' / ' + eps.length + ' episodes out' : 'Coming soon'}</span></div></div>
      <div class="rail"><button class="rail-arrow prev" aria-label="Scroll left">&#10094;</button>
      <div class="shelf">${cards}</div>
      <button class="rail-arrow next" aria-label="Scroll right">&#10095;</button></div></div>`;
  }).join('');
  box.querySelectorAll('.rail').forEach(rail => {
    const shelf = rail.querySelector('.shelf');
    rail.querySelector('.prev').addEventListener('click', () => shelf.scrollBy({ left: -shelf.clientWidth * 0.8, behavior: 'smooth' }));
    rail.querySelector('.next').addEventListener('click', () => shelf.scrollBy({ left: shelf.clientWidth * 0.8, behavior: 'smooth' }));
  });
  box.addEventListener('click', ev => {
    const a = ev.target.closest('a.chip'); if (!a) return;
    seen[a.dataset.ep + '_' + a.dataset.part] = 1;
    try { localStorage.setItem('rishi_seen', JSON.stringify(seen)); localStorage.setItem('rishi_last', JSON.stringify({ ep: +a.dataset.ep, part: +a.dataset.part })); } catch (e) {}
    a.classList.add('seen');
  });
  let last = null; try { last = JSON.parse(localStorage.getItem('rishi_last') || 'null'); } catch (e) {}
  const ordered = data.episodes.filter(released);
  const next = last ? ordered.find(e => e.ep > last.ep || (e.ep === last.ep && e.part > last.part)) : ordered[0];
  const cont = document.getElementById('continue');
  if (next && cont) { cont.hidden = false; cont.href = link(next); cont.target = '_blank'; cont.rel = 'noopener';
    cont.innerHTML = `<span>${last ? 'Continue the story' : 'Start from Episode 1'}</span><b>Ep ${next.ep} &middot; Part ${next.part}: ${esc(next.title)}</b>`; }
  const st = document.getElementById('statEp'); if (st) st.dataset.count = new Set(ordered.map(e => e.ep)).size;
})();
