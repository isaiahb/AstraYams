"""Presentation-only scene styling; collision/control attributes are invariant."""
from pathlib import Path
import argparse
import json
import xml.etree.ElementTree as E
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def add(parent, tag, **attrs):
    return E.SubElement(parent, tag, {k: str(v) for k, v in attrs.items()})


def camera(parent, name, position, target):
    p, t = np.array(position), np.array(target)
    forward = (t-p)/np.linalg.norm(t-p)
    right = np.cross(forward, [0., 0., 1.]); right /= np.linalg.norm(right)
    up = np.cross(right, forward)
    add(parent, 'camera', name=name, pos=' '.join(map(str,p)), xyaxes=' '.join(map(str,np.r_[right,up])), fovy='38')


def signature(root):
    ignored = {'rgba', 'material', 'group'}
    return [(x.tag, tuple(sorted((k,v) for k,v in x.attrib.items() if k not in ignored)))
            for x in root.iter() if x.tag in {'body','joint','freejoint','inertial','geom','motor','position','velocity','option','exclude','pair','weld'}]


def style(path):
    tree=E.parse(path); root=tree.getroot(); before=signature(root)
    visual=root.find('visual')
    if visual is None: visual=add(root,'visual')
    for child in list(visual):visual.remove(child)
    add(visual,'global',offwidth='1440',offheight='1080')
    add(visual,'quality',shadowsize='4096',offsamples='8')
    add(visual,'headlight',ambient='.28 .28 .3',diffuse='.35 .35 .35',specular='.15 .15 .15')
    add(visual,'rgba',haze='.83 .87 .9 1')
    assets=root.find('asset')
    if assets is None:assets=add(root,'asset')
    for child in list(assets):
        if child.get('name','').startswith('studio_'):assets.remove(child)
    add(assets,'texture',name='studio_sky',type='skybox',builtin='gradient',rgb1='.72 .79 .86',rgb2='.94 .96 .98',width='512',height='3072')
    for name,rgba,spec,shine,reflect in [
        ('studio_arm','.63 .68 .73 1','.65','.65','.03'),
        ('studio_dark','.07 .085 .105 1','.3','.35','0'),
        ('studio_socket','.48 .55 .63 1','.75','.7','.05'),
        ('studio_peg','.92 .47 .10 1','.55','.6','.02'),
        ('studio_bench','.18 .215 .245 1','.2','.2','0')]:
        add(assets,'material',name=name,rgba=rgba,specular=spec,shininess=shine,reflectance=reflect)
    world=root.find('worldbody')
    for child in list(world):
        if child.tag in ['light','camera']:world.remove(child)
    add(world,'light',name='studio_key',pos='.2 -.6 1.4',dir='0 .35 -1',diffuse='.8 .78 .73',specular='.8 .8 .8',castshadow='true',directional='true')
    add(world,'light',name='studio_fill',pos='-.4 .4 .8',dir='.5 -.3 -.8',diffuse='.36 .43 .52',specular='.25 .3 .4',castshadow='false',directional='true')
    add(world,'light',name='studio_rim',pos='.8 .5 1',dir='-.4 -.4 -1',diffuse='.42 .45 .5',specular='.6 .6 .6',castshadow='false',directional='true')
    camera(world,'overview',[.95,-1.05,.82],[.22,0,.19])
    camera(world,'insertion',[.54,-.30,.28],[.32,0,.045])
    for geom in world.iter('geom'):
        label=' '.join([geom.get('name',''),geom.get('mesh','')]).lower()
        material='studio_arm'
        if any(s in label for s in ['bench','table','floor','ground']):material='studio_bench'
        elif any(s in label for s in ['socket','wall']):material='studio_socket'
        elif 'peg' in label:material='studio_peg'
        elif any(s in label for s in ['finger','gripper','mount']):material='studio_dark'
        geom.set('material',material);geom.attrib.pop('rgba',None)
    assert before==signature(root), 'Styling changed physics attributes'
    E.indent(root);tree.write(path,encoding='unicode')
    print(json.dumps({'scene':str(path),'physics_attributes_unchanged':True,'cameras':['overview','insertion']}))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--scene',default=str(ROOT/'tasks/yam_keyed_insertion/scene.xml'))
    style(Path(parser.parse_args().scene))
