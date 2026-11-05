import json
m=json.load(open(r"E:\program\1project\video\projects\悬疑动漫\mirror-who-are-you\audio\takes-seed123\meta.json",encoding="utf-8"))
shots=m["shots"]
total=0
for k in sorted(shots.keys()):
    s=shots[k]
    total+=s["audio_s"]
    print(f"{k}\t{s['audio_s']:.2f}\t{s['text']}")
print("TOTAL", round(total,2), "count", len(shots))
