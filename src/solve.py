"""Each native solver lives in a subprocess, so a C++ failure cannot kill the UI."""
import sys, json, time, resource, shutil, os
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
from common import ROOT, UPSTREAM, validate_params, write_json
from tracks import TRACK_PATHS,track_info

def main(run):
    run=Path(run); config=json.loads((run/'config.json').read_text()); p=validate_params(config['params'])
    sys.path.insert(0,str(UPSTREAM/'examples/python'))
    import fastest_lap as fl
    tree=ET.parse(UPSTREAM/'database/vehicles/kart/roberto-lot-kart-2016.xml')
    mapping={'mass':'chassis/mass','power_kw':'rear-axle/engine/maximum-power','brake_nm':'rear-axle/brakes/max_torque','cd':'chassis/aerodynamics/cd'}
    for key,path in mapping.items(): tree.find(path).text=str(p[key])
    for tire in ['front-tire','rear-tire']: tree.find(f'{tire}/lateral/pure/pDy1').text=str(p['grip'])
    vehicle=config.get('vehicle')
    if vehicle and vehicle.get('engine_model')=='honda-torque-v1':
        engine=tree.find('rear-axle/engine')
        for field,tag in [('gear_ratio','rental-gear-ratio'),('efficiency','rental-efficiency'),('limit_rpm','rental-limit-rpm'),('clutch_rpm','rental-clutch-rpm')]:ET.SubElement(engine,tag).text=str(vehicle[field])
        ET.SubElement(engine,'rental-torque-coefficients').text=','.join(map(str,vehicle['curve']['coefficients']))
        ET.SubElement(engine,'rental-reference-power').text=str(vehicle['curve']['rated_power_kw'])
        tree.find('rear-tire/radius').text=str(vehicle['rear_wheel_radius_m'])
    tree.write(run/'vehicle.xml')
    fl.create_vehicle_from_xml('kart',str(run/'vehicle.xml'))
    key=config.get('track','vendrell');meta=config.get('track_metadata') or track_info(key)
    track=run/'track.xml'
    if not track.exists():shutil.copyfile(TRACK_PATHS[key],track)
    fl.create_track_from_xml('track',str(track))
    length=fl.track_download_length('track')
    s=np.linspace(0,length,p['points'],endpoint=False).tolist()
    variables=['laptime','chassis.position.x','chassis.position.y','chassis.velocity.x','rear-axle.throttle','front-axle.steering-angle','road.arclength','time','road.lateral-displacement']
    if vehicle and vehicle.get('engine_model')=='honda-torque-v1':variables+=['rear-axle.engine.rpm','rear-axle.engine.power','rear-axle.shaft-power','chassis.acceleration.x']
    options='<options><print_level>5</print_level><output_variables><prefix>run/</prefix><variables>'+''.join(f'<{v}/>' for v in variables)+'</variables></output_variables><write_xml>true</write_xml><xml_file_name>'+str(run/'solution.xml')+'</xml_file_name></options>'
    if config.get('record_iterations'):
        _,names,controls,_=fl.vehicle_type_get_names('kart-6dof')
        os.environ.update(RACINGLINE_ITERATIONS=str(run/'iterations.jsonl'),RACINGLINE_POINTS=str(p['points']),RACINGLINE_STRIDE=str(len(names)-1+2*len(controls)),RACINGLINE_LATERAL=str(names.index('road.lateral-displacement')-1),RACINGLINE_VELOCITY=str(names.index('chassis.velocity.x')))
    else:os.environ.pop('RACINGLINE_ITERATIONS',None)
    started=time.monotonic(); fl.optimal_laptime('kart','track',s,options)
    result={v:fl.download_scalar('run/'+v) if v=='laptime' else fl.download_vector('run/'+v) for v in variables}
    result.update(vehicle=config.get('vehicle'),track=key,track_metadata=meta,track_length_m=length,params=p,elapsed_s=time.monotonic()-started,peak_rss_mb=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/(1024**2 if sys.platform=='darwin' else 1024),engine='Fastest-lap kart-6dof',status='succeeded')
    if not np.all(np.diff(result['time'])>0):raise ValueError('结果时间未严格递增：参考线坐标不可行')
    result['boundaries']={k:fl.track_download_data('track',k) for k in ['left.x','left.y','right.x','right.y']}
    ts=np.array(fl.track_download_data('track','arclength'))
    nl=np.interp(s,ts,fl.track_download_data('track','distance-left-boundary'),period=length)
    nr=np.interp(s,ts,fl.track_download_data('track','distance-right-boundary'),period=length)
    offset=np.array(result['road.lateral-displacement'])
    result['validation']=dict(finite=all(np.all(np.isfinite(v)) for v in result.values() if isinstance(v,list)),reference_point_boundary_excess_m=float(max(0.,np.max(offset-nr),np.max(-offset-nl))))
    if key=='nanjing':
        from shapely.geometry import Polygon,LineString
        geometry=run/'geometry.json'
        if not geometry.exists():shutil.copyfile(ROOT/'tracks/nanjing/geometry.json',geometry)
        g=json.loads(geometry.read_text());road=Polygon(g['left_px']).symmetric_difference(Polygon(g['right_px']))
        xy=np.c_[result['chassis.position.x'],result['chassis.position.y']]/meta['m_per_px']+np.array(meta['origin_px'])
        line=LineString(np.r_[xy,xy[:1]])
        result['validation']['full_raceline_in_image_corridor']=road.covers(line)
        if meta.get('boundary_revision')=='manual-smooth-v2':
            inset=meta.get('width_inset_per_side_m',meta['inset_per_side_m'])/meta['m_per_px']
            result['validation']['full_raceline_in_width_corridor']=road.buffer(-inset,quad_segs=16).buffer(1e-4).covers(line)
        result['physical_boundaries']={side:((np.array(g[key])-np.array(meta['origin_px']))*meta['m_per_px']).tolist() for side,key in [('left','left_px'),('right','right_px')]}
    write_json(run/'result.json',result)
if __name__=='__main__': main(sys.argv[1])
