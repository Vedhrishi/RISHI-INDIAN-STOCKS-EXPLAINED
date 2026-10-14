r"""Build the website data (read-only use of Instagram / YouTube / Facebook data):
website\data\videos.json, website\supabase\seed.sql, thumbnails in website\thumbs\ and bonus/course media."""
import os, re, json, glob, datetime, subprocess, shutil
ROOT = r'R:\INSTA'
WEB = os.path.join(ROOT, 'website')
for d in ('data', 'thumbs', 'supabase', os.path.join('media', 'bonus'), os.path.join('media', 'course')):
    os.makedirs(os.path.join(WEB, d), exist_ok=True)

IG = 'https://www.instagram.com/indian.stocks.explained/'
YT = 'https://www.youtube.com/@indian.stocks.explained'
FB = 'https://www.facebook.com/112325647216156'

yt = json.load(open(os.path.join(ROOT, 'youtube', 'captions', 'youtube_meta.json'), encoding='utf-8'))
yts = json.load(open(os.path.join(ROOT, 'youtube', 'schedule', 'yt_status.json'), encoding='utf-8'))
fb = json.load(open(os.path.join(ROOT, 'facebook', 'captions', 'facebook_meta.json'), encoding='utf-8'))
comp_f = os.path.join(ROOT, 'youtube', 'captions', 'compilations_meta.json')
comps = json.load(open(comp_f, encoding='utf-8')) if os.path.exists(comp_f) else {}

def topic(k):
    return yt[k]['title'].split(' | ')[0].split(' \u2192 ')[-1]

CAP = json.load(open(os.path.join(ROOT, 'series_cap.json')))['last_ep']
eps = []
for k, v in yt.items():
    ep, part = v['ep'], v['part']
    if ep > CAP:
        continue
    date = v['publish']
    tags = [t for t in re.findall(r'#(\w+)', fb.get(k, {}).get('caption', '')) if t.lower() != 'indianstocksexplained']
    thumb = f'thumbs/ep{ep:03d}_p{part}.jpg'
    src = os.path.join(ROOT, 'output', v['file'])
    dst = os.path.join(WEB, thumb)
    if not os.path.exists(dst):
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', '6', '-i', src, '-frames:v', '1', '-vf', 'scale=270:-2', '-q:v', '6', dst])
    eps.append(dict(ep=ep, part=part, title=topic(k), series_title=yt[f'{ep}_1']['title'].split(' | ')[0],
                    publish=date, tags=tags[:4], thumb=thumb,
                    youtube=yts.get(k, {}).get('url') or '', instagram=IG, facebook=FB))
eps.sort(key=lambda e: (e['publish'], e['ep'], e['part']))

weekly = [] if True else [dict(week=m['week'], title=m['title'], publish=m['publish'], minutes=m['minutes'], dates=m['dates'],
               thumb=f"comp_thumbs/{m['thumbnail']}") for m in sorted(comps.values(), key=lambda m: m['week'])]
os.makedirs(os.path.join(WEB, 'comp_thumbs'), exist_ok=True)
for m in comps.values():
    s = os.path.join(ROOT, 'youtube', 'compilations', 'thumbnails', m['thumbnail'])
    if os.path.exists(s):
        shutil.copyfile(s, os.path.join(WEB, 'comp_thumbs', m['thumbnail']))

bonus = []
for f in sorted(glob.glob(os.path.join(ROOT, 'output', 'rishi_ep90[1-3]_part*_instagram.mp4'))):
    n = os.path.basename(f)
    m = re.match(r'rishi_ep(\d+)_part(\d)_(.+)_instagram\.mp4', n)
    out = os.path.join(WEB, 'media', 'bonus', f'bonus_{m[1]}_part{m[2]}.mp4')
    shutil.copyfile(f, out)
    bonus.append(dict(ep=int(m[1]), part=int(m[2]), file=f'media/bonus/bonus_{m[1]}_part{m[2]}.mp4'))

data = dict(generated=datetime.datetime.now().isoformat(timespec='minutes'),
            links=dict(instagram=IG, youtube=YT, facebook=FB), episodes=eps, weekly=weekly, bonus=bonus)
json.dump(data, open(os.path.join(WEB, 'data', 'videos.json'), 'w', encoding='utf-8'), ensure_ascii=False)

def q(s):
    return "'" + str(s).replace("'", "''") + "'"
rows = [f"({e['ep']},{e['part']},{q(e['title'])},{q(e['series_title'])},{q(e['publish'])},{q(e['thumb'])},{q(e['youtube'])},{q(e['instagram'])},{q(e['facebook'])})" for e in eps]
seed = ('insert into episodes (ep, part, title, series_title, publish_at, thumb, youtube_url, instagram_url, facebook_url) values\n'
        + ',\n'.join(rows) + '\non conflict (ep, part) do update set title=excluded.title, youtube_url=excluded.youtube_url, publish_at=excluded.publish_at;\n')
open(os.path.join(WEB, 'supabase', 'seed.sql'), 'w', encoding='utf-8').write(seed)
print('episodes', len(eps), 'weekly', len(weekly), 'bonus', len(bonus))
