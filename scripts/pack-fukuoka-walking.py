#!/usr/bin/env python3
"""Pack the OSM walk graph into compact typed columns for a browser worker."""
from pathlib import Path
import argparse,gzip,hashlib,json,struct
import numpy as np
root=Path(__file__).resolve().parents[1]/'fukuoka-mobility/data/osm'
ap=argparse.ArgumentParser();ap.add_argument('input',type=Path);args=ap.parse_args()
data=json.loads(gzip.decompress(args.input.read_bytes()))
meta=json.dumps(data['meta'],ensure_ascii=False,separators=(',',':')).encode()
count=len(data['nodes']);edges=len(data['edges'])
coords=np.rint(np.array(data['nodes'],dtype=np.float64)*1e7).astype('<i4')
rows=np.array(data['edges'],dtype=np.float64)
parts=[b'MDLWALK1',struct.pack('<III',len(meta),count,edges),meta,coords.tobytes(),rows[:,:2].astype('<u4').tobytes(),np.rint(rows[:,2]*100).astype('<u4').tobytes(),rows[:,3].astype('u1').tobytes()]
output=b''.join(parts);compressed=gzip.compress(output,mtime=0)
parts=[]
for n,start in enumerate(range(0,len(compressed),6*1024*1024),1):
    part=compressed[start:start+6*1024*1024];file=f'walking-graph.part{n:02d}'
    (root/file).write_bytes(part);parts.append({'file':file,'bytes':len(part),'sha256':hashlib.sha256(part).hexdigest()})
(root/'walking-graph.json').write_text(json.dumps({'format':'MDLWALK1/gzip-parts','bytes':len(compressed),'sha256':hashlib.sha256(compressed).hexdigest(),'parts':parts},indent=2)+'\n')
print('walk graph packed',len(output),'bytes',count,'nodes',edges,'edges')
