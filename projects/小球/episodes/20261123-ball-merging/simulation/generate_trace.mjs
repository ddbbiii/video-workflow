import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import Matter from '../../20261122-escape-rings/renderers/pixi/node_modules/matter-js/build/matter.js';

const { Bodies, Body, Composite, Engine, Events } = Matter;
const here = path.dirname(fileURLToPath(import.meta.url));
const width = 1080, height = 1920, fps = 30;
const targetTier = 7;
const tailFrames = fps;
const maxSimulationFrames = 90 * fps;
const physicsFps = 120, stepMs = 1000 / physicsFps;
const baseRadius = 41;
const radiusGrowth = 1.20;
const dropEveryTicks = physicsFps * 0.3;
const mouthY = 401;
const dropVelocity = 3.7;
const bodyWidthScale = 0.94;
const bodyHeightScale = 0.72;
const neckEndY = 635;
const leftRim = [
  [462, 398], [462, 635], [459, 668], [450, 702], [436, 736],
  [168, 1345], [157, 1383], [157, 1418], [167, 1448],
  [188, 1473], [214, 1486], [243, 1490],
].map(([x, y]) => {
  if (y <= neckEndY) return [x, y];
  const shoulder = Math.max(0, (736 - y) / (736 - neckEndY));
  const widthScale = bodyWidthScale + (1 - bodyWidthScale) * shoulder;
  return [540 - (540 - x) * widthScale, neckEndY + (y - neckEndY) * bodyHeightScale];
});
const flaskOutline = [...leftRim, ...leftRim.slice().reverse().map(([x, y]) => [width - x, y])];
const tierColors = ['#ffca66', '#f78b66', '#f26981', '#bd86f5', '#6eafff', '#47d7c2', '#b2ec78', '#f5d6ff', '#ffef9b'];
const engine = Engine.create({ enableSleeping: false });
engine.gravity.y = 0.95;
engine.positionIterations = 10;
engine.velocityIterations = 8;

function radiusFor(tier) { return baseRadius * radiusGrowth ** tier; }

const wallThickness = 30;
const walls = flaskOutline.slice(1).map(([x2, y2], i) => {
  const [x1, y1] = flaskOutline[i];
  const dx = x2 - x1, dy = y2 - y1;
  const length = Math.hypot(dx, dy);
  const outset = wallThickness / 2;
  return Bodies.rectangle(
    (x1 + x2) / 2 - dy / length * outset,
    (y1 + y2) / 2 + dx / length * outset,
    length + 14, wallThickness,
    { isStatic: true, angle: Math.atan2(dy, dx), friction: 0.09, restitution: 0.24, label: 'flask-wall' },
  );
});
Composite.add(engine.world, walls);

let nextId = 1;
const balls = new Map();
const events = [];
const states = [];
let spawnIndex = 0;
let targetFrame;

function spawnBall(x, y, tier, vx = 0, vy = 0, angularVelocity = 0) {
  const r = radiusFor(tier);
  const body = Bodies.circle(x, y, r, {
    label: 'ball', restitution: 0.28, friction: 0.025, frictionAir: 0.0008,
    density: 0.0012, slop: 0.02,
  });
  body.plugin.ballId = nextId;
  body.plugin.tier = tier;
  body.plugin.merged = false;
  Body.setVelocity(body, { x: vx, y: vy });
  Body.setAngularVelocity(body, angularVelocity);
  balls.set(nextId, { id: nextId, tier, body, bornFrame: -1 });
  Composite.add(engine.world, body);
  return nextId++;
}

function dropBall(frame) {
  const x = width / 2;
  const y = mouthY;
  // The previous ball needs to clear the mouth before another appears at the same point.
  const id = spawnBall(x, y, 0, 0, dropVelocity, 0);
  events.push({ frame, tick: physicsTick, type: 'spawn', tier: 0, x, y, ball_id: id });
  spawnIndex++;
}

Events.on(engine, 'collisionStart', ({ pairs }) => {
  const frame = Math.floor(physicsTick / physicsFramesPerOutput);
  for (const { bodyA, bodyB, collision } of pairs) {
    const normal = collision.normal;
    const approach = Math.abs((bodyA.velocity.x-bodyB.velocity.x)*normal.x+(bodyA.velocity.y-bodyB.velocity.y)*normal.y);
    if (approach > 0.18) for (const body of [bodyA,bodyB]) {
      if (balls.has(body.plugin.ballId)) events.push({frame,type:'collision',ball_id:body.plugin.ballId,normal_x:normal.x,normal_y:normal.y,intensity:Math.min(1,approach/8)});
    }
    const a = balls.get(bodyA.plugin.ballId);
    const b = balls.get(bodyB.plugin.ballId);
    if (!a || !b || a.id === b.id || a.tier !== b.tier || a.body.plugin.merged || b.body.plugin.merged) continue;
    a.body.plugin.merged = true;
    b.body.plugin.merged = true;
    const tier = a.tier + 1;
    const x = (a.body.position.x + b.body.position.x) / 2;
    const y = (a.body.position.y + b.body.position.y) / 2;
    const vx = (a.body.velocity.x + b.body.velocity.x) / 2;
    const vy = (a.body.velocity.y + b.body.velocity.y) / 2;
    const angularVelocity = (a.body.angularVelocity + b.body.angularVelocity) / 2;
    Composite.remove(engine.world, a.body);
    Composite.remove(engine.world, b.body);
    balls.delete(a.id);
    balls.delete(b.id);
    const id = spawnBall(x, y, tier, vx, vy, angularVelocity);
    balls.get(id).bornFrame = frame;
    events.push({ frame, type: 'merge', tier, x, y, ball_id: id, source_ids: [a.id, b.id] });
    if (tier === targetTier && targetFrame === undefined) targetFrame = frame;
  }
});

const physicsFramesPerOutput = physicsFps / fps;
let physicsTick = 0;
for (let frame = 0; frame < (targetFrame === undefined ? maxSimulationFrames : targetFrame + tailFrames); frame++) {
  for (let sub = 0; sub < physicsFramesPerOutput; sub++) {
    if (targetFrame === undefined && physicsTick % dropEveryTicks === 0) dropBall(frame);
    Engine.update(engine, stepMs);
    physicsTick++;
  }
  states.push({
    frame,
    balls: [...balls.values()].map(({ id, tier, body, bornFrame }) => ({
      id, tier, x: body.position.x, y: body.position.y,
      vx: body.velocity.x * physicsFps, vy: body.velocity.y * physicsFps,
      angle: body.angle, angularVelocity: body.angularVelocity * physicsFps,
      radius: radiusFor(tier), born_frame: bornFrame,
    })),
  });
}

if (targetFrame === undefined) throw new Error(`The selected drop pattern did not reach tier ${targetTier}.`);
const trace = { schema_version: 1, width, height, fps, duration_frames: states.length, duration_s: states.length / fps, target_tier: targetTier, target_frame: targetFrame, base_radius: baseRadius, radius_growth: radiusGrowth, flask_outline: flaskOutline, tier_colors: tierColors, states, events };
await mkdir(here, { recursive: true });
await writeFile(path.join(here, 'trace.json'), `${JSON.stringify(trace)}\n`);
console.log(JSON.stringify({ frames: states.length, spawns: spawnIndex, merges: events.filter((event) => event.type === 'merge').length, highest_tier: Math.max(0, ...events.filter((event) => event.type === 'merge').map((event) => event.tier)) }));
