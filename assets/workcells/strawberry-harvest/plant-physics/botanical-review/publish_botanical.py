from pathlib import Path
import json,shutil
P=Path(__file__).resolve().parent;ROOT=P.parents[1].parent/'AstraFactory';OUT=ROOT/'assets/workcells/strawberry-harvest/plant-physics/botanical-review';OUT.mkdir(parents=True,exist_ok=True)
metrics=json.loads((P/'botanical-v8-metrics.json').read_text());r=json.loads((P/'botanical-v8/result.json').read_text());assert r['valid_run'] and metrics['quiet_rest_gate_max_span_2mm']
report='''# Strawberry morphology and shape retention revision

Status: contact-only candidate. Original harvest baseline preserved. This revision does not implement fruit detachment; it must not be described as a working harvest environment.

## Why the previous version was wrong
Long, straight stalks radiated from a high junction, foliage lay near the soil, and oscillation persisted. Merely increasing a damping number would not fix the anatomy or the natural resting geometry.

## Botanical changes
Crown-rooted upright petioles carry broad trifoliate foliage. Curved trusses emerge separately, with a primary terminal fruit and a secondary fork carrying shorter pedicels. One smaller green fruit provides a different development stage, with mass and collision geometry scaled consistently. The resting centerlines are curved, with tapered radii; they no longer start as a straight hanging frame. Botanical layout follows the crown/petiole/compound-cyme distinction in NC State's production guide, but remains a procedural approximation, not a measured cultivar model. Canopy shape and variation still need improvement.

Reference: https://content.ces.ncsu.edu/southern-regional-strawberry-plasticulture-production-guide (Strawberry biology / Morphology)
Reference: https://strawberrycenterblog.com/2025/12/15/strawberry-anatomy-part-3-leaves-and-stems/

## Mechanical changes
Natural shape is encoded by curved rest geometry. Equivalent rotational stiffness derives from EI/L. The final candidate uses spherical joints with approximate isotropic rotational stiffness, stronger restoring stiffness and damping than the rejected version. Tissue values remain uncalibrated. This is not a validated Cosserat/FEM model.

Internal collisions between connected tissue at crowns/forks/fruit attachments are excluded; external robot, tool, berry and plant contacts remain. Free fruit bodies plus stiff attachment constraints proved problematic in the stiffer trials. For this diagnostic, berries are directly attached to the flexible stalk hierarchy, preserving their mass and inertia without attachment-constraint stretch. This removes detachment capability from this candidate; explicit topology change/contact restoration is required before cutting tests. No robot, gripper, tool or camera geometry changed.

## Validation
A matching untouched control tests whether the plant settles under gravity. The contact test drives a force-limited dynamic probe against a berry and withdraws. There are five seconds of settling before the contact test. The video starts after that settling period; the interactive replay and raw trace include it. No fruit is teleported or animated by keyframes.

'''
report+=f"Both final trials ran for 14 simulated seconds at a 0.5 ms timestep without warnings. The largest control span during the one-second window before contact was {max(metrics['max_control_span_before_contact_mm']):.4f} mm. Peak probe contact force was {r['peak_probe_force_n']:.3f} N; maximum probe penetration was {r['max_probe_penetration_m']*1000:.3f} mm. Maximum final difference from the untouched control was {max(metrics['final_contact_difference_mm']):.4f} mm. These are simulator checks, not measurements of a real strawberry plant.\n\n"
report+='''## Rejected trials retained
The initial botanical build and revisions v2, v5, v6 and v7 reported numerical instability and were rejected. Version v4 was finite but failed the quiet-rest intent, with roughly 11 mm motion on one coordinate of the immature fruit in the final second. The final v8 changes the attachment representation rather than hiding that failure with scripted trajectories.

## What is still unproven
Real-plant load–deflection curves, recovery time, damping, turgor effects, fruit deformation/bruising and cutting forces have not been calibrated. The quiet-rest gate is an engineering sanity check, not a biological tolerance. Stable contact response does not establish sim-to-real accuracy. Training throughput and solver/discretization convergence must be assessed after the final attachment/cutting model is chosen.
'''
(OUT/'REVIEW.md').write_text(report);(OUT/'metrics.json').write_text(json.dumps(metrics,indent=2))
for f in ['botanical.py','botanical-v4-generator.py','botanical-v5-generator.py','botanical-v7-generator.py','test_botanical.py','analyze_botanical.py','render_botanical.py','export_botanical.py','publish_botanical.py']:
 shutil.copy2(P/f,OUT/f)
for tag in ['botanical-contact','botanical-v2','botanical-v3','botanical-v4','botanical-v4-control','botanical-v5','botanical-v6','botanical-v7','botanical-v8','botanical-v8-control']:
 target=OUT/tag;target.mkdir(exist_ok=True)
 for f in ['result.json','model.json']:
  if (P/tag/f).exists():shutil.copy2(P/tag/f,target/f)
 if tag.startswith('botanical-v8'):
  for f in ['scene.xml','rollout.npz','trace.json']:shutil.copy2(P/tag/f,target/f)
for f in ['plant-response.mp4','frame-5.png','frame-6.2.png','frame-13.5.png']:shutil.copy2(P/'botanical-v8'/f,OUT/f)
mp=ROOT/'assets/workcells/strawberry-harvest/demo.json';m=json.loads(mp.read_text());prefix=str(OUT.relative_to(ROOT))+'/'
m['environment_review']['plant_physics']={'title':'Strawberry plant · shape retention and contact','path':prefix+'plant-response.mp4','replay_path':prefix+'replay.json','report':prefix+'REVIEW.md','summary':'Rebuilt crown, upright trifoliate foliage and curved branching fruit trusses. Stronger shape retention; quiet-rest and contact tests passed in simulation. YAM hardware unchanged. Contact-only candidate: fruit detachment is not implemented and tissue properties are uncalibrated.'}
for label,path in [('Botanical structure and shape-retention review','REVIEW.md'),('Plant settling measurements','metrics.json')]:
 if not any(s.get('path')==prefix+path for s in m['sources']):m['sources'].append({'label':label,'path':prefix+path})
m['improvements']=[{'title':'Calibrate the plant response','detail':'Compare bending force and recovery against real strawberry plants; current parameters are assumed.'},{'title':'Add physical detachment to the revised plant','detail':'The new contact-only candidate needs a cutting/topology-change model before harvesting.'},{'title':'Refine canopy geometry','detail':'Add measured leaf shapes, orientations and cultivar-dependent plant variation.'}]
mp.write_text(json.dumps(m,indent=2));print(OUT)
