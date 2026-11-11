"""Thumbnail for the clothing episode.

Built the way the rain thumbnail had to be after v1 was rejected as flat, but
with a different problem to solve. Rain had one obvious subject; this episode's
strongest object is a 7 cm needle, which is invisible at 320 px. So the subject
is a close crop of the stitched seam (t042) - two pieces of hide, a coarse
thread, and a very visible hole - and the headline does the rest.

Rules carried over:
  * one big subject, not a wide landscape
  * the headline poses a problem instead of describing the topic
  * a date, because the date is the curiosity hook
  * high contrast so it separates from a grey feed
  * the reconstruction label stays, small but legible
  * nothing dishonest: no red arrows, no shocked face, no fake evidence

The headline is deliberately a problem rather than a fact: "NO ZIP. NO BUTTON.
NO THREAD?" asks what you would actually do, which is the episode's question.
"""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
KIT = os.path.join(ROOT, 'production/tailors/kit')
os.makedirs(KIT, exist_ok=True)
W, H = 1280, 720
DEJA = '/usr/share/fonts/truetype/dejavu/'

SRC = os.path.join(ROOT, 'production/tailors/stills/t042.jpg')
ALT = os.path.join(ROOT, 'production/tailors/stills/t043.jpg')

F_HUGE = ImageFont.truetype(DEJA + 'DejaVuSans-Bold.ttf', 96)
F_BIG = ImageFont.truetype(DEJA + 'DejaVuSans-Bold.ttf', 76)
F_YEAR = ImageFont.truetype(DEJA + 'DejaVuSans-Bold.ttf', 32)
F_LAB = ImageFont.truetype(DEJA + 'DejaVuSans.ttf', 19)

AMBER = (255, 176, 60)
WHITE = (255, 255, 255)


def cover(im, w, h, fx=0.5, fy=0.5):
    s = max(w / im.width, h / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    x = int((im.width - w) * fx)
    y = int((im.height - h) * fy)
    return im.crop((x, y, x + w, y + h))


def shadow_text(d, xy, text, font, fill, layers=5):
    x, y = xy
    for i in range(layers, 0, -1):
        a = int(85 / i)
        d.text((x + i, y + i * 1.5), text, font=font, fill=(0, 0, 0, a))
    d.text((x, y), text, font=font, fill=fill)


def build(src, lines, out_name, fx=0.5, fy=0.5):
    im = Image.open(src).convert('RGB')
    im = cover(im, W, H, fx, fy)
    # grade: push contrast and cool the shadow end so the plate reads hard and
    # cold rather than soft and beige, which is what got v1 rejected
    im = im.filter(ImageFilter.UnsharpMask(radius=3, percent=85, threshold=2))
    px = im.load()
    im = im.point(lambda v: min(255, int((v - 128) * 1.22 + 118)))
    im = im.convert('RGB')

    # left-hand vignette so type has somewhere to live without a flat bar
    grad = Image.new('L', (W, 1))
    for x in range(W):
        grad.putpixel((x, 0), int(215 * max(0.0, 1 - x / (W * 0.72)) ** 1.25))
    shade = Image.new('RGB', (W, H), (6, 10, 14))
    im = Image.composite(shade, im, grad.resize((W, H), Image.BILINEAR))

    d = ImageDraw.Draw(im, 'RGBA')
    y = 176
    for i, (txt, font, col, size) in enumerate(lines):
        shadow_text(d, (54, y), txt, font, col)
        y += size

    d.text((56, 96), 'NO TAILOR. NO ZIP. NO BUTTON.', font=F_YEAR, fill=AMBER)
    d.line([(56, 140), (56 + 470, 140)], fill=(255, 176, 60, 150), width=3)

    lab = 'Reconstruction, not a photograph of a find'
    tw = d.textbbox((0, 0), lab, font=F_LAB)[2]
    d.rounded_rectangle([W - tw - 44, 24, W - 20, 60], radius=7, fill=(0, 0, 0, 130))
    d.text((W - tw - 32, 31), lab, font=F_LAB, fill=(228, 228, 228, 240))

    out = os.path.join(KIT, out_name)
    im.save(out, quality=93)
    prev = im.resize((320, 180), Image.LANCZOS)
    prev.save(os.path.join(KIT, out_name.replace('.jpg', '-preview-320.jpg')), quality=90)
    print('wrote', out)
    return out


if __name__ == '__main__':
    build(SRC,
          [('WHAT DID', F_BIG, WHITE, 92),
           ('THEY SEW', F_BIG, WHITE, 92),
           ('IT WITH?', F_BIG, AMBER, 92)],
          'thumbnail-1280x720.jpg', fx=0.42, fy=0.5)
