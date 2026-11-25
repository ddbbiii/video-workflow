const TAU=Math.PI*2;
const diff=(a,b)=>Math.atan2(Math.sin(a-b),Math.cos(a-b));
export function randomGenerator(seed){let a=seed>>>0;return()=>{a+=0x6D2B79F5;let t=a;t=Math.imul(t^t>>>15,t|1);t^=t+Math.imul(t^t>>>7,t|61);return((t^t>>>14)>>>0)/4294967296;};}
export function initialState(c){
 const random=randomGenerator(c.seed),r=Math.sqrt(random())*c.startRadius,a=random()*TAU;
 return {x:r*Math.cos(a),y:r*Math.sin(a),heading:random()*TAU,phase:random()*TAU};
}
export function ringShape(c,id){
 return {phase:c.phase+id*c.phasePerLayer+0.10*Math.sin(id*.035),
 speed:c.angularSpeed,width:c.gapWidth*(1+.06*Math.sin(id*.027))};
}
export function simulate(input){
 for(const key of ['width','height','fps','physicsHz','total','seed','startRadius','initialRadius','minimumRadius','spacing','thickness','ballRadius','squareSide','speed','feedSpeed','angularSpeed','gapWidth','phasePerLayer','maxDuration'])if(!Number.isFinite(input[key]))throw new Error(`设置缺少有效数值：${key}`);
 if(!Number.isInteger(input.total)||input.total<1||input.total>5000)throw new Error('层数须为 1–5000 的整数');
 if(!Number.isInteger(input.seed)||input.seed<0||input.seed>4294967295)throw new Error('开局编号须为 0–4294967295 的整数');
 if(input.speed<=0||input.feedSpeed<=0||input.physicsHz<=0||input.fps<=0||input.maxDuration<=0)throw new Error('速度、帧率和最长时间须大于零');
 if(input.gapWidth<=0||input.gapWidth>=Math.PI*2)throw new Error('缺口宽度须在 0–360 度之间');
 if(input.startRadius<0||input.startRadius+input.ballRadius+input.thickness/2>=input.initialRadius)throw new Error('随机起点范围必须完整位于初始内圈');
 if(input.minimumRadius<=input.ballRadius+input.thickness||input.spacing<=input.thickness)throw new Error('内圈半径或层间距过小');
 const c={...input},start=initialState(c);c.phase=start.phase;
 const dt=1/c.physicsHz,contact=c.ballRadius+c.thickness/2;
 const shapes=Array.from({length:c.total},(_,id)=>ringShape(c,id));
 let {x,y}=start,vx=Math.cos(start.heading)*c.speed,vy=Math.sin(start.heading)*c.speed;
 let consumed=0,offset=0,lastHit=-1,completeTime=null,minClearance=Infinity,maxPenetration=0,omega=0,rotation=0,previousContact=-1,grazeCount=0,lastUnstick=-Infinity;
 const states=[],events=[],crossings=new Map();
 const substeps=c.physicsHz/c.fps;if(!Number.isInteger(substeps))throw new Error('物理步数必须能整除帧率');
 for(let step=0;step<=c.maxDuration*c.physicsHz;step++){
  const t=step*dt;
  const oldOffset=offset,oldX=x,oldY=y;
  if(step>0 && consumed<c.total)offset=Math.min(offset+c.feedSpeed*dt,c.initialRadius+consumed*c.spacing-c.minimumRadius);
  const inward=(offset-oldOffset)/dt;
  if(step>0){
    const damping=Math.exp(-(c.linearDrag+c.speedDrag*Math.hypot(vx,vy))*dt);vx*=damping;vy=(vy+c.gravity*dt)*damping;
    // A continuous flight governor restores cruising speed gradually, never at impact.
    if(c.speedRelaxation>0){const speed=Math.hypot(vx,vy);if(speed>1e-6){const next=c.speed+(speed-c.speed)*Math.exp(-c.speedRelaxation*dt);vx*=next/speed;vy*=next/speed;}}
    x+=vx*dt;y+=vy*dt;rotation+=omega*dt;omega*=Math.exp(-.025*dt);
   }
  const impacted=new Set();
  for(let iteration=0;iteration<8;iteration++){
   const contacts=[];
   const dist=Math.hypot(x,y),angle=Math.atan2(y,x);
   const first=Math.max(consumed,Math.floor((dist-contact+offset-c.initialRadius)/c.spacing)-1);
   const last=Math.min(c.total-1,Math.ceil((dist+contact+offset-c.initialRadius)/c.spacing)+1);
   for(let id=first;id<=last;id++){
    const r=c.initialRadius+id*c.spacing-offset;
    const shape=shapes[id],ga=shape.phase+shape.speed*t,delta=diff(angle,ga),half=shape.width/2;
    const endpoint=Math.abs(delta)<half;
    const a=endpoint?ga+Math.sign(delta||1)*half:angle;
    const px=r*Math.cos(a),py=r*Math.sin(a),dx=x-px,dy=y-py,d=Math.hypot(dx,dy);
    if(d>=contact)continue;
    const nx=d>1e-8?dx/d:-Math.cos(a),ny=d>1e-8?dy/d:-Math.sin(a);
    // A rotating endpoint sweeps through space; include its tangential velocity.
    // On an arc interior only radial motion changes the geometric surface.
    const turn=endpoint?shape.speed*r:0;
    const wx=-inward*Math.cos(a)-turn*Math.sin(a),wy=-inward*Math.sin(a)+turn*Math.cos(a);
    const approach=(vx-wx)*nx+(vy-wy)*ny;
    contacts.push({id,nx,ny,d,wx,wy,endpoint,approach,order:approach<0?-(contact-d)/(-approach):0});
   }
   if(!contacts.length)break;
   contacts.sort((a,b)=>a.order-b.order);
   // Resolve the contact manifold repeatedly; restitution is applied once per
   // surface per substep, preventing repeated elastic impulses in a tight corner.
   for(const hit of contacts){
    const {id,nx,ny,d,wx,wy,endpoint}=hit;
    x+=nx*(contact-d+0.001);y+=ny*(contact-d+0.001);
    const approach=(vx-wx)*nx+(vy-wy)*ny;
    if(approach<0){
     const before={vx,vy};
     const normalImpulse=-(1+(impacted.has(id)?0:c.restitution))*approach;
     impacted.add(id);
     vx+=normalImpulse*nx;vy+=normalImpulse*ny;
     const tx=-ny,ty=nx,slip=(vx-wx)*tx+(vy-wy)*ty-omega*c.ballRadius;
     const tangentialImpulse=Math.max(-c.friction*normalImpulse,Math.min(c.friction*normalImpulse,-slip/3));
     vx+=tangentialImpulse*tx;vy+=tangentialImpulse*ty;omega-=2*tangentialImpulse/c.ballRadius;
     const rx=vx-wx,ry=vy-wy,relativeSpeed=Math.hypot(rx,ry),out=rx*nx+ry*ny;
     if(t-previousContact<.2 && out<relativeSpeed*.25)grazeCount++;else grazeCount=0;
     previousContact=t;
     // Only sustained grazing enables the arcade fallback. Ordinary endpoint
     // contacts retain their physical reflected direction.
     if(c.arcadeRecovery!==false && (grazeCount>=4) && t-lastUnstick>.18 && relativeSpeed>1){
       const radial=Math.hypot(x,y),ix=-x/radial,iy=-y/radial;
       const tangentSign=Math.sign(vx*(-iy)+vy*ix||1),speed=Math.hypot(vx,vy);
       const inwardSpeed=speed*.7,tangentSpeed=tangentSign*speed*Math.sqrt(1-.7**2);
       vx=inwardSpeed*ix-tangentSpeed*iy;vy=inwardSpeed*iy+tangentSpeed*ix;
       events.push({type:'unstick',time:t,id,x,y});grazeCount=0;lastUnstick=t;
     }
     if(t-lastHit>0.025){events.push({type:'bounce',time:t,id,x,y,nx,ny,endpoint,wallVx:wx,wallVy:wy,...before,vx_after:vx,vy_after:vy,approach,normalImpulse,omega,speed_before:Math.hypot(before.vx,before.vy),speed_after:Math.hypot(vx,vy)});lastHit=t;}
    }
   }
  }
  // Validate the opening when the centre crosses the ring, not later when the
  // trailing edge clears it: a rotating opening may already have moved by then.
  const radialStart=Math.hypot(oldX,oldY)+oldOffset-c.initialRadius;
  const radialEnd=Math.hypot(x,y)+offset-c.initialRadius;
  if(radialEnd>radialStart){
   for(let id=Math.max(consumed,Math.ceil(radialStart/c.spacing));id<=Math.min(c.total-1,Math.floor(radialEnd/c.spacing));id++){
    const u=Math.max(0,Math.min(1,(id*c.spacing-radialStart)/(radialEnd-radialStart)));
    const cx=oldX+(x-oldX)*u,cy=oldY+(y-oldY)*u,ct=t-dt+u*dt;
    const shape=shapes[id],r=c.initialRadius+id*c.spacing-(oldOffset+(offset-oldOffset)*u);
    const margin=shape.width/2-Math.abs(diff(Math.atan2(cy,cx),shape.phase+shape.speed*ct));
    const clearance=r*Math.sin(margin)-contact;
    if(margin<=0 || clearance < -1)throw new Error(`第 ${id+1} 层穿越实体边界，t=${ct.toFixed(3)}`);
    crossings.set(id,clearance);
   }
  }
  while(consumed<c.total && Math.hypot(x,y)>c.initialRadius+consumed*c.spacing-offset+contact){
   const r=c.initialRadius+consumed*c.spacing-offset,shape=shapes[consumed],ga=shape.phase+shape.speed*t;
   const clearance=crossings.get(consumed);
   if(clearance===undefined)throw new Error(`第 ${consumed+1} 层缺少有效缺口穿越记录`);
   crossings.delete(consumed);
   minClearance=Math.min(minClearance,clearance);
   events.push({type:'pass',time:t,id:consumed,radius:r,gap:ga,gapWidth:shape.width,x,y,clearance});consumed++;
   if(consumed===c.total){completeTime=t;events.push({type:'escape',time:t,x,y});}
  }
  if(step%substeps===0)states.push({time:t,x,y,vx,vy,consumed,offset,angle:rotation,omega});
  if(completeTime!==null && t>=completeTime+0.55)break;
  if(!Number.isFinite(x+y+vx+vy)||Math.hypot(x,y)>20000)throw new Error('运动数值超出有效范围');
 }

 c.duration=states.length/c.fps;
 const passes=events.filter(e=>e.type==='pass'),hits=events.filter(e=>e.type==='bounce');
 // Identify prolonged near-alignment with the moving opening, as a diagnostic.
 let maxAlignedSeconds=0,alignedSeconds=0;
 for(const s of states){
  const shape=shapes[Math.min(s.consumed,c.total-1)];const a=shape.phase+shape.speed*s.time;
  const delta=Math.abs(diff(Math.atan2(s.y,s.x),a));
  if(s.consumed<c.total&&delta<0.13){alignedSeconds+=1/c.fps;maxAlignedSeconds=Math.max(maxAlignedSeconds,alignedSeconds);}else alignedSeconds=0;
 }
 return {config:c,shapes,initial:start,states,events,result:{complete:consumed===c.total,passes:passes.length,bounces:hits.length,completeTime,minClearance,maxAlignedSeconds,firstBounce:hits[0]?.time,firstPass:passes[0]?.time}};
}
