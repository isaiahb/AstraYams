from pathlib import Path
import json,shutil,numpy as np,mujoco,xml.etree.ElementTree as ET
P=Path(__file__).resolve().parent;OUT=P.parents[1].parent/'AstraFactory/assets/workcells/strawberry-harvest/plant-physics'
a=np.load(P/'surface-matched/rollout.npz');b=np.load(P/'surface-control/rollout.npz');motion=np.linalg.norm(a['fruit']-b['fruit'],axis=2).max(axis=0)*1000
r=json.loads((P/'surface-matched/result.json').read_text());half=json.loads((P/'surface-half-timestep/result.json').read_text());m=mujoco.MjModel.from_xml_path(str(P/'surface-matched/scene.xml'));d=mujoco.MjData(m)
errors=[]
for q in a['qpos']:
 d.qpos[:]=q;mujoco.mj_forward(m,d)
 errors.extend([float(np.linalg.norm(d.xpos[m.body('pedicel_right_'+str(j)+'_tip').id]-d.xpos[m.body('crop_fruit_'+str(j)).id])*1000) for j in [2,3,4]])
metrics={'contact_response_vs_control_mm':motion.tolist(),'probe_peak_force_n':r['peak_probe_force_n'],'probe_penetration_max_mm':r['max_probe_penetration_m']*1000,'max_right_cluster_attachment_gap_mm':max(errors),'half_timestep_peak_force_change_percent':abs(half['peak_probe_force_n']/r['peak_probe_force_n']-1)*100,'half_timestep_impulse_change_percent':abs(half['probe_impulse_ns']/r['probe_impulse_ns']-1)*100,'hardware_unchanged':json.loads((P/'surface-matched/model.json').read_text())['hardware_unchanged'],'status':'Candidate physical plant; diagnostic tests only, not a learned harvest or calibrated digital twin'}
(P/'summary.json').write_text(json.dumps(metrics,indent=2))
# Persist actual integration timestep for the half-step trial's reproducing scene.
s=P/'surface-half-timestep/scene.xml';root=ET.parse(s);root.find('option').set('timestep','.0005');root.write(s,encoding='unicode')
report='''# Plant physics iteration

YAM arms, cameras, grippers and both held tools are unchanged. The original successful harvest remains the baseline; this candidate is a separate physical-interaction test, not a newly trained harvest.

## Revisions
1. Replaced five decorative berries and single-link target stalks with eight physical berries, common flexible branch parents and segmented stalks. Equivalent bending spring stiffness is EI/L with radius-dependent second moment of area. This is a reduced beam approximation, not a Cosserat or FEM implementation. Bodies have mass, damping and contacts with robot surfaces, tools, fixtures and other plant elements.
2. Reviewed the first render: stem attachments stretched visibly and stacked leaf ellipsoids looked implausible. Tightened attachment constraints and replaced leaves with contiguous mesh panels in trifoliate groups. 81 leaf panels are physical, though each panel remains rigid between hinges.
3. Replaced ellipsoidal berry collision proxies with convex collision hulls derived from the visible berry mesh. Increased stalk discretization from five to eight segments and tested a half timestep.

## Evidence
A force-limited dynamic spherical probe moves through the cluster, then withdraws. Robot motors hold their reset pose. Probe position is initialized once, clear of the fruit, after three seconds of settling; during the interaction the probe is force-driven, never teleported. An otherwise matching no-contact run provides a control. Neighbouring fruit can respond through their common branch and fruit–fruit contact; these tests do not isolate those mechanisms individually.

'''
report+=f"Compared with the no-contact control, maximum positional differences for the three right-cluster berries were {', '.join(f'{x:.1f}' for x in motion)} mm. Peak probe force was {r['peak_probe_force_n']:.3f} N. Maximum probe penetration was {metrics['probe_penetration_max_mm']:.3f} mm; maximum right-cluster attachment error was {max(errors):.3f} mm. These are simulated measurements.\n\n"
report+=f"Halving the timestep from 1 ms to 0.5 ms changed peak force by {metrics['half_timestep_peak_force_change_percent']:.1f}% and contact impulse by {metrics['half_timestep_impulse_change_percent']:.1f}%. Both runs remained finite and reported no MuJoCo warnings. The earlier five-to-eight-segment comparison changed peak force by roughly 29%, so mesh/segment convergence is not established.\n\n"
report+='''## Remaining reality gaps
- Young's modulus, damping, stem density and fruit contact properties are uncalibrated assumptions. Fit them to measured load–deflection, release/oscillation and contact experiments before asserting transfer accuracy.
- Rigid fruit cannot predict local deformation or bruising. Mesh contacts use convex hulls; fine seeds and calyx details are not independently compliant.
- Leaf panels approximate bending; vein structure, tissue anisotropy and full sheet deformation are absent. Branch shapes and fruit distribution need measured botanical geometry.
- Harvest controller has not been commissioned on the moving plant. A cut/recoil test, unintended stem damage, and physical fracture calibration remain outstanding. Existing simplified work threshold is not validated by this probe test.
- Need longer settling and a wider sweep of stiffness, damping, integration resolution and held-out cluster shapes. Contact response is sensitive to initial conditions.

## Research informing model choice
- Gazebo Plants, Cosserat rod plant interactions: https://arxiv.org/abs/2402.02570
- Strawberry segmented-beam digital replicas, reported deflection errors 32–40%: https://doi.org/10.1007/978-3-032-15375-3_9
- Experimental strawberry stalk cutting/gripping forces: https://arxiv.org/abs/2207.12552
- MuJoCo elasticity plugin: https://github.com/google-deepmind/mujoco/blob/main/plugin/elasticity/README.md

Next: calibrate branch compliance and recovery against real plant video/force measurements, then test actual blade engagement and post-cut recoil. A visually convincing response alone is insufficient validation.
'''
(P/'REVIEW.md').write_text(report)
OUT.mkdir(parents=True,exist_ok=True)
for name in ['plant.py','plant-v1.py','plant-v2.py','test_plant.py','render.py','export_review.py','publish.py','REVIEW.md','summary.json']:
 shutil.copy2(P/name,OUT/name)
for tag in ['contact','no-contact','refined','refined-control','refined-eight-segments','surface-matched','surface-control','surface-half-timestep']:
 shutil.copytree(P/tag,OUT/tag,dirs_exist_ok=True)
mp=OUT.parent/'demo.json';manifest=json.loads(mp.read_text());prefix='assets/workcells/strawberry-harvest/plant-physics/'
manifest['environment_review']['plant_physics']={'title':'Plant contact & recovery','path':prefix+'surface-matched/plant-response.mp4','replay_path':prefix+'replay.json','report':prefix+'REVIEW.md','summary':f"Eight physical berries, connected flexible stalks and 81 leaf panels. Diagnostic probe response; YAM hardware unchanged. Peak force {r['peak_probe_force_n']:.2f} N; maximum probe penetration {metrics['probe_penetration_max_mm']:.2f} mm. Parameters remain uncalibrated."}
manifest['improvements']=[{'title':'Calibrate plant bending and recovery','detail':'Fit branch stiffness and damping to real load–deflection and release measurements.'},{'title':'Validate cutting and recoil','detail':'Test actual blade–stalk engagement and the motion of the remaining cluster.'},{'title':'Refine fruit and leaf contact','detail':'Validate deformation and damage; the current fruit model is rigid.'}]
for label,path in [('Plant physics review','REVIEW.md'),('Plant response measurements','summary.json'),('Plant interaction video','surface-matched/plant-response.mp4'),('Plant model generator','plant.py')]:
 if not any(x.get('path')==prefix+path for x in manifest['sources']):manifest['sources'].append({'label':label,'path':prefix+path})
mp.write_text(json.dumps(manifest,indent=2));print(json.dumps(metrics,indent=2))
