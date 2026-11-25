import {simulate} from '../simulation/model.mjs';
import {readFile,writeFile} from 'node:fs/promises';
const config=JSON.parse(await readFile(new URL('../simulation/config.json',import.meta.url)));
const trace=simulate(config);
if(!trace.result.complete||trace.result.passes!==300)throw Error('未完成全部300层');
const end=trace.result.completeTime;
const frames=Math.ceil((end+.65)*60),duration=frames/60;
// Fixed centre; smooth, precomputed framing follows extent, never ball direction.
const raw=trace.states.map(s=>{
 const active=s.consumed<300?config.initialRadius+s.consumed*config.spacing-s.offset:0;
 const extent=Math.max(active+config.ballRadius,Math.abs(s.x)+config.ballRadius,Math.abs(s.y)*1080/1920+config.ballRadius);
 return Math.min(1.85,1080*.43/extent);
});
// Limit per-second logarithmic zoom change; look ahead by propagating constraints
// backwards, so rapid bursts cannot push a ball out before the camera reacts.
const camera=[...raw],rate=.38/60;
for(let i=camera.length-2;i>=0;i--)camera[i]=Math.min(camera[i],camera[i+1]*Math.exp(rate));
for(let i=1;i<camera.length;i++)camera[i]=Math.min(camera[i],camera[i-1]*Math.exp(rate));
trace.camera=camera;trace.output={frames,duration,fps:60,width:1080,height:1920};
let outside=0,minBall=Infinity,maxBall=0,inside=0,near=0;let maxspeed=0;
for(let i=0;i<trace.states.length;i++){
 const s=trace.states[i],scale=camera[i],r=config.ballRadius;
 if(Math.abs(s.x)*scale+r*scale>540||Math.abs(s.y)*scale+r*scale>960)outside++;
 minBall=Math.min(minBall,2*r*scale);maxBall=Math.max(maxBall,2*r*scale);maxspeed=Math.max(maxspeed,Math.hypot(s.vx,s.vy));
 const active=config.initialRadius+s.consumed*config.spacing-s.offset,dist=Math.hypot(s.x,s.y);
 if(s.consumed<300){if(dist<active*.55)inside++;if(dist>active*.85)near++;}
}
const passes=trace.events.filter(e=>e.type==='pass'),hits=trace.events.filter(e=>e.type==='bounce');
if(outside||trace.result.postSolvePenetration>.01)throw Error('画面或碰撞检查失败');
if(passes.some((e,i)=>e.id!==i))throw Error('层号不连续');
let responseFailures=0;
for(const e of hits){const after=(e.vx_after-e.wallVx)*e.nx+(e.vy_after-e.wallVy)*e.ny;if(after<-.01)responseFailures++;}
if(responseFailures)throw Error('碰后未分离');
const qa={...trace.result,output:trace.output,passes:passes.length,arc_bounces:hits.filter(e=>!e.endpoint).length,
 endpoint_bounces:hits.filter(e=>e.endpoint).length,responseFailures,ball_outside_frames:outside,
 ball_diameter_px:[minBall,maxBall],camera_scale_range:[Math.min(...camera),Math.max(...camera)],
 maximum_speed:maxspeed,inner_area_fraction:inside/trace.states.length,near_wall_fraction:near/trace.states.length,
 per_ten_seconds:Array.from({length:Math.ceil(end/10)},(_,i)=>({start:i*10,passes:passes.filter(e=>e.time>=i*10&&e.time<(i+1)*10).length,bounces:hits.filter(e=>e.time>=i*10&&e.time<(i+1)*10).length}))};
await writeFile(new URL('../simulation/config.json',import.meta.url),JSON.stringify(config,null,2));
await writeFile(new URL('../simulation/trace.json',import.meta.url),JSON.stringify(trace));
await writeFile(new URL('../qa/physics.json',import.meta.url),JSON.stringify(qa,null,2));
console.log(JSON.stringify(qa,null,2));
