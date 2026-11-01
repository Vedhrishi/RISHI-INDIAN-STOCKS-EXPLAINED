"""Daily pipeline entrypoint:  python main.py"""
import logging
import shutil
import sys
import time

import requests

import config
import scraper
import script_gen
import uploader
import visuals
import voice


def notify(msg: str) -> None:
    if config.NOTIFY_WEBHOOK:
        try:  # "text" for Slack, "content" for Discord
            requests.post(config.NOTIFY_WEBHOOK, json={"text": msg, "content": msg}, timeout=10)
        except Exception:
            pass


def run() -> None:
    article = scraper.get_next_article()
    pkg = script_gen.generate_package(article)

    work = config.OUTPUT_DIR / time.strftime("%Y%m%d-%H%M%S")
    work.mkdir(parents=True, exist_ok=True)
    (work / "package.txt").write_text(
        f"{pkg['title']}\n\n{pkg['description']}\n\n{pkg['script']}", encoding="utf-8")

    audio = work / "voice.mp3"
    words = voice.synthesize(pkg["script"], audio)
    video = visuals.build_video(audio, words, pkg["scene_queries"], work, work / "final.mp4")
    vid = uploader.upload(video, pkg["title"], pkg["description"], pkg["tags"])

    scraper.mark_used(article["link"])  # only after a successful upload
    notify(f"Uploaded: https://youtu.be/{vid} ({pkg['title']})")

    for p in work.glob("scene_*.mp4"):
        p.unlink()
    runs = sorted(d for d in config.OUTPUT_DIR.iterdir() if d.is_dir())
    for old in runs[:-7]:  # keep the last 7 runs on disk
        shutil.rmtree(old, ignore_errors=True)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
                        handlers=[logging.StreamHandler(sys.stdout)])
    try:
        run()
    except Exception as e:
        logging.exception("Pipeline failed")
        notify(f"YouTube pipeline FAILED: {e}")
        sys.exit(1)
