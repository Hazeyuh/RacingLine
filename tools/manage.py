#!/usr/bin/env python3
"""Local service lifecycle; standard library only, no application dependencies."""
import argparse, fcntl, json, os, signal, socket, subprocess, sys, time, urllib.request, webbrowser
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description='RacingLine 后台与网页入口')
    parser.add_argument('action',nargs='?',default='start',choices=['start','stop','restart','status','open','menu'])
    parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--no-open',action='store_true',help='启动后不打开浏览器')
    parser.add_argument('--force',action='store_true',help='停止正在运行或暂停的求解')
    args=parser.parse_args()
    if not 1024<=args.port<=65535:parser.error('端口必须在 1024–65535 之间')
    folder=ROOT/'runs';folder.mkdir(exist_ok=True)
    state=folder/f'server-{args.port}.json';url=f'http://127.0.0.1:{args.port}'
    def health():
        try:
            with urllib.request.urlopen(url+'/api/health',timeout=1) as r:data=json.load(r)
            return data
        except Exception:
            try:
                with socket.create_connection(('127.0.0.1',args.port),timeout=.2):return {'occupied':True}
            except OSError:return None
    def own(data):return data and data.get('project_root')==str(ROOT)
    def running():
        h=health()
        if h and not own(h):raise RuntimeError(f'{url} 被其他服务或旧版后台占用；请先退出旧后台，或使用 --port 8766')
        return h
    def start():
        h=running()
        if own(h):print(f'后台已运行：{url}（PID {h["pid"]}）')
        else:
            python=ROOT/'.venv/bin/python'
            if not python.exists():raise RuntimeError('尚未安装，请先运行 ./tools/setup.sh')
            with (folder/f'server-{args.port}.log').open('ab') as log:
                proc=subprocess.Popen([str(python),str(ROOT/'tools/server.py'),str(args.port)],cwd=ROOT,stdout=log,stderr=log,stdin=subprocess.DEVNULL,start_new_session=True)
            state.write_text(json.dumps({'pid':proc.pid,'project_root':str(ROOT),'port':args.port}))
            for _ in range(100):
                h=health()
                if own(h) and h['pid']==proc.pid:break
                if proc.poll() is not None:raise RuntimeError(f'启动失败，请查看 runs/server-{args.port}.log；端口可能被占用')
                time.sleep(.1)
            else:
                proc.terminate();raise RuntimeError('启动超时，请查看后台日志')
            print(f'后台已启动：{url}（PID {proc.pid}）')
        if not args.no_open: webbrowser.open(url)
    def stop():
        h=running()
        if not own(h):print('后台未运行');return
        if h.get('active') and not args.force:raise RuntimeError('有运行或暂停中的求解；请等待完成。确需终止可加 --force，实验将标记为中断。')
        pid=h['pid']
        # Recheck server identity immediately before signalling it.
        check=health()
        if not own(check) or check['pid']!=pid:raise RuntimeError('后台进程发生变化，请重试')
        os.kill(pid,signal.SIGTERM)
        for _ in range(100):
            process_state=subprocess.run(['ps','-p',str(pid),'-o','stat='],capture_output=True,text=True).stdout.strip()
            if not process_state or process_state.startswith('Z'):break
            time.sleep(.1)
        else:raise RuntimeError('后台未能正常退出，请查看日志')
        state.unlink(missing_ok=True);print('后台已停止')
    if args.action=='menu':
        print('RacingLine：1 启动并打开网页  2 停止后台  3 查看状态  4 重启  5 打开网页  0 退出')
        while True:
            choice=input('选择操作 [1]：').strip() or '1'
            try:
                if choice=='0':return
                if choice in ['1','2','3','4','5']:
                    command=[sys.executable,str(Path(__file__)),{'1':'start','2':'stop','3':'status','4':'restart','5':'open'}[choice],'--port',str(args.port)]
                    if args.no_open:command.append('--no-open')
                    if args.force:command.append('--force')
                    subprocess.run(command)
                else:print('请输入 0–5')
            except RuntimeError as e:print(e)
    else:
        with (folder/f'server-{args.port}.lock').open('w') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            if args.action=='start':start()
            elif args.action=='stop':stop()
            elif args.action=='restart':stop();start()
            elif args.action=='status':print(json.dumps(running() or {'status':'stopped'},ensure_ascii=False,indent=2))
            elif args.action=='open':
                if not own(running()):raise RuntimeError('后台未运行，请先运行 ./racingline start')
                webbrowser.open(url)
if __name__=='__main__':
    try:main()
    except (RuntimeError,KeyboardInterrupt) as e:print(str(e),file=sys.stderr);sys.exit(1)
