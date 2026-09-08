import { spawn, type ChildProcessWithoutNullStreams } from 'node:child_process';
import { createInterface } from 'node:readline';

export class Codex {
  process?: ChildProcessWithoutNullStreams;
  pending = new Map<number, {resolve: (v:any)=>void, reject:(e:Error)=>void, timer:ReturnType<typeof setTimeout>}>();
  sequence = 0;
  ready = false;
  error: string | null = null;
  notifications: (message:any)=>void = ()=>{};
  approval: (message:any)=>void = ()=>{};
  startPromise?: Promise<void>;
  start() {
    if(this.startPromise) return this.startPromise;
    this.startPromise = this.connect().catch(e=>{this.error=String(e); this.startPromise=undefined; throw e;});
    return this.startPromise;
  }
  private async connect() {
    const binary = process.env.CODEX_BIN || Bun.which('codex') || '/Applications/ChatGPT.app/Contents/Resources/codex';
    this.process = spawn(binary, ['app-server', '--listen', 'stdio://'], {stdio:['pipe','pipe','pipe']});
    createInterface({input:this.process.stdout}).on('line', line=>{
      let message; try {message=JSON.parse(line);} catch {return;}
      if(message.id!==undefined && message.method) {this.approval(message); return;}
      if(message.id!==undefined) {
        const pending=this.pending.get(message.id); if(!pending)return;
        clearTimeout(pending.timer);this.pending.delete(message.id);
        if(message.error)pending.reject(new Error(message.error.message));else pending.resolve(message.result);
      } else this.notifications(message);
    });
    this.process.stderr.on('data', ()=>{}); // Never expose inherited service logs or credentials to UI.
    this.process.on('error', e=>this.fail(e));
    this.process.on('exit', code=>{this.ready=false;this.startPromise=undefined;this.fail(new Error(`Codex server exited (${code})`));});
    await this.request('initialize',{clientInfo:{name:'astrafactory',title:'AstraFactory',version:'0.1.0'}});
    this.send({method:'initialized',params:{}});
    this.ready=true;this.error=null;
  }
  fail(error:Error){this.error=error.message;for(const p of this.pending.values()){clearTimeout(p.timer);p.reject(error);}this.pending.clear();}
  send(message:any){this.process?.stdin.write(JSON.stringify(message)+'\n');}
  request(method:string,params:any={},timeout=30000):Promise<any>{
    return new Promise((resolve,reject)=>{const id=++this.sequence;const timer=setTimeout(()=>{this.pending.delete(id);reject(new Error(`Timed out: ${method}`));},timeout);this.pending.set(id,{resolve,reject,timer});this.send({id,method,params});});
  }
  close(){this.process?.kill();}
}
