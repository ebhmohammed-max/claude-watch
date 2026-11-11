"""Stitch the nine narration sections into one master and re-derive the map.

The sections are generated separately, so each file starts with a small
encoder delay. Concatenating the raw files carries that delay into every
section boundary and the picture drifts. So: trim the delay off each file,
measure what is actually left, and use those measured durations as the
authority for the slot grid. The map is rebuilt from the same numbers the
audio was built from, which is the only way captions and voice stay aligned.

    python voice.py            # writes narration/master.wav + durations.json
"""
import json, os, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
NAR = os.path.join(ROOT, 'production/tailors/narration')

FF = '/tmp/rd/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v9.0.2'
FFPROBE = FF.rsplit('ffmpeg', 1)[0] + 'ffprobe' if os.path.exists(
    FF.rsplit('ffmpeg', 1)[0] + 'ffprobe') else None

SECTIONS = [f'{k:02d}' for k in range(1, 10)]


def dur(path):
    out = subprocess.run([FF, '-hide_banner', '-i', path],
                         capture_output=True, text=True).stderr
    for line in out.splitlines():
        if 'Duration:' in line:
            h, m, s = line.split('Duration:')[1].split(',')[0].strip().split(':')
            return int(h) * 3600 + int(m) * 60 + float(s)
    raise RuntimeError(f'no duration for {path}')


def main():
    trimmed = []
    for sec in SECTIONS:
        src = os.path.join(NAR, f'{sec}.mp3')
        dst = os.path.join(NAR, f'{sec}.wav')
        # drop the leading encoder delay, then hold the measured length
        subprocess.run([FF, '-y', '-loglevel', 'error', '-i', src,
                        '-af', 'atrim=start=0.030,asetpts=PTS-STARTPTS',
                        '-ar', '44100', '-ac', '1', dst], check=True)
        trimmed.append(dst)

    durations = {sec: round(dur(p), 3) for sec, p in zip(SECTIONS, trimmed)}
    total = round(sum(durations.values()), 3)
    print('section durations:', json.dumps(durations))
    print(f'total {total:.3f} s = {int(total // 60)}:{total % 60:05.2f}')

    lst = os.path.join(NAR, 'concat.txt')
    with open(lst, 'w') as fh:
        for p in trimmed:
            fh.write(f"file '{p}'\n")
    master = os.path.join(NAR, 'master.wav')
    subprocess.run([FF, '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0',
                    '-i', lst, '-ar', '44100', '-ac', '1', master], check=True)
    got = dur(master)
    print(f'master {got:.3f} s  (drift {got - total:+.3f} s)')

    json.dump(durations, open(os.path.join(NAR, 'durations.json'), 'w'), indent=1)
    print('wrote narration/durations.json - rerun script_to_plan.py --audio with it')


if __name__ == '__main__':
    main()
