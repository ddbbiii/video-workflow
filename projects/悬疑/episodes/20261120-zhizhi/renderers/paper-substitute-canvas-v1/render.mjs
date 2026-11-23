import { chromium } from 'playwright';
import { mkdir, rm } from 'node:fs/promises';
import { join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawn } from 'node:child_process';

const root=dirname(fileURLToPath(import.meta.url));
const frames=join(root,'frames'), output=join(root,'../../video/candidates/纸替_canvas_完整叙事_v1.mp4');
await rm(frames,{recursive:true,force:true}); await mkdir(frames,{recursive:true}); await mkdir(dirname(output),{recursive:true});
const browser=await chromium.launch({headless:true}); const page=await browser.newPage({viewport:{width:1080,height:1920},deviceScaleFactor:1});
await page.goto(`file://${join(root,'index.html')}`); await page.waitForFunction(()=>typeof window.renderFrame==='function');
for(let i=0;i<16*4*24;i++){await page.evaluate((f)=>window.renderFrame(f),i);await page.locator('#frame').screenshot({path:join(frames,`frame-${String(i).padStart(5,'0')}.png`)});}
await browser.close();
await new Promise((resolvePromise,reject)=>{const p=spawn('ffmpeg',['-y','-framerate','24','-i',join(frames,'frame-%05d.png'),'-an','-c:v','libx264','-pix_fmt','yuv420p','-movflags','+faststart',output],{stdio:'inherit'});p.on('exit',c=>c?reject(new Error(`ffmpeg exited ${c}`)):resolvePromise());});
await rm(frames,{recursive:true,force:true});
console.log(JSON.stringify({output,frames:16*4*24,duration_s:64,width:1080,height:1920}));
