import { chromium } from '../../../20261122-escape-rings/renderers/pixi/node_modules/playwright/index.mjs';
import { createServer } from 'node:http';
import { readFile,writeFile,mkdir,rm } from 'node:fs/promises';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
const root=fileURLToPath(new URL('../../',import.meta.url));
const cues=JSON.parse(await readFile(path.join(root,'audio/cues.json'),'utf8'));
const server=createServer(async(req,res)=>{try{const file=path.resolve(root,'.'+decodeURIComponent(req.url.split('?')[0]));if(!file.startsWith(root)){res.writeHead(403);res.end();return;}const data=await readFile(file);const ext=path.extname(file);res.setHeader('Content-Type',({'.html':'text/html','.json':'application/json','.wav':'audio/wav','.mjs':'text/javascript'})[ext]||'application/octet-stream');res.end(data);}catch{res.writeHead(404);res.end();}});
server.listen(0,'127.0.0.1');await once(server,'listening');
const browser=await chromium.launch({headless:true});
try{
  const page=await browser.newPage({viewport:{width:1080,height:1920},deviceScaleFactor:1});
  page.on('pageerror',e=>console.error(e));
  await page.goto(`http://127.0.0.1:${server.address().port}/renderers/canvas/index.html`);
  await page.waitForFunction(()=>window.__ready);
  const output=path.join(root,'video/candidates/ball-physics-test.mp4');
  const frames=Math.round(cues.duration*60);
  const encoder=spawn('ffmpeg',['-hide_banner','-loglevel','error','-y','-f','image2pipe','-vcodec','png','-framerate','60','-i','pipe:0','-i',path.join(root,'audio/pass-sfx.wav'),'-frames:v',String(frames),'-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-movflags','+faststart',output],{stdio:['pipe','ignore','pipe']});
  let errors='';encoder.stderr.on('data',x=>errors+=x);const done=once(encoder,'close');
  for(let i=0;i<frames;i++){
    const jpg=await page.evaluate(i=>{window.__drawFrame(i);return document.querySelector('canvas').toDataURL('image/png').split(',')[1];},i);
    if(!encoder.stdin.write(Buffer.from(jpg,'base64')))await once(encoder.stdin,'drain');
    if(i%120===0)console.log(`${i}/${frames}`);
  }
  encoder.stdin.end();const [code]=await done;if(code!==0)throw new Error(errors);
  for(const [name,t] of [['opening',0],['burst',cues.duration/2],['ending',cues.duration-0.1]]){
    const png=await page.evaluate(t=>{window.__drawTime(t);return document.querySelector('canvas').toDataURL('image/png').split(',')[1];},t);
    await writeFile(path.join(root,`qa/${name}.png`),png,'base64');
  }
  console.log(JSON.stringify({output,frames,duration:cues.duration}));
}finally{await browser.close();server.close();}
