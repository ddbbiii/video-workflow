// Decompress concatenated zstd frames from DSH session logs and aggregate token usage.
const fs = require('fs');
const path = require('path');
const zlib = require('zlib');

const MAGIC = Buffer.from([0x28, 0xb5, 0x2f, 0xfd]);

function frames(buf) {
  const pos = [];
  let i = 0;
  while ((i = buf.indexOf(MAGIC, i)) !== -1) { pos.push(i); i += 4; }
  return pos;
}

function decompressAll(file) {
  const buf = fs.readFileSync(file);
  const pos = frames(buf);
  const parts = [];
  for (let k = 0; k < pos.length; k++) {
    const start = pos[k];
    const end = k + 1 < pos.length ? pos[k + 1] : buf.length;
    try {
      parts.push(zlib.zstdDecompressSync(buf.subarray(start, end)));
    } catch {
      // frame boundary guess can cut a frame short; try to the next-next boundary
      if (k + 2 <= pos.length - 1) {
        try {
          parts.push(zlib.zstdDecompressSync(buf.subarray(start, pos[k + 2])));
        } catch {}
      }
    }
  }
  return Buffer.concat(parts).toString('utf8');
}

function collectUsage(obj, out) {
  if (!obj || typeof obj !== 'object') return;
  for (const [k, v] of Object.entries(obj)) {
    if (v && typeof v === 'object') {
      const nums = Object.entries(v).filter(([, vv]) => typeof vv === 'number');
      const keys = nums.map(([kk]) => kk.toLowerCase());
      if (keys.some((x) => x.includes('input') || x.includes('output') || x.includes('token'))) {
        out.push({ at: k, ...Object.fromEntries(nums) });
      }
      collectUsage(v, out);
    }
  }
}

const root = process.argv[2] || 'C:\\Users\\10060\\.dsh\\sessions\\--E-program-1project-video--';
const files = [];
(function walk(dir) {
  for (const name of fs.readdirSync(dir)) {
    const p = path.join(dir, name);
    const st = fs.statSync(p);
    if (st.isDirectory()) walk(p);
    else if (name.endsWith('.zstd')) files.push({ p, mtime: st.mtimeMs, size: st.size });
  }
})(root);
files.sort((a, b) => b.mtime - a.mtime);

for (const f of files.slice(0, 3)) {
  let text;
  try { text = decompressAll(f.p); } catch (e) { console.log('skip', e.message); continue; }
  const lines = text.split('\n').filter(Boolean);
  const usage = [];
  const types = {};
  let last = 0;
  for (const line of lines) {
    let obj;
    try { obj = JSON.parse(line); } catch { continue; }
    types[obj.type] = (types[obj.type] || 0) + 1;
    collectUsage(obj, usage);
    if (obj.ts) last = Math.max(last, obj.ts);
  }
  console.log('\n==', path.basename(path.dirname(f.p)), 'lines', lines.length, 'bytes', text.length);
  console.log('types', types);
  console.log('usage records', usage.length, 'sample', usage.slice(0, 2));
  const totals = {};
  for (const u of usage) for (const [k, v] of Object.entries(u)) if (k !== 'at' && Number.isFinite(v)) totals[k] = (totals[k] || 0) + v;
  console.log('totals', totals);
}
