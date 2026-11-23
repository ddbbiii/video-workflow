import { createServer } from 'vite';
import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import { mkdir, mkdtemp, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { basename, dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = dirname(fileURLToPath(import.meta.url));
const tracePath = resolve(root, process.argv[2] ?? '../../simulation/trace.json');
const outputPath = resolve(root, process.argv[3] ?? '../../video/candidates/escape-rings-p5-reversal.mp4');
const trace = JSON.parse(await readFile(tracePath, 'utf8'));
if (!trace.states?.length || trace.states.length !== trace.duration_frames) {
  throw new Error('Trace must contain one state per output frame.');
}

const tempDir = await mkdtemp(join(tmpdir(), 'escape-rings-p5-'));
const framePattern = join(tempDir, 'frame_%05d.png');
let server;
let browser;
const startedAt = performance.now();

try {
  server = await createServer({
    configFile: false,
    root,
    logLevel: 'error',
    server: { host: '127.0.0.1', port: 0, strictPort: false },
  });
  await server.listen();
  const address = server.httpServer.address();
  const url = `http://127.0.0.1:${address.port}/`;
  browser = await chromium.launch({
    headless: true,
    ...(process.env.P5_CHROME_PATH ? { executablePath: process.env.P5_CHROME_PATH } : {}),
  });
  const page = await browser.newPage({
    viewport: { width: trace.width, height: trace.height },
    deviceScaleFactor: 1,
  });
  await page.route('**/trace.json', (route) => route.fulfill({ json: trace }));
  await page.goto(url, { waitUntil: 'networkidle' });
  await page.waitForFunction(() => window.__traceReady || window.__traceError, null, { timeout: 30000 });
  const traceError = await page.evaluate(() => window.__traceError ?? null);
  if (traceError) throw new Error(traceError);

  for (let frame = 0; frame < trace.duration_frames; frame++) {
    await page.evaluate((index) => window.__drawFrame(index), frame);
    await page.screenshot({ path: framePattern.replace('%05d', String(frame).padStart(5, '0')), type: 'png' });
    if (frame > 0 && frame % 150 === 0) process.stdout.write(`Rendered ${frame}/${trace.duration_frames}\n`);
  }

  await mkdir(dirname(outputPath), { recursive: true });
  await run('ffmpeg', [
    '-hide_banner', '-loglevel', 'error', '-y',
    '-framerate', String(trace.fps), '-i', framePattern,
    '-frames:v', String(trace.duration_frames),
    '-an', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18',
    '-pix_fmt', 'yuv420p', '-movflags', '+faststart', outputPath,
  ]);
  const probe = JSON.parse(await run('ffprobe', [
    '-v', 'error', '-count_frames', '-select_streams', 'v:0',
    '-show_entries', 'stream=codec_name,width,height,r_frame_rate,nb_read_frames',
    '-show_entries', 'format=duration', '-of', 'json', outputPath,
  ]));
  const stream = probe.streams?.[0];
  if (!stream || stream.codec_name !== 'h264' || stream.width !== trace.width || stream.height !== trace.height || Number(stream.nb_read_frames) !== trace.duration_frames) {
    throw new Error(`Output QA failed: ${JSON.stringify(probe)}`);
  }
  process.stdout.write(JSON.stringify({ output: outputPath, trace: tracePath, frames: trace.duration_frames, fps: trace.fps, duration_s: probe.format.duration, render_seconds: ((performance.now() - startedAt) / 1000).toFixed(2), probe }, null, 2) + '\n');
} finally {
  await browser?.close();
  if (server) await server.close();
  await rm(tempDir, { recursive: true, force: true });
}

function run(command, args) {
  return new Promise((resolvePromise, reject) => {
    const child = spawn(command, args, { stdio: ['ignore', 'pipe', 'pipe'] });
    let stdout = '';
    let stderr = '';
    child.stdout.setEncoding('utf8').on('data', (data) => { stdout += data; });
    child.stderr.setEncoding('utf8').on('data', (data) => { stderr += data; });
    child.on('error', reject);
    child.on('close', (code) => code === 0 ? resolvePromise(stdout) : reject(new Error(`${command} exited ${code}: ${stderr}`)));
  });
}
