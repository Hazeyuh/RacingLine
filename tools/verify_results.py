#!/usr/bin/env python3
"""Verify actual solver artifacts and default vehicle, not mocked outputs."""
import sys,json,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from common import ROOT,UPSTREAM,parse_iterations,write_json
track=ET.parse(UPSTREAM/'database/tracks/vendrell/vendrell.xml')
def arr(path):return np.array([float(x) for x in track.find(path).text.split(',')])
ts,nl,nr=arr('data/arclength'),arr('data/nl'),arr('data/nr')
vehicle=ET.parse(UPSTREAM/'database/vehicles/kart/roberto-lot-kart-2016.xml')
rows=[]
for path in sorted((ROOT/'runs').glob('*/result.json')):
    r=json.loads(path.read_text())
    if r['track']!='vendrell':continue
    n=r['params']['points'];folder=path.parent
    log=(folder/'solver.log').read_text();assert 'EXIT: Optimal Solution Found.' in log
    for name in ['chassis.position.x','chassis.position.y','chassis.velocity.x','rear-axle.throttle','front-axle.steering-angle','road.arclength','time','road.lateral-displacement']:
        x=np.array(r[name]);assert len(x)==n and np.all(np.isfinite(x)),(folder,name)
    assert np.all(np.diff(r['road.arclength'])>0) and np.all(np.diff(r['time'])>0)
    assert r['time'][0]==0 and r['laptime']>r['time'][-1]>0
    assert min(r['chassis.velocity.x'])>0
    s=np.array(r['road.arclength']);offset=np.array(r['road.lateral-displacement']);length=r['track_length_m']
    # Fastest-lap: positive lateral displacement is right, unlike the diagram y convention.
    excess=float(max(0.,max(offset-np.interp(s,ts,nr,period=length)),max(-offset-np.interp(s,ts,nl,period=length))))
    assert excess<1e-6,(folder,excess)
    actual=ET.parse(folder/'vehicle.xml')
    def leaves(node,prefix=''):
        out={}
        for child in node:
            key=prefix+'/'+child.tag
            if list(child):out.update(leaves(child,key))
            else:out[key]=(child.text or '').split()
        return out
    assert leaves(vehicle.getroot())==leaves(actual.getroot()),'默认车辆参数发生变化'
    it=parse_iterations(log);assert it[-1]['constraint_error']<1e-7
    rows.append(dict(id=folder.name,points=n,laptime_s=r['laptime'],solve_elapsed_s=r['elapsed_s'],peak_rss_mb=r['peak_rss_mb'],iterations=it[-1]['iteration'],constraint_error=it[-1]['constraint_error'],reference_point_boundary_excess_m=excess))
write_json(ROOT/'docs/benchmark.json',{'track':'Vendrell','engine':'Fastest-lap kart-6dof','runs':sorted(rows,key=lambda r:r['points'])})
print(json.dumps(sorted(rows,key=lambda r:r['points']),ensure_ascii=False,indent=2))
