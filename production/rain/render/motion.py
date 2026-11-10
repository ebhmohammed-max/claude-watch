"""Give each placement a slow camera move, then lay the type back on top.

Each slot becomes a short clip: the still is pushed/pulled/panned by a few
percent over the slot's duration, then the pre-rendered RGBA overlay is
composited on top so the captions never wobble.

Assets are 840x472, so the move is deliberately small (<=7%). Bigger moves
would outrun the source resolution and look mushy.
"""
import json, os, subprocess, sys, hashlib
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
W, H, FPS = 1280, 720, 25
SUP = 1400          # supersampled source width; >= W * max zoom
ZOOM = 0.07

FF = None


def ff():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def prep(src, dst):
    """Upscale the still once, with a touch of sharpening to survive the move."""
    im = Image.open(src).convert('RGB')
    im = im.resize((SUP, round(SUP * im.height / im.width)), Image.LANCZOS)
    im = im.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=3))
    im.save(dst, quality=95)


def move(shot, n):
    """Pick a deterministic camera move so the cut doesn't feel mechanical."""
    kind = hashlib.md5(str(shot).encode()).hexdigest()
    k = int(kind[:2], 16) % 5
    c = 'iw/2-(iw/zoom/2)'
    cy = 'ih/2-(ih/zoom/2)'
    if k == 0:      # push in
        return f"z='1.0+{ZOOM}*on/{n}':x='{c}':y='{cy}'"
    if k == 1:      # pull out
        return f"z='1.0+{ZOOM}-{ZOOM}*on/{n}':x='{c}':y='{cy}'"
    if k == 2:      # drift left -> right
        return f"z='1.0+{ZOOM}':x='(iw-iw/zoom)*on/{n}':y='{cy}'"
    if k == 3:      # drift right -> left
        return f"z='1.0+{ZOOM}':x='(iw-iw/zoom)*(1-on/{n})':y='{cy}'"
    return f"z='1.0+{ZOOM}':x='{c}':y='(ih-ih/zoom)*on/{n}'"  # drift down


def build(item):
    f, ov, n = item['src'], item['ov'], item['frames']
    out = item['out']
    if os.path.exists(out) and os.path.getsize(out) > 2000:
        return out
    if item['quiz']:
        # opaque card: a single still is both correct and cheap
        vf = f"[0:v]scale={W}:{H},setsar=1[bg];[1:v]format=rgba[ov];[bg][ov]overlay=0:0,format=yuv420p[v]"
        cmd = [ff(), '-y', '-loglevel', 'error', '-loop', '1', '-i', f,
               '-loop', '1', '-i', ov, '-filter_complex', vf, '-map', '[v]',
               '-r', str(FPS), '-frames:v', str(n), '-c:v', 'libx264',
               '-preset', 'veryfast', '-crf', '19', out]
        subprocess.run(cmd, check=True)
        return out
    m = move(item['shot'], n)
    vf = (f"[0:v]zoompan=d={n}:s={W}x{H}:fps={FPS}:{m},setsar=1[bg];"
          f"[1:v]format=rgba[ov];[bg][ov]overlay=0:0:format=auto,format=yuv420p[v]")
    cmd = [ff(), '-y', '-loglevel', 'error', '-i', f, '-i', ov,
           '-filter_complex', vf, '-map', '[v]', '-r', str(FPS),
           '-frames:v', str(n), '-c:v', 'libx264', '-preset', 'veryfast',
           '-crf', '19', out]
    subprocess.run(cmd, check=True)
    return out


def main():
    plan = json.load(open(os.path.join(HERE, 'plan.json')))
    work = os.path.join(HERE, 'work')
    clips = os.path.join(HERE, 'clips')
    for p in (work, clips):
        os.makedirs(p, exist_ok=True)

    total = 0
    for p in plan:
        # frame counts come from cumulative rounding so the cut stays frame-exact
        p['frames'] = round(p['end'] * FPS) - round(p['start'] * FPS)
        total += p['frames']
    print(f"{len(plan)} clips, {total} frames, {total / FPS:.3f} s")

    for p in plan:
        p['src'] = os.path.join(work, p['stem'] + '.jpg')
        p['ov'] = os.path.join(HERE, 'overlays', p['stem'] + '.png')
        p['out'] = os.path.join(clips, p['stem'] + '.mp4')
        if not os.path.exists(p['src']):
            prep(os.path.join(ROOT, p['file']), p['src'])

    todo = [p for p in plan if not (os.path.exists(p['out']) and os.path.getsize(p['out']) > 2000)]
    print(f"{len(todo)} to encode")
    with ThreadPoolExecutor(max_workers=2) as ex:
        for k, _ in enumerate(ex.map(build, todo), 1):
            if k % 25 == 0 or k == len(todo):
                print(f"  {k}/{len(todo)}", flush=True)

    lst = os.path.join(HERE, 'clips.txt')
    with open(lst, 'w') as fh:
        for p in plan:
            fh.write(f"file '{p['out']}'\n")
    print(lst)


if __name__ == '__main__':
    main()
