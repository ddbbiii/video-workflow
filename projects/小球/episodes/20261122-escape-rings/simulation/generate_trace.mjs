import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import Matter from 'matter-js';

const { Bodies, Body, Composite, Engine, Events } = Matter;
const here = path.dirname(fileURLToPath(import.meta.url));
const output = path.join(here, 'trace.json');
const width = 1080, height = 1920, fps = 30;
const durationSeconds = 12, durationFrames = durationSeconds * fps;
const center = { x: width / 2, y: height / 2 };
const ballRadius = 26, physicsFps = 240, matterVelocityFps = 60, physicsStepMs = 1000 / physicsFps;
const segmentCount = 180;
const colors = ['#36d6c4', '#ffc45c', '#ff6f76', '#7f9cff'];
const ringDefs = Array.from({ length: 10 }, (_, i) => ({
  id: i + 1, radius: 48 + i * 43.5, thickness: 12, gap_width: 0,
  gap_angle: [0.18, 1.52, 2.74, 4.31, 5.58, 0.91, 2.16, 3.77, 4.91, 0.43][i],
  rotate_speed: [0.11, -0.09, 0.08, -0.07, 0.06, -0.05, 0.045, -0.04, 0.035, -0.03][i],
  color: colors[i % colors.length],
}));

function angleDifference(a, b) { return Math.atan2(Math.sin(a - b), Math.cos(a - b)); }
function clamp(n, lo, hi) { return Math.max(lo, Math.min(hi, n)); }

function buildRing(engine, ring) {
  const step = Math.PI * 2 / segmentCount;
  const length = ring.radius * step * 1.16;
  const bodies = [];
  for (let i = 0; i < segmentCount; i++) {
    const angle = i * step;
    if (Math.abs(angleDifference(angle, ring.gap_angle)) < ring.gap_width / 2) continue;
    const mid = angle + step / 2;
    const segment = Bodies.rectangle(
      center.x + Math.cos(mid) * ring.radius,
      center.y + Math.sin(mid) * ring.radius,
      length, ring.thickness,
      { isStatic: true, restitution: 0.94, friction: 0, frictionStatic: 0, label: `ring-${ring.id}`, angle: mid + Math.PI / 2 },
    );
    segment.plugin.ringId = ring.id;
    bodies.push(segment);
  }
  Composite.add(engine.world, bodies);
  return bodies;
}

function run(seed) {
  const engine = Engine.create({ enableSleeping: false });
  engine.gravity.scale = 0;
  engine.positionIterations = 10;
  engine.velocityIterations = 10;
  const ball = Bodies.circle(center.x + 12, center.y - 18, ballRadius, {
    label: 'ball', restitution: 0.98, friction: 0, frictionAir: 0.00001, density: 0.008,
  });
  Body.setPosition(ball, { x: center.x + 4, y: center.y - 7 });
  Body.setVelocity(ball, { x: 600 / matterVelocityFps, y: 171 / matterVelocityFps });
  Composite.add(engine.world, ball);

  const byRing = new Map();
  const alive = new Set(ringDefs.map((r) => r.id));
  for (const ring of ringDefs) byRing.set(ring.id, buildRing(engine, ring));
  const events = [], states = [];
  let pending = new Map(), renderedFrame = 0;
  let velocityBeforeStep = { x: ball.velocity.x, y: ball.velocity.y };
  let escapedSlowdownStarted = false;

  Events.on(engine, 'collisionStart', ({ pairs }) => {
    for (const { bodyA, bodyB } of pairs) {
      const ringId = bodyA.label === 'ball' ? bodyB.plugin.ringId : bodyB.label === 'ball' ? bodyA.plugin.ringId : null;
      if (!ringId || !alive.has(ringId) || pending.has(ringId)) continue;
      pending.set(ringId, {
        x: ball.position.x,
        y: ball.position.y,
        speed: Math.hypot(velocityBeforeStep.x, velocityBeforeStep.y) * matterVelocityFps,
        velocityBefore: { ...velocityBeforeStep },
      });
    }
  });

  for (let physicsFrame = 0; renderedFrame < durationFrames; physicsFrame++) {
    velocityBeforeStep = { x: ball.velocity.x, y: ball.velocity.y };
    Engine.update(engine, physicsStepMs);
    const radialDistance = Math.hypot(ball.position.x - center.x, ball.position.y - center.y);
    if (alive.size === 0 && radialDistance > ringDefs.at(-1).radius + ballRadius) {
      const damping = escapedSlowdownStarted ? 0.96 : 0.3;
      escapedSlowdownStarted = true;
      Body.setVelocity(ball, { x: ball.velocity.x * damping, y: ball.velocity.y * damping });
    }
    const hits = [...pending.entries()].sort(([a], [b]) => a - b);
    pending = new Map();
    for (const [ringId, hit] of hits) {
        if (!alive.has(ringId)) continue;
        const velocityBefore = hit.velocityBefore;
        const dx = hit.x - center.x, dy = hit.y - center.y;
        const distance = Math.max(1, Math.hypot(dx, dy));
        const n = { x: dx / distance, y: dy / distance };
        const impulse = clamp(hit.speed / 520, 0.18, 1);
        const incoming = velocityBefore.x * n.x + velocityBefore.y * n.y;
        // A first touch breaks the ring and reflects the ball at that same contact.
        const reflected = incoming > 0 ? {
          x: velocityBefore.x - 2 * incoming * n.x * 0.98,
          y: velocityBefore.y - 2 * incoming * n.y * 0.98,
        } : { ...velocityBefore };
        Body.setVelocity(ball, reflected);
        // Schedule the impact on the next rendered sample, which contains the reflected state.
        const frame = renderedFrame;
        events.push({ frame, type: 'ring_hit', ring_id: ringId, x: hit.x, y: hit.y, impulse, damage: 1, color: ringDefs[ringId - 1].color,
          radial_velocity_before: incoming * matterVelocityFps, radial_velocity_after: (reflected.x * n.x + reflected.y * n.y) * matterVelocityFps,
          velocity_before: { x: velocityBefore.x * matterVelocityFps, y: velocityBefore.y * matterVelocityFps },
          velocity_after: { x: reflected.x * matterVelocityFps, y: reflected.y * matterVelocityFps },
          velocity_reversal_dot: (velocityBefore.x * reflected.x + velocityBefore.y * reflected.y) * matterVelocityFps * matterVelocityFps,
          reversed: incoming > 0 && reflected.x * n.x + reflected.y * n.y < 0,
        });
        alive.delete(ringId);
        for (const part of byRing.get(ringId)) Composite.remove(engine.world, part, true);
        events.push({ frame, type: 'ring_break', ring_id: ringId, x: hit.x, y: hit.y, impulse, damage: 1, color: ringDefs[ringId - 1].color });
    }

    if (physicsFrame % (physicsFps / fps) !== 0 && physicsFrame !== 0) continue;
    const speed = Math.hypot(ball.velocity.x, ball.velocity.y) * matterVelocityFps;
    states.push({
      frame: renderedFrame, x: ball.position.x, y: ball.position.y, angle: ball.angle,
      vx: ball.velocity.x * matterVelocityFps, vy: ball.velocity.y * matterVelocityFps, speed,
      alive_ring_ids: ringDefs.map((ring) => ring.id)
        .filter((id) => alive.has(id))
        .sort((a, b) => a - b),
    });
    renderedFrame++;
  }
  const brokenIds = events.filter((e) => e.type === 'ring_break').map((e) => e.ring_id);
  const hits = events.filter((e) => e.type === 'ring_hit');
  const reversalPass = hits.length === ringDefs.length && hits.every((event) => {
    const before = states[event.frame - 1];
    const atImpact = states[event.frame];
    if (!before || !atImpact) return false;
    const nx = event.x - center.x, ny = event.y - center.y;
    const radius = Math.max(1, Math.hypot(nx, ny));
    const incoming = (before.vx * nx + before.vy * ny) / radius;
    const outgoing = (atImpact.vx * nx + atImpact.vy * ny) / radius;
    return incoming > 0 && outgoing < 0
      && event.radial_velocity_before > 0 && event.radial_velocity_after < 0;
  });
  const final = states.at(-1);
  const finalRadius = Math.hypot(final.x - center.x, final.y - center.y);
  const escaped = finalRadius > ringDefs.at(-1).radius + ballRadius
    && final.x >= ballRadius && final.x <= width - ballRadius
    && final.y >= ballRadius && final.y <= height - ballRadius;
  return { seed, states, events, brokenIds, reversalPass, escaped };
}

let result;
for (let seed = 31; seed <= 31; seed++) {
  result = run(seed);
  if (result.brokenIds.join(',') === '1,2,3,4,5,6,7,8,9,10' && result.reversalPass && result.escaped) break;
}
if (result?.brokenIds.join(',') !== '1,2,3,4,5,6,7,8,9,10' || !result.reversalPass || !result.escaped) {
  throw new Error(`Trace validation failed in ${durationSeconds}s; seed=${result?.seed}, broken=${result?.brokenIds.join(',')}, reversalPass=${result?.reversalPass}, escaped=${result?.escaped}, hits=${JSON.stringify(result?.events.filter((event) => event.type === 'ring_hit').map(({ ring_id, frame }) => ({ ring_id, frame })))}, last=${JSON.stringify(result?.states.at(-1))}`);
}

const trace = {
  schema_version: 2, width, height, fps, duration_frames: durationFrames, duration_s: durationSeconds,
  center, seed: result.seed, ball_radius: ballRadius, ring_thickness: 12,
  rings: ringDefs.map(({ durability, ...ring }) => ring), states: result.states, events: result.events,
  result: {
    escaped: result.escaped,
    ring_break_frames: result.events.filter((e) => e.type === 'ring_break').map(({ ring_id, frame }) => ({ ring_id, frame })),
  },
};
await mkdir(here, { recursive: true });
await writeFile(output, `${JSON.stringify(trace)}\n`);
console.log(JSON.stringify({ output, seed: trace.seed, duration_frames: trace.duration_frames, ring_breaks: trace.result.ring_break_frames, hits: trace.events.filter((e) => e.type === 'ring_hit').length, escaped: trace.result.escaped }));
