"""Assemble the cut: per-slot clips, with a dissolve at each section change.

Hard cuts inside a section are correct - the whole point is ~30 images a
minute. But cutting hard *into* a new chapter makes it feel like a slideshow
restarting. So the last clip of each section gets its tail extended by the
dissolve length, and the next clip is cross-faded over that tail.

Everything is frame-exact: frame counts come from cumulative rounding so the
sum of clips equals the narration length exactly.
"""
import json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import motion as M

HERE = M.HERE
FPS = 25
DISSOLVE = 0.5


def load():
    plan = json.load(open(os.path.join(HERE, 'plan.json')))
    for p in plan:
        p['frames'] = round(p['end'] * FPS) - round(p['start'] * FPS)
    m = json.load(open(os.path.join(M.ROOT, 'production/rain/shot-map-sentence.json')))
    first = {}
    for i, s in enumerate(m['slots']):
        first.setdefault(s['section'], i)
    # clip whose *start* opens a new section (not the very first one)
    starts = sorted(v for v in first.values() if v > 0)
    return plan, starts


def rebuild_boundary(plan, i, dframes):
    """Re-render clip i with extra tail frames so a dissolve has something to eat."""
    p = dict(plan[i])
    p['frames'] = plan[i]['frames'] + dframes
    p['src'] = os.path.join(HERE, 'work', p['stem'] + '.jpg')
    p['ov'] = os.path.join(HERE, 'overlays', p['stem'] + '.png')
    p['out'] = os.path.join(HERE, 'clips', p['stem'] + '.mp4')
    if not os.path.exists(p['src']):
        M.prep(os.path.join(M.ROOT, p['file']), p['src'])
    if os.path.exists(p['out']):
        os.remove(p['out'])
    M.build(p)
    return p


def main():
    plan, starts = load()
    dframes = round(DISSOLVE * FPS)
    print(f"{len(plan)} clips, dissolves into {len(starts)} section starts")

    clips = os.path.join(HERE, 'clips')
    missing = [p for p in plan if not os.path.exists(os.path.join(clips, p['stem'] + '.mp4'))]
    if missing:
        print(f"!! {len(missing)} clips missing; run motion.py first")
        sys.exit(1)

    for i in starts:
        rebuild_boundary(plan, i - 1, dframes)
        print(f"  extended tail of clip {i-1} by {dframes} frames")

    # filter graph: xfade chains, offsets measured from each cut point
    # Walk the clips in order and carry one running output. Clips are chained
    # straight through so no input is ever left dangling: an unused input is a
    # hard error, and 283 of them in one graph is also a bad time.
    # Each xfade eats DISSOLVE seconds of timeline, so the offset for the next
    # one is not the absolute start time - it is the running output length
    # minus the overlap. Track it explicitly or every dissolve drifts.
    lines = ["[0:v]setpts=PTS-STARTPTS,fps=%d,settb=1/1000[c0]" % FPS]
    cur, n = "c0", 1
    cur_len = plan[starts[0]]['start'] + (DISSOLVE if starts else 0)
    for j, idx in enumerate(starts):
        nxt = starts[j + 1] if j + 1 < len(starts) else len(plan)
        chain = ""
        body_len = 0.0
        for i in range(idx, nxt):
            lines.append(f"[{i}:v]setpts=PTS-STARTPTS,fps={FPS},settb=1/1000[c{n}]")
            chain += f"[c{n}]"
            body_len += plan[i]['frames'] / FPS
            n += 1
        lines.append(f"{chain}concat=n={nxt - idx}:v=1:a=0,settb=1/1000[body{j}]")
        offset = cur_len - DISSOLVE
        lines.append(
            f"[{cur}][body{j}]xfade=transition=fade:duration={DISSOLVE}:offset={offset:.3f}[x{j}]")
        cur_len = offset - DISSOLVE + DISSOLVE + DISSOLVE + body_len - DISSOLVE
        cur_len = offset + body_len
        cur = f"x{j}"
        print(f"  xfade {j}: offset {offset:.3f}, body {body_len:.3f}, out {cur_len:.3f}")
    lines.append(f"[{cur}]settb=1/1000,format=yuv420p[outv]")
    script = os.path.join(HERE, 'xfade.ffscript')
    open(script, 'w').write(";\n".join(lines) + "\n")

    cmd = [M.ff(), '-y', '-loglevel', 'error', '-stats']
    for p in plan:
        cmd += ['-i', os.path.join(clips, p['stem'] + '.mp4')]
    # ffmpeg 9 renamed -filter_complex_script to -/filter_complex
    cmd += ['-/filter_complex', script, '-map', '[outv]',
            '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '19',
            '-r', str(FPS), '/tmp/video_xfade.mp4']
    print(" ".join(cmd[:6]), "...")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("ffmpeg failed:\n" + r.stderr[-3000:])
        sys.exit(1)
    dur = subprocess.run([M.ff(), '-hide_banner', '-i', '/tmp/video_xfade.mp4'],
                         capture_output=True, text=True).stderr
    print([l for l in dur.splitlines() if 'Duration' in l])


if __name__ == '__main__':
    main()
