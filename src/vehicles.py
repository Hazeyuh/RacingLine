"""Editable power and combined mass; preserve the upstream remaining physics."""
import json, math
from common import ROOT, validate_params
PRESETS = json.loads((ROOT/'vehicles/presets.json').read_text())
CURVES=json.loads((ROOT/'vehicles/engine-curves.json').read_text())
def vehicle_config(data):
    key=data.get('vehicle_preset','200cc')
    if key not in PRESETS: raise ValueError('未知车辆配置')
    vehicle=dict(PRESETS[key])
    for field,lo,hi in [('kart_mass_kg',40,250),('driver_mass_kg',20,150),('power_kw',1,60),('gear_ratio',2,12),('efficiency',.5,1),('limit_rpm',2500,6000),('clutch_rpm',1000,3000),('rear_wheel_radius_m',.08,.25),('vehicle_width_m',.8,2.0)]:
        value=float(data.get(field,vehicle[field]))
        if not math.isfinite(value) or not lo<=value<=hi: raise ValueError(f'{field} 必须在 {lo}–{hi} 之间')
        vehicle[field]=value
    if vehicle['clutch_rpm']>=vehicle['limit_rpm']:raise ValueError('离合器接合转速必须低于限转')
    params=validate_params(dict(mass=vehicle['kart_mass_kg']+vehicle['driver_mass_kg'],power_kw=vehicle['power_kw'],points=data.get('points',500)))
    curve='GX200' # One shared base shape; presets only supply editable parameters.
    if curve not in CURVES:raise ValueError('未知发动机曲线')
    vehicle['engine_curve']=curve
    vehicle['curve']=CURVES[curve]
    vehicle['modified']=any(vehicle[k]!=PRESETS[key][k] for k in ['kart_mass_kg','driver_mass_kg','power_kw','gear_ratio','efficiency','limit_rpm','clutch_rpm','rear_wheel_radius_m','engine_curve','vehicle_width_m'])
    return params,vehicle
