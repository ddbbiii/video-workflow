const fs = require('fs');
const path = require('path');
const zlib = require('zlib');
const root = 'C:\\Users\\10060\\.dsh\\sessions\\--E-program-1project-video--';
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
const f = files[0];

const chunks = [];
const dec = zlib.createZstdDecompress();
dec.on('data', (c) => chunks.push(c));
dec.on('end', () => {
  const text = Buffer.concat(chunks).toString('utf8');
  console.log('decomp', text.length, 'lines', (text.match(/\n/g) || []).length);
  const lines = text.split('\n').filter(Boolean);
  console.log('first line type:', JSON.parse(lines[0]).type);
  const types = {};
  for (const l of lines) { try { const o = JSON.parse(l); types[o.type] = (types[o.type] || 0) + 1; } catch {} }
  console.log(types);
});
dec.on('error', (e) => console.log('err', e.message));
fs.createReadStream(f.p).pipe(dec);
