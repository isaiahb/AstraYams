"""Build scientific comparison plates from credited photos and unchanged sim renders.

No AI image synthesis, photo warping, plant edits, or product UI changes.
Photo crops, viewpoint limitations and source conditions stay explicit.
"""
from pathlib import Path
import json,textwrap
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'assets/workcells/strawberry-specimen/morphology-review-2026-09-09'
S={r['id']:r for r in json.loads((P/'sources.json').read_text())}
BG='#f4f2ec';INK='#20382b';MUTED='#546359';ORANGE='#b9512b'
plt.rcParams.update({'font.family':'DejaVu Sans','text.color':INK,'axes.titlecolor':INK})

def page(title,subtitle,size=(16,11)):
 fig=plt.figure(figsize=size,facecolor=BG)
 fig.text(.035,.955,title,fontsize=25,weight='bold',va='top')
 fig.text(.035,.907,subtitle,fontsize=11.5,color=MUTED,va='top')
 return fig

def panel(fig,box,path,title,caption,crop=None,title_size=13):
 ax=fig.add_axes(box);im=Image.open(path);ax.imshow(im);ax.axis('off');ax.set_title(title,loc='left',fontsize=title_size,pad=11,weight='bold')
 if crop:
  x0,y0,x1,y1=crop;ax.set_xlim(x0,x1);ax.set_ylim(y1,y0)
 fig.text(box[0],box[1]-.012,caption,fontsize=9.3,color=MUTED,va='top',linespacing=1.5)
 return ax,im.size

def photo(id):return ROOT/S[id]['local_file']
def mark(ax,size,n,point,offset=(20,20)):
 x,y=point[0]*size[0],point[1]*size[1]
 ax.annotate(str(n),xy=(x,y),xytext=offset,textcoords='offset points',ha='center',va='center',fontsize=12,weight='bold',color='white',bbox=dict(boxstyle='circle,pad=.30',fc=ORANGE,ec='white',lw=1.5),arrowprops=dict(arrowstyle='-',color=ORANGE,lw=2))
def footer(fig,text):fig.text(.035,.035,text,fontsize=9,color=MUTED,va='bottom')
def save(fig,name):fig.savefig(P/name,dpi=150,facecolor=BG);plt.close(fig)

def whole():
 fig=page('01 / Spot the difference: whole plant','Comparable oblique views. Different specimens and containers; no shared metric scale or calibrated camera match.')
 a,sz=panel(fig,[.035,.28,.43,.57],photo('osu-whole'),'REAL / Standing field plant',"Bernadine Strik / Oregon State University, Figure 1. Foreground crop;\nneighboring foliage remains. Immature fruit; standing plant.",(0,380,1500,1994))
 for n,point,offset in [(1,(.54,.64),(-30,-6)),(2,(.38,.42),(-18,25)),(3,(.555,.785),(32,-4))]:mark(a,sz,n,point,offset)
 b,sz=panel(fig,[.52,.28,.445,.57],P/'renders/whole-standing.png','OURS / v7, saved gravity-settled pose','Same model and saved state as the contact tests. One crown in a trough.\nNo geometry, stiffness, lighting style or pose was adjusted to improve this comparison.')
 for n,point,offset in [(1,(.416,.433),(-14,33)),(2,(.80,.49),(24,10)),(3,(.51,.53),(-35,-5))]:mark(b,sz,n,point,offset)
 notes=[('1  Stalk curve','Several model stalks arch outward early. The standing reference shows steeper paths supporting the leaves.'),('2  Leaf orientation','Several model leaflets hang edge-on. The reference has cupped surfaces with more visible upper faces.'),('3  Crown / new growth','Our simple exposed hub lacks the layered bases and developing central leaves visible in the reference.')]
 for i,(head,body) in enumerate(notes):
  x=.035+i*.323;fig.text(x,.183,head,fontsize=13,weight='bold');fig.text(x,.151,textwrap.fill(body,48),fontsize=11,va='top',linespacing=1.45)
 footer(fig,'Visual hypotheses for the next edit, not measured biological parameters. Sources and comparison conditions are recorded in sources.json.')
 save(fig,'01-whole-plant.png')

def crowns():
 fig=page('02 / Crown and roots: five reference views','Photos show attachment anatomy across conditions. Dug, held-apart and trimmed specimens do not supply standing stem angles.',(17,13))
 panels=[
 ('arkansas-branch','A / Field plant, held apart','Arkansas Extension. Main and branch crowns are labeled.\nHands disturb the stalk positions; compare connections.'),
 ('calpoly-trimmed','B / Trimmed bare-root crown','Gerald Holmes / Cal Poly. Clipped stalks expose the bases.\nDo not use this silhouette as the mature plant target.'),
 ('unl-large-crown','C / Large crown, dug for storage','University of Nebraska–Lincoln. Soil and older tissue remain.\nUseful base/root transition; not an undisturbed pose.'),
 ('calpoly-uprooted','D / Whole plant, uprooted','Cal Poly Strawberry Center. Petioles and roots differ in\ntexture and branching. Laid-out plant, not standing geometry.'),
 ('osu-crown','E / Older container crown, winter','Bernadine Strik / Oregon State University, Figure 8.\nLow-resolution context: growth and substrate interface.'),
 ]
 boxes=[(.035,.535,.288,.305),(.355,.535,.288,.305),(.675,.535,.288,.305),(.035,.135,.288,.305),(.355,.135,.288,.305),(.675,.135,.288,.305)]
 for (id,title,cap),box in zip(panels,boxes):panel(fig,box,photo(id),title,cap,title_size=12)
 ax,sz=panel(fig,boxes[5],P/'renders/attachment-cutaway.png','F / OURS: inspection cutaway','Only crown and proximal stalks shown; soil and distal parts\nhidden for rendering. Biological roots are NOT modeled.',title_size=12)
 ax.annotate('No root system',xy=(500,455),xytext=(500,745),ha='center',fontsize=12,weight='bold',color=ORANGE,arrowprops=dict(arrowstyle='->',color=ORANGE,lw=2))
 footer(fig,'Repeated concern: a single simplified hub misses the layered attachments. Branch crowns depend on plant history; not every plant has them.\nMetric dimensions, hidden connections and tissue mechanics cannot be recovered from these unrelated photographs.')
 save(fig,'02-crown-roots.png')

def environments():
 fig=page('03 / Keep the growing context in the comparison','Young potted plant, mature container planting and a crop row are different cases. Do not average their shapes into one plant.',(17,14))
 rows=[
 ('unl-pot','A / Young Evie-2 in a nursery pot','UNL. Leaves overlap near the center; flower stage is visible.','whole-high.png','OURS / Higher oblique view','Same v7 state; not transplanted into a new pot.'),
 ('osu-containers','B / Rectangular container examples','OSU Figure 7, A–D. Mixed stages/plant counts; low source resolution.','whole-standing.png','OURS / One crown in a rectangular trough','Compare leaf attitude and growth center; do not equate plant density.'),
 ('osu-tabletop','C / Mature greenhouse trough row','Meteor Systems via Ohio State Kubota Lab. Crowns overlap.','trough-side.png','OURS / Low side view at the trough edge','Compare truss path, rim contact and visible fruit. One plant, not a row.'),
 ]
 for i,(id,title,cap,render,stitle,scap) in enumerate(rows):
  y=.64-i*.275
  panel(fig,[.035,y,.435,.195],photo(id),title,cap,title_size=12)
  panel(fig,[.53,y,.435,.195],P/'renders'/render,stitle,scap,title_size=12)
 footer(fig,'Use the trough crop for the intended harvesting environment. Use isolated/potted plants to understand each crown.\nThese are viewing-direction comparisons only: camera elevation, cultivar, age, loading and pruning are not matched experiments.')
 save(fig,'03-environments.png')

if __name__=='__main__':
 whole();crowns();environments();print(P)
