"""Give each slot a slow camera move, then lay the type back on top.

Each slot becomes a short clip: the still is pushed, pulled or panned by a few
percent over the slot's duration, then the pre-rendered RGBA layer is
composited on top so the captions never wobble.

Source stills arrive at different sizes from this generator, so every still is
normalised once to a supersampled 1440-wide copy with a light unsharp mask,
then zoompan crops inside it. Zoom is small because the source is only ~2 MP;
a big move would outrun the detail.
"""
import json, os, subprocess, hashlib
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
W, H, FPS = 1280, 720, 25
SUP = 1440
ZOOM = 0.06

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


def prep(src, dst):
    im = Image.open(src).convert('RGB')
    # cover-crop to 16:9 before upscaling, so zoompan never letterboxes
    tr = W / H
    if im.width / im.height > tr:
        nw = round(im.height * tr)
        im = im.crop(((im.width - nw) // 2, 0, (im.width + nw) // 2, im.height))
    else:
        nh = round(im.width / tr)
        im = im.crop((0, (im.height - nh) // 2, im.width, (im.height + nh) // 2))
    im = im.resize((SUP, round(SUP / tr)), Image.LANCZOS)
    im = im.filter(ImageFilter.UnsharpMask(radius=2, percent=55, threshold=3))
    im.save(dst, quality=95)


def move(seed, n):
    k = int(hashlib.md5(str(seed).encode()).hexdigest()[:2], 16) % 5
    c, cy = 'iw/2-(iw/zoom/2)', 'ih/2-(ih/zoom/2)'
    if k == 0:
        return f"z='1.0+{ZOOM}*on/{n}':x='{c}':y='{cy}'"
    if k == 1:
        return f"z='1.0+{ZOOM}-{ZOOM}*on/{n}':x='{c}':y='{cy}'"
    if k == 2:
        return f"z='1.0+{ZOOM}':x='(iw-iw/zoom)*on/{n}':y='{cy}'"
    if k == 3:
        return f"z='1.0+{ZOOM}':x='(iw-iw/zoom)*(1-on/{n})':y='{cy}'"
    return f"z='1.0+{ZOOM}':x='{c}':y='(ih-ih/zoom)*on/{n}'"


def clip_seconds(path):
    out = subprocess.run([FF, '-hide_banner', '-i', path],
                         capture_output=True, text=True).stderr
    for line in out.splitlines():
        if 'Duration:' in line:
            h, m, s = line.split('Duration:')[1].split(',')[0].strip().split(':')
            return int(h) * 3600 + int(m) * 60 + float(s)
    return -1


def build(it):
    out = it['out']
    # A clip is only reusable if it is the right LENGTH. Checking existence alone
    # silently reused footage from an earlier plan: the stems still matched, so a
    # rebuild reported "0 to encode" and shipped a cut 18 s too long.
    if os.path.exists(out) and os.path.getsize(out) > 2000:
        want = it['frames'] / FPS
        got = clip_seconds(out)
        if abs(got - want) <= 0.021:
            return out
        os.remove(out)
    n = it['frames']
    m = move(it['still'], n)
    vf = (f"[0:v]zoompan=d={n}:s={W}x{H}:fps={FPS}:{m},setsar=1[bg];"
          f"[1:v]format=rgba[ov];[bg][ov]overlay=0:0:format=auto,format=yuv420p[v]")
    subprocess.run([FF, '-y', '-loglevel', 'error', '-i', it['src'], '-i', it['ov'],
                    '-filter_complex', vf, '-map', '[v]', '-r', str(FPS),
                    '-frames:v', str(n), '-c:v', 'libx264', '-preset', 'veryfast',
                    '-crf', '19', out], check=True)
    return out


def main():
    plan = json.load(open(os.path.join(HERE, 'plan.json')))
    work, clips = os.path.join(HERE, 'work'), os.path.join(HERE, 'clips')
    for p in (work, clips):
        os.makedirs(p, exist_ok=True)
    # Stale clips from an earlier map are poison: the concat list picks up every
    # file on disk, so a run with a changed plan silently doubles the runtime.
    # A clip is stale if its stem is not in this plan.
    stems = {p['stem'] for p in plan}
    for d in (work, clips):
        for f in os.listdir(d):
            if f.split('.')[0] not in stems:
                os.remove(os.path.join(d, f))
    total = 0
    for p in plan:
        p['frames'] = round(p['end'] * FPS) - round(p['start'] * FPS)
        total += p['frames']
        p['src'] = os.path.join(work, p['stem'] + '.jpg')
        p['ov'] = os.path.join(HERE, 'overlays', p['stem'] + '.png')
        p['out'] = os.path.join(clips, p['stem'] + '.mp4')
        if not os.path.exists(p['src']):
            prep(os.path.join(ROOT, f"production/tailors/stills/t{int(p['still']):03d}.jpg"),
                 p['src'])
    print(f"{len(plan)} clips · {total} frames · {total / FPS:.2f} s")
    # The reuse test has to live here, not only inside build(): todo decides what
    # build() ever sees, so an existence-only test here meant a changed plan
    # reported "0 to encode" and shipped the previous cut.
    def fresh(p):
        out = p['out']
        if not (os.path.exists(out) and os.path.getsize(out) > 2000):
            return False
        return abs(clip_seconds(out) - p['frames'] / FPS) <= 0.021

    todo = [p for p in plan if not fresh(p)]
    print(f'{len(todo)} to encode')
    with ThreadPoolExecutor(max_workers=2) as ex:
        for k, _ in enumerate(ex.map(build, todo), 1):
            if k % 25 == 0 or k == len(todo):
                print(f'  {k}/{len(todo)}', flush=True)
    lst = os.path.join(HERE, 'clips.txt')
    with open(lst, 'w') as fh:
        for p in plan:
            fh.write(f"file '{p['out']}'\n")
    print(lst)


if __name__ == '__main__':
    main()
