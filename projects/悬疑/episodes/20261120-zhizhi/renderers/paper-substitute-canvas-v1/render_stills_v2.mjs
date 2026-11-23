import {spawn} from 'node:child_process';
import {mkdir} from 'node:fs/promises';
import {join, resolve} from 'node:path';

const root=resolve(decodeURIComponent(new URL('.', import.meta.url).pathname));
const imageRoot=resolve(root,'../../image/final');
const output=resolve(root,'../../video/candidates/纸替_分层静帧运动_v3.mp4');
const ass=resolve(root,'paper-substitute-v2.ass');
const args=['-y'];
for(let i=1;i<=16;i++){args.push('-loop','1','-t','4.8','-i',join(imageRoot,`S${String(i).padStart(2,'0')}.png`))}
const filters=[];
for(let i=0;i<16;i++){
  const x=i%3===0?'iw*0.04':'iw*0.01';
  const y=i%3===1?'ih*0.03':'ih*0.01';
  filters.push(`[${i}:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080:${x}:${y},zoompan=z='min(zoom+0.0008,1.07)':d=1:s=1920x1080:fps=30,setsar=1[v${i}]`);
}
filters.push(`${Array.from({length:16},(_,i)=>`[v${i}]`).join('')}concat=n=16:v=1:a=0,eq=contrast=1.04:brightness=0.01:saturation=0.98:gamma=1.04,noise=alls=2:allf=t+u,subtitles='${ass.replaceAll("'","\\'")}'[v]`);
args.push('-filter_complex',filters.join(';'),'-map','[v]','-an','-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',output);
await mkdir(resolve(root,'../../video/candidates'),{recursive:true});
await new Promise((res,rej)=>{const p=spawn('/Users/mac/bin/ffmpeg',args,{stdio:'inherit'});p.on('exit',c=>c?rej(new Error(`ffmpeg exited ${c}`)):res())});
console.log(JSON.stringify({output,duration_s:64,width:1920,height:1080,fps:30}));
