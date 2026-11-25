import { createServer } from '../../../20261122-escape-rings/renderers/pixi/node_modules/vite/dist/node/index.js';
import { chromium } from '../../../20261122-escape-rings/renderers/pixi/node_modules/playwright/index.mjs';
import { spawn } from 'node:child_process';
import { mkdir, mkdtemp, readFile, rename, rm, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const episode = path.resolve(here, '../..');
const trace = JSON.parse(await readFile(path.join(episode, 'simulation/trace.json'), 'utf8'));
const audioPath = path.join(episode, 'audio/merge-escalation.wav');
const audioProbe = JSON.parse(await run('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'json', audioPath]));
const audioDuration = Number(audioProbe.format.duration);
const outputFrames = Math.ceil(audioDuration * trace.fps);
const faceMode = process.argv[2] || '';
if (faceMode && !['ears', 'round', 'character'].includes(faceMode)) throw new Error('Unknown face mode');
const output = path.join(episode, faceMode ? `video/final/cat-faces-${faceMode}.mp4` : 'video/candidates/ball-merging-preview.mp4');
await mkdir(path.dirname(output), { recursive: true });
const temp = await mkdtemp(path.join(path.dirname(output), '.ball-merge-render-'));
const framePattern = path.join(temp, 'frame_%05d.png');
const rendered = path.join(temp, 'preview.mp4');
let server, browser;
try {
  server = await createServer({ configFile: false, root: episode, logLevel: 'error', server: { host: '127.0.0.1', port: 0 } });
  await server.listen();
  const port = server.httpServer.address().port;
  browser = await chromium.launch({});
  const page = await browser.newPage({ viewport: { width: trace.width, height: trace.height }, deviceScaleFactor: 1 });
  await page.goto(`http://127.0.0.1:${port}/renderers/canvas/index.html?faces=${faceMode}`, { waitUntil: 'networkidle' });
  await page.waitForFunction(() => window.__traceReady === true);
  for (let frame = 0; frame < outputFrames; frame++) {
    const png = await page.evaluate((index) => {
      window.__drawFrame(index);
      return document.querySelector('#scene').toDataURL('image/png').split(',')[1];
    }, frame);
    await writeFile(framePattern.replace('%05d', String(frame).padStart(5, '0')), png, 'base64');
  }
  await run('ffmpeg', ['-hide_banner', '-loglevel', 'error', '-y', '-framerate', String(trace.fps), '-i', framePattern, '-i', audioPath, '-frames:v', String(outputFrames), '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', rendered]);
  const probe = JSON.parse(await run('ffprobe', ['-v', 'error', '-count_frames', '-show_entries', 'stream=codec_name,width,height,r_frame_rate,nb_read_frames,sample_rate,channels', '-show_entries', 'format=duration', '-of', 'json', rendered]));
  await rename(rendered, output);
  console.log(JSON.stringify({ output, probe }, null, 2));
} finally {
  await browser?.close();
  if (server) await server.close();
  await rm(temp, { recursive: true, force: true });
}

function run(command, args) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, { stdio: ['ignore', 'pipe', 'pipe'] });
    let stdout = '', stderr = '';
    child.stdout.setEncoding('utf8').on('data', (chunk) => { stdout += chunk; });
    child.stderr.setEncoding('utf8').on('data', (chunk) => { stderr += chunk; });
    child.on('error', reject);
    child.on('close', (code) => code === 0 ? resolve(stdout) : reject(new Error(`${command} exited ${code}: ${stderr}`)));
  });
}
