"""Render the static typography layer for every slot.

One RGBA PNG per slot at 1280x720, transparent everywhere except the type.
Keeping type on its own layer means the camera move can drift underneath
without the captions wobbling.

Everything is drawn on separate overlay images and alpha_composited, because
PIL's RGBA draw *replaces* alpha instead of blending it (see shot-register.md).
"""
import json, os, re, glob
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))

d = json.load(open(os.path.join(ROOT, 'production/rain/shot-map-sentence.json')))
cues = json.load(open(os.path.join(HERE, 'cues.json')))
Q = json.load(open(os.path.join(HERE, 'quiz_window.json')))
files = {int(re.match(r'real-(\d+)-', os.path.basename(f)).group(1)): f
         for f in glob.glob(os.path.join(ROOT, 'production/rain/visuals-3d/real-*'))}
RECON = set(d['reconstruction_shots'])
rows = d['slots']

# The script has no section 5, so on-screen numbers are 1-4 then 6-9 and do not
# match the map's own 01-08 slot indices.
SEC_TITLE = {"01": "1 · The rain doesn't stop",
             "02": "2 · The first problem isn't just getting wet",
             "03": "3 · A camp beside a lake",
             "04": "4 · What a floor can tell us",
             "05": "6 · The trouble with fire",
             "06": "7 · What about food?",
             "07": "8 · Not everyone lived the same way",
             "08": "9 · When the rain ends"}

# Place cards change mid-section: §07 opens on Ohalo II and only becomes Border
# Cave when the narration says so. Never let the two share a frame.
SUB_BREAKS = {"03": [(124.607, "Ohalo II · Sea of Galilee · c. 23,000 years ago")],
              "07": [(412.084, "Ohalo II · Sea of Galilee · c. 23,000 years ago"),
                     (427.620, "Border Cave · southern Africa · c. 200,000 years ago")]}

W, H = 1280, 720
DEJA = '/usr/share/fonts/truetype/dejavu/'
F = ImageFont.truetype(DEJA + 'DejaVuSans.ttf', 18)
FS = ImageFont.truetype(DEJA + 'DejaVuSans-Bold.ttf', 40)
FM = ImageFont.truetype(DEJA + 'DejaVuSans.ttf', 26)
FB = ImageFont.truetype(DEJA + 'DejaVuSans-Bold.ttf', 26)


def sub_for(sec, t):
    best = None
    for at, txt in SUB_BREAKS.get(sec, []):
        if t >= at - 0.02:
            best = txt
    return best


def wrap(dr, t, f, maxw):
    ls, c = [], ""
    for w in t.split():
        x = (c + " " + w).strip()
        if dr.textbbox((0, 0), x, font=f)[2] <= maxw:
            c = x
        else:
            if c:
                ls.append(c)
            c = w
    if c:
        ls.append(c)
    return ls


def cue_at(t):
    for c in cues:
        if c['start'] <= t < c['end']:
            return c['text']
    return cues[-1]['text']


def quiz_layer():
    ov = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    dr = ImageDraw.Draw(ov)
    dr.rectangle([0, 0, W, H], fill=(11, 15, 20, 255))
    panels = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    dp = ImageDraw.Draw(panels)
    for k in range(4):
        y = 272 + k * 62
        dp.rounded_rectangle([90, y, 600, y + 50], radius=8,
                             fill=(255, 255, 255, 30), outline=(255, 255, 255, 80), width=1)
    ov.alpha_composite(panels)
    txt = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    dt = ImageDraw.Draw(txt)
    dt.text((90, 104), "QUIZ", font=FB, fill=(150, 195, 225, 255))
    dt.text((90, 144), "Roughly how old is the Border Cave", font=FS, fill=(255, 255, 255, 255))
    dt.text((90, 190), "grass-bedding evidence?", font=FS, fill=(255, 255, 255, 255))
    for k, (o, tx) in enumerate([("A", "2,000 years"), ("B", "23,000 years"),
                                 ("C", "200,000 years"), ("D", "2 million years")]):
        y = 272 + k * 62
        dt.text((112, y + 12), o, font=FB, fill=(150, 195, 225, 255))
        dt.text((152, y + 12), tx, font=FM, fill=(250, 250, 250, 255))
    dt.text((90, 556), "Answer in the narration that follows.", font=F, fill=(185, 185, 185, 235))
    ov.alpha_composite(txt)
    return ov


def still_layer(r, i):
    ov = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    dr = ImageDraw.Draw(ov)
    dr.rectangle([0, 0, W, 84], fill=(0, 0, 0, 55))
    dr.rectangle([0, H - 120, W, H], fill=(0, 0, 0, 68))

    prev = rows[i - 1] if i > 0 else None
    new_sec = prev is None or prev['section'] != r['section']
    sub = sub_for(r['section'], r['start'])
    run_i = 0
    for j in range(i - 1, -1, -1):
        if rows[j]['section'] != r['section'] or sub_for(r['section'], rows[j]['start']) != sub:
            break
        run_i += 1

    if new_sec:
        t = SEC_TITLE[r['section']]
        c = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        dc = ImageDraw.Draw(c)
        tw = dc.textbbox((0, 0), t, font=FS)[2]
        dc.rounded_rectangle([54, 124, 84 + tw, 200], radius=10, fill=(0, 0, 0, 100))
        dc.text((70, 140), t, font=FS, fill=(255, 255, 255, 255))
        ov.alpha_composite(c)
    # hold a place card for its first three slots; a 2 s flash reads as a glitch
    if sub and run_i < 3:
        c = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        dc = ImageDraw.Draw(c)
        dc.rounded_rectangle([54, 206, 74 + dc.textbbox((0, 0), sub, font=FM)[2], 248],
                             radius=8, fill=(0, 0, 0, 92))
        dc.text((64, 213), sub, font=FM, fill=(238, 238, 238, 240))
        ov.alpha_composite(c)

    ls = wrap(dr, cue_at((r['start'] + r['end']) / 2), FM, 1080)
    lh = 34
    y = H - 56 - lh * len(ls)
    for ln in ls:
        ww = dr.textbbox((0, 0), ln, font=FM)[2]
        x = (W - ww) // 2
        dr.rounded_rectangle([x - 14, y - 4, x + ww + 14, y + 30], radius=6, fill=(0, 0, 0, 118))
        dr.text((x, y), ln, font=FM, fill=(255, 255, 255, 246))
        y += lh

    lab = ("Illustrative reconstruction — hypothetical scene" if r['shot'] in RECON
           else "Modern landscape — atmosphere only")
    lw = dr.textbbox((0, 0), lab, font=F)[2]
    dr.rounded_rectangle([30, 30, 44 + lw, 64], radius=6, fill=(0, 0, 0, 100))
    dr.text((37, 37), lab, font=F, fill=(228, 228, 228, 240))
    return ov


def main():
    out = os.path.join(HERE, 'overlays')
    os.makedirs(out, exist_ok=True)
    for f in glob.glob(out + '/*.png'):
        os.remove(f)
    plan = []
    for i, r in enumerate(rows):
        on_quiz = Q['start'] - 0.01 <= r['start'] < Q['end'] - 0.01
        layer = quiz_layer() if on_quiz else still_layer(r, i)
        layer.save(f'{out}/{i:04d}.png')
        plan.append({'i': i, 'shot': r['shot'], 'file': os.path.relpath(files[r['shot']], ROOT),
                     'stem': f'{i:04d}', 'start': r['start'], 'end': r['end'],
                     'dur': round(r['end'] - r['start'], 3), 'quiz': bool(on_quiz)})
    json.dump(plan, open(os.path.join(HERE, 'plan.json'), 'w'), indent=1)
    print(f"{len(plan)} overlay layers -> {out}")


if __name__ == '__main__':
    main()
