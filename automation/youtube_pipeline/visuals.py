"""Step 4: Pexels footage + MoviePy assembly with burned-in subtitles."""
import logging
import random
from pathlib import Path

import requests
from moviepy import (AudioFileClip, CompositeVideoClip, TextClip, VideoFileClip,
                     concatenate_videoclips)
from moviepy.video.fx import Loop

import config

log = logging.getLogger(__name__)
W, H = config.VIDEO_SIZE


def _pexels_clip(query: str, dest: Path, skip: set) -> Path | None:
    r = requests.get(
        "https://api.pexels.com/videos/search",
        headers={"Authorization": config.pexels_key()},
        params={"query": query, "orientation": "landscape", "size": "medium", "per_page": 15},
        timeout=30,
    )
    r.raise_for_status()
    videos = [v for v in r.json().get("videos", []) if v["id"] not in skip]
    random.shuffle(videos)
    for v in videos:
        files = [f for f in v["video_files"]
                 if f["file_type"] == "video/mp4" and f.get("width") and 1280 <= f["width"] <= 1920]
        if not files:
            continue
        best = max(files, key=lambda f: f["width"])
        with requests.get(best["link"], stream=True, timeout=120) as resp:
            resp.raise_for_status()
            with open(dest, "wb") as fh:
                for chunk in resp.iter_content(1 << 20):
                    fh.write(chunk)
        skip.add(v["id"])
        return dest
    return None


def _fit(clip: VideoFileClip, duration: float):
    clip = clip.without_audio()
    if clip.duration < duration:
        clip = clip.with_effects([Loop(duration=duration)])
    else:
        clip = clip.subclipped(0, duration)
    clip = clip.resized(max(W / clip.w, H / clip.h))
    return clip.cropped(width=W, height=H, x_center=clip.w / 2, y_center=clip.h / 2)


def _subtitle_clips(words: list[dict], per_chunk: int = 4):
    clips = []
    for i in range(0, len(words), per_chunk):
        chunk = words[i:i + per_chunk]
        start = chunk[0]["start"]
        # hold until the next chunk begins so there is no flicker between lines
        end = words[i + per_chunk]["start"] if i + per_chunk < len(words) else chunk[-1]["end"] + 0.3
        txt = TextClip(
            font=config.FONT_PATH, text=" ".join(w["word"] for w in chunk).upper(),
            font_size=72, color="white", stroke_color="black", stroke_width=4,
            method="caption", size=(W - 300, 200), text_align="center",
        )
        clips.append(txt.with_start(start).with_duration(end - start)
                        .with_position(("center", 0.78), relative=True))
    return clips


def build_video(audio_path: Path, words: list[dict], queries: list[str],
                work: Path, out_path: Path) -> Path:
    audio = AudioFileClip(str(audio_path))
    total = audio.duration + 0.5
    per_scene = total / len(queries)

    skip: set = set()
    scenes, handles = [], []
    for i, q in enumerate(queries):
        dest = work / f"scene_{i}.mp4"
        p = _pexels_clip(q, dest, skip) or _pexels_clip("abstract technology", dest, skip)
        if p is None:
            log.warning("No footage for %r, skipping", q)
            continue
        src = VideoFileClip(str(p))
        handles.append(src)
        scenes.append(_fit(src, total / len(queries)))
    if not scenes:
        raise RuntimeError("No stock footage could be fetched")

    base = concatenate_videoclips(scenes, method="chain").with_duration(total)
    final = CompositeVideoClip([base, *_subtitle_clips(words)], size=(W, H)).with_audio(audio)
    final.write_videofile(str(out_path), fps=config.FPS, codec="libx264", audio_codec="aac",
                          preset="medium", threads=2, logger=None)
    for c in handles + [audio]:
        c.close()
    log.info("Rendered %s", out_path)
    return out_path
