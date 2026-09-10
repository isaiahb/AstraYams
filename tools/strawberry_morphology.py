"""Photograph-derived longitudinal outlines and explicit unobserved 3D priors.

The digitized curves come from the labelled fruit photographs in Nagamatsu
et al. (2021), Fig. 1, not their symmetric mean EFD drawings. Raster dimensions
are approximate; these are single projections, not recovered 3D scans.
"""
from pathlib import Path
import json
import numpy as np
from scipy import ndimage
from scipy.interpolate import UnivariateSpline, PchipInterpolator
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets/workcells/strawberry-specimen/surface-study/v3'
SOURCE='https://www.jstage.jst.go.jp/article/jsbbs/71/2/71_19106/_html/-char/en'
NAMES=['Fukuoka S6','Kaorino','Sachinoka','06A-184','Beni Hoppe','Ookimi']

def extract():
    image=np.asarray(Image.open(OUT/'reference/nagamatsu-fig1.jpg').convert('RGB'))
    cols=[(100,259),(261,407),(415,553),(558,705),(707,858),(861,1000)]
    rows=[(174,293),(303,415),(417,561)]
    data=[];fig,axes=plt.subplots(3,6,figsize=(15,8.6))
    for ri,(y0,y1) in enumerate(rows):
      for ci,(x0,x1) in enumerate(cols):
        im=image[y0:y1,x0:x1];rgb=im.astype(float);mx=rgb.max(2);mn=rgb.min(2)
        mask=(mx-mn>22)&(rgb[:,:,0]>rgb[:,:,1]*1.02)&(rgb[:,:,0]>rgb[:,:,2]*1.06)&(mx>55)
        mask=ndimage.binary_fill_holes(ndimage.binary_closing(mask,iterations=2))
        labels,n=ndimage.label(mask);sizes=ndimage.sum(mask,labels,range(1,n+1));mask=labels==(1+np.argmax(sizes))
        ys,xs=np.where(mask);xmin,xmax=xs.min(),xs.max();xx=np.arange(xmin,xmax+1)
        upper=np.array([np.where(mask[:,x])[0].min() for x in xx],float)
        lower=np.array([np.where(mask[:,x])[0].max() for x in xx],float)
        # Smooth at the raster uncertainty scale, retaining side-to-side differences.
        t=(xx-xmin)/(xmax-xmin);u=UnivariateSpline(t,upper,s=len(t)*.65)(t);v=UnivariateSpline(t,lower,s=len(t)*.65)(t)
        w=v-u;centre=(v+u)/2;imax=np.argmax(w);half=w[imax]/2
        samples=np.linspace(0,1,41)
        # Center at the calyx-end midline, not at the centroid of the silhouette.
        anchor=np.mean(centre[t<.08]);rn=np.interp(samples,t,w/(2*half));cn=np.interp(samples,t,(anchor-centre)/half)
        key=f'{ci}-{ri}';row=dict(id=key,cultivar=NAMES[ci],panel=['A','B-long','B-broad'][ri],crop_xyxy=[x0,y0,x1,y1],
          x_min_px=int(xmin),anchor_y_px=float(anchor),half_width_px=float(half),
          axis='Calyx left to apex right in source photograph',length_px=int(xmax-xmin),width_px=float(2*half),
          length_width_ratio=float((xmax-xmin)/(2*half)),maximum_width_fraction_from_calyx=float(t[imax]),
          apex_lateral_offset_over_width=float((cn[-1]-cn[0])/2),t=samples.tolist(),radius=rn.tolist(),centre=cn.tolist(),
          uncertainty='Approximately 1–2 pixels per outline; calyx manually removed in source; photograph projection only.')
        data.append(row);ax=axes[ri,ci];ax.imshow(im);ax.plot(xx,u,color='#00c9c9',lw=1);ax.plot(xx,v,color='#00c9c9',lw=1);ax.plot(xx,centre,color='#ffea66',lw=.9)
        Image.fromarray((mask*255).astype('uint8')).save(OUT/'reference'/f'mask-{key}.png')
        ax.set_title(f"{NAMES[ci]} / {row['panel']}\nL/W {row['length_width_ratio']:.2f} · widest at {row['maximum_width_fraction_from_calyx']:.0%}",fontsize=9);ax.axis('off')
    fig.suptitle('Measured photographic outlines — not a repeated ideal cone',fontsize=19,x=.04,ha='left')
    fig.text(.04,.012,'Cyan: segmented + smoothed skin boundary. Yellow: slice midpoint. Nagamatsu et al. (2021), Fig. 1. Single-view measurements; no depth recovery.',fontsize=10)
    fig.tight_layout(rect=[0,.03,1,.95]);fig.savefig(OUT/'outline-analysis.png',dpi=130);plt.close(fig)
    (OUT/'outline-profiles.json').write_text(json.dumps(dict(source=SOURCE,figure=1,method='Color segmentation, largest component, 0.8 px RMS smoothing target, 41 axial samples; inspect overlay.',profiles=data),indent=2)+'\n')
    print([(r['id'],r['cultivar'],round(r['length_width_ratio'],2),round(r['apex_lateral_offset_over_width'],2)) for r in data])

def warp(vertices,f):
    """Deform the common compact mesh using observed width/centerline and depth priors.

    Coordinates are material coordinates: skin, seeds and collision envelope
    receive exactly the same macroscopic mapping. No per-vertex random noise.
    """
    from strawberry_surface import profile
    q=f['morphology'];v=np.asarray(vertices).copy();t=np.clip((-v[:,2]-.002)/f['length'],0,1)
    p=profile(f['radius'],f['length'],'measured_loft');base=np.maximum(p(t),f['radius']*.0001)
    target=PchipInterpolator(q['t'],q['radius'])(t)*f['radius'];centre=PchipInterpolator(q['t'],q['centre'])(t)*f['radius']
    angle=np.arctan2(v[:,1],v[:,0]);radial=target/base
    # Hidden azimuthal structure is explicitly assumed and constrained to leave
    # the observed front contour unchanged at angle 0/pi.
    lobe=1+q['depth_lobe']*np.sin(np.pi*t)**2*np.sin(angle)**2*np.cos(3*angle+q['lobe_phase'])
    v[:,0]=v[:,0]*radial*lobe+centre
    v[:,1]=v[:,1]*radial*lobe*q['depth_width_ratio']*(1+q['depth_taper']*(t-.4))
    v[:,1]+=f['radius']*q['depth_bend']*t*t
    return v

def measured_spec(old,profile_id,depth=.88,depth_bend=.07,depth_taper=-.10,lobe=.035,phase=.4,blend_id=None,blend_weight=0.):
    from strawberry_surface import envelope
    data=json.loads((OUT/'outline-profiles.json').read_text());p=next(p for p in data['profiles'] if p['id']==profile_id)
    if blend_id:
        other=next(p for p in data['profiles'] if p['id']==blend_id)
        p=dict(p)
        for key in ['radius','centre']:
            p[key]=((1-blend_weight)*np.array(p[key])+blend_weight*np.array(other[key])).tolist()
        p['length_width_ratio']=(1-blend_weight)*p['length_width_ratio']+blend_weight*other['length_width_ratio']
        p['blend']=dict(other=blend_id,weight=blend_weight,scope='Interpolation between two observed outlines, not another measured specimen.')
    q=dict(p,depth_width_ratio=depth,depth_bend=depth_bend,depth_taper=depth_taper,depth_lobe=lobe,lobe_phase=phase,
           depth_scope='Unobserved 3D parameters are explicit priors, not reconstructed from the photograph.')
    # Use the normalized shape's actual convex-envelope volume to set scale.
    f=dict(old,radius=1.,length=2*p['length_width_ratio'],surface_profile='measured_loft',flatten_y=1.,morphology=q)
    unit=envelope(f);scale=(old['mass']/1000/unit.volume)**(1/3)
    f.update(radius=float(scale),length=float(scale*2*p['length_width_ratio']),density_assumption_kg_m3=1000.)
    return f

if __name__=='__main__':extract()
