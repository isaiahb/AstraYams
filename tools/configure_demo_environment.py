#!/usr/bin/env python3
"""Package and compile prepared demo environments; never train or claim task success.

Run with the project Python environment (MuJoCo required). JSONL progress is
emitted to stdout and the same event history is persisted in progress.json.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
SCENARIOS={
 'keyed-insertion':{'scene':'tasks/yam_contact_curriculum/scene.xml','task':'tasks/yam_contact_curriculum','env_class':'astrafactory.contact_curriculum:CurriculumEnv','status':'prepared free-object articulated-YAM task'},
 'machine-tending':{'scene':'tasks/yam_machine_tending/scene.xml','task':'tasks/yam_machine_tending','env_class':'astrafactory.machine_tending:MachineTendingEnv','status':'prepared powered-vise machine-tending task'},
 'manual-vise':{'scene':'runs/bimanual-vise-design/scene.xml','builder':'tools/check_bimanual_vise_layout.py','env_class':None,'status':'untrained dual-arm manual-vise MuJoCo design scene; Gym task and learning not supplied'},
}


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def atomic_json(path,value):
    temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n');temporary.replace(path)


class Progress:
    def __init__(self,output,scenario):self.output=output;self.scenario=scenario;self.started=time.monotonic();self.events=[]
    def emit(self,stage,status,message,**details):
        event={'schema_version':1,'event':'stage','scenario':self.scenario,'stage':stage,'status':status,
               'elapsed_s':round(time.monotonic()-self.started,6),'message':message,'details':details}
        self.events.append(event)
        atomic_json(self.output/'progress.json',{'schema_version':1,'scenario':self.scenario,'status':('failed' if status=='failed' else 'complete' if stage=='complete' else 'running'),
                    'current_stage':stage,'elapsed_s':event['elapsed_s'],'events':self.events})
        print(json.dumps(event,allow_nan=False),flush=True)


def configure(scenario,output):
    import mujoco
    import numpy as np
    output=Path(output).expanduser().resolve()
    if output.exists() and any(output.iterdir()):raise ValueError('Output must be a new or empty directory; existing bundles are preserved.')
    output.mkdir(parents=True,exist_ok=True);progress=Progress(output,scenario);template=SCENARIOS[scenario]
    try:
        progress.emit('resolve_template','running','Resolving an existing prepared scene; no new design or training is implied.')
        source=ROOT/template['scene'];builder_record=None
        if not source.exists() and 'builder' in template:
            builder=ROOT/template['builder'];env=os.environ.copy();env['PYTHONPATH']=str(ROOT/'src')+os.pathsep+env.get('PYTHONPATH','')
            progress.emit('resolve_template','running','Building the missing prepared manual-vise design scene.',builder=template['builder'])
            start=time.monotonic()
            with (output/'template-builder.log').open('w') as log:
                subprocess.run([sys.executable,str(builder)],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=120)
            builder_record={'path':template['builder'],'sha256':sha(builder),'elapsed_s':time.monotonic()-start,'log':'template-builder.log'}
        if not source.is_file():raise FileNotFoundError(source)
        source_hash=sha(source);tree=ET.parse(source);root=tree.getroot()
        if root.findall('.//include'):raise ValueError('Prepared scene unexpectedly has XML includes; flatten explicitly before packaging.')
        progress.emit('resolve_template','complete','Prepared scene selected.',source=template['scene'],source_sha256=source_hash,template_status=template['status'])
        progress.emit('bundle_assets','running','Copying referenced assets and rewriting resource paths only.')
        assets=output/'assets';assets.mkdir();compiler=root.find('compiler');comp={} if compiler is None else dict(compiler.attrib);records=[];copied={}
        for element in root.findall('.//*[@file]'):
            original=element.get('file');kind=element.tag
            directory=comp.get('meshdir' if kind=='mesh' else 'texturedir' if kind=='texture' else 'assetdir',comp.get('assetdir',''))
            path=Path(original)
            resolved=path if path.is_absolute() else source.parent/ directory/path
            resolved=resolved.resolve()
            if not resolved.is_file():raise FileNotFoundError(f'{kind} resource {original}: {resolved}')
            digest=sha(resolved);key=(digest,resolved.suffix.lower())
            if key not in copied:
                filename=digest[:20]+'_'+resolved.name;destination=assets/filename;shutil.copyfile(resolved,destination)
                if sha(destination)!=digest:raise RuntimeError(f'Asset copy hash mismatch: {resolved}')
                copied[key]='assets/'+filename
            element.set('file',copied[key]);records.append({'kind':kind,'name':element.get('name'),'original_reference':original,
               'source_path':str(resolved.relative_to(ROOT)) if resolved.is_relative_to(ROOT) else str(resolved),
               'bundle_path':copied[key],'sha256':digest,'bytes':resolved.stat().st_size})
        if compiler is not None:
            for key in ['meshdir','texturedir','assetdir']:compiler.attrib.pop(key,None)
        tree.write(output/'scene.xml',encoding='unicode')
        task_files=[]
        if 'task' in template:
            for name in ['task.json','task.py','reward.py']:
                source_file=ROOT/template['task']/name
                if source_file.exists():shutil.copyfile(source_file,output/name);task_files.append({'path':name,'source':str(source_file.relative_to(ROOT)),'sha256':sha(source_file)})
        progress.emit('bundle_assets','complete','Referenced assets copied and hashed.',asset_references=len(records),unique_assets=len(copied),asset_bytes=sum((output/v).stat().st_size for v in copied.values()))
        progress.emit('compile_model','running','Loading source and portable bundle with MuJoCo; checking matching model parameters.')
        original_model=mujoco.MjModel.from_xml_path(str(source));model=mujoco.MjModel.from_xml_path(str(output/'scene.xml'))
        arrays=['body_mass','body_inertia','body_pos','body_quat','body_ipos','body_iquat','jnt_type','jnt_axis','jnt_pos','jnt_range','qpos0',
                'geom_type','geom_pos','geom_quat','geom_size','geom_contype','geom_conaffinity','geom_friction','actuator_gainprm','actuator_biasprm','actuator_ctrlrange','eq_data']
        for name in arrays:
            if not np.array_equal(getattr(original_model,name),getattr(model,name)):raise RuntimeError(f'Bundling altered compiled model parameter {name}')
        data=mujoco.MjData(model);mujoco.mj_forward(model,data)
        if not np.isfinite(data.qpos).all() or not np.isfinite(data.qvel).all():raise RuntimeError('Nonfinite initial MuJoCo state')
        statistics={name:int(getattr(model,name)) for name in ['nq','nv','nu','ngeom','nbody','njnt','nmesh','neq']}
        statistics.update(timestep_s=float(model.opt.timestep),gravity_m_s2=model.opt.gravity.tolist())
        progress.emit('compile_model','complete','MuJoCo loaded both scenes; model parameters match.',model=statistics,verified_parameter_arrays=arrays)
        gym_smoke=None
        if template['env_class']:
            import importlib
            module,class_name=template['env_class'].split(':')
            cls=getattr(importlib.import_module(module),class_name)
            env=cls(str(output))
            try:
                observation,_=env.reset(seed=42)
                next_observation,reward,terminated,truncated,info=env.step(np.zeros(env.action_space.shape))
                assert np.isfinite(observation).all() and np.isfinite(next_observation).all() and np.isfinite(reward)
                gym_smoke={'reset_seed':42,'steps':1,'finite':True,'terminated':bool(terminated),'truncated':bool(truncated),'scope':'Single zero-action smoke check, not a task rollout.'}
            finally:env.close()
        progress.emit('write_report','running','Writing configuration provenance and explicit validation limits.')
        environment={'schema_version':1,'scenario':scenario,'scene':'scene.xml','env_class':template['env_class'],
          'task_config':'task.json' if 'task' in template else None,'prepared_template':True,
          'runtime_requirement':'Project astrafactory Python package and its dependencies are required for task plugins.',
          'learning_run':None,'trained_policy':None,'manual_machine_interface':'Powered vise command separate from robot actions.' if scenario=='machine-tending' else None}
        atomic_json(output/'environment.json',environment)
        report={'schema_version':1,'scenario':scenario,'status':'configured_and_mujoco_loaded','prepared_template':True,
          'template_status':template['status'],'source_scene':template['scene'],'source_scene_sha256':source_hash,
          'bundled_scene':'scene.xml','bundled_scene_sha256':sha(output/'scene.xml'),'tool_source_sha256':sha(Path(__file__)),
          'mujoco_version':mujoco.__version__,'model':statistics,'assets':records,'task_files':task_files,'builder':builder_record,
          'validation':{'mujoco_load':True,'initial_forward_finite':True,'source_parameter_arrays_identical':arrays,
                        'gym_reset_step_tested':gym_smoke is not None,'gym_smoke':gym_smoke,'physical_task_rollout_tested':False,'training_performed':False,'task_success_claim':False},
          'provenance_note':'Prepared scene configuration and asset packaging, not prompt-generated CAD or a newly trained policy.',
          'limitations':['Model compilation does not prove contact stability, collision clearance, reachability or task success.',
                         'Manual-vise is a design scene, not a completed Gym task or demonstrated bimanual manipulation.'] if scenario=='manual-vise' else
                        ['Model compilation does not prove contact stability, collision clearance, reachability or task success.'],
          'elapsed_s':time.monotonic()-progress.started}
        atomic_json(output/'configuration-report.json',report)
        progress.emit('write_report','complete','Environment bundle configured; no training or task-success claim.',report='configuration-report.json',environment='environment.json')
        progress.emit('complete','complete','Configuration finished.',report=str(output/'configuration-report.json'),elapsed_s_actual=time.monotonic()-progress.started)
        return report
    except Exception as error:
        progress.emit('failed','failed',str(error),error_type=type(error).__name__)
        raise


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--scenario',required=True,choices=SCENARIOS);parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    try:configure(args.scenario,args.output)
    except Exception as error:print(f'Configuration failed: {error}',file=sys.stderr);return 1
    return 0


if __name__=='__main__':raise SystemExit(main())
