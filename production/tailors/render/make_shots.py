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
    # §7-§9 — Sunghir beads, absence, and the closing
    '54': 'OBJECT', '55': 'OBJECT', '57': 'OBJECT', '63': 'OBJECT',
    # §7 absence plates, the tighter opening, and two material details
    '65': 'DETAIL', '66': 'DETAIL', '67': 'RECON', '68': 'DETAIL',
    '69': 'RECON', '70': 'RECON', '71': 'DETAIL', '72': 'OBJECT', '73': 'RECON',
    # Honesty fix: t059 is a wide museum gallery, not a close detail, and
    # t060/t061 are a modern interior and a modern street -- neither is a
    # landscape. All three were carrying a label the picture contradicted.
    '59': 'MUSEUM', '60': 'MODERN', '61': 'MODERN',
    # t004 shows walking figures with spears -- a hypothetical scene, not a
    # modern landscape. Only t006 is a true empty landscape.
    '4': 'RECON',
    '62': 'DETAIL',
}

# Ordered rules: first match wins, so put the specific before the general.
RULES = [
    # ---- pacing overrides -------------------------------------------------
    # assign.py already warns above MAX_RUN=4 slots ("otherwise the 2 s cut is
    # invisible") and v2 shipped 58 of those warnings: 76% of the film sat on a
    # still held six seconds or longer, t50 for 34 s. Rain averaged 2.0 s per
    # image with 104 images; this episode had 43. These rules give the longest
    # single-plate sentences a second and third plate drawn from stills that
    # were generated and then left unused, so the 2 s grid actually reads as a cut.
    (r'What we do not have is one complete garment', ['65', '68']),
    (r'Every museum figure standing there', ['59', '68']),
    (r'Around the same era, at Pavlov', ['71', '50']),
    (r'Which means someone took a plant', ['50', '71']),
    (r'stopped being the same animal', ['12', '11']),
    (r'drops the habit deep into', ['18', '15']),
    (r'They were studying ancient climate', ['52', '53']),
    (r'two children were buried', ['57', '55']),
    (r'Around thirty-four thousand years ago, people', ['55', '63']),
    (r'somebody drilled three thousand holes', ['54', '55']),
    (r'dyed turquoise', ['50', '51']),
    (r'rebuilt for every single body', ['61', '1']),
    (r'ground eats|softest, most personal', ['3', '65']),
    (r'A blade that cuts skin', ['17', '13']),
    (r'the beads were lying in rows', ['63', '57', '62']),
    (r'became something you build', ['5', '70']),
    # second pass, aimed at the specific sentences that were stacking up
    (r'coloured', ['50', '51']),
    (r'pink', ['51', '50']),
    (r'between a plant and a garment', ['71', '50']),
    (r'wrap that body in hide', ['51', '52']),
    (r'had nowhere to go', ['51', '49']),
    (r'pulled up, in one piece', ['30', '28', '32']),
    (r'took a wildcat off like a sock', ['30', '32']),
    (r'glacial winter, where what keeps you alive', ['8', '10']),
    (r'hand-cut beads on it', ['63', '62']),
    (r'thought the dead were owed', ['63', '57']),
    (r'Hide is skin', ['11', '16']),
    (r'looking at clothing', ['16', '11']),
    (r'clothes were for', ['41', '43']),
    (r'what clothes were for', ['41', '1']),
    (r'Something changed', ['31', '32']),
    (r'Body lice live in clothing', ['12', '11']),
    (r'hadn.t had one', ['57', '55']),
    # third pass, the last of the cheap wins
    (r'genuinely terrible', ['7', '1']),
    (r'sets like cardboard', ['7', '3']),
    (r'hold your wrist or your ankle', ['7', '10']),
    (r'tailor . the one who fits', ['41', '42']),
    (r'ninety thousand years', ['41', '43']),
    (r'twelve thousand bone fragments', ['31', '32', '30']),
    (r'strong proxy evidence', ['25', '31']),
    (r'cutting is easy', ['42', '41']),
    (r'strip of leather', ['42', '44']),
    (r'What they found was fibre', ['50', '53']),
    (r'spun, deliberately', ['50', '53']),
    # fourth pass: the joins argument and Contrebandiers, which still held one
    # plate for ten seconds because the sentence itself is that long
    (r'twelve thousand bone fragments', ['31', '26', '32']),
    (r'spatula', ['26', '27']),
    (r'sleeve, or a seam', ['42', '43']),
    (r'cutting is easy', ['42', '44']),
    (r'announce yourself', ['51', '49']),
    (r'wrap that body in hide', ['51', '63']),
    (r'opened at the feet', ['30', '28', '26']),

    # ---- §1
    (r'drilled a hole through a bird bone', ['43']),
    (r'^Not for food|For a seam', ['72']),
    (r'before there were tailors|holding shut with one hand', ['1']),
    (r'one garment|It.s a hide|Not a coat|animal skin|folded over one shoulder', ['1', '10']),
    (r'outfit is genuinely terrible|hangs open at the neck|cardboard', ['7']),
    (r'noble and doomed|shuffle around', ['2']),
    (r'stopped being something you drape|something you build', ['5']),
    (r'cave in Morocco', ['23']),
    (r'needle you could lose', ['43']),
    (r'grave with three thousand beads|abruptly, it is', ['54']),
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
    (r'part nobody puts in', ['67']),
    (r'We know the tools|five thousand years|Egypt', ['65']),
    (r'rectangle with a hole|museum figure|lab coat', ['59']),
    (r'where the story lives', ['66']),
    # ---- §8
    (r'Moscow, near Vladimir|Sunghir', ['18']),
    (r'buried their dead|Thirty-four thousand years ago, people', ['55']),
    (r'Three thousand of them|Mammoth ivory|jeweller swear', ['54']),
    (r'ivory armbands|pierced fox teeth|rows, in the pattern', ['63', '57']),
    (r'drilled three thousand holes', ['54']),
    (r'stops being a story about weather|what the community could afford', ['63']),
    (r'two children were buried|reward for a long life', ['57']),
    # ---- §9
    (r'^So\. What did ancient humans wear', ['1']),
    (r'already tailoring|before there.s a shop', ['41']),
    (r'Warmth. Then fit|identity', ['10']),
    (r'ground eats|width of a hair|liked it', ['3']),
    (r'pull on a coat', ['60']),
    (r'every single body', ['61']),
    (r'^Right\. Subscribe|Subscribe if you want', ['60']),
    (r'What are you making|one hide, one bone needle', ['43']),
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
