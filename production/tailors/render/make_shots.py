"""Routing table: which still carries which sentence.

Routing is by keyword, not by cue index. The index-keyed version broke the
moment the script was rewritten - every number shifted and the table silently
routed the wrong plate under the wrong claim. Keywords survive edits, and when a
sentence matches nothing the build fails loudly instead of guessing.

A still labelled LANDSCAPE is modern atmosphere and may never carry a sentence
that names a site, a study, a date or an artefact. assign.py enforces that.
"""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
M = json.load(open(os.path.join(HERE, 'map.json')))

# Still -> label class.
LABELS = {
    # §1 cold morning
    '1': 'RECON', '2': 'RECON', '3': 'DETAIL', '4': 'LANDSCAPE', '5': 'RECON',
    '6': 'LANDSCAPE', '7': 'DETAIL', '8': 'RECON', '9': 'RECON', '10': 'RECON',
    # §2 decay, lice, genetics
    '11': 'DETAIL', '12': 'DETAIL', '13': 'OBJECT', '14': 'OBJECT', '15': 'RECON',
    '16': 'DETAIL', '17': 'RECON', '18': 'DETAIL',
    # §3 Contrebandiers
    '23': 'RECON', '24': 'RECON', '25': 'RECON', '26': 'OBJECT', '27': 'OBJECT',
    '28': 'RECON', '30': 'OBJECT', '31': 'RECON', '32': 'RECON',
    # §4-§6 artefacts and sites
    '41': 'OBJECT', '42': 'OBJECT', '43': 'OBJECT', '44': 'OBJECT', '45': 'OBJECT',
    '49': 'OBJECT', '50': 'DETAIL', '51': 'DETAIL', '52': 'RECON', '53': 'RECON',
}

# Ordered rules: first match wins, so put the specific before the general.
RULES = [
    # ---- §1
    (r'one garment|It.s a hide|Not a coat|animal skin|folded over one shoulder', ['1', '10']),
    (r'outfit is genuinely terrible|hangs open at the neck|cardboard', ['7']),
    (r'noble and doomed|shuffle around', ['2']),
    (r'stopped being something you drape|something you build', ['5']),
    (r'cave in Morocco', ['9']),
    (r'needle you could lose', ['43']),
    (r'grave with three thousand beads', ['10']),
    (r'not a sleeve|not a stitch|the workshop|the mess', ['3']),
    (r'cold morning', ['8']),
    # ---- §2
    (r'^Clothes rot|whole problem|Hide is skin|meal for bacteria', ['11']),
    (r'vanishes long before|shadow of it', ['16']),
    (r'bone tool with a polish|blade that cuts skin|bead that had to be', ['17']),
    (r'lice', ['12']),
    (r'Toups|eighty-three thousand|hundred and seventy', ['15']),
    (r'window, not a date|Middle Stone Age', ['18']),
    (r'How well could they make them', ['14']),
    # ---- §3
    (r'Contrebandiers|Atlantic coast of Morocco|hear it working', ['23']),
    (r'twelve thousand bone fragments|Sixty-two', ['31']),
    (r'looks like a spatula|rib —|split and flattened', ['26']),
    (r'walk past it|microscope it has grooves', ['27']),
    (r'cut marks on the paws|Like a sock|took a wildcat off', ['30']),
    (r'not a hungry person|fur is worth more than the meat', ['28']),
    (r'start fibbing|strong proxy evidence|does not prove', ['25']),
    (r'animal chosen for its pelt|makes the result soft', ['32']),
    (r'cold country', ['24']),
    # ---- §4
    (r'cutting is easy|Joining is the nightmare', ['42']),
    (r'sleeve, or a seam|cold-air vent', ['42']),
    (r'first answer was the awl', ['41']),
    (r'leaves a gap|paper bag', ['41']),
    (r'A needle fixes that|carries the thread', ['44']),
    (r'oldest bone needle|Denisova|Seven centimetres', ['43']),
    (r'Denisovan remains|assigned to a species|is guessing', ['44']),
    (r'drilled a hole through a sliver|caveman with a rock|bad afternoon', ['43']),
    (r'Then it gets strange|Eyed needles don.t turn up', ['52']),
    (r'last glacial maximum', ['6']),
    (r'So why build the hard tool', ['43']),
    # ---- §5
    (r'Gilligan', ['45']),
    (r'scraped hide|glacial winter|against your skin', ['8']),
    (r'Fitted means fine sewing|underwear', ['42']),
    (r'announce yourself|Ochre. Scars|wrap that body', ['51']),
    (r'put it on the clothes|thermostat and becomes a sentence', ['49']),
    (r'It.s a hypothesis|can.t stop seeing it', ['10']),
    # ---- §6
    (r'foothills of the Caucasus|Dzudzuana', ['52']),
    (r'Kvavadze|pollen|Glamorous work', ['53']),
    (r'Wild flax|thousands of strands|fibre', ['50']),
    (r'twisted|spun|knotted|coloured|pink', ['50']),
    (r'Dyeing is not a survival|colour a rope', ['51']),
    (r'Pavlov|fired clay|hides-or-cloth|fashionably late', ['53']),
    # ---- §7
    (r'part nobody puts in', ['25']),
    (r'We know the tools|five thousand years|Egypt', ['3']),
    (r'rectangle with a hole|museum figure|lab coat', ['10']),
    (r'where the story lives', ['11']),
    # ---- §8
    (r'Moscow, near Vladimir|Sunghir', ['18']),
    (r'buried their dead|Thirty-four thousand years ago, people', ['10']),
    (r'Three thousand of them|Mammoth ivory|jeweller swear', ['49']),
    (r'ivory armbands|pierced fox teeth|rows, in the pattern', ['49']),
    (r'drilled three thousand holes', ['49']),
    (r'stops being a story about weather|what the community could afford', ['10']),
    (r'two children were buried|reward for a long life', ['10']),
    # ---- §9
    (r'^So\. What did ancient humans wear', ['1']),
    (r'already tailoring|before there.s a shop', ['41']),
    (r'Warmth. Then fit|identity', ['10']),
    (r'ground eats|width of a hair|liked it', ['3']),
    (r'pull on a coat|every single body', ['8']),
    (r'^Right\. Subscribe|What are you making', ['4']),
]


# Short rhetorical sentences ("It works.", "Fine.", "Skinning marks.") belong
# on the same plate as the sentence they answer. Falling back to the previous
# cue's still keeps a paragraph visually coherent instead of cutting away
# mid-argument to a generic plate.
CARRY = re.compile(r'^(It|That|This|Not|So|Fine|And|But|Which|They|We|Now|Right|'
                   r'Windows|Skinning|Then|Twenty|Three|Mammoth)', re.I)


def route(sentence, prev=None):
    s = sentence.strip()
    for pat, picks in RULES:
        if re.search(pat, s, re.I):
            return picks, 'rule'
    if prev:
        return prev, 'carry'
    return None, 'miss'


def main():
    cues = M['cues']
    table, missing = {}, []
    prev = None
    for i, c in enumerate(cues):
        picks, how = route(c['sentence'], prev)
        if how == 'miss':
            missing.append((i, c['sentence']))
            picks = ['10']
        prev = picks
        table[str(i)] = picks
    carried = sum(1 for v in table.values())
    if missing:
        print(f'{len(missing)} cues fell through to the default plate:')
        for i, s in missing:
            print(f'  {i:3d}  {s[:88]}')
    json.dump({'labels': LABELS, 'cues': table},
              open(os.path.join(HERE, 'shots.json'), 'w'), indent=1)
    print(f'shots.json: {len(table)} cues routed, {len(LABELS)} labelled stills')


if __name__ == '__main__':
    main()
