import {resolve} from 'node:path';
const root=resolve(import.meta.dir,'..'),c=await Bun.file(resolve(root,'.local/connection.json')).json();
const p=Bun.spawn(['bunx','electrobun','dev'],{cwd:root,env:{...process.env,ASTRA_SKILL_URL:c.url},stdout:'inherit',stderr:'inherit'});await p.exited;
