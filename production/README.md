# Production

Episodes built for Atlas Understory. Each episode directory is self-contained
and rebuildable from what is committed here.

- `rain/` — "What Happened When It Rained for Days Before Houses?"
- `tailors/` — "What Did Ancient Humans Wear Before Tailors?"

## Before calling an episode delivered

```
python3 production/qc.py production/<episode>
```

Exit code 0 means nothing failed; warnings are judgement calls. The gate exists
because every check in it is a defect that shipped at least once first:

| Check | What it caught |
|---|---|
| no image held absurdly long | 76% of one cut sat on stills held over 6 s; one held 34 s |
| images per minute | the same cut ran 4.5 images/min against rain's 11.3 |
| label class under a claim | a modern hallway, a modern street and a scene with people all labelled "modern landscape" |
| every label class has wording | a retired class left `overlays.py` raising KeyError mid-render |
| source card inside its cue | a study credited 10 s after the voice named it |
| caption overlaps and gaps | cues drifting out of step with the narration |
| chapter times | chapters listed against a previous cut's timing |
| mp4 frame count matches plan | a rebuild reusing stale clips by duration |
| no clip older than its overlay | re-timed overlays with unchanged durations, so motion.py reused every old clip |

Both episodes fail the last check locally by design: the delivered MP4 is
gitignored (it lives in Drive), so only a full local rebuild clears it.

## ffmpeg and Pillow

The render scripts resolve ffmpeg at runtime — `$FFMPEG`, then `PATH`, then the
`imageio-ffmpeg` wheel. They used to hard-code a sandbox path, which broke the
entire rebuild when the sandbox was reset.
