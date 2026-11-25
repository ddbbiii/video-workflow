// Stateless source-time sampling keeps live playback, scrubbing and export identical.
export function collisionBounce(time,hits,options) {
  const identity={angle:0,normalScale:1,tangentScale:1};
  if(options.bounceEnabled===false)return identity;
  const strength=Math.max(0,Math.min(1,options.bounceStrength??.35));
  const duration=Math.max(.12,Math.min(.6,options.bounceDuration??.28));
  let chosen, displacement=0;
  for(const hit of hits){
    const age=time-hit.time;
    if(age<0||age>=duration)continue;
    const phase=age/duration;
    const pulse=Math.sin(phase*Math.PI*3)*Math.exp(-phase*4)*(1-phase);
    const value=pulse*Math.max(0,Math.min(1,hit.intensity));
    if(Math.abs(value)>Math.abs(displacement)){chosen=hit;displacement=value;}
  }
  if(!chosen)return identity;
  const scale=Math.exp(-displacement*strength*.42);
  return {angle:Math.atan2(chosen.normalY,chosen.normalX),normalScale:scale,tangentScale:1/scale};
}
