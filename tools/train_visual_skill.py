"""Train a sensor-only visual pickup policy on recorded demonstrations.

Privileged offline segment annotations select pickup training examples; they are
never policy inputs. Evaluation must call VisualPolicy.act(sensor_observation).
"""
import argparse,copy,hashlib,json,time
from pathlib import Path
import numpy as np
import torch
from astrafactory.vision_policy import VisualNetwork,resolve_device


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def load_split(root,split,limit):
    paths=sorted((root/split).glob('*.npz'))[:limit]
    if not paths:raise ValueError('No episodeNPZ in '+str(root/split))
    episodes=[]
    for path in paths:
        with np.load(path) as d:
            length=len(d['action'])
            if 'pickup_end_step' not in d or int(d['pickup_end_step'])<=0:
                raise ValueError(f'{path}: missing/nonpositive pickup_end_step; failed episode metadata retained in source dataset, cannot use as successfulpickup demonstration')
            length=min(length,int(d['pickup_end_step']))
            e={'path':str(path),'sha256':sha(path),'images':d['images'].copy(),'image_index':d['image_index'][:length].copy(),
               'proprio':d['proprio'][:length].astype(np.float32),'action':d['action'][:length].astype(np.float32)}
            if e['proprio'].shape!=(length,28) or e['images'].shape[1:]!=(2,160,160,3):raise ValueError('Frozen sensor schema mismatch')
            episodes.append(e)
    return episodes


def batch(episodes,indices,history,chunk,mean,std,device):
    rgbs=[];props=[];ys=[];masks=[]
    for episode,step in indices:
        e=episodes[episode];length=len(e['action']);past=np.maximum(0,np.arange(step-history+1,step+1));future=np.arange(step,step+chunk)
        rgbs.append(e['images'][e['image_index'][past]])
        props.append((e['proprio'][past]-mean)/std)
        ys.append(e['action'][np.minimum(future,length-1)])
        masks.append((future<length).astype(np.float32))
    images=np.stack(rgbs).transpose(0,1,2,5,3,4)
    return (torch.from_numpy(images).to(device,dtype=torch.float32)/255.,torch.from_numpy(np.asarray(props)).to(device),
            torch.from_numpy(np.asarray(ys)).to(device),torch.from_numpy(np.asarray(masks)).to(device))


def loss_fn(model,data):
    rgb,prop,y,mask=data;return (((model(rgb,prop)-y)**2)*mask[:,:,None]).sum()/(mask.sum()*7)


def sync(device):
    if device=='mps':torch.mps.synchronize()
    elif device=='cuda':torch.cuda.synchronize()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--data',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--device',default='auto');p.add_argument('--updates',type=int,default=400);p.add_argument('--batch-size',type=int,default=8)
    p.add_argument('--history-steps',type=int,default=16);p.add_argument('--chunk-size',type=int,default=8);p.add_argument('--execute-steps',type=int,default=2)
    p.add_argument('--train-limit',type=int,default=32);p.add_argument('--development-limit',type=int,default=8)
    p.add_argument('--resume',type=Path);p.add_argument('--benchmark',action='store_true')
    p.add_argument('--sampling',choices=['uniform','balanced-early'],default='uniform');p.add_argument('--normalization',choices=['empirical-v1','sensor-ranges-v2'],default='empirical-v1')
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);start=time.perf_counter();torch.set_num_threads(2);torch.manual_seed(2026);rng=np.random.default_rng(2026)
    device=resolve_device(a.device);train=load_split(a.data,'train',a.train_limit);dev=load_split(a.data,'development',a.development_limit)
    states=np.concatenate([e['proprio'] for e in train]);mean=states.mean(0);std=np.maximum(states.std(0),1e-3)
    if a.normalization=='sensor-ranges-v2':
        std[:7]=np.maximum(std[:7],.05);std[7:14]=np.maximum(std[7:14],.10);std[14:21]=np.maximum(std[14:21],.05)
        mean[21:28]=0.;std[21:28]=np.asarray([.4]*6+[.5],dtype=np.float32)
    model=VisualNetwork(a.chunk_size);config={'history_steps':a.history_steps,'chunk_size':a.chunk_size,'execute_steps':a.execute_steps,'rgb_shape':[2,160,160,3],'proprio_size':28}
    if a.resume:
        saved=torch.load(a.resume,map_location='cpu',weights_only=False)
        if saved['config']!=config:raise ValueError('Resume config mismatch')
        model.load_state_dict(saved['model']);mean=saved['proprio_mean'];std=saved['proprio_std']
    report={'scope':'Visual pickup action-chunk BC; twofixedRGB cameras+deployable joint/commandfeedback only. Noenv/pose/contact/phase at studentruntime.',
            'config':config,'parameters':sum(p.numel() for p in model.parameters()),'device':device,'cpu_threads':2,'updates':a.updates,'batch_size':a.batch_size,
            'sampling':a.sampling,'normalization':a.normalization,'training_rng_seed':2026,'source_sha256':{'policy':sha('src/astrafactory/vision_policy.py'),'trainer':sha(__file__)},
            'episodes':{key:[{'path':e['path'],'sha256':e['sha256'],'steps':len(e['action'])} for e in data] for key,data in [('train',train),('development',dev)]}}
    initial_checkpoint=a.out/'initial-policy.pt'
    torch.save({'model':model.state_dict(),'proprio_mean':mean,'proprio_std':std,'config':config},initial_checkpoint)
    report['initial_checkpoint_sha256']=sha(initial_checkpoint)
    if a.benchmark:
        pairs=[(j%len(train),min(50,len(train[j%len(train)]['action'])-1)) for j in range(a.batch_size)]
        original=copy.deepcopy(model.state_dict());bench=[]
        for target in ['cpu']+(['mps'] if torch.backends.mps.is_available() else [])+(['cuda'] if torch.cuda.is_available() else []):
            sync(target);t=time.perf_counter();data=batch(train,pairs,a.history_steps,a.chunk_size,mean,std,target)
            trial=VisualNetwork(a.chunk_size).to(target);trial.load_state_dict(original);opt=torch.optim.Adam(trial.parameters(),lr=.0003);sync(target);allocation=time.perf_counter()-t
            for _ in range(2):loss=loss_fn(trial,data);opt.zero_grad();loss.backward();opt.step()
            sync(target);t=time.perf_counter()
            for _ in range(10):loss=loss_fn(trial,data);opt.zero_grad();loss.backward();opt.step()
            sync(target);bench.append({'device':target,'ten_updates_seconds':time.perf_counter()-t,'transfer_allocation_seconds':allocation});del trial,opt,data
        report['actual_batch_benchmark']=bench;print(json.dumps({'benchmark':bench}),flush=True)
    model=model.to(device);optimizer=torch.optim.Adam(model.parameters(),lr=.0003);trainstart=time.perf_counter();losses=[]
    for update in range(a.updates):
        pairs=[(int(rng.integers(len(train))),0) for _ in range(a.batch_size)]
        selected=[]
        for i,_ in pairs:
            draw=rng.random() if a.sampling=='balanced-early' else 1.
            step=0 if draw<.25 else int(rng.integers(min(64,len(train[i]['action'])))) if draw<.5 else int(rng.integers(len(train[i]['action'])))
            selected.append((i,step))
        pairs=selected
        data=batch(train,pairs,a.history_steps,a.chunk_size,mean,std,device);loss=loss_fn(model,data)
        optimizer.zero_grad();loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),1.);optimizer.step()
        if (update+1)%50==0:
            sync(device);row={'update':update+1,'train_batch_mse':float(loss.detach().cpu()),'seconds':time.perf_counter()-trainstart};losses.append(row);print(json.dumps(row),flush=True)
    sync(device);report['training_seconds']=time.perf_counter()-trainstart;report['training_log']=losses
    model.eval();metrics=[]
    with torch.inference_mode():
        for step in range(20):
            pairs=[(int(rng.integers(len(dev))),0) for _ in range(a.batch_size)];pairs=[(i,int(rng.integers(len(dev[i]['action'])))) for i,_ in pairs]
            metrics.append(float(loss_fn(model,batch(dev,pairs,a.history_steps,a.chunk_size,mean,std,device)).cpu()))
    report['offline_development_mse']=float(np.mean(metrics))
    checkpoint=a.out/'policy.pt';torch.save({'model':{k:v.cpu() for k,v in model.state_dict().items()},'proprio_mean':mean,'proprio_std':std,'config':config,
        'training_data_sha256':[e['sha256'] for e in train],'training_rng_seed':2026},checkpoint)
    report['checkpoint_sha256']=sha(checkpoint);report['total_seconds']=time.perf_counter()-start
    (a.out/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps({'checkpoint':str(checkpoint),'offline_development_mse':report['offline_development_mse'],'seconds':report['total_seconds']}),flush=True)
if __name__=='__main__':main()
