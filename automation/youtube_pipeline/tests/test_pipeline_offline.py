"""Network-free tests: word-timing parser and a full MoviePy render with fake footage/audio."""
import base64
import os
import shutil
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
for k in ("ANTHROPIC_API_KEY", "ELEVENLABS_API_KEY", "PEXELS_API_KEY"):
    os.environ.setdefault(k, "test")

import config  # noqa: E402
import voice  # noqa: E402

TEXT = "Hello brave new world, this is a test of the subtitle timing logic today"


def _fake_elevenlabs():
    chars = list(TEXT)
    starts = [i * 0.05 for i in range(len(chars))]
    return {
        "audio_base64": base64.b64encode(b"fake").decode(),
        "alignment": {
            "characters": chars,
            "character_start_times_seconds": starts,
            "character_end_times_seconds": [s + 0.05 for s in starts],
        },
    }


def _words(tmp_path):
    with mock.patch("voice.requests.post") as post:
        post.return_value.json.return_value = _fake_elevenlabs()
        post.return_value.raise_for_status = lambda: None
        return voice.synthesize(TEXT, tmp_path / "x.mp3")


def test_word_alignment_parsing(tmp_path):
    words = _words(tmp_path)
    assert [w["word"] for w in words] == TEXT.split()
    assert all(w["end"] >= w["start"] for w in words)


@pytest.mark.skipif(shutil.which("ffmpeg") is None or not Path(config.FONT_PATH).exists(),
                    reason="needs ffmpeg and the subtitle font")
def test_render_with_fake_footage(tmp_path):
    import visuals

    audio = tmp_path / "a.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    "sine=frequency=440:duration=5", str(audio)], check=True)

    def fake_pexels(query, dest, skip):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                        "testsrc=size=1280x720:rate=24:duration=2", "-pix_fmt", "yuv420p", str(dest)],
                       check=True)
        return dest

    words = [{"word": w["word"], "start": w["start"] * 0.4, "end": w["end"] * 0.4}
             for w in _words(tmp_path)]
    with mock.patch.object(visuals, "_pexels_clip", fake_pexels):
        out = visuals.build_video(audio, words, ["a", "b", "c"], tmp_path, tmp_path / "final.mp4")
    assert out.exists() and out.stat().st_size > 10_000
