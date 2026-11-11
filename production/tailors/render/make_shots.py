"""Routing table: which still carries which sentence.

Keyed by cue index into map.json. One still per cue unless the cue is long
enough to earn two placements; those list two shots and the second takes the
later slots.

Rule that this file exists to enforce: a still labelled LANDSCAPE is modern
atmosphere and may never sit under a sentence that names a site, a study, a
date or an artefact. assign.py fails the build if one does.
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
M = json.load(open(os.path.join(HERE, 'map.json')))
N = len(M['cues'])

# Still -> label class. OBJECT is new for this episode: a plate of a modelled
# artefact, which must never be read as a photograph of the real find.
LABELS = {
    # §1 cold morning
    '1': 'RECON', '2': 'RECON', '3': 'DETAIL', '5': 'RECON', '6': 'LANDSCAPE',
    '7': 'DETAIL', '8': 'RECON', '9': 'RECON', '10': 'RECON',
    # §2 decay, lice, genetics
    '4': 'LANDSCAPE', '6': 'LANDSCAPE', '11': 'DETAIL', '12': 'DETAIL', '13': 'OBJECT', '14': 'OBJECT', '15': 'RECON',
    '16': 'DETAIL', '17': 'RECON', '18': 'DETAIL',
    # §3 Contrebandiers
    '23': 'RECON', '24': 'RECON', '25': 'RECON', '26': 'OBJECT',
    '27': 'OBJECT', '28': 'RECON', '30': 'OBJECT', '31': 'LANDSCAPE', '32': 'RECON',
}

CUES = {
    # ---- 1 · A morning without buttons
    '0': ['8'], '1': ['1'], '2': ['1'], '3': ['1'],
    '4': ['10'], '5': ['2'], '6': ['7'], '7': ['5'], '8': ['5'],
    '9': ['4'], '10': ['9'], '11': ['7'], '12': ['10'],
    '13': ['3'], '14': ['3'],
    # ---- 2 · Why skin alone is not clothing
    '15': ['11'], '16': ['11'], '17': ['13'], '18': ['16'],
    '19': ['12'], '20': ['12'], '21': ['12'], '22': ['12'],
    '23': ['17'], '24': ['16'], '25': ['6'], '26': ['14'],
    '27': ['14'], '28': ['17'], '29': ['15'],
    # ---- 3 · A cave that smells of fur
    '30': ['23'], '31': ['15'], '32': ['31'], '33': ['26'],
    '34': ['26'], '35': ['27'], '36': ['28'], '37': ['28'],
    '38': ['30'], '39': ['30'], '40': ['32'], '41': ['32'],
    '42': ['25'], '43': ['25'], '44': ['25'],
    '45': ['23'], '46': ['23'],
    # ---- 4 · The hard part is the hole  (stills not shot yet)
    '47': ['24'], '48': ['24'], '49': ['32'], '50': ['32'], '51': ['32'],
    '52': ['27'], '53': ['27'], '54': ['27'], '55': ['27'],
    '56': ['27'], '57': ['32'], '58': ['31'], '59': ['31'], '60': ['31'],
    '61': ['31'], '62': ['32'], '63': ['32'], '64': ['32'], '65': ['32'],
    # ---- 5 · The layer against your skin
    '66': ['10'], '67': ['2'], '68': ['7'], '69': ['7'], '70': ['7'],
    '71': ['1'], '72': ['10'], '73': ['8'], '74': ['8'], '75': ['8'],
    '76': ['3'], '77': ['3'], '78': ['25'], '79': ['25'],
    # ---- 6 · A thread nobody was looking for
    '80': ['24'], '81': ['24'], '82': ['16'], '83': ['18'], '84': ['18'],
    '85': ['3'], '86': ['3'], '87': ['3'], '88': ['16'], '89': ['16'],
    '90': ['11'], '91': ['11'], '92': ['15'], '93': ['18'], '94': ['18'],
    '95': ['6'], '96': ['6'], '97': ['24'],
    # ---- 7 · What we cannot know
    '98': ['11'], '99': ['17'], '100': ['31'], '101': ['25'],
    '102': ['17'],
    # ---- 8 · Three thousand beads  (graves: abstract, no body)
    '103': ['25'], '104': ['25'], '105': ['10'], '106': ['10'],
    '107': ['10'], '108': ['3'], '109': ['3'], '110': ['3'],
    '111': ['10'], '112': ['10'], '113': ['18'], '114': ['18'], '115': ['18'],
    # ---- 9 · The first thing you put on
    '116': ['10'], '117': ['10'], '118': ['8'], '119': ['8'], '120': ['8'],
    '121': ['3'], '122': ['3'], '123': ['11'], '124': ['11'], '125': ['11'],
    '126': ['6'], '127': ['6'], '128': ['6'], '129': ['6'], '130': ['4'],
}


def build():
    cues = {str(i): [str(s) for s in v] for i, v in CUES.items()}
    missing = [i for i in range(N) if str(i) not in cues]
    if missing:
        raise SystemExit(f'routing missing cues: {missing}')
    spec = {'labels': LABELS, 'cues': cues}
    json.dump(spec, open(os.path.join(HERE, 'shots.json'), 'w'), indent=1)
    print(f'shots.json: {len(cues)} cues routed, {len(LABELS)} labelled stills')


if __name__ == '__main__':
    build()
