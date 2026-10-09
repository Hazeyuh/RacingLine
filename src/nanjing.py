"""Build each run's center-point corridor from the physical road and kart width."""
import json,hashlib
from pathlib import Path
import numpy as np
from scipy.interpolate import CubicSpline
from shapely.geometry import Polygon,LineString,Point
import xml.etree.ElementTree as ET
from common import ROOT,UPSTREAM

def track_for_width(width_m=1.4,margin_m=.1,track_folder=None):
    folder=Path(track_folder) if track_folder else ROOT/'tracks/nanjing'
    path=folder/'geometry.json';raw=path.read_bytes();g=json.loads(raw)
    scale=g['m_per_px'];c=np.array(g['center_px']);n=len(c)
    curve=CubicSpline(np.arange(n+1),np.r_[c,c[:1]],bc_type='periodic');d=curve(np.arange(n),1);dd=curve(np.arange(n),2);speed=np.linalg.norm(d,axis=1);normal=np.c_[-d[:,1],d[:,0]]/speed[:,None]
    width_inset=width_m/2+margin_m
    discretization_guard=.08
    inset=width_inset+discretization_guard
    physical=Polygon(g['left_px']).difference(Polygon(g['right_px']))
    corridor=physical.buffer(-inset/scale,quad_segs=16)
    if corridor.geom_type!='Polygon' or len(corridor.interiors)!=1:raise ValueError('所选车宽导致道路走廊断开，请减小车宽或核对赛道')
    widths=[]
    for sign in [-1,1]:
        values=[]
        for p,nv in zip(c,normal*sign):
            if not corridor.covers(Point(p)):raise ValueError('所选车宽使参考线超出有效道路范围')
            hit=LineString([p,p+nv*2000]).intersection(corridor.boundary)
            points=list(hit.geoms) if hasattr(hit,'geoms') else [hit]
            values.append(min(Point(p).distance(x) for x in points if not x.is_empty)*scale)
        widths.append(np.array(values))
    k=(d[:,0]*dd[:,1]-d[:,1]*dd[:,0])/speed**3/scale
    wl,wr=widths
    origin=c[0];xy=(c-origin)*scale
    steps=np.linalg.norm(np.diff(np.r_[xy,xy[:1]],axis=0),axis=1);s=np.r_[0,np.cumsum(steps[:-1])];length=sum(steps)
    # The visual boundary is the actual buffered ring, sampled in its own
    # arclength. Normal rays can revisit a tight corner; do not shrink the road
    # merely to make that coordinate parameterization monotone.
    def ring_points(ring):
        line=LineString(ring.coords)
        return (np.array([line.interpolate(t).coords[0] for t in np.linspace(0,line.length,n,endpoint=False)])-origin)*scale
    left=ring_points(corridor.exterior);right=ring_points(corridor.interiors[0])
    tree=ET.parse(ROOT/'tracks/nanjing/nanjing.xml');root=tree.getroot();root.set('name',folder.name+'-manual-smooth-v2')
    root.find('header/track_length').text=repr(float(length))
    for key in ['L2_error_left','L2_error_right','max_error_left','max_error_right']:root.find('header/'+key).text='0'
    for key in ['origin_longitude','origin_latitude','reference_latitude']:root.find('GPS_parameters/'+key).text='0'
    data=root.find('data');data.set('number_of_points',str(len(c)))
    yaw=np.unwrap(np.arctan2(d[:,1],d[:,0]));k=(d[:,0]*dd[:,1]-d[:,1]*dd[:,0])/speed**3/scale
    def put(key,a):data.find(key).text=', '.join(format(float(v),'.14g') for v in a)
    for key,a in [('arclength',s),('yaw',yaw),('yaw_dot',k),('nl',wl),('nr',wr),('dyaw_dot',np.gradient(k,s)),('dnl',np.gradient(wl,s)),('dnr',np.gradient(wr,s))]:put(key,a)
    for name,p in [('centerline',xy),('left_boundary',left),('right_boundary',right),('left_measured_boundary',left),('right_measured_boundary',right)]:
        for i,axis in enumerate(['x','y']):put(name+'/'+axis,p[:,i])
    xml=ET.tostring(root,encoding='utf-8',xml_declaration=True)
    meta=dict(id=folder.name,name=g['source']['name'],track_length_m=float(length),m_per_px=scale,origin_px=origin.tolist(),image_size=g.get('image_size',[1000,707]),status='image-derived-estimate',vehicle_envelope_m=width_m,safety_margin_per_side_m=margin_m,inset_per_side_m=inset,width_inset_per_side_m=width_inset,discretization_guard_per_side_m=discretization_guard,minimum_corridor_width_m=float(min(wl+wr)),calibration=g['calibration'],direction=g['source']['direction'],boundary_revision='manual-smooth-v2',maximum_coordinate_fold_repair_m=0.,boundary_sampling='display rings sampled independently; nl/nr are normal intersections with the same corridor',kerb_policy=g['boundary_trace']['kerb_policy'],export_method='manual smooth road/kerb trace; Euclidean physical-road inset; native XML adapter',geometry_sha256=hashlib.sha256(raw).hexdigest(),xml_sha256=hashlib.sha256(xml).hexdigest())
    return xml,meta
