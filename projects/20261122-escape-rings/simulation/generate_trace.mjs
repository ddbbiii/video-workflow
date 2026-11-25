import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import Matter from 'matter-js';

const { Bodies, Body, Composite, Engine, Events } = Matter;
const here = path.dirname(fileURLToPath(import.meta.url));
const output = path.join(here, 'trace.json');
const width = 1080;
const height = 1920;
const fps = 30;
const durationSeconds = 14;
const durationFrames = durationSeconds * fps;
const center = { x: width / 2, y: height / 2 };
const ballRadius = 26;
const physicsFps = 120;
const physicsStepMs = 1000 / physicsFps;
const segmentCount = 180;
const ringDefs = Array.from({ length: 10 }, (_, index) => ({
  id: index + 1,
  radius: 70 + index * 75,
  thickness: 12,
  gap_width: 0.045,
  gap_angle: [0.18, 1.52, 2.74, 4.31, 5.58, 0.91, 2.16, 3.77, 4.91, 0.43][index],
  rotate_speed: [0.11, -0.09, 0.08, -0.07, 0.06, -0.05, 0.045, -0.04, 0.035, -0.03][index],
  color: ['#36d6c4', '#ffc45c', '#ff6f76', '#7f9cff', '#36d6c4', '#ffc45c', '#ff6f76', '#7f9cff', '#36d6c4', '#ffc45c'][index],
  durability: index === 0 || index === 9 ? 1.65 : 0.82,
}));

function seededRandom(seed) {
  let state = seed >>> 0;
  return () => {
    state = (state * 1664525 + 1013904223) >>> 0;
    return state / 0x100000000;
  };
}

function angleDifference(a, b) {
  return Math.atan2(Math.sin(a - b), Math.cos(a - b));
}

function buildRing(engine, ring) {
  const angularStep = (Math.PI * 2) / segmentCount;
  const segmentLength = ring.radius * angularStep * 1.16;
  const bodies = [];

  for (let i = 0; i < segmentCount; i++) {
    const angle = i * angularStep;
    if (Math.abs(angleDifference(angle, ring.gap_angle)) < ring.gap_width / 2) continue;
    const mid = angle + angularStep / 2;
    const x = center.x + Math.cos(mid) * ring.radius;
    const y = center.y + Math.sin(mid) * ring.radius;
    const segment = Bodies.rectangle(x, y, segmentLength, ring.thickness, {
      isStatic: true,
      restitution: 0.94,
      friction: 0,
      frictionStatic: 0,
      label: `ring-${ring.id}`,
      angle: mid + Math.PI / 2,
    });
    segment.plugin.ringId = ring.id;
    bodies.push(segment);
  }
  Composite.add(engine.world, bodies);
  return bodies;
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function run(seed) {
  const random = seededRandom(seed);
  const engine = Engine.create({ enableSleeping: false });
  engine.gravity.scale = 0;
  engine.positionIterations = 10;
  engine.velocityIterations = 10;

  const body = Bodies.circle(center.x + 12, center.y - 18, ballRadius, {
    label: 'ball',
    restitution: 0.98,
    friction: 0,
    frictionAir: 0.00004,
    density: 0.008,
  });
  Body.setVelocity(body, { x: 330 / physicsFps, y: 82 / physicsFps });
  Composite.add(engine.world, body);

  const bodiesByRing = new Map();
  const alive = new Set(ringDefs.map((ring) => ring.id));
  const damage = new Map(ringDefs.map((ring) => [ring.id, 0]));
  for (const ring of ringDefs) bodiesByRing.set(ring.id, buildRing(engine, ring));

  const events = [];
  const states = [];
  let pendingHits = new Map();

  Events.on(engine, 'collisionStart', ({ pairs }) => {
    for (const pair of pairs) {
      const a = pair.bodyA;
      const b = pair.bodyB;
      const ringId = a.label === 'ball' ? b.plugin.ringId : b.label === 'ball' ? a.plugin.ringId : null;
      if (!ringId || !alive.has(ringId) || pendingHits.has(ringId)) continue;
      pendingHits.set(ringId, {
        x: body.position.x,
        y: body.position.y,
        speed: Math.hypot(body.velocity.x, body.velocity.y) * physicsFps,
      });
    }
  });

  let renderedFrame = 0;
  let heldFrames = 0;
  for (let physicsFrame = 0; renderedFrame < durationFrames; physicsFrame++) {
    if (heldFrames === 0) {
      Engine.update(engine, physicsStepMs);
      const hits = [...pendingHits.entries()].sort(([a], [b]) => a - b);
      pendingHits = new Map();

      for (const [ringId, hit] of hits) {
        if (!alive.has(ringId)) continue;
        const ring = ringDefs[ringId - 1];
        const radius = Math.max(1, Math.hypot(hit.x - center.x, hit.y - center.y));
        const normal = { x: (hit.x - center.x) / radius, y: (hit.y - center.y) / radius };
        const impulse = clamp(hit.speed / 520, 0.18, 1);
        const nextDamage = Math.min(ring.durability, damage.get(ringId) + impulse);
        damage.set(ringId, nextDamage);
        const frame = Math.min(durationFrames - 1, Math.floor(physicsFrame / (physicsFps / fps)));
        events.push({
          frame,
          type: 'ring_hit',
          ring_id: ringId,
          x: hit.x,
          y: hit.y,
          impulse,
          damage: nextDamage / ring.durability,
          color: ring.color,
        });

        if (nextDamage + 1e-6 < ring.durability) continue;
        alive.delete(ringId);
        for (const segment of bodiesByRing.get(ringId)) Composite.remove(engine.world, segment, true);
        events.push({
          frame: Math.min(durationFrames - 1, frame + 1),
          type: 'ring_break',
          ring_id: ringId,
          x: hit.x,
          y: hit.y,
          impulse,
          damage: 1,
          color: ring.color,
        });

        const velocity = body.velocity;
        const normalSpeed = velocity.x * normal.x + velocity.y * normal.y;
        const tangent = {
          x: velocity.x - normal.x * normalSpeed,
          y: velocity.y - normal.y * normalSpeed,
        };
        const releaseSpeed = Math.max(Math.abs(normalSpeed) * 0.88, (hit.speed / physicsFps) * 0.42, 2.2);
        const side = random() < 0.5 ? -1 : 1;
        const tangentBoost = side * random() * 0.22 * releaseSpeed;
        const tx = -normal.y;
        const ty = normal.x;
        Body.setVelocity(body, {
          x: tangent.x * 0.72 + normal.x * releaseSpeed + tx * tangentBoost,
          y: tangent.y * 0.72 + normal.y * releaseSpeed + ty * tangentBoost,
        });
        heldFrames = 8;
      }
    } else {
      heldFrames -= 1;
    }

    if (physicsFrame % 4 !== 0 && physicsFrame !== 0) continue;
    const frame = renderedFrame++;
    const speed = Math.hypot(body.velocity.x, body.velocity.y) * physicsFps;
    states.push({
      frame,
      x: body.position.x,
      y: body.position.y,
      angle: body.angle,
      vx: body.velocity.x * physicsFps,
      vy: body.velocity.y * physicsFps,
      speed,
      alive_ring_ids: [...alive].sort((a, b) => a - b),
    });
  }

  const brokenIds = events.filter((event) => event.type === 'ring_break').map((event) => event.ring_id);
  return { seed, states, events, brokenIds };
}

let result;
for (let seed = 31; seed <= 130; seed++) {
  result = run(seed);
  if (result.brokenIds.join(',') === '1,2,3,4,5,6,7,8,9,10') break;
}

if (result?.brokenIds.join(',') !== '1,2,3,4,5,6,7,8,9,10') {
  throw new Error(`Could not break all ten rings in ${durationSeconds}s; last seed=${result?.seed}, rings=${result?.brokenIds.join(',')}`);
}

const trace = {
  schema_version: 2,
  width,
  height,
  fps,
  duration_frames: durationFrames,
  duration_s: durationSeconds,
  center,
  seed: result.seed,
  ball_radius: ballRadius,
  ring_thickness: 12,
  rings: ringDefs.map(({ durability, ...ring }) => ring),
  states: result.states,
  events: result.events,
  result: {
    escaped: result.states.at(-1).alive_ring_ids.length === 0,
    ring_break_frames: result.events.filter((event) => event.type === 'ring_break').map(({ ring_id, frame }) => ({ ring_id, frame })),
  },
};

await mkdir(here, { recursive: true });
await writeFile(output, `${JSON.stringify(trace)}\n`);
console.log(JSON.stringify({
  output,
  seed: trace.seed,
  duration_frames: trace.duration_frames,
  ring_breaks: trace.result.ring_break_frames,
  hits: trace.events.filter((event) => event.type === 'ring_hit').length,
  escaped: trace.result.escaped,
}));
