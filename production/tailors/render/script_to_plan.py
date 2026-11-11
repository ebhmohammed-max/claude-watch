"""Turn the narration script into an exact 2 s shot plan.

The rain episode's map was built from a voice track that already carried
per-sentence timings. This build generates narration in section-sized chunks,
so the only thing known for certain is where each *section* starts and ends.

So: sections get real audio durations, and sentences inside a section are
distributed by length. That is accurate to a few tenths of a second, which
matters because a caption is held for a whole slot - a 200 ms error inside a
section is invisible, but a section boundary that drifts by a second would put
the wrong caption over the wrong place card.

Usage:
    python script_to_plan.py            # writes script.json + plan.json (dry, estimated)
    python script_to_plan.py --audio durations.json
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SRC = os.path.join(ROOT, 'production/tailors/script.md')

SLOT = 2.0          # the 2 s cut the user chose
MIN_SLOT = 1.5      # below this a cut reads as a flash, not a shot
SNAP = 0.42         # pull a cut onto a sentence end if one is this close

# Fitted on the 112 real cues of the rain episode (mean abs residual 0.65 s):
# duration ~ pause + chars. Characters beat words as a predictor here (0.65 s
# vs 0.85 s), because long words are slower than short ones.
PAUSE = 0.047
PER_CHAR = 0.06159


def parse():
    """-> [{'section': '01', 'title': ..., 'sentences': [...]}]"""
    raw = open(SRC, encoding='utf-8').read()
    body = raw.split('---', 1)[1]
    parts = re.split(r'^## ', body, flags=re.M)[1:]
    out = []
    for k, p in enumerate(parts):
        lines = p.splitlines()
        title = lines[0].strip()
        text = ' '.join(l.strip() for l in lines[1:] if not l.startswith('---'))
        text = re.sub(r'\s+', ' ', text).strip()
        sents = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
        out.append({'section': f'{k+1:02d}', 'title': title, 'sentences': sents})
    return out


def weights(sents):
    return [PAUSE + PER_CHAR * len(s) for s in sents]


def estimate_section(sents):
    return sum(weights(sents))


def build(sections, durations):
    """durations: {'01': seconds, ...}. Missing sections fall back to estimate."""
    cues, slots = [], []
    t = 0.0
    for sec in sections:
        sents = sec['sentences']
        dur = durations.get(sec['section']) or estimate_section(sents)
        w = weights(sents)
        tot = sum(w)
        for s, ww in zip(sents, w):
            d = dur * ww / tot
            cues.append({'section': sec['section'], 'sentence': s,
                         'start': round(t, 3), 'end': round(t + d, 3)})
            t += d
    total = round(t, 3)

    # Build the cut grid globally, then snap it to cue boundaries.
    #
    # Subdividing each cue on its own leaves sub-second flashes whenever a
    # sentence is short ("Not a coat." is 0.7 s). A fixed 2 s grid never does
    # that, but it puts cuts mid-phrase. So: cut every 2 s, then pull each
    # boundary onto a nearby cue edge if one is within SNAP seconds, then merge
    # anything still too short into its neighbour.
    n = max(1, round(total / SLOT))
    bounds = [round(k * total / n, 3) for k in range(n + 1)]
    edges = [c['start'] for c in cues[1:]]
    snapped = [bounds[0]]
    for b in bounds[1:-1]:
        near = min(edges, key=lambda e: abs(e - b))
        snapped.append(near if abs(near - b) <= SNAP else b)
    snapped.append(bounds[-1])
    # drop duplicates and enforce ordering
    clean = [snapped[0]]
    for b in snapped[1:]:
        if b > clean[-1] + 0.05:
            clean.append(b)
    # merge any slot shorter than MIN_SLOT into the previous one
    merged = [clean[0]]
    for b in clean[1:-1]:
        if b - merged[-1] < MIN_SLOT:
            continue
        merged.append(b)
    if clean[-1] - merged[-1] < MIN_SLOT and len(merged) > 1:
        merged.pop()
    merged.append(clean[-1])

    for a, b in zip(merged, merged[1:]):
        mid = (a + b) / 2
        c = next((c for c in cues if c['start'] <= mid < c['end']), cues[-1])
        slots.append({'section': c['section'], 'sentence': c['sentence'],
                      'start': round(a, 3), 'end': round(b, 3)})
    return cues, slots, total


def main():
    durations = {}
    if '--audio' in sys.argv:
        durations = json.load(open(sys.argv[sys.argv.index('--audio') + 1]))
    sections = parse()
    cues, slots, total = build(sections, durations)
    words = sum(len(x.split()) for s in sections for x in s['sentences'])
    print(f"{len(sections)} sections · {len(cues)} cues · {len(slots)} slots · {total:.2f} s "
          f"({int(total//60)}:{total%60:05.2f})")
    print(f"{words} words -> {words/(total/60):.1f} wpm")
    for sec in sections:
        span = [c for c in cues if c['section'] == sec['section']]
        print(f"  {sec['section']}  {span[0]['start']:7.2f} - {span[-1]['end']:7.2f}  "
              f"{len(span):3d} cues  {sec['title'][:44]}")
    if '--write' in sys.argv:
        json.dump({'narration_seconds': total, 'slot': SLOT,
                   'sections': [{'section': s['section'], 'title': s['title'],
                                 'start': next(c['start'] for c in cues if c['section'] == s['section']),
                                 'end': [c['end'] for c in cues if c['section'] == s['section']][-1]}
                                for s in sections],
                   'cues': cues, 'slots': slots},
                  open(os.path.join(HERE, 'map.json'), 'w'), indent=1)
        print('wrote render/map.json')


if __name__ == '__main__':
    main()
