from lab import *
import hashlib
out=HERE/'batch-stratified';out.mkdir(exist_ok=True);results=[];tiles=[]
for i in range(9):
 seed=7100+i;rng=np.random.default_rng(seed);it=i//3+1;c=copy.deepcopy(CONFIGS[it]);c['title']=f'Sample {i+1:02d} / '+c['layout'];c['width']=float([.46,.59,.72][i%3]+rng.uniform(-.007,.007));c['depth']=float([.145,.085,.115][i%3]+rng.uniform(-.003,.003));c['top']=float([.445,.47,.49][i%3]);c['leaf_count']=int(rng.integers(12,31));c['targets']=(np.array(c['targets'])+rng.uniform([-.008,-.008,-.006],[.008,.008,.006],(3,3))).tolist();dest=out/f'seed-{seed}'
 e,reset=make(c,dest,seed);metrics=render(e,c,dest);pids=[j for j in range(e.model.ngeom) if e.model.geom(j).name.startswith('planter_')]
 minimum=10.
 for j in range(3):
  fid=e.model.geom('berry_collision'+('' if j==0 else '_'+str(j))).id
  for gid in pids:minimum=min(minimum,mujoco.mj_geomDistance(e.model,e.data,fid,gid,2,None))
 # Short actual simulation smoke test, not a successful harvest episode.
 poses=[];actions=[]
 for _ in range(25):
  a=controller(e);_,_,_,_,info=e.step(a);actions.append(a);poses.append(e.data.qpos.copy())
 np.savez_compressed(dest/'smoke-episode.npz',qpos=poses,actions=actions)
 maxik=max(reset[1]['reset_ik_error_m'].values());passed=bool(minimum>.01 and maxik<.001 and np.all(np.isfinite(e.data.qpos)))
 cameras={}
 for name in ['cut_wrist_d405','catch_wrist_d405']:
  idx=e.model.camera(name).id;cameras[name]={'position_world_m':e.data.cam_xpos[idx].tolist(),'rotation_world':e.data.cam_xmat[idx].reshape(3,3).tolist(),'nominal_fov_degrees':[87,58]}
 sensor=mujoco.Renderer(e.model,288,512)
 for name in cameras:
  sensor.update_scene(e.data,camera=name);Image.fromarray(sensor.render().copy()).save(dest/(name+'-rgb.png'))
  sensor.enable_depth_rendering();depth=sensor.render().copy();sensor.disable_depth_rendering();np.savez_compressed(dest/(name+'-depth.npz'),depth_m=depth)
  sensor.enable_segmentation_rendering();seg=sensor.render().copy();sensor.disable_segmentation_rendering();np.savez_compressed(dest/(name+'-segmentation.npz'),object_id=seg[:,:,0],object_type=seg[:,:,1])
  cameras[name]['timestamp_sim_s']=float(e.data.time);cameras[name]['resolution']=[512,288];cameras[name]['nominal_focal_pixels']=[512/(2*np.tan(np.radians(87/2))),288/(2*np.tan(np.radians(58/2)))];cameras[name]['principal_point_pixels']=[256,144]
 sensor.close();np.savez_compressed(dest/'sensor-state.npz',qpos=e.data.qpos,qvel=e.data.qvel,time=e.data.time)
 (dest/'geometry-labels.json').write_text(json.dumps([{'id':j,'name':e.model.geom(j).name,'body':e.model.body(e.model.geom_bodyid[j]).name} for j in range(e.model.ngeom)]))
 row={'seed':seed,'layout':c['layout'],'config':c,'preview':'seed-'+str(seed)+'/review.png','minimum_fruit_planter_clearance_m':minimum,'max_reset_ik_residual':maxik,'finite_smoke_steps':25,'simulated_seconds':info['time'],'geometry_gate_pass':passed,'sensor_preview':metrics,'cameras_after_smoke':cameras,'scene_sha256':hashlib.sha256((dest/'scene.xml').read_bytes()).hexdigest(),'scope':'Environment sample and 0.5 s simulation check; not a completed harvest or trained policy.'};(dest/'sample.json').write_text(json.dumps(row,indent=2));results.append(row)
 im=Image.open(dest/'review.png').crop((20,150,1044,726)).resize((512,288));tile=Image.new('RGB',(530,360),(246,243,234));tile.paste(im,(9,8));dr=ImageDraw.Draw(tile);text(dr,(12,303),f'{seed}  {c["layout"]}  /  {c["width"]*1000:.0f} × {c["depth"]*1000:.0f} mm',17,True);text(dr,(12,332),'Clearance + reset: '+('pass' if passed else 'reject'),17);tiles.append(tile);print(seed,passed,minimum,flush=True);e.close()
grid=Image.new('RGB',(1590,1170),(246,243,234));dr=ImageDraw.Draw(grid);text(dr,(24,15),'NINE DIFFERENT WORLDS / RECORDED ENVIRONMENT SAMPLES',27,True);text(dr,(24,53),'Geometry + fruit layout + foliage. 0.5 s checks, not successful harvest demonstrations.',20)
for i,t in enumerate(tiles):grid.paste(t,((i%3)*530,90+(i//3)*360))
grid.save(out/'gallery.png');(out/'manifest.json').write_text(json.dumps({'samples':results,'limits':'Ranges are design exploration assumptions, not calibrated farm distributions. Visual-only canopy; no deformable foliage physics. Camera calibration and robot hardware remain fixed.','geometry_passes':sum(r['geometry_gate_pass'] for r in results)},indent=2))
