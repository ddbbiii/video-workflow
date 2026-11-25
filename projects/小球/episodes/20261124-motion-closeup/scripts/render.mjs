import {chromium} from '../../20261122-escape-rings/renderers/pixi/node_modules/playwright/index.mjs';
import {createServer} from 'node:http';import {readFile,writeFile} from 'node:fs/promises';
import {spawn} from 'node:child_process';import {once} from 'node:events';import {fileURLToPath} from 'node:url';import path from 'node:path';
const root=fileURLToPath(new URL('../',import.meta.url));
const server=createServer(async(req,res)=>{try{const file=path.resolve(root,'.'+decodeURIComponent(req.url.split('?')[0]));if(!file.startsWith(root))throw Error('path');const data=await readFile(file);res.setHeader('Content-Type',path.extname(file)==='.html'?'text/html':'application/json');res.end(data);}catch{res.writeHead(404);res.end();}});
server.listen(0,'127.0.0.1');await once(server,'listening');const browser=await chromium.launch({headless:true});
try{
 const page=await browser.newPage({viewport:{width:1080,height:1920},deviceScaleFactor:1});const errors=[];page.on('pageerror',e=>errors.push(e.message));await page.goto(`http://127.0.0.1:${server.address().port}/scene.html`);
 for(const name of ['A','B','C']){
  await page.evaluate(name=>window.loadVariant(name),name);
  const encoder=spawn('ffmpeg',['-v','error','-y','-f','image2pipe','-vcodec','mjpeg','-framerate','60','-i','pipe:0','-frames:v','600','-an','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',path.join(root,`video/${name}.mp4`)],{stdio:['pipe','ignore','pipe']});let stderr='';encoder.stderr.on('data',b=>stderr+=b);const done=once(encoder,'close');
  for(let i=0;i<600;i++){
   const jpg=await page.evaluate(i=>{window.drawFrame(i);return document.querySelector('canvas').toDataURL('image/jpeg',.96).split(',')[1];},i);
   if(!encoder.stdin.write(Buffer.from(jpg,'base64')))await once(encoder.stdin,'drain');
   if(i%120===0)console.log(name,i);
  }
  encoder.stdin.end();const [code]=await done;if(code)throw Error(stderr);
  for(const frame of [0,180,360,540]){await page.evaluate(i=>window.drawFrame(i),frame);await page.locator('canvas').screenshot({path:path.join(root,`qa/${name}-${frame}.png`)});}
 }
 if(errors.length)throw Error(errors.join('\n'));await writeFile(path.join(root,'qa/render.json'),JSON.stringify({page_errors:errors,frames:600,fps:60,fixed_camera:true},null,2));
}finally{await browser.close();server.close();}
