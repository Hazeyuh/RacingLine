#!/usr/bin/env python3
"""Smooth manual boundary traces of the supplied image, including red/white kerbs."""
import sys,json
from pathlib import Path
import numpy as np
from scipy.interpolate import CubicSpline
from scipy.ndimage import gaussian_filter1d
from shapely.geometry import Polygon,LineString,Point
from PIL import Image,ImageDraw
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from common import ROOT,write_json
out=ROOT/'tracks/nanjing';old=json.loads((out/'geometry-before-boundary-fix.json').read_text());old['calibration']=json.loads((ROOT/'tracks/calibration.json').read_text());old['m_per_px']=old['calibration']['diagram_m_per_px']
left=[[432,462],[300,462],[150,462],[116,454],[102,436],[99,410],[102,350],[103,290],[111,263],[133,245],[190,237],[265,234],[322,235],[353,246],[371,268],[376,291],[369,314],[350,331],[316,338],[276,334],[240,330],[222,331],[211,339],[203,352],[204,362],[230,365],[290,366],[345,367],[374,365],[389,350],[395,321],[397,274],[404,242],[423,222],[457,216],[514,215],[567,219],[593,231],[607,250],[609,270],[598,291],[572,304],[537,311],[511,313],[496,314],[495,330],[504,349],[523,365],[590,366],[710,366],[777,365],[793,356],[801,340],[805,319],[806,307],[799,306],[773,315],[732,333],[690,346],[654,351],[630,348],[615,337],[607,320],[608,297],[616,265],[625,245],[640,227],[679,218],[755,213],[832,208],[887,210],[918,224],[940,252],[949,282],[940,313],[922,338],[902,353],[889,375],[884,413],[872,439],[852,457],[800,462],[650,462],[550,462]]
right=[[432,418],[410,418],[380,418],[340,418],[300,418],[200,418],[150,418],[143,410],[144,350],[148,294],[154,280],[173,276],[226,275],[297,274],[325,275],[337,282],[337,292],[325,299],[299,297],[260,293],[234,292],[213,295],[193,306],[176,326],[167,350],[172,376],[190,393],[219,401],[274,402],[340,402],[389,402],[414,390],[432,367],[437,338],[436,300],[439,274],[447,258],[469,253],[510,252],[543,254],[558,258],[560,264],[545,271],[515,274],[486,279],[466,291],[456,313],[461,348],[475,378],[495,397],[531,402],[650,402],[776,402],[812,399],[829,385],[836,362],[844,335],[843,310],[836,289],[823,274],[807,266],[786,266],[760,273],[721,288],[680,304],[659,312],[647,312],[644,303],[650,281],[658,264],[675,258],[739,254],[801,249],[863,245],[885,245],[900,253],[911,272],[912,291],[903,307],[883,321],[866,341],[859,365],[856,399],[850,416],[800,418],[620,418],[520,418],[474,418],[458,407],[446,402],[434,408],[432,414]]
# At painted kerbs, trace the grass-side edge so the full red/white strip
# belongs to the road. Do not expand adjoining tyre walls or unpainted edges.
kerb_left={(203,352):(207,352),(204,362):(208,359),(374,365):(370,361),(389,350):(385,348),(496,314):(500,316),(495,330):(500,330),(504,349):(508,349),(523,365):(525,361),(777,365):(776,361),(793,356):(790,354),(801,340):(798,339),(805,319):(802,319),(806,307):(802,310),(799,306):(797,310)}
kerb_right={(154,280):(158,284),(173,276):(174,279),(325,275):(323,279),(337,282):(333,284),(337,292):(333,290),(447,258):(451,263),(469,253):(471,256),(558,258):(555,260),(560,264):(556,264),(647,312):(650,308),(658,264):(662,267),(885,245):(883,249),(900,253):(897,256),(911,272):(907,273)}
left=[list(kerb_left.get(tuple(p),p)) for p in left]
right=[list(kerb_right.get(tuple(p),p)) for p in right]
def smooth(points):
 p=np.array(points,float);q=np.r_[p,p[:1]];t=np.r_[0,np.cumsum(np.linalg.norm(np.diff(q,axis=0),axis=1))];return CubicSpline(t,q,bc_type='periodic')(np.linspace(0,t[-1],2400,endpoint=False))
l=smooth(left);r=smooth(right)
for p in [l,r]:assert LineString(np.r_[p,p[:1]]).is_simple
road=Polygon(l).difference(Polygon(r));assert road.is_valid and not LineString(l).intersects(LineString(r))
anchors=np.array(old['source']['anchors_px'],float)
i=np.flatnonzero(np.all(anchors==[591,252],axis=1))[0]
anchors=np.r_[anchors[:i],np.array([[574,239],[581,250],[584,263],[581,276],[574,287]]),anchors[i+2:]]
anchors[np.all(anchors==[566,287],axis=1)]=[565,294]
j=np.flatnonzero(np.all(anchors==[499,292],axis=1))[0]
anchors=np.r_[anchors[:j],np.array([[510,293],[498,294],[486,298],[477,306],[474,318],[477,332]]),anchors[j+3:]]
q=np.r_[anchors,anchors[:1]];t=np.r_[0,np.cumsum(np.linalg.norm(np.diff(q,axis=0),axis=1))]
c=CubicSpline(t,q,bc_type='periodic')(np.linspace(0,t[-1],1800,endpoint=False));c=gaussian_filter1d(c,10,axis=0,mode='wrap');old['source']['anchors_px']=anchors.tolist();curve=CubicSpline(np.arange(len(c)+1),np.r_[c,c[:1]],bc_type='periodic');v=curve(np.arange(len(c)),1);v/=np.linalg.norm(v,axis=1)[:,None];normal=np.c_[-v[:,1],v[:,0]]
widths=[]
for sign in [-1,1]:
 values=[]
 for p,n in zip(c,sign*normal):
  assert road.covers(Point(p)),p
  ray=LineString([p,p+n*2000]);hit=ray.intersection(road.boundary)
  points=list(hit.geoms) if hasattr(hit,'geoms') else [hit]
  values.append(min(Point(p).distance(x) for x in points if not x.is_empty))
 widths.append(values)
source=old['source'];source['notes']='人工沿原图灰色道路及红白路肩外缘平滑描边；排除轮胎墙、黑黄隔离墙和维修通道。替代受文字/颜色噪声影响的逐像素边界。';source['boundary_revision']='manual-smooth-v2'
g=dict(old,center_px=c.tolist(),left_px=l.tolist(),right_px=r.tolist(),w_left_px=widths[0],w_right_px=widths[1],source=source,offset_repair_min_ratio=1.,boundary_trace=dict(left_anchors_px=left,right_anchors_px=right,method='periodic cubic spline through manually traced road/kerb outer edges',kerb_policy='红白路肩纳入道路，轮胎与隔离墙排除；可驾驶性仍待现场确认'))
write_json(out/'source.json',source);write_json(out/'geometry.json',g);write_json(out/'boundary-trace.json',g['boundary_trace'])
im=Image.open(ROOT/'赛道图片和卫星图对照/赛道图.jpg').convert('RGB');d=ImageDraw.Draw(im)
for p,col in [(l,'#00baff'),(r,'#ff3488'),(c,'#15ba66')]:d.line([tuple(x) for x in np.r_[p,p[:1]]],fill=col,width=2)
im.save(out/'geometry-overlay.png')
print('Smooth physical boundaries verified; half widths',min(widths[0]),min(widths[1]))

# Keep image masks consistent with the actual physical-road trace.
from shapely import contains_xy
y,x=np.indices((707,1000));mask=contains_xy(road,x,y)
Image.fromarray((mask*255).astype('uint8')).save(out/'drivable-mask.png')
rgb=np.asarray(Image.open(ROOT/'赛道图片和卫星图对照/赛道图.jpg').convert('RGB')).astype(float)
red=(rgb[:,:,0]>150)&(rgb[:,:,0]>1.45*rgb[:,:,1])&(rgb[:,:,1]<150)
Image.fromarray(((red&mask)*255).astype('uint8')).save(out/'kerb-mask.png')

scale=g['m_per_px']
np.savetxt(out/'centerline.csv',np.c_[c*scale,np.array(widths[1])*scale,np.array(widths[0])*scale],delimiter=',',header='x_m,y_m,w_tr_right_m,w_tr_left_m')
for name,points in [('left',l),('right',r)]:
 np.savetxt(out/(name+'.csv'),points*scale,delimiter=',',header='x_m,y_m')
 xy=(points-r[0])*scale;coords=np.c_[xy[:,0]/6378388*180/np.pi,-xy[:,1]/6378388*180/np.pi,np.zeros(len(xy))]
 text=', '.join(format(float(z),'.12f') for z in coords.ravel())
 (out/(name+'.kml')).write_text('<kml><Document><Folder><Placemark><LineString><coordinates>'+text+'</coordinates></LineString></Placemark></Folder></Document></kml>')
