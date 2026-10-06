"""Convert native current-iterate lateral offsets into static track polylines."""
import json
import xml.etree.ElementTree as ET
import numpy as np

def read_frames(folder,after=0):
    path=folder/'iterations.jsonl'
    if not path.exists():return []
    cfg=json.loads((folder/'config.json').read_text());tree=ET.parse(folder/'track.xml')
    arr=lambda key:np.fromstring(tree.find('data/'+key).text,sep=',')
    ts=arr('arclength');length=cfg['track_metadata']['track_length_m'];s=np.linspace(0,length,cfg['params']['points'],endpoint=False)
    x=np.interp(s,ts,arr('centerline/x'),period=length);y=np.interp(s,ts,arr('centerline/y'),period=length)
    yaw=np.interp(s,ts,np.unwrap(arr('yaw')))
    frames=[]
    for index,line in enumerate(path.read_text().splitlines()):
        if index<after:continue
        try:row=json.loads(line)
        except json.JSONDecodeError:break # Callback may still be writing the last line.
        offset=np.array(row.pop('offset'));velocity=row.pop('velocity')
        if len(offset)!=len(s):raise ValueError('迭代轨迹维度与卡丁车网格不一致')
        row.update(index=index,x=(x-np.sin(yaw)*offset).tolist(),y=(y+np.cos(yaw)*offset).tolist(),speed_kmh=(np.array(velocity)*3.6).tolist())
        frames.append(row)
    return frames

def scene(folder):
    cfg=json.loads((folder/'config.json').read_text());tree=ET.parse(folder/'track.xml');arr=lambda key:np.fromstring(tree.find('data/'+key).text,sep=',').tolist()
    data=dict(track=cfg['track'],track_metadata=cfg['track_metadata'],track_length_m=cfg['track_metadata']['track_length_m'],boundaries={side+'.'+axis:arr(side+'_boundary/'+axis) for side in ['left','right'] for axis in ['x','y']})
    if (folder/'geometry.json').exists():
        g=json.loads((folder/'geometry.json').read_text());m=cfg['track_metadata'];data['physical_boundaries']={side:((np.array(g[key])-np.array(m['origin_px']))*m['m_per_px']).tolist() for side,key in [('left','left_px'),('right','right_px')]}
    return data
