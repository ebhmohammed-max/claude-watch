"""Synthesise the rain bed and mix it under the narration.

No licensed music here: the ambience is procedural, so it is reproducible and
free of rights problems. Structure:

  * broadband noise shaped into a rain spectrum (sub rumble, body, hiss)
  * slow gusts (a few low-frequency LFOs) so it breathes instead of sitting flat
  * an intensity curve driven by the section boundaries of the shot map, so the
    weather tracks the script: heavy at the open, easing through the camp, back
    up for the fire, gone by "when the rain ends"
  * sparse drip transients once the rain has stopped
  * decorrelated left/right so it has width on headphones
  * narration stays dual-mono and centred on top

Level: the bed sits about 15 dB under the narration, which is immersive without
fighting the voice.
"""
import json, os, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SR = 44100
DUR = 554.652
N = int(SR * DUR)
rng = np.random.default_rng(7)

# Bed level relative to full scale, and the section intensity curve.
BED_RMS_DB = -29.0
# seconds -> relative level in dB. Matches the eight sections of the map.
CURVE = [
    (0.0, 2.0), (20.0, 1.0), (61.0, 2.5), (110.0, 1.5), (124.0, 0.0),
    (150.0, -1.0), (192.0, -2.0), (240.0, -1.0), (272.0, 1.0),
    (300.0, 2.0), (348.0, 0.5), (380.0, -0.5), (411.0, -0.5),
    (440.0, -1.5), (470.0, -3.0), (486.0, -6.0), (500.0, -12.0),
    (515.0, -18.0), (530.0, -22.0), (545.0, -26.0), (554.652, -30.0),
]


GRAIN_S = 8.0           # tile length for the shaped noise grain


def shaped_noise(seed, n):
    """Build one 8 s grain of shaped noise, then tile it with crossfades.

    A single FFT over the full 9 minutes needs ~1 GB of complex buffers and this
    box has 3 GB, so we synthesise a short grain and tile instead. Random
    offsets per tile stop it sounding looped.
    """
    r = np.random.default_rng(seed)
    g = int(GRAIN_S * SR)
    x = r.standard_normal(g).astype(np.float32)
    X = np.fft.rfft(x)
    f = np.maximum(np.fft.rfftfreq(g, 1 / SR), 1e-6)
    # Rain reads as *body* plus a soft hiss. An earlier version put most of its
    # energy at 1.5-5 kHz, which sounded like static and sat right on top of the
    # narration's intelligibility band. Weight it lower now.
    spec = (0.55 * np.exp(-((np.log(f / 420.0)) ** 2) / 0.85)
            + 0.42 * np.exp(-((np.log(f / 1100.0)) ** 2) / 0.75)
            + 0.30 * np.exp(-((np.log(f / 180.0)) ** 2) / 0.80)
            + 0.16 * np.exp(-((np.log(f / 3600.0)) ** 2) / 0.60)
            + 0.05)
    spec[f < 70] *= f[f < 70] / 70.0
    spec[f > 9000] *= np.exp(-(f[f > 9000] - 9000) / 4000.0)
    grain = np.fft.irfft(X * spec, g).astype(np.float32)
    grain /= np.abs(grain).max() + 1e-12

    out = np.zeros(n, dtype=np.float32)
    fade = int(0.4 * SR)
    win = np.hanning(2 * fade).astype(np.float32)
    rr = np.random.default_rng(seed + 1000)
    step = g - 2 * fade
    for at in range(0, n, step):
        seg = np.roll(grain, int(rr.integers(0, g)))
        seg = np.concatenate([seg, seg[:2 * fade]])
        seg = seg[:min(len(seg), n - at)]
        if len(seg) < len(win):
            out[at:at + len(seg)] += seg
            continue
        ramp = np.concatenate([win[:fade], np.ones(len(seg) - 2 * fade, dtype=np.float32), win[fade:]])
        out[at:at + len(seg)] += seg * ramp
    return out


def gusts(n):
    """Slow amplitude movement so the rain swells and eases."""
    t = np.arange(n) / SR
    g = np.zeros(n, dtype=np.float32)
    for rate, phase, amp in [(0.037, 0.0, 0.45), (0.081, 1.7, 0.30), (0.157, 3.1, 0.18)]:
        g += amp * np.sin(2 * np.pi * rate * t + phase)
    return np.exp(g * 0.16)          # ~ +/-1.5 dB


def curve_env(n):
    ts = np.array([c[0] for c in CURVE])
    vs = np.array([c[1] for c in CURVE])
    t = np.arange(n) / SR
    db = np.interp(t, ts, vs)
    # smooth the steps so section changes are not audible clicks
    # two passes of a box blur: cheap, and smooth enough to hide section steps
    k = int(SR * 2.0)
    for _ in range(2):
        db = np.pad(db, (k // 2, k // 2), mode='edge')
        c = np.cumsum(db)
        db = (c[k:] - c[:-k]) / k
        db = db[:n]
    return (10 ** (db / 20.0)).astype(np.float32)


def drips(n, start_s, count=90):
    """Sparse post-rain drips, each a short damped ping."""
    out = np.zeros(n)
    i0 = int(start_s * SR)
    for _ in range(count):
        at = i0 + int(rng.random() ** 1.6 * (n - i0 - SR * 0.1))
        if at >= n - 200:
            continue
        ln = int(SR * rng.uniform(0.03, 0.09))
        tt = np.arange(ln) / SR
        f0 = rng.uniform(900, 2600)
        env = np.exp(-tt * rng.uniform(60, 140))
        ping = np.sin(2 * np.pi * f0 * tt * (1 - 0.25 * tt / (tt[-1] + 1e-9))) * env
        amp = 10 ** (rng.uniform(-30, -18) / 20.0)
        out[at:at + ln] += ping * amp
    return out


def rms_db(x):
    return 20 * np.log10(np.sqrt((x ** 2).mean()) + 1e-12)


def main():
    src = os.path.join(ROOT, 'google_drive',
                       'Atlas Understory — Rain episode narration DRAFT.mp3')
    import subprocess, imageio_ffmpeg
    FF = imageio_ffmpeg.get_ffmpeg_exe()
    tmp_nar = '/tmp/_nar_amb.wav'
    subprocess.run([FF, '-y', '-loglevel', 'error', '-i', src,
                    '-ac', '1', '-ar', str(SR), tmp_nar], check=True)
    w = wave.open(tmp_nar)
    nar = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64) / 32768.0
    if len(nar) < N:
        nar = np.pad(nar, (0, N - len(nar)))
    nar = nar[:N]

    env = curve_env(N)
    left = shaped_noise(11, N) * gusts(N)
    right = shaped_noise(29, N) * np.roll(gusts(N), 3000)

    bed = np.stack([left, right], axis=1)
    # normalise the bed before the curve so BED_RMS_DB means the quiet passages
    bed_lvl = 10 ** (BED_RMS_DB / 20.0)
    bed = bed / (np.sqrt((bed.astype(np.float64) ** 2).mean()) + 1e-12) * bed_lvl
    bed *= env[:, None]

    d = drips(N, 486.0)
    bed += np.stack([d, np.roll(d, 900)], axis=1)

    # 2 s fade in, 3 s fade out
    fi = int(SR * 2.0); fo = int(SR * 3.0)
    bed[:fi] *= np.linspace(0, 1, fi)[:, None]
    bed[-fo:] *= np.linspace(1, 0, fo)[:, None]

    out = bed + nar[:, None]
    peak = np.abs(out).max()
    if peak > 10 ** (-1.0 / 20.0):
        out *= 10 ** (-1.0 / 20.0) / peak
    print(f"bed rms {rms_db(bed):.1f} dBFS · mixed rms {rms_db(out):.1f} dBFS "
          f"· peak {20 * np.log10(np.abs(out).max()):.1f} dBFS")

    dst = '/tmp/ambience_mix.wav'
    with wave.open(dst, 'w') as o:
        o.setnchannels(2); o.setsampwidth(2); o.setframerate(SR)
        o.writeframes((np.clip(out, -1, 1) * 32767).astype(np.int16).tobytes())
    print(dst)


if __name__ == '__main__':
    main()
