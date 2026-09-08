import {resolve} from 'node:path';
const cwd=resolve(import.meta.dir,'..');
const child=Bun.spawn(['bunx','electrobun','dev'],{cwd,env:{...process.env,ASTRAFACTORY_ROOT:resolve(cwd,'../..'),ASTRAFACTORY_UI_DIST:resolve(cwd,'dist')},stdin:'inherit',stdout:'inherit',stderr:'inherit'});
process.exit(await child.exited);
