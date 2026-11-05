"""grant.py <request_id> : self-grant OUR OWN queued request (老大 2026-10-07 17:55 UTC+11 授权代管). Refuses if any GPU lock exists or another request is granted/running."""
import json, os, sys, datetime, glob
Q = r'E:\program\1project\video\shared\gpu-queue'
rid = sys.argv[1]; assert rid.startswith('zhumian-geomag-v3-')
for lk in (r'E:\program\1project\video\shared\work\cache\gpu.lock', r'E:\program\1project\video\shared\work\cache\gpu.lock', r'E:\program\1project\video\shared\work\cache\gpu.lock'):
    if os.path.exists(lk): sys.exit('lock present: ' + lk)
for f in glob.glob(os.path.join(Q, 'requests', '*.json')):
    j = json.load(open(f, encoding='utf-8-sig'))
    if j.get('status') in ('granted', 'running') and j.get('id') != rid: sys.exit('other active request: %s %s' % (j.get('id'), j['status']))
p = os.path.join(Q, 'requests', rid + '.json'); j = json.load(open(p, encoding='utf-8-sig'))
if j['status'] != 'queued': sys.exit('status is ' + j['status'])
j['status'] = 'granted'; j['granted_at'] = datetime.datetime.now().astimezone().isoformat(timespec='seconds')
j['granted_by'] = '助眠解说线路自授（老大 2026-10-07 17:55 UTC+11 授权全程自行处理、不等管理聊天）；授予前已核对两处锁不存在、无其他 granted/running 请求'
t = p + '.tmp'; json.dump(j, open(t, 'w', encoding='utf-8'), ensure_ascii=False, indent=2); os.replace(t, p); print('granted', rid, j['granted_at'])

