"""Matched-camera renders of independently generated physical specimens."""
from pathlib import Path
import json
import mujoco,numpy as np
from PIL import Image,ImageDraw,ImageFont
P=Path('runs/harvest-skill-suite/population');manifest=json.loads((P/'manifest.json').read_text());board=Image.new('RGB',(1800,1160),'#edf1e7');font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',21)
for i,row in enumerate(manifest):
 p=P/str(row['seed']);m=mujoco.MjModel.from_xml_path(str(p/'scene.xml'));d=mujoco.MjData(m);d.qpos[:]=np.load(p/'initial-state.npz')['qpos'];mujoco.mj_forward(m,d);r=mujoco.Renderer(m,500,600);cam=mujoco.MjvCamera();cam.orthographic=1;cam.lookat[:]=[0,-.015,.24];cam.distance=.80;cam.azimuth=90;cam.elevation=-8;r.update_scene(d,cam);im=Image.fromarray(r.render());im.save(p/'same-camera.png');r.close();x=(i%3)*600;y=(i//3)*580;board.paste(im,(x,y+80));draw=ImageDraw.Draw(board);counts={k:sum(f['maturity']==k for f in row['fruit']) for k in ['red','turning','green']};draw.text((x+15,y+8),f"Seed {row['seed']} · {row['fruit_count']} fruit · {row['leaf_count']} leaves",font=font,fill='#1c4537');draw.text((x+15,y+34),f"ripe {counts['red']} / turning {counts['turning']} / green {counts['green']}",font=font,fill='#1c4537');draw.text((x+15,y+59),'Settled' if row['quiet'] else 'REJECTED: still moving after settling',font=font,fill='#1c4537' if row['quiet'] else '#a33c25')
board.save(P/'same-camera-comparison.png');print(P/'same-camera-comparison.png')
