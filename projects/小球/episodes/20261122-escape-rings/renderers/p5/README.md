# p5.js candidate renderer

This renderer consumes the shared fixed-step trace and does not simulate motion. It draws each frame at the trace's exact dimensions, then encodes the PNG sequence with FFmpeg. The browser is headless and capture is frame-indexed, so export does not depend on wall-clock playback speed.

From this directory:

```sh
pnpm install
./node_modules/.bin/playwright install chromium
pnpm render
```

If a compatible local Chrome installation is already available, set `P5_CHROME_PATH` to its executable instead of downloading Playwright's Chromium.

Optional arguments override the default trace and output paths:

```sh
pnpm render ../../simulation/trace.json ../../video/candidates/escape-rings-p5-reversal.mp4
```

Expected trace convention: absolute canvas pixel coordinates with origin at the top left, ring center at `center`, ring angles and angular speeds in radians and radians per second, and one `states` entry for every rendered frame. `alive_ring_ids` controls which rings remain visible. `events` drive render-only fracture effects.
