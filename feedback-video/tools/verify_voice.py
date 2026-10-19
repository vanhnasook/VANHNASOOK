#!/usr/bin/env python3
"""Transcribe every voice clip with Gemini and compare it to the script line.

Prints one row per clip: the expected caption, what was heard, and whether the
model judged it a match. Used to catch TTS clips that skip, repeat or add words.
"""
import base64, json, sys, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from tts import OUT, ROOT, api_key, tts_text  # noqa: E402

MODEL = "gemini-3.8-flash"


def main():
    script = json.loads((ROOT / "script.json").read_text())
    only = set(sys.argv[1:])
    parts, items = [], []
    for s in script["scenes"]:
        if only and s["id"] not in only:
            continue
        for i, line in enumerate(s["lines"]):
            cid = f"{s['id']}.{i}"
            items.append({"id": cid, "expected": tts_text(line["lo"], script["tts_replace"])})
            parts.append({"text": f"Clip {cid}:"})
            parts.append({"inlineData": {"mimeType": "audio/wav",
                                         "data": base64.b64encode((OUT / f"{cid}.wav").read_bytes()).decode()}})
    parts.append({"text": (
        "Transcribe each Lao audio clip above exactly, in Lao script. Compare with the expected text "
        "(spoken forms of numbers/URLs are fine). Return JSON only: a list of "
        '{"id","heard","match": true/false,"problem": "missing/extra/repeated/garbled words, or empty"}.\n\n'
        "Expected:\n" + "\n".join(f"{it['id']}: {it['expected']}" for it in items))})
    body = json.dumps({"contents": [{"parts": parts}],
                       "generationConfig": {"responseMimeType": "application/json"}}).encode()
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent",
        data=body, headers={"Content-Type": "application/json", "x-goog-api-key": api_key()})
    with urllib.request.urlopen(req, timeout=600) as r:
        result = json.loads(json.load(r)["candidates"][0]["content"]["parts"][-1]["text"])
    for row in result:
        flag = "OK " if row.get("match") else "BAD"
        print(f"{flag} {row['id']}: {row.get('heard')}" + (f"  <-- {row['problem']}" if row.get("problem") else ""))


if __name__ == "__main__":
    main()
