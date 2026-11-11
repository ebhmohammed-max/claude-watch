"""Assign a still to every slot, and refuse to render if the routing is unsafe.

The rain episode's hardest lesson was that a generic plate under a specific
claim reads as a photograph of that find. So routing is not automatic here:
`shots.json` says, per cue, which still carries that sentence, and this script
validates the result before anything is encoded.

Rules enforced:
  * every slot resolves to a still file that exists
  * every still used has a label class
  * a still labelled LANDSCAPE (modern, atmosphere only) may never sit under a
    cue that names a site, a study, a date or an artefact
  * an OBJECT plate may only appear where the sentence is about an artefact
  * no still runs longer than MAX_RUN consecutive slots without a framing
    change, otherwise the 2 s cut is invisible

Usage:
  python assign.py --check        # validate and report
  python assign.py --write        # write shotplan.json for overlays/motion
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
STILLS = os.path.join(ROOT, 'production/tailors/stills')
MAP = os.path.join(HERE, 'map.json')
SPEC = os.path.join(HERE, 'shots.json')

MAX_RUN = 4     # slots a single framing may hold

# Words that make a cue a *claim*: it needs a still that shows the thing.
CLAIM_WORDS = re.compile(
    r'\b(Contrebandiers|Morocco|Denisova|Siberia|Dzudzuana|Georgia|Pavlov|'
    r'Sunghir|Vladimir|Toulouse|Egypt|needle|scraper|bead|fibre|fiber|flax|'
    r'awl|hide|pelt|ivory|ochre|clothing lice|Toups|Hallett|Gilligan|'
    r'Kvavadze|Bar-Yosef|thirty-four|fifty thousand|hundred and twenty)\b', re.I)
RHETORICAL = re.compile(r'^(And tell us|Given|So: what|How |What if)', re.I)


def load():
    m = json.load(open(MAP))
    spec = json.load(open(SPEC))
    return m, spec


def main():
    m, spec = load()
    slots = m['slots']
    labels = spec['labels']
    assign = spec['cues']            # {"<cue index>": [still, ...]}
    cues = m['cues']
    problems, warnings = [], []

    # expand cue assignments across the slots that cue covers
    last = None
    used = set()
    plan = []
    for i, c in enumerate(cues):
        picks = assign.get(str(i))
        if not picks:
            problems.append(f'cue {i} has no still: {c["sentence"][:60]}')
            continue
        mine = [s for s in slots
                if s['start'] < c['end'] - 0.001 and s['end'] > c['start'] + 0.001]
        for k, s in enumerate(mine):
            still = picks[k % len(picks)]
            plan.append({'start': s['start'], 'end': s['end'], 'still': still,
                         'cue': i, 'section': s['section'], 'sentence': c['sentence'],
                         'variant': k // len(picks)})
            used.add(still)

    # validate
    for p in plan:
        f = os.path.join(STILLS, f't{int(p["still"]):03d}.jpg')
        if not os.path.exists(f):
            problems.append(f'missing still {p["still"]} for cue {p["cue"]}')
    for st in used:
        if str(st) not in labels:
            problems.append(f'still {st} has no label class')
    for p in plan:
        lab = labels.get(str(p['still']), '?')
        if lab == 'LANDSCAPE' and CLAIM_WORDS.search(p['sentence']) \
                and not RHETORICAL.search(p['sentence']):
            problems.append(
                f'still {p["still"]} (LANDSCAPE) under a claim: {p["sentence"][:70]}')
        if lab == 'OBJECT' and not CLAIM_WORDS.search(p['sentence']):
            warnings.append(
                f'still {p["still"]} (OBJECT) under a non-artefact sentence: '
                f'{p["sentence"][:60]}')
    # run length
    run = 1
    for a, b in zip(plan, plan[1:]):
        run = run + 1 if a['still'] == b['still'] and a['variant'] == b['variant'] else 1
        if run > MAX_RUN:
            warnings.append(f'still {b["still"]} holds for {run} slots at {b["start"]:.1f}s')

    print(f'{len(plan)} slots · {len(used)} stills used · '
          f'{len(problems)} problems · {len(warnings)} warnings')
    for p in problems[:40]:
        print('  PROBLEM', p)
    for w in warnings[:20]:
        print('  warn   ', w)
    if '--write' in sys.argv and not problems:
        json.dump(plan, open(os.path.join(HERE, 'shotplan.json'), 'w'), indent=1)
        print('wrote render/shotplan.json')
    if problems:
        sys.exit(1)


if __name__ == '__main__':
    main()
