"""Step 3: ElevenLabs TTS with character-level timestamps (used for subtitles)."""
import base64
import logging
from pathlib import Path

import requests

import config

log = logging.getLogger(__name__)


def synthesize(script: str, out_path: Path) -> list[dict]:
    """Writes an mp3 and returns [{'word', 'start', 'end'}, ...]."""
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{config.ELEVENLABS_VOICE_ID}/with-timestamps"
    r = requests.post(
        url,
        headers={"xi-api-key": config.elevenlabs_key(), "Content-Type": "application/json"},
        json={
            "text": script,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75, "style": 0.2},
        },
        timeout=300,
    )
    r.raise_for_status()
    data = r.json()
    out_path.write_bytes(base64.b64decode(data["audio_base64"]))

    al = data["alignment"]
    words, buf, w_start, prev_end = [], "", None, 0.0
    for ch, s, e in zip(al["characters"], al["character_start_times_seconds"],
                        al["character_end_times_seconds"]):
        if ch.isspace():
            if buf:
                words.append({"word": buf, "start": w_start, "end": prev_end})
                buf, w_start = "", None
        else:
            if w_start is None:
                w_start = s
            buf += ch
            prev_end = e
    if buf:
        words.append({"word": buf, "start": w_start, "end": prev_end})
    log.info("Voiceover saved (%d words timed)", len(words))
    return words
