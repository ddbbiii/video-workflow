from render_images import *
p=EP/'image/final/S19A.png';original=EP/'qa/S19A-before-prop-repair.png'
if not original.exists():shutil.copyfile(p,original)
# Tighten framing on the actual writing action; the unintended extra family print is entirely outside delivered crop.
im=Image.open(original);im.crop((150,0,1892,980)).resize((2048,1152),Image.Resampling.LANCZOS).save(p)
m=json.loads(MANIFEST.read_text());m['S19A'].update(derived_edit='crop [150,0,1892,980] excludes unintended incidental portrait; writing action and notebook retained',file=str(p.relative_to(EP)),sha256=hashlib.sha256(p.read_bytes()).hexdigest());MANIFEST.write_text(json.dumps(m,ensure_ascii=False,indent=2))
