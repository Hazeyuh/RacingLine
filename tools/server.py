#!/usr/bin/env python3
import sys, json, subprocess, threading, uuid, time, os, pty, shutil, signal, atexit
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from common import ROOT, UPSTREAM, DEFAULTS, validate_params, parse_iterations, write_json
from tracks import TRACK_PATHS,track_info
from nanjing import track_for_width
from iterations import read_frames,scene
from vehicles import PRESETS,CURVES,vehicle_config
LOCK=threading.Lock(); ACTIVE=None; PROCESSES={}; PAUSES={}; PAUSED_AT={}

def stop_children():
    with LOCK:
        for proc in list(PROCESSES.values()):
            if proc.poll() is None:
                proc.send_signal(signal.SIGCONT)
                proc.terminate()
atexit.register(stop_children)

def run_dir(key):
    if len(key)!=12 or any(c not in '0123456789abcdef' for c in key): raise ValueError('无效实验 ID')
    path=ROOT/'runs'/key
    if not path.exists(): raise ValueError('实验不存在')
    return path

def status(path):
    data=json.loads((path/'config.json').read_text())
    state=json.loads((path/'status.json').read_text())
    log=(path/'solver.log').read_text(errors='replace') if (path/'solver.log').exists() else ''
    data.update(state,id=path.name,iterations=parse_iterations(log),log_tail=log[-3500:])
    if (path/'result.json').exists(): data['result']=json.loads((path/'result.json').read_text())
    return data

def solve_job(path):
    global ACTIVE
    try:
        master, slave = pty.openpty()
        with (path/'solver.log').open('wb') as log:
            proc=subprocess.Popen([sys.executable,'-u',str(ROOT/'src/solve.py'),str(path)],stdout=slave,stderr=slave,cwd=ROOT)
            os.close(slave)
            with LOCK:PROCESSES[path.name]=proc
            try:
                while True:
                    try: chunk=os.read(master,65536)
                    except OSError: break
                    if not chunk: break
                    log.write(chunk); log.flush()
            finally: os.close(master)
            proc.wait()
        if (path/'result.json').exists():
            result=json.loads((path/'result.json').read_text());result['paused_s']=PAUSES.get(path.name,0);result['active_elapsed_s']=max(0,result['elapsed_s']-result['paused_s']);write_json(path/'result.json',result)
        ok=proc.returncode==0 and (path/'result.json').exists()
        write_json(path/'status.json',dict(status='succeeded' if ok else 'failed',returncode=proc.returncode))
    except Exception as e: write_json(path/'status.json',dict(status='failed',error=str(e)))
    finally:
        with LOCK: ACTIVE=None;PROCESSES.pop(path.name,None);PAUSED_AT.pop(path.name,None)

class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs): super().__init__(*args,directory=str(ROOT/'web'),**kwargs)
    def json(self,data,code=200):
        raw=json.dumps(data,ensure_ascii=False,allow_nan=False).encode(); self.send_response(code); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Content-Length',str(len(raw))); self.end_headers(); self.wfile.write(raw)
    def do_GET(self):
        path=urlparse(self.path).path
        try:
            if path=='/api/state':
                runs=[status(p) for p in sorted((ROOT/'runs').glob('*/config.json'),key=lambda p:p.stat().st_mtime,reverse=True) for p in [p.parent]]
                return self.json(dict(tracks=[track_info(k) for k in TRACK_PATHS if TRACK_PATHS[k].exists()],defaults=DEFAULTS,vehicles=PRESETS,engine_curves=CURVES,runs=runs,ready=bool(list((UPSTREAM/'build/lib').glob('*fastestlapc*.dylib'))),active=ACTIVE,calibration=json.loads((ROOT/'tracks/calibration.json').read_text())))
            if path.startswith('/api/run/') and path.endswith('/trajectories'):
                from urllib.parse import parse_qs
                after=max(0,int(parse_qs(urlparse(self.path).query).get('after',['0'])[0]))
                folder=run_dir(path.split('/')[3]);return self.json({'frames':read_frames(folder,after),'scene':scene(folder) if after==0 else None})
            if path.startswith('/api/run/'): return self.json(status(run_dir(path.split('/')[-1])))
            if path=='/api/nanjing-geometry':return self.json(json.loads((ROOT/'tracks/nanjing/geometry.json').read_text()))
            if path=='/images/nanjing-overlay':
                raw=(ROOT/'tracks/nanjing/geometry-overlay.png').read_bytes();self.send_response(200);self.send_header('Content-Type','image/png');self.end_headers();self.wfile.write(raw);return
            if path.startswith('/images/'):
                name={'satellite':'卫星图对照.png','diagram':'赛道图.jpg'}.get(path.split('/')[-1])
                if not name: raise ValueError('图片不存在')
                raw=(ROOT/'赛道图片和卫星图对照'/name).read_bytes();self.send_response(200);self.send_header('Content-Type','image/png' if name.endswith('png') else 'image/jpeg');self.end_headers();self.wfile.write(raw);return
            return super().do_GET()
        except (ValueError,FileNotFoundError) as e: self.json({'error':str(e)},400)
    def do_POST(self):
        global ACTIVE
        try:
            if self.headers.get('Origin') and self.headers['Origin']!=f'http://{self.headers.get("Host")}': raise ValueError('只接受本地页面请求')
            size=int(self.headers.get('Content-Length',0))
            if not 0<size<=2_000_000: raise ValueError('请求体大小无效')
            data=json.loads(self.rfile.read(size)); path=urlparse(self.path).path
            if path in ['/api/pause','/api/resume']:
                folder=run_dir(data['id']);key=folder.name
                with LOCK:
                    proc=PROCESSES.get(key)
                    if key!=ACTIVE or proc is None or proc.poll() is not None:return self.json({'error':'实验已结束或仍在初始化'},409)
                    if path=='/api/pause':
                        if key not in PAUSED_AT:
                            proc.send_signal(signal.SIGSTOP);PAUSED_AT[key]=time.monotonic();write_json(folder/'status.json',{'status':'paused'})
                    elif key in PAUSED_AT:
                        proc.send_signal(signal.SIGCONT);PAUSES[key]=PAUSES.get(key,0)+time.monotonic()-PAUSED_AT.pop(key);write_json(folder/'status.json',{'status':'running'})
                return self.json({'status':'paused' if path=='/api/pause' else 'running'})
            if path=='/api/run':
                p,vehicle=vehicle_config(data);track=data.get('track','nanjing');meta=track_info(track)
                custom_xml=None
                if track=='nanjing':custom_xml,meta=track_for_width(vehicle['vehicle_width_m'])
                if not list((UPSTREAM/'build/lib').glob('*fastestlapc*.dylib')): return self.json({'error':'Fastest-lap 尚未编译完成'},409)
                with LOCK:
                    if ACTIVE: return self.json({'error':'已有实验在求解，请等待完成'},409)
                    key=uuid.uuid4().hex[:12]; folder=ROOT/'runs'/key;folder.mkdir(); ACTIVE=key
                    write_json(folder/'config.json',dict(params=p,vehicle=vehicle,record_iterations=bool(data.get('record_iterations',False)),name=str(data.get('name','实验'))[:80],created=time.strftime('%Y-%m-%d %H:%M:%S'),track=track,track_metadata=meta))
                    if custom_xml is not None:(folder/'track.xml').write_bytes(custom_xml)
                    else:shutil.copyfile(TRACK_PATHS[track],folder/'track.xml')
                    if track=='nanjing':shutil.copyfile(ROOT/'tracks/nanjing/geometry.json',folder/'geometry.json')
                    write_json(folder/'status.json',{'status':'running'})
                threading.Thread(target=solve_job,args=(folder,),daemon=True).start();return self.json({'id':key})
            if path=='/api/calibration':
                pairs=data['pairs']
                import math
                for key in ['scale','satellite_width','diagram_width']:
                    if len(pairs[key])!=2 or any(len(p)!=2 or any(not isinstance(v,(int,float)) or not math.isfinite(v) for v in p) for p in pairs[key]): raise ValueError('每组需两个有效端点')
                lengths={k:math.dist(*pairs[k]) for k in pairs}
                if any(v<2 for v in lengths.values()): raise ValueError('端点距离过小')
                mpp=25/lengths['scale']; result=dict(pairs=pairs,lengths_px=lengths,satellite_m_per_px=mpp,straight_width_m=lengths['satellite_width']*mpp,diagram_m_per_px=lengths['satellite_width']*mpp/lengths['diagram_width'],status='manual-draft',note='人工测量草稿：须核对同位置边界与垂直方向；未提取比赛边界。')
                write_json(ROOT/'tracks/calibration.json',result);return self.json(result)
            self.json({'error':'未知接口'},404)
        except (ValueError,KeyError,TypeError,OverflowError) as e: self.json({'error':str(e)},400)
    def log_message(self,*args): pass
if __name__=='__main__':
    port=int(sys.argv[1]) if len(sys.argv)>1 else 8765
    print(f'RacingLine http://127.0.0.1:{port}',flush=True)
    (ROOT/'runs').mkdir(exist_ok=True)
    ThreadingHTTPServer(('127.0.0.1',port),Handler).serve_forever()
