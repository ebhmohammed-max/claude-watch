# Clothing episode — visual shot register and generation plan

Episode: *What Did Ancient Humans Wear Before Tailors?*
Narration ~9:55 at 2 s cuts → **~300 placements**, **~120 distinct stills**.

All ancient scenes are AI-generated illustrative reconstructions. No image may
be presented as a photograph of a real find. Labels follow the same three
classes as the rain episode, plus one new one for this subject.

## Label classes

| Class | On-screen text | Use |
|---|---|---|
| `RECON` | Illustrative reconstruction — hypothetical scene | Any scene with people, shelters, or a site as it may have looked |
| `OBJECT` | Illustrative reconstruction of an object — not the original find | Any bone tool, needle, bead, or fibre plate |
| `LANDSCAPE` | Modern landscape — atmosphere only | Modern cave mouths, coasts, steppe, forest; weather |
| `DETAIL` | Close detail — illustrative, not a find | Macro plates: fibre, hide grain, polish, thread |

`OBJECT` is new. The rain episode only needed reconstruction vs modern vs detail,
but this episode is built around specific artefacts, and a viewer will read a
clean studio bone tool as the actual Denisova needle. Every artefact plate must
say it is a reconstruction of an object, in the same frame as the object.

## Failure modes to prompt against

Carried over from the rain build, plus clothing-specific ones seen in the
research imagery:

- **Posed humans fail.** Bare backs, modern-looking wraps, staged groups,
  mannequin posture. Use distant figures, hands only, rear silhouettes, shadows.
- **Modern tailoring reads instantly.** Zips, buttons, even stitches, lapels,
  seams pressed flat, symmetrical hems. Any of these kills the period read.
- **Tents and A-frames.** A hide over a frame is fine; a neat teepee is not.
- **Neat studio object shots** on white/grey backgrounds look like museum
  photography of a real specimen. Objects must sit in ground scatter, dust,
  a hand, or a cave floor.
- **Warm sunset grades** creep in and clash. This episode should sit in cold,
  desaturated light — overcast, cave dark, snow light.
- **Whole animal skinning** is visually grotesque. Imply it: pelt stretched,
  cut marks, fur side up. Never a flayed carcass.

## Shot budget by section

| § | Subject | Stills | Notes |
|---|---|---|---|
| 1 | Cold morning, one hide, modern contrast | 10 | Open on a hand holding a hide shut. No face. |
| 2 | Rot, decay, lice, genetics | 12 | Lice are hard to render well — prefer a single louse on a seam, macro, low light |
| 3 | Contrebandiers: coast, cave, scraper, pelts | 18 | Strongest visual section; give it the most shots |
| 4 | Awl vs needle, the hole, Denisova | 16 | The hero object sequence — needs the clearest OBJECT plates |
| 5 | Layers, cold, decoration moving to cloth | 14 | Multi-layer cross-section diagram + figures in snow |
| 6 | Dzudzuana: flax, spinning, dye, Pavlov | 18 | Fibre macro, dyed strands, clay impression |
| 7 | What we cannot know | 8 | Empty ground, trowel, unreadable fragment |
| 8 | Sunghir: beads, rows, ochre, children | 16 | Beads in rows is the money shot; also a bead-counting wide |
| 9 | The coat, today | 8 | Modern coat on a hook, cold light, no brand |

Total ~120 distinct stills. With 300 placements that is 2.5 placements per
still on average, which needs deliberate re-use: wide/medium/close framings of
the same scene, and repeat framings across a section's argument.

## Re-use strategy

Because 120 stills cannot cover 300 placements without visible repetition:

1. **Frame variants.** For ~30 key stills, generate one wide and crop three
   sub-framings at render time. Free placements, no new generation.
2. **Deliberate motifs.** The hide appears in §1, §5 and §9; the bead row in
   §5 and §8. Repeats read as callback if the framing differs.
3. **B-roll of ground and weather** carries transitions and the "we cannot
   know" section, where repetition is honest.

## Prompt skeleton

Reconstructions:
> Cold overcast light, desaturated palette, 35 mm documentary still. {scene}.
> Upper Palaeolithic / Middle Stone Age setting, {place}, {date}. No modern
> objects, no tailored seams, no visible fastenings, no text. Figures distant
> or partial, faces not visible.

Object plates:
> Museum-quality but natural context: {object} resting on {dust / cave floor /
> ground scatter}, raking light from one side, shallow depth of field, muted
> cold palette. Bone surface shows working marks and polish, not a clean
> modern finish. No scale bar, no label, no text, no white background.

## Still numbering (reserved)

| Range | Section |
|---|---|
| 001–010 | §1 cold morning |
| 011–022 | §2 decay, lice, genetics |
| 023–040 | §3 Contrebandiers |
| 041–056 | §4 awl, needle, Denisova |
| 057–070 | §5 layers, cold, decoration |
| 071–088 | §6 Dzudzuana, Pavlov |
| 089–096 | §7 limits |
| 097–112 | §8 Sunghir |
| 113–120 | §9 today |

Gaps of 2–3 in each range are held for retries, because the rain episode needed
roughly one replacement per eight generated stills.
