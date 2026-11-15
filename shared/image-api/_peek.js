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
const buf = zlib.zstdDecompressSync(fs.readFileSync(f.p));
console.log('file', f.p, 'raw', f.size, 'decomp', buf.length);
const text = buf.toString('utf8');
console.log('first 600:', text.slice(0, 600));
console.log('has newline:', text.includes('\n'), 'count:', (text.match(/\n/g) || []).length);
console.log('starts:', JSON.stringify(text.slice(0, 20)));
