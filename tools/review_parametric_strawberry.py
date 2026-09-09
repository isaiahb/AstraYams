"""Matched simulation views and a credited, non-metric real-plant comparison."""
from pathlib import Path
import argparse,json,hashlib
import mujoco,numpy as np
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'assets/workcells/strawberry-specimen'
OUT=BASE/'parametric-study'

def render(path,kind='whole'):
    m=mujoco.MjModel.from_xml_path(str(path/'scene.xml'));d=mujoco.MjData(m)
    d.qpos[:]=np.load(path/'rest/rollout.npz')['qpos'][-1];mujoco.mj_forward(m,d)
    cam=mujoco.MjvCamera();cam.lookat[:]=[0,.035,.32];cam.distance=.70;cam.azimuth=105;cam.elevation=-25
    if kind=='crown':cam.lookat[:]=[0,.055,.307];cam.distance=.22;cam.azimuth=125;cam.elevation=-25
    rr=mujoco.Renderer(m,800,700);rr.update_scene(d,cam);im=Image.fromarray(rr.render());rr.close()
    (path/'review').mkdir(exist_ok=True);im.save(path/'review'/f'{kind}.png')
    return im

def plate(candidate='v12'):
    plt.rcParams.update({'font.family':'DejaVu Sans','text.color':'#233c2e','font.size':11})
    images={}
    for name,path in [('v7',BASE/'basal-study/v7'),('v11',OUT/'v11'),(candidate,OUT/candidate)]:
        images[name]={kind:render(path,kind) for kind in ['whole','crown']}
    ref=Image.open(BASE/'morphology-review-2026-09-09/references/osu-whole.png').crop((0,380,1500,1994))
    fig,axes=plt.subplots(1,3,figsize=(16,8),facecolor='#f3f2ec')
    for ax,im,title,caption in zip(axes,[ref,images['v7']['whole'],images[candidate]['whole']],
        ['REAL / standing field plant','BEFORE / v7',f'CURRENT / {candidate}'],
        ['Bernadine Strik / Oregon State, Fig. 1.\nForeground crop; neighboring plants overlap.\nDifferent growth stage and container.',
         'Earlier loaded geometry.\nOne modulus across all leaf stalks;\nearly arching, hanging leaf faces.',
         'Explicit growth paths, staggered bases,\ncentral young growth, corrected leaf frames,\nage-stratified petiole-modulus prior.']):
        ax.imshow(im);ax.set_title(title,loc='left',fontweight='bold',pad=14);ax.axis('off');ax.text(0,-.035,caption,transform=ax.transAxes,va='top',fontsize=10,linespacing=1.4)
    fig.suptitle('Research → model revision → physical checks',x=.035,ha='left',fontsize=23,fontweight='bold',y=.96)
    fig.text(.035,.887,'Model panels use the same camera and saved gravity-settled states. Real photograph is a structural reference, not a calibrated reconstruction.',fontsize=11)
    fig.text(.035,.035,'Still unresolved: continuous leaf mechanics • full crown/root structure • measured contact response • cutting / damage\nAll motion is simulated; parameters are not calibrated to a real specimen.',fontsize=11,linespacing=1.5)
    fig.subplots_adjust(left=.035,right=.98,top=.84,bottom=.20,wspace=.10)
    fig.savefig(OUT/'whole-plant-progress.png',dpi=150);plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(16,7),facecolor='#f3f2ec')
    for ax,name,title in zip(axes,['v7','v11',candidate],['v7 / original','v11 / geometry + leaf mass',f'{candidate} / age-dependent modulus']):
        ax.imshow(images[name]['crown']);ax.set_title(title,loc='left',fontweight='bold');ax.axis('off')
    fig.suptitle('Crown and stalks / same camera, loaded poses',x=.035,ha='left',fontsize=21,fontweight='bold')
    fig.text(.035,.075,'The v11 → current comparison holds shape and mass fixed. Modulus changes with leaf age; the existing stiffness-proportional damping rule remains.\nCrown remains fixed; roots and root/soil motion are absent. These are inspectable hypotheses, not a validated digital twin.',fontsize=11,linespacing=1.5)
    fig.subplots_adjust(left=.035,right=.98,top=.87,bottom=.18,wspace=.07)
    fig.savefig(OUT/'crown-progress.png',dpi=150);plt.close(fig)
    (OUT/'review-provenance.json').write_text(json.dumps({'reference':'https://extension.oregonstate.edu/catalog/pub/ec-1307-growing-strawberries-your-home-garden','credit':'Bernadine Strik / Oregon State University, Figure 1','comparison':'approximate viewing direction only; different specimens, no calibrated shared scale','candidate':candidate,'models':{name:hashlib.sha256(((BASE/'basal-study/v7' if name=='v7' else OUT/name)/'scene.xml').read_bytes()).hexdigest() for name in images}},indent=2))
    print(OUT/'whole-plant-progress.png')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--candidate',default='v12');a=p.parse_args();plate(a.candidate)
