"""Still renders of the generated anatomy. No dynamics are stepped."""
from pathlib import Path
import json
import xml.etree.ElementTree as ET
import numpy as np
import mujoco
from PIL import Image, ImageDraw, ImageFont

HERE=Path(__file__).resolve().parent
OUT=HERE.parents[2]/'runs/hemp-whole-plant-v1'


def main():
    data=json.loads((OUT/'plant.json').read_text())
    root=ET.Element('mujoco',model='static_anatomy_render_only')
    ET.SubElement(root,'compiler',angle='radian')
    visual=ET.SubElement(root,'visual')
    ET.SubElement(visual,'global',offwidth='1000',offheight='1100')
    ET.SubElement(visual,'headlight',ambient='.65 .65 .65',diffuse='.55 .55 .55',specular='0 0 0')
    asset=ET.SubElement(root,'asset');world=ET.SubElement(root,'worldbody')
    ET.SubElement(asset,'texture',name='sky',type='skybox',builtin='flat',rgb1='.90 .93 .87',rgb2='.90 .93 .87',width='32',height='32')
    ET.SubElement(world,'geom',name='floor',type='plane',pos='0 0 -.27',size='3 3 .1',rgba='.88 .91 .85 1',contype='0',conaffinity='0')
    ET.SubElement(world,'light',pos='-2 -3 4',dir='2 3 -4',diffuse='.5 .5 .5',castshadow='false')
    meshdir=OUT/'render-meshes';meshdir.mkdir(exist_ok=True)
    for kind,g in data['groups'].items():
        # External OBJ avoids very large XML numeric attributes. These are
        # visual-only meshes; no collision shapes or inertial model are tested.
        obj=meshdir/f'{kind}.obj'
        with obj.open('w') as handle:
            for v in g['vertices']:handle.write('v '+' '.join(f'{x:.9g}' for x in v)+'\n')
            for face in g['faces']:handle.write('f '+' '.join(str(x+1) for x in face)+'\n')
        ET.SubElement(asset,'mesh',name=kind,file=str(obj),maxhullvert='64',inertia='shell')
        color=np.mean(g['colors'],axis=0)
        ET.SubElement(world,'geom',name=kind,type='mesh',mesh=kind,rgba=' '.join(map(str,[*color,1])),contype='0',conaffinity='0',group='1' if kind=='root' else '0')
    model=mujoco.MjModel.from_xml_string(ET.tostring(root,encoding='unicode'))
    state=mujoco.MjData(model);mujoco.mj_forward(model,state)
    renderer=mujoco.Renderer(model,1100,1000);camera=mujoco.MjvCamera();option=mujoco.MjvOption()
    font=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',25)
    small=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',17)
    normal=model.geom_rgba.copy()
    node=next(o['attachment'] for o in data['organs'] if o['kind']=='node' and o.get('rank')==6)
    flower=[o['attachment'] for o in data['organs'] if o['kind']=='inflorescence_axis'][-1]
    cases=[('whole',-65,-10,2.3,[0,0,.44]),('side',10,-12,2.3,[0,0,.44]),
           ('structure',-65,-12,2.3,[0,0,.44]),('node',-65,-20,.30,node),
           ('flower',-65,-20,.23,[flower[0],flower[1],flower[2]+.055]),
           ('roots',-65,-18,.55,[0,0,-.12])]
    for name,az,el,dist,target in cases:
        model.geom_rgba[:]=normal
        for kind in data['groups']:
            visible=kind!='root'
            if name=='structure' and kind in ['leaf','small_leaf','vein','bract','stigma','flower_axis']:visible=False
            if name=='roots':visible=kind in ['root','stem']
            model.geom_rgba[model.geom(kind).id,3]=float(visible)
        option.geomgroup[1]=int(name=='roots')
        camera.azimuth=az;camera.elevation=el;camera.distance=dist;camera.lookat[:]=target
        renderer.update_scene(state,camera,scene_option=option)
        renderer.scene.flags[mujoco.mjtRndFlag.mjRND_CULL_FACE]=False
        im=Image.fromarray(renderer.render());draw=ImageDraw.Draw(im)
        draw.rectangle((0,0,1000,82),fill='#edf0e7')
        draw.text((24,12),f'HEMP / {name.upper()} / anatomy candidate',font=font,fill='#26392f')
        draw.text((24,48),'Static geometry · dimensions and pose assumed · mechanics unvalidated',font=small,fill='#5b6c55')
        im.save(OUT/f'{name}.png')
    renderer.close()
    print('Saved six static model views to',OUT)


if __name__=='__main__':main()
