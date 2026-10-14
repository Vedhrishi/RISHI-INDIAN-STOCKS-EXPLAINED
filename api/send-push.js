// Runs from Vercel Cron (twice a day). Sends a Web Push to every subscriber for episodes that went live in the last ~100 minutes.
// Env: VAPID_PRIVATE_KEY, VAPID_PUBLIC_KEY, PUSH_SECRET, CRON_SECRET, SUPABASE_URL, SUPABASE_ANON_KEY
import webpush from 'web-push';
import { readFile } from 'node:fs/promises';
import { join } from 'node:path';

const rpc = (name, body) => fetch(`${process.env.SUPABASE_URL}/rest/v1/rpc/${name}`, {
  method: 'POST',
  headers: { apikey: process.env.SUPABASE_ANON_KEY, Authorization: `Bearer ${process.env.SUPABASE_ANON_KEY}`, 'Content-Type': 'application/json' },
  body: JSON.stringify({ p_secret: process.env.PUSH_SECRET, ...body })
}).then(r => r.json());

export default async function handler(req, res) {
  if (req.headers.authorization !== `Bearer ${process.env.CRON_SECRET}`) return res.status(401).end();
  webpush.setVapidDetails('mailto:vedhrishi54@gmail.com', process.env.VAPID_PUBLIC_KEY, process.env.VAPID_PRIVATE_KEY);
  const data = JSON.parse(await readFile(join(process.cwd(), 'data', 'videos.json'), 'utf8'));
  const nowIst = new Date(Date.now() + 5.5 * 3600e3);                       // IST wall clock held in UTC fields
  const at = e => new Date(e.publish.replace(' ', 'T') + 'Z');
  const due = data.episodes.filter(e => at(e) <= nowIst && nowIst - at(e) < 100 * 60e3);
  let sent = 0;
  for (const e of due) {
    if (!(await rpc('push_claim', { p_key: `${e.ep}_${e.part}` }))) continue;   // already announced
    const subs = await rpc('push_list', {});
    const payload = JSON.stringify({ title: `New: ${e.title}`, body: `Episode ${e.ep}, Part ${e.part} is out now.`, url: 'https://rishi-indian-stocks-explained.vercel.app/#episodes' });
    await Promise.all((Array.isArray(subs) ? subs : []).map(async s => {
      try { await webpush.sendNotification(s, payload); sent++; }
      catch (err) { if ([404, 410].includes(err.statusCode)) await rpc('push_remove', { p_endpoint: s.endpoint }); }
    }));
  }
  res.json({ due: due.length, sent });
}
