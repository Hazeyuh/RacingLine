#!/usr/bin/env python3
"""Check native kart outputs and actual limit sensitivity, using saved solves."""
import sys,json
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from common import ROOT,write_json
rows=[]
for f in (ROOT/'runs').glob('*/result.json'):
 r=json.loads(f.read_text());v=r.get('vehicle') or {}
 if v.get('engine_model')!='honda-torque-v1' or r.get('status')=='invalid':continue
 rpm=np.array(r['rear-axle.engine.rpm']);engine=np.array(r['rear-axle.engine.power']);shaft=np.array(r['rear-axle.shaft-power']);acc=np.array(r['chassis.acceleration.x'])
 for x in [rpm,engine,shaft,acc]:assert len(x)==r['params']['points'] and np.all(np.isfinite(x))
 assert min(rpm)>=v['clutch_rpm']
 assert min(engine)>=0 and min(shaft)>=0
 assert np.all(shaft<=engine*v['efficiency']+1e-6),'传动损失不能产生能量'
 # Recover synchronized shaft rpm from the smooth-max relation; check exported power.
 sync=rpm-2500/(rpm-v['clutch_rpm'])
 assert np.allclose(shaft,engine*v['efficiency']*sync/rpm,rtol=1e-7,atol=1e-6)
 assert 'EXIT: Optimal Solution Found.' in (f.parent/'solver.log').read_text()
 assert r['validation']['full_raceline_in_image_corridor']
 rows.append(dict(id=f.parent.name,vehicle=v['name'],curve=v['engine_curve'],target_power_kw=r['params']['power_kw'],gear_ratio=v['gear_ratio'],limit_rpm=v['limit_rpm'],laptime_s=r['laptime'],maximum_speed_kmh=max(r['chassis.velocity.x'])*3.6,maximum_rpm=float(max(rpm)),maximum_engine_power_kw=float(max(engine)/1000),maximum_shaft_power_kw=float(max(shaft)/1000),elapsed_s=r['elapsed_s']))
reference=[x for x in rows if x['vehicle']=='270cc' and x['gear_ratio']==5 and x['limit_rpm']==3600]
reduced=[x for x in rows if x['vehicle']=='270cc' and x['gear_ratio']==5 and x['limit_rpm']==3000]
if reference and reduced:
 assert reduced[-1]['maximum_speed_kmh']<reference[-1]['maximum_speed_kmh']
 assert reduced[-1]['laptime_s']>reference[-1]['laptime_s']
write_json(ROOT/'docs/engine-comparison.json',dict(engine='honda-torque-v1',runs=rows))
print(json.dumps(rows,ensure_ascii=False,indent=2))
