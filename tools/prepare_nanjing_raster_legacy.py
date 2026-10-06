#!/usr/bin/env python3
import sys,json,math
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from scipy import ndimage as nd
from scipy.interpolate import CubicSpline
from shapely.geometry import LineString
from shapely.strtree import STRtree
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from common import ROOT,write_json
OUT=ROOT/'tracks/nanjing'
source=json.loads((OUT/'source.json').read_text());cal=json.loads((ROOT/'tracks/calibration.json').read_text())
im=Image.open(ROOT/'赛道图片和卫星图对照/赛道图.jpg').convert('RGB');rgb=np.asarray(im).astype(float)
gray=(np.ptp(rgb,axis=2)<25)&(rgb.mean(axis=2)>115)&(rgb.mean(axis=2)<195)
gray[:210]=False;gray[505:]=False;gray[:,:82]=False
mask=nd.binary_closing(gray,iterations=3)
labels,n=nd.label(~mask)
sizes=np.bincount(labels.ravel());mask|=(sizes[labels]<500)
red=(rgb[:,:,0]>150)&(rgb[:,:,0]>1.45*rgb[:,:,1])&(rgb[:,:,1]<150)
kerb=red&nd.binary_dilation(mask,iterations=6)
kerb[:230]=False;kerb[420:]=False;kerb[:,:120]=False;kerb[:,920:]=False
mask|=nd.binary_dilation(kerb,iterations=2)
# Explicitly prevent a normal ray from crossing the main-straight median into the pit lane.
mask[464:,:]=False
# Race turn T1 stays to the right of the PIT EXIT branch.
mask[290:460,:102]=False
walls=[[(187,411),(280,410),(405,409),(423,398),(444,400)],[(511,411),(650,410),(774,408)],[(454,362),(449,327),(450,299),(456,282),(473,273),(515,270)],[(389,337),(393,268),(396,235),(407,222),(447,211)],[(604,294),(614,267),(619,243),(612,224),(584,213)],[(706,279),(768,263),(833,255)],[(85,400),(86,280),(103,251),(148,236),(247,225)],[(453,200),(601,203),(782,204),(899,202),(923,211),(944,243),(960,282),(950,311),(921,344),(908,380),(896,416)]]
wallimage=Image.new('L',im.size);wd=ImageDraw.Draw(wallimage)
for wall in walls:wd.line(wall,fill=255,width=4)
mask[np.asarray(wallimage)>0]=False
anchors=np.array(source['anchors_px'],float);q=np.r_[anchors,anchors[:1]]
t=np.r_[0,np.cumsum(np.linalg.norm(np.diff(q,axis=0),axis=1))]
spline=CubicSpline(t,q,bc_type='periodic');u=np.linspace(0,t[-1],1800,endpoint=False);c=spline(u);v=spline(u,1);v/=np.linalg.norm(v,axis=1)[:,None];normal=np.c_[-v[:,1],v[:,0]]
# In image axes (y down), +normal is driver's right.
def distances(sign):
 out=[]
 for p,n in zip(c,normal*sign):
  distance=0.
  for d in np.arange(0,80,.5):
   x,y=np.rint(p+d*n).astype(int)
   if not(0<=x<1000 and 0<=y<707) or not mask[y,x]:break
   distance=d
  out.append(distance)
 return np.array(out)
wr=distances(1);wl=distances(-1)
# Remove tiny raster/letter gaps; do not widen corridors beyond measured edges.
wl=nd.gaussian_filter1d(nd.minimum_filter1d(wl,size=15,mode='wrap'),7,mode='wrap')
wr=nd.gaussian_filter1d(nd.minimum_filter1d(wr,size=15,mode='wrap'),7,mode='wrap')
curvature=np.abs(v[:,0]*spline(u,2)[:,1]-v[:,1]*spline(u,2)[:,0])/np.linalg.norm(spline(u,1),axis=1)**2
cap=np.minimum(40,.8/np.maximum(curvature,.0001))
wl=np.minimum(wl,cap);wr=np.minimum(wr,cap)
print('Pixel half widths',wl.min(),wr.min(),'center outside',int(sum(~mask[np.rint(c[:,1]).astype(int),np.rint(c[:,0]).astype(int)])))
# Repair only intersecting offset sections by pulling their edges inward.
raw_wl=wl.copy();raw_wr=wr.copy()
for width,sign in [(wl,-1),(wr,1)]:
 for iteration in range(20):
  edge=c+sign*normal*width[:,None];segments=[LineString([edge[i],edge[(i+1)%len(edge)]]) for i in range(len(edge))]
  pairs=STRtree(segments).query(segments,predicate='intersects');bad=set()
  for i,j in pairs.T:
   if i!=j and (i-j)%len(edge) not in (1,len(edge)-1):bad.update([int(i),int(j)])
  if not bad:break
  weight=np.zeros(len(edge))
  for i in bad:
   delta=np.minimum((np.arange(len(edge))-i)%len(edge),(i-np.arange(len(edge)))%len(edge))
   weight=np.maximum(weight,np.exp(-.5*(delta/15)**2))
  width*=1-.15*weight
 else:raise ValueError('Boundary self-intersections could not be repaired')
scale=cal['diagram_m_per_px'];left=c-normal*wl[:,None];right=c+normal*wr[:,None]
assert LineString(np.r_[left,left[:1]]).is_simple and LineString(np.r_[right,right[:1]]).is_simple
assert not LineString(np.r_[left,left[:1]]).intersects(LineString(np.r_[right,right[:1]]))
d=ImageDraw.Draw(im)
for points,color in [(left,'#00baff'),(right,'#ff3488'),(c,'#15ba66')]:d.line([tuple(p) for p in np.r_[points,points[:1]]],fill=color,width=2)
for i in range(0,len(c),90):
 p=c[i];end=p+v[i]*12;d.line([tuple(p),tuple(end)],fill='#008050',width=3)
d.line((432,420,432,463),fill='yellow',width=4);d.text((440,443),'S/F',fill='black');im.save(OUT/'geometry-overlay.png')
Image.fromarray((mask*255).astype('uint8')).save(OUT/'drivable-mask.png');Image.fromarray((kerb*255).astype('uint8')).save(OUT/'kerb-mask.png')
geometry=dict(center_px=c.tolist(),left_px=left.tolist(),right_px=right.tolist(),w_left_px=wl.tolist(),w_right_px=wr.tolist(),m_per_px=scale,source=source,calibration=cal,offset_repair_min_ratio=float(min(np.min(wl/raw_wl),np.min(wr/raw_wr))))
write_json(OUT/'geometry.json',geometry)
np.savetxt(OUT/'centerline.csv',np.c_[c*scale,wr*scale,wl*scale],delimiter=',',header='x_m,y_m,w_tr_right_m,w_tr_left_m')
for name,points in [('left',left),('right',right)]:
 np.savetxt(OUT/(name+'.csv'),points*scale,delimiter=',',header='x_m,y_m')
 # Synthetic local KML is an adapter: latitude 0, not a claim of surveyed GPS position.
 xy=(points-right[0])*scale;coords=np.c_[xy[:,0]/6378388*180/math.pi,-xy[:,1]/6378388*180/math.pi,np.zeros(len(xy))]
 text=', '.join(format(float(z),'.12f') for z in coords.ravel())
 (OUT/(name+'.kml')).write_text('<kml><Document><Folder><Placemark><LineString><coordinates>'+text+'</coordinates></LineString></Placemark></Folder></Document></kml>')
