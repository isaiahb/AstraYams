"""Verify recorded contact evidence and write a revision manifest. No score tuning."""
from pathlib import Path
import json,hashlib
P=Path(__file__).resolve().parents[1]/'assets/workcells/strawberry-specimen'
def verify():
 results={k:json.loads((P/k/'result.json').read_text()) for k in ['rest','leaf','leaf-control','stalk','stalk-control','neighbor','neighbor-control']}
 for kind in ['leaf','stalk','neighbor']:
  a,b=results[kind],results[kind+'-control']
  assert a['valid_run'] and b['valid_run']
  assert a['target_touched'] and not a['initial_probe_contacts']
  assert not b['probe_contacts']
  assert a['probe_start_m']==b['probe_start_m'] and a['probe_end_m']==b['probe_end_m']
 summary={'checkpoint':'single-specimen-crown-v4','model_sha256':hashlib.sha256((P/'scene.xml').read_bytes()).hexdigest(),'all_three_intended_targets_touched':True,'controls_have_zero_probe_contacts':True,'matching_control_trajectories':True,'no_initial_probe_overlap':True,'all_trials_without_physics_warnings':all(r['valid_run'] for r in results.values()),'rest_last_second_span_mm':results['rest']['final_second_max_geom_coordinate_span_mm'],'contact_trials':{k:{'max_probe_penetration_mm':max(x['max_penetration_mm'] for x in results[k]['probe_contacts'].values()),'peak_probe_contact_force_n':max(x['peak_force_n'] for x in results[k]['probe_contacts'].values())} for k in ['leaf','stalk','neighbor']},'limits':['Assumed depth and metric scale, no exact multi-view reconstruction','Uncalibrated tissue properties','Transient settling contacts exceeded 1 mm; see raw report','Rigid fruit; no detachment or bruising','Neighboring fruit already touch at rest; this tests cluster response, not first-contact onset','Crown fixed to substrate; root/substrate mechanics omitted']}
 (P/'validation.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
if __name__=='__main__':verify()
