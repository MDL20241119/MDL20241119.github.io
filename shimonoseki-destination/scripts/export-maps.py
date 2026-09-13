"""Export the generated SVG maps to WebP using Inkscape and Pillow.
PNG embedding in the temporary render copy supports older Inkscape builds.
Published SVGs embed WebP and remain independently viewable in modern browsers.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
import base64,io,os,subprocess,tempfile,sys
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'assets'
replacements={}
for name in ['map-landmarks-sheet','after-dark-play-sheet']:
 raw=(OUT/(name+'.webp')).read_bytes();buf=io.BytesIO();Image.open(io.BytesIO(raw)).save(buf,format='PNG')
 replacements['data:image/webp;base64,'+base64.b64encode(raw).decode()]='data:image/png;base64,'+base64.b64encode(buf.getvalue()).decode()
def render(p):
 with tempfile.TemporaryDirectory() as temp:
  t=Path(temp);svg=p.read_text()
  for a,b in replacements.items():svg=svg.replace(a,b)
  (t/'map.svg').write_text(svg)
  r=subprocess.run(['inkscape',str(t/'map.svg'),'--export-filename='+str(t/'map.png')],capture_output=True,text=True)
  if r.returncode:raise RuntimeError(r.stderr)
  im=Image.open(t/'map.png').convert('RGB');im.save(OUT/(p.stem+'.webp'),quality=94,method=6)
  if os.environ.get('MAP_RENDER_DIR'):
   dest=Path(os.environ['MAP_RENDER_DIR']);dest.mkdir(exist_ok=True,parents=True);im.save(dest/(p.stem+'.png'))
 return p.stem
pattern=sys.argv[1] if len(sys.argv)>1 else 'map-*.svg'
with ThreadPoolExecutor(max_workers=3) as pool:print(list(pool.map(render,sorted(OUT.glob(pattern)))))
