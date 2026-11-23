import p5 from 'p5';

const TAU = Math.PI * 2;
const TRAIL_LENGTH = 11;
const HIT_PULSE_FRAMES = 14;
const BREAK_EFFECT_FRAMES = 24;

const ready = async () => {
  const response = await fetch('/trace.json');
  if (!response.ok) throw new Error(`trace.json load failed: ${response.status}`);
  const trace = await response.json();
  const stateByFrame = trace.states;
  const events = trace.events ?? [];
  const center = trace.center ?? { x: trace.width / 2, y: trace.height / 2 };
  const rings = [...trace.rings].sort((a, b) => b.radius - a.radius);
  const seed = trace.seed ?? 1;

  new p5((sketch) => {
    let currentFrame = 0;
    let starPoints = [];

    sketch.setup = () => {
      sketch.pixelDensity(1);
      sketch.createCanvas(trace.width, trace.height);
      sketch.noLoop();
      sketch.noStroke();
      const random = seededRandom(seed ^ 0x51f15e);
      starPoints = Array.from({ length: 46 }, () => ({
        x: random() * trace.width,
        y: random() * trace.height,
        r: 1 + random() * 1.6,
        a: 0.12 + random() * 0.22,
      }));
      window.__drawFrame = (frame) => {
        currentFrame = Math.max(0, Math.min(trace.duration_frames - 1, frame | 0));
        sketch.redraw();
      };
      window.__traceReady = true;
      sketch.redraw();
    };

    sketch.draw = () => {
      const ctx = sketch.drawingContext;
      const state = stateByFrame[currentFrame];
      if (!state) throw new Error(`missing state at frame ${currentFrame}`);

      const shake = shakeAt(events, currentFrame, seed);
      ctx.save();
      ctx.translate(shake.x, shake.y);
      drawBackdrop(sketch, ctx, starPoints, center, trace.width, trace.height);

      const alive = new Set(state.alive_ring_ids ?? rings.map((ring) => ring.id));
      for (const ring of rings) {
        if (!alive.has(ring.id)) continue;
        const gapWidth = ring.gap_width ?? trace.gap_width ?? 0.34;
        const angle = gapWidth <= 0.001 ? 0 : ring.gap_angle + ring.rotate_speed * (currentFrame / trace.fps);
        const pulse = pulseForRing(events, ring.id, currentFrame);
        drawRing(sketch, ctx, ring, center, angle, gapWidth, pulse);
      }

      drawEventEffects(sketch, ctx, events, rings, currentFrame, seed);
      drawTrail(sketch, ctx, stateByFrame, currentFrame);
      drawBall(sketch, ctx, state, trace.ball_radius ?? 18);
      ctx.restore();
    };
  }, document.querySelector('#stage'));
};

function seededRandom(seed) {
  let value = seed >>> 0;
  return () => {
    value += 0x6d2b79f5;
    let t = value;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function drawBackdrop(p, ctx, stars, center, width, height) {
  p.background('#0b0e14');
  const glow = ctx.createRadialGradient(center.x, center.y, width * 0.04, center.x, center.y, height * 0.58);
  glow.addColorStop(0, 'rgba(28, 40, 55, 0.62)');
  glow.addColorStop(0.54, 'rgba(18, 24, 34, 0.34)');
  glow.addColorStop(1, 'rgba(8, 10, 15, 0)');
  ctx.fillStyle = glow;
  ctx.fillRect(0, 0, width, height);

  p.noStroke();
  for (const star of stars) {
    p.fill(202, 219, 235, star.a * 255);
    p.circle(star.x, star.y, star.r);
  }
}

function drawRing(p, ctx, ring, center, gapAngle, gapWidth, pulse) {
  const start = gapAngle + gapWidth / 2;
  const end = gapAngle + TAU - gapWidth / 2;
  const impulseScale = Math.min(1.8, Math.max(0, pulse.strength));
  const envelope = Math.max(0, 1 - pulse.age / HIT_PULSE_FRAMES);
  const pulseProgress = Math.max(0, Math.min(1, pulse.age / HIT_PULSE_FRAMES));
  const pulseWave = Math.sin(pulseProgress * Math.PI);
  const radius = ring.radius + pulseWave * 3.5 * impulseScale * envelope;
  const thickness = ring.thickness * (1 + impulseScale * 0.48);
  const outer = radius + thickness * 0.5;
  const inner = radius - thickness * 0.5;

  ctx.save();
  ctx.lineCap = 'round';
  ctx.shadowColor = ring.color;
  ctx.shadowBlur = 17 + impulseScale * 27;
  ctx.strokeStyle = ring.color;
  ctx.lineWidth = thickness;
  ctx.beginPath();
  ctx.arc(center.x, center.y, radius, start, end);
  ctx.stroke();

  ctx.shadowBlur = 0;
  ctx.strokeStyle = 'rgba(236, 247, 255, 0.62)';
  ctx.lineWidth = Math.max(1.4, thickness * 0.15);
  ctx.beginPath();
  ctx.arc(center.x, center.y, radius - thickness * 0.18, start + 0.03, end - 0.03);
  ctx.stroke();

  ctx.globalAlpha = 0.24;
  ctx.strokeStyle = 'rgba(255,255,255,0.6)';
  ctx.lineWidth = Math.max(1, thickness * 0.08);
  ctx.beginPath();
  ctx.arc(center.x, center.y, outer + ring.thickness * 0.2, start, end);
  ctx.stroke();
  ctx.restore();
}

function pulseForRing(events, ringId, frame) {
  let strongest = { strength: 0, age: HIT_PULSE_FRAMES };
  for (const event of events) {
    if (event.type !== 'ring_hit' || event.ring_id !== ringId) continue;
    const age = frame - event.frame;
    if (age < 0 || age >= HIT_PULSE_FRAMES) continue;
    const impact = Math.max(clamp01(event.impulse), clamp01(event.damage));
    const strength = (0.35 + impact * 1.25) * (1 - age / HIT_PULSE_FRAMES);
    if (strength > strongest.strength) strongest = { strength, age };
  }
  return strongest;
}

function shakeAt(events, frame, seed) {
  let x = 0;
  let y = 0;
  for (const event of events) {
    if (event.type !== 'ring_hit') continue;
    const age = frame - event.frame;
    if (age < 0 || age > 7) continue;
    const random = seededRandom((seed ^ Math.imul(event.ring_id + 11, 0x9e3779b1) ^ event.frame ^ frame) >>> 0);
    const impact = Math.max(clamp01(event.impulse), clamp01(event.damage));
    const amplitude = (1.2 + 2.5 * impact) * (1 - age / 8);
    const phase = age * 1.2 + event.frame * 0.17;
    x += Math.sin(phase) * amplitude;
    y += Math.cos(phase * 1.13) * amplitude;
  }
  const magnitude = Math.hypot(x, y);
  if (magnitude > 8) {
    x *= 8 / magnitude;
    y *= 8 / magnitude;
  }
  return { x, y };
}

function drawEventEffects(p, ctx, events, rings, frame, seed) {
  for (const event of events) {
    const age = frame - event.frame;
    if (age < 0) continue;
    const random = seededRandom((seed ^ Math.imul(event.ring_id + 37, 0x9e3779b1) ^ event.frame) >>> 0);
    const color = event.color ?? rings.find((ring) => ring.id === event.ring_id)?.color ?? '#f4c95d';

    if (event.type === 'ring_hit' && age < HIT_PULSE_FRAMES) {
      const impact = Math.max(clamp01(event.impulse), clamp01(event.damage));
      const impulse = 0.35 + impact * 1.25;
      const progress = age / HIT_PULSE_FRAMES;
      const strength = (1 - progress) * impulse;
      const radius = 10 + progress * (48 + impulse * 20);
      ctx.save();
      ctx.globalAlpha = Math.min(0.85, strength * 0.48);
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.5 + strength * 2.5;
      ctx.shadowColor = color;
      ctx.shadowBlur = 17 + strength * 12;
      ctx.beginPath();
      ctx.arc(event.x, event.y, radius, 0, TAU);
      ctx.stroke();
      ctx.restore();

      p.noStroke();
      for (let i = 0; i < 5; i++) {
        const angle = (i / 5) * TAU + random() * 0.12;
        const sparkDistance = 8 + age * (2.3 + random() * 1.1);
        p.fill(245, 252, 255, Math.min(225, strength * 130));
        p.circle(event.x + Math.cos(angle) * sparkDistance, event.y + Math.sin(angle) * sparkDistance, 2 + strength * 2);
      }
    }

    if (event.type !== 'ring_break' || age >= BREAK_EFFECT_FRAMES) continue;
    const strength = 1 - age / BREAK_EFFECT_FRAMES;
    const radius = 17 + age * 8;

    ctx.save();
    ctx.globalAlpha = strength * 0.55;
    ctx.strokeStyle = color;
    ctx.lineWidth = 2 + strength * 6;
    ctx.shadowColor = color;
    ctx.shadowBlur = 20;
    const angle = event.angle ?? -0.45;
    ctx.beginPath();
    ctx.arc(event.x, event.y, radius, angle - 1.1, angle + 1.1);
    ctx.stroke();
    ctx.restore();

    p.noStroke();
    for (let i = 0; i < 15; i++) {
      const angle = random() * TAU;
      const speed = 14 + random() * 42;
      const x = event.x + Math.cos(angle) * (speed * age * 0.3);
      const y = event.y + Math.sin(angle) * (speed * age * 0.3);
      p.fill(color);
      p.circle(x, y, Math.max(1.2, (4 + random() * 5) * strength));
    }
  }
}

function clamp01(value = 0) {
  return Math.max(0, Math.min(1, Number(value) || 0));
}

function drawTrail(p, ctx, states, frame) {
  for (let offset = TRAIL_LENGTH; offset >= 1; offset--) {
    const prior = states[Math.max(0, frame - offset)];
    if (!prior) continue;
    const alpha = (1 - offset / (TRAIL_LENGTH + 1)) * 0.22;
    p.noStroke();
    p.fill(159, 219, 240, alpha * 255);
    p.circle(prior.x, prior.y, 5 + (1 - offset / TRAIL_LENGTH) * 9);
  }
}

function drawBall(p, ctx, state, radius) {
  ctx.save();
  ctx.shadowColor = 'rgba(156, 223, 255, 0.86)';
  ctx.shadowBlur = radius * 1.8;
  const gradient = ctx.createRadialGradient(
    state.x - radius * 0.34,
    state.y - radius * 0.4,
    radius * 0.06,
    state.x,
    state.y,
    radius,
  );
  gradient.addColorStop(0, '#ffffff');
  gradient.addColorStop(0.25, '#f4fbff');
  gradient.addColorStop(0.66, '#b9d3df');
  gradient.addColorStop(1, '#6f8d9b');
  ctx.fillStyle = gradient;
  ctx.beginPath();
  ctx.arc(state.x, state.y, radius, 0, TAU);
  ctx.fill();

  ctx.shadowBlur = 0;
  ctx.globalAlpha = 0.76;
  ctx.fillStyle = '#ffffff';
  ctx.beginPath();
  ctx.ellipse(state.x - radius * 0.31, state.y - radius * 0.39, radius * 0.15, radius * 0.23, -0.65, 0, TAU);
  ctx.fill();
  ctx.restore();
}

ready().catch((error) => {
  console.error(error);
  window.__traceError = String(error?.stack ?? error);
});
