// Offline capture of the same cel-shaded, recorded-state viewer. No robot motion
// is synthesized here: only replay time, camera selection and captions change.
const puppeteer=require('puppeteer-core');
const fs=require('node:fs'),path=require('node:path'),{spawn}=require('node:child_process');
const {once}=require('node:events');
(async()=>{
 const run=path.resolve(process.argv[2]||'runs/catcher-specialist-v2'),preview=process.argv.includes('--preview');
 const report=JSON.parse(fs.readFileSync(path.join(run,fs.existsSync(path.join(run,'report.json'))?'report.json':'progress.json')));
 if(!preview && report.status!=='evaluated')throw Error('Evaluate the frozen checkpoint before making the demo video');
 const datasetPath=path.join(run,'synthetic-demonstrations.json'),ds=fs.existsSync(datasetPath)?JSON.parse(fs.readFileSync(datasetPath)):null;
 const output=path.join(run,'presentation');fs.mkdirSync(output,{recursive:true});
 const browser=await puppeteer.launch({executablePath:process.env.CHROME_PATH||'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true,args:['--enable-unsafe-swiftshader']});
 try{
 const page=await browser.newPage();await page.setViewport({width:1280,height:720,deviceScaleFactor:1});
 page.on('pageerror',e=>console.error(e.message));
 const relative=path.relative(process.cwd(),run).split(path.sep).join('/');
 await page.goto('http://127.0.0.1:8793/'+relative+'/review/index.html',{waitUntil:'networkidle0',timeout:120000});
 await page.waitForFunction(()=>window.catcherReplay?.ready,{timeout:120000});
 await page.addStyleTag({content:'main{padding:0!important;max-width:none}nav,.flow,main>small,main>h1,main>p,.controls,.cols,details{display:none!important}#view{margin-top:112px;height:546px!important;min-height:0;border:0;border-radius:0}#telemetry{border-radius:0;height:34px;font-size:14px;padding:7px 18px}.hint{display:none}#filmCaption{position:absolute;left:0;top:0;width:100%;height:112px;padding:18px 24px;background:#eff1e8;color:#183c38}#filmCaption strong{display:block;font-size:31px;line-height:1.2}#filmCaption span{display:block;font-size:18px;margin-top:8px}#filmNote{position:fixed;bottom:0;left:0;width:100%;height:28px;background:#183c38;color:#eff1e8;padding:3px 18px;font-size:13px}'});
 await page.evaluate(()=>{for(const id of ['filmCaption','filmNote']){let e=document.createElement('div');e.id=id;document.body.append(e)}document.querySelector('#filmNote').textContent='Recorded simulator replay · PPO controls six arm joints · engineered jaw/PD control · no cut, catch or real-arm claim';});
 const cases=await page.evaluate(()=>window.catcherReplay.cases());
 const first=cases.findIndex(c=>c.split==='holdout'),dev=cases.findIndex(c=>c.split==='development');
 async function select(i,view,title,subtitle){await page.evaluate(async({i,view,title,subtitle})=>{await window.catcherReplay.select(i);window.catcherReplay.view(view);const e=document.querySelector('#filmCaption');e.replaceChildren();const a=document.createElement('strong'),b=document.createElement('span');a.textContent=title;b.textContent=subtitle;e.append(a,b);},{i,view,title,subtitle});}
 async function seek(t){await page.evaluate(t=>new Promise(resolve=>{window.catcherReplay.seek(t);requestAnimationFrame(()=>requestAnimationFrame(resolve));}),t);}
 await select(first>=0?first:Math.max(0,dev),'close','An AI that creates the robot skills it’s missing.',report.status==='evaluated'?`${report.actor_parameters.toLocaleString()} actor parameters · ${report.successes}/${report.episodes} unseen trials passed`:'PPO development replay · final evaluation pending');await seek(4);
 await page.screenshot({path:path.join(output,'poster.png')});console.log('poster saved');if(preview)return;
 const fps=25,segments=[];
 segments.push({i:first,view:'whole',duration:3,freeze:true,title:'An AI that creates the robot skills it’s missing.',sub:'Astra builds the simulation, defines the task and shapes rewards.'});
 segments.push({i:0,view:'close',duration:4,title:'Before training',sub:'Untrained policy · development seed 41001 · misses the positioning criterion'});
 if(dev>=0)segments.push({i:dev,view:'close',duration:4,title:'A small specialist learns the skill',sub:'PPO controls six joint commands from simulator state. No IK or BC chooses the motion.'});
 const held=cases.map((c,i)=>({c,i})).filter(x=>x.c.split==='holdout');
 for(const {c,i} of held)segments.push({i,view:'close',duration:3,title:`Unseen trial ${c.seed} · ${c.success?'passed':'failed'}`,sub:'Different plant position, yaw and stiffness · same frozen checkpoint and acceptance criteria'});
 segments.push({i:first,view:'grasp',duration:3,freeze:true,last:true,title:'The tool is held through jaw contact',sub:'The catcher is a free body. This skill stops before fruit/net contact.'});
 segments.push({i:first,view:'close',duration:4,freeze:true,last:true,title:`${report.successes} / ${report.episodes} held-out trials passed`,sub:ds?`${ds.accepted}/${ds.attempted} fresh demonstrations · ${ds.state_action_pairs.toLocaleString()} state/action pairs · ${ds.actor_parameter_count.toLocaleString()} parameters`:'Separate synthetic demonstration generation follows the evaluation.'});
 const filename=path.join(output,'astra-catcher-ppo.mp4');const ff=spawn('ffmpeg',['-y','-loglevel','error','-f','image2pipe','-vcodec','mjpeg','-framerate',String(fps),'-i','pipe:0','-an','-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',filename],{stdio:['pipe','inherit','inherit']});
 const finished=once(ff,'close');let frames=0;
 for(const s of segments){await select(s.i,s.view,s.title,s.sub);for(let j=0;j<fps*s.duration;j++){await seek(s.freeze?(s.last?100:0):j/fps);const jpg=await page.screenshot({type:'jpeg',quality:90});if(!ff.stdin.write(jpg))await once(ff.stdin,'drain');frames++;}console.log(s.title,frames);}
 ff.stdin.end();const [code]=await finished;if(code!==0)throw Error('ffmpeg failed '+code);fs.writeFileSync(path.join(output,'capture.json'),JSON.stringify({fps,frames,duration_s:frames/fps,segments,scope:'Recorded MuJoCo poses shown in cel shading. Real-time playback; frozen holds clearly separate the captions. Aggregate scores from saved evaluation and generation manifests.'},null,2));console.log(filename);
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
