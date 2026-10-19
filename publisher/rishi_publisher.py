#!/usr/bin/env python3
"""RISHI Publisher: batch-wise upload to YouTube, Instagram, Facebook and the website in one run.

Pure standard library (needs ffmpeg/ffprobe and git on PATH). See publisher/README.md.

Phases per batch:  1 scan -> 2 validate -> 3 plan -> 4 publish (YouTube | Facebook | Instagram in parallel)
                   -> 5 website (videos.json, seed.sql, thumbs, git push) -> 6 report
State is saved after every step, so an interrupted run resumes without re-uploading anything.
"""
import argparse, concurrent.futures as cf, datetime as dt, json, mimetypes, os, re, shutil, subprocess, sys, threading, time
import urllib.error, urllib.parse, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)
STATE_DIR = os.path.join(HERE, 'state')
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
PLATFORMS = ('youtube', 'facebook', 'instagram')
LOCK = threading.RLock()


def log(*a):
    print(time.strftime('%H:%M:%S'), *a, flush=True)


# ---------------------------------------------------------------- config
def load_env():
    p = os.path.join(HERE, '.env')
    if os.path.exists(p):
        for line in open(p, encoding='utf-8'):
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"\''))


def env(k, required=True):
    v = os.environ.get(k, '')
    if required and not v:
        raise RuntimeError(f'missing setting {k} (see publisher/.env.example)')
    return v


GRAPH = lambda: f"https://graph.facebook.com/{os.environ.get('GRAPH_VERSION', 'v21.0')}"


# ---------------------------------------------------------------- http
class HttpError(Exception):
    pass


def http(method, url, headers=None, data=None, form=None, js=None, retries=4, raw=False):
    """HTTP with retry on 429/5xx. Returns (status, headers, parsed-json-or-text)."""
    headers = dict(headers or {})
    if form is not None:
        data = urllib.parse.urlencode(form).encode()
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
    if js is not None:
        data = json.dumps(js).encode()
        headers['Content-Type'] = 'application/json; charset=UTF-8'
    for attempt in range(retries + 1):
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                body, status, h = r.read(), r.status, dict(r.headers)
        except urllib.error.HTTPError as e:
            body, status, h = e.read(), e.code, dict(e.headers)
        except urllib.error.URLError as e:
            if attempt < retries:
                time.sleep(2 ** (attempt + 1)); continue
            raise HttpError(f'{method} {url.split("?")[0]}: {e.reason}')
        if status in (429, 500, 502, 503, 504) and attempt < retries:
            time.sleep(2 ** (attempt + 1)); continue
        text = body.decode('utf-8', 'replace')
        try:
            parsed = json.loads(text) if text and not raw else text
        except ValueError:
            parsed = text
        return status, h, parsed
    raise HttpError('unreachable')


def need_ok(res, what, ok=(200, 201)):
    status, _, body = res
    if status not in ok:
        msg = str(body)[:400]
        for k in ('access_token', 'refresh_token', 'client_secret'):
            msg = re.sub(rf'{k}=[^&\s"]+', f'{k}=***', msg)
        raise HttpError(f'{what} failed [{status}]: {msg}')
    return res[2]


# ---------------------------------------------------------------- manifest & state
def parse_pub(s):
    return dt.datetime.strptime(s, '%Y-%m-%d %H:%M').replace(tzinfo=IST)


def key(it):
    return f"{it['ep']}_{it['part']}"


def load_batch(path):
    path = os.path.abspath(path)
    m = json.load(open(path, encoding='utf-8'))
    m['_dir'] = os.path.dirname(path)
    m['_name'] = os.path.splitext(os.path.basename(path))[0]
    return m


def file_for(m, it, plat):
    f = (it.get('files') or {}).get(plat) or it['file']
    return f if os.path.isabs(f) else os.path.join(m['_dir'], f)


def state_path(m):
    os.makedirs(STATE_DIR, exist_ok=True)
    return os.path.join(STATE_DIR, m['_name'] + '.json')


def load_state(m):
    p = state_path(m)
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else {'items': {}, 'yt_quota': {}}


def save_state(m, st):
    with LOCK:
        p = state_path(m)
        json.dump(st, open(p + '.tmp', 'w', encoding='utf-8'), indent=1)
        os.replace(p + '.tmp', p)


def set_state(m, st, it, plat, **kw):
    with LOCK:
        st['items'].setdefault(key(it), {}).setdefault(plat, {}).update(kw)
        save_state(m, st)


def get_state(st, it, plat):
    return st['items'].get(key(it), {}).get(plat, {})


# ---------------------------------------------------------------- captions
SITE_URL = 'https://rishi-indian-stocks-explained.vercel.app'
DISCLAIMER = 'Educational content only. Not financial advice.'


def caption(it, plat, links):
    if it.get('captions', {}).get(plat):
        return it['captions'][plat]
    tags = ' '.join('#' + t.lstrip('#') for t in it.get('tags', [])) + ' #IndianStocksExplained'
    head = f"{it['title']}\n\nEpisode {it['ep']} · Part {it['part']} of {it.get('series_title', it['title'])}"
    if plat == 'youtube':
        return f"{head}\n\nFull series: {SITE_URL}\n\n{DISCLAIMER}\n\n{tags} #Shorts"
    return f"{head}\n\nMore episodes: {SITE_URL}\n\n{DISCLAIMER}\n\n{tags}"


# ---------------------------------------------------------------- phase 1-2: scan, validate
def probe(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                          'stream=codec_name,width,height:format=duration,size', '-of', 'json', path],
                         capture_output=True, text=True)
    if out.returncode:
        raise RuntimeError(out.stderr.strip() or 'ffprobe failed')
    j = json.loads(out.stdout)
    s = j['streams'][0]
    return dict(codec=s['codec_name'], w=s['width'], h=s['height'], dur=float(j['format']['duration']), size=int(j['format']['size']))


def cmd_scan(a):
    pat = re.compile(r'rishi_ep(\d+)_part(\d)', re.I)
    files = {}
    for f in sorted(os.listdir(a.folder)):
        mm = pat.search(f)
        if mm and f.lower().endswith('.mp4'):
            files.setdefault((int(mm[1]), int(mm[2])), {})[
                'instagram' if 'instagram' in f.lower() else 'youtube' if 'youtube' in f.lower() else 'facebook' if 'facebook' in f.lower() else 'any'] = f
    start = parse_pub(a.start)
    items = []
    for i, ((ep, part), fs) in enumerate(sorted(files.items())):
        day, slot = divmod(i, 2 * a.eps_per_day)
        when = start + dt.timedelta(days=day, minutes=slot)
        base = fs.get('any') or next(iter(fs.values()))
        items.append(dict(ep=ep, part=part, file=base, files={k: v for k, v in fs.items() if k != 'any'},
                          title='', series_title='', tags=[], publish=when.strftime('%Y-%m-%d %H:%M')))
    out = os.path.join(a.folder, a.out)
    json.dump(dict(name=a.out, items=items), open(out, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    log(f'wrote {out} with {len(items)} items. Fill in "title", "series_title" and "tags" for each, then run validate.')


def validate(m, strict=True):
    errs, warns, seen = [], [], set()
    for it in m['items']:
        k = key(it); tag = f'ep{it["ep"]}p{it["part"]}'
        if k in seen:
            errs.append(f'{tag}: duplicate episode/part')
        seen.add(k)
        if not it.get('title', '').strip():
            errs.append(f'{tag}: title is empty')
        if not it.get('series_title', '').strip():
            it['series_title'] = it.get('title', '')
        try:
            parse_pub(it['publish'])
        except Exception:
            errs.append(f'{tag}: publish must look like "2026-10-20 10:40" (IST)')
        for plat in PLATFORMS:
            f = file_for(m, it, plat)
            if not os.path.exists(f):
                errs.append(f'{tag}/{plat}: file not found {f}'); continue
            try:
                p = probe(f)
            except Exception as e:
                errs.append(f'{tag}/{plat}: unreadable video ({e})'); continue
            if p['h'] <= p['w']:
                errs.append(f'{tag}/{plat}: not vertical ({p["w"]}x{p["h"]}); Reels/Shorts need 9:16')
            if p['codec'] != 'h264':
                warns.append(f'{tag}/{plat}: codec {p["codec"]}, h264 recommended')
            if p['dur'] > 90:
                errs.append(f'{tag}/{plat}: {p["dur"]:.0f}s is over 90s (Reels/Shorts limit)')
            if p['size'] > 1 << 30:
                errs.append(f'{tag}/{plat}: file over 1 GB')
    return errs, warns


def cmd_validate(a):
    m = load_batch(a.batch)
    errs, warns = validate(m)
    for w in warns: log('WARN ', w)
    for e in errs: log('ERROR', e)
    log(f'{len(m["items"])} items, {len(errs)} errors, {len(warns)} warnings')
    return 1 if errs else 0


# ---------------------------------------------------------------- phase 4: platforms
def yt_token():
    r = need_ok(http('POST', 'https://oauth2.googleapis.com/token', form=dict(
        client_id=env('YT_CLIENT_ID'), client_secret=env('YT_CLIENT_SECRET'),
        refresh_token=env('YT_REFRESH_TOKEN'), grant_type='refresh_token')), 'YouTube auth')
    return r['access_token']


def upload_youtube(m, it):
    path = file_for(m, it, 'youtube'); size = os.path.getsize(path)
    when = parse_pub(it['publish']); now = dt.datetime.now(IST)
    status = {'selfDeclaredMadeForKids': False}
    if when > now + dt.timedelta(minutes=5):
        status.update(privacyStatus='private', publishAt=when.astimezone(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z'))
    else:
        status['privacyStatus'] = 'public'
    body = {'snippet': {'title': it['title'][:92] + ('' if '#Shorts' in it['title'] else ' #Shorts'),
                        'description': caption(it, 'youtube', None), 'tags': it.get('tags', [])[:15],
                        'categoryId': '27'}, 'status': status}
    tok = yt_token(); auth = {'Authorization': f'Bearer {tok}'}
    st, h, _ = http('POST', 'https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status',
                    headers={**auth, 'X-Upload-Content-Type': 'video/mp4', 'X-Upload-Content-Length': str(size)}, js=body)
    if st != 200:
        raise HttpError(f'YouTube session failed [{st}]')
    up = {k.lower(): v for k, v in h.items()}['location']
    chunk, pos = 8 << 20, 0
    with open(path, 'rb') as f:
        while True:
            f.seek(pos); buf = f.read(chunk)
            end = pos + len(buf) - 1
            st, _, res = http('PUT', up, headers={'Content-Length': str(len(buf)), 'Content-Range': f'bytes {pos}-{end}/{size}'}, data=buf)
            if st in (200, 201):
                return dict(id=res['id'], url=f"https://youtube.com/shorts/{res['id']}")
            if st != 308:
                raise HttpError(f'YouTube upload failed [{st}] {str(res)[:300]}')
            pos = end + 1


def upload_facebook(m, it):
    page, tok = env('FB_PAGE_ID'), env('FB_PAGE_TOKEN')
    path = file_for(m, it, 'facebook'); size = os.path.getsize(path)
    r = need_ok(http('POST', f'{GRAPH()}/{page}/video_reels', form=dict(upload_phase='start', access_token=tok)), 'Facebook start')
    vid = r['video_id']
    with open(path, 'rb') as f:
        need_ok(http('POST', r['upload_url'], headers={'Authorization': f'OAuth {tok}', 'offset': '0', 'file_size': str(size)}, data=f.read()), 'Facebook upload')
    when = parse_pub(it['publish']); now = dt.datetime.now(IST)
    fin = dict(upload_phase='finish', video_id=vid, description=caption(it, 'facebook', None), access_token=tok)
    if when > now + dt.timedelta(minutes=15):
        fin.update(video_state='SCHEDULED', scheduled_publish_time=str(int(when.timestamp())))
    else:
        fin['video_state'] = 'PUBLISHED'
    need_ok(http('POST', f'{GRAPH()}/{page}/video_reels', form=fin), 'Facebook publish')
    return dict(id=vid, url=f'https://www.facebook.com/reel/{vid}')


def upload_instagram(m, it):
    ig, tok = env('IG_USER_ID'), env('IG_ACCESS_TOKEN')
    path = file_for(m, it, 'instagram'); size = os.path.getsize(path)
    r = need_ok(http('POST', f'{GRAPH()}/{ig}/media', form=dict(
        media_type='REELS', upload_type='resumable', caption=caption(it, 'instagram', None), share_to_feed='true', access_token=tok)), 'Instagram container')
    cid = r['id']
    with open(path, 'rb') as f:
        need_ok(http('POST', r['uri'], headers={'Authorization': f'OAuth {tok}', 'offset': '0', 'file_size': str(size)}, data=f.read()), 'Instagram upload')
    for _ in range(60):                                   # up to ~10 min of processing
        s = need_ok(http('GET', f'{GRAPH()}/{cid}?fields=status_code,status&access_token={tok}'), 'Instagram status')
        if s.get('status_code') == 'FINISHED':
            break
        if s.get('status_code') in ('ERROR', 'EXPIRED'):
            raise HttpError(f'Instagram processing {s.get("status_code")}: {s.get("status")}')
        time.sleep(10)
    else:
        raise HttpError('Instagram processing timed out')
    mid = need_ok(http('POST', f'{GRAPH()}/{ig}/media_publish', form=dict(creation_id=cid, access_token=tok)), 'Instagram publish')['id']
    link = http('GET', f'{GRAPH()}/{mid}?fields=permalink&access_token={tok}')[2]
    return dict(id=mid, url=link.get('permalink') if isinstance(link, dict) else '')


UPLOADERS = dict(youtube=upload_youtube, facebook=upload_facebook, instagram=upload_instagram)


def run_platform(m, st, it, plat, dry, yt_limit):
    cur = get_state(st, it, plat)
    if cur.get('status') == 'done':
        return 'done'
    # Instagram has no native scheduling for Reels: publish only once the slot is due.
    if plat == 'instagram' and parse_pub(it['publish']) > dt.datetime.now(IST):
        set_state(m, st, it, plat, status='waiting', note='publishes when due (use --watch)')
        return 'waiting'
    if plat == 'youtube':
        today = dt.date.today().isoformat()
        with LOCK:
            used = st['yt_quota'].get(today, 0)
            if used >= yt_limit:
                set_state(m, st, it, plat, status='deferred', note=f'daily upload cap {yt_limit} reached; resumes next run')
                return 'deferred'
            if not dry:
                st['yt_quota'][today] = used + 1
    if dry:
        log(f'  [dry-run] would upload ep{it["ep"]}p{it["part"]} -> {plat} ({it["publish"]} IST)')
        return 'dry'
    set_state(m, st, it, plat, status='uploading', note='')
    try:
        res = UPLOADERS[plat](m, it)
        set_state(m, st, it, plat, status='done', note='', **res)
        log(f'  OK   ep{it["ep"]}p{it["part"]} {plat}: {res.get("url")}')
        return 'done'
    except Exception as e:
        set_state(m, st, it, plat, status='failed', note=str(e)[:400])
        log(f'  FAIL ep{it["ep"]}p{it["part"]} {plat}: {e}')
        return 'failed'


# ---------------------------------------------------------------- phase 5: website
def build_seed(eps):
    q = lambda s: "'" + str(s).replace("'", "''") + "'"
    rows = [f"({e['ep']},{e['part']},{q(e['title'])},{q(e['series_title'])},{q(e['publish'])},{q(e['thumb'])},{q(e['youtube'])},{q(e['instagram'])},{q(e['facebook'])})" for e in eps]
    return ('insert into episodes (ep, part, title, series_title, publish_at, thumb, youtube_url, instagram_url, facebook_url) values\n'
            + ',\n'.join(rows) + '\non conflict (ep, part) do update set title=excluded.title, youtube_url=excluded.youtube_url, instagram_url=excluded.instagram_url, facebook_url=excluded.facebook_url, publish_at=excluded.publish_at;\n')


def update_website(m, st, items, dry, push):
    vp = os.path.join(SITE, 'data', 'videos.json')
    data = json.load(open(vp, encoding='utf-8'))
    links = data['links']; by = {(e['ep'], e['part']): e for e in data['episodes']}
    changed = 0
    for it in items:
        thumb = f"thumbs/ep{it['ep']:03d}_p{it['part']}.jpg"
        tp = os.path.join(SITE, thumb)
        if not os.path.exists(tp) and not dry:
            src = it.get('thumb')
            src = (src if os.path.isabs(src) else os.path.join(m['_dir'], src)) if src else None
            if src and os.path.exists(src):
                shutil.copyfile(src, tp)
            else:
                for ss in ('6', '1', '0'):          # frame at 6s like the original thumbs; fall back for short clips
                    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', ss, '-i', file_for(m, it, 'youtube'), '-frames:v', '1',
                                    '-vf', 'scale=270:-2', '-q:v', '6', tp], capture_output=True)
                    if os.path.exists(tp):
                        break
                else:
                    raise RuntimeError(f'could not create thumbnail for ep{it["ep"]}p{it["part"]}')
        g = lambda p: get_state(st, it, p).get('url') or ''
        new = dict(ep=it['ep'], part=it['part'], title=it['title'], series_title=it['series_title'], publish=it['publish'],
                   tags=it.get('tags', [])[:4], thumb=thumb, youtube=g('youtube') or by.get((it['ep'], it['part']), {}).get('youtube', ''),
                   instagram=g('instagram') or links['instagram'], facebook=g('facebook') or links['facebook'])
        if by.get((it['ep'], it['part'])) != new:
            by[(it['ep'], it['part'])] = new; changed += 1
        set_state(m, st, it, 'website', status='done' if not dry else 'dry')
    if not changed:
        log('  website: already up to date')
        if push and not dry:
            git_push(m)
        return
    if dry:
        log(f'  [dry-run] website: would update {changed} episode entries, seed.sql and push'); return
    data['episodes'] = sorted(by.values(), key=lambda e: (e['publish'], e['ep'], e['part']))
    data['generated'] = dt.datetime.now(IST).strftime('%Y-%m-%dT%H:%M')
    json.dump(data, open(vp, 'w', encoding='utf-8'), ensure_ascii=False)
    open(os.path.join(SITE, 'supabase', 'seed.sql'), 'w', encoding='utf-8').write(build_seed(data['episodes']))
    log(f'  website: updated {changed} entries (total {len(data["episodes"])})')
    if push:
        git_push(m, changed)


def git_push(m, changed=0):
    git = lambda *c: subprocess.run(['git', '-C', SITE, *c], capture_output=True, text=True)
    git('add', 'data/videos.json', 'supabase/seed.sql', 'thumbs')
    if git('status', '--porcelain', '--', 'data', 'supabase', 'thumbs').stdout.strip():
        r = git('commit', '-m', f'Publish {m["_name"]}: {changed} episode entries')
        if r.returncode:
            log('  website: commit failed:', r.stderr.strip()[:300]); return
    r = git('push')                                  # also pushes commits left over from an earlier failed push
    if r.returncode:
        log('  website: push failed (will retry on next run):', r.stderr.strip()[:300])
    else:
        log('  website: pushed (Vercel deploys automatically)')


# ---------------------------------------------------------------- orchestration
def process(m, st, items, a):
    only = set(a.only.split(',')) if a.only else set(PLATFORMS) | {'website'}
    plats = [p for p in PLATFORMS if p in only]
    with cf.ThreadPoolExecutor(max_workers=max(1, a.workers)) as ex:
        futs = []
        for it in items:
            for p in plats:
                futs.append(ex.submit(run_platform, m, st, it, p, a.dry_run, a.yt_daily_limit))
        for f in futs:
            f.result()
    if 'website' in only:
        update_website(m, st, items, a.dry_run, a.push)


def run_once(a):
    m = load_batch(a.batch)
    errs, warns = validate(m)
    for w in warns: log('WARN ', w)
    if errs:
        for e in errs: log('ERROR', e)
        raise SystemExit('Fix the errors above, then run again.')
    st = load_state(m)
    items = sorted(m['items'], key=lambda i: (i['publish'], i['ep'], i['part']))
    size = a.batch_size or len(items)
    chunks = [items[i:i + size] for i in range(0, len(items), size)]
    log(f'{len(items)} items -> {len(chunks)} batch(es) of up to {size}')
    for n, chunk in enumerate(chunks, 1):
        log(f'== batch {n}/{len(chunks)}: ep{chunk[0]["ep"]}p{chunk[0]["part"]} .. ep{chunk[-1]["ep"]}p{chunk[-1]["part"]}')
        process(m, st, chunk, a)
        if n < len(chunks) and a.pause > 0 and not a.dry_run:
            log(f'  pausing {a.pause}s before next batch'); time.sleep(a.pause)
    return report(m, st)


def report(m, st):
    log('== report')
    todo = 0
    for it in m['items']:
        row = []
        for p in (*PLATFORMS, 'website'):
            s = get_state(st, it, p).get('status', 'pending'); row.append(f'{p[:2]}={s}')
            todo += s not in ('done', 'dry')
        log(f'  ep{it["ep"]:>3}p{it["part"]} {it["publish"]}  ' + '  '.join(row))
    log('ALL DONE' if not todo else f'{todo} step(s) still pending/waiting/failed; run again (or use --watch) to continue')
    return todo


def cmd_run(a):
    if not a.dry_run:
        load_env()
    else:
        load_env()
    while True:
        todo = run_once(a)
        if not a.watch or not todo:
            return 0 if not todo else 2
        log(f'watching: next pass in {a.interval}s (Ctrl+C to stop)'); time.sleep(a.interval)


def cmd_status(a):
    m = load_batch(a.batch); report(m, load_state(m))


def cmd_doctor(a):
    load_env(); ok = True
    for t in ('ffmpeg', 'ffprobe', 'git'):
        found = shutil.which(t); ok &= bool(found); log(('OK   ' if found else 'MISSING'), t)
    groups = dict(youtube=['YT_CLIENT_ID', 'YT_CLIENT_SECRET', 'YT_REFRESH_TOKEN'], facebook=['FB_PAGE_ID', 'FB_PAGE_TOKEN'],
                  instagram=['IG_USER_ID', 'IG_ACCESS_TOKEN'])
    for g, ks in groups.items():
        miss = [k for k in ks if not os.environ.get(k)]
        log(('OK   ' if not miss else 'MISSING'), g, '' if not miss else ', '.join(miss)); ok &= not miss
    if os.environ.get('FB_PAGE_TOKEN'):
        r = http('GET', f"{GRAPH()}/me?access_token={os.environ['FB_PAGE_TOKEN']}", retries=0)
        log('OK   ' if r[0] == 200 else 'FAIL ', 'Facebook token check')
    return 0 if ok else 1


# ---------------------------------------------------------------- local dashboard
PAGE = """<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>RISHI Publisher</title>
<style>body{font:15px system-ui;margin:0;background:#0f1220;color:#eaeaf2}main{max-width:980px;margin:auto;padding:20px}
table{border-collapse:collapse;width:100%}td,th{padding:6px 8px;border-bottom:1px solid #2a2f4a;text-align:left}
.done{color:#4ade80}.failed{color:#f87171}.waiting,.deferred,.uploading{color:#fbbf24}.pending{color:#94a3b8}
button{background:#6366f1;color:#fff;border:0;padding:10px 18px;border-radius:8px;font-size:15px;cursor:pointer;margin-right:8px}
pre{background:#080a14;padding:10px;border-radius:8px;max-height:220px;overflow:auto}</style>
<main><h1>RISHI Publisher</h1><p><button onclick="go(0)">Publish batch now</button><button onclick="go(1)">Dry run</button><span id=busy></span></p>
<table id=t></table><h3>Log</h3><pre id=l></pre></main>
<script>async function load(){const j=await (await fetch('/api/status')).json();
document.getElementById('busy').textContent=j.running?'running...':'';document.getElementById('l').textContent=j.log;
document.getElementById('t').innerHTML='<tr><th>Episode<th>Publish (IST)<th>YouTube<th>Facebook<th>Instagram<th>Website</tr>'+j.rows.map(r=>
'<tr><td>'+r.k+'<td>'+r.pub+r.s.map(s=>'<td class='+s+'>'+s).join('')+'</tr>').join('')}
async function go(d){await fetch('/api/run?dry='+d,{method:'POST'});load()}load();setInterval(load,3000)</script>"""


def cmd_ui(a):
    load_env(); m = load_batch(a.batch); logbuf, running = [], [False]

    def worker(dry):
        class W(list):
            def write(s, x): logbuf.append(x)
            def flush(s): pass
        old = sys.stdout; sys.stdout = W()
        try:
            ns = argparse.Namespace(batch=a.batch, dry_run=dry, only='', workers=3, batch_size=a.batch_size, pause=0, push=a.push, watch=False,
                                    interval=600, yt_daily_limit=a.yt_daily_limit)
            run_once(ns)
        except BaseException as e:
            logbuf.append(f'ERROR {e}\n')
        finally:
            sys.stdout = old; running[0] = False

    class H(BaseHTTPRequestHandler):
        def log_message(s, *x): pass
        def send(s, body, ct='application/json'):
            s.send_response(200); s.send_header('Content-Type', ct); s.end_headers(); s.wfile.write(body if isinstance(body, bytes) else body.encode())
        def do_GET(s):
            if s.path == '/api/status':
                st = load_state(m)
                rows = [dict(k=f'Ep {i["ep"]} · Part {i["part"]}', pub=i['publish'],
                             s=[get_state(st, i, p).get('status', 'pending') for p in (*PLATFORMS, 'website')]) for i in m['items']]
                s.send(json.dumps(dict(rows=rows, running=running[0], log=''.join(logbuf)[-6000:])))
            else:
                s.send(PAGE, 'text/html; charset=utf-8')
        def do_POST(s):
            if s.path.startswith('/api/run') and not running[0]:
                running[0] = True
                threading.Thread(target=worker, args=('dry=1' in s.path,), daemon=True).start()
            s.send('{}')

    log(f'dashboard: http://127.0.0.1:{a.port}  (Ctrl+C to stop)')
    ThreadingHTTPServer(('127.0.0.1', a.port), H).serve_forever()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    s = sp.add_parser('doctor', help='check tools and credentials'); s.set_defaults(fn=cmd_doctor)
    s = sp.add_parser('scan', help='build a batch.json from a folder of rishi_epNNN_partN*.mp4 files')
    s.add_argument('folder'); s.add_argument('--start', required=True, help='first publish time, IST, e.g. "2026-10-20 10:40"')
    s.add_argument('--eps-per-day', type=int, default=1, help='episodes (2 parts each) per day'); s.add_argument('--out', default='batch.json'); s.set_defaults(fn=cmd_scan)
    s = sp.add_parser('validate', help='check every file and field'); s.add_argument('batch'); s.set_defaults(fn=cmd_validate)
    s = sp.add_parser('status', help='show progress per item and platform'); s.add_argument('batch'); s.set_defaults(fn=cmd_status)
    for name in ('run', 'ui'):
        s = sp.add_parser(name, help='publish the batch' if name == 'run' else 'local dashboard with a Publish button')
        s.add_argument('batch'); s.add_argument('--batch-size', type=int, default=0, help='items per sub-batch (0 = all at once)')
        s.add_argument('--push', action='store_true', help='git commit + push website changes')
        s.add_argument('--yt-daily-limit', type=int, default=6, help='YouTube API quota allows ~6 uploads/day by default')
        if name == 'run':
            s.add_argument('--dry-run', action='store_true'); s.add_argument('--only', default='', help='comma list: youtube,facebook,instagram,website')
            s.add_argument('--workers', type=int, default=3); s.add_argument('--pause', type=int, default=30, help='seconds between sub-batches')
            s.add_argument('--watch', action='store_true', help='keep looping until every step is done (Instagram waits for its slot)')
            s.add_argument('--interval', type=int, default=600); s.set_defaults(fn=cmd_run)
        else:
            s.add_argument('--port', type=int, default=8765); s.set_defaults(fn=cmd_ui)
    a = ap.parse_args()
    try:
        sys.exit(a.fn(a) or 0)
    except (RuntimeError, HttpError) as e:
        sys.exit(f'ERROR: {e}')
    except KeyboardInterrupt:
        sys.exit('stopped')


if __name__ == '__main__':
    main()
