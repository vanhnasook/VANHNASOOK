#!/usr/bin/env python3
"""Lay the voice clips out on a timeline and write the caption files.

Each scene is: lead-in, its lines separated by `gap` (or the scene's own
`gaps` list), then a tail. Clips are
sped up by `voice_tempo` (pitch kept) and line timing comes from the measured
length of those clips, so captions match the voice exactly.

Writes build/timeline.json, build/timeline.js (for the page) and
output/captions.lo.srt / output/captions.en.srt.
"""
import json, subprocess, wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def srt_time(t):
    ms = round(t * 1000)
    return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"


def speed_up(src, tempo):
    """Copy a clip through ffmpeg atempo (pitch kept); returns (path, seconds)."""
    dst = ROOT / "build" / "audio" / f"tempo-{tempo}" / src.name
    if not dst.exists() or dst.stat().st_mtime < src.stat().st_mtime:
        dst.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-af", f"atempo={tempo}",
                        "-ar", "24000", "-ac", "1", str(dst)], check=True)
    with wave.open(str(dst)) as w:
        return dst, w.getnframes() / w.getframerate()


def main():
    script = json.loads((ROOT / "script.json").read_text())
    tempo = script.get("voice_tempo", 1.0)
    t, scenes = 0.0, []
    for s in script["scenes"]:
        start = t
        t += s["lead"]
        lines = []
        for i, line in enumerate(s["lines"]):
            if i:
                t += s.get("gaps", [script["gap"]] * len(s["lines"]))[i - 1]
            clip, dur = speed_up(ROOT / "build" / "audio" / f"{s['id']}.{i}.wav", tempo)
            lines.append({"lo": line["lo"], "en": line["en"], "start": round(t, 3), "end": round(t + dur, 3),
                          "audio": str(clip.relative_to(ROOT))})
            t += dur
        t += s["tail"]
        scenes.append({"id": s["id"], "start": round(start, 3), "end": round(t, 3), "lines": lines})
    timeline = {"duration": round(t, 3), "fps": 30, "width": 1920, "height": 1080, "scenes": scenes}
    (ROOT / "build" / "timeline.json").write_text(json.dumps(timeline, ensure_ascii=False, indent=1))
    (ROOT / "build" / "timeline.js").write_text("window.TIMELINE = " + json.dumps(timeline, ensure_ascii=False) + ";\n")

    out = ROOT / "output"
    out.mkdir(exist_ok=True)
    for lang in ("lo", "en"):
        rows = [l for s in scenes for l in s["lines"]]
        srt = "\n".join(f"{i}\n{srt_time(l['start'])} --> {srt_time(l['end'])}\n{l[lang]}\n"
                        for i, l in enumerate(rows, 1))
        (out / f"captions.{lang}.srt").write_text(srt)
    print(f"duration {t:.1f}s, {sum(len(s['lines']) for s in scenes)} caption lines")
    for s in scenes:
        print(f"  {s['id']:6} {s['start']:6.2f} - {s['end']:6.2f}")


if __name__ == "__main__":
    main()
