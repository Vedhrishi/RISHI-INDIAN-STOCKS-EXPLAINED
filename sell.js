// Sales pages: no payment gateway. Every enquiry becomes a pre-filled email to the owner, who replies personally.
const EMAIL = 'vedhrishi54@gmail.com';
const $ = (s, r = document) => r.querySelector(s), $$ = (s, r = document) => [...r.querySelectorAll(s)];
$$('[data-email]').forEach(el => el.textContent = EMAIL);

// reveal on scroll
const io = 'IntersectionObserver' in window ? new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } }), { threshold: .12 }) : null;
$$('.s-sec > h2, .tile, .plan, .step, .reel figure, .langbox, .worksheet').forEach((el, i) => {
  if (!io) return; el.classList.add('reveal'); el.style.setProperty('--d', (i % 4) * .07 + 's'); io.observe(el);
});

// copy email
$$('.copy').forEach(b => b.addEventListener('click', async () => {
  try { await navigator.clipboard.writeText(EMAIL); b.textContent = 'Copied ✓'; } catch (e) { b.textContent = EMAIL; }
  setTimeout(() => b.textContent = 'Copy', 2500);
}));

// sound toggle on hero / language demo videos
$$('.sound').forEach(b => b.addEventListener('click', () => {
  const v = b.parentElement.querySelector('video'); v.muted = !v.muted; if (!v.muted) { v.currentTime = 0; v.play(); }
  b.textContent = v.muted ? '🔇 Tap for sound' : '🔊 Sound on';
}));

// language demo: same scene in English, Hindi, Telugu
const lv = $('#langVideo');
$$('.tabs button').forEach(b => b.addEventListener('click', () => {
  $$('.tabs button').forEach(x => x.classList.toggle('on', x === b));
  const t = lv.currentTime; lv.src = b.dataset.src; lv.muted = false; lv.currentTime = 0;
  lv.play().catch(() => {}); const s = lv.parentElement.querySelector('.sound'); if (s) s.textContent = '🔊 Sound on';
}));

// only one sample video plays with sound at a time
$$('video').forEach(v => v.addEventListener('play', () => { if (!v.muted) $$('video').forEach(o => { if (o !== v && !o.muted) o.pause(); }); }));

// "Choose" buttons pre-select the package in the enquiry form
$$('[data-pick]').forEach(a => a.addEventListener('click', () => {
  const sel = $('#f-package'); if (sel) sel.value = a.dataset.pick;
  setTimeout(() => $('#f-name') && $('#f-name').focus({ preventScroll: true }), 600);
}));

// enquiry form -> email
const form = $('#enquiry');
if (form) {
  const KEY = 'rishi_enquiry_' + form.dataset.kind;
  try { const s = JSON.parse(localStorage.getItem(KEY) || '{}'); Object.entries(s).forEach(([k, v]) => { const el = form.elements[k]; if (el && el.type !== 'checkbox' && !el.length) el.value = v; }); } catch (e) {}
  form.addEventListener('input', () => {
    const o = {}; [...form.elements].forEach(el => { if (el.name && el.type !== 'checkbox') o[el.name] = el.value; });
    try { localStorage.setItem(KEY, JSON.stringify(o)); } catch (e) {}
  });
  const build = () => {
    const f = form.elements, g = n => (f[n] && f[n].value || '').trim();
    const langs = $$('input[name=lang]:checked', form).map(x => x.value).join(', ') || 'not sure yet';
    const org = g('org') || g('name');
    const subject = `${form.dataset.kind === 'studio' ? 'RISHI Studio enquiry' : 'RISHI Learn enquiry'}: ${g('package')} | ${org}`;
    const rows = [['Name', g('name')], [form.dataset.kind === 'studio' ? 'Business' : 'School / organisation', g('org')], ['Type', g('type')],
      ['Phone / WhatsApp', g('phone')], ['City', g('city')], ['Interested in', g('package')], ['Languages', langs], ['Students / quantity', g('qty')],
      ['Website / Instagram', g('site')]].filter(r => r[1]);
    const body = `Hi RISHI team,\n\n${g('msg') || 'I would like to know more.'}\n\n` + rows.map(r => `${r[0]}: ${r[1]}`).join('\n') + `\n\nSent from ${location.href.split('#')[0]}`;
    return { subject, body };
  };
  const valid = () => { if (!form.reportValidity()) return false; return true; };
  const done = () => { $('#okmsg').textContent = "Your email is ready. Press Send in your mail app, and we'll reply within 24 hours."; };
  form.addEventListener('submit', ev => {
    ev.preventDefault(); if (!valid()) return; const { subject, body } = build();
    location.href = `mailto:${EMAIL}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`; done();
  });
  $('#viaGmail').addEventListener('click', () => {
    if (!valid()) return; const { subject, body } = build();
    window.open(`https://mail.google.com/mail/?view=cm&fs=1&to=${EMAIL}&su=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`, '_blank', 'noopener'); done();
  });
  $('#copyAll').addEventListener('click', async () => {
    if (!valid()) return; const { subject, body } = build();
    try { await navigator.clipboard.writeText(`To: ${EMAIL}\nSubject: ${subject}\n\n${body}`); $('#okmsg').textContent = `Copied. Paste it into an email to ${EMAIL}.`; }
    catch (e) { $('#okmsg').textContent = `Please email ${EMAIL}`; }
  });
}

// lesson shelf (Learn page) from the episode data
const lb = $('#lessons');
if (lb) fetch('data/videos.json').then(r => r.json()).then(d => {
  const ids = lb.dataset.eps.split(',').map(Number);
  const by = {}; d.episodes.forEach(e => { if (e.part === 1) by[e.ep] = e; });
  lb.innerHTML = ids.filter(n => by[n]).map((n, k) => `<div class="lesson"><img loading="lazy" src="${by[n].thumb}" alt=""><div><span>Lesson ${k + 1}</span>${by[n].series_title.replace(/[<>&]/g, '')}</div></div>`).join('');
}).catch(() => {});
