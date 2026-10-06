from pathlib import Path
import json, math, re
ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / 'upstream/fastest-lap'
DEFAULTS = dict(mass=165., power_kw=20.1, brake_nm=200., grip=1.5, cd=0.7, points=120)
LIMITS = dict(mass=(70,400), power_kw=(1,60), brake_nm=(10,500), grip=(0.3,2.5), cd=(0.1,2), points=(80,1000))
def validate_params(data):
    out = {}
    for k, (lo,hi) in LIMITS.items():
        v = float(data.get(k,DEFAULTS[k]))
        if not math.isfinite(v) or not lo <= v <= hi:
            raise ValueError(f'{k} 必须在 {lo}–{hi} 之间')
        out[k] = int(v) if k=='points' else v
    return out

def parse_iterations(log):
    rows=[]
    for line in log.splitlines():
        m=re.match(r'^\s*(\d+)[r]?\s+([-+\d.eE]+)\s+([-+\d.eE]+)\s+([-+\d.eE]+)',line)
        if m:
            rows.append(dict(iteration=int(m[1]),objective=float(m[2]),constraint_error=float(m[3]),dual_error=float(m[4])))
    return rows

def write_json(path,data):
    path=Path(path)
    temp=path.with_suffix('.tmp')
    temp.write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False))
    temp.replace(path)
