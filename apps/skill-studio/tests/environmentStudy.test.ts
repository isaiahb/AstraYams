import {describe,expect,test} from 'bun:test';
import {readEnvironmentStudy} from '../src/environmentStudySchema';
import {ENVIRONMENT_STUDY_INSTRUCTIONS} from '../environmentStudyPrompt';
import {resolve} from 'node:path';

const root=resolve(import.meta.dir,'../../..');
const recorded=await Bun.file(resolve(root,'assets/workcells/strawberry-specimen/study.json')).json();
const fresh=()=>({schema_version:1,provenance:'current-run',title:'A new fixture',status:'Gathering references',scope:'No simulation run yet',objective:'Check tool access',sources:[],revisions:[],experiments:[],assumptions:[],next_steps:['Inspect the input CAD']});

describe('Environment study publication',()=>{
  test('a new task can publish honestly before sources or tests exist',()=>{
    expect(readEnvironmentStudy(fresh()).experiments).toHaveLength(0);
  });
  test('a recorded study cannot silently become unspecified live activity',()=>{
    expect(()=>readEnvironmentStudy({...recorded,provenance:undefined})).toThrow('provenance');
  });
  test('a completed test needs an evidence artifact',()=>{
    const copy=structuredClone(recorded);delete copy.experiments[0].result_path;
    expect(()=>readEnvironmentStudy(copy)).toThrow('result artifact');
  });
  test('malformed media paths are rejected before the view tries to render them',()=>{
    const copy=structuredClone(recorded);copy.preview_path={path:'image.png'};
    expect(()=>readEnvironmentStudy(copy)).toThrow('repository-relative');
    expect(()=>readEnvironmentStudy({...recorded,preview_path:'../../other-project/image.png'})).toThrow('repository-relative');
  });
  test('decisions must point to real source records with safe source links',()=>{
    const copy=structuredClone(recorded);copy.revisions[0].source_ids=['missing'];
    expect(()=>readEnvironmentStudy(copy)).toThrow('unknown source');
    const unsafe=structuredClone(recorded);unsafe.sources[0].url='javascript:alert(1)';
    expect(()=>readEnvironmentStudy(unsafe)).toThrow('source URL');
  });
  test('published strawberry metrics agree with saved simulator results and controls',async()=>{
    const study=readEnvironmentStudy(recorded);
    expect(study.provenance).toBe('recorded');
    for(const e of study.experiments){
      const r=await Bun.file(resolve(root,e.result_path!)).json();
      const c=await Bun.file(resolve(root,e.control_path!)).json();
      expect(r.valid_run&&r.target_touched).toBe(true);
      expect(r.initial_probe_contacts).toHaveLength(0);
      expect(c.probe_contacts).toEqual({});
      expect(r.probe_start_m).toEqual(c.probe_start_m);
      expect(r.probe_end_m).toEqual(c.probe_end_m);
      const contacts=Object.values(r.probe_contacts) as {peak_force_n:number,max_penetration_mm:number}[];
      expect(e.metrics[0].value).toBe(Math.max(...contacts.map(x=>x.peak_force_n)).toFixed(3)+' N');
      expect(e.metrics[1].value).toBe(Math.max(...contacts.map(x=>x.max_penetration_mm)).toFixed(3)+' mm');
    }
  });
  test('the future engineer contract preserves provenance and physical acceptance criteria',()=>{
    expect(ENVIRONMENT_STUDY_INSTRUCTIONS).toContain('environment_study_path');
    expect(ENVIRONMENT_STUDY_INSTRUCTIONS).toContain('Preserve fixed acceptance criteria');
    expect(ENVIRONMENT_STUDY_INSTRUCTIONS).toContain('not private chain-of-thought');
  });
});
