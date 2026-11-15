// Inspect DSH session JSONL: find token usage records and aggregate per session.
const fs = require('fs');
const path = require('path');
const zlib = require('zlib');

const root = 'C:\\Users\\10060\\.dsh\\sessions\\--E-program-1project-video--';

function walk(dir, out = []) {
  for (const name of fs.readdirSync(dir)) {
    const p = path.join(dir, name);
    const st = fs.statSync(p);
    if (st.isDirectory()) walk(p, out);
    else if (name.endsWith('.zstd')) out.push({ p, mtime: st.mtimeMs, size: st.size });
  }
  return out;
}

function usageOf(obj, acc) {
  if (!obj || typeof obj !== 'object') return;
  for (const [k, v] of Object.entries(obj)) {
    if (/usage/i.test(k) && v && typeof v === 'object') {
      const pick = {};
      for (const [kk, vv] of Object.entries(v)) if (typeof vv === 'number') pick[kk] = vv;
      if (Object.keys(pick).length) acc.push({ key: k, ...pick });
    }
    if (v && typeof v === 'object') usageOf(v, acc);
  }
}

const files = walk(root).sort((a, b) => b.mtime - a.mtime);
console.log('sessions:', files.length);
for (const f of files.slice(0, 5)) {
  let buf;
  try { buf = zlib.zstdDecompressSync(fs.readFileSync(f.p)); } catch (e) { console.log('skip', f.p, e.message); continue; }
  const text = buf.toString('utf8');
  const lines = text.split('\n').filter(Boolean);
  const acc = [];
  for (const line of lines) {
    let obj;
    try { obj = JSON.parse(line); } catch { continue; }
    usageOf(obj, acc);
  }
  const totals = {};
  for (const a of acc) for (const [k, v] of Object.entries(a)) if (k !== 'key') totals[k] = (totals[k] || 0) + v;
  console.log('\n==', path.basename(path.dirname(f.p)), '| lines', lines.length, '| usage records', acc.length);
  console.log('sample keys:', [...new Set(acc.map(a => a.key))].slice(0, 5));
  console.log('totals:', totals);
}
