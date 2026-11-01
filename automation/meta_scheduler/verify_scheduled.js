/*
 * Collect and verify every slot in Meta Business Suite -> Content -> Posts and reels -> Scheduled.
 *
 * Usage: open the Scheduled tab, paste this into the page console (or run it with Claude in
 * Chrome's JavaScript tool). Edit CONFIG first.
 */
(async () => {
  const CONFIG = {
    start: new Date(),              // first day you expect a post (local time)
    days: 29,                       // how many days the schedule should cover
    times: ['07:00', '19:00'],      // posts per day, 24h, in the account's time zone
    month: new Intl.DateTimeFormat('en-GB', { month: 'long' }),
  };

  const found = new Map();
  const grab = () => document.querySelectorAll('[role=row],tr').forEach((r) => {
    const t = r.innerText.replace(/\s+/g, ' ').trim();
    const m = t.match(/(\d{1,2} [A-Za-z]+) (\d{2}:\d{2}) (Public|Private)/);
    if (m) found.set(`${m[1]} ${m[2]}`, true);
  });

  // find the element that actually scrolls the list
  let el = document.querySelector('[role=row],tr'), scroller = null;
  while (el) {
    if (/auto|scroll/.test(getComputedStyle(el).overflowY) && el.scrollHeight > el.clientHeight + 20) { scroller = el; break; }
    el = el.parentElement;
  }
  if (!scroller) throw new Error('Open the Scheduled tab first (no list found).');

  scroller.scrollTop = 0;
  await new Promise((r) => setTimeout(r, 1000));
  let stall = 0, prev = 0;
  for (let i = 0; i < 120 && stall < 6; i++) {
    grab();
    scroller.scrollTop += 300;
    await new Promise((r) => setTimeout(r, 1300));   // the list lazy-loads; be patient
    if (found.size === prev) stall++; else { stall = 0; prev = found.size; }
  }
  grab();

  const expected = [];
  for (let d = 0; d < CONFIG.days; d++) {
    const day = new Date(CONFIG.start.getFullYear(), CONFIG.start.getMonth(), CONFIG.start.getDate() + d);
    for (const t of CONFIG.times) expected.push(`${day.getDate()} ${CONFIG.month.format(day)} ${t}`);
  }
  const missing = expected.filter((x) => !found.has(x));
  const extra = [...found.keys()].filter((x) => !expected.includes(x));
  const report = { expected: expected.length, found: found.size, missing, extra };
  console.log(JSON.stringify(report, null, 2));
  return report;
})();
