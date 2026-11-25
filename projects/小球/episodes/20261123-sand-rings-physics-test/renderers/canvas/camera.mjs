export function buildCamera(trace){
 const c=trace.config,passes=trace.events.filter(e=>e.type==='pass');
 let scale=1.45,target=scale,index=0,x=0,y=0;
 const samples=[],positions=[],changes=[];
 for(const state of trace.states){
  while(index<passes.length&&passes[index].time<=state.time){
   const e=passes[index++],extent=e.radius+c.ballRadius+110;
   if(extent*target>c.width*.38){
    const next=Math.max(c.minViewScale??.8,Math.min(target,c.width*.34/extent));
    if(next<target-.002){target=next;changes.push({time:e.time,id:e.id,target});}
   }
  }
  scale=target+(scale-target)*Math.exp(-1/(c.fps*.10));
  // Follow only outside a dead zone, reserving the outer frame for travel.
  const dx=state.x-x,dy=state.y-y,zoneX=c.width*.16/scale,zoneY=c.height*.19/scale;
  const tx=x+Math.sign(dx)*Math.max(0,Math.abs(dx)-zoneX),ty=y+Math.sign(dy)*Math.max(0,Math.abs(dy)-zoneY);
  const blend=1-Math.exp(-1/(c.fps*.09));x+=(tx-x)*blend;y+=(ty-y)*blend;
  samples.push(scale);positions.push({x,y});
 }
 return {samples,positions,changes};
}
export function cameraAt(camera,t,fps){const p=Math.max(0,Math.min(camera.samples.length-1,t*fps)),i=Math.floor(p),u=p-i;return camera.samples[i]*(1-u)+camera.samples[Math.min(i+1,camera.samples.length-1)]*u;}
export function cameraPositionAt(camera,t,fps){const p=Math.max(0,Math.min(camera.positions.length-1,t*fps)),i=Math.floor(p),u=p-i,a=camera.positions[i],b=camera.positions[Math.min(i+1,camera.positions.length-1)];return {x:a.x+(b.x-a.x)*u,y:a.y+(b.y-a.y)*u};}
