#!/usr/bin/env python3
"""RISHI Autopilot: single-file installer and launcher (Python 3.10+, standard library only).

    python rishi_setup.py              install + guided setup (keys, YouTube login, health check, daily schedule)
    python rishi_setup.py run          make one video now (uploads as PRIVATE unless you changed YOUTUBE_PRIVACY)
    python rishi_setup.py doctor       re-run the health check
    python rishi_setup.py schedule     (re)create the daily job
    python rishi_setup.py claude       open Claude Code in the install folder to schedule Instagram/Facebook Reels
    python rishi_setup.py update       download the newest toolkit code, keeping your keys and login

Your keys are typed into your own terminal and saved only to <install dir>/youtube_pipeline/.env on your machine.
Nothing is sent anywhere except to the providers you configure. MIT licence.
"""
import argparse
import getpass
import hashlib
import io
import os
import re
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

REPO = "Vedhrishi/RISHI-INDIAN-STOCKS-EXPLAINED"
ASSET = "rishi-automation-toolkit.zip"
BASE = f"https://github.com/{REPO}/releases/latest/download"
DEFAULT_DIR = Path.home() / "rishi-autopilot"
IS_WIN = os.name == "nt"
PRESERVE = {".env", "token.json", "client_secret.json"}


def say(msg: str = "") -> None:
    print(msg, flush=True)


def step(n: int, total: int, title: str) -> None:
    say(f"\n[{n}/{total}] {title}")


NON_INTERACTIVE = False


def interactive() -> bool:
    return not NON_INTERACTIVE and sys.stdin is not None and sys.stdin.isatty()


def ask(prompt: str, default: str = "", secret: bool = False) -> str:
    if not interactive():
        return default
    suffix = f" [{default}]" if default and not secret else ""
    try:
        val = (getpass.getpass if secret else input)(f"  {prompt}{suffix}: ").strip()
    except (EOFError, KeyboardInterrupt):
        say("\nCancelled.")
        sys.exit(130)
    return val or default


def yes(prompt: str, default: bool = True) -> bool:
    if not interactive():
        return default
    d = "Y/n" if default else "y/N"
    return (ask(f"{prompt} ({d})") or ("y" if default else "n")).lower().startswith("y")


def run(cmd, cwd=None, check=True, **kw):
    return subprocess.run([str(c) for c in cmd], cwd=cwd, check=check, **kw)


# ---------- paths ----------
def pipeline(root: Path) -> Path:
    return root / "youtube_pipeline"


def venv_python(root: Path) -> Path:
    return pipeline(root) / "venv" / ("Scripts/python.exe" if IS_WIN else "bin/python")


# ---------- download + extract ----------
def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "rishi-setup"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def get_zip(local_zip: str | None) -> bytes:
    if local_zip:
        return Path(local_zip).read_bytes()
    say(f"  downloading {BASE}/{ASSET}")
    data = fetch(f"{BASE}/{ASSET}")
    try:
        want = fetch(f"{BASE}/{ASSET}.sha256").decode().split()[0].lower()
        got = hashlib.sha256(data).hexdigest()
        if want != got:
            sys.exit(f"Checksum mismatch (expected {want[:12]}..., got {got[:12]}...). Aborting.")
        say("  checksum OK")
    except Exception:  # checksum file is optional
        say("  (no checksum file found, continuing)")
    return data


def extract(data: bytes, root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    base = root.resolve()
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for m in z.infolist():
            if m.is_dir():
                continue
            rel = m.filename[len("automation/"):] if m.filename.startswith("automation/") else m.filename
            if not rel:
                continue
            target = (root / rel).resolve()
            if base not in target.parents and target != base:
                sys.exit(f"Unsafe path in archive: {m.filename}")
            if target.name in PRESERVE and target.exists():
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(z.read(m))


# ---------- environment ----------
def check_prereqs() -> None:
    if sys.version_info < (3, 10):
        sys.exit(f"Python 3.10+ is required (you have {sys.version.split()[0]}).")
    if shutil.which("ffmpeg") is None:
        hint = {"nt": "winget install Gyan.FFmpeg", "posix": "brew install ffmpeg  |  sudo apt install ffmpeg"}[os.name]
        say(f"  WARNING: ffmpeg not found on PATH. Install it ({hint}) before making videos.")
    else:
        say("  ffmpeg found")


def ensure_venv(root: Path) -> Path:
    py = venv_python(root)
    if not py.exists():
        say("  creating virtual environment")
        run([sys.executable, "-m", "venv", pipeline(root) / "venv"])
    say("  installing dependencies (a few minutes the first time)")
    run([py, "-m", "pip", "install", "-q", "--disable-pip-version-check", "-r", pipeline(root) / "requirements.txt"])
    return py


def default_font() -> str:
    for p in ("C:/Windows/Fonts/arialbd.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        if Path(p).exists():
            return p
    return "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def read_env(path: Path) -> dict:
    out = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^([A-Z0-9_]+)=(.*)$", line.strip())
            if m:
                out[m.group(1)] = m.group(2)
    return out


def write_env(path: Path, updates: dict) -> None:
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    seen = set()
    for i, line in enumerate(lines):
        m = re.match(r"^([A-Z0-9_]+)=", line)
        if m and m.group(1) in updates:
            lines[i] = f"{m.group(1)}={updates[m.group(1)]}"
            seen.add(m.group(1))
    lines += [f"{k}={v}" for k, v in updates.items() if k not in seen]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if not IS_WIN:
        path.chmod(0o600)


def configure(root: Path) -> None:
    p = pipeline(root)
    env_path = p / ".env"
    if not env_path.exists():
        shutil.copy(p / ".env.example", env_path)
    cur = read_env(env_path)
    updates = {"FONT_PATH": default_font()}
    say("  Enter your own keys (input is hidden; press Enter to keep the current value / skip).")
    for key, label in (("ANTHROPIC_API_KEY", "Anthropic API key"),
                       ("ELEVENLABS_API_KEY", "ElevenLabs API key"),
                       ("PEXELS_API_KEY", "Pexels API key")):
        val = os.environ.get(key) or ask(f"{label}" + (" (set)" if cur.get(key) else ""), secret=True)
        if val:
            updates[key] = val
    updates["RSS_FEED_URL"] = ask("RSS feed to turn into videos", cur.get("RSS_FEED_URL") or "https://feeds.bbci.co.uk/news/technology/rss.xml")
    updates["NICHE_HINT"] = ask("Channel topic (one line)", cur.get("NICHE_HINT") or "technology news for a general audience")
    updates["YOUTUBE_PRIVACY"] = ask("YouTube privacy for uploads (private/unlisted/public)", cur.get("YOUTUBE_PRIVACY") or "private")
    write_env(env_path, updates)
    say(f"  saved {env_path}")


def youtube_login(root: Path) -> None:
    p = pipeline(root)
    if (p / "token.json").exists():
        say("  YouTube login already done (token.json found)")
        return
    secret = p / "client_secret.json"
    if not secret.exists():
        say("  You need a Google OAuth 'Desktop app' client file. Steps: docs/01-credentials.md")
        src = ask("Path to the downloaded client_secret JSON (Enter to skip for now)")
        if not src:
            say("  skipped. Later: put client_secret.json in youtube_pipeline/ and run: python rishi_setup.py doctor")
            return
        shutil.copy(Path(src.strip('"')).expanduser(), secret)
    if yes("Open the browser to log in to YouTube now?"):
        run([venv_python(root), "auth_youtube.py"], cwd=p, check=False)


def doctor(root: Path) -> bool:
    say("")
    return run([venv_python(root), "doctor.py"], cwd=pipeline(root), check=False).returncode == 0


# ---------- scheduling ----------
def schedule(root: Path) -> None:
    p, py = pipeline(root), venv_python(root)
    when = ask("Run every day at (HH:MM, 24h, this computer's time)", "14:00")
    if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", when):
        say("  invalid time, skipping")
        return
    hh, mm = when.split(":")
    if IS_WIN:
        ps = (f"$a=New-ScheduledTaskAction -Execute '{py}' -Argument 'main.py' -WorkingDirectory '{p}';"
              f"$t=New-ScheduledTaskTrigger -Daily -At {when};"
              "$s=New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries "
              "-ExecutionTimeLimit (New-TimeSpan -Hours 2);"
              "Register-ScheduledTask -TaskName 'RISHI Autopilot Daily' -Action $a -Trigger $t -Settings $s -Force | Out-Null")
        r = run(["powershell", "-NoProfile", "-Command", ps], check=False)
        say("  daily task 'RISHI Autopilot Daily' created" if r.returncode == 0 else "  could not create the task (try an Administrator terminal)")
    else:
        line = f"{int(mm)} {int(hh)} * * * cd '{p}' && '{py}' main.py >> '{p}/cron.log' 2>&1"
        old = subprocess.run(["crontab", "-l"], capture_output=True, text=True).stdout
        kept = "\n".join(l for l in old.splitlines() if "youtube_pipeline" not in l or "main.py" not in l)
        subprocess.run(["crontab", "-"], input=(kept + "\n" if kept else "") + line + "\n", text=True, check=False)
        say(f"  cron job added: {line}")
    say("  The computer must be on at that time. For always-on, see docs/04-deploy.md.")


# ---------- commands ----------
def cmd_install(a) -> None:
    root = Path(a.dir).expanduser().resolve()
    total = 6
    step(1, total, "Checking your computer")
    check_prereqs()
    step(2, total, f"Getting the toolkit into {root}")
    extract(get_zip(a.zip), root)
    step(3, total, "Python environment")
    ensure_venv(root)
    if a.update:
        say("\nUpdated. Your keys and YouTube login were kept.")
        return
    step(4, total, "Your keys")
    configure(root)
    step(5, total, "YouTube login")
    youtube_login(root)
    step(6, total, "Health check")
    ok = doctor(root)
    say("\nNext:")
    if ok and yes("Make your first video now? (uploads as private by default)", False):
        run([venv_python(root), "main.py"], cwd=pipeline(root), check=False)
    if ok and yes("Run it automatically every day?", True):
        schedule(root)
    say(f"\nDone. Folder: {root}")
    say("  make a video now:             python rishi_setup.py run")
    say("  Instagram/Facebook Reels:     python rishi_setup.py claude   (needs Claude Code + Claude in Chrome)")
    say("  guides:                       docs/ folder inside the install directory")


def installed_root(a) -> Path:
    root = Path(a.dir).expanduser().resolve()
    if not venv_python(root).exists():
        sys.exit(f"Not installed in {root}. Run: python rishi_setup.py")
    return root


def cmd_run(a) -> None:
    root = installed_root(a)
    sys.exit(run([venv_python(root), "main.py"], cwd=pipeline(root), check=False).returncode)


def cmd_doctor(a) -> None:
    sys.exit(0 if doctor(installed_root(a)) else 1)


def cmd_schedule(a) -> None:
    schedule(installed_root(a))


def cmd_claude(a) -> None:
    root = installed_root(a)
    claude = shutil.which("claude")
    if claude is None:
        say("Claude Code is not installed. Install it from https://claude.com/claude-code and add the Claude in Chrome extension,")
        say(f"then run:  cd \"{root}\"  &&  claude")
        say("The runbook is in docs/02-meta-reels-scheduling.md and the prompt in meta_scheduler/schedule_prompt.md.")
        return
    run([claude, "Read CLAUDE.md, then help me set up and run the Instagram and Facebook Reels scheduler."], cwd=root, check=False)


def main() -> None:
    ap = argparse.ArgumentParser(description="RISHI Autopilot installer and launcher")
    ap.add_argument("command", nargs="?", default="install", choices=["install", "run", "doctor", "schedule", "claude", "update"])
    ap.add_argument("--dir", default=str(DEFAULT_DIR), help=f"install folder (default {DEFAULT_DIR})")
    ap.add_argument("--zip", help="use a local toolkit zip instead of downloading (offline/testing)")
    ap.add_argument("--non-interactive", action="store_true",
                    help="never prompt; take keys from environment variables (ANTHROPIC_API_KEY, ELEVENLABS_API_KEY, PEXELS_API_KEY)")
    a = ap.parse_args()
    global NON_INTERACTIVE
    NON_INTERACTIVE = a.non_interactive
    a.update = a.command == "update"
    {"install": cmd_install, "update": cmd_install, "run": cmd_run, "doctor": cmd_doctor,
     "schedule": cmd_schedule, "claude": cmd_claude}[a.command](a)


if __name__ == "__main__":
    main()
