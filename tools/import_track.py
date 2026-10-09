#!/usr/bin/env python3
"""Reproducible image/tablet trace -> physical geometry -> native track XML."""
import argparse, hashlib, json, re, sys, tempfile, shutil
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
from scipy.interpolate import CubicSpline
from shapely.geometry import LineString, Polygon
from PIL import Image, ImageDraw
from common import ROOT, write_json
from nanjing import track_for_width

def build(trace, output, image_path=None):
    ident=trace['id']
    if not re.fullmatch('[a-z][a-z0-9-]{1,47}',ident) or ident in ['nanjing','vendrell']:raise ValueError('id 须为 2–48 位小写英文/数字/连字符，不可使用内置赛道 id')
    if not str(trace.get('name','')).strip():raise ValueError('需要赛道名称')
    cal=trace['calibration'];points=np.asarray(cal['points_px'],float);known=float(cal['length_m'])
    if points.shape!=(2,2) or not np.isfinite(points).all() or known<=0 or not np.isfinite(known):raise ValueError('比例尺需要两个有限坐标和正的米制长度')
    distance=np.linalg.norm(points[1]-points[0])
    if distance<2:raise ValueError('比例尺像素长度太短')
    scale=known/distance
    def ring(key):
        a=np.asarray(trace[key],float)
        if a.ndim!=2 or a.shape[1]!=2 or len(a)<6 or not np.isfinite(a).all():raise ValueError(key+' 至少需要 6 个有效二维点')
        if np.allclose(a[0],a[-1]):a=a[:-1]
        q=np.r_[a,a[:1]];d=np.linalg.norm(np.diff(q,axis=0),axis=1)
        if np.min(d)<1e-6:raise ValueError(key+' 有重复相邻点')
        t=np.r_[0,np.cumsum(d)]
        p=CubicSpline(t,q,bc_type='periodic')(np.linspace(0,t[-1],800,endpoint=False))
        if not LineString(np.r_[p,p[:1]]).is_simple:raise ValueError(key+' 平滑后自交；请修正描点，不能自动猜交叉口')
        return p
    c=ring('centerline_px')
    if 'outer_boundary_px' in trace or 'inner_boundary_px' in trace:
        outer=ring('outer_boundary_px');inner=ring('inner_boundary_px')
        if not Polygon(outer).contains(Polygon(inner)):raise ValueError('外边界必须完整包含内边界且不能接触')
        road=Polygon(outer).difference(Polygon(inner))
    else:
        width=float(trace['road_width_m'])
        if not np.isfinite(width) or width<=0:raise ValueError('道路宽度必须为正数')
        road=LineString(np.r_[c,c[:1]]).buffer(width/(2*scale),quad_segs=16)
        if road.geom_type!='Polygon' or len(road.interiors)!=1:raise ValueError('中心线扩宽后道路重叠或闭环消失；请拉开相邻段/减小路宽，或提供内外边界')
        outer=np.asarray(road.exterior.coords[:-1]);inner=np.asarray(road.interiors[0].coords[:-1])
    if not road.is_valid or not road.covers(LineString(np.r_[c,c[:1]])):raise ValueError('参考线必须全程位于有效道路内')
    size=trace.get('image_size',[1200,900]);policy=trace.get('kerb_policy','道路宽度以设计值为准；未指定路肩时不另扩张')
    g=dict(center_px=c.tolist(),left_px=outer.tolist(),right_px=inner.tolist(),m_per_px=float(scale),image_size=size,calibration=cal,source=dict(name=trace['name'],direction=trace['direction'],provenance=trace.get('source','自绘赛道'),trace_sha256=hashlib.sha256(json.dumps(trace,sort_keys=True).encode()).hexdigest()),boundary_trace=dict(kerb_policy=policy))
    write_json(output/'geometry.json',g);write_json(output/'trace.json',trace)
    xml,meta=track_for_width(float(trace.get('vehicle_width_m',1.4)),track_folder=output)
    # Temporary folders have random names; public identity comes from the trace.
    meta.update(id=ident,name=trace['name'],status='user-designed' if trace.get('kind')=='design' else 'image-derived-estimate')
    import xml.etree.ElementTree as ET
    tree=ET.fromstring(xml);tree.set('name',ident)
    arr=lambda key:np.fromstring(tree.find('data/'+key).text,sep=',')
    if min(np.min(1+arr('yaw_dot')*arr('nl')),np.min(1-arr('yaw_dot')*arr('nr')))<=.05:raise ValueError('弯道参考线坐标折叠；请重新选择参考线或平滑急弯，不能直接求解')
    xml=ET.tostring(tree,encoding='utf-8',xml_declaration=True);meta['xml_sha256']=hashlib.sha256(xml).hexdigest()
    (output/(ident+'.xml')).write_bytes(xml);write_json(output/'metadata.json',meta)
    im=Image.open(image_path).convert('RGB') if image_path else Image.new('RGB',tuple(size),'#142024')
    if list(im.size)!=list(size):raise ValueError('图片尺寸与 image_size 不一致；禁止静默缩放后使用旧描点')
    draw=ImageDraw.Draw(im)
    for p,col in [(outer,'#16baff'),(inner,'#ff4088'),(c,'#bde66c')]:draw.line([tuple(v) for v in np.r_[p,p[:1]]],fill=col,width=3)
    im.save(output/'geometry-overlay.png')
    write_json(output/'validation.json',dict(geometry_valid=True,closed=True,self_intersection=False,scale_m_per_px=scale,track_length_m=meta['track_length_m'],minimum_center_corridor_width_m=meta['minimum_corridor_width_m'],native_solve_verified=False))
    return meta

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('trace',type=Path);p.add_argument('--check',action='store_true',help='只生成检查预览，不安装进赛道列表');p.add_argument('--image',type=Path);p.add_argument('--output',type=Path,help='--check 模式的预览目录')
    a=p.parse_args();trace=json.loads(a.trace.read_text());dest=ROOT/'tracks'/trace['id']
    if a.check:
        dest=a.output or ROOT/'runs'/('track-preview-'+trace['id']);dest.mkdir(parents=True,exist_ok=True);m=build(trace,dest,a.image)
    else:
        if dest.exists():raise ValueError('目标赛道已存在；请使用新 id 保留旧实验的几何版本')
        with tempfile.TemporaryDirectory(prefix='racingline-track-') as tmp:
            staged=Path(tmp);m=build(trace,staged,a.image);shutil.copytree(staged,dest)
    print(json.dumps(dict(folder=str(dest),metadata=m),ensure_ascii=False,indent=2))
if __name__=='__main__':
    try:main()
    except (ValueError,KeyError) as e:sys.exit('赛道输入错误：'+str(e))
