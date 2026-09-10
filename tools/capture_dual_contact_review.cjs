// Capture recorded physics from the orbitable review; only camera/time change.
const puppeteer=require('puppeteer-core'),fs=require('fs'),path=require('path');
const {spawn}=require('child_process'),{once}=require('events');
(async()=>{
 const run=path.resolve(process.argv[2]),out=path.join(run,'presentation'),videoName=process.argv[3]||'recorded-physics.mp4';fs.mkdirSync(out,{recursive:true});
 const browser=await puppeteer.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true,args:['--enable-unsafe-swiftshader']});
 try{
  const page=await browser.newPage();await page.setViewport({width:1280,height:900,deviceScaleFactor:1});page.on('pageerror',e=>{throw e});
  await page.goto('http://127.0.0.1:8793/'+path.relative(process.cwd(),run)+'/review/index.html',{waitUntil:'networkidle0'});await page.waitForFunction(()=>window.dualReplay?.ready);
  const info=await page.evaluate(()=>window.dualReplay.info());if(!info.result.controller)throw Error('Replay needs recorded controller provenance');
  async function seek(t,view){await page.evaluate(({t,view})=>new Promise(resolve=>{window.dualReplay.view(view);window.dualReplay.seek(t);requestAnimationFrame(()=>requestAnimationFrame(resolve))}),{t,view});}
  for(const view of ['whole','close','side']){await seek(info.end,view);await page.screenshot({path:path.join(out,view+'.png')});}
  await page.addStyleTag({content:'main{padding:0;max-width:none}main>small,main>h1,main>p,.controls{display:none}#view{height:832px;min-height:0;border-radius:0}#telemetry{height:68px;border-radius:0;padding:10px 20px}#caption{position:absolute;top:0;left:0;padding:12px 20px;background:#eff1e8e8;width:100%;color:#183c38;font-size:18px}'});
  await page.evaluate(()=>{const e=document.createElement('div');e.id='caption';document.body.append(e)});
  const fps=20,segments=[{view:'whole',start:0,end:info.end,label:'Recorded episode'},{view:'close',start:Math.max(0,(info.result.cut_event?.time_s||3.4)-1.5),end:info.result.net_hold_steps>=25?info.end:Math.min(info.end,(info.result.cut_event?.time_s||info.end)+2),label:info.result.net_hold_steps>=25?'Cut and catch, close view':'Same contact event, close view'}];
  const ff=spawn('/opt/homebrew/bin/ffmpeg',['-y','-loglevel','error','-f','image2pipe','-vcodec','mjpeg','-framerate',String(fps),'-i','pipe:0','-an','-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',path.join(out,videoName)],{stdio:['pipe','inherit','inherit']});const done=once(ff,'close');let frames=0;
  for(const segment of segments){await page.evaluate(({label,passed})=>document.querySelector('#caption').textContent=label+' · recorded physics at 1× · '+(passed?'PASS':'INCOMPLETE / FAILED')+' · simulation only',{label:segment.label,passed:info.result.is_success});for(let t=segment.start;t<=segment.end+1e-7;t+=1/fps){await seek(t,segment.view);const buffer=await page.screenshot({type:'jpeg',quality:88});if(!ff.stdin.write(buffer))await once(ff.stdin,'drain');frames++;}console.log(segment.label);}
  ff.stdin.end();const[code]=await done;if(code!==0)throw Error('ffmpeg '+code);fs.writeFileSync(path.join(out,videoName+'.capture.json'),JSON.stringify({fps,frames,segments,scope:'Recorded MuJoCo body and net states. Same episode, different views.',controller:info.result.controller,result:info.result},null,2));console.log(out);
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
