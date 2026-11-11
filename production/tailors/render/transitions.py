"""Dissolve at section changes, and only at section changes.

Ported from the rain episode, which needed it first. The hard rule for this
series is that a cut stays hard *inside* a section and only a section change
gets a dissolve; without this script every boundary was a hard cut, which broke
that rule in the one place it is most visible.

The graph approach (concat bodies + chained xfade) truncated silently at ~80 s
in this ffmpeg build, so this does it the boring way:

  for each section boundary, blend the outgoing and incoming *stills* across
  D seconds, give the incoming clip up to the blend in frames, and splice the
  blend in between. Net duration is unchanged.

Blending the encoded clips cross-faded their burned-in captions too, so two
sentences sat on top of each other. This blends the images and swaps the type
at the halfway frame instead.
"""
import json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import motion as M
from PIL import Image

HERE = M.HERE
ROOT = M.ROOT
FPS = 25
D = 0.5
DF = round(D * FPS)          # 12 frames
W, H = 1280, 720
FF = M.FF


def sh(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("FAILED:", " ".join(cmd[:8]), "\n", r.stderr[-1500:])
        sys.exit(1)
    return r


def nframes(path):
    out = subprocess.run([FF, '-hide_banner', '-i', path],
                         capture_output=True, text=True).stderr
    for line in out.splitlines():
        if 'Duration:' in line:
            t = line.split('Duration:')[1].split(',')[0].strip()
            hh, mm, ss = t.split(':')
            return round((int(hh) * 3600 + int(mm) * 60 + float(ss)) * FPS)
    raise RuntimeError("no duration " + path)


def still_path(entry):
    """The prepared, cover-cropped 16:9 copy the camera move was built from."""
    return os.path.join(HERE, 'work', entry['stem'] + '.jpg')


def blend_clip(prev, cur, out):
    ia = Image.open(still_path(prev)).convert('RGB').resize((W, H), Image.LANCZOS)
    ib = Image.open(still_path(cur)).convert('RGB').resize((W, H), Image.LANCZOS)
    oa = Image.open(os.path.join(HERE, 'overlays', prev['stem'] + '.png')).convert('RGBA')
    ob = Image.open(os.path.join(HERE, 'overlays', cur['stem'] + '.png')).convert('RGBA')
    tmp = out + '.frames'
    os.makedirs(tmp, exist_ok=True)
    for k in range(DF):
        t = k / (DF - 1)
        frame = Image.blend(ia, ib, t).convert('RGBA')
        frame.alpha_composite(oa if k < DF // 2 else ob)
        frame.convert('RGB').save(f'{tmp}/{k:03d}.png')
    sh([FF, '-y', '-loglevel', 'error', '-framerate', str(FPS),
        '-i', f'{tmp}/%03d.png', '-c:v', 'libx264', '-preset', 'veryfast',
        '-crf', '19', '-pix_fmt', 'yuv420p', '-r', str(FPS), out])
    for f in os.listdir(tmp):
        os.remove(os.path.join(tmp, f))
    os.rmdir(tmp)


def main():
    plan = json.load(open(os.path.join(HERE, 'plan.json')))
    clips = os.path.join(HERE, 'clips')
    trans = os.path.join(HERE, 'trans')
    os.makedirs(trans, exist_ok=True)
    for f in os.listdir(trans):
        os.remove(os.path.join(trans, f))

    boundaries = {i for i in range(1, len(plan))
                  if plan[i]['section'] != plan[i - 1]['section']}
    print(f'{len(boundaries)} section boundaries: {sorted(boundaries)}')

    order = []
    for i, p in enumerate(plan):
        cur = os.path.join(clips, p['stem'] + '.mp4')
        if i in boundaries:
            prev = plan[i - 1]
            blend = f'{trans}/{i:04d}blend.mp4'
            blend_clip(prev, p, blend)
            # La + DF + (Lb - DF) = La + Lb, so the total runtime cannot drift
            # and every caption after the boundary still lands on its word.
            trimmed = f'{trans}/{i:04d}in.mp4'
            q = dict(p)
            q['frames'] = nframes(cur) - DF
            q['src'] = still_path(p)
            q['ov'] = os.path.join(HERE, 'overlays', p['stem'] + '.png')
            q['out'] = trimmed
            if os.path.exists(trimmed):
                os.remove(trimmed)
            M.build(q)
            order.append(blend)
            order.append(trimmed)
        else:
            order.append(cur)

    total = sum(nframes(c) for c in order)
    print(f'{len(order)} segments, {total} frames = {total / FPS:.3f} s')
    if total != 14384:
        print(f'WARNING: expected 14384 frames, got {total}')

    lst = os.path.join(HERE, 'final.txt')
    with open(lst, 'w') as f:
        for c in order:
            f.write(f"file '{c}'\n")
    print(lst)


if __name__ == '__main__':
    main()
