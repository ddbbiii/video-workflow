import { spawn } from 'node:child_process';
import { copyFile, mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';

const here = path.dirname(fileURLToPath(import.meta.url));
const episodeRoot = path.resolve(here, '../..');
const tracePath = path.join(episodeRoot, 'simulation/trace.json');
const outDir = path.join(here, 'output');
const framesDir = path.join(outDir, 'frames');
const videoPath = path.join(episodeRoot, 'video/candidates/escape-rings-pixi-reversal.mp4');
const trace = JSON.parse(await readFile(tracePath, 'utf8'));
const publicDir = path.join(here, 'public');
const baseUrl = 'http://127.0.0.1:5186';

await mkdir(outDir, { recursive: true });
await rm(framesDir, { recursive: true, force: true });
await mkdir(framesDir, { recursive: true });
await mkdir(publicDir, { recursive: true });
await copyFile(tracePath, path.join(publicDir, 'trace.json'));

const vite = spawn('pnpm', ['exec', 'vite', '--host', '127.0.0.1', '--port', '5186', '--strictPort'], {
  cwd: here,
  stdio: ['ignore', 'pipe', 'pipe'],
});
let viteOutput = '';
vite.stdout.on('data', (chunk) => { viteOutput += chunk.toString(); });
vite.stderr.on('data', (chunk) => { viteOutput += chunk.toString(); });

const waitForServer = async () => {
  const deadline = Date.now() + 30000;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(baseUrl);
      if (response.ok) return;
    } catch {}
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error(`Vite did not start. ${viteOutput}`);
};

let browser;
try {
  await waitForServer();
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  page.on('pageerror', (error) => { throw error; });
  await page.goto(`${baseUrl}/?frame=0`);
  await page.waitForFunction(() => document.documentElement.dataset.ready === 'true');

  const startedAt = Date.now();
  for (let frame = 0; frame < trace.duration_frames; frame += 1) {
    await page.evaluate((value) => window.drawFrame(value), frame);
    const buffer = await page.locator('#frame').screenshot({ type: 'png' });
    const filename = `frame-${String(frame).padStart(5, '0')}.png`;
    await writeFile(path.join(framesDir, filename), buffer);
    if ((frame + 1) % 100 === 0) process.stdout.write(`Rendered ${frame + 1}/${trace.duration_frames}\n`);
  }
  process.stdout.write(`Frame render seconds: ${((Date.now() - startedAt) / 1000).toFixed(2)}\n`);
} finally {
  if (browser) await browser.close();
  vite.kill('SIGTERM');
}

const ffmpeg = spawn('ffmpeg', [
  '-y', '-v', 'error', '-framerate', String(trace.fps), '-i', path.join(framesDir, 'frame-%05d.png'),
  '-frames:v', String(trace.duration_frames), '-an', '-c:v', 'libx264', '-crf', '18',
  '-pix_fmt', 'yuv420p', '-movflags', '+faststart', videoPath,
], { stdio: 'inherit' });
const code = await new Promise((resolve) => ffmpeg.on('close', resolve));
if (code !== 0) throw new Error(`ffmpeg exited with code ${code}`);
await rm(framesDir, { recursive: true, force: true });
process.stdout.write(`Wrote ${videoPath}\n`);
