#!/usr/bin/env python3
"""Build the soundtrack and mux the final video.

- background music: synthesised here (soft pad, marimba arpeggio, bass, shaker)
- sound effects: synthesised, placed at the cue times the page exported (build/sfx.json)
- voice: the timed clips from build/timeline.json; music ducks under the voice
- loudness: two-pass EBU R128 normalisation to -16 LUFS

Writes build/mix.wav and output/lap-feedback-guide.mp4 (Lao captions burned in,
Lao + English subtitle tracks embedded).
"""
import json, subprocess, sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
SR = 48000
rand = np.random.default_rng(11)


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def env_adsr(n, a, r, sr=SR):
    e = np.ones(n)
    na, nr = int(a * sr), int(r * sr)
    e[:na] = np.linspace(0, 1, na) if na else 1
    if nr:
        e[-nr:] *= np.linspace(1, 0, nr)
    return e


def lowpass(x, cutoff):
    """One-pole low-pass; cutoff may be a scalar or a per-sample array."""
    c = np.broadcast_to(np.asarray(cutoff, dtype=float), x.shape)
    a = 1 - np.exp(-2 * np.pi * c / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc += a[i] * (x[i] - acc)
        y[i] = acc
    return y


def fft_lowpass(x, cutoff):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= 1 / (1 + (f / cutoff) ** 4)
    return np.fft.irfft(X, len(x))


def fft_highpass(x, cutoff):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= 1 / (1 + (cutoff / np.maximum(f, 1e-3)) ** 4)
    return np.fft.irfft(X, len(x))


def reverb(st, seconds=2.2, wet=.28):
    n = int(seconds * SR)
    t = np.arange(n) / SR
    out = np.zeros((st.shape[0] + n, 2))
    for ch in range(2):
        ir = rand.standard_normal(n) * np.exp(-t * 3.2)
        ir = fft_lowpass(ir, 6000)
        ir /= np.sqrt((ir ** 2).sum())
        L = st.shape[0] + n
        size = 1 << (L - 1).bit_length()
        out[:, ch] = np.fft.irfft(np.fft.rfft(st[:, ch], size) * np.fft.rfft(ir, size), size)[:L]
    dry = np.vstack([st, np.zeros((n, 2))])
    return (dry * (1 - wet) + out * wet)[: st.shape[0]]


# ------------------------------------------------------------------ music

CHORDS = [  # root, pad voicing (MIDI), arpeggio tones
    (36, [48, 55, 59, 62, 64], [64, 67, 71, 74, 76, 79]),   # Cmaj9
    (33, [45, 52, 55, 60, 64], [64, 67, 69, 72, 76, 79]),   # Am7
    (29, [41, 48, 52, 57, 60], [64, 65, 69, 72, 76, 77]),   # Fmaj7
    (31, [43, 50, 55, 59, 62], [62, 67, 71, 74, 79, 81]),   # G6
]


def music(duration, bpm=96):
    beat = 60 / bpm
    bar = beat * 4
    n = int((duration + 3) * SR)
    L = np.zeros(n); R = np.zeros(n)
    ML = np.zeros(n); MR = np.zeros(n)  # mallet bus, filtered separately

    def add(sig, start, pan=0.0, gain=1.0, bus=None):
        i = int(start * SR)
        if i >= n:
            return
        sig = sig[: n - i] * gain
        l, r = bus or (L, R)
        l[i:i + len(sig)] += sig * np.cos((pan + 1) * np.pi / 4)
        r[i:i + len(sig)] += sig * np.sin((pan + 1) * np.pi / 4)

    chord_len = bar * 2
    k = 0
    while k * chord_len < duration + 2:
        root, pad, arp = CHORDS[k % len(CHORDS)]
        t0 = k * chord_len
        # pad: detuned soft saws, slow attack, overlapping release
        m = int((chord_len + 1.6) * SR)
        tt = np.arange(m) / SR
        for j, note in enumerate(pad):
            for det, pan in ((-.0014, -.5), (.0014, .5)):
                f = midi(note) * (1 + det)
                sig = sum(np.sin(2 * np.pi * f * h * tt + h) / h ** 1.6 for h in range(1, 7))
                sig *= env_adsr(m, 1.2, 1.6) * (1 + .15 * np.sin(2 * np.pi * .23 * tt + j))
                add(sig, t0, pan, .010)
        # bass on beats 1 and 3
        for b in range(0, 8, 2):
            m2 = int(beat * 1.9 * SR)
            tt2 = np.arange(m2) / SR
            f = midi(root)
            sig = (np.sin(2 * np.pi * f * tt2) + .35 * np.sin(4 * np.pi * f * tt2)) * np.exp(-tt2 * 2.2) * env_adsr(m2, .01, .08)
            add(sig, t0 + b * beat, 0, .09)
        # soft marimba, an octave down, mostly quarter notes with a few eighth pickups
        steps = [(0, 0), (2, 2), (4, 4), (6, 2), (7, 3), (8, 1), (10, 3), (12, 5), (14, 3)]
        for e, idx in steps:
            if k % 2 and e == 7:
                continue
            note = arp[idx] - 12
            m3 = int(1.4 * SR)
            tt3 = np.arange(m3) / SR
            f = midi(note)
            vel = .75 + .25 * rand.random()
            sig = (np.sin(2 * np.pi * f * tt3) * np.exp(-tt3 * 4.2)
                   + .09 * np.sin(2 * np.pi * f * 3.9 * tt3) * np.exp(-tt3 * 18)
                   + .015 * np.sin(2 * np.pi * f * 9.2 * tt3) * np.exp(-tt3 * 40)) * env_adsr(m3, .008, .08)
            add(sig, t0 + e * beat / 2, (-.55, .55)[(e // 2) % 2], .032 * vel, bus=(ML, MR))
        k += 1

    # shaker on off-beat sixteenths, very soft
    hit = fft_highpass(rand.standard_normal(int(.06 * SR)), 6000) * np.exp(-np.arange(int(.06 * SR)) / SR * 70)
    s = 0
    while s * beat / 4 < duration + 2:
        if s % 2:
            add(hit, s * beat / 4, .25, (.010 if s % 4 == 3 else .006))
        s += 1

    L += fft_lowpass(ML, 2800); R += fft_lowpass(MR, 2800)
    st = np.stack([L, R], axis=1)
    st = reverb(st, 2.6, .36)
    fade = np.ones(n)
    fade[: int(1.5 * SR)] = np.linspace(0, 1, int(1.5 * SR))
    end = int(duration * SR)
    fade[end - int(3.5 * SR): end] = np.linspace(1, 0, int(3.5 * SR))
    fade[end:] = 0
    st *= fade[:, None]
    return st[:end]


# -------------------------------------------------------------- effects

def noise(sec):
    return rand.standard_normal(int(sec * SR))


def sweep_noise(sec, f0, f1, peak=.45):
    n = int(sec * SR)
    t = np.linspace(0, 1, n)
    cut = f0 * (f1 / f0) ** t
    x = lowpass(noise(sec), cut) - .7 * lowpass(noise(sec), cut * .25)
    e = np.where(t < peak, (t / peak) ** 2, ((1 - t) / (1 - peak)) ** 1.5)
    return x * e


def tone(sec, f0, f1, decay, harmonics=((1, 1),)):
    n = int(sec * SR)
    t = np.arange(n) / SR
    f = f0 * (f1 / f0) ** (t / sec)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return sum(a * np.sin(h * ph) for h, a in harmonics) * np.exp(-t * decay) * env_adsr(n, .004, .01)


def layer(*parts):
    """Sum signals of different lengths."""
    out = np.zeros(max(len(p) for p in parts))
    for p in parts:
        out[: len(p)] += p
    return out


def make_sfx():
    fx = {
        'whoosh': sweep_noise(.55, 300, 3200) * 1.6,
        'swish': sweep_noise(.32, 800, 6000, .35) * 1.3,
        'swoosh': sweep_noise(1.0, 250, 4200, .55) * 1.6,
        'rise': layer(sweep_noise(1.4, 150, 5000, .8) * 1.4, tone(1.4, 220, 660, .4) * .15),
        'pop': tone(.12, 520, 980, 30, ((1, 1), (2, .2))) * .8,
        'tap': layer(tone(.05, 1800, 1400, 90) * .5, tone(.09, 180, 90, 40) * .9),
        'type': fft_highpass(noise(.018), 2500) * np.exp(-np.arange(int(.018 * SR)) / SR * 260) * .35,
        'tick': tone(.08, 1250, 1250, 50, ((1, 1), (3, .2))) * .5,
        'drop': tone(.18, 320, 140, 22, ((1, 1), (2, .3))) * .8,
    }
    bell = np.zeros(int(1.8 * SR))
    for k, (f, a) in enumerate(((1318.5, 1), (1975.5, .8))):
        b = tone(1.8 - k * .12, f, f, 3.2, ((1, 1), (2.76, .25), (5.4, .08)))
        bell[int(k * .12 * SR):int(k * .12 * SR) + len(b)] += a * b
    fx['chime'] = bell * .45
    for k in fx:
        fx[k] = fx[k] / (np.abs(fx[k]).max() + 1e-9) * .5
    return fx


# ------------------------------------------------------------------ mixing

def music_eq(x):
    """High-pass at 40 Hz and a 2 dB dip around 350 Hz to leave room for the voice."""
    X = np.fft.rfft(x)
    f = np.maximum(np.fft.rfftfreq(len(x), 1 / SR), 1e-3)
    hp = 1 / np.sqrt(1 + (40 / f) ** 4)
    bell = 1 - (1 - 10 ** (-2 / 20)) * np.exp(-np.log2(f / 350) ** 2 / (2 * .6 ** 2))
    return np.fft.irfft(X * hp * bell, len(x))


def load_audio(path):
    raw = subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', str(path), '-f', 'f32le', '-ac', '1', '-ar', str(SR), '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).astype(float)


def loudnorm(src, dst, target=-16.0):
    args = f'loudnorm=I={target}:TP=-1.5:LRA=11'
    r = subprocess.run(['ffmpeg', '-hide_banner', '-i', str(src), '-af', args + ':print_format=json', '-f', 'null', '-'],
                       capture_output=True, text=True, check=True).stderr
    m = json.loads(r[r.rindex('{'):r.rindex('}') + 1])
    second = (f"{args}:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
              f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(src), '-af', second, '-ar', str(SR), str(dst)], check=True)
    return m


def write_wav(path, st):
    pcm = (np.clip(st, -1, 1) * 32767).astype('<i2')
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 's16le', '-ar', str(SR), '-ac', '2', '-i', '-', str(path)],
                   input=pcm.tobytes(), check=True)


def main():
    tl = json.loads((ROOT / 'build/timeline.json').read_text())
    cues = json.loads((ROOT / 'build/sfx.json').read_text())
    dur = tl['duration']
    n = int(dur * SR)

    voice = np.zeros(n)
    for s in tl['scenes']:
        for line in s['lines']:
            clip = fft_highpass(load_audio(ROOT / line['audio']), 70)
            i = int(line['start'] * SR)
            voice[i:i + len(clip)] += clip[: n - i]

    music_path = ROOT / 'build/music.wav'
    meta = ROOT / 'build/music.json'
    if not music_path.exists() or not meta.exists() or json.loads(meta.read_text()).get('duration') != dur:
        print('synthesising music...')
        write_wav(music_path, music(dur))
        meta.write_text(json.dumps({'duration': dur}))
    m = np.frombuffer(subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', str(music_path), '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-'],
                                     capture_output=True, check=True).stdout, dtype=np.float32).reshape(-1, 2).astype(float)[:n]
    m = np.vstack([m, np.zeros((n - len(m), 2))])
    m = np.stack([music_eq(m[:, 0]), music_eq(m[:, 1])], axis=1)

    # duck the music under the voice (smoothed voice-activity envelope)
    hop = int(.02 * SR)
    act = np.repeat((np.sqrt((voice[: n // hop * hop].reshape(-1, hop) ** 2).mean(axis=1)) > .01).astype(float), hop)
    act = np.concatenate([act, np.zeros(n - len(act))])
    k = int(.5 * SR)
    act = np.convolve(act, np.ones(k) / k, mode='same')
    act = np.clip(act * 1.6, 0, 1)
    m *= (1 - .45 * act)[:, None]
    music_rms = np.sqrt((m ** 2).mean())
    m *= 10 ** (-27 / 20) / max(music_rms, 1e-9)

    fx = make_sfx()
    sfx = np.zeros((n, 2))
    for c in cues:
        s = fx[c['name']] * c['gain'] * .55
        if c['name'] == 'type':
            s = s * (.7 + .6 * rand.random())
        i = int(c['t'] * SR)
        if i >= n:
            continue
        s = s[: n - i]
        pan = .15 if c['name'] in ('tap', 'type', 'pop') else 0
        sfx[i:i + len(s), 0] += s * (1 - pan)
        sfx[i:i + len(s), 1] += s * (1 + pan)

    vr = np.sqrt((voice[np.abs(voice) > .01] ** 2).mean())
    voice *= 10 ** (-17 / 20) / vr
    mix = m + sfx * 10 ** (-18 / 20) / .2 + voice[:, None]
    peak = np.abs(mix).max()
    if peak > .98:
        mix *= .98 / peak
    write_wav(ROOT / 'build/mix_raw.wav', mix)
    stats = loudnorm(ROOT / 'build/mix_raw.wav', ROOT / 'build/mix.wav')
    print(f"mix: input {stats['input_i']} LUFS -> -16 LUFS")

    out = ROOT / 'output'
    out.mkdir(exist_ok=True)
    final = out / 'lap-feedback-guide.mp4'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(ROOT / 'build/video.mp4'), '-i', str(ROOT / 'build/mix.wav'),
                    '-i', str(out / 'captions.lo.srt'), '-i', str(out / 'captions.en.srt'),
                    '-map', '0:v', '-map', '1:a', '-map', '2', '-map', '3',
                    '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-c:s', 'mov_text',
                    '-metadata:s:a:0', 'language=lao', '-metadata:s:s:0', 'language=lao', '-metadata:s:s:0', 'title=ລາວ',
                    '-metadata:s:s:1', 'language=eng', '-metadata:s:s:1', 'title=English',
                    '-metadata', 'title=ວິທີແຈ້ງບັນຫາ ແລະ ສົ່ງຄຳຄິດເຫັນ ຜ່ານເວັບໄຊ lap.com.la',
                    '-movflags', '+faststart', str(final)], check=True)
    print(final)


if __name__ == '__main__':
    sys.exit(main())
