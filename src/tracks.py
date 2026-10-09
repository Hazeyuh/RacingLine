import json,hashlib
from common import ROOT,UPSTREAM
TRACK_PATHS={'vendrell':UPSTREAM/'database/tracks/vendrell/vendrell.xml','nanjing':ROOT/'tracks/nanjing/nanjing.xml'}
for metadata in (ROOT/'tracks').glob('*/metadata.json'):
    candidate=metadata.parent/(metadata.parent.name+'.xml')
    if candidate.exists():TRACK_PATHS[metadata.parent.name]=candidate

def track_info(key):
    if key not in TRACK_PATHS:raise ValueError('未知赛道')
    path=TRACK_PATHS[key]
    if not path.exists():raise ValueError('赛道尚未生成')
    meta=json.loads((path.parent/'metadata.json').read_text()) if key!='vendrell' else dict(id=key,name='Vendrell · 官方赛道',track_length_m=1253.2326712146032,status='upstream-reference')
    meta['xml_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
    return meta
