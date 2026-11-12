"""Build the thumbnail from a frame of the episode itself.

The draft thumbnail labelled a campfire scene "SLEEP WITHOUT LOCKS?", which
summarises the video instead of posing the problem. The template the channel
already uses is a kicker line, a two or three line headline with one phrase in
orange, and a small reconstruction disclosure -- so this follows that template
rather than inventing a new look.

The frame is the cave mouth at dusk (615 s), because the whole episode is about
standing inside a shelter with no door to shut. It is a generated reconstruction
and the disclosure says so, in the same corner the clothing episode used.

Outputs 1280x720 plus a 320-wide preview, so legibility can be judged at the
size most people actually see it.
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
EP = os.path.dirname(HERE)
KIT = os.path.join(EP, 'kit')

WHITE = (255, 255, 255)
ORANGE = (240, 150, 40)
SHADOW = (0, 0, 0)
FONT_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
# When PIL writes a JPEG it cannot keep RGBA, so translucent plates in this
# script are composited before saving; TEXT_OPAQUE selects the readable variant.
TEXT_OPAQUE = True
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'


def load(path, size):
    return ImageFont.truetype(path, size)


def dim(img, box, strength=0.55):
    """Darken a region so type reads over it, without flattening the picture."""
    layer = Image.new('L', img.size, 0)
    d = ImageDraw.Draw(layer)
    d.rectangle(box, fill=int(255 * strength))
    layer = layer.filter(ImageFilter.GaussianBlur(60))
    black = Image.new('RGB', img.size, (0, 0, 0))
    return Image.composite(black, img, layer)


def text_with_shadow(draw, xy, text, font, fill, shadow_off=3):
    x, y = xy
    draw.text((x + shadow_off, y + shadow_off), text, font=font, fill=SHADOW)
    draw.text((x, y), text, font=font, fill=fill)


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'frame-615.png')
    if not os.path.exists(src):
        print(f'missing source frame: {src}')
        return 2
    img = Image.open(src).convert('RGB').resize((1280, 720), Image.LANCZOS)

    # Left half carries the type; the cave mouth stays visible on the right.
    img = dim(img, (-200, -200, 780, 900), strength=0.62)

    d = ImageDraw.Draw(img)

    kicker = load(FONT_BOLD, 34)
    head = load(FONT_BOLD, 82)
    small = load(FONT, 21)

    text_with_shadow(d, (64, 92), 'NO DOOR. NO LOCK. NO WALL.', kicker, ORANGE, 2)
    d.line([(66, 148), (66 + 470, 148)], fill=ORANGE, width=3)

    text_with_shadow(d, (62, 196), 'HOW DID THEY', head, WHITE)
    text_with_shadow(d, (62, 292), 'SLEEP AT NIGHT?', head, WHITE)
    text_with_shadow(d, (62, 400), '200,000 YEARS AGO', load(FONT_BOLD, 56), ORANGE, 2)

    # Disclosure, in the corner the channel already uses. It has to clear the
    # corner mark the picture now carries: the old position overlapped it and
    # the two sets of wording collided into unreadable mush at 320 px.
    note = 'Reconstruction, not a photograph of a site'
    w = d.textlength(note, font=small)
    ny = 52 if TEXT_OPAQUE else 22
    if TEXT_OPAQUE:
        d.rectangle([1280 - w - 34, ny - 6, 1280 - 12, ny + 20],
                    fill=(8, 10, 14, 190))
    d.text((1280 - w - 26, ny), note, font=small, fill=(240, 240, 240))

    out = os.path.join(KIT, 'thumbnail-1280x720.jpg')
    img.save(out, quality=92, optimize=True)

    prev = img.resize((320, 180), Image.LANCZOS)
    prev_out = os.path.join(KIT, 'thumbnail-preview-320.jpg')
    prev.save(prev_out, quality=92, optimize=True)

    print(f'wrote {out} ({os.path.getsize(out) / 1024:.0f} KB)')
    print(f'wrote {prev_out} ({os.path.getsize(prev_out) / 1024:.0f} KB)')
    return 0


if __name__ == '__main__':
    from PIL import ImageFilter  # noqa: E402  (only needed by dim())
    raise SystemExit(main())
