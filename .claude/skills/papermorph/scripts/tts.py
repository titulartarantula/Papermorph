"""Generate narration audio and word-mark timings with Edge TTS (default) or ElevenLabs.

Usage (from the project root; SKILL is this skill's folder):
    uv run --with edge-tts $SKILL/scripts/tts.py content/ch01/narration.en.json site/ch01/audio/en

Needs network access and ffprobe (from ffmpeg) for clip durations.

The narration file picks the provider. Edge TTS (no key):
    {"voice": "en-US-AndrewMultilingualNeural", "rate": "-4%", "beats": {...}}
ElevenLabs (paid, per character; key from ELEVENLABS_API_KEY or a .env file in the
working directory or a parent folder, never from the narration file):
    {"provider": "elevenlabs", "voice": "<voice id>", "model": "eleven_v4",
     "settings": {"speed": 0.96, "stability": 0.5, "similarity_boost": 0.75}, "beats": {...}}
"model" and "settings" are optional (settings are ElevenLabs voice_settings; speed 0.7-1.2).
Respell a word for the voice with {{shown|spoken}}: the voice says "spoken", captions show "shown".
The spoken text alone keys the audio cache, so adding a respelling around already-spoken text is free.
Word times come from the API's character alignment.

Narration text may contain [[mark]] tags placed before a word. The output
timings.js records each clip's duration and the time (seconds) at which the
word after every mark starts, so page animations can wait for that word,
plus one caption cue per sentence. Only beats whose text or voice changed are
regenerated; spoken word times are cached, so caption and mark rules can change
without new audio.
"""

import asyncio
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

MARK = re.compile(r"\[\[(\w+)\]\]")
# {{shown|spoken}}: the voice reads "spoken"; captions show "shown" (e.g. {{honne|honneh}}).
SAY = re.compile(r"\{\{([^|{}]+)\|([^{}]+)\}\}")


async def synth(text, voice, rate, mp3_path):
    import edge_tts  # only needed for the default provider
    words = []  # (seconds, word)
    comm = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
    with open(mp3_path, "wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                words.append((chunk["offset"] / 1e7, chunk["text"]))
    return words


def api_key(name="ELEVENLABS_API_KEY"):
    """The key from the environment, else from the nearest .env file (KEY=VALUE lines)."""
    if os.environ.get(name):
        return os.environ[name].strip()
    for d in [Path.cwd(), *Path.cwd().parents]:
        env = d / ".env"
        if env.is_file():
            for line in env.read_text(encoding="utf-8").splitlines():
                k, sep, v = line.partition("=")
                v = v.strip().strip('"').strip("'")
                if sep and k.strip() == name and v:
                    return v
    raise SystemExit(f"{name} is not set (environment variable or .env file)")


def synth_elevenlabs(text, voice, model, settings, mp3_path):
    """Write the clip; return [(seconds, word)] grouped from the character alignment."""
    body = {"text": text, "model_id": model}
    if settings:
        body["voice_settings"] = settings
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice}/with-timestamps?output_format=mp3_44100_128",
        data=json.dumps(body).encode(), method="POST",
        headers={"xi-api-key": api_key(), "Content-Type": "application/json", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise SystemExit(f"ElevenLabs error {e.code}: {e.read().decode(errors='replace')[:400]}")
    Path(mp3_path).write_bytes(base64.b64decode(data["audio_base64"]))
    al = data.get("alignment") or {}
    words, cur, start = [], "", None
    for ch, t in zip(al.get("characters", []), al.get("character_start_times_seconds", [])):
        if ch.isspace():
            if cur:
                words.append((start, cur))
            cur, start = "", None
        else:
            if not cur:
                start = t
            cur += ch
    if cur:
        words.append((start, cur))
    if not words:
        raise SystemExit("ElevenLabs returned no character alignment")
    return words


def split_marks(raw):
    """Return spoken text, {mark: char position in it} and [(spoken, shown)] caption respellings."""
    shown = [(m.group(2), m.group(1)) for m in SAY.finditer(raw)]
    raw = SAY.sub(lambda m: m.group(2), raw)
    marks, clean, pos = {}, [], 0
    # MARK.split alternates text, name, text, name, ...
    for i, part in enumerate(MARK.split(raw)):
        if i % 2:
            if part in marks:
                raise ValueError(f"duplicate mark {part!r} in one beat")
            marks[part] = pos
        else:
            clean.append(part)
            pos += len(part)
    return "".join(clean), marks, shown


def time_at(clean, words):
    """Return f(pos): start time of the first spoken word at or after char pos."""
    cursor, located = 0, []
    for t, w in words:
        i = clean.find(w, cursor)
        if i < 0:
            continue
        located.append((i, t))
        cursor = i + len(w)
    return lambda pos: next((round(t, 3) for i, t in located if i >= pos), None)


def mark_times(clean, marks, words):
    at, out = time_at(clean, words), {}
    for name, pos in marks.items():
        out[name] = at(pos)
        if out[name] is None:
            raise SystemExit(f"mark {name!r} not matched to a spoken word")
    return out


def respell(cues, shown):
    """Show each {{shown|spoken}} pair's written form in the captions."""
    for spoken, written in shown:
        pat = re.compile(r"(?<!\w)" + re.escape(spoken) + r"(?!\w)")
        cues = [[t, pat.sub(written, text)] for t, text in cues]
    return cues


def caption_cues(clean, words):
    """One cue per sentence: [start seconds, sentence]."""
    at, cues, start = time_at(clean, words), [], 0
    for m in list(re.finditer(r"[.?!]\s+", clean)) + [None]:
        end = m.end() if m else len(clean)
        text = clean[start:end].strip()
        if text:
            cues.append([at(start) or 0, text])
        start = end
    return cues


def duration(mp3):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(mp3)],
        capture_output=True, text=True, check=True)
    return round(float(r.stdout), 3)


def write_atomic(path, text):
    """Replace output only after its complete contents have been written."""
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}-", delete=False) as f:
        tmp = Path(f.name)
    try:
        tmp.write_text(text, encoding="utf-8")
        tmp.replace(path)
    finally:
        tmp.unlink(missing_ok=True)


async def main(src, out_dir):
    spec = json.loads(Path(src).read_text())
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cache_path = Path(src).with_suffix(".timings.json")  # build cache, kept out of the site
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    provider = spec.get("provider", "edge")
    voice = spec["voice"]
    if provider == "edge":
        rate = spec["rate"]
        tag = f"{voice}|{rate}"   # unchanged from earlier versions, so existing caches stay valid
    elif provider == "elevenlabs":
        rate, model, settings = None, spec.get("model", "eleven_v4"), spec.get("settings", {})
        tag = f"elevenlabs|{voice}|{model}|{json.dumps(settings, sort_keys=True)}"
    else:
        raise SystemExit(f"unknown provider {provider!r} (edge or elevenlabs)")
    result = {}
    public = lambda v: {k: v[k] for k in ("dur", "marks", "cues")}
    live = {b: public(v) for b, v in cache.items()
            if {"dur", "marks", "cues"} <= v.keys() and (out_dir / f"{b}.mp3").exists()}
    timings_path = out_dir / "timings.js"
    for beat, raw in spec["beats"].items():
        mp3 = out_dir / f"{beat}.mp3"
        old = cache.get(beat)
        clean, marks, shown = split_marks(raw)
        key = hashlib.sha1(f"{tag}|{clean}".encode()).hexdigest()
        # Existing caches included [[marks]] in the key; reuse an unchanged old beat once,
        # then save its spoken-text key so future mark edits do not regenerate audio.
        legacy_key = hashlib.sha1(f"{tag}|{raw}".encode()).hexdigest()
        reusable = old and old.get("key") in (key, legacy_key) and "words" in old and mp3.exists() and mp3.stat().st_size > 0
        tmp = None
        if reusable:
            words = old["words"]
            clip = mp3
        else:
            with tempfile.NamedTemporaryFile(dir=out_dir, prefix=f".{beat}-", suffix=".mp3", delete=False) as f:
                tmp = Path(f.name)
            clip = tmp
        try:
            if not reusable:
                words = (await synth(clean, voice, rate, clip) if provider == "edge"
                         else synth_elevenlabs(clean, voice, model, settings, clip))
            entry = {"key": key, "dur": duration(clip), "words": words,
                     "marks": mark_times(clean, marks, words), "cues": respell(caption_cues(clean, words), shown)}
            if tmp:
                tmp.replace(mp3)
                print(f"{beat}: synthesized")
            result[beat] = entry
            cache[beat] = entry
            # A later failed beat must not discard the successful beats' cache.
            write_atomic(cache_path, json.dumps(cache, indent=1))
            # Keep the successful MP3's timings consistent even if a later beat fails.
            live[beat] = public(entry)
            write_atomic(timings_path, "window.TIMINGS = " + json.dumps(live, indent=1) + ";\n")
        finally:
            if tmp:
                tmp.unlink(missing_ok=True)
    write_atomic(cache_path, json.dumps(result, indent=1))
    js = {b: public(v) for b, v in result.items()}
    write_atomic(timings_path, "window.TIMINGS = " + json.dumps(js, indent=1) + ";\n")


if __name__ == "__main__":
    asyncio.run(main(*sys.argv[1:3]))
