# PixiJS candidate renderer

This renderer draws the canonical physics trace from `../../simulation/trace.json`. It does not simulate or modify motion.

## Run

```sh
pnpm install
./node_modules/.bin/playwright install chromium
pnpm render
```

The renderer snapshots each fixed frame in headless Chromium and encodes `../../video/candidates/escape-rings-pixi-reversal.mp4` with the system FFmpeg. It uses the trace's pixel coordinates, ring openings, ring visibility and impact/break events. Temporary frame images are removed after export. Output contains no text, audio or subtitle stream.

## Build check

```sh
pnpm exec vite build
```
