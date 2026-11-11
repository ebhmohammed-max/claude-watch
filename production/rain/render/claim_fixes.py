"""Re-route sentences whose claim is specific enough that a generic pool shot
misrepresents it.

The pool routing is keyword-based, so "microscopic starch traces on a grinding
stone" was landing on a fish plate simply because both sit in the food pool.
Where a sentence names an object, the shot has to show that object.

Each override is a list of shots cycled across the slots of the sentence. Only
shots verified to depict the named thing are used - 212 was rejected as a
moulded-concrete prop, so it is deliberately absent.
"""
import json, os, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
MAP = os.path.join(ROOT, 'production/rain/shot-map-sentence.json')

# (substring of the sentence, [shot, ...] in order of preference)
OVERRIDES = [
    # grinding / cereal processing: grain in a hollow stone, husks, standing wild cereal
    ("Microscopic starch traces on a grinding stone", [192, 211, 85]),
    ("The grinding stone and wild cereals", [192, 211, 85]),
    # grass bedding, plainly.
    # NB: the Border Cave sentence is deliberately NOT overridden. Putting a
    # generic grass macro under a headline claim about a real published find
    # would read as a photograph of that find. It keeps its cave shots.
    ("On an earlier floor, researchers identified grass bedding", [131]),
    ("Bedding may need to dry or be replaced", [22, 131]),
]


def main():
    m = json.load(open(MAP))
    shutil.copy(MAP, MAP + '.bak')
    slots = m['slots']
    slotidx = {s['slot']: i for i, s in enumerate(slots)}

    # group slots by sentence run so the cycle restarts per sentence
    changed = []
    for needle, picks in OVERRIDES:
        run = [s for s in slots if needle in s['sentence']]
        if not run:
            print(f"  !! no slots matched: {needle}")
            continue
        for k, s in enumerate(run):
            new = picks[k % len(picks)]
            if s['shot'] != new:
                changed.append((s['slot'], round(s['start'], 2), s['shot'], new, needle[:48]))
                s['shot'] = new
    for c in changed:
        print(f"  slot {c[0]:3d} @{c[1]:7.2f}  {c[2]:3d} -> {c[3]:3d}   {c[4]}")

    json.dump(m, open(MAP, 'w'), indent=1)
    print(f"{len(changed)} slots re-routed")


if __name__ == '__main__':
    main()
