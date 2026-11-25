const TAU=Math.PI*2;
const diff=(a,b)=>Math.atan2(Math.sin(a-b),Math.cos(a-b));
export function randomGenerator(seed){let a=seed>>>0;return()=>{a+=0x6D2B79F5;let t=a;t=Math.imul(t^t>>>15,t|1);t^=t+Math.imul(t^t>>>7,t|61);return((t^t>>>14)>>>0)/4294967296;};}
export function initialState(c){
 const random=randomGenerator(c.seed),r=Math.sqrt(random())*c.startRadius,a=random()*TAU;
 return {x:r*Math.cos(a),y:r*Math.sin(a),heading:random()*TAU,phase:random()*TAU};
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
 let {x,y}=start,vx=Math.cos(start.heading)*c.speed,vy=Math.sin(start.heading)*c.speed;
 let consumed=0,offset=0,lastHit=-1,completeTime=null,minClearance=Infinity,maxPenetration=0;
 const states=[],events=[];
 const substeps=c.physicsHz/c.fps;if(!Number.isInteger(substeps))throw new Error('物理步数必须能整除帧率');
 for(let step=0;step<=c.maxDuration*c.physicsHz;step++){
  const t=step*dt;
  const oldOffset=offset;
  if(step>0 && consumed<c.total)offset=Math.min(offset+c.feedSpeed*dt,c.initialRadius+consumed*c.spacing-c.minimumRadius);
  const inward=(offset-oldOffset)/dt;
  if(step>0){x+=vx*dt;y+=vy*dt;}
  for(let iteration=0;iteration<4;iteration++){
   const dist=Math.hypot(x,y),angle=Math.atan2(y,x);
   const first=Math.max(consumed,Math.floor((dist-contact+offset-c.initialRadius)/c.spacing)-1);
   const last=Math.min(c.total-1,Math.ceil((dist+contact+offset-c.initialRadius)/c.spacing)+1);
   for(let id=first;id<=last;id++){
    const r=c.initialRadius+id*c.spacing-offset;
    const ga=c.phase+c.angularSpeed*t+id*c.phasePerLayer,delta=diff(angle,ga),half=c.gapWidth/2;
    const a=Math.abs(delta)<half?ga+Math.sign(delta||1)*half:angle;
    const px=r*Math.cos(a),py=r*Math.sin(a),dx=x-px,dy=y-py,d=Math.hypot(dx,dy);
    if(d>=contact)continue;
    const nx=d>1e-8?dx/d:-Math.cos(a),ny=d>1e-8?dy/d:-Math.sin(a);
    x+=nx*(contact-d+0.001);y+=ny*(contact-d+0.001);
    // Gap rotation reveals/occludes boundary; it never injects tangential velocity.
    // Only radial feed contributes wall velocity, avoiding a conveyor dragging the ball.
    const wx=-inward*Math.cos(a),wy=-inward*Math.sin(a);
    const approach=(vx-wx)*nx+(vy-wy)*ny;
    if(approach<0){
     const before={vx,vy};vx-=2*approach*nx;vy-=2*approach*ny;
     const speed=Math.hypot(vx,vy);vx*=c.speed/speed;vy*=c.speed/speed;
     if(t-lastHit>0.025){events.push({type:'bounce',time:t,id,x,y,nx,ny,...before,vx_after:vx,vy_after:vy});lastHit=t;}
    }
   }
  }
  while(consumed<c.total && Math.hypot(x,y)>c.initialRadius+consumed*c.spacing-offset+contact){
   const r=c.initialRadius+consumed*c.spacing-offset,ga=c.phase+c.angularSpeed*t+consumed*c.phasePerLayer;
   const margin=c.gapWidth/2-Math.abs(diff(Math.atan2(y,x),ga));
   const clearance=r*Math.sin(margin)-contact;
   if(margin<=0||clearance< -1)throw new Error(`第 ${consumed+1} 层越过实体边界，t=${t.toFixed(3)}`);
   minClearance=Math.min(minClearance,clearance);
   events.push({type:'pass',time:t,id:consumed,radius:r,gap:ga,x,y,clearance});consumed++;
   if(consumed===c.total){completeTime=t;events.push({type:'escape',time:t,x,y});}
  }
  if(step%substeps===0)states.push({time:t,x,y,vx,vy,consumed,offset,angle:t*2.4});
  if(completeTime!==null && t>=completeTime+0.55)break;
  if(Math.hypot(x,y)>1250)throw new Error('主体离开有效画面范围');
 }
 if(consumed!==c.total)throw new Error(`未在 ${c.maxDuration} 秒内完成：${consumed}/${c.total}`);
 c.duration=states.length/c.fps;
 const passes=events.filter(e=>e.type==='pass'),hits=events.filter(e=>e.type==='bounce');
 // Identify prolonged near-alignment with the moving opening, as a diagnostic.
 let maxAlignedSeconds=0,alignedSeconds=0;
 for(const s of states){
  const a=c.phase+c.angularSpeed*s.time+s.consumed*c.phasePerLayer;
  const delta=Math.abs(diff(Math.atan2(s.y,s.x),a));
  if(s.consumed<c.total&&delta<0.13){alignedSeconds+=1/c.fps;maxAlignedSeconds=Math.max(maxAlignedSeconds,alignedSeconds);}else alignedSeconds=0;
 }
 return {config:c,initial:start,states,events,result:{complete:true,passes:passes.length,bounces:hits.length,completeTime,minClearance,maxAlignedSeconds,firstBounce:hits[0]?.time,firstPass:passes[0]?.time}};
}
