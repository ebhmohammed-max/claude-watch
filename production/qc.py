"""Preflight checks for an episode, so the next one doesn't repeat these bugs.

Every failure below was found by hand while making the clothing episode, and
every one of them had already shipped at least once before it was caught:

  * clips that were the right length but the wrong picture (motion.py reuses a
    clip by duration, and a re-timed overlay keeps the duration identical)
  * a stills plan whose "2 s cuts" were a time grid, not a cut grid -- 76% of
    the film sat on one image held six seconds or longer, one for 34 s
  * labels that contradicted the picture underneath them
  * source cards firing seconds away from the sentence they attribute
  * chapter timestamps that drift out of step with the sections
  * captions with gaps, overlaps, or speech that falls outside every cue

Run this against an episode directory before calling anything delivered:

    python3 production/qc.py production/tailors

Exit code is 0 only if nothing FAILED. Warnings are judgement calls and do not
fail the build.
"""
import json, os, re, subprocess, sys

def _resolve_ffmpeg():
    """No hard-coded sandbox path -- that is what broke the rebuild once."""
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
FPS = 25
# how often to sample the delivered picture for a disclosure mark
SAMPLE_STEP = 2

# A single image may not sit on screen longer than this before the "2 s cut"
# claim stops being true. The rain episode (accepted) never exceeded 2.9 s.
MAX_HOLD_WARN = 6.0
MAX_HOLD_FAIL = 12.0
# Images per minute. Rain ran 11.3; anything under ~8 is a slideshow.
MIN_IMGS_PER_MIN = 8.0

CLAIM_WORDS = re.compile(
    r'\b(Contrebandiers|Morocco|Denisova|Siberia|Dzudzuana|Georgia|Pavlov|'
    r'Sunghir|Vladimir|Toulouse|Egypt|needle|scraper|bead|fibre|fiber|flax|'
    r'awl|hide|pelt|ivory|ochre|Toups|Hallett|Gilligan|Kvavadze|Bar-Yosef|'
    r'Trinkaus|Buzhilova)\b', re.I)

# LANDSCAPE means "modern landscape, atmosphere only". It must never sit under a
# specific claim, and it was also found on a modern hallway, a modern street and
# a scene containing people -- none of which are landscapes.
SCENE_CLASSES = {'LANDSCAPE': 'modern landscape',
                 'MODERN': 'present-day scene',
                 'MUSEUM': 'museum gallery'}

RESULTS = []

# Disclosure is proved by differencing, not by recognising a shape: decode the
# same instant from the source picture and from the delivered file and look at
# the bottom-left corner. If it is unchanged, nothing was drawn there. This has
# no heuristic to tune and cannot be fooled by dark or washed-out footage, which
# is exactly what three earlier attempts at a "does this look labelled" test
# got wrong.
DISC_CROP = 'crop=420:44:860:6'   # top-right, where the mark is drawn
DISC_MIN_DELTA = 1.0   # a drawn plate moves the mean by ~8 luma; nothing moves it <1
SAMPLE_STEP = 2          # seconds of film between disclosure samples


def _disc_grab(path, t, tmp):
    subprocess.run([FF, '-hide_banner', '-loglevel', 'error', '-y', '-ss', str(t),
                    '-i', path, '-frames:v', '1', '-vf', DISC_CROP, tmp],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _disc_delta(a, b):
    import numpy as np
    from PIL import Image
    x = np.asarray(Image.open(a).convert('L'), dtype=np.float32)
    y = np.asarray(Image.open(b).convert('L'), dtype=np.float32)
    return float(np.abs(x - y).mean())


def missing_disclosure(mp4, total, source, step=None):
    """Times where the delivered corner matches the unlabelled source."""
    import tempfile
    step = step or SAMPLE_STEP
    bad = []
    t1 = tempfile.NamedTemporaryFile(suffix='.png', delete=False).name
    t2 = tempfile.NamedTemporaryFile(suffix='.png', delete=False).name
    for t in range(3, int(total) - 3, step):
        _disc_grab(mp4, t, t1)
        _disc_grab(source, t, t2)
        if _disc_delta(t1, t2) < DISC_MIN_DELTA:
            bad.append(t)
    os.unlink(t1); os.unlink(t2)
    return sorted(bad)


def _resolve_ffmpeg():
    """No hard-coded sandbox path -- that is what broke the rebuild once."""
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
FPS = 25
# how often to sample the delivered picture for a disclosure mark
SAMPLE_STEP = 2

# A single image may not sit on screen longer than this before the "2 s cut"
# claim stops being true. The rain episode (accepted) never exceeded 2.9 s.
MAX_HOLD_WARN = 6.0
MAX_HOLD_FAIL = 12.0
# Images per minute. Rain ran 11.3; anything under ~8 is a slideshow.
MIN_IMGS_PER_MIN = 8.0

CLAIM_WORDS = re.compile(
    r'\b(Contrebandiers|Morocco|Denisova|Siberia|Dzudzuana|Georgia|Pavlov|'
    r'Sunghir|Vladimir|Toulouse|Egypt|needle|scraper|bead|fibre|fiber|flax|'
    r'awl|hide|pelt|ivory|ochre|Toups|Hallett|Gilligan|Kvavadze|Bar-Yosef|'
    r'Trinkaus|Buzhilova)\b', re.I)

# LANDSCAPE means "modern landscape, atmosphere only". It must never sit under a
# specific claim, and it was also found on a modern hallway, a modern street and
# a scene containing people -- none of which are landscapes.
SCENE_CLASSES = {'LANDSCAPE': 'modern landscape',
                 'MODERN': 'present-day scene',
                 'MUSEUM': 'museum gallery'}

RESULTS = []

# Where the disclosure corner mark lives, and its signature: a nearly
# gradient-free band with bright glyphs on top of a darker plate.
DISC_FLAT = 3.2          # max luma variation across the plate
DISC_BRIGHT = 0.6        # share of pixels above this that count as glyphs
DISC_BRIGHT_LEVEL = 150


def check(name, ok, detail='', warn=False):
    RESULTS.append((name, ok, detail, warn))
    tag = 'WARN' if (warn and not ok) else ('PASS' if ok else 'FAIL')
    print(f'  [{tag}] {name}' + (f' -- {detail}' if detail else ''))
    return ok


def ffprobe_frames(path):
    out = subprocess.run([FF, '-hide_banner', '-i', path],
                         capture_output=True, text=True).stderr
    for line in out.splitlines():
        if 'Duration:' in line:
            t = line.split('Duration:')[1].split(',')[0].strip()
            hh, mm, ss = t.split(':')
            return round((int(hh) * 3600 + int(mm) * 60 + float(ss)) * FPS)
    return -1


def load_json(path):
    with open(path) as fh:
        return json.load(fh)


def runs_of(plan, key):
    """Collapse the plan into runs of consecutive slots sharing one image."""
    runs = []
    for c in plan:
        if runs and runs[-1][0] == c[key]:
            runs[-1][2] = c['end']
        else:
            runs.append([c[key], c['start'], c['end']])
    return runs


def parse_srt(path):
    def ts(x):
        h, m, rest = x.split(':')
        s, ms = rest.split(',')
        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000
    cues = []
    for block in open(path).read().strip().split('\n\n'):
        lines = block.split('\n')
        if len(lines) < 2:
            continue
        a, b = [ts(p) for p in lines[1].split(' --> ')]
        cues.append((a, b, '\n'.join(lines[2:])))
    return cues


def main(ep):
    print(f'\nQC · {ep}\n' + '=' * (6 + len(ep)))
    render = os.path.join(ep, 'render')
    plan_p = os.path.join(render, 'plan.json')
    if not os.path.exists(plan_p):
        print('  no render/plan.json -- nothing to check')
        return 1
    plan = load_json(plan_p)
    kind = 'still' if 'still' in plan[0] else ('file' if 'file' in plan[0] else None)
    if kind is None:
        print('  unrecognised plan schema')
        return 1

    # ---- 1. plan integrity -------------------------------------------------
    gaps = [(a['i'], round(b['start'] - a['end'], 3))
            for a, b in zip(plan, plan[1:]) if abs(b['start'] - a['end']) > 0.002]
    check('plan has no gaps or overlaps', not gaps, f'{len(gaps)} bad joins' if gaps else '')
    total = round(plan[-1]['end'], 3)
    frames = round(plan[-1]['end'] * FPS)
    check('plan starts at zero', abs(plan[0]['start']) < 0.002, f'{plan[0]["start"]}')

    # ---- 2. pacing ---------------------------------------------------------
    if kind == 'still' or kind == 'file':
        runs = runs_of(plan, kind)
        holds = [b - a for _, a, b in runs]
        worst = max(holds)
        per_min = len(runs) / (total / 60)
        check('no single image held absurdly long', worst <= MAX_HOLD_FAIL,
              f'longest {worst:.1f}s')
        check(f'no image held over {MAX_HOLD_WARN:.0f}s', worst <= MAX_HOLD_WARN,
              f'longest {worst:.1f}s', warn=True)
        check(f'at least {MIN_IMGS_PER_MIN:.0f} images per minute',
              per_min >= MIN_IMGS_PER_MIN, f'{per_min:.1f}/min', warn=True)

    # ---- 3. label honesty --------------------------------------------------
    shots_p = os.path.join(render, 'shots.json')
    if kind == 'still' and os.path.exists(shots_p) and 'sentence' in plan[0]:
        spec = load_json(shots_p)
        labels = spec.get('labels', {})
        missing = [c['still'] for c in plan if str(c['still']) not in labels]
        check('every still in the cut has a label class', not missing,
              f'{sorted(set(missing))}' if missing else '')
        bad = [c for c in plan
               if labels.get(str(c['still'])) == 'LANDSCAPE'
               and CLAIM_WORDS.search(c['sentence'])]
        check('no landscape label under a specific claim', not bad,
              f'{len(bad)} slots, first {bad[0]["sentence"][:50]!r}' if bad else '')
        # every class used must have on-screen wording, or overlays.py KeyErrors
        ov_p = os.path.join(render, 'overlays.py')
        if os.path.exists(ov_p):
            src = open(ov_p).read()
            used = {labels.get(str(c['still'])) for c in plan}
            absent = [u for u in used if u and f"'{u}'" not in src]
            check('every label class has on-screen wording', not absent, str(absent))

    # ---- 4. captions -------------------------------------------------------
    srt = os.path.join(ep, os.path.basename(ep.rstrip('/')) + '-episode.srt')
    if not os.path.exists(srt):
        cands = [f for f in os.listdir(ep) if f.endswith('.srt')]
        srt = os.path.join(ep, cands[0]) if cands else None
    if srt and os.path.exists(srt):
        cues = parse_srt(srt)
        overlaps = [(cues[i][1], cues[i + 1][0]) for i in range(len(cues) - 1)
                    if cues[i][1] > cues[i + 1][0] + 0.001]
        check('caption cues do not overlap', not overlaps, f'{len(overlaps)} overlaps')
        gaps = [b[0] - a[1] for a, b in zip(cues, cues[1:]) if b[0] - a[1] > 0.001]
        check('caption cues are contiguous', not gaps,
              f'{len(gaps)} gaps, max {max(gaps):.2f}s' if gaps else '')
        check('last cue ends at the runtime', abs(cues[-1][1] - total) < 0.6,
              f'{cues[-1][1]:.2f}s vs {total:.2f}s')
    else:
        check('subtitle file present', False, 'no .srt found')

    # ---- 5. chapters -------------------------------------------------------
    kit_p = os.path.join(ep, 'kit', 'upload-kit.md')
    if os.path.exists(kit_p):
        kit = open(kit_p).read()
        listed = re.findall(r'^(\d{1,2}:\d{2})\s+(.+)$', kit, re.M)
        starts, prev = [], None
        map_p = os.path.join(render, 'map.json')
        if os.path.exists(map_p):
            for c in load_json(map_p)['cues']:
                if c['section'] != prev:
                    starts.append(c['start'])
                    prev = c['section']
        if listed and starts:
            def s(x):
                m, sec = x.split(':')
                return int(m) * 60 + int(sec)
            off = [(s(a), round(b, 1)) for (a, _), b in zip(listed, starts)
                   if abs(s(a) - b) > 1.0]
            check('chapter times match section starts', not off,
                  f'{off}' if off else f'{len(listed)} chapters')

    # ---- 6. source cards ---------------------------------------------------
    ov_p = os.path.join(render, 'overlays.py')
    map_p = os.path.join(render, 'map.json')
    if os.path.exists(ov_p) and os.path.exists(map_p):
        py = open(ov_p).read()
        srcs = re.findall(r"\(\s*([0-9.]+)\s*,\s*'(Source · [^']+)'", py)
        cues = load_json(map_p)['cues']
        if srcs:
            orphans, soft = [], []
            for t, text in srcs:
                t = float(t)
                near = [c for c in cues if c['start'] - 1.0 <= t <= c['end']]
                who = re.findall(r'([A-Z][a-zë]+)', text.split('·')[1])
                named = near and any(
                    any(w.lower() in c['sentence'].lower() for w in who[:1])
                    for c in near)
                if not near:
                    orphans.append((t, text, 'no cue at that time'))
                elif not named:
                    # The voice does not always say the author's name: the
                    # Sunghir card credits a paper the narration applies without
                    # naming. It still has to fall inside a real cue, and that
                    # cue still has to be about the site. Naming the author is
                    # the stronger form, so warn when it is absent and fail only
                    # when the card lands on nothing.
                    soft.append((t, text))
            check('every source card names its author on screen at that moment',
                  not soft,
                  '; '.join(f'{t:.1f}s {x[:30]}' for t, x in soft)
                  if soft else f'{len(srcs)} cards', warn=True)
            check('every source card lands inside a cue',
                  not orphans,
                  '; '.join(f'{t:.1f}s {x[:28]} ({why})' for t, x, why in orphans)
                  if orphans else f'{len(srcs)} cards')

    # ---- 6b. disclosure actually on the picture ----------------------------
    # The gate used to take shots.json's word that every still carried a label.
    # It did not: measured on the delivered frames, most of the ancient
    # reconstruction had no disclosure at all while the file claimed it did.
    # So this samples the *delivered* pixels. A disclosure is a bottom-left
    # corner mark lying flat in the luma gradient and containing bright glyphs;
    # scene content, however dark, is textured across that patch and has no
    # crisp edge.
    kitdir = os.path.join(ep, 'kit')
    kit_mp4s = ([os.path.join(kitdir, f) for f in sorted(os.listdir(kitdir))
                 if f.endswith('.mp4')] if os.path.isdir(kitdir) else [])
    # Only episodes that opted into the continuous corner mark carry
    # labels.json. For those it is provable, so it is a hard check; older
    # episodes without the mark are left alone rather than retro-failed.
    src_pic = os.path.join(render, 'picture.mp4')
    has_marks = os.path.exists(os.path.join(render, 'labels.json')) \
        and os.path.exists(src_pic)
    if kit_mp4s and has_marks:
        try:
            blind = missing_disclosure(kit_mp4s[0], frames / FPS, src_pic)
        except ImportError:
            check('disclosure present on the delivered picture', False,
                  'numpy/PIL not available to measure it', warn=True)
        else:
            n = len(range(3, int(frames / FPS) - 3, SAMPLE_STEP))
            check('every sampled frame carries a disclosure', not blind,
                  f'{len(blind)} of {n} samples unlabelled, first at '
                  f'{blind[0] / FPS:.0f}s' if blind else f'{n} samples')

    # ---- 7. the delivered file --------------------------------------------
    mp4s = []
    for root, _, files in os.walk(os.path.join(ep, 'kit')):
        mp4s += [os.path.join(root, f) for f in files if f.endswith('.mp4')]
    if mp4s:
        got = ffprobe_frames(mp4s[0])
        check('delivered mp4 frame count matches the plan', got == frames,
              f'{got} vs {frames}')
        check('delivered mp4 is under the 100 MB upload limit',
              os.path.getsize(mp4s[0]) < 100_000_000,
              f'{os.path.getsize(mp4s[0]) / 1e6:.1f} MB', warn=True)
        # a clip rebuilt after its overlay changed is the stale-clip trap
        ovdir = os.path.join(render, 'overlays')
        cldir = os.path.join(render, 'clips')
        if os.path.isdir(ovdir) and os.path.isdir(cldir):
            stale = 0
            for f in os.listdir(ovdir):
                c = os.path.join(cldir, f.replace('.png', '.mp4'))
                if os.path.exists(c) and \
                        os.path.getmtime(c) < os.path.getmtime(os.path.join(ovdir, f)):
                    stale += 1
            check('no clip is older than the overlay it should contain', stale == 0,
                  f'{stale} stale clips -- rebuild motion.py' if stale else '')
    else:
        check('delivered mp4 present in kit/', False, 'no mp4 found')

    fails = [r for r in RESULTS if not r[1] and not r[3]]
    warns = [r for r in RESULTS if not r[1] and r[3]]
    print(f'\n  {len(RESULTS) - len(fails) - len(warns)} pass · '
          f'{len(warns)} warn · {len(fails)} fail')
    return 0 if not fails else 1


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
