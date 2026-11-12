"""Rebuild the captions so they break where the voice breaks.

The V3 draft had 190 cues, 58 of them ending mid-sentence, because the cues were
cut on a time grid rather than on phrases -- "return to bed, and let the quiet" /
"settle." It also ran lines out to 72 characters. A viewer reads a caption, not
a grid.

This does not re-time the film. It takes the draft's word timing as given (the
draft is a forced-alignment estimate of the same raw narration) and regroups the
words into cues that follow the sentence:

  * pack whole clauses; a case is never split where a noun phrase is broken
  * a cue never opens on 'of', 'and', 'that' or ends on 'the', 'a'
  * up to 96 characters over at most two lines of 42
  * minimum 1.2 s on screen, maximum 9 s
  * contiguous: every cue starts where the last ended

The last two points are what the delivery gate checks, so the file that ships
is the file that was measured.
"""
import re
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
EP = os.path.dirname(HERE)
OUT = os.path.join(EP, 'sleep-episode.srt')
RUNTIME = 682.36

MAX_LINE = 44
MAX_LINES = 3
# A cue may run onto a third line rather than be cut mid-clause. Breaking
# "glimpse of a place / people returned to" is worse than one extra line.
CUE_BUDGET = MAX_LINE * MAX_LINES
MIN_CUE = 1.2
MAX_CUE = 9.0
MAX_CPS = 21.0

# Never end a cue on these. "Take away the quiet room, the mattress, the" is a
# worse subtitle than a slightly ragged line.
STOP_END = {
    'the', 'a', 'an', 'and', 'but', 'or', 'nor', 'of', 'to', 'in', 'on', 'at',
    'with', 'that', 'which', 'is', 'was', 'were', 'been', 'as', 'for', 'from',
    'by', 'so', 'if', 'than', 'then', 'when', 'while', 'into', 'over', 'under',
    'it', 'its', 'his', 'her', 'their', 'your', 'my', 'our', 'this', 'these',
    'those', 'he', 'she', 'they', 'we', 'you', 'i', 'not', 'no', 'up', 'out',
    'about', 'after', 'before', 'between', 'through', 'during', 'because',
    # a count owns the noun after it: 'over twenty / nights.' is unreadable
    'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine',
    'ten', 'eleven', 'twelve', 'fifteen', 'eighteen', 'twenty', 'thirty',
    'forty', 'fifty', 'hundred', 'thousand', 'million', 'dozen',
}

# And never start one with these: 'of thirty-three adults' belongs to the line
# before it, not the top of a new cue.
STOP_START = {
    'of', 'and', 'or', 'but', 'that', 'which', 'to', 'in', 'on', 'at', 'with',
    'from', 'by', 'as', 'than', 'into', 'over', 'under', 'for', 'is', 'was',
    'were', 'their', 'his', 'her', 'its',
}

TERMINAL = re.compile(r'[.!?…]$')
ABBREV = re.compile(r'^(Mr|Ms|Mrs|Dr|St|vs|No|etc)\.$')


def parse(path):
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
        text = ' '.join(l.strip() for l in lines[2:] if l.strip())
        cues.append((a, b, text))
    return cues


def words_of(cues):
    """Every word with the time the draft gave it.

    Words are spread evenly across each draft cue's span -- the same assumption
    the draft already made, so nothing is invented that the file did not assert.
    """
    out = []
    for a, b, text in cues:
        ws = text.split()
        if not ws:
            continue
        wd = (b - a) / len(ws)
        for k, w in enumerate(ws):
            out.append((w, a + k * wd, a + (k + 1) * wd))
    return out


def sentences(words):
    """Group words into sentences, keeping each word's own timing."""
    out, cur = [], []
    for w, t0, t1 in words:
        cur.append((w, t0, t1))
        if TERMINAL.search(w) and not ABBREV.match(w):
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def clause_split(sentence):
    """Split a sentence into clause groups at commas, colons and dashes.

    A clause is the unit a reader already hears as one breath. Packing whole
    clauses into cues is what stops breaks like "South African / site" and
    "estimate the sleep / of thirty-three", which a character budget produces
    happily because it has no idea what a noun phrase is.
    """
    groups, cur = [], []
    for w, t0, t1 in sentence:
        cur.append((w, t0, t1))
        if re.search(r'[,;:—–]$', w):
            groups.append(cur)
            cur = []
    if cur:
        groups.append(cur)
    return groups


def best_seam(ws, lo, hi):
    """Index in [lo, hi] where a long clause can best be broken."""
    best, best_score = None, -1e9
    for i in range(max(1, lo), min(hi, len(ws) - 1) + 1):
        prev, nxt = ws[i - 1][0], ws[i][0]
        score = 0.0
        if re.search(r'[,;:—–]$', prev):
            score += 100
        if prev not in STOP_END:
            score += 40
        if nxt in STOP_START:
            score -= 45
        score += len(' '.join(w[0] for w in ws[:i])) * 0.5
        if score > best_score:
            best, best_score = i, score
    return best if best is not None else hi


def wrap_lines(ws):
    """The greedy wrap, without printing -- used to test a cue's real height."""
    lines, cur = [], []
    for w in ws:
        if cur and len(' '.join(cur + [w])) > MAX_LINE:
            lines.append(' '.join(cur))
            cur = [w]
        else:
            cur.append(w)
    if cur:
        lines.append(' '.join(cur))
    return lines


def chunk(sentence):
    """Cut one sentence into cues, packing whole clauses first."""
    ws = list(sentence)
    # Test the sentence the way it will actually be drawn: a cue is only
    # acceptable if it fits MAX_LINES lines after wrapping, not merely if it
    # fits a character count.
    if len(wrap_lines([w[0] for w in ws])) <= MAX_LINES:
        return [ws]

    groups, cur = [], []
    for cl in clause_split(ws):
        if cur:
            joined = [w[0] for g in cur for w in g] + [w[0] for w in cl]
            if len(wrap_lines(joined)) > MAX_LINES:
                groups.append([w for g in cur for w in g])
                cur = []
        if len(wrap_lines([w[0] for w in cl])) > MAX_LINES:
            if cur:
                groups.append([w for g in cur for w in g])
                cur = []
            left = list(cl)
            while left:
                if len(wrap_lines([w[0] for w in left])) <= MAX_LINES:
                    groups.append(left)
                    break
                end = len(left)
                while end > 2 and len(wrap_lines([w[0] for w in left[:end]])) > MAX_LINES:
                    end -= 1
                seam = best_seam(left, end - 4, end)
                groups.append(left[:seam])
                left = left[seam:]
            continue
        cur.append(cl)
    if cur:
        groups.append([w for g in cur for w in g])
    return groups


def wrap(ws):
    """Greedy word-wrap at MAX_LINE, at most MAX_LINES lines.

    Any cue that exceeds MAX_LINES means chunk() let something through that it
    should have split, so say so rather than silently emit an unreadable block.
    """
    lines, cur = [], []
    for w in ws:
        if cur and len(' '.join(cur + [w])) > MAX_LINE:
            lines.append(' '.join(cur))
            cur = [w]
        else:
            cur.append(w)
    if cur:
        lines.append(' '.join(cur))
    if len(lines) > MAX_LINES:
        print(f'  WIDE CUE ({len(lines)} lines): {" ".join(ws)}', file=sys.stderr)
    return '\n'.join(lines)


def build(sents):
    """Turn sentences into contiguous cues."""
    cues = []
    for sent in sents:
        for grp in chunk(sent):
            cues.append([grp[0][1], grp[-1][2], grp])

    # stretch any cue too short to read into its neighbour's space
    for c in cues:
        c[1] = max(c[1], c[0] + MIN_CUE)
    cues[0][0] = 0.0
    for k in range(len(cues) - 1):
        # contiguous: this cue runs to the start of the next one. Where a short
        # cue was stretched, the earlier cue gives the time back.
        nxt = cues[k + 1]
        if cues[k][1] > nxt[0]:
            cues[k][1] = nxt[0] = max(cues[k][1], cues[k][0] + MIN_CUE)
        nxt[0] = cues[k][1]
    cues[-1][1] = max(cues[-1][1], RUNTIME - 0.16)
    return cues


def fmt(x):
    h = int(x // 3600)
    m = int((x % 3600) // 60)
    s = x % 60
    return f'{h:02d}:{m:02d}:{s:06.3f}'.replace('.', ',')


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    draft = parse(sys.argv[1])
    sents = sentences(words_of(draft))
    cues = build(sents)

    body = []
    for i, (a, b, grp) in enumerate(cues, 1):
        body.append(f'{i}\n{fmt(a)} --> {fmt(b)}\n{wrap([w[0] for w in grp])}\n')
    open(OUT, 'w', encoding='utf-8').write('\n'.join(body))

    overlap = sum(1 for i in range(len(cues) - 1) if cues[i][1] > cues[i + 1][0] + 1e-6)
    gap = sum(1 for i in range(len(cues) - 1) if cues[i + 1][0] - cues[i][1] > 1e-6)
    cps = [(i, round(len(' '.join(w[0] for w in g)) / (b - a), 1))
           for i, (a, b, g) in enumerate(cues, 1) if (b - a) > 0
           and len(' '.join(w[0] for w in g)) / (b - a) > MAX_CPS]
    long_cue = [(i, round(b - a, 2)) for i, (a, b, g) in enumerate(cues, 1)
                if b - a > MAX_CUE]
    lines = [len(wrap([w[0] for w in g]).split('\n')) for _, _, g in cues]

    print(f'draft cues {len(draft)} -> sentences {len(sents)} -> {len(cues)} cues')
    print(f'wrote {OUT}')
    print(f'  span {cues[0][0]:.2f} -> {cues[-1][1]:.2f}s '
          f'(runtime {RUNTIME:.2f})')
    print(f'  overlaps {overlap}  gaps {gap}  max lines {max(lines)}')
    print(f'  over {MAX_CPS:.0f} cps: {len(cps)} {cps[:6]}')
    print(f'  over {MAX_CUE:.0f}s: {len(long_cue)} {long_cue[:6]}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
