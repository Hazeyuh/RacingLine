#!/usr/bin/env python3
import sys,json
from pathlib import Path
import numpy as np
from shapely.geometry import Polygon,LineString
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from common import ROOT,write_json
rows=[]
for f in (ROOT/'runs').glob('*/result.json'):
 r=json.loads(f.read_text());m=r.get('track_metadata',{})
 if m.get('boundary_revision')!='manual-smooth-v2' or r.get('status')=='invalid':continue
 assert np.all(np.diff(r['time'])>0)
 assert r['validation']['full_raceline_in_width_corridor']
 g=json.loads((f.parent/'geometry.json').read_text());road=Polygon(g['left_px']).difference(Polygon(g['right_px']));corridor=road.buffer(-m['width_inset_per_side_m']/m['m_per_px'],quad_segs=16)
 points=np.c_[r['chassis.position.x'],r['chassis.position.y']]/m['m_per_px']+np.array(m['origin_px']);line=LineString(np.r_[points,points[:1]])
 assert corridor.buffer(1e-4).covers(line)
 for side in ['left','right']:
  b=np.c_[r['boundaries'][side+'.x'],r['boundaries'][side+'.y']];assert LineString(np.r_[b,b[:1]]).is_simple
 rows.append(dict(id=f.parent.name,width_m=m['vehicle_envelope_m'],points=r['params']['points'],laptime_s=r['laptime'],geometry_sha256=m['geometry_sha256'],xml_sha256=m['xml_sha256'],time_monotonic=True,full_width_corridor_valid=True))
write_json(ROOT/'docs/width-comparison.json',dict(boundary_revision='manual-smooth-v2',runs=rows))
print(json.dumps(rows,ensure_ascii=False,indent=2))
