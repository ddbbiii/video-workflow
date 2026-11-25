import{simulate}from'../simulation/model.mjs';
import{readFile,writeFile}from'node:fs/promises';
const baseline=JSON.parse(await readFile(new URL('../../20261124-rings-300-sfx/simulation/config.json',import.meta.url)));
const results=[];
for(const gravity of [0,80,140,220,240,320]){
 const trace=simulate({...baseline,gravity});
 const ss=trace.states.filter(s=>s.consumed<300),passes=trace.events.filter(e=>e.type==='pass');
 let previous=0,maxGap=0;for(const e of passes){maxGap=Math.max(maxGap,e.time-previous);previous=e.time;}
 results.push({gravity,complete:trace.result.complete,passes:trace.result.passes,completeTime:trace.result.completeTime,
  bounces:trace.result.bounces,maxGrazingDuration:trace.result.maxGrazingDuration,postSolvePenetration:trace.result.postSolvePenetration,
  lower_half_fraction:ss.filter(s=>s.y>0).length/ss.length,
  inner_area_fraction:ss.filter(s=>Math.hypot(s.x,s.y)<(225+s.consumed*10-s.offset)*.55).length/ss.length,
  maximum_speed:Math.max(...ss.map(s=>Math.hypot(s.vx,s.vy))),maximum_pass_gap_seconds:maxGap});
}
await writeFile(new URL('../qa/gravity-comparison.json',import.meta.url),JSON.stringify({selected_gravity:240,units:'scene coordinate units per second squared, +y down',same_initial_state:true,only_changed_parameter:'gravity',speedRelaxation:2,candidates:results,scope:'Single fixed initial state, not a multi-seed stability guarantee.'},null,2));
console.log(results);
