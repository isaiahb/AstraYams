"""Presentation-only concatenation of audited videos, with explicit playback labels."""
from pathlib import Path
import json,subprocess,hashlib
import imageio.v2 as imageio
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'runs/hackathon-demo'
def run(args):subprocess.run(args,check=True)
def main():
 manifest=json.loads((OUT/'final-demo.json').read_text());segments=[]
 labels={'failure':('1. Find the failure | earlier chain: 2/10 development trials','2x playback | selected failure; different seeds from final evaluation'), 'success':('2. Correct, train and compose | final nominal: 20/20','1x playback | selected final trial, seed 5000'), 'generalization':('3. Test different layouts | 6/6 named cases passed','1x playback | four selected cases; same geometry, different poses')}
 for v in manifest['videos']:
  key=v['id'];speed=2 if key=='failure' else 1;label,note=labels[key]
  (OUT/f'{key}-title.txt').write_text(label);(OUT/f'{key}-note.txt').write_text(note)
  (OUT/'scope.txt').write_text('SIMULATION STATE | learned specialists + scripted control | no hardware validation')
  dst=OUT/f'{key}-reel-segment.mp4';segments.append(dst)
  reader=imageio.get_reader(v['absolute_path']);fps=reader.get_meta_data()['fps'];writer=imageio.get_writer(str(dst),fps=fps*speed,codec='libx264',quality=8,macro_block_size=1)
  fontpath='/System/Library/Fonts/Supplemental/Arial.ttf'
  titlefont=ImageFont.truetype(fontpath,27);font=ImageFont.truetype(fontpath,20)
  try:
   for arr in reader:
    canvas=Image.new('RGB',(1280,720),(12,23,32));frame=Image.fromarray(arr);frame.thumbnail((1280,560));canvas.paste(frame,((1280-frame.width)//2,100+(560-frame.height)//2))
    draw=ImageDraw.Draw(canvas);draw.text((24,20),label,font=titlefont,fill='white');draw.text((24,60),'SIMULATION STATE | learned specialists + scripted control | no hardware validation',font=font,fill=(200,214,223));draw.text((24,682),note,font=font,fill=(255,209,110));writer.append_data(np.asarray(canvas))
  finally:reader.close();writer.close()

 playlist=OUT/'concat.txt';playlist.write_text(''.join(f"file '{p}'\n" for p in segments));reel=OUT/'astra-learning-demo.mp4'
 run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(playlist),'-r','25','-c:v','libx264','-preset','fast','-crf','20','-movflags','+faststart',str(reel)])
 manifest['fallback_reel']={'path':str(reel.relative_to(ROOT)),'absolute_path':str(reel),'url':'/'+str(reel.relative_to(ROOT)),'sha256':hashlib.sha256(reel.read_bytes()).hexdigest(),'description':'Three audited source clips; earlier failure at2x, success and layout trials at1x. Presentation montage, not one continuous rollout.'}
 (OUT/'final-demo.json').write_text(json.dumps(manifest,indent=2)+'\n')
 for p in segments:p.unlink()
 print(reel)
if __name__=='__main__':main()
