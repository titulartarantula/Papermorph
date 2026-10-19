"""Generate narration audio and word-mark timings with Edge TTS, Kokoro or ElevenLabs.

Usage (from the project root; SKILL is this skill's folder):
    uv run --with edge-tts $SKILL/scripts/tts.py content/ch01/narration.en.json site/ch01/audio/en
    uv run --python 3.12 --with kokoro $SKILL/scripts/tts.py ...      # narration with "engine": "kokoro"

The narration file names the engine ("edge", the default, or "kokoro"), the voice and the rate. Edge needs network
access. Kokoro (Apache 2.0) runs locally: its first run downloads the model (about 330 MB) and an English dictionary;
voices start with the accent's letter (am_michael, af_heart: American; bm_george, bf_emma: British) and its word
timings cover English. All engines need ffmpeg/ffprobe.

ElevenLabs (paid, per character; key from ELEVENLABS_API_KEY or a .env file in the working directory or a parent
folder, never from the narration file; no extra package):
    {"engine": "elevenlabs", "voice": "<voice id>", "model": "eleven_v4",
     "settings": {"speed": 0.96, "stability": 0.5, "similarity_boost": 0.75}, "beats": {...}}
"model" and "settings" are optional (settings are ElevenLabs voice_settings; speed 0.7-1.2); "rate" is not used.
Older narration files that say "provider": "elevenlabs" instead of "engine" still work. Word times come from the
API's character alignment.

Respell a word for the voice with {{shown|spoken}} (any engine): the voice says "spoken", captions show "shown".
The spoken text alone keys the audio cache, so adding a respelling around already-spoken text is free.

Narration text may contain [[mark]] tags placed before a word. The output
timings.js records each clip's duration and the time (seconds) at which the
word after every mark starts, so page animations can wait for that word,
plus one caption cue per sentence. Only beats whose text or voice changed are
regenerated; spoken word times are cached, so caption and mark rules can change
without new audio.

Narration files are read as UTF-8 (a byte order mark is allowed) on every platform.
Keep beat ids and mark names ASCII: they become file names and JS keys, and are
printed to the console.

Edge sometimes answers a request with no audio (NoAudioReceived), more often for
some voices; such a beat is requested again up to MAX_ATTEMPTS times with growing
pauses. If it still gets none, a short test phrase in the same voice tells whether
the voice is unavailable or this beat's text is the problem, and the run stops.
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
MAX_ATTEMPTS = 5          # requests per beat when Edge returns no audio
FIRST_RETRY_DELAY = 2     # seconds before the second request; doubles after each failure
PROBE_TEXT = "1, 2, 3."   # checks the voice after a beat fails; any voice reads digits in its own language


async def synth(text, voice, rate, mp3_path):
    import edge_tts
    words = []  # (seconds, word)
    comm = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
    with open(mp3_path, "wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                words.append((chunk["offset"] / 1e7, chunk["text"]))
    return words


async def synth_with_retries(beat, text, voice, rate, mp3_path):
    """synth(), requested again after NoAudioReceived; each attempt rewrites mp3_path from the start."""
    from edge_tts.exceptions import NoAudioReceived
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return await synth(text, voice, rate, mp3_path)
        except NoAudioReceived:
            if attempt == MAX_ATTEMPTS:
                raise
            delay = FIRST_RETRY_DELAY * 2 ** (attempt - 1)
            print(f"{beat}: Edge returned no audio, retrying in {delay} s (attempt {attempt + 1} of {MAX_ATTEMPTS})",
                  file=sys.stderr, flush=True)
            await asyncio.sleep(delay)


async def explain_no_audio(beat, voice, rate, out_dir):
    """The message for a beat that ran out of attempts: whether the voice or this beat's text failed."""
    from edge_tts.exceptions import NoAudioReceived
    with tempfile.NamedTemporaryFile(dir=out_dir, prefix=".probe-", suffix=".mp3", delete=False) as f:
        probe_path = Path(f.name)
    try:
        await synth(PROBE_TEXT, voice, rate, probe_path)
        voice_works = True
    except NoAudioReceived:
        voice_works = False
    finally:
        probe_path.unlink(missing_ok=True)
    if voice_works:
        return (f"{beat}: the voice {voice} works, but Edge returned no audio for this beat's text "
                f"{MAX_ATTEMPTS} times. Look for unusual characters in it, or split the beat.")
    return (f"{beat}: the voice {voice} returned no audio {MAX_ATTEMPTS} times, and also for a short test phrase, "
            "so the voice is unavailable at Edge right now; the text is not the cause. Completed beats are saved. "
            "Rerun later, or choose another voice for the whole book (uv run --with edge-tts edge-tts --list-voices).")


async def edge_beat(beat, text, voice, rate, mp3_path, out_dir):
    from edge_tts.exceptions import NoAudioReceived
    try:
        return await synth_with_retries(beat, text, voice, rate, mp3_path)
    except NoAudioReceived:
        raise SystemExit(await explain_no_audio(beat, voice, rate, out_dir)) from None


KOKORO = {}   # one pipeline per accent, loaded once per run


def kokoro_beat(text, voice, rate, mp3_path):
    """Synthesize locally with Kokoro; word start times come from its predicted durations."""
    import numpy as np
    from kokoro import KPipeline
    lang = voice[0]
    if lang not in KOKORO:
        KOKORO[lang] = KPipeline(lang_code=lang, repo_id="hexgrad/Kokoro-82M")
    speed = 1 + float(rate.rstrip("%")) / 100 if rate else 1
    words, chunks, offset = [], [], 0.0
    for r in KOKORO[lang](text, voice=voice, speed=speed):
        audio = np.asarray(r.audio, dtype=np.float32)
        for tk in r.tokens or []:
            if tk.start_ts is not None and any(c.isalnum() for c in tk.text):
                words.append((round(offset + tk.start_ts, 3), tk.text))
        chunks.append(audio)
        offset += len(audio) / 24000
    pcm = (np.clip(np.concatenate(chunks), -1, 1) * 32767).astype("<i2").tobytes()
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ar", "24000", "-ac", "1", "-i", "-",
                    "-b:a", "64k", str(mp3_path)], input=pcm, check=True)
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


def elevenlabs_beat(text, voice, model, settings, mp3_path):
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
    spec = json.loads(Path(src).read_text(encoding="utf-8-sig"))
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cache_path = Path(src).with_suffix(".timings.json")  # build cache, kept out of the site
    cache = json.loads(cache_path.read_text(encoding="utf-8-sig")) if cache_path.exists() else {}
    engine = spec.get("engine", spec.get("provider", "edge"))   # "provider": older ElevenLabs narration files
    voice = spec["voice"]
    if engine in ("edge", "kokoro"):
        rate = spec["rate"]
        tag = f"{voice}|{rate}" if engine == "edge" else f"{engine}|{voice}|{rate}"   # Edge keys stay as they were, so its audio is kept
    elif engine == "elevenlabs":
        rate, model, settings = None, spec.get("model", "eleven_v4"), spec.get("settings", {})
        tag = f"elevenlabs|{voice}|{model}|{json.dumps(settings, sort_keys=True)}"
    else:
        raise SystemExit(f"unknown engine {engine!r}: use edge, kokoro or elevenlabs")
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
        reusable = old and old.get("key") in (key, legacy_key if engine != "kokoro" else key) and "words" in old and mp3.exists() and mp3.stat().st_size > 0
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
                words = (kokoro_beat(clean, voice, rate, clip) if engine == "kokoro"
                         else elevenlabs_beat(clean, voice, model, settings, clip) if engine == "elevenlabs"
                         else await edge_beat(beat, clean, voice, rate, clip, out_dir))
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
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(0 if sys.argv[1:] in (["-h"], ["--help"]) else 2)
    asyncio.run(main(*sys.argv[1:3]))
