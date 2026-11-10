# Render pipeline

Rebuild the whole episode from the shot map:

```bash
python -m pip install --target /tmp/rain-deps pillow imageio-ffmpeg
export PYTHONPATH=/tmp/rain-deps

python production/rain/render/build_cues.py   # 112 cues + quiz window from the map
python production/rain/render/overlays.py     # 283 RGBA type layers -> render/overlays/
python production/rain/render/motion.py       # 283 clips -> render/clips/
```

Then concat and mux:

```bash
FF=$(python -c 'import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())')
$FF -f concat -safe 0 -i production/rain/render/clips.txt -c copy /tmp/mv.mp4
$FF -i /tmp/mv.mp4 -i "google_drive/Atlas Understory — Rain episode narration DRAFT.mp3" \
    -map 0:v -map 1:a -c:v libx264 -preset slow -crf 27 -pix_fmt yuv420p \
    -c:a aac -b:a 128k -ac 1 -movflags +faststart -t 554.652 out.mp4
```

Notes:
- Type is rendered once per slot as a transparent PNG and composited after the
  camera move, so captions never wobble or resample.
- Camera moves are deterministic (md5 of shot number) and capped at 7% zoom,
  because the source stills are 840x472.
- Google Drive rejects uploads over 100 MB; crf 27 lands this cut at ~85 MB.
- `render/clips/`, `render/work/` and the output MP4 are build artifacts.
