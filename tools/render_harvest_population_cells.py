"""One fixed camera, distinct physical two-arm workcells; no camera-only DR."""
from pathlib import Path
import json
import mujoco,numpy as np
from PIL import Image,ImageDraw,ImageFont
P=Path('runs/harvest-skill-suite/population-cells');rows=json.loads((P/'manifest.json').read_text());rows=[r for r in rows if (P/str(r['seed'])/'rest.npz').exists()];board=Image.new('RGB',(1800,1120),'#edf1e7');font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',21)
for i,row in enumerate(rows):
 p=P/str(row['seed']);m=mujoco.MjModel.from_xml_path(str(p/'task/scene.xml'));d=mujoco.MjData(m);d.qpos[:]=np.load(p/'rest.npz')['final_qpos'];mujoco.mj_forward(m,d);renderer=mujoco.Renderer(m,480,600);cam=mujoco.MjvCamera();cam.orthographic=1;cam.lookat[:]=[.32,-.06,.32];cam.distance=1.12;cam.azimuth=90;cam.elevation=-14;renderer.update_scene(d,cam);im=Image.fromarray(renderer.render());im.save(p/'same-camera.png');renderer.close();x=(i%3)*600;y=(i//3)*560;board.paste(im,(x,y+80));draw=ImageDraw.Draw(board);draw.text((x+15,y+8),f"{row['seed']} · {row['split']} · {row['fruit_count']} fruit",font=font,fill='#1c4537');draw.text((x+15,y+36),f"{row['leaf_count']} leaves · {row['status']}",font=font,fill='#1c4537')
draw.text((1220,690),'Same camera. Different physical plants.',font=font,fill='#1c4537');draw.text((1220,730),'72002 excluded: settling failed.',font=font,fill='#a33c25');draw.text((1220,770),'Workcell setup, not trained rollouts.',font=font,fill='#1c4537');board.save(P/'same-camera-comparison.png');print(P/'same-camera-comparison.png')
