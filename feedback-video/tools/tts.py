#!/usr/bin/env python3
"""Generate the Lao voice-over with Gemini TTS and split it into caption lines.

One request per scene (lines joined by line breaks); the scene audio is then cut
at its longest pauses into one clip per caption line. Each take is transcribed
back with Gemini and re-recorded if any clip adds, drops or changes words. Results are cached by text
hash in build/audio, so re-running only re-records scenes whose text changed.

Pass scene ids to re-record just those scenes; every other scene keeps its
current take. API key: GEMINI_API_KEY, or a file path in GEMINI_API_KEY_FILE. Never commit it.
"""
import base64, hashlib, io, json, os, sys, time, urllib.error, urllib.request, wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "build" / "audio"
MODELS = ["gemini-3.8-flash-tts", "gemini-3.1-flash-tts-preview", "gemini-2.5-flash-preview-tts", "gemini-2.5-pro-preview-tts"]
RATE = 24000


def api_key():
    if os.environ.get("GEMINI_API_KEY"):
        return os.environ["GEMINI_API_KEY"].strip()
    if os.environ.get("GEMINI_API_KEY_FILE"):
        return Path(os.environ["GEMINI_API_KEY_FILE"]).read_text().strip()
    sys.exit("Set GEMINI_API_KEY or GEMINI_API_KEY_FILE")


def tts_text(text, replacements):
    for a, b in replacements:
        text = text.replace(a, b)
    return text


def request_tts(prompt, voice, key):
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}},
        },
    }).encode()
    for model in MODELS:
        for attempt in range(4):
            req = urllib.request.Request(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                data=body, headers={"Content-Type": "application/json", "x-goog-api-key": key})
            try:
                with urllib.request.urlopen(req, timeout=300) as r:
                    data = json.load(r)
                part = data["candidates"][0]["content"]["parts"][0]["inlineData"]
                return decode_audio(base64.b64decode(part["data"])), model
            except urllib.error.HTTPError as e:
                msg = e.read().decode(errors="replace")[:200]
                if e.code == 429:
                    print(f"  {model}: quota exhausted, trying next model", file=sys.stderr)
                    break
                if e.code in (500, 503) and attempt < 3:
                    time.sleep(2 ** (attempt + 2))
                    continue
                raise SystemExit(f"{model}: HTTP {e.code} {msg}")
            except (KeyError, IndexError):
                print(f"  {model}: no audio in response, retrying", file=sys.stderr)
                time.sleep(3)
    raise SystemExit("All TTS models failed")


def decode_audio(raw):
    if raw[:4] == b"RIFF":
        with wave.open(io.BytesIO(raw)) as w:
            assert w.getframerate() == RATE and w.getsampwidth() == 2
            raw = w.readframes(w.getnframes())
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0


def save_wav(path, samples):
    pcm = (np.clip(samples, -1, 1) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(RATE)
        w.writeframes(pcm.tobytes())


def load_wav(path):
    with wave.open(str(path)) as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0


def silent_runs(x, frame=0.01, thresh_db=-42):
    """Return (start, end) sample ranges of silence longer than 120 ms."""
    n = int(RATE * frame)
    frames = x[: len(x) // n * n].reshape(-1, n)
    db = 20 * np.log10(np.sqrt((frames ** 2).mean(axis=1)) + 1e-9)
    quiet = db < thresh_db
    runs, start = [], None
    for i, q in enumerate(np.append(quiet, False)):
        if q and start is None:
            start = i
        elif not q and start is not None:
            if i - start >= 12:
                runs.append((start * n, i * n))
            start = None
    return runs


def trim(x, pad=0.06):
    idx = np.where(np.abs(x) > 0.01)[0]
    if not len(idx):
        return x
    p = int(pad * RATE)
    return x[max(idx[0] - p, 0): idx[-1] + p]


def split_lines(audio, texts):
    """Cut scene audio at its len(texts)-1 longest internal pauses."""
    if len(texts) == 1:
        return [trim(audio)]
    audio = trim(audio, pad=0)
    runs = [r for r in silent_runs(audio) if r[0] > 0 and r[1] < len(audio)]
    if len(runs) < len(texts) - 1:
        return None
    cuts = sorted(sorted(runs, key=lambda r: r[1] - r[0], reverse=True)[: len(texts) - 1])
    bounds = [0] + [(a + b) // 2 for a, b in cuts] + [len(audio)]
    clips = [trim(audio[bounds[i]: bounds[i + 1]]) for i in range(len(texts))]
    # sanity: seconds per character should be roughly even across the lines
    rates = [len(c) / RATE / max(len(t), 1) for c, t in zip(clips, texts)]
    if max(rates) > 2.2 * min(rates):
        return None
    return clips


def check_takes(clips, texts, key, model="gemini-3.8-flash"):
    """Transcribe the clips and return a list of problems (empty when every clip reads its line)."""
    parts = []
    for i, c in enumerate(clips):
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(RATE)
            w.writeframes((np.clip(c, -1, 1) * 32767).astype(np.int16).tobytes())
        parts += [{"text": f"Clip {i}:"}, {"inlineData": {"mimeType": "audio/wav", "data": base64.b64encode(buf.getvalue()).decode()}}]
    parts.append({"text": "Transcribe each Lao clip and compare it with its expected text (spoken forms of numbers are fine). "
                          "A clip fails if it adds, drops, repeats or changes words, or reads any instructions aloud. "
                          'Return JSON only: [{"clip": 0, "ok": true, "problem": ""}].\n\nExpected:\n'
                          + "\n".join(f"Clip {i}: {t}" for i, t in enumerate(texts))})
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=json.dumps({"contents": [{"parts": parts}], "generationConfig": {"responseMimeType": "application/json"}}).encode(),
        headers={"Content-Type": "application/json", "x-goog-api-key": key})
    with urllib.request.urlopen(req, timeout=300) as r:
        rows = json.loads(json.load(r)["candidates"][0]["content"]["parts"][-1]["text"])
    return [f"clip {row['clip']}: {row.get('problem')}" for row in rows if not row.get("ok")]


def main():
    script = json.loads((ROOT / "script.json").read_text())
    OUT.mkdir(parents=True, exist_ok=True)
    key = api_key()
    manifest = {}
    only = set(sys.argv[1:])
    for scene in script["scenes"]:
        texts = [tts_text(l["lo"], script["tts_replace"]) for l in scene["lines"]]
        prompt = script["style"] + "\n\n" + "\n\n".join(texts)
        digest = hashlib.sha1((script["voice"] + "\n\n".join(texts)).encode()).hexdigest()[:12]
        meta_path = OUT / f"{scene['id']}.json"
        meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
        if meta and only and scene["id"] not in only:
            meta["hash"] = digest  # keep the current take
            meta_path.write_text(json.dumps(meta))
        if meta.get("hash") == digest and scene["id"] not in only:
            manifest[scene["id"]] = meta
            continue
        print(f"[tts] {scene['id']} ({len(texts)} lines)")
        clips = None
        for attempt in range(4):
            if scene.get("per_line"):  # one request per line: no pause-based cutting
                takes = [request_tts(script["style"] + "\n\n" + t, script["voice"], key) for t in texts]
                clips, model = [trim(a) for a, _ in takes], takes[-1][1]
                audio = np.concatenate(clips)
            else:
                audio, model = request_tts(prompt, script["voice"], key)
                clips = split_lines(audio, texts)
            if not clips:
                print("  could not split scene into lines, re-recording", file=sys.stderr)
                continue
            problems = check_takes(clips, texts, key)
            if not problems:
                break
            print(f"  take {attempt + 1} rejected: {problems}", file=sys.stderr)
            clips = None
        if not clips:
            sys.exit(f"{scene['id']}: no clean take after 4 attempts; keeping the previous audio")
        save_wav(OUT / f"{scene['id']}.full.wav", audio)
        durations = []
        for i, c in enumerate(clips):
            save_wav(OUT / f"{scene['id']}.{i}.wav", c)
            durations.append(round(len(c) / RATE, 3))
        meta = {"hash": digest, "model": model, "durations": durations}
        meta_path.write_text(json.dumps(meta))
        manifest[scene["id"]] = meta
        print(f"  {model}: {durations}")
    (ROOT / "build" / "voice.json").write_text(json.dumps(manifest, indent=1))


if __name__ == "__main__":
    main()
