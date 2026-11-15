// Map session ids -> titles from projcache, print alongside token cost for big sessions.
const fs = require('fs');
const path = require('path');

const cacheDir = 'C:\\Users\\10060\\.dsh\\storages\\session_projcache\\sessions';
const titles = {};
for (const name of fs.readdirSync(cacheDir)) {
  if (!name.endsWith('.json')) continue;
  try {
    const j = JSON.parse(fs.readFileSync(path.join(cacheDir, name), 'utf8'));
    const id = j?.record?.identity?.sessionId || name.replace(/^session-/, '').replace(/\.json$/, '');
    const title = j?.record?.rows?.title?.val;
    if (title) titles[id] = title;
    // also try all keys
    for (const k of Object.keys(j?.record?.rows || {})) {
      if (/title/i.test(k) && typeof j.record.rows[k].val === 'string') titles[id] = titles[id] || j.record.rows[k].val;
    }
  } catch {}
}
console.log('titles found:', Object.keys(titles).length);
for (const [id, t] of Object.entries(titles)) console.log(id.slice(0, 24), '|', String(t).slice(0, 60));
