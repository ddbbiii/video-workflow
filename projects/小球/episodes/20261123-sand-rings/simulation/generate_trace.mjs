import {readFile,writeFile} from 'node:fs/promises';
import {simulate} from './model.mjs';
const source=new URL('./config.json',import.meta.url);
const config=JSON.parse(await readFile(source,'utf8'));
const trace=simulate(config);
await writeFile(new URL('./trace.json',import.meta.url),JSON.stringify(trace));
console.log(JSON.stringify({initial:trace.initial,...trace.result,duration:trace.config.duration},null,2));
