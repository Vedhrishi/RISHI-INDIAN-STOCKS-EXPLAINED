#!/usr/bin/env python3
"""RISHI Publisher desktop app (Tkinter, standard library). Double-click, no terminal needed.

Tabs: 1 Settings (platform keys) · 2 Batch (pick folder, fill titles, set times) · 3 Publish (validate, dry run, run, live status).
Uses the engine in rishi_publisher.py, so the command line and the app behave identically.
"""
import argparse, datetime as dt, io, json, os, queue, sys, threading, tkinter as tk
from tkinter import filedialog, messagebox, ttk

import rishi_publisher as rp

HERE = rp.HERE
ENV_PATH = os.path.join(HERE, '.env')
BATCH_DIR = os.path.join(HERE, 'batches')
FIELDS = [('YouTube', [('YT_CLIENT_ID', 'Client ID'), ('YT_CLIENT_SECRET', 'Client secret'), ('YT_REFRESH_TOKEN', 'Refresh token')]),
          ('Facebook Page', [('FB_PAGE_ID', 'Page ID'), ('FB_PAGE_TOKEN', 'Page access token')]),
          ('Instagram', [('IG_USER_ID', 'Instagram user ID'), ('IG_ACCESS_TOKEN', 'Access token')])]
COLS = [('key', 'Episode', 90), ('title', 'Title', 260), ('series_title', 'Series', 180), ('tags', 'Tags (comma separated)', 190), ('publish', 'Publish (IST)', 130)]
STAT = ('youtube', 'facebook', 'instagram', 'website')
COLOR = dict(done='#16a34a', failed='#dc2626', waiting='#d97706', deferred='#d97706', uploading='#2563eb', dry='#6b7280')


DONE = object()


class QueueOut(io.TextIOBase):
    def __init__(self, q): self.q = q
    def write(self, s): self.q.put(s); return len(s)


def read_env():
    out = {}
    if os.path.exists(ENV_PATH):
        for line in open(ENV_PATH, encoding='utf-8'):
            if '=' in line and not line.lstrip().startswith('#'):
                k, v = line.strip().split('=', 1); out[k] = v
    return out


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('RISHI Publisher'); self.geometry('1060x700'); self.minsize(900, 560)
        self.q = queue.Queue(); self.running = False; self.batch_path = None; self.items = []
        nb = ttk.Notebook(self); nb.pack(fill='both', expand=True, padx=8, pady=8); self.nb = nb
        self.t_set, self.t_batch, self.t_pub = ttk.Frame(nb, padding=12), ttk.Frame(nb, padding=12), ttk.Frame(nb, padding=12)
        nb.add(self.t_set, text='1  Settings'); nb.add(self.t_batch, text='2  Batch'); nb.add(self.t_pub, text='3  Publish')
        self.build_settings(); self.build_batch(); self.build_publish()
        self.after(150, self.pump)
        if os.path.exists(os.path.join(BATCH_DIR, 'batch.json')):
            self.open_batch(os.path.join(BATCH_DIR, 'batch.json'))
        if not read_env().get('YT_REFRESH_TOKEN'):
            nb.select(self.t_set)

    # ---- settings
    def build_settings(self):
        f = self.t_set; self.vars = {}; env = read_env(); r = 0
        ttk.Label(f, text='Keys are stored only on this computer in publisher/.env (git-ignored).', foreground='#555').grid(row=r, column=0, columnspan=2, sticky='w'); r += 1
        for group, fields in FIELDS:
            ttk.Label(f, text=group, font=('', 11, 'bold')).grid(row=r, column=0, sticky='w', pady=(12, 2)); r += 1
            for k, label in fields:
                ttk.Label(f, text=label).grid(row=r, column=0, sticky='e', padx=(0, 8), pady=2)
                v = tk.StringVar(value=env.get(k, '')); self.vars[k] = v
                ttk.Entry(f, textvariable=v, width=70, show='•').grid(row=r, column=1, sticky='w'); r += 1
        bar = ttk.Frame(f); bar.grid(row=r, column=0, columnspan=2, sticky='w', pady=14)
        ttk.Button(bar, text='Save settings', command=self.save_env).pack(side='left')
        ttk.Button(bar, text='Check tools and keys', command=self.doctor).pack(side='left', padx=8)

    def save_env(self):
        env = read_env(); env.update({k: v.get().strip() for k, v in self.vars.items()})
        env.setdefault('GRAPH_VERSION', 'v21.0')
        open(ENV_PATH, 'w', encoding='utf-8').write(''.join(f'{k}={v}\n' for k, v in env.items()))
        for k, v in env.items(): os.environ[k] = v
        messagebox.showinfo('Saved', 'Settings saved.')

    def doctor(self):
        self.save_quiet(); self.nb.select(self.t_pub); self.start(lambda: rp.cmd_doctor(argparse.Namespace()))

    def save_quiet(self):
        env = read_env(); env.update({k: v.get().strip() for k, v in self.vars.items()})
        open(ENV_PATH, 'w', encoding='utf-8').write(''.join(f'{k}={v}\n' for k, v in env.items()))
        for k, v in env.items(): os.environ[k] = v

    # ---- batch
    def build_batch(self):
        f = self.t_batch
        top = ttk.Frame(f); top.pack(fill='x')
        ttk.Button(top, text='New batch from folder…', command=self.new_batch).pack(side='left')
        ttk.Button(top, text='Open batch…', command=lambda: self.open_batch(filedialog.askopenfilename(initialdir=BATCH_DIR, filetypes=[('Batch', '*.json')]))).pack(side='left', padx=6)
        ttk.Label(top, text='First slot (IST)').pack(side='left', padx=(18, 4))
        self.start_var = tk.StringVar(value=(dt.datetime.now(rp.IST) + dt.timedelta(days=1)).strftime('%Y-%m-%d 10:40'))
        ttk.Entry(top, textvariable=self.start_var, width=17).pack(side='left')
        ttk.Label(top, text='Episodes/day').pack(side='left', padx=(10, 4))
        self.perday = tk.IntVar(value=1); ttk.Spinbox(top, from_=1, to=10, textvariable=self.perday, width=4).pack(side='left')
        self.batch_lbl = ttk.Label(f, text='No batch open. Create one from a folder of rishi_epNNN_partN*.mp4 files.', foreground='#555'); self.batch_lbl.pack(anchor='w', pady=8)
        tv = ttk.Treeview(f, columns=[c[0] for c in COLS], show='headings', height=16); self.tv = tv
        for k, label, w in COLS:
            tv.heading(k, text=label); tv.column(k, width=w, anchor='w')
        sb = ttk.Scrollbar(f, orient='vertical', command=tv.yview); tv.configure(yscrollcommand=sb.set)
        tv.pack(side='left', fill='both', expand=True); sb.pack(side='left', fill='y')
        tv.bind('<Double-1>', self.edit_cell)
        side = ttk.Frame(f); side.pack(side='left', fill='y', padx=8)
        ttk.Button(side, text='Save batch', command=self.save_batch).pack(fill='x')
        ttk.Label(side, text='Double-click a cell\nto edit it.', foreground='#555').pack(pady=10)

    def new_batch(self):
        folder = filedialog.askdirectory(title='Folder with the episode videos')
        if not folder: return
        try:
            rp.parse_pub(self.start_var.get())
        except ValueError:
            return messagebox.showerror('Time', 'First slot must look like 2026-10-20 10:40')
        os.makedirs(BATCH_DIR, exist_ok=True)
        name = 'batch_' + dt.datetime.now().strftime('%Y%m%d_%H%M') + '.json'
        out = os.path.join(BATCH_DIR, name)
        rp.cmd_scan(argparse.Namespace(folder=folder, start=self.start_var.get(), eps_per_day=self.perday.get(), out=name))
        os.replace(os.path.join(folder, name), out)
        m = json.load(open(out, encoding='utf-8'))            # items keep absolute file paths so the batch can live anywhere
        for it in m['items']:
            it['file'] = os.path.join(folder, it['file'])
            it['files'] = {k: os.path.join(folder, v) for k, v in it['files'].items()}
        json.dump(m, open(out, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
        if not m['items']:
            return messagebox.showwarning('Empty', 'No files named like rishi_ep034_part1*.mp4 found in that folder.')
        self.open_batch(out)

    def open_batch(self, path):
        if not path: return
        m = json.load(open(path, encoding='utf-8'))
        self.batch_path, self.items = path, m['items']
        self.batch_lbl.config(text=f'{os.path.basename(path)}  ·  {len(self.items)} videos')
        self.refresh_table()
        self.refresh_status()

    def refresh_table(self):
        self.tv.delete(*self.tv.get_children())
        for i, it in enumerate(self.items):
            self.tv.insert('', 'end', iid=str(i), values=(f'Ep {it["ep"]} · P{it["part"]}', it.get('title', ''), it.get('series_title', ''),
                                                          ', '.join(it.get('tags', [])), it['publish']))

    def edit_cell(self, ev):
        row, col = self.tv.identify_row(ev.y), self.tv.identify_column(ev.x)
        if not row or col == '#1': return
        key = COLS[int(col[1:]) - 1][0]; x, y, w, h = self.tv.bbox(row, col)
        cur = self.tv.set(row, key); e = ttk.Entry(self.tv); e.insert(0, cur); e.place(x=x, y=y, width=w, height=h); e.focus()
        def done(_=None):
            val = e.get().strip(); e.destroy(); it = self.items[int(row)]
            if key == 'tags': it['tags'] = [t.strip().lstrip('#') for t in val.split(',') if t.strip()]; val = ', '.join(it['tags'])
            else: it[key] = val
            self.tv.set(row, key, val)
        e.bind('<Return>', done); e.bind('<FocusOut>', done); e.bind('<Escape>', lambda _: e.destroy())

    def save_batch(self):
        if not self.batch_path: return False
        m = json.load(open(self.batch_path, encoding='utf-8')); m['items'] = self.items
        json.dump(m, open(self.batch_path, 'w', encoding='utf-8'), indent=1, ensure_ascii=False); return True

    # ---- publish
    def build_publish(self):
        f = self.t_pub
        opt = ttk.Frame(f); opt.pack(fill='x')
        self.plat = {p: tk.BooleanVar(value=True) for p in (*rp.PLATFORMS, 'website')}
        for p, v in self.plat.items(): ttk.Checkbutton(opt, text=p.capitalize(), variable=v).pack(side='left', padx=4)
        self.push = tk.BooleanVar(value=True); ttk.Checkbutton(opt, text='Push website to GitHub', variable=self.push).pack(side='left', padx=12)
        ttk.Label(opt, text='Sub-batch size').pack(side='left'); self.bsize = tk.IntVar(value=10)
        ttk.Spinbox(opt, from_=1, to=100, textvariable=self.bsize, width=4).pack(side='left', padx=4)
        bar = ttk.Frame(f); bar.pack(fill='x', pady=8)
        self.btns = [ttk.Button(bar, text=t, command=c) for t, c in
                     (('Validate', self.do_validate), ('Dry run', lambda: self.do_run(True)), ('Publish now', lambda: self.do_run(False)),
                      ('Keep running until done', lambda: self.do_run(False, watch=True)))]
        for b in self.btns: b.pack(side='left', padx=(0, 6))
        self.stop_btn = ttk.Button(bar, text='Stop', command=self.stop, state='disabled'); self.stop_btn.pack(side='left')
        self.status = ttk.Treeview(f, columns=('ep', 'pub', *STAT), show='headings', height=9); self.status.pack(fill='x')
        for k, label, w in (('ep', 'Episode', 110), ('pub', 'Publish (IST)', 140), *[(s, s.capitalize(), 110) for s in STAT]):
            self.status.heading(k, text=label); self.status.column(k, width=w)
        for s, c in COLOR.items(): self.status.tag_configure(s, foreground=c)
        self.log_box = tk.Text(f, height=14, bg='#0b0d17', fg='#d7dbea', state='disabled'); self.log_box.pack(fill='both', expand=True, pady=(8, 0))

    def refresh_status(self):
        self.status.delete(*self.status.get_children())
        if not self.batch_path: return
        m = rp.load_batch(self.batch_path); st = rp.load_state(m)
        for it in self.items:
            s = [rp.get_state(st, it, p).get('status', 'pending') for p in STAT]
            worst = next((x for x in ('failed', 'uploading', 'waiting', 'deferred') if x in s), 'done' if all(x in ('done',) for x in s) else '')
            self.status.insert('', 'end', values=(f'Ep {it["ep"]} · P{it["part"]}', it['publish'], *s), tags=(worst,))

    def say(self, s):
        self.log_box.config(state='normal'); self.log_box.insert('end', s); self.log_box.see('end'); self.log_box.config(state='disabled')

    def pump(self):
        try:
            while True:
                item = self.q.get_nowait()
                if item is DONE: self.finished()
                else: self.say(item)
        except queue.Empty:
            pass
        if self.running or not self.q.empty(): self.refresh_status()
        self.after(400, self.pump)

    def start(self, fn):
        if self.running: return
        self.running = True; self.stop_flag = threading.Event()
        for b in self.btns: b.config(state='disabled')
        self.stop_btn.config(state='normal')
        def work():
            old = sys.stdout; sys.stdout = QueueOut(self.q)
            try:
                rc = fn()
            except SystemExit as e:
                print(e.code if isinstance(e.code, str) else '')
            except Exception as e:
                print('ERROR:', e)
            finally:
                sys.stdout = old; self.running = False
                self.q.put(DONE)                                   # Tk is touched only from the main thread
        threading.Thread(target=work, daemon=True).start()

    def finished(self):
        for b in self.btns: b.config(state='normal')
        self.stop_btn.config(state='disabled'); self.refresh_status()

    def stop(self):
        if self.running:
            self.stop_flag.set(); self.say('\nStopping after the current pass… (anything already uploaded is saved)\n')

    def need_batch(self):
        if not self.batch_path:
            messagebox.showinfo('Batch', 'Create or open a batch first (tab 2).'); self.nb.select(self.t_batch); return False
        self.save_batch(); self.save_quiet(); return True

    def do_validate(self):
        if self.need_batch(): self.start(lambda: rp.cmd_validate(argparse.Namespace(batch=self.batch_path)))

    def do_run(self, dry, watch=False):
        if not self.need_batch(): return
        if not dry and not messagebox.askyesno('Publish', f'Upload {len(self.items)} videos to the selected platforms now?'): return
        only = ','.join(p for p, v in self.plat.items() if v.get())
        ns = argparse.Namespace(batch=self.batch_path, dry_run=dry, only=only, workers=3, batch_size=self.bsize.get(), pause=30, push=self.push.get(),
                                watch=watch, interval=300, yt_daily_limit=6)
        def go():
            self_stop = self.stop_flag
            while True:                                           # same loop as the CLI, but stoppable
                todo = rp.run_once(ns)
                if not watch or not todo or self_stop.is_set(): break
                print('next check in 5 minutes…')
                if self_stop.wait(ns.interval): break
        rp.load_env(); self.start(go)


if __name__ == '__main__':
    App().mainloop()
