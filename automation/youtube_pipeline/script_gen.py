"""Step 2: Claude turns the article into a script + YouTube metadata."""
import json
import logging
import re

import anthropic

import config

log = logging.getLogger(__name__)

SYSTEM = """You are a veteran YouTube scriptwriter for a channel about {niche}.
Write ORIGINAL commentary and explanation inspired by the source article. Do not copy its
sentences; add context, analysis and a clear point of view. Attribute the source by name
in the script. Never invent facts that are not in the source."""

PROMPT = """Source article title: {title}
Source URL: {link}

Source text:
\"\"\"
{text}
\"\"\"

Produce a video package for a ~3 minute video (about 430-480 spoken words).
Script rules: strong hook in the first sentence, short punchy sentences, conversational tone,
smooth transitions, a closing line that invites viewers to subscribe. Plain spoken text only:
no stage directions, no headings, no emojis, no markdown.

Return ONLY valid JSON with this shape:
{{
  "title": "<=70 chars, curiosity-driven but not misleading",
  "description": "2-3 paragraph description, include 'Source: {link}' and 3-5 hashtags at the end",
  "tags": ["10-15 tags"],
  "script": "the full narration text",
  "scene_queries": ["8-10 concrete 1-3 word stock-footage search queries, in narrative order"]
}}"""


def _extract_json(raw: str) -> dict:
    raw = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.M).strip()
    return json.loads(raw[raw.find("{"):raw.rfind("}") + 1])


def generate_package(article: dict, retries: int = 3) -> dict:
    client = anthropic.Anthropic(api_key=config.anthropic_key())
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            msg = client.messages.create(
                model=config.CLAUDE_MODEL,
                max_tokens=4000,
                system=SYSTEM.format(niche=config.NICHE_HINT),
                messages=[{"role": "user", "content": PROMPT.format(**article)}],
            )
            pkg = _extract_json(msg.content[0].text)
            words = len(pkg["script"].split())
            if not 300 <= words <= 700:
                raise ValueError(f"Script length {words} words out of range")
            if not pkg.get("scene_queries"):
                raise ValueError("No scene queries")
            log.info("Script ready: %d words, title=%r", words, pkg["title"])
            return pkg
        except Exception as e:  # malformed JSON, bad length, API hiccup
            last_err = e
            log.warning("Script attempt %d failed: %s", attempt, e)
    raise RuntimeError(f"Script generation failed: {last_err}")
