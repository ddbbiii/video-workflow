import json, urllib.request
obj = json.loads(urllib.request.urlopen("http://127.0.0.1:8188/object_info", timeout=30).read())
keys = [k for k in obj if "IPAdapter" in k or "ipadapter" in k.lower()]
print("\n".join(sorted(keys)[:40]))
for k in ["IPAdapterAdvanced", "IPAdapterStyleComposition", "IPAdapterModelLoader", "CLIPVisionLoader", "IPAdapter"]:
    if k in obj:
        print("====", k)
        print(json.dumps(obj[k]["input"], ensure_ascii=False)[:1200])
