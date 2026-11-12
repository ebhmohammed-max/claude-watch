# Production

Episodes built for Atlas Understory. Each episode directory is self-contained
and rebuildable from what is committed here.

- `rain/` — "What Happened When It Rained for Days Before Houses?"
- `tailors/` — "What Did Ancient Humans Wear Before Tailors?"
- `sleep/` — "How Did Ancient Humans Sleep Without Locked Doors?"
  - this one is a **remaster**, not a rebuild: the picture is the existing
    11:22 cut, measured frame by frame rather than re-rendered. The work was
    the sound (it shipped narration-only three times), the captions, and the
    packaging. `render/build_plan.py` writes the gate's plan from the measured
    cut; `render/captions.py` regroups the draft SRT by clause;
    `render/ambience.py` builds the bed and mixes it.

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
| (sleep) a single cut threshold | the dark study graphics swap between near-identical images. Detected at 6.0 mean-diff they read as one 23.6 s hold; the two-threshold detector in `sleep/render/picture-plan.json` finds the four real cuts, and the longest true hold drops to 8.7 s |

The rain and tailors episodes fail the last check locally by design: the
delivered MP4 is gitignored (it lives in Drive), so only a full local rebuild
clears it. The sleep episode keeps a local copy during the build, so it passes
all twelve.

## Episodes and their gate results

| Episode | Result | Open warnings |
|---|---|---|
| tailors (v6, 9:35) | 14 pass · 3 warn · 0 fail | 10.2 s hold; Trinkaus card does not name its author on screen; 100.5 MB |
| rain | 8 pass · 0 warn · 1 fail | mp4 not local |
| sleep (11:22) | 12 pass · 1 warn · 0 fail | four study graphics held 6.7-8.7 s |

## ffmpeg and Pillow

The render scripts resolve ffmpeg at runtime — `$FFMPEG`, then `PATH`, then the
`imageio-ffmpeg` wheel. They used to hard-code a sandbox path, which broke the
entire rebuild when the sandbox was reset.
