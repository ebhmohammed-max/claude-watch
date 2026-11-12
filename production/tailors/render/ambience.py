"""Synthesise the bed for the clothing episode and mix it under the narration.

Nothing here is licensed: every sound is generated, so the mix is reproducible
and rights-free. The rain episode had an obvious bed - rain - so one shaped
noise carried it. This episode does not, so the bed has to be built from two
different kinds of sound:

  * WIND, always present, very low. A high-passed noise layer with slow gusts
    and a pair of decorrelated channels for width.
  * CRAFT, only in the sections about making things. Short filtered noise
    transients: a hide being scraped, a drill turning, a thread being pulled
    through. Sparse - one every few seconds at most - and quiet.

The craft layer is what gives this its character, and it is also the thing most
likely to annoy: a scrape every 2 seconds for nine minutes is a metronome. So
the transients are seeded, jittered, and gated by section, and they sit under
the voice rather than beside it.

Level: the bed is measured against the narration and held 8-12 dB below it,
which is where the rain mix landed after it was retuned.
"""
import json, os, subprocess, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
NAR = os.path.join(ROOT, 'production/tailors/narration')
SR = 44100
def _resolve_ffmpeg():
    """Find ffmpeg without hard-coding a sandbox path.

    These scripts used to point at /tmp/rd, which vanished when the sandbox was
    reset and took the whole rebuild with it. Order: explicit override, then
    PATH, then the imageio-ffmpeg wheel, then the old hard-coded location.
    """
    import shutil as _sh, glob as _gl
    if os.environ.get('FFMPEG'):
        return os.environ['FFMPEG']
    p = _sh.which('ffmpeg')
    if p:
        return p
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass
    for c in _gl.glob('/tmp/*/lib/python*/site-packages/imageio_ffmpeg/binaries/ffmpeg-*'):
        return c
    return 'ffmpeg'


FF = _resolve_ffmpeg()

MAP = json.load(open(os.path.join(HERE, 'map.json')))
DUR = MAP['narration_seconds']
N = int(SR * DUR)
rng = np.random.default_rng(11)

BED_RMS_DB = -25.0   # the rain mix landed near here after retuning - a bed
                     # at -30 measured as -34.5 in practice and disappeared under the voice

# Where the craft textures are allowed, and how busy. Seconds.
CRAFT = [
    (18.0, 64.0, 0.9),      # the cold morning, hide being handled
    (137.0, 216.0, 1.0),    # Contrebandiers: scraping and skinning
    (216.0, 270.0, 0.7),    # awl and needle: drilling and piercing
    (340.0, 418.0, 0.8),    # flax: spinning and twisting
    (454.0, 523.0, 0.6),    # Sunghir: drilling ivory
]
# Where the wind leans in: the cold sections.
GUST = [(0.0, 1.3), (65.0, 0.7), (216.0, 0.5), (270.0, 1.4),
        (418.0, 0.6), (454.0, 1.2), (523.0, 0.4), (DUR, 0.2)]


def noise_grain(seed, seconds=6.0):
    r = np.random.default_rng(seed)
    n = int(seconds * SR)
    x = r.standard_normal(n).astype(np.float32)
    X = np.fft.rfft(x)
    f = np.maximum(np.fft.rfftfreq(n, 1 / SR), 1e-6)
    # wind body: broad, weighted low-mid so it reads under speech without
    # masking it. Sloping off above 3 kHz keeps it out of the voice band.
    spec = (0.70 * np.exp(-((np.log(f / 240.0)) ** 2) / 1.10)
            + 0.35 * np.exp(-((np.log(f / 620.0)) ** 2) / 0.90)
            + 0.18 * np.exp(-((np.log(f / 90.0)) ** 2) / 0.70))
    spec[f > 3200] *= 0.25
    y = np.fft.irfft(X * spec, n).astype(np.float32)
    y /= (np.abs(y).max() + 1e-9)
    return y


def tile(grain, n):
    """Tile a grain to n samples with 1 s crossfades and random offsets."""
    g = len(grain)
    xf = int(1.0 * SR)
    out = np.zeros(n + g, dtype=np.float32)
    pos, k = 0, 0
    while pos < n:
        off = int(rng.integers(0, max(1, g - xf)))
        seg = grain[off:off + g]
        m = len(seg)
        if pos > 0:
            w = np.linspace(0, 1, min(xf, m), dtype=np.float32)
            out[pos:pos + len(w)] *= (1 - w)
            out[pos:pos + len(w)] += seg[:len(w)] * w
            out[pos + len(w):pos + m] += seg[len(w):]
        else:
            out[pos:pos + m] += seg
        pos += m - xf
        k += 1
    return out[:n]


def env(points, n):
    """Piecewise-linear envelope in seconds -> sample values."""
    xs = np.array([p[0] for p in points], dtype=np.float32)
    ys = np.array([p[1] for p in points], dtype=np.float32)
    t = np.arange(n, dtype=np.float32) / SR
    return np.interp(t, xs, ys).astype(np.float32)


def lfo(n, rate, depth, phase=0.0, seed=0):
    t = np.arange(n, dtype=np.float32) / SR
    r = np.random.default_rng(seed)
    out = np.zeros(n, dtype=np.float32)
    for k in range(3):
        f = rate * (1 + 0.37 * k) * r.uniform(0.8, 1.25)
        out += np.sin(2 * np.pi * f * t + phase + r.uniform(0, 6.28)) / (k + 1)
    return (1 + depth * out / 2.2).astype(np.float32)


def transients(n, weight):
    """Craft sounds: filtered noise bursts with a fast attack and short tail."""
    out = np.zeros(n, dtype=np.float32)
    if weight <= 0:
        return out
    for a, b, density in CRAFT:
        t = a + rng.uniform(0, 2.0)
        while t < b:
            i = int(t * SR)
            # each hit is a scrape (noise, 30-60 ms) or a softer handling knock
            dur = rng.uniform(0.04, 0.16)
            m = int(dur * SR)
            if i + m >= n:
                break
            r = np.random.default_rng(int(t * 1000) % 99991)
            x = r.standard_normal(m).astype(np.float32)
            X = np.fft.rfft(x)
            f = np.maximum(np.fft.rfftfreq(m, 1 / SR), 1e-6)
            # bandpass around 700-2600 Hz: a dry, woody scrape
            centre = r.uniform(650, 1500)
            spec = np.exp(-((np.log(f / centre)) ** 2) / 0.55)
            spec[f < 250] *= 0.1
            spec[f > 4200] *= 0.2
            y = np.fft.irfft(X * spec, m).astype(np.float32)
            # envelope: 4 ms attack, exponential decay
            e = np.exp(-np.linspace(0, 5.5, m)).astype(np.float32)
            e[:int(0.004 * SR)] *= np.linspace(0, 1, int(0.004 * SR), dtype=np.float32)
            out[i:i + m] += y * e * rng.uniform(0.5, 1.0)
            t += rng.exponential(1.0 / max(density, 1e-3)) + 0.9
    return out * weight


def build():
    gL = noise_grain(3)
    gR = noise_grain(4)
    wL = tile(gL, N)
    wR = tile(gR, N)
    gust = env(GUST, N) * lfo(N, 0.05, 0.55, seed=5)
    wL *= gust
    wR *= gust

    cr = transients(N, 2.4)   # hits need to sit above the wind or they vanish
    # craft sits slightly right of centre so it does not blur the voice
    bedL = wL * 0.88 + cr * 0.62
    bedR = wR * 0.88 + cr * 0.80

    # normalise the bed to the target RMS, then duck under the narration
    rms = float(np.sqrt(np.mean(np.concatenate([bedL, bedR]) ** 2)) + 1e-12)
    gain = 10 ** (BED_RMS_DB / 20) / rms
    bedL *= gain
    bedR *= gain
    print(f'bed rms {20*np.log10(rms):.1f} dBFS -> {BED_RMS_DB:.1f} dBFS')

    # fades: 4 s in, 6 s out
    for ch in (bedL, bedR):
        fi = int(4 * SR)
        fo = int(6 * SR)
        ch[:fi] *= np.linspace(0, 1, fi, dtype=np.float32)
        ch[-fo:] *= np.linspace(1, 0, fo, dtype=np.float32)

    st = np.stack([bedL, bedR], axis=1)
    pcm = (np.clip(st, -1, 1) * 32767).astype('<i2')
    out = os.path.join(NAR, 'bed.wav')
    with wave.open(out, 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print('wrote', out)
    return out


def read_wav(path):
    with wave.open(path, 'rb') as w:
        n, ch = w.getnframes(), w.getnchannels()
        x = np.frombuffer(w.readframes(n), dtype='<i2').astype(np.float32) / 32768.0
    return x.reshape(-1, ch) if ch > 1 else x.reshape(-1, 1)


def mix(bed_path):
    """Mix in numpy rather than trusting a filter graph.

    An amix with normalize=0 still came back 6 dB down on this build, which
    quietly halved the narration. Doing the sum here means the voice leaves at
    exactly the level it was recorded at, and the ducking curve is inspectable.

    Ducking: the bed drops while the voice is present so the craft textures sit
    in the gaps, where they are audible without fighting a sentence.
    """
    vo = read_wav(os.path.join(NAR, 'master.wav'))[:, 0]
    bed = read_wav(bed_path)
    n = min(len(vo), len(bed))
    vo, bed = vo[:n], bed[:n]

    # activity envelope: rectify, then 40 ms attack / 300 ms release smoothing
    a = np.abs(vo)
    atk = int(0.040 * SR)
    rel = int(0.300 * SR)
    envl = np.zeros(n, dtype=np.float32)
    cur = 0.0
    k_atk = 1 - np.exp(-1 / atk)
    k_rel = 1 - np.exp(-1 / rel)
    for i in range(n):
        k = k_atk if a[i] > cur else k_rel
        cur += k * (a[i] - cur)
        envl[i] = cur
    act = np.clip(envl / 0.06, 0, 1).astype(np.float32)     # 1 = speech present

    # 0 dB in silence, -13 dB under speech
    gain_db = -10.0 * act
    bed_gain = (10 ** (gain_db / 20)).astype(np.float32)[:, None]
    mixed = vo[:, None] + bed * bed_gain

    peak = float(np.abs(mixed).max()) + 1e-9
    target = 10 ** (-1.5 / 20)
    if peak > target:
        mixed *= target / peak
        print(f'peak trimmed {20*np.log10(peak):.2f} -> -1.50 dBFS')
    out = os.path.join(NAR, 'mix.wav')
    pcm = (np.clip(mixed, -1, 1) * 32767).astype('<i2')
    with wave.open(out, 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print(f'wrote {out}  ({n / SR:.2f} s)')
    print(f'voice rms {20*np.log10(np.sqrt((vo**2).mean())):.1f} dBFS · '
          f'mix rms {20*np.log10(np.sqrt((mixed**2).mean())):.1f} dBFS')


if __name__ == '__main__':
    mix(build())
