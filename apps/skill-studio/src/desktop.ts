import {BrowserWindow} from 'electrobun/main';
const url=process.env.ASTRA_SKILL_URL;
if(!url)throw new Error('Launch using bun run desktop from apps/skill-studio');
new BrowserWindow({title:'Astra Yams',url,frame:{width:1440,height:960,x:50,y:30}});
