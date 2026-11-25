import {simulate} from '../simulation/model.mjs';
import {writeFile} from 'node:fs/promises';
const common={width:1080,height:1920,fps:60,physicsHz:1200,total:1000,seed:1873287513,initialGapPhase:2,
 startRadius:60,initialRadius:225,minimumRadius:205,spacing:10,thickness:2.4,ballRadius:10,
 squareSide:18,speed:430,feedSpeed:35,angularSpeed:.42,gapWidth:.68,phasePerLayer:.1,
 phaseWave:0,phaseFrequency:.35,maxDuration:10,center:{x:540,y:960},viewScale:1.85,
 gravity:0,linearDrag:0,restitution:1,friction:0,speedDrag:0,speedRelaxation:0,arcadeRecovery:false};
const variants={A:{total:6,feedSpeed:0,spacing:18,phasePerLayer:.3},B:{},C:{phaseWave:-.3}};
const report={};
for(const [name,changes]of Object.entries(variants)){
 const trace=simulate({...common,...changes});
 // Exactly 600 rendered frames; the final boundary state remains available for interpolation.
 const hits=trace.events.filter(e=>e.type==='bounce'),arc=hits.filter(e=>!e.endpoint);
 const turns=arc.map(e=>{const dot=e.vx*e.vx_after+e.vy*e.vy_after;return Math.acos(Math.max(-1,Math.min(1,dot/(e.speed_before*e.speed_after))))*180/Math.PI;});
 const radii=trace.states.map(s=>trace.config.initialRadius+s.consumed*trace.config.spacing-s.offset);
 let inside=0,wall=0,minR=Infinity,maxR=0;
 for(const s of trace.states){const r=Math.hypot(s.x,s.y),active=trace.config.initialRadius+s.consumed*trace.config.spacing-s.offset;minR=Math.min(minR,r);maxR=Math.max(maxR,r);if(r<active*.55)inside++;if(r>active*.85)wall++;}
 const metrics={...trace.result,arc_bounces:arc.length,endpoint_bounces:hits.length-arc.length,
  turns_degrees:turns,large_arc_turns:turns.filter(x=>x>60).length,
  inner_area_fraction:inside/trace.states.length,near_wall_fraction:wall/trace.states.length,
  radial_range:[minR,maxR],active_radius_range:[Math.min(...radii),Math.max(...radii)],
  ball_diameter_pixels:common.ballRadius*2*common.viewScale,
  active_diameter_fraction_width:[Math.min(...radii),Math.max(...radii)].map(r=>2*r*common.viewScale/common.width),
  ball_outside_frame:trace.states.filter(s=>Math.abs(s.x)*common.viewScale+common.ballRadius*common.viewScale>540||Math.abs(s.y)*common.viewScale+common.ballRadius*common.viewScale>960).length};
 report[name]=metrics;
 await writeFile(new URL(`../simulation/${name}.json`,import.meta.url),JSON.stringify(trace));
 console.log(name,JSON.stringify(metrics));
}
await writeFile(new URL('../qa/motion.json',import.meta.url),JSON.stringify(report,null,2));
