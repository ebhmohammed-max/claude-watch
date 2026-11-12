# Sleep episode — build notes, remaster

**Runtime** 11:22.36 · 1280×720 · 25 fps · H.264 High, re-encoded once at CRF 24
to carry the corner mark (SSIM 0.987, PSNR 38.3 dB against the V3 picture) ·
AAC-LC 160 k stereo @ 48 kHz · English captions, both a sidecar SRT and a muxed
mov_text track. 74,210,754 bytes. 17,059 frames, matching the plan exactly. Full
decode clean.

## What this build is

The previous three cuts (11m22s review draft, V2, V3) were all picture-and-
narration only. Every one of their reports says the same thing in a different
order: *no music, no sound effects, no mix; captions unverified; thumbnail and
upload kit outstanding*. This build closes those four items. It also fixes the
one thing that turned out to be worse than any of them: the picture was showing
reconstructions as though they were footage, and the gate was certifying it.

## What changed

1. **Sound.** The episode now has a bed, synthesised in `render/ambience.py` and
   mixed in numpy. Three environments, following the shot map's own Sound cue
   column: an interior room with sparse floor creaks, the outdoor night (wind,
   distant non-specific insects, subdued fire), and a quiet modern room under
   the study. Measured −16.7 LUFS integrated, LRA 4.7 LU. True peak reads −1.5 dBTP at
   mix time but −1.3 dBTP once AAC has been through it, which is the number
   that matters for delivery and is what this file claims.

2. **Captions.** `render/captions.py` regroups the 190-cue draft into 179 cues
   paced by clause. The draft broke mid-sentence 58 times and ran lines to 72
   characters; this has no cue over three lines of 44, no overlaps and no gaps,
   and ends 0.16 s before the runtime.

3. **Packaging.** New thumbnail from the 615 s cave-mouth frame, 1280×720 plus a
   320-wide preview; the upload kit is rewritten against the finished cut with
   ten chapters taken from the plan's section starts.

4. **Disclosure on every frame.** The V3 picture carries its own source cards,
   but only on part of the film. Sampled at 39 points, cards appeared only in
   the study (6:55-7:57) and on two Morocco shots; the ancient reconstruction --
   most of the episode -- and the modern opening and closing carried nothing.
   `render/labels.py` now burns a small top-right corner mark that runs
   continuously through each of the ten measured sections, so coverage is 100%
   by construction instead of by hope. It sits top-right: bottom-left was
   tried first and a three-line caption reached into the same corner, and the
   player decides how low captions sit, so the mark had to go where the
   captions cannot reach. Wording is about the image, never the
   archaeology: "Illustrative reconstruction", "Not the actual site", "Present
   day - illustrative reconstruction", "Illustrative graphic". The mark sits
   clear of the picture's own top-left cards and of the bottom-centre captions.

5. **A measured plan.** The gate needs to know where every image starts and
   ends. Rather than copy the edit notes, `render/picture-plan.json` measures the
   cut: a held still is a run of near-identical decoded frames, so the joins are
   visible in the pixels. 289 images, 25.4 per minute, median 2.28 s, longest
   8.72 s.

## Gate result

```
13 pass · 1 warn · 0 fail
```

The disclosure check is a new gate check, and it is measured rather than
trusted: it decodes the same instant from the source picture and from the
delivered file and compares the marked corner. If the corner is unchanged,
nothing was drawn there. On the old delivery it reports 34 of 34 samples
unlabelled; on this one, 0. Three earlier attempts at "does this look labelled"
-- brightness, bright-pixel count, corner flatness -- each mismeasured dark or
washed-out frames, which is why the check now has no heuristic in it at all.

The chapter check caught a real drift on the first pass: the kit listed
"Take away the lock" at 01:06 when the cut turns over at 67.5 s. Chapters now
match the section starts the plan records.

The warning is the four study graphics at 410.5 s, 439.7 s, 446.5 s and 470.4 s,
which sit 6.7-8.7 s each. That is the honest reading: the dark diagrams swap
between near-identical images and the edit does hold them. I left it as a
warning rather than splitting the plan to make it disappear.

## Four defects I introduced and caught

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
- **The labels were mostly missing.** `shots.json` claimed every still carried
  a label class, and the gate's label checks all read that claim. Nothing ever
  looked at the pixels. Measured on the frames, the mark was absent from the
  great majority of the run. That is the same trap as the two audio bugs -- a
  target mistaken for a measurement -- and the fix was to stop asking the plan
  what it did and start differencing the delivered file against its source.
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

## Rebuilding after a reset

The sandbox here is ephemeral and `/tmp` does not survive it. Two files that
matter are *not* in git, by design: `render/picture.mp4` (the V3 picture, 55 MB)
and `narration/master.wav` (the voice). A reset therefore takes the ability to
re-derive the bed, but it does not take the delivered audio: the accepted mix is
inside the delivered MP4, so restore it losslessly rather than re-synthesising:

```
ffmpeg -i "Sleep episode — final MP4 (11m22s, mixed).mp4" -map 0:a -c copy \
       production/sleep/narration/delivered-mix.m4a
python3 production/sleep/render/labels.py            # rebuilds the marked picture
ffmpeg -i render/picture-labelled.mp4 -i narration/delivered-mix.m4a \
       -i sleep-episode.srt -map 0:v -map 1:a -map 2:s -c:v copy -c:s mov_text \
       -movflags +faststart -t 682.36 kit/sleep-episode.mp4
```

The picture itself can be re-derived from the V3 review cut in Drive
(`Sleep episode — full review candidate V3.mp4`) with `-map 0:v -c copy`; its
video stream md5 is `f34612543eb0f12ef70bedeb19a8d482`, so you can prove you
restored the right picture before doing anything else.
