import { Application, Container, Graphics } from 'pixi.js';

const WIDTH = 1080;
const HEIGHT = 1920;
const frameIndex = Number(new URLSearchParams(location.search).get('frame') ?? 0);

function hexToInt(color) {
  return Number.parseInt(String(color).replace('#', ''), 16);
}

function addGlowArc(layer, cx, cy, radius, ring, angle, alpha = 1) {
  const gap = ring.gap_width ?? Math.PI / 7;
  if (gap <= 0) {
    for (const [width, opacity] of [[ring.thickness * 3.1, 0.045], [ring.thickness * 1.8, 0.11], [ring.thickness, 0.82]]) {
      const path = new Graphics();
      path.setStrokeStyle({ width, color: hexToInt(ring.color), alpha: opacity * alpha });
      path.circle(cx, cy, radius);
      path.stroke();
      layer.addChild(path);
    }
    return;
  }
  const start = angle + gap / 2;
  const end = angle + Math.PI * 2 - gap / 2;
  const segments = Math.max(72, Math.ceil(radius / 2));
  for (const [width, opacity] of [[ring.thickness * 3.1, 0.045], [ring.thickness * 1.8, 0.11], [ring.thickness, 0.82]]) {
    const path = new Graphics();
    path.setStrokeStyle({
      width,
      color: hexToInt(ring.color),
      alpha: opacity * alpha,
      cap: 'round',
    });
    for (let i = 0; i <= segments; i += 1) {
      const a = start + ((end - start) * i) / segments;
      const x = cx + Math.cos(a) * radius;
      const y = cy + Math.sin(a) * radius;
      if (i === 0) path.moveTo(x, y);
      else path.lineTo(x, y);
    }
    path.stroke();
    layer.addChild(path);
  }
}

function addFracture(layer, event, frame, rings) {
  const age = frame - event.frame;
  if (age < 0 || age > 26) return;
  const progress = age / 26;
  const x = event.x;
  const y = event.y;
  const sourceColor = rings.find((ring) => ring.id === event.ring_id)?.color ?? '#ffffff';
  const color = hexToInt(sourceColor);
  for (let i = 0; i < 10; i += 1) {
    const a = (i / 10) * Math.PI * 2 + event.ring_id * 0.31;
    const distance = 10 + progress * (36 + (i % 3) * 15);
    const r = Math.max(1, (1 - progress) * (4 + (i % 2) * 2));
    const shard = new Graphics();
    shard.circle(x + Math.cos(a) * distance, y + Math.sin(a) * distance, r);
    shard.fill({ color, alpha: (1 - progress) * 0.88 });
    layer.addChild(shard);
  }
}

function drawScene(root, trace, frame) {
  root.removeChildren();
  const { width, height, fps, rings, states, events, ball_radius: ballRadius } = trace;
  const state = states[Math.max(0, Math.min(frame, states.length - 1))];
  if (!state) throw new Error(`No state at frame ${frame}`);

  const cx = width / 2;
  const cy = height / 2;
  const background = new Graphics();
  background.rect(0, 0, width, height).fill(0x111318);
  root.addChild(background);

  const halo = new Graphics();
  halo.circle(cx, cy, width * 0.34).fill({ color: 0x243238, alpha: 0.16 });
  root.addChild(halo);

  const ringLayer = new Container();
  root.addChild(ringLayer);
  for (const ring of rings) {
    if (!state.alive_ring_ids.includes(ring.id)) continue;
    const radius = ring.radius;
    const angle = ring.gap_angle + ring.rotate_speed * (frame / fps);
    addGlowArc(ringLayer, cx, cy, radius, ring, angle);
  }

  const eventLayer = new Container();
  root.addChild(eventLayer);
  for (const event of events) addFracture(eventLayer, event, frame, rings);

  const bx = state.x;
  const by = state.y;
  const trail = new Graphics();
  for (let i = 7; i >= 1; i -= 1) {
    const prior = states[Math.max(0, frame - i * 2)];
    if (!prior) continue;
    const alpha = (8 - i) / 46;
    trail.circle(prior.x, prior.y, ballRadius * (1 - i * 0.055));
    trail.fill({ color: 0xcce4ed, alpha });
  }
  root.addChild(trail);

  const ballGlow = new Graphics();
  ballGlow.circle(bx, by, ballRadius * 2.7).fill({ color: 0xbce9f4, alpha: 0.075 });
  ballGlow.circle(bx, by, ballRadius * 1.8).fill({ color: 0xd9f5ff, alpha: 0.12 });
  root.addChild(ballGlow);

  const ball = new Graphics();
  ball.circle(bx, by, ballRadius).fill({ color: 0xe9f4f8 });
  ball.circle(bx - ballRadius * 0.28, by - ballRadius * 0.34, ballRadius * 0.28)
    .fill({ color: 0xffffff, alpha: 0.9 });
  ball.circle(bx + ballRadius * 0.08, by + ballRadius * 0.1, ballRadius * 0.82)
    .stroke({ color: 0x99b8c3, width: 2, alpha: 0.36 });
  root.addChild(ball);
}

const trace = await (await fetch('/trace.json')).json();
const app = new Application();
await app.init({
  width: WIDTH,
  height: HEIGHT,
  resolution: 1,
  antialias: true,
  backgroundColor: 0x111318,
  autoDensity: false,
  preference: 'webgl',
});
app.canvas.id = 'frame';
document.body.appendChild(app.canvas);
drawScene(app.stage, trace, frameIndex);
window.drawFrame = (frame) => drawScene(app.stage, trace, frame);
document.documentElement.dataset.ready = 'true';
