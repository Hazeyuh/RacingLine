#!/usr/bin/env python3
import sys,json,hashlib
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
from PIL import Image,ImageDraw
from shapely.geometry import LineString,Polygon,Point
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from common import ROOT,write_json
out=ROOT/'tracks/nanjing';g=json.loads((out/'geometry.json').read_text());meta=json.loads((out/'metadata.json').read_text())
curves={key:np.array(g[key]) for key in ['center_px','left_px','right_px']}
for key,p in curves.items():assert LineString(np.r_[p,p[:1]]).is_simple,key
assert not LineString(curves['left_px']).intersects(LineString(curves['right_px']))
a=Polygon(curves['left_px']);b=Polygon(curves['right_px']);road=a.symmetric_difference(b);assert road.is_valid
assert all(road.covers(Point(p)) for p in curves['center_px'])
assert min(g['w_left_px'])>0 and min(g['w_right_px'])>0
results=[]
for f in (ROOT/'runs').glob('*/result.json'):
 r=json.loads(f.read_text())
 if r['track']!='nanjing' or r.get('status')=='invalid':continue
 xml=ET.parse(f.parent/'track.xml');data=xml.find('data');arr=lambda path:np.fromstring(data.find(path).text,sep=',');s=arr('arclength');nl=arr('nl');nr=arr('nr');q=np.array(r['road.arclength']);offset=np.array(r['road.lateral-displacement']);length=r['track_length_m']
 assert 'EXIT: Optimal Solution Found.' in (f.parent/'solver.log').read_text()
 def leaves(node,prefix=''):
  out={}
  for child in node:
   key=prefix+'/'+child.tag
   if list(child):out.update(leaves(child,key))
   else:out[key]=(child.text or '').split()
  return out
 original=ET.parse(ROOT/'upstream/fastest-lap/database/vehicles/kart/roberto-lot-kart-2016.xml')
 for key,path in {'mass':'chassis/mass','power_kw':'rear-axle/engine/maximum-power','brake_nm':'rear-axle/brakes/max_torque','cd':'chassis/aerodynamics/cd'}.items():original.find(path).text=str(r['params'][key])
 for tire in ['front-tire','rear-tire']:original.find(f'{tire}/lateral/pure/pDy1').text=str(r['params']['grip'])
 vehicle=r.get('vehicle')
 if vehicle and vehicle.get('engine_model')=='honda-torque-v1':
  for field,tag in [('gear_ratio','rental-gear-ratio'),('efficiency','rental-efficiency'),('limit_rpm','rental-limit-rpm'),('clutch_rpm','rental-clutch-rpm')]:ET.SubElement(original.find('rear-axle/engine'),tag).text=str(vehicle[field])
  ET.SubElement(original.find('rear-axle/engine'),'rental-torque-coefficients').text=','.join(map(str,vehicle['curve']['coefficients']))
  ET.SubElement(original.find('rear-axle/engine'),'rental-reference-power').text=str(vehicle['curve']['rated_power_kw'])
  original.find('rear-tire/radius').text=str(vehicle['rear_wheel_radius_m'])
 assert leaves(original.getroot())==leaves(ET.parse(f.parent/'vehicle.xml').getroot()),'车辆 XML 与实验参数不一致'

 assert all(np.all(np.isfinite(v)) for v in r.values() if isinstance(v,list))
 assert len(q)==r['params']['points'] and np.all(np.diff(q)>0) and np.all(np.diff(r['time'])>0)
 assert r['laptime']>r['time'][-1]
 excess=float(max(0.,max(offset-np.interp(q,s,nr,period=length)),max(-offset-np.interp(q,s,nl,period=length))))
 assert excess<1e-6
 snapshot=json.loads((f.parent/'geometry.json').read_text());road=Polygon(snapshot['left_px']).symmetric_difference(Polygon(snapshot['right_px']))
 rm=r['track_metadata'];points=np.c_[r['chassis.position.x'],r['chassis.position.y']]/rm['m_per_px']+np.array(rm['origin_px'])
 line_inside=road.covers(LineString(np.r_[points,points[:1]]))
 if len(q)>=500:assert line_inside,'细网格线路跨出道路'
 r['validation']['full_raceline_in_image_corridor']=line_inside;write_json(f,r)
 outside=max(road.distance(Point(p)) for p in points)*rm['m_per_px'];assert outside<1e-3,(f,outside)
 results.append(dict(id=f.parent.name,vehicle=r.get('vehicle'),mass_kg=r['params']['mass'],power_kw=r['params']['power_kw'],points=len(q),laptime_s=r['laptime'],elapsed_s=r['elapsed_s'],boundary_excess_m=excess,full_raceline_in_image_corridor=line_inside,image_corridor_outside_m=outside,xml_sha256=hashlib.sha256((f.parent/'track.xml').read_bytes()).hexdigest()))
 if len(q)>=500:
  im=Image.open(ROOT/'赛道图片和卫星图对照/赛道图.jpg').convert('RGB');d=ImageDraw.Draw(im);v=np.array(r['chassis.velocity.x']);
  for i in range(len(points)):
   t=(v[i]-min(v))/(max(v)-min(v));color=(int(60+190*t),int(200-50*t),int(240-190*t));d.line([tuple(points[i]),tuple(points[(i+1)%len(points)])],fill=color,width=3)
  d.line((432,420,432,463),fill='yellow',width=3);im.save(out/'raceline-overlay.png')
write_json(out/'verification.json',dict(geometry_simple=True,closed=True,reference_length_m=meta['track_length_m'],runs=sorted(results,key=lambda r:r['points'])))
print(json.dumps(results,indent=2))
