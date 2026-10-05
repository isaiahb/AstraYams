from pathlib import Path
import json,shutil
P=Path(__file__).resolve().parent;ROOT=P.parents[1].parent/'AstraFactory';OUT=ROOT/'assets/workcells/strawberry-harvest/plant-physics/canopy-review';OUT.mkdir(parents=True,exist_ok=True)
metrics=json.loads((P/'canopy-v1-metrics.json').read_text());trial=json.loads((P/'canopy-v1/result.json').read_text());assert trial['valid_run'] and metrics['quiet_rest_gate_max_span_2mm']
for f in ['canopy.py','test_canopy.py','render_canopy.py','canopy_style.py','canopy_visibility.py','export_canopy.py','publish_canopy.py','canopy-v1-metrics.json']:
 shutil.copy2(P/f,OUT/f)
for tag in ['canopy-v1','canopy-v1-control']:shutil.copytree(P/tag,OUT/tag,dirs_exist_ok=True)
shutil.copy2(P/'checkpoints/2026-09-09-botanical-v8/CHECKPOINT.json',OUT/'previous-checkpoint.json')
report='''# Canopy iteration after approved botanical v8 checkpoint

The prior checkpoint remains at ../botanical-review/ with its video, replay and source. An additional local checkpoint with SHA-256 file hashes is saved in the study at checkpoints/2026-09-09-botanical-v8/. The YAM hardware, tools, fruit truss geometry and stiffness baseline are unchanged.

Changes: deterministic per-crown variation in petiole lengths, heights and directions; varied leaflet pitch and roll; contiguous cupped/serrated lamina panels; lower older leaves near the fruit; subtle leaf color variation. Removed the thin artificial midrib geometry and reduced the dark contour thickness specifically on leaf surfaces. Physics still uses physical hinged panels with convex-hull contacts; leaf tissue is not FEM and the concave visual cup is approximated by a hull for contact.

Both 14-second control/contact runs completed without MuJoCo warnings. The unchanged 2 mm engineering quiet-rest gate passed. The largest control motion span in the final second was %.3f mm; the final maximum contact-vs-control positional difference was %.3f mm. This is a simulated sanity check, not a real-plant validation. It is less quiet than the previous checkpoint, with additional foliage interaction, and does not demonstrate improved transfer performance.

A single-pose rendering check found that leaf surfaces hide about 6.4%% of berry-mesh pixels in the cutting wrist view, 1.3%% in the overview, and 0%% in the catching wrist view. This is modest added occlusion, not a dense-canopy benchmark. RGB images, counts and the counterfactual definition are in canopy-v1/visibility.json. No camera mount was moved.

The leaves are physical and can contact objects. The orange sphere is a force-driven diagnostic probe, not a learned robot action. Fruit detachment is still unavailable in this contact-only candidate. Real leaf geometry, stiffness/damping measurements, cutting/topology change and fruit deformation remain outstanding.
''' % (max(metrics['max_control_span_last_second_mm']),max(metrics['final_contact_difference_mm']))
(OUT/'REVIEW.md').write_text(report)
mp=ROOT/'assets/workcells/strawberry-harvest/demo.json';m=json.loads(mp.read_text());prefix=str(OUT.relative_to(ROOT))+'/'
m['environment_review']['plant_physics']={'title':'Strawberry canopy · varied leaves and contact','path':prefix+'canopy-v1/plant-response.mp4','replay_path':prefix+'replay.json','report':prefix+'REVIEW.md','summary':'Checkpoint preserved. Varied leaf height, tilt and cupping; lower foliage near the fruit; lighter leaf outlines. Control and contact runs passed the existing rest check. YAM hardware unchanged. Contact-only candidate: cutting unavailable; tissue properties uncalibrated.'}
for label,path in [('Canopy iteration review',prefix+'REVIEW.md'),('Canopy visibility measurements',prefix+'canopy-v1/visibility.json'),('Previous approved plant checkpoint video','assets/workcells/strawberry-harvest/plant-physics/botanical-review/plant-response.mp4'),('Checkpoint file hashes',prefix+'previous-checkpoint.json')]:
 if not any(s.get('path')==path for s in m['sources']):m['sources'].append({'label':label,'path':path})
mp.write_text(json.dumps(m,indent=2))
replay=json.loads((OUT/'replay.json').read_text());assert all((ROOT/o['mesh_path']).exists() for o in replay['objects']);assert (ROOT/m['environment_review']['plant_physics']['path']).stat().st_size>10000
print('Published',len(replay['frames']),'frames; all',len(replay['objects']),'mesh paths verified. Previous checkpoint preserved.')
