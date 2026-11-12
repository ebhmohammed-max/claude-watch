"""Keep the reconstruction disclosure on screen for the whole film.

The V3 picture carries its own source cards, but only on part of the film: the
study graphics and a few Morocco shots. Measured on the delivered file, the
ancient reconstruction -- 1:10 to 9:55, most of the episode -- and the modern
opening and closing carried no disclosure at all. The project's rule is that an
image must never be presented as something it is not, so that had to change.

Why a corner mark rather than another card:

  * Detection of "does this shot already have a card" kept misfiring. Dark
    footage, washed-out white frames and the cards themselves all look alike in
    the top-left corner, and a wrong guess means either a double-labelled shot
    or, worse, an unlabelled one.
  * The section boundaries are measured, not guessed. map.json already records
    where each section starts, so a mark that runs continuously for each
    section can be proven to cover 100% of the runtime -- no per-shot detection
    to get wrong.
  * A corner mark reads as a documentary convention rather than a mistake, and
    it cannot collide with the picture's own cards (top-left) or the captions
    (bottom centre): it sits at bottom-left, clear of both.

The wording is about the image and never about the archaeology:

  ILLUSTRATIVE RECONSTRUCTION      no real place is shown
  ILLUSTRATIVE - NOT THE ACTUAL SITE   a landscape standing in for a place
  PRESENT DAY - ILLUSTRATIVE RECONSTRUCTION   a modern room, not archive footage
  ILLUSTRATIVE GRAPHIC             a chart drawn for this film

Nothing here asserts that a study exists, that a site looked like this, or that
anyone was photographed.
"""
import json
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'picture.mp4')
OUT = os.path.join(HERE, 'picture-labelled.mp4')
SPEC = os.path.join(HERE, 'labels.json')
MAP = os.path.join(HERE, 'map.json')

W, H = 1280, 720
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
SIZE = 15

# section start -> wording for that section. Keys are the section starts in
# map.json; anything unlisted falls back to the reconstruction wording.
BY_SECTION = {
    0.0: 'PRESENT DAY \u00b7 ILLUSTRATIVE RECONSTRUCTION',
    98.0: 'ILLUSTRATIVE \u00b7 NOT THE ACTUAL SITE',
    137.0: 'ILLUSTRATIVE \u00b7 NOT THE ACTUAL SITE',
    190.0: 'ILLUSTRATIVE RECONSTRUCTION',
    251.0: 'ILLUSTRATIVE RECONSTRUCTION',
    400.0: 'ILLUSTRATIVE RECONSTRUCTION',
    491.0: 'ILLUSTRATIVE RECONSTRUCTION',
    597.0: 'ILLUSTRATIVE RECONSTRUCTION',
    659.0: 'PRESENT DAY \u00b7 ILLUSTRATIVE RECONSTRUCTION',
}
# the study stretch is graphics, not places
GRAPHIC_SPANS = [(436.6, 490.0)]

MARGIN_X, MARGIN_Y = 16, 14
ALPHA_PLATE, ALPHA_TEXT = 96, 165


def _resolve_ffmpeg():
    import glob, shutil
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


def corner_plate(text, path):
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype(FONT, SIZE)
    track = 1.9
    widths = [d.textlength(ch, font=font) + track for ch in text]
    tw = int(sum(widths)) - int(track)
    th = SIZE + 8
    x0 = MARGIN_X
    y0 = H - MARGIN_Y - th
    d.rectangle([x0, y0, x0 + tw + 20, y0 + th], fill=(8, 10, 14, ALPHA_PLATE))
    x = x0 + 10
    for ch, wd in zip(text, widths):
        d.text((x, y0 + 4), ch, font=font, fill=(236, 236, 236, ALPHA_TEXT))
        x += wd
    img.save(path)


def plan_spans():
    """Section spans from map.json, with the study stretch re-worded."""
    m = json.load(open(MAP))
    secs = m['sections'] if isinstance(m, dict) else m
    starts = [s['start'] for s in secs]
    end = 682.36
    spans = []
    for i, st in enumerate(starts):
        en = starts[i + 1] if i + 1 < len(starts) else end
        text = BY_SECTION.get(round(st, 1), 'ILLUSTRATIVE RECONSTRUCTION')
        pieces = [(st, en, text)]
        for ga, gb in GRAPHIC_SPANS:
            out = []
            for a, b, t in pieces:
                if b <= ga or a >= gb:
                    out.append((a, b, t))
                    continue
                if a < ga:
                    out.append((a, ga, t))
                out.append((max(a, ga), min(b, gb), 'ILLUSTRATIVE GRAPHIC'))
                if b > gb:
                    out.append((gb, b, t))
            pieces = out
        spans.extend(pieces)
    return spans


def main():
    ff = _resolve_ffmpeg()
    os.makedirs(os.path.join(HERE, 'labels'), exist_ok=True)
    spans = plan_spans()

    plates = {}
    for a, b, text in spans:
        if text not in plates:
            p = os.path.join(HERE, 'labels', f'corner_{len(plates):02d}.png')
            corner_plate(text, p)
            plates[text] = p

    order = list(plates)
    idx = {t: i + 1 for i, t in enumerate(order)}
    cmd = [ff, '-hide_banner', '-loglevel', 'error', '-y', '-i', SRC]
    for t in order:
        cmd += ['-i', plates[t]]

    BS = chr(92)
    chain, prev = [], '[0:v]'
    for k, text in enumerate(order, start=1):
        runs = [(a, b) for a, b, t in spans if t == text]
        expr = '+'.join(f'between(t{BS},{a:.3f}{BS},{b:.3f})' for a, b in runs)
        out = f'[v{k}]'
        chain.append(f'{prev}[{idx[text]}:v]overlay=0:0:enable={expr}{out}')
        prev = out
        print(f'  {text:52s} {len(runs):2d} run(s)')

    cmd += ['-filter_complex', ';'.join(chain), '-map', prev,
            '-c:v', 'libx264', '-preset', 'slow', '-crf', '24',
            '-tune', 'stillimage', '-pix_fmt', 'yuv420p', '-r', '25',
            '-an', '-sn', OUT]
    print('encoding ...')
    subprocess.run(cmd, check=True)

    covered = sum(b - a for a, b, _ in spans)
    json.dump({'source': 'picture.mp4',
               'method': ('Continuous bottom-left corner mark, one run per '
                          'measured section, so disclosure covers every frame '
                          'by construction instead of by detection.'),
               'spans': [{'start': a, 'end': b, 'text': t} for a, b, t in spans],
               'covered_seconds': round(covered, 2)},
              open(SPEC, 'w'), indent=1)
    print(f'coverage {covered:.2f}s of 682.36s')
    print(f'wrote {OUT}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
