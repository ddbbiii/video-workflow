import {readFile} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const root = path.dirname(fileURLToPath(import.meta.url));
const tracePath = path.resolve(root, process.argv[2] ?? '../../simulation/trace.json');
const trace = JSON.parse(await readFile(tracePath, 'utf8'));
const states = trace.states;
const center = trace.center ?? {x: trace.width / 2, y: trace.height / 2};
const hits = trace.events.filter((event) => event.type === 'ring_hit');

function radial(state) {
  const dx = state.x - center.x;
  const dy = state.y - center.y;
  const radius = Math.hypot(dx, dy) || 1;
  return {radius, velocity: (state.vx * dx + state.vy * dy) / radius};
}

const checks = hits.map((event) => {
  const before = radial(states[Math.max(0, event.frame - 1)]);
  const at = radial(states[Math.min(states.length - 1, event.frame)]);
  const horizon = Math.min(states.length - 1, event.frame + 8);
  const after = Array.from({length: horizon - event.frame + 1}, (_, i) => radial(states[event.frame + i]));
  const reversed = before.velocity > 20 && after.some((sample) => sample.velocity < -20);
  const radiusDrop = after.some((sample) => sample.radius < at.radius - 1);
  return {
    ring_id: event.ring_id,
    frame: event.frame,
    before_radial: Number(before.velocity.toFixed(1)),
    at_radial: Number(at.velocity.toFixed(1)),
    min_after_radial: Number(Math.min(...after.map((sample) => sample.velocity)).toFixed(1)),
    radius_drop: radiusDrop,
    reversed,
  };
});

const failures = checks.filter((check) => !check.reversed || !check.radius_drop);
console.log(JSON.stringify({trace: tracePath, hit_count: checks.length, checks, reversal_passed: failures.length === 0, failures}, null, 2));
if (failures.length > 0) process.exitCode = 1;
