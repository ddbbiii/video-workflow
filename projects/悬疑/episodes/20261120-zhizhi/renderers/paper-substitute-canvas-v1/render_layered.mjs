import { chromium } from 'playwright';
import { mkdir, rm } from 'node:fs/promises';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawn } from 'node:child_process';
const root=dirname(fileURLToPath(import.meta.url));
const frames=join(root,'frames-layered'), output=join(root,'../../video/candidates/纸替_新技术方案_分层木偶_v2.mp4');
await rm(frames,{recursive:true,force:true});await mkdir(frames,{recursive:true});await mkdir(dirname(output),{recursive:true});
const browser=await chromium.launch({headless:true});const page=await browser.newPage({viewport:{width:1080,height:1920},deviceScaleFactor:1});
await page.goto(`file://${join(root,'index_layered.html')}`);await page.waitForFunction(()=>window.renderFrame&&document.querySelector('#frame').width===1080);await page.waitForTimeout(800);
for(let i=0;i<24*24;i++){await page.evaluate(f=>window.renderFrame(f),i);await page.locator('#frame').screenshot({path:join(frames,`frame-${String(i).padStart(5,'0')}.png`)});}
await browser.close();
await new Promise((resolve,reject)=>{const p=spawn('ffmpeg',['-y','-framerate','24','-i',join(frames,'frame-%05d.png'),'-an','-c:v','libx264','-preset','medium','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',output],{stdio:'inherit'});p.on('exit',c=>c?reject(new Error(`ffmpeg exited ${c}`)):resolve())});
await rm(frames,{recursive:true,force:true});console.log(JSON.stringify({output,duration_s:24,width:1080,height:1920,fps:24}));
