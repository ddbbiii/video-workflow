// Summarize every session: title, turns, token totals (from DSH session logs).
const fs = require('fs');
const path = require('path');
const zlib = require('zlib');

const MAGIC = Buffer.from([0x28, 0xb5, 0x2f, 0xfd]);

function decompressAll(file) {
  const buf = fs.readFileSync(file);
  const pos = [];
  let i = 0;
  while ((i = buf.indexOf(MAGIC, i)) !== -1) { pos.push(i); i += 4; }
  const parts = [];
  for (let k = 0; k < pos.length; k++) {
    const start = pos[k];
    const end = k + 1 < pos.length ? pos[k + 1] : buf.length;
    try { parts.push(zlib.zstdDecompressSync(buf.subarray(start, end))); }
    catch {
      if (k + 2 < pos.length) { try { parts.push(zlib.zstdDecompressSync(buf.subarray(start, pos[k + 2]))); } catch {} }
    }
  }
  return Buffer.concat(parts).toString('utf8');
}

function totalsOf(obj) {
  // assistant/message payloads carry {usage:{inputTokens,...}} or {data:{...}}
  const out = {};
  const walk = (o) => {
    if (!o || typeof o !== 'object') return;
    if (o.inputTokens !== undefined || o.cacheReadTokens !== undefined || o.outputTokens !== undefined) {
      for (const k of ['inputTokens', 'outputTokens', 'cacheReadTokens', 'cacheWriteTokens', 'totalTokens']) {
        if (typeof o[k] === 'number') out[k] = (out[k] || 0) + o[k];
      }
    }
    for (const v of Object.values(o)) if (v && typeof v === 'object') walk(v);
  };
  walk(obj);
  return out;
}

const roots = [
  'C:\\Users\\10060\\.dsh\\sessions\\--E-program-1project-video--',
  'C:\\Users\\10060\\.dsh\\sessions\\--C-Users-10060-Documents-deepseek-harness-default-workspace--',
];

for (const root of roots) {
  if (!fs.existsSync(root)) continue;
  const files = [];
  (function walk(dir) {
    for (const name of fs.readdirSync(dir)) {
      const p = path.join(dir, name);
      const st = fs.statSync(p);
      if (st.isDirectory()) walk(p);
      else if (name.endsWith('.zstd')) files.push({ p, mtime: st.mtimeMs });
    }
  })(root);
  files.sort((a, b) => a.mtime - b.mtime);
  console.log('\n### ' + path.basename(root) + ' (' + files.length + ' sessions)');
  for (const f of files) {
    let text;
    try { text = decompressAll(f.p); } catch { continue; }
    let title = '';
    const sum = {};
    let turns = 0, steps = 0, date = '';
    for (const line of text.split('\n')) {
      if (!line) continue;
      let o;
      try { o = JSON.parse(line); } catch { continue; }
      if (o.type === 'session' && o.createdAt) date = new Date(o.createdAt).toISOString().slice(0, 10);
      if (o.type === 'turn/start') turns++;
      if (o.type === 'step/start') steps++;
      if (o.type === 'session/title' && o.title) title = String(o.title).slice(0, 40);
      const t = totalsOf(o);
      for (const [k, v] of Object.entries(t)) sum[k] = (sum[k] || 0) + v;
    }
    const usd = ((sum.inputTokens || 0) / 1e6) * 0.15
      + ((sum.cacheReadTokens || 0) / 1e6) * 0.003
      + ((sum.outputTokens || 0) / 1e6) * 0.60;
    console.log([
      date, path.basename(path.dirname(f.p)).slice(0, 16).padEnd(16),
      String(turns).padStart(3), String(steps).padStart(4),
      ((sum.inputTokens || 0) / 1e6).toFixed(2).padStart(6),
      ((sum.cacheReadTokens || 0) / 1e6).toFixed(1).padStart(8),
      ((sum.outputTokens || 0) / 1e6).toFixed(3).padStart(6),
      ('$' + usd.toFixed(2)).padStart(7),
      title,
    ].join(' | '));
  }
}
