from pathlib import Path
import numpy as np,json,argparse
P=Path(__file__).resolve().parent;p=argparse.ArgumentParser();p.add_argument('--tag',default='botanical-v5');a=p.parse_args();tag=a.tag
x=np.load(P/tag/'rollout.npz');y=np.load(P/(tag+'-control')/'rollout.npz');t=x['t'];err=np.linalg.norm(x['fruit']-y['fruit'],axis=2)*1000
span=np.linalg.norm(np.ptp(y['fruit'][t>13],axis=0),axis=1)*1000;pre=np.linalg.norm(np.ptp(y['fruit'][(t>4)&(t<5)],axis=0),axis=1)*1000
threshold=max(2,float(err.max())*.05);settling=None
for j in np.where(t>7.7)[0]:
 if np.max(err[j:])<threshold:settling=float(t[j]-7.7);break
r={'tag':tag,'max_control_span_last_second_mm':span.tolist(),'max_control_span_before_contact_mm':pre.tolist(),'peak_contact_difference_mm':err.max(axis=0).tolist(),'final_contact_difference_mm':err[-1].tolist(),'relative_recovery_after_withdraw_seconds':settling,'relative_recovery_threshold_mm':threshold,'quiet_rest_gate_max_span_2mm':bool(max(span)<2),'scope':'Engineering sanity gate, not a measured biological tolerance. Compare real plant force and motion data before claiming accuracy.'}
(P/(tag+'-metrics.json')).write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
