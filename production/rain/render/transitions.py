"""Dissolve at section changes, without a 283-input filter graph.

The graph approach (concat bodies + chained xfade) truncated silently at ~80 s
in this ffmpeg build, so this does it the boring way:

  for each section boundary, take the last frame of the outgoing clip and the
  first frame of the incoming clip, render a 0.5 s cross-fade between them, then
  trim 0.5 s off each neighbour and splice the blend in between.

Net duration is unchanged, and the concat stays a straight list of clips.
"""
import json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import motion as M
from PIL import Image

HERE = M.HERE
FPS = 25
D = 0.5
DF = round(D * FPS)          # 12 frames
W, H = 1280, 720


def sh(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("FAILED:", " ".join(cmd[:8]), "\n", r.stderr[-1500:])
        sys.exit(1)
    return r


def nframes(path):
    out = subprocess.run([M.ff(), '-hide_banner', '-i', path],
                         capture_output=True, text=True).stderr
    for line in out.splitlines():
        if 'Duration:' in line:
            t = line.split('Duration:')[1].split(',')[0].strip()
            hh, mm, ss = t.split(':')
            return round((int(hh) * 3600 + int(mm) * 60 + float(ss)) * FPS)
    raise RuntimeError("no duration " + path)


def frame_at(src, t, dst):
    sh([M.ff(), '-y', '-loglevel', 'error', '-ss', f'{t:.3f}', '-i', src,
        '-frames:v', '1', '-q:v', '2', dst])


def blend_clip(prev, cur, out):
    """Cross-fade *images* for DF frames, with a single caption swap.

    Blending the encoded clips cross-faded their burned-in captions too, so two
    sentences sat on top of each other for half a second. Instead this blends
    the raw stills and composites the outgoing slot's type for the first half
    and the incoming slot's type for the second half.
    """
    ia = Image.open(os.path.join(M.ROOT, prev['file'])).convert('RGB').resize((W, H), Image.LANCZOS)
    ib = Image.open(os.path.join(M.ROOT, cur['file'])).convert('RGB').resize((W, H), Image.LANCZOS)
    oa = Image.open(os.path.join(HERE, 'overlays', prev['stem'] + '.png')).convert('RGBA')
    ob = Image.open(os.path.join(HERE, 'overlays', cur['stem'] + '.png')).convert('RGBA')
    tmp = out + '.frames'
    os.makedirs(tmp, exist_ok=True)
    for k in range(DF):
        t = k / (DF - 1)
        frame = Image.blend(ia, ib, t).convert('RGBA')
        frame.alpha_composite(oa if k < DF // 2 else ob)
        frame.convert('RGB').save(f'{tmp}/{k:03d}.png')
    sh([M.ff(), '-y', '-loglevel', 'error', '-framerate', str(FPS),
        '-i', f'{tmp}/%03d.png', '-c:v', 'libx264', '-preset', 'veryfast',
        '-crf', '19', '-pix_fmt', 'yuv420p', '-r', str(FPS), out])
    for f in os.listdir(tmp):
        os.remove(os.path.join(tmp, f))
    os.rmdir(tmp)


def main():
    plan = json.load(open(os.path.join(HERE, 'plan.json')))
    m = json.load(open(os.path.join(M.ROOT, 'production/rain/shot-map-sentence.json')))
    first = {}
    for i, s in enumerate(m['slots']):
        first.setdefault(s['section'], i)
    starts = sorted(v for v in first.values() if v > 0)

    clips = os.path.join(HERE, 'clips')
    trans = os.path.join(HERE, 'trans')
    os.makedirs(trans, exist_ok=True)

    # A previous assemble.py run extended the tails of the boundary clips so a
    # chained xfade had something to chew on. Those files are still on disk and
    # are DF frames too long, so rebuild any clip whose length disagrees with
    # the plan before splicing.
    for p in plan:
        want = round(p['end'] * FPS) - round(p['start'] * FPS)
        got_path = os.path.join(clips, p['stem'] + '.mp4')
        if not os.path.exists(got_path) or nframes(got_path) != want:
            print(f"  rebuilding clip {p['stem']} ({want} frames)")
            q = dict(p)
            q['frames'] = want
            q['src'] = os.path.join(HERE, 'work', p['stem'] + '.jpg')
            q['ov'] = os.path.join(HERE, 'overlays', p['stem'] + '.png')
            q['out'] = got_path
            if os.path.exists(got_path):
                os.remove(got_path)
            if not os.path.exists(q['src']):
                M.prep(os.path.join(M.ROOT, p['file']), q['src'])
            M.build(q)

    order = []           # list of clip paths in final order
    boundaries = set(starts)

    for i, p in enumerate(plan):
        cur = os.path.join(clips, p['stem'] + '.mp4')
        if i in boundaries:
            prev = plan[i - 1]
            prevp = os.path.join(clips, prev['stem'] + '.mp4')
            # The dissolves must not change the total running time, or every
            # caption after them drifts. So the outgoing clip keeps all of its
            # frames and the incoming clip gives up its first DF frames, which
            # the blend stands in for. La + DF + (Lb - DF) = La + Lb.
            blend = f'{trans}/{i:04d}blend.mp4'
            blend_clip(prev, p, blend)
            trimmed = f'{trans}/{i:04d}in.mp4'
            # Re-render rather than trim: seeking into a 2 s H.264 clip lands on
            # the nearest frame and was costing one frame per boundary.
            q = dict(p)
            q['frames'] = nframes(cur) - DF
            q['src'] = os.path.join(HERE, 'work', p['stem'] + '.jpg')
            q['ov'] = os.path.join(HERE, 'overlays', p['stem'] + '.png')
            q['out'] = trimmed
            if os.path.exists(trimmed):
                os.remove(trimmed)
            M.build(q)
            order.append(blend)
            order.append(trimmed)
            print(f"  boundary at clip {i}: dissolve replaces the incoming "
                  f"{DF} frames")
        else:
            order.append(cur)

    # sanity: total frames must equal the narration
    total = sum(nframes(c) for c in order)
    print(f"{len(order)} segments, {total} frames = {total / FPS:.3f} s")

    lst = os.path.join(HERE, 'final.txt')
    with open(lst, 'w') as f:
        for c in order:
            f.write(f"file '{c}'\n")
    sh([M.ff(), '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0',
        '-i', lst, '-c', 'copy', '/tmp/video_master.mp4'])
    out = subprocess.run([M.ff(), '-hide_banner', '-i', '/tmp/video_master.mp4'],
                         capture_output=True, text=True).stderr
    print([l for l in out.splitlines() if 'Duration' in l])


if __name__ == '__main__':
    main()
