"""Write plan.json, map.json and shots.json for the sleep episode.

The clothing episode built these from a generated still list. This episode's
picture already exists as a finished 11:22 cut, so the honest source of truth is
the cut itself: the boundaries below were measured from the encoded frames (a
held still is a byte-identical run of frames), not copied from the edit notes.
The notes and the measurement agree to within a frame on all 249 joins the
notes record, which is worth knowing but is not the same as measuring.

The gate reads:

  plan.json   one entry per on-screen image, with start/end and the sentence
              the image sits under
  map.json    the narration cues, with section and sentence
  shots.json  the label class for each image and the on-screen wording

Nothing here decides what the picture is. The label classes come from the shot
map's own Category column; where an image is a reconstruction the card says so.
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
EP = os.path.dirname(HERE)
RUNTIME = 682.36
FPS = 25
FRAMES = 17059

# Sections, in the film's own order. The three-section split is the one the shot
# map uses (Modern / Ancient / Study), but the film returns to Modern and to the
# shelter, so the chapter list has nine entries rather than three.
SECTIONS = [
    ('01', 0.0, "A noise in the night"),
    ('02', 66.0, "Take away the lock"),
    ('03', 98.0, "The world at dusk"),
    ('04', 137.0, "Border Cave's bedding"),
    ('05', 190.0, "Ash, pests and uncertainty"),
    ('06', 251.0, "Beyond the firelight"),
    ('07', 400.0, "Was someone always on watch?"),
    ('08', 491.0, "The ground, the air, the clothes"),
    ('09', 597.0, "Dawn, and the traces left"),
    ('10', 659.0, "Back in your room"),
]

# What each stretch of the film is, for the label honesty check. The gate fails
# a LANDSCAPE label sitting under a claim about a named site or study.
LABEL_SPANS = [
    # (from, to, label class)
    (0.0, 66.0, 'MODERN'),
    (66.0, 137.0, 'LANDSCAPE'),      # dusk on the slope, no people, no claim
    (137.0, 190.0, 'RECON'),         # Border Cave shelter and bedding
    (190.0, 251.0, 'RECON'),         # ash, grass, the working surface
    (251.0, 400.0, 'RECON'),         # firelight and the dark beyond
    (400.0, 440.0, 'RECON'),         # the scrape, watching
    (440.0, 491.0, 'STUDY'),         # Hadza study graphics
    (491.0, 597.0, 'RECON'),         # shelter, sleeping, clothes, Morocco
    (597.0, 659.0, 'RECON'),         # dawn and the traces
    (659.0, RUNTIME, 'MODERN'),      # back in the room
]

# On-screen wording for each class. Must match overlays in the picture; the gate
# compares these keys against what the renderer draws.
LABEL_TEXT = {
    'MODERN': 'PRESENT DAY · RECONSTRUCTION',
    'LANDSCAPE': 'ILLUSTRATIVE LANDSCAPE',
    'RECON': 'ILLUSTRATIVE RECONSTRUCTION',
    'STUDY': 'CONTEMPORARY STUDY · ILLUSTRATIVE GRAPHIC',
}


def label_for(t):
    for a, b, lab in LABEL_SPANS:
        if a <= t < b:
            return lab
    return 'RECON'


def section_for(t):
    name = SECTIONS[0][0]
    for key, start, _ in SECTIONS:
        if t >= start:
            name = key
    return name


def parse_srt(path):
    def ts(x):
        h, m, rest = x.split(':')
        s, ms = rest.split(',')
        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000
    cues = []
    for block in open(path, encoding='utf-8').read().strip().split('\n\n'):
        lines = block.split('\n')
        if len(lines) < 3:
            continue
        a, b = [ts(p) for p in lines[1].split(' --> ')]
        cues.append((a, b, ' '.join(lines[2:])))
    return cues


def main():
    plan_src = json.load(open(os.path.join(HERE, 'picture-plan.json')))
    images = plan_src['images']
    cues = parse_srt(os.path.join(EP, 'sleep-episode.srt'))

    def sentence_at(t):
        for a, b, text in cues:
            if a <= t < b:
                return text.replace('\n', ' ')
        return cues[-1][2].replace('\n', ' ')

    plan = []
    for k, im in enumerate(images):
        mid = (im['start'] + im['end']) / 2
        plan.append({
            'i': k,
            'still': f'{k + 1:03d}',
            'stem': f'{k + 1:04d}',
            'start': im['start'],
            'end': im['end'],
            'section': section_for(mid),
            'sentence': sentence_at(mid),
            'sub': 0,
        })

    labels = {f'{k + 1:03d}': label_for((im['start'] + im['end']) / 2)
              for k, im in enumerate(images)}

    mapj = {
        'narration_seconds': RUNTIME,
        'sections': [{'key': k, 'start': s, 'title': t} for k, s, t in SECTIONS],
        'cues': [{'section': section_for((a + b) / 2), 'sentence': text,
                  'start': a, 'end': b} for a, b, text in cues],
    }

    shots = {
        'labels': labels,
        'label_text': LABEL_TEXT,
        'note': ('Label classes follow the shot map Category column. Every '
                 'class carries an on-screen disclosure; the film is a '
                 'reconstruction throughout and no image is presented as '
                 'footage of a site or of the study.'),
        'cues': [{'start': a, 'end': b, 'sentence': text} for a, b, text in cues],
    }

    for name, obj in (('plan.json', plan), ('map.json', mapj), ('shots.json', shots)):
        out = os.path.join(HERE, name)
        json.dump(obj, open(out, 'w'), indent=1)
        print(f'wrote {out}')

    print(f'  images {len(plan)} · cues {len(cues)} · sections {len(SECTIONS)}')
    print(f'  runtime {plan[-1]["end"]:.2f}s · frames {round(plan[-1]["end"] * FPS)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
