# ວິດີໂອແນະນຳ: ແຈ້ງບັນຫາ ແລະ ສົ່ງຄຳຄິດເຫັນ ຜ່ານ lap.com.la

Motion-graphic tutorial (1920×1080, 30 fps, Lao voice-over and Lao captions) showing how to use
the anonymous **ກ່ອງຮັບຄຳຄິດເຫັນ & ແຈ້ງບັນຫາ** form on lap.com.la.

## Outputs (`output/`)

| File | What |
| --- | --- |
| `lap-feedback-guide.mp4` | Final video. Lao captions burned in; Lao + English subtitle tracks embedded (off by default). |
| `captions.lo.srt` | Lao captions, timed to the voice. |
| `captions.en.srt` | English translation of the captions. |

## How it is made

1. **Script**: `script.json` holds every narration line (Lao + English), per-scene lead-in/tail
   and the spelling substitutions used for speech (e.g. `lap.com.la` → `ແລັບ ດັອດ ຄອມ ດັອດ ແອວເອ`).
2. **Voice**: `tools/tts.py` records each scene with Gemini TTS (voice *Kore*) and cuts it into one
   clip per caption line. `tools/verify_voice.py` transcribes the clips back and flags any clip that
   skips, repeats or adds words. Takes are cached in `build/audio/`.
3. **Timeline**: `tools/timeline.py` speeds the clips up slightly (`voice_tempo`), lays them out,
   and writes `build/timeline.js` plus the SRT files, so captions match the voice exactly.
4. **Animation**: `index.html` + `src/main.js` build the scenes with GSAP. The phone shows the real
   screenshots from `assets/screens/`. Highlights, spotlight, finger taps, typed text, icons and
   panels are vector overlays drawn in the screenshot's own coordinates.
5. **Render**: `tools/render.mjs` seeks the page frame by frame in headless Chromium and encodes
   with ffmpeg (`build/video.mp4`). It also exports the sound-effect cue times.
6. **Sound**: `tools/mix.py` synthesises the music bed and sound effects, ducks the music under the
   voice, normalises to −16 LUFS and muxes the final MP4 with subtitle tracks.

## Rebuild

```bash
npm install
export GEMINI_API_KEY=...            # only needed to re-record the voice
python3 tools/tts.py step3           # re-record one scene (omit ids to record changed scenes)
python3 tools/verify_voice.py        # check the takes
npm run build                        # timeline -> render -> mix
```

Preview in a browser: serve the folder (`npx http-server .`) and open `index.html`
(space pauses, `?t=40` starts at 40 s). Stills for review: `node tools/render.mjs --stills 18,42.5`.

The screenshots are the two phone captures supplied for this video (home page and the open form).
The form content that appears being typed is an illustration added as an overlay.
