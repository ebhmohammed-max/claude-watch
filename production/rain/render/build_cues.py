"""Build caption cues + quiz window from the sentence-aligned shot map."""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
m = json.load(open(os.path.join(ROOT, 'production/rain/shot-map-sentence.json')))
slots = m['slots']

cues = []
for s in slots:
    if cues and cues[-1]['text'] == s['sentence'] and abs(cues[-1]['end'] - s['start']) < 0.02:
        cues[-1]['end'] = s['end']
    else:
        cues.append({'start': s['start'], 'end': s['end'],
                     'text': s['sentence'], 'sec': s['section']})

# quiz: the "Elsewhere, natural rock shelters…" line, up to the Border Cave line
qz = [s for s in slots if s['sentence'].startswith('Elsewhere, natural rock shelters')]
quiz = {'start': qz[0]['start'], 'end': qz[-1]['end']} if qz else None

json.dump(cues, open(os.path.join(HERE, 'cues.json'), 'w'))
json.dump(quiz, open(os.path.join(HERE, 'quiz_window.json'), 'w'))
print(f"{len(cues)} cues, {cues[-1]['end']:.3f} s; quiz {quiz}")
