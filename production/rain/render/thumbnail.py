"""Thumbnail v2 - built to earn the click.

The first version was honest but inert: no subject, no stakes, flat grey. This
one is built the way a thumbnail actually has to work at 320 px:

  * one big subject (lit shelter, backlit figure) instead of a wide landscape
  * a hard warm/cold split so it separates from a grey feed
  * a headline that poses a problem rather than describing the topic:
    "RAIN FOR 3 DAYS / NO HOUSE" - concrete, ancient, and it raises a question
  * the year, because "23,000 years ago" is the curiosity hook
  * the reconstruction label stays, small but present

Nothing here is dishonest: the scene is a labelled illustration, the claim in
the headline is exactly what the episode is about, and there is no fake arrow,
red circle, or shocked face.
"""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
KIT = os.path.join(ROOT, 'production/rain/kit')
W, H = 1280, 720
DEJA = '/usr/share/fonts/truetype/dejavu/'
SRC = os.path.join(KIT, 'base-a.jpg')

F_HUGE = ImageFont.truetype(DEJA + 'DejaVuSans-Bold.ttf', 104)
F_YEAR = ImageFont.truetype(DEJA + 'DejaVuSans-Bold.ttf', 34)
F_LAB = ImageFont.truetype(DEJA + 'DejaVuSans.ttf', 20)

AMBER = (255, 176, 60)
WHITE = (255, 255, 255)


def cover(im, w, h, fx=0.5, fy=0.5):
    s = max(w / im.width, h / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    x = int((im.width - w) * fx)
    y = int((im.height - h) * fy)
    return im.crop((x, y, x + w, y + h))


def shadow_text(d, xy, text, font, fill, sh=(0, 6), blur_passes=4):
    """Fake a soft drop shadow by stacking offset dark copies."""
    x, y = xy
    for i in range(blur_passes, 0, -1):
        a = int(70 / i)
        d.text((x + sh[0] * i / 2, y + sh[1] * i / 2), text, font=font, fill=(0, 0, 0, a))
    d.text((x, y), text, font=font, fill=fill)


def main():
    base = cover(Image.open(SRC).convert('RGB'), W, H, fx=0.5, fy=0.45)
    base = base.filter(ImageFilter.UnsharpMask(radius=2, percent=70, threshold=3))
    base = ImageEnhance.Color(base).enhance(1.12)
    base = ImageEnhance.Contrast(base).enhance(1.08)

    # scrim: darken the left third and the bottom so type reads on any feed
    scrim = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ds = ImageDraw.Draw(scrim)
    for x in range(W):
        t = max(0.0, 1 - x / (W * 0.62))
        ds.line([(x, 0), (x, H)], fill=(4, 7, 11, int(150 * t ** 1.4)))
    for y in range(H):
        t = max(0.0, (y - H * 0.45) / (H * 0.55))
        ds.line([(0, y), (W, y)], fill=(4, 7, 11, int(165 * t ** 1.5)))
    base = Image.alpha_composite(base.convert('RGBA'), scrim)

    txt = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(txt)

    # year eyebrow - the hook
    year = "23,000 YEARS AGO"
    yw = d.textbbox((0, 0), year, font=F_YEAR)[2]
    d.rounded_rectangle([48, 60, 74 + yw, 108], radius=6, fill=(0, 0, 0, 150))
    d.text((61, 68), year, font=F_YEAR, fill=AMBER)

    # headline
    # three lines, tightened so the last one is not clipped when YouTube shows
    # this at 320 px wide
    shadow_text(d, (56, 352), "RAIN FOR", F_HUGE, WHITE)
    shadow_text(d, (56, 452), "3 DAYS.", F_HUGE, WHITE)
    shadow_text(d, (56, 552), "NO HOUSE.", F_HUGE, AMBER)

    # honest label, top right
    lab = "Illustrative reconstruction"
    lw = d.textbbox((0, 0), lab, font=F_LAB)[2]
    d.rounded_rectangle([W - 66 - lw, 48, W - 40, 92], radius=6, fill=(0, 0, 0, 155))
    d.text((W - 57 - lw, 57), lab, font=F_LAB, fill=(230, 230, 230, 250))

    out = Image.alpha_composite(base, txt).convert('RGB')
    out.save(os.path.join(KIT, 'thumbnail-1280x720.jpg'), quality=93)
    out.resize((320, 180), Image.LANCZOS).save(
        os.path.join(KIT, 'thumbnail-preview-320.jpg'), quality=93)
    print('wrote thumbnail')


if __name__ == '__main__':
    main()
