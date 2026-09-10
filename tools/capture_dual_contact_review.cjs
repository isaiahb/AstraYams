// Capture recorded physics from the orbitable review; only camera/time change.
const puppeteer=require('puppeteer-core'),fs=require('fs'),path=require('path');
const {spawn}=require('child_process'),{once}=require('events');
(async()=>{
 const run=path.resolve(process.argv[2]),out=path.join(run,'presentation');fs.mkdirSync(out,{recursive:true});
 const browser=await puppeteer.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true,args:['--enable-unsafe-swiftshader']});
 try{
  const page=await browser.newPage();await page.setViewport({width:1280,height:900,deviceScaleFactor:1});page.on('pageerror',e=>{throw e});
  await page.goto('http://127.0.0.1:8793/'+path.relative(process.cwd(),run)+'/review/index.html',{waitUntil:'networkidle0'});await page.waitForFunction(()=>window.dualReplay?.ready);
  const info=await page.evaluate(()=>window.dualReplay.info());if(info.result.invalid||!info.result.is_success)throw Error('Commissioning did not pass');
  async function seek(t,view){await page.evaluate(({t,view})=>new Promise(resolve=>{window.dualReplay.view(view);window.dualReplay.seek(t);requestAnimationFrame(()=>requestAnimationFrame(resolve))}),{t,view});}
  for(const view of ['whole','close','side']){await seek(info.end,view);await page.screenshot({path:path.join(out,view+'.png')});}
  await page.addStyleTag({content:'main{padding:0;max-width:none}main>small,main>h1,main>p,.controls{display:none}#view{height:832px;min-height:0;border-radius:0}#telemetry{height:68px;border-radius:0;padding:10px 20px}#caption{position:absolute;top:0;left:0;padding:12px 20px;background:#eff1e8e8;width:100%;color:#183c38;font-size:18px}'});
  await page.evaluate(()=>{const e=document.createElement('div');e.id='caption';document.body.append(e)});
  const fps=25,segments=[{view:'whole',start:0,end:info.end,label:'Full sequence'},{view:'close',start:3.4,end:info.end,label:'Same cut, close view'},{view:'side',start:3.4,end:info.end,label:'Same cut, lower view'}];
  const ff=spawn('/opt/homebrew/bin/ffmpeg',['-y','-loglevel','error','-f','image2pipe','-vcodec','mjpeg','-framerate',String(fps),'-i','pipe:0','-an','-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',path.join(out,'contact-fix.mp4')],{stdio:['pipe','inherit','inherit']});const done=once(ff,'close');let frames=0;
  for(const segment of segments){await page.evaluate(label=>document.querySelector('#caption').textContent=label+' · recorded physics at 1× · PPO catcher / scripted cutter · simulation only',segment.label);for(let t=segment.start;t<=segment.end+1e-7;t+=1/fps){await seek(t,segment.view);const buffer=await page.screenshot({type:'jpeg',quality:88});if(!ff.stdin.write(buffer))await once(ff.stdin,'drain');frames++;}console.log(segment.label);}
  ff.stdin.end();const[code]=await done;if(code!==0)throw Error('ffmpeg '+code);fs.writeFileSync(path.join(out,'capture.json'),JSON.stringify({fps,frames,segments,scope:'Recorded MuJoCo body and net states. Same episode replayed from three cameras.'},null,2));console.log(out);
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
