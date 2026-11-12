# Sleep episode — build notes, remaster

**Runtime** 11:22.36 · 1280×720 · 25 fps · H.264 High, CRF carried from the V3
picture · AAC-LC 160 k stereo @ 48 kHz · English captions, both a sidecar SRT
and a muxed mov_text track. 69,535,248 bytes. 17,059 frames, matching the plan
exactly. Full decode clean.

## What this build is

The previous three cuts (11m22s review draft, V2, V3) were all picture-and-
narration only. Every one of their reports says the same thing in a different
order: *no music, no sound effects, no mix; captions unverified; thumbnail and
upload kit outstanding*. This build closes those four items and does not touch
the picture.

## What changed

1. **Sound.** The episode now has a bed, synthesised in `render/ambience.py` and
   mixed in numpy. Three environments, following the shot map's own Sound cue
   column: an interior room with sparse floor creaks, the outdoor night (wind,
   distant non-specific insects, subdued fire), and a quiet modern room under
   the study. Measured −16.8 LUFS integrated, −1.5 dBTP, LRA 4.7 LU.

2. **Captions.** `render/captions.py` regroups the 190-cue draft into 179 cues
   paced by clause. The draft broke mid-sentence 58 times and ran lines to 72
   characters; this has no cue over three lines of 44, no overlaps and no gaps,
   and ends 0.16 s before the runtime.

3. **Packaging.** New thumbnail from the 615 s cave-mouth frame, 1280×720 plus a
   320-wide preview; the upload kit is rewritten against the finished cut with
   ten chapters taken from the plan's section starts.

4. **A measured plan.** The gate needs to know where every image starts and
   ends. Rather than copy the edit notes, `render/picture-plan.json` measures the
   cut: a held still is a run of near-identical decoded frames, so the joins are
   visible in the pixels. 289 images, 25.4 per minute, median 2.28 s, longest
   8.72 s.

## Gate result

```
12 pass · 1 warn · 0 fail
```

The chapter check caught a real drift on the first pass: the kit listed
"Take away the lock" at 01:06 when the cut turns over at 67.5 s. Chapters now
match the section starts the plan records.

The warning is the four study graphics at 410.5 s, 439.7 s, 446.5 s and 470.4 s,
which sit 6.7-8.7 s each. That is the honest reading: the dark diagrams swap
between near-identical images and the edit does hold them. I left it as a
warning rather than splitting the plan to make it disappear.

## Two defects I introduced and caught

- **The bed was silent for 173 s.** The first build used `np.maximum` over
  hard-edged windows and the ancient window never resumed after the study, so
  487.7 s to 661 s — the dawn, Morocco and the closing shelter — had no bed at
  all. A second attempt then left a 1.8 s hole at 660 s where two windows both
  faded to zero at once. Both are now continuous gain curves, and `build()`
  refuses to write a bed with any silent stretch.
- **The study room was 14 dB above the narration.** I mixed room tone at a 1:1
  multiplier with filtered wind, and room tone carries far more low-frequency
  energy per sample. Layer levels are now explicit constants set from
  measurement (`ROOM_DB`, `STUDY_DB`, `INSECT_DB`, `FIRE_DB`).
- **The fire was inaudible.** It measured 9 dB under the wind everywhere, so a
  section with a hearth and a section without one came out at the same spectral
  centroid (946 vs 913 Hz — i.e. indistinguishable). Gated to the firelight
  sections it now lifts them 3-4 dB and moves the centroid by ~125 Hz.

## What is still not done

- **The picture is untouched.** The door/lamp/bedroom continuity problem in the
  closing sequence, and the earlier shelter, clothing and crowd variance, are as
  they were. The prior notes call the door fix "a mitigation, not a verified
  continuity fix"; that remains true.
- **Nobody has watched or listened to it in full.** The gate checks structure.
  It cannot check whether a joke lands or whether the mix survives a phone
  speaker.
- **Captions are regrouped, not proofread by ear** against the audio.
- **No specialist review**, which the shot map's Read First sheet requires.
- **720p only**; the source stills are higher resolution than the cut uses.
