"""Three-body 2D preview: convex silhouettes, real contacts, continuous sampling.

Independent of the deprecated track animation. No hold/release, pair-specific
forces, or post-contact trajectory edits. Coordinates use screen Y down.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
import subprocess
import wave

import numpy as np
import pymunk
from PIL import Image, ImageDraw, ImageFilter

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "out" / "ellipse_v3"
HZ = 480
FPS = 60


@dataclass
class Config:
    radii: tuple = (34., 43., 54.)
    aspect: float = .835
    width: float = 230.
    height: float = 165.
    edge_margin: float = 3.
    push: float = 245.
    gravity: float = 750.
    friction: float = .85
    elasticity: float = .55
    mass_power: float = 2.
    duration: float = 8.
    start_lead: float = 24.
    receiver_frac: float = .78
    receiver_fracs: tuple = ()


def world(c):
    s = pymunk.Space()
    s.gravity = (0, c.gravity)
    s.iterations = 35
    s.collision_slop = .15
    s.damping = .999
    stairs = []
    for i in range(4):
        left, right, y = 90+i*c.width, 90+(i+1)*c.width, 400+i*c.height
        if i == 3:
            right += 250
        seg = pymunk.Segment(s.static_body, (left, y), (right, y), 1.2)
        seg.friction, seg.elasticity, seg.collision_type = c.friction, .3, 2
        seg.step_id = i
        s.add(seg)
        stairs.append(((left,y),(right,y)))
        if i < 3:
            seg = pymunk.Segment(s.static_body,(right,y),(right,y+c.height),1.2)
            seg.friction, seg.elasticity, seg.collision_type = c.friction,.3,3
            s.add(seg)
            stairs.append(((right,y),(right,y+c.height)))
    bodies, shapes = [], []
    for i,r in enumerate(c.radii):
        verts = [(r*math.cos(2*math.pi*j/40), r*c.aspect*math.sin(2*math.pi*j/40)) for j in range(40)]
        mass=(r/c.radii[0])**c.mass_power
        b=pymunk.Body(mass,pymunk.moment_for_poly(mass,verts))
        x=90+(i+1)*c.width-c.edge_margin
        if i == 0:
            x=90+c.width-r*c.aspect-c.start_lead
        else:
            frac=c.receiver_fracs[i-1] if c.receiver_fracs else c.receiver_frac
            x=90+i*c.width+frac*c.width
        b.position=(x,400+i*c.height-r*c.aspect-1.2)
        sh=pymunk.Poly(b,verts)
        sh.friction,sh.elasticity,sh.collision_type=c.friction,c.elasticity,1
        sh.body_id=i
        s.add(b,sh)
        bodies.append(b)
        shapes.append(sh)
    return s,bodies,shapes,stairs


def simulate(c, retain=True):
    s,bs,shs,stairs=world(c)
    clock=0.
    hits=[]
    landings=[]
    min_pen=0.
    last={}
    def contact(arb,space,data):
        nonlocal min_pen
        a,b=arb.shapes
        pair=tuple(sorted((a.body_id,b.body_id)))
        j=arb.total_impulse.length
        if j > .8 and clock-last.get(pair,-100) > .25:
            normal=tuple(arb.normal)
            hits.append(dict(t=clock,pair=pair,impulse=j,
                             point=tuple(arb.contact_point_set.points[0].point_a),normal=normal))
            last[pair]=clock
        for p in arb.contact_point_set.points:
            min_pen=min(min_pen,p.distance)
    def landed(arb,space,data):
        nonlocal min_pen
        a,b=arb.shapes
        if a.collision_type != 1:
            a,b=b,a
        pair=(a.body_id,b.step_id)
        if pair not in [x["pair"] for x in landings]:
            landings.append(dict(pair=pair,t=clock,impact=arb.total_impulse.length))
        for p in arb.contact_point_set.points:
            min_pen=min(min_pen,p.distance)
    s.on_collision(1,1,post_solve=contact)
    s.on_collision(1,2,post_solve=landed)
    # Settle initial contact; record drift before the one initial push.
    for _ in range(240):
        s.step(1/HZ)
    rest=np.array([tuple(b.position) for b in bs])
    for _ in range(240):
        s.step(1/HZ)
    drift=float(np.max(np.linalg.norm(np.array([tuple(b.position) for b in bs])-rest,axis=1)))
    initial=np.array([tuple(b.position) for b in bs])
    hits.clear();landings.clear();last.clear();min_pen=0.
    bs[0].velocity=(c.push,0)
    bs[0].angular_velocity=c.push/(c.radii[0]*c.aspect)
    trace=[]
    maxspeed=0.
    for k in range(round(c.duration*HZ)+1):
        clock=k/HZ
        if retain:
            trace.append([[b.position.x,b.position.y,b.angle,b.velocity.x,b.velocity.y,b.angular_velocity] for b in bs])
        maxspeed=max(maxspeed,max(b.velocity.length for b in bs))
        s.step(1/HZ)
    pairs=set(tuple(h['pair']) for h in hits)
    first=[next((h['t'] for h in hits if h['pair']==p),None) for p in [(0,1),(1,2)]]
    skips=[x["pair"] for x in landings if x["pair"][1]>x["pair"][0]+1]
    landing_match=[]
    for i,t in enumerate(first):
        candidates=[x for x in landings if x["pair"]==(i,i+1)]
        lt=min((x["t"] for x in candidates),key=lambda x:abs(x-t),default=None) if t is not None else None
        landing_match.append(dict(pair=[i,i+1],hit=t,landing=lt,
                                  delta=abs(lt-t) if lt is not None else None))
    final=np.array([tuple(b.position) for b in bs])
    sep=[]
    for h in hits:
        a,b=h['pair']
        if not retain:
            break
        kk=min(len(trace)-1,round((h['t']+.22)*HZ))
        # SAT on recorded vertices; no mutation of a live/cached physics shape.
        polys=[]
        for j in (a,b):
            x,y,angle=trace[kk][j][:3]
            ca,sa=math.cos(angle),math.sin(angle)
            verts=np.array([tuple(v) for v in shs[j].get_vertices()])
            polys.append(verts@np.array([[ca,sa],[-sa,ca]])+np.array([x,y]))
        axes=[]
        for poly in polys:
            edges=np.roll(poly,-1,axis=0)-poly
            axes.extend(np.stack([-edges[:,1],edges[:,0]],axis=1))
        gap=-1e9
        for axis in axes:
            axis=axis/np.linalg.norm(axis)
            pa,pb=polys[0]@axis,polys[1]@axis
            gap=max(gap,float(max(pb.min()-pa.max(),pa.min()-pb.max())))
        sep.append(dict(pair=h['pair'],t=h['t'],separated_220ms=gap>0,gap_axis_px=gap))
    report=dict(config=asdict(c),initial_positions=initial.tolist(),idle_drift=drift,
                impacts=hits,landings=landings,first_hits=first,landing_hit_delta=landing_match,skipped_treads=skips,
                max_penetration=min_pen,max_speed=maxspeed,final_positions=final.tolist(),
                separation=sep,assistance='none; initial push only')
    report['pass']=bool(pairs=={(0,1),(1,2)} and all(x is not None for x in first)
                        and first[0]<first[1] and not skips and min_pen > -1.5 and drift<.5
                        and np.linalg.norm(final[2]-initial[2])>30)
    if retain:
        report['pass']=report['pass'] and all(x['separated_220ms'] for x in sep)
        report['pre_contact_drift']=[float(np.max(np.linalg.norm(
            np.asarray(trace)[:max(1,int(first[i-1]*HZ)-1),i,:2]-initial[i],axis=1)))
            if first[i-1] is not None else None for i in (1,2)]
        report['pass']=report['pass'] and all(v is not None and v<.5 for v in report['pre_contact_drift'])
    return report,np.array(trace),stairs


def search():
    rng=np.random.default_rng(26)
    candidates=[]
    for n in range(420):
        c=Config(width=float(rng.choice([200,220,240,260])),height=float(rng.choice([130,150,170,190])),
                 edge_margin=float(rng.choice([2,4,8])),push=float(rng.choice([250,300,350,400])),
                 gravity=float(rng.choice([900,1100,1300,1500])),elasticity=float(rng.choice([.45,.55,.68])),
                 duration=4.,start_lead=float(rng.choice([12,24,36])),
                 receiver_frac=float(rng.choice([.60,.66,.72,.78,.84])))
        r,tr,_=simulate(c,True)
        if r['pass']:
            t0,t1=r['first_hits']
            angles=[abs(math.degrees(sample(tr,t+.42)[i,2]-sample(tr,t-.02)[i,2]))
                    for i,t in ((1,t0),(2,t1))]
            deltas=[x["delta"] for x in r["landing_hit_delta"]]
            normals=[abs(h['normal'][0]) for h in r['impacts'] if tuple(h['pair']) in [(0,1),(1,2)]]
            if min(angles)<20 or t0>1.1 or t1>2.3 or t1-t0>1.5 or any(d is None or d>.2 for d in deltas):
                continue
            impulses=[h["impulse"] for h in r["impacts"] if tuple(h["pair"]) in [(0,1),(1,2)]]
            score=abs(t0-.65)+abs((t1-t0)-.9)+max(0,t1-1.6)*2-sum(impulses)/5000+sum(deltas)*.2+sum(normals)*.35-min(angles)/150
            r["receiver_rotation_420ms_degrees"]=angles
            candidates.append((score,c,r))
        if n%70==0:
            print('search',n,'valid',len(candidates),flush=True)
    candidates.sort(key=lambda p:p[0])
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'search.json').write_text(json.dumps([dict(score=x[0],**x[2]) for x in candidates[:10]],indent=2),encoding='utf-8')
    if not candidates:
        raise RuntimeError('No passing scene; inspect geometry before rendering')
    (OUT/'config.json').write_text(json.dumps(asdict(candidates[0][1]),indent=2),encoding='utf-8')
    print('selected',asdict(candidates[0][1]),candidates[0][2]['first_hits'],flush=True)


def smooth(x):
    x=np.clip(x,0,1)
    return x*x*x*(x*(x*6-15)+10)


def source_times(events,end):
    # Apply a short 0.85x window after each measured impact.
    ts=np.arange(0,end+1/HZ,1/HZ)
    rate=np.ones_like(ts)
    for h in events:
        age=ts-h['t']
        envelope=smooth((age+.04)/.08)*(1-smooth((age-.28)/.12))
        rate=np.minimum(rate,1-.15*envelope)
    out=np.r_[0,np.cumsum((1/rate[:-1]+1/rate[1:])*.5/HZ)]
    times=np.arange(0,out[-1],1/FPS)
    return times,np.interp(times,out,ts),ts,out


def sample(tr,t):
    x=np.clip(t*HZ,0,len(tr)-1)
    i=min(int(x),len(tr)-2)
    return tr[i]*(1-(x-i))+tr[i+1]*(x-i)


def render(c,report,tr,stairs):
    W,H=1080,1920
    events=[]
    for pair in [(0,1),(1,2)]:
        events.append(next(h for h in report['impacts'] if tuple(h['pair'])==pair))
    end=min(c.duration,events[-1]['t']+1.35)
    times,src,st,ot=source_times(events,end)
    report['output_duration']=len(times)/FPS
    report['slow_motion']='0.85x short impact windows; 480Hz simulation continuously sampled at 60fps'
    report['output_impact_times']=[float(np.interp(h['t'],st,ot)) for h in events]
    asset=Image.open(BASE/'assets/potato.png').convert('RGBA')
    asset=asset.crop(asset.getbbox())
    # Same ellipse envelope for visible silhouette and collision proxy.
    mask=Image.new('L',asset.size)
    ImageDraw.Draw(mask).ellipse((1,1,asset.width-2,asset.height-2),fill=255)
    asset.putalpha(Image.fromarray(np.minimum(np.array(asset.getchannel('A')),np.array(mask))))
    yy,xx=np.mgrid[0:H,0:W]
    vignette=np.clip(1-((xx-W*.46)/(W*.9))**2-((yy-H*.43)/(H*.9))**2,0,1)
    bg=np.zeros((H,W,3),dtype=np.uint8)
    for j,(base,extra) in enumerate([(10,10),(9,8),(13,7)]):
        bg[:,:,j]=base+vignette*extra
    bg=Image.fromarray(bg)
    proc=subprocess.Popen(['ffmpeg','-y','-v','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}',
         '-r',str(FPS),'-i','-','-an','-c:v','h264_nvenc','-preset','p5','-cq','19','-pix_fmt','yuv420p',
         '-movflags','+faststart',str(OUT/'silent.mp4')],stdin=subprocess.PIPE)
    first=events[0]['t']
    # World-space camera path: wide opening, gradual follow of the next contact.
    centers=[np.array([90+c.width*1.50,400+c.height*.92]),
             np.array(events[0]['point'])+[-5,35],np.array(events[1]['point'])+[10,40]]
    sample_frames=[]
    for fi,(out_t,t) in enumerate(zip(times,src)):
        state=sample(tr,float(t))
        opening=float(smooth((t-.45)/max(.3,first+.15-.45)))
        progress=float(smooth((t-events[0]['t']-.2)/max(.4,events[1]['t']-events[0]['t']-.15)))
        center=centers[0]*(1-opening)+(centers[1]*(1-progress)+centers[2]*progress)*opening
        z=1.55+.58*opening+.12*progress
        # Follow final receiver after the second impact, keeping the landing in view.
        tail=float(smooth((t-events[1]['t']-.25)/1.4))
        target=np.array([state[2,0]+30,state[2,1]-10])
        center=center*(1-tail*.62)+target*tail*.62
        roll=.09
        shake_x=shake_y=0.
        for h in events:
            age=t-h['t']
            if age>=0:
                envelope=math.exp(-age/.105)
                kick=min(1.5,h['impulse']/180)
                shake_x+=math.sin(age*115)*29*kick*envelope
                shake_y+=math.sin(age*83+1.1)*20*kick*envelope
                roll+=.045*math.sin(age*48)*math.exp(-age/.16)*kick
        cr,sr=math.cos(roll),math.sin(roll)
        def screen(p):
            x,y=np.asarray(p)-center
            return ((cr*x-sr*y)*z+W*.5+shake_x,(sr*x+cr*y)*z+H*.48+shake_y)
        im=bg.copy().convert('RGBA')
        # A dark stair side creates a readable ledge without changing the clean style.
        d=ImageDraw.Draw(im,'RGBA')
        for a,b in stairs:
            if a[1]==b[1]:
                poly=[screen(a),screen(b),screen((b[0],b[1]+12)),screen((a[0],a[1]+12))]
                d.polygon(poly,fill=(36,32,39,255))
            d.line([screen(a),screen(b)],fill=(222,220,218,255),width=4)
        # Contact shadows track actual support distance, rather than pasted glows.
        shadows=Image.new('RGBA',(W,H))
        sd=ImageDraw.Draw(shadows)
        for i,r in enumerate(c.radii):
            x,y,a=state[i,:3]
            step=int(np.clip((x-90)//c.width,0,3))
            floor=400+step*c.height
            support=r*math.sqrt(math.sin(a)**2+c.aspect**2*math.cos(a)**2)
            gap=max(0,floor-y-support-1.2)
            if gap<110:
                sx,sy=screen((x,floor+3))
                rx=r*z*(.65+.002*gap)
                sd.ellipse((sx-rx,sy-7,sx+rx,sy+7),fill=(0,0,0,int(100*math.exp(-gap/45))))
        im.alpha_composite(shadows.filter(ImageFilter.GaussianBlur(5)))
        for i,r in enumerate(c.radii):
            x,y,angle=state[i,:3]
            squash=1.
            stretch=1.
            for h in events:
                if i in h['pair']:
                    age=t-h['t']
                    if 0<=age<.16:
                        amount=min(.34,h['impulse']/760)*math.exp(-age/.06)
                        squash=min(squash,1.-amount)
                        stretch=max(stretch,1.+amount*.8)
            sprite=asset.resize((round(2*r*z*squash),round(2*r*c.aspect*z*stretch)),Image.Resampling.LANCZOS)
            sprite=sprite.rotate(-math.degrees(angle+roll),resample=Image.Resampling.BICUBIC,expand=True)
            sx,sy=screen((x,y))
            im.alpha_composite(sprite,(round(sx-sprite.width/2),round(sy-sprite.height/2)))
        fx=Image.new('RGBA',(W,H))
        fd=ImageDraw.Draw(fx,'RGBA')
        for event_index,h in enumerate(events):
            age=t-h['t']
            if 0<=age<.24:
                px,py=screen(h['point'])
                fade=(1-age/.24)**1.5
                ring_r=(8+age*230)*z
                fd.ellipse((px-ring_r,py-ring_r*.72,px+ring_r,py+ring_r*.72),
                           outline=(255,221,170,int(170*fade)),width=3)
                rng=np.random.default_rng(260+event_index)
                for j in range(14):
                    theta=-math.pi/2+(j/13-.5)*2.35
                    speed=105+float(rng.random())*150
                    dx=math.cos(theta)*speed*age
                    dy=math.sin(theta)*speed*age+170*age*age
                    radius=(1.5+float(rng.random())*3.5)*z*(.55+fade*.45)
                    alpha=int(210*fade)
                    fd.ellipse((px+dx-radius,py+dy-radius,px+dx+radius,py+dy+radius),
                               fill=(238,192,129,alpha))
        im.alpha_composite(fx)
        rgb=im.convert('RGB')
        proc.stdin.write(rgb.tobytes())
        if fi%120==0:
            print('render',fi,'/',len(times),flush=True)
        if any(abs(t-h['t']-.10)<1/FPS for h in events) or fi==0:
            if len(sample_frames)<5:
                sample_frames.append((fi,rgb.resize((270,480))))
    proc.stdin.close()
    if proc.wait()!=0:
        raise RuntimeError('encode failed')
    sheet=Image.new('RGB',(270*len(sample_frames),480))
    for j,(_,im) in enumerate(sample_frames):
        sheet.paste(im,(j*270,0))
    sheet.save(OUT/'preview_sheet.jpg',quality=88)
    np.savez_compressed(OUT/'trace.npz',state=tr,hz=HZ)
    (OUT/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')


def add_audio():
    """Punchy, short synthetic impacts triggered by measured contacts."""
    report=json.loads((OUT/'report.json').read_text())
    sr=48000
    mix=np.zeros((math.ceil(report['output_duration']*sr),2),dtype=np.float64)
    for j,t in enumerate(report['output_impact_times']):
        u=np.arange(round(.65*sr))/sr
        rate=.75
        freq=(95-35*(1-np.exp(-u*16)))*rate/(1+.12*j)
        phase=2*np.pi*np.cumsum(freq)/sr
        body=np.sin(phase)*np.exp(-u*11)
        ring=np.sin(2*np.pi*(180-45*(1-np.exp(-u*7)))*rate*u)*np.exp(-u*9)*.3
        noise=np.random.default_rng(26+j).normal(0,1,len(u))
        snap=noise*np.exp(-u*180)*.20
        texture=noise*np.exp(-u*65)*.075
        hit=(body*1.45+ring*1.15+snap+texture)*np.minimum(u/.0015,1)*.76
        start=round(t*sr)
        n=min(len(hit),len(mix)-start)
        # Stereo position follows the broadly central contact; no hard panning.
        mix[start:start+n,0]+=hit[:n]*(.9 if j else 1.)
        mix[start:start+n,1]+=hit[:n]*(1. if j else .9)
    with wave.open(str(OUT/'impacts.wav'),'wb') as f:
        f.setnchannels(2);f.setsampwidth(2);f.setframerate(sr)
        f.writeframes((np.clip(mix,-.95,.95)*32767).astype('<i2').tobytes())
    subprocess.run(['ffmpeg','-y','-v','error','-i',str(OUT/'silent.mp4'),'-i',str(OUT/'impacts.wav'),
                    '-c:v','copy','-c:a','aac','-b:a','192k','-shortest','-movflags','+faststart',
                    str(OUT/'potato_ellipse_v2.mp4')],check=True)
    report['audio']='synthetic impact placeholders; not the final potato vocal'
    (OUT/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--search',action='store_true')
    ap.add_argument('--simulate-only',action='store_true')
    args=ap.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    if args.search:
        search()
    c=Config(**json.loads((OUT/'config.json').read_text())) if (OUT/'config.json').exists() else Config()
    r,tr,stairs=simulate(c)
    print(json.dumps({k:v for k,v in r.items() if k!='config'},indent=2),flush=True)
    (OUT/'report.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
    if not r['pass']:
        raise RuntimeError('Physics gates did not pass')
    if not args.simulate_only:
        render(c,r,tr,stairs)
        add_audio()


if __name__=='__main__':
    main()
