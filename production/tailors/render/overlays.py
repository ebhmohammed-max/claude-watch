"""Render the typography layer for every slot.

One RGBA PNG per slot at 1280x720, transparent except for type. Type is drawn
on its own layer and composited *after* the camera move, so captions never
wobble or resample with the push-in.

PIL's RGBA draw replaces alpha rather than blending it, so every element that
needs translucency is drawn on its own image and alpha_composited.
"""
import json, os, glob
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
M = json.load(open(os.path.join(HERE, 'map.json')))
SPEC = json.load(open(os.path.join(HERE, 'shots.json')))
LABELS = SPEC['labels']
rows = json.load(open(os.path.join(HERE, 'shotplan.json')))
cues = M['cues']

W, H = 1280, 720
DEJA = '/usr/share/fonts/truetype/dejavu/'
F = ImageFont.truetype(DEJA + 'DejaVuSans.ttf', 18)
FSM = ImageFont.truetype(DEJA + 'DejaVuSans.ttf', 16)
FOBJ = ImageFont.truetype(DEJA + 'DejaVuSans.ttf', 18)
FM = ImageFont.truetype(DEJA + 'DejaVuSans.ttf', 26)
FS = ImageFont.truetype(DEJA + 'DejaVuSans-Bold.ttf', 40)
FB = ImageFont.truetype(DEJA + 'DejaVuSans-Bold.ttf', 26)

LABEL_TEXT = {
    'RECON':     'Illustrative reconstruction — hypothetical scene',
    'OBJECT':    'Illustrative reconstruction of an object — not the original find',
    'DETAIL':    'Close detail — illustrative, not a find',
    # 'Modern landscape' was doing two incompatible jobs: it described the wide
    # establishing shots, and it also ended up on a modern hallway and a modern
    # suburban street. A landscape label over an interior is simply false, so
    # the class is split and the landscape wording retired.
    'LANDSCAPE': 'Modern landscape — atmosphere only',
    'MUSEUM':    'Modern museum gallery — not excavation in progress',
    'MODERN':    'Present-day scene — illustration, not archaeology',
}

# Section titles carry the number the *script* uses, which is the same as the
# map index here (unlike the rain episode, which skipped section 5).
SEC_TITLE = {s['section']: f"{int(s['section'])} · {s['title'].split(' · ')[-1]}"
             for s in M['sections']}

# Place cards: a site gets named once, and stays named while it is discussed.
PLACES = [
    (135.28, '03', 'Contrebandiers Cave · Atlantic Morocco · 120,000–90,000 years ago'),
    (214.92, None, None),
    (240.00, '04', 'Denisova Cave · Altai Mountains, Siberia · c. 50,000 years ago'),
    (268.99, None, None),
    (339.03, '06', 'Dzudzuana Cave · Caucasus, Georgia · c. 34,000 years ago'),
    (390.00, '06', 'Pavlov · Czech Republic · c. 26,000 years ago'),
    (416.75, None, None),
    (452.23, '08', 'Sunghir · near Vladimir, Russia · c. 34,000 years ago'),
    (521.95, None, None),
]
PLACE_HOLD = 3      # slots a place card stays up

# On-screen attribution wherever the voice makes a sourced claim.
SOURCES = [
    (109.4, 'Source · Toups et al., Mol. Biol. Evol. 2011'),
    (149.0, 'Source · Hallett et al., iScience 2021'),
    (269.0, 'Source · Gilligan et al., Sci. Adv. 2024'),
    (344.2, 'Source · Kvavadze et al., Science 2009'),
    (464.4, 'Source · Trinkaus & Buzhilova, Antiquity 2015'),
]
SRC_HOLD = 3


def wrap(dr, t, f, maxw):
    ls, c = [], ''
    for w in t.split():
        x = (c + ' ' + w).strip()
        if dr.textbbox((0, 0), x, font=f)[2] <= maxw:
            c = x
        else:
            if c:
                ls.append(c)
            c = w
    if c:
        ls.append(c)
    return ls


def card(ov, xy, text, font, pad=(14, 11), fill=(0, 0, 0, 105)):
    """Draws a rounded translucent card behind text, on its own layer."""
    c = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    dc = ImageDraw.Draw(c)
    tw = dc.textbbox((0, 0), text, font=font)[2]
    th = dc.textbbox((0, 0), text, font=font)[3]
    x, y = xy
    dc.rounded_rectangle([x, y, x + tw + pad[0] * 2, y + th + pad[1] * 2],
                         radius=8, fill=fill)
    dc.text((x + pad[0], y + pad[1] - 2), text, font=font, fill=(255, 255, 255, 245))
    ov.alpha_composite(c)


def place_at(t):
    cur = None
    for at, _sec, txt in PLACES:
        if t >= at - 0.02:
            cur = (at, txt)
    return cur


def source_at(t):
    cur = None
    for at, txt in SOURCES:
        if t >= at - 0.02:
            cur = (at, txt)
    return cur


def layer_for(r, i):
    ov = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    dr = ImageDraw.Draw(ov)
    # top and bottom scrims so type survives a bright plate
    # A hard-edged scrim shows as a seam across sky and cave walls, so both
    # are vertical gradients built as a 1 px column stretched to width.
    sc = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    top = Image.new('RGBA', (1, 120))
    for y in range(120):
        a = round(72 * (1 - y / 119) ** 1.4)
        top.putpixel((0, y), (0, 0, 0, a))
    sc.alpha_composite(top.resize((W, 120), Image.BILINEAR), (0, 0))
    bot = Image.new('RGBA', (1, 170))
    for y in range(170):
        a = round(88 * (y / 169) ** 1.6)
        bot.putpixel((0, y), (0, 0, 0, a))
    sc.alpha_composite(bot.resize((W, 170), Image.BILINEAR), (0, H - 170))
    ov.alpha_composite(sc)

    sec = r['section']
    prev = rows[i - 1] if i > 0 else None
    if prev is None or prev['section'] != sec:
        card(ov, (54, 118), SEC_TITLE[sec], FS, pad=(18, 12), fill=(0, 0, 0, 96))

    # place card: appears on the site's first slots only
    p = place_at(r['start'])
    if p and p[1]:
        run = sum(1 for x in rows[:i + 1] if place_at(x['start']) == p)
        if run <= PLACE_HOLD:
            card(ov, (54, 196), p[1], FM, pad=(12, 8), fill=(0, 0, 0, 100))

    # captions
    txt = r['sentence']
    ls = wrap(dr, txt, FM, 1060)
    lh = 34
    y = H - 58 - lh * len(ls)
    for ln in ls:
        ww = dr.textbbox((0, 0), ln, font=FM)[2]
        x = (W - ww) // 2
        dr.rounded_rectangle([x - 14, y - 5, x + ww + 14, y + 30], radius=6,
                             fill=(0, 0, 0, 122))
        dr.text((x, y), ln, font=FM, fill=(255, 255, 255, 247))
        y += lh

    # honesty label, always on
    cls = LABELS.get(str(r['still']), 'RECON')
    # the object caveat is the longest and the most important: give it 18 pt
    f = FOBJ if cls == 'OBJECT' else F
    card(ov, (30, 24), LABEL_TEXT[cls], f, pad=(11, 8), fill=(0, 0, 0, 110))

    # source card, top right
    s = source_at(r['start'])
    if s:
        run = sum(1 for x in rows[:i + 1] if source_at(x['start']) == s)
        if run <= SRC_HOLD:
            c = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            dc = ImageDraw.Draw(c)
            tw = dc.textbbox((0, 0), s[1], font=FSM)[2]
            x = W - 30 - tw - 16
            dc.rounded_rectangle([x, 26, W - 30, 58], radius=7, fill=(0, 0, 0, 120))
            dc.text((x + 8, 32), s[1], font=FSM, fill=(232, 232, 232, 245))
            ov.alpha_composite(c)
    return ov


def main():
    out = os.path.join(HERE, 'overlays')
    os.makedirs(out, exist_ok=True)
    for f in glob.glob(out + '/*.png'):
        os.remove(f)
    plan = []
    n = 0
    for i, r in enumerate(rows):
        layer = layer_for(r, i)
        # motion splits any slot longer than SLOT_MAX into equal segments: a
        # 3.9 s still on a 2 s cut reads as a freeze. The counter has to be a
        # plain variable. `f'{len(plan):04d}'` read len() *again* while
        # plan.append() was still evaluating its argument, so the stem was one
        # ahead of the slot it belonged to and the first slot of every pair
        # duplicated the previous one.
        dur = r['end'] - r['start']
        k = max(1, round(dur / 2.0))
        step = dur / k
        for j in range(k):
            stem = f'{n:04d}'
            layer.save(os.path.join(out, stem + '.png'))
            start = r['start'] + j * step
            end = r['start'] + (j + 1) * step if j < k - 1 else r['end']
            plan.append({'i': n, 'still': r['still'], 'stem': stem,
                         'start': round(start, 3), 'end': round(end, 3),
                         'section': r['section'], 'sentence': r['sentence'],
                         'sub': j})
            n += 1
    print(f'{len(plan)} type layers -> {out}')
    return plan


if __name__ == '__main__':
    # written last, after the files are on disk, so a crash can never leave a
    # plan pointing at layers that were never rendered
    p = main()
    json.dump(p, open(os.path.join(HERE, 'plan.json'), 'w'), indent=1)
