import { BrowserWindow } from 'electrobun/main';
import { startServer } from './server';
const app=process.env.ASTRAFACTORY_SERVER_URL?null:await startServer({root:process.env.ASTRAFACTORY_ROOT,dist:process.env.ASTRAFACTORY_UI_DIST});
new BrowserWindow({title:'AstraFactory',url:app?.url||process.env.ASTRAFACTORY_SERVER_URL!,frame:{width:1440,height:940,x:70,y:50}});
process.on('exit',()=>app?.close());
