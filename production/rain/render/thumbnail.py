"""Build the YouTube thumbnail (1280x720) from a frame of the episode.

Rules it follows:
  * legible at 320 px wide - YouTube shows thumbnails tiny in most feeds, so
    the type is huge and limited to four words
  * the reconstruction label stays on the image even here; a clickable image of
    a prehistoric camp with no qualifier is the one thing this series must not
    publish
  * no clickbait, no arrows, no red circles
"""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
OUT = os.path.join(ROOT, 'production/rain/kit')
W, H = 1280, 720
DEJA = '/usr/share/fonts/truetype/dejavu/'

BG = os.path.join(ROOT, 'production/rain/visuals-3d/real-164-smoke-over-camp-distant.jpg')
FBIG = ImageFont.truetype(DEJA + 'DejaVuSans-Bold.ttf', 104)
FSER = ImageFont.truetype(DEJA + 'DejaVuSans-Bold.ttf', 30)
FSM = ImageFont.truetype(DEJA + 'DejaVuSans.ttf', 20)


def cover(im, w, h):
    s = max(w / im.width, h / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    x = (im.width - w) // 2
    y = (im.height - h) // 2
    return im.crop((x, y, x + w, y + h))


def main():
    os.makedirs(OUT, exist_ok=True)
    base = cover(Image.open(BG).convert('RGB'), W, H)

    # lift contrast and cool the shadows slightly; thumbnails need punch
    base = base.filter(ImageFilter.UnsharpMask(radius=3, percent=90, threshold=2))

    # darken the lower half so type sits on it
    shade = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ds = ImageDraw.Draw(shade)
    for y in range(H):
        t = max(0.0, (y - H * 0.34) / (H * 0.66))
        ds.line([(0, y), (W, y)], fill=(6, 10, 14, int(200 * t ** 1.25)))
    base = Image.alpha_composite(base.convert('RGBA'), shade)

    txt = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(txt)

    # headline, two lines, 4 words total
    d.text((60, 440), "RAIN FOR", font=FBIG, fill=(255, 255, 255, 255))
    d.text((60, 552), "THREE DAYS", font=FBIG, fill=(255, 255, 255, 255))

    # Brand top-left, honest qualifier top-right. The eyebrow used to sit just
    # above the headline, but at 320 px wide it merged into it and read as mud.
    brand = "ATLAS UNDERSTORY"
    bw = d.textbbox((0, 0), brand, font=FSER)[2]
    d.rounded_rectangle([40, 36, 62 + bw, 86], radius=6, fill=(0, 0, 0, 130))
    d.text((51, 47), brand, font=FSER, fill=(150, 195, 225, 255))

    lab = "Illustrative reconstruction"
    lw = d.textbbox((0, 0), lab, font=FSM)[2]
    d.rounded_rectangle([W - 62 - lw, 44, W - 44, 82], radius=6, fill=(0, 0, 0, 130))
    d.text((W - 53 - lw, 52), lab, font=FSM, fill=(226, 226, 226, 245))
    base = Image.alpha_composite(base, txt)

    base.convert('RGB').save(os.path.join(OUT, 'thumbnail-1280x720.jpg'), quality=92)
    # YouTube also wants something that survives the tiny mobile crop
    base.convert('RGB').resize((320, 180), Image.LANCZOS).save(
        os.path.join(OUT, 'thumbnail-preview-320.jpg'), quality=92)
    print("wrote thumbnail")


if __name__ == '__main__':
    main()
