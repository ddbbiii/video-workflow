import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import {simulate} from './model.mjs';
import {buildCamera} from '../renderers/canvas/camera.mjs';
const c=JSON.parse(await readFile(new URL('./config.json',import.meta.url)));
const diff=(a,b)=>Math.atan2(Math.sin(a-b),Math.cos(a-b));
const rows=[];
for(const seed of [...Array.from({length:100},(_,i)=>i+1),2026,c.seed]){
 const trace=simulate({...c,seed}),camera=buildCamera(trace);
 let offscreen=0,maxPenetration=0,maxGrazing=0,run=0;
 for(let i=0;i<trace.states.length;i++){
  const p=trace.states[i],scale=camera.samples[i],dist=Math.hypot(p.x,p.y),angle=Math.atan2(p.y,p.x);
  if((Math.abs(p.x)+c.ballRadius)*scale>c.width/2-12||(Math.abs(p.y)+c.ballRadius)*scale>c.height/2-12)offscreen++;
  let nearest=Infinity;
  const contact=c.ballRadius+c.thickness/2;
  const first=Math.max(p.consumed,Math.floor((dist-contact+p.offset-c.initialRadius)/c.spacing)-1);
  const last=Math.min(c.total-1,Math.ceil((dist+contact+p.offset-c.initialRadius)/c.spacing)+1);
  for(let id=first;id<=last;id++){
   const r=c.initialRadius+id*c.spacing-p.offset,shape=trace.shapes[id],ga=shape.phase+shape.speed*p.time,delta=diff(angle,ga);
   const a=Math.abs(delta)<shape.width/2?ga+Math.sign(delta||1)*shape.width/2:angle;
   nearest=Math.min(nearest,Math.hypot(p.x-r*Math.cos(a),p.y-r*Math.sin(a)));
  }
  maxPenetration=Math.max(maxPenetration,contact-nearest);
  const speed=Math.hypot(p.vx,p.vy),radial=(p.vx*p.x+p.vy*p.y)/Math.max(1,dist);
  run=nearest<contact+10&&Math.abs(radial)<speed*.3?run+1/c.fps:0;maxGrazing=Math.max(maxGrazing,run);
 }
 assert.equal(offscreen,0,`seed ${seed}: ball outside camera`);
 assert.ok(maxPenetration<.5,`seed ${seed}: penetration ${maxPenetration}`);
 for(const change of camera.changes)assert.ok(trace.events.some(e=>e.type==='pass'&&e.time===change.time&&e.id===change.id));
 for(let i=1;i<camera.samples.length;i++)assert.ok(camera.samples[i]<=camera.samples[i-1]+1e-9);
 const hits=trace.events.filter(e=>e.type==='bounce');
 const clearTurns=hits.filter(e=>(e.vx*e.vx_after+e.vy*e.vy_after)/(e.speed_before*e.speed_after)<Math.cos(Math.PI/4)).length;
 rows.push({seed,passes:trace.result.passes,bounces:hits.length,clearTurns,recovery:trace.events.filter(e=>e.type==='unstick').length,maxGrazingSeconds:maxGrazing,maxPenetration,offscreen,cameraStart:camera.samples[0],cameraEnd:camera.samples.at(-1),cameraTargets:camera.changes.length});
}
assert.equal(JSON.stringify(simulate(c)),await readFile(new URL('./trace.json',import.meta.url),'utf8'));
const report={checkedSeeds:rows.length,reproducible:true,allCameraChangesFollowPasses:true,maxPenetration:Math.max(...rows.map(r=>r.maxPenetration)),maxGrazingSeconds:Math.max(...rows.map(r=>r.maxGrazingSeconds)),current:rows.at(-1),seeds:rows};
await writeFile(new URL('../qa/physics.json',import.meta.url),JSON.stringify(report,null,2));
console.log(JSON.stringify({...report,seeds:undefined},null,2));
