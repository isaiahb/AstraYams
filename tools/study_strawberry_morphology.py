"""Observed outline family, parametric 3D priors, and the shared full plant."""
from pathlib import Path
import json,hashlib
import xml.etree.ElementTree as E
import numpy as np,mujoco,trimesh
from PIL import Image,ImageDraw,ImageFont
from strawberry_morphology import OUT,ROOT,measured_spec
from strawberry_surface import envelope,make_fruit,reshape_physical,enrich
import reshape_strawberry as shared

def dump(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2)+'\n')

def library():
    folder=OUT/'library';folder.mkdir(exist_ok=True);rows=[];manifest=[]
    font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',18)
    for i in range(6):
        f=measured_spec(dict(id=f'example_{i}',mass=.018,maturity='red'),f'{i}-0',depth=[.86,.92,.88,.96,.81,.89][i],depth_bend=[.08,-.06,.04,-.09,.10,-.03][i],phase=i*.8)
        shapes,report=make_fruit(f);scene=trimesh.Scene()
        colors={'skin':[161,9,5,255],'achenes':[148,97,27,255],'calyx':[41,79,14,255]}
        for key,g in shapes.items():
            g.visual.vertex_colors=colors[key];scene.add_geometry(g,node_name=key)
        scene.export(folder/f'{i}.glb');collision=envelope(f);collision.export(folder/f'{i}-collision.stl')
        q=f['morphology'];manifest.append(dict(id=str(i),name=q['cultivar'],file=f'library/{i}.glb',parameters=f,collision_volume_mm3=collision.volume*1e9))
        Image.open(OUT/'reference/nagamatsu-fig1.jpg').crop(q['crop_xyxy']).rotate(-90,expand=True).save(OUT/'reference'/f'fruit-{i}.png')
        # Render actual generated surface from orthographic front and 90-degree side.
        assets=E.Element('mujoco');E.SubElement(assets,'asset');w=E.SubElement(assets,'worldbody');E.SubElement(w,'light',pos='-.15 -.25 .2',diffuse='.8 .8 .8',ambient='.4 .4 .4');body=E.SubElement(w,'body',name='fruit_'+f['id'])
        enrich(assets,dict(truss=[dict(fruit=f)]),folder/str(i));E.ElementTree(assets).write(folder/f'{i}.xml',encoding='unicode')
        E.SubElement(assets.find('asset'),'texture',type='skybox',builtin='flat',rgb1='.92 .94 .89',rgb2='.92 .94 .89',width='32',height='32')
        visual=E.SubElement(assets,'visual');E.SubElement(visual,'headlight',ambient='.6 .6 .6',diffuse='.8 .8 .8',specular='.05 .05 .05')
        E.ElementTree(assets).write(folder/f'{i}.xml',encoding='unicode')
        m=mujoco.MjModel.from_xml_path(str(folder/f'{i}.xml'));d=mujoco.MjData(m);mujoco.mj_forward(m,d);m.vis.global_.offwidth=500;m.vis.global_.offheight=500;r=mujoco.Renderer(m,380,330)
        cam=mujoco.MjvCamera();cam.orthographic=1;cam.lookat[:]=[0,0,-.002-f['length']/2];cam.distance=.087;cam.elevation=0
        pair=[]
        for az in [-90,0]:
            cam.azimuth=az;r.update_scene(d,cam);r.scene.flags[mujoco.mjtRndFlag.mjRND_SHADOW]=0;pair.append(Image.fromarray(r.render()))
        r.close();row=Image.new('RGB',(660,420),'#eff2e9');row.paste(pair[0],(0,40));row.paste(pair[1],(330,40));draw=ImageDraw.Draw(row);draw.text((12,8),q['cultivar']+' / observed front + assumed side',font=font,fill='#243b2a');row.save(folder/f'{i}.png');rows.append(row)
    board=Image.new('RGB',(1980,840),'white')
    for i,row in enumerate(rows):board.paste(row,((i%3)*660,(i//3)*420))
    board.save(OUT/'shape-family.png');dump(OUT/'shape-library.json',dict(examples=manifest,scope='Six distinct observed front outlines; depths are assumed. Same 18 g mass to compare shape independent of size.'))
    print('Built six observed-outline 3D variants',flush=True)

def build():
    base=shared.BASE;root=E.parse(base/'scene.xml').getroot();spec=json.loads((base/'reference-graph.json').read_text());fs={b['fruit']['id']:b['fruit'] for b in spec['truss'] if 'fruit' in b}
    # Keep a single cultivar outline family for the example plant. These are
    # interpolated hypotheses, not recovered fruit from the same actual plant.
    fs={
      'primary':measured_spec(fs['primary'],'0-0',.86,.08,blend_id='0-2',blend_weight=.35),
      'secondary_a':measured_spec(fs['secondary_a'],'0-0',.90,-.06,blend_id='0-1',blend_weight=.48),
      'secondary_b':measured_spec(fs['secondary_b'],'0-0',.87,.10,blend_id='0-2',blend_weight=.16),
      'green':measured_spec(fs['green'],'0-0',.97,-.03,blend_id='0-1',blend_weight=.25),
    }
    spec=reshape_physical(root,spec,fs);report=enrich(root,spec,OUT/'meshes');E.indent(root);E.ElementTree(root).write(OUT/'scene.xml',encoding='unicode');dump(OUT/'reference-graph.json',spec)
    a=mujoco.MjModel.from_xml_path(str(base/'scene.xml'));b=mujoco.MjModel.from_xml_path(str(OUT/'scene.xml'))
    unchanged=['body_mass','body_parentid','body_pos','body_quat','jnt_stiffness','dof_damping','dof_armature','qpos_spring','qpos0']
    for attr in unchanged:assert np.array_equal(getattr(a,attr),getattr(b,attr)),attr
    fruit_ids=[b.body('fruit_'+key).id for key in fs];others=[i for i in range(b.nbody) if i not in fruit_ids]
    for attr in ['body_inertia','body_ipos']:assert np.array_equal(getattr(a,attr)[others],getattr(b,attr)[others]),attr
    for key,f in fs.items():
        i=b.body('fruit_'+key).id;geo=envelope(f)
        report[key].update(parameters=f,collision_dimensions_mm=(geo.extents*1000).tolist(),mass_g=b.body_mass[i]*1000,com_m=b.body_ipos[i].tolist(),inertia_kg_m2=b.body_inertia[i].tolist(),collision_volume_mm3=geo.volume*1e9)
    dump(OUT/'shape-audit.json',dict(fruit=report,exactly_unchanged=unchanged+['nonfruit COM and inertia'],
       source_scene_sha256=hashlib.sha256((base/'scene.xml').read_bytes()).hexdigest(),scene_sha256=hashlib.sha256((OUT/'scene.xml').read_bytes()).hexdigest(),
       scope='Single-view photograph-derived family with assumed depth and interpolation. Rigid convex envelopes, no flesh indentation. Green fruit uses a ripe-outline proxy; this is not a measured growth law.'))
    print('Rebuilt full plant with morphology-driven fruit',flush=True)

def settle():shared.OUT=OUT;shared.settle()
def export():
    shared.OUT=OUT;shared.export()
    path=shared.CAD/'specimen-source.json';data=json.loads(path.read_text());data['physics_review']='/'+str((OUT/'plant.html').relative_to(ROOT));data['morphology_review']='/'+str((OUT/'index.html').relative_to(ROOT));dump(path,data)
def render():
    shared.OUT=OUT;shared.OLD=ROOT/'assets/workcells/strawberry-specimen/surface-study/v2';shared.render()
    im=Image.open(OUT/'comparison.png');draw=ImageDraw.Draw(im);draw.rectangle((0,0,1400,59),fill='#edf1e7');font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',24)
    draw.text((20,15),'BEFORE / repeated symmetric profile',font=font,fill='#263f2d');draw.text((720,15),'AFTER / observed outline family',font=font,fill='#263f2d');im.save(OUT/'comparison.png')

def audit():
    from scipy.spatial import ConvexHull
    report={};spec=json.loads((OUT/'reference-graph.json').read_text())
    for branch in spec['truss']:
        if 'fruit' not in branch:continue
        f=branch['fruit'];skin=trimesh.load(OUT/'meshes'/('fruit_detail_'+f['id']+'_skin.stl'),force='mesh')
        pts=np.asarray(skin.vertices)[::max(1,len(skin.vertices)//4096)]
        eq=ConvexHull(envelope(f).vertices).equations;signed=[]
        for start in range(0,len(pts),128):signed.extend(np.max(pts[start:start+128]@eq[:,:3].T+eq[:,3],axis=1))
        values=np.asarray(signed)*1000
        report[f['id']]=dict(skin_samples=len(pts),maximum_inward_plane_gap_mm=float(max(0,-values.min())),median_inward_plane_gap_mm=float(np.median(-values)),maximum_outside_plane_mm=float(max(0,values.max())))
    dump(OUT/'collision-fit.json',dict(method='Sample skin vertices against convex collision-hull planes. Inside-plane distance is a lower bound on surface distance near edges; sampling does not prove a global maximum. Includes visual seed pits.',fruit=report,scope='Contact approximation check, not flesh deformation or calibration.'))

def fit_review():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    profiles=json.loads((OUT/'outline-profiles.json').read_text())['profiles']
    lib=json.loads((OUT/'shape-library.json').read_text())['examples'];report=[]
    fig,axes=plt.subplots(2,3,figsize=(13,8))
    source=Image.open(OUT/'reference/nagamatsu-fig1.jpg')
    for e,ax in zip(lib,axes.flat):
        f=e['parameters'];p=next(p for p in profiles if p['id']==f['morphology']['id']);photo=np.array(source.crop(p['crop_xyxy']));truth=np.array(Image.open(OUT/'reference'/('mask-'+p['id']+'.png')))>0
        geo=trimesh.load(OUT/'library'/e['id']/(f"fruit_detail_{f['id']}_skin.stl"),force='mesh')
        coords=np.c_[p['x_min_px']+(-geo.vertices[:,2]-.002)/f['length']*p['length_px'],p['anchor_y_px']-geo.vertices[:,0]/f['radius']*p['half_width_px']]
        mask=Image.new('L',(truth.shape[1],truth.shape[0]));draw=ImageDraw.Draw(mask)
        for face in geo.faces:draw.polygon([tuple(x) for x in coords[face]],fill=255)
        predicted=np.asarray(mask)>0;iou=float((predicted&truth).sum()/(predicted|truth).sum())
        report.append(dict(id=e['id'],name=e['name'],fitted_view_iou=iou,reference_pixels=int(truth.sum()),scope='In-sample projection fit to the segmented source photograph; not held-out shape or 3D validation. Pixel rasterization included.'))
        ax.imshow(photo);ax.contour(predicted,levels=[.5],colors=['#00e7ed'],linewidths=[1.2]);ax.set_title(f"{e['name']} · fitted-view IoU {iou:.3f}");ax.axis('off')
    fig.suptitle('Project the generated mesh back onto its source photograph',fontsize=18);fig.text(.07,.018,'Cyan is the actual generated skin projection. Remaining calyx-end/tip differences stay visible. This is a fit check, not a held-out validation.',fontsize=10)
    fig.tight_layout(rect=[0,.04,1,.94]);fig.savefig(OUT/'projection-fit.png',dpi=150);plt.close(fig);dump(OUT/'projection-fit.json',report)

if __name__=='__main__':
    import sys
    for name in sys.argv[1:] or ['library','build','settle','export','render']:globals()[name]()
