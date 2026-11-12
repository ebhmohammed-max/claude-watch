"""Build the bed for the sleep episode and mix it under the narration.

Nothing here is licensed: every sound is generated, so the mix is reproducible
and rights-free. The shot map asks for three environments, and they are not the
same bed:

  * INTERIOR (00:00-01:10 and 11:01-end) "soft interior room tone; restrained
    floor creak when motivated". A room is not outdoors. Low, close, no wind.
  * ANCIENT (01:10-07:20) "low wind, distant non-specific insects, subdued fire
    where visible". Wind plus insects at the edge of hearing, fire underneath.
  * STUDY (07:20-10:50) a modern paper being described on screen. The bed pulls
    back to almost nothing so the numbers are not fighting a soundscape.

The previous three cuts of this episode shipped with narration only, because the
report kept saying "no music, ambience or effects". A defence of that as a style
choice would be dishonest: what it actually was, is unfinished.

Level is measured against the narration and held under it, then ducked further
while the voice is present. The rain mix landed at a bed RMS of -25 dBFS and was
still too loud at -30 measured - so this one is set by measurement, not by hope.
"""
import json, os, subprocess, sys, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
EP = os.path.dirname(HERE)
NAR = os.path.join(EP, 'narration')
SR = 44100


def _resolve_ffmpeg():
    """Find ffmpeg without hard-coding a sandbox path.

    These scripts used to point at /tmp/rd, which vanished when the sandbox was
    reset and took the whole rebuild with it. Order: explicit override, then
    PATH, then the imageio-ffmpeg wheel.
    """
    import shutil, glob
    if os.environ.get('FFMPEG'):
        return os.environ['FFMPEG']
    p = shutil.which('ffmpeg')
    if p:
        return p
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass
    for c in glob.glob('/tmp/*/lib/python*/site-packages/imageio_ffmpeg/binaries/ffmpeg-*'):
        return c
    return 'ffmpeg'


FF = _resolve_ffmpeg()

# Section boundaries in the finished picture, not in the shot map.
# Measured: the modern room opens and closes the film, the study runs 07:20.8
# to 08:07.7, and the shelter returns at 08:07.7.
DUR = 682.36
# Gains as continuous curves, not as a max of windows. The first build used
# np.maximum over hard-edged windows and left 487.7-661.0 with no bed at all --
# nearly three minutes of dead air under the dawn -- and then a 1.8 s hole at
# 660 s where two windows both faded to zero at the same instant. Curves that
# cross-fade cannot do that.
INTERIOR_GAIN = [(0.0, 1.0), (60.0, 1.0), (76.0, 0.0),
                 (654.0, 0.0), (668.0, 1.0), (DUR, 1.0)]
ANCIENT_GAIN = [(0.0, 0.0), (64.0, 0.0), (78.0, 1.0),
                (430.0, 1.0), (440.0, 0.18), (487.7, 0.18),
                (495.0, 0.95), (650.0, 1.0), (670.0, 0.0), (DUR, 0.0)]
# The study is a modern paper on a screen, so the outdoor world drops away and
# a quiet room comes up under it -- not silence, which reads as a broken file.
STUDY_GAIN = [(0.0, 0.0), (432.0, 0.0), (440.0, 1.0),
              (487.7, 1.0), (496.0, 0.0), (DUR, 0.0)]

# Wind gusts: where it leans in. The ancient night is the body of the film.
GUST = [(0.0, 0.0), (62.0, 0.0), (74.0, 0.9), (190.0, 0.6), (274.0, 0.7),
        (330.0, 1.1), (400.0, 1.0), (436.0, 0.25), (490.0, 0.45),
        (560.0, 0.9), (628.0, 1.0), (662.0, 0.15), (DUR, 0.0)]

BED_RMS_DB = -27.0   # target for the whole bed before ducking
DUCK_DB = -11.0      # how far the bed drops under speech

# Layer levels, relative to the wind, which is the reference at 0 dB. Room tone
# has more low-frequency energy per sample than filtered wind, so a 1:1 mix put
# the study room 14 dB above the outdoor bed -- louder than the narration it was
# supposed to sit under. These are set from measurement, not by eye.
WIND_DB = 0.0
ROOM_DB = -8.0       # interior room tone under the wind
STUDY_DB = -11.0     # the study's room: present, but the quietest place in the film
INSECT_DB = -22.0    # at the edge of hearing, deliberately unidentifiable
FIRE_DB = -20.0      # subdued, and only where the shot map asks for it

rng = np.random.default_rng(20261107)


def band_noise(n, shape, seed):
    """Noise shaped by a frequency response given as f -> gain."""
    r = np.random.default_rng(seed)
    x = r.standard_normal(n).astype(np.float32)
    X = np.fft.rfft(x)
    f = np.maximum(np.fft.rfftfreq(n, 1 / SR), 1e-6)
    y = np.fft.irfft(X * shape(f), n).astype(np.float32)
    return y / (np.abs(y).max() + 1e-9)


def wind_grain(seed):
    def shape(f):
        s = (0.70 * np.exp(-((np.log(f / 240.0)) ** 2) / 1.10)
             + 0.35 * np.exp(-((np.log(f / 620.0)) ** 2) / 0.90)
             + 0.18 * np.exp(-((np.log(f / 90.0)) ** 2) / 0.70))
        s[f > 3200] *= 0.25
        return s
    return band_noise(int(6.0 * SR), shape, seed)


def room_grain(seed):
    """A room: low rumble plus a little air, no gust structure at all."""
    def shape(f):
        s = (0.9 * np.exp(-((np.log(f / 110.0)) ** 2) / 0.60)
             + 0.22 * np.exp(-((np.log(f / 400.0)) ** 2) / 1.4))
        s[f > 1200] *= 0.12
        return s
    return band_noise(int(6.0 * SR), shape, seed)


def tile(grain, n, seed):
    """Tile a grain to n samples with 1 s crossfades at random offsets."""
    r = np.random.default_rng(seed)
    g = len(grain)
    xf = int(1.0 * SR)
    out = np.zeros(n + g, dtype=np.float32)
    pos = 0
    while pos < n:
        off = int(r.integers(0, max(1, g - xf)))
        seg = grain[off:off + g]
        m = len(seg)
        if pos > 0:
            w = np.linspace(0, 1, min(xf, m), dtype=np.float32)
            out[pos:pos + len(w)] *= (1 - w)
            out[pos:pos + len(w)] += seg[:len(w)] * w
            outro = pos + len(w)
            out[outro:outro + (m - len(w))] += seg[len(w):]
        else:
            out[pos:pos + m] += seg
        pos += m - xf
    return out[:n]


def env(points, n):
    xs = np.array([p[0] for p in points], dtype=np.float32)
    ys = np.array([p[1] for p in points], dtype=np.float32)
    t = np.arange(n, dtype=np.float32) / SR
    return np.interp(t, xs, ys).astype(np.float32)


def lfo(n, rate, depth, seed):
    t = np.arange(n, dtype=np.float32) / SR
    r = np.random.default_rng(seed)
    out = np.zeros(n, dtype=np.float32)
    for k in range(3):
        f = rate * (1 + 0.37 * k) * r.uniform(0.8, 1.25)
        out += np.sin(2 * np.pi * f * t + r.uniform(0, 6.28)) / (k + 1)
    return (1 + depth * out / 2.2).astype(np.float32)


def insects(n, density, seed):
    """Distant, non-specific chirps. Not crickets: we do not know what sang.

    Short high-pitched chirp trains, placed sparsely and panned wide, low enough
    to sit under the voice. The shot map asks for 'distant non-specific
    insects' precisely so the sound cannot claim a species the record lacks.
    """
    r = np.random.default_rng(seed)
    out = np.zeros((n, 2), dtype=np.float32)
    t = 0.6
    while t < DUR:
        dur = r.uniform(0.02, 0.06)
        m = int(dur * SR)
        i = int(t * SR)
        if i + m >= n:
            break
        k = np.arange(m) / SR
        f0 = r.uniform(3800, 5200)
        # a chirp with a slight downward bend, as insects do
        ph = 2 * np.pi * (f0 * k - r.uniform(200, 700) * k ** 2 / (2 * dur))
        sig = np.sin(ph) * np.exp(-k / (dur * 0.55)) * r.uniform(0.4, 1.0)
        # a train of 2-4 chirps
        for j in range(int(r.integers(2, 5))):
            o = i + int(j * r.uniform(0.05, 0.11) * SR)
            if o + m < n:
                pan = r.uniform(0.15, 0.85)
                out[o:o + m, 0] += sig * (1 - pan)
                out[o:o + m, 1] += sig * pan
        t += r.exponential(1.0 / max(density, 1e-6)) + 0.35
    return out


def fire(n, seed):
    """Subdued fire: a low roar plus irregular ticks, never a crackle loop."""
    r = np.random.default_rng(seed)

    def shape(f):
        s = (0.8 * np.exp(-((np.log(f / 300.0)) ** 2) / 1.0)
             + 0.3 * np.exp(-((np.log(f / 900.0)) ** 2) / 1.2))
        s[f > 5000] *= 0.2
        return s

    roar = band_noise(n, shape, seed + 1)
    roar *= lfo(n, 0.35, 0.5, seed + 2)
    # ticks: tiny high transients, jittered, thinning out
    ticks = np.zeros(n, dtype=np.float32)
    t = 0.4
    while t < DUR:
        m = int(r.uniform(0.004, 0.02) * SR)
        i = int(t * SR)
        if i + m >= n:
            break
        x = r.standard_normal(m).astype(np.float32)
        X = np.fft.rfft(x)
        f = np.maximum(np.fft.rfftfreq(m, 1 / SR), 1e-6)
        y = np.fft.irfft(X * np.exp(-((np.log(f / r.uniform(1800, 3600))) ** 2) / 0.5), m)
        y /= (np.abs(y).max() + 1e-9)
        ticks[i:i + m] += y * np.exp(-np.linspace(0, 6, m)).astype(np.float32) * r.uniform(0.3, 1.0)
        t += r.exponential(1 / 7.0) + 0.05
    return roar * 0.9 + ticks * 0.5


def build():
    n = int(SR * DUR)
    print(f'building bed: {DUR:.2f} s at {SR} Hz')

    # --- interior: a room, close and dry -------------------------------
    riL = tile(room_grain(1), n, 2) * 1.0
    riR = tile(room_grain(3), n, 4) * 1.0
    # restrained floor creaks: sparse, low, only where the map says 'when motivated'
    creaks = np.zeros(n, dtype=np.float32)
    r = np.random.default_rng(77)
    # creaks only where the room is actually up
    for a, b in ((0.0, 66.0), (663.0, DUR)):
        t = a + 1.5
        while t < b - 1.0:
            m = int(r.uniform(0.25, 0.6) * SR)
            i = int(t * SR)
            if i + m >= n:
                break
            k = np.arange(m) / SR
            f = r.uniform(150, 320)
            sig = np.sin(2 * np.pi * f * k * (1 + 0.15 * k / (m / SR)))
            e = np.sin(np.pi * np.clip(k / (m / SR), 0, 1)) ** 1.5
            creaks[i:i + m] += (sig * e).astype(np.float32) * r.uniform(0.25, 0.5)
            t += r.exponential(1 / 0.09) + 2.0
    room = np.stack([riL + creaks * 0.8, riR + creaks * 0.8], axis=1)
    interior = room * 10 ** (ROOM_DB / 20)
    interior *= env(INTERIOR_GAIN, n)[:, None]

    # --- ancient: wind, insects, fire ----------------------------------
    wL = tile(wind_grain(11), n, 12)
    wR = tile(wind_grain(13), n, 14)
    gust = env(GUST, n) * lfo(n, 0.05, 0.55, 15)
    insect = insects(n, 0.55, 16)
    fr = fire(n, 17)
    ancient = np.stack([wL * gust, wR * gust], axis=1) * 10 ** (WIND_DB / 20)
    ancient += insect * 10 ** (INSECT_DB / 20)
    ancient += fr[:, None] * 10 ** (FIRE_DB / 20)
    ancient *= env(ANCIENT_GAIN, n)[:, None]

    # --- study: a modern room, quiet, so the figures are audible -------
    stL = tile(room_grain(21), n, 22)
    stR = tile(room_grain(23), n, 24)
    study = np.stack([stL, stR], axis=1) * 10 ** (STUDY_DB / 20)
    study *= env(STUDY_GAIN, n)[:, None]

    bed = interior + ancient + study

    # Refuse to ship a silent stretch. The bed must be present at every point
    # of the film, and the first two builds both failed this.
    hop = int(0.25 * SR)
    levels = np.sqrt((bed[:len(bed) // hop * hop]
                      .reshape(-1, hop, 2) ** 2).mean(axis=(1, 2)))
    dead = np.where(levels < 10 ** (-55 / 20))[0]
    if len(dead):
        print(f'DEAD BED at {dead[0] * 0.25:.1f}-{dead[-1] * 0.25:.1f} s '
              f'({len(dead) * 0.25:.1f} s of silence)')
        raise SystemExit('bed has silent gaps; fix the gain curves')
    rms = float(np.sqrt(np.mean(bed ** 2)) + 1e-12)
    bed *= 10 ** (BED_RMS_DB / 20) / rms
    print(f'bed rms {20*np.log10(rms):.1f} -> {BED_RMS_DB:.1f} dBFS')

    # fades: 3 s in, 5 s out
    fi, fo = int(3 * SR), int(5 * SR)
    bed[:fi] *= np.linspace(0, 1, fi, dtype=np.float32)[:, None]
    bed[-fo:] *= np.linspace(1, 0, fo, dtype=np.float32)[:, None]

    out = os.path.join(NAR, 'bed.wav')
    pcm = (np.clip(bed, -1, 1) * 32767).astype('<i2')
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

    An amix with normalize=0 still came back 6 dB down on the clothing build,
    which quietly halved the narration. Doing the sum here means the voice
    leaves at exactly the level it was recorded at, and the ducking curve is
    inspectable.
    """
    vo = read_wav(os.path.join(NAR, 'master.wav'))[:, 0]
    bed = read_wav(bed_path)
    n = min(len(vo), len(bed))
    vo, bed = vo[:n], bed[:n]
    # The picture runs 2 s past the last word so the final frame can fade to
    # black. Pad the voice with silence to the full runtime and let the bed
    # carry that tail -- dead air would read as a broken encode.
    need = int(round(DUR * SR))
    if n < need:
        vo = np.concatenate([vo, np.zeros(need - n, dtype=np.float32)])
        bed = np.concatenate(
            [bed, np.zeros((need - n, bed.shape[1]), dtype=np.float32)])[:need]
        n = need

    # activity envelope: rectify, then 40 ms attack / 300 ms release smoothing
    a = np.abs(vo)
    atk, rel = int(0.040 * SR), int(0.300 * SR)
    envl = np.zeros(n, dtype=np.float32)
    cur = 0.0
    k_atk = 1 - np.exp(-1 / atk)
    k_rel = 1 - np.exp(-1 / rel)
    for i in range(n):
        k = k_atk if a[i] > cur else k_rel
        cur += k * (a[i] - cur)
        envl[i] = cur
    act = np.clip(envl / 0.06, 0, 1).astype(np.float32)

    bed_gain = (10 ** ((DUCK_DB * act) / 20)).astype(np.float32)[:, None]
    mixed = vo[:, None] * 0.98 + bed * bed_gain

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
    return out


if __name__ == '__main__':
    mix(build())
