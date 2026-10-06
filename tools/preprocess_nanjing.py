#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from common import ROOT,UPSTREAM
sys.path.insert(0,str(UPSTREAM/'examples/python'))
import fastest_lap as fl
out=ROOT/'tracks/nanjing'
options=f'''<options><kml_files><left>{out/'left.kml'}</left><right>{out/'right.kml'}</right></kml_files><mode>equally-spaced</mode><is_closed>true</is_closed><number_of_elements>600</number_of_elements><xml_file_name>{out/'nanjing.xml'}</xml_file_name><print_level>5</print_level><optimization><cost_curvature>10</cost_curvature><cost_centerline>1</cost_centerline><cost_track_limits_errors>100</cost_track_limits_errors><cost_track_limits_smoothness>1</cost_track_limits_smoothness></optimization></options>'''
(out/'preprocess-options.xml').write_text(options)
fl.circuit_preprocessor(options)
if not (out/'nanjing.xml').exists():raise RuntimeError('预处理未产生 XML')
fl.create_track_from_xml('nanjing',str(out/'nanjing.xml'))
print('Verified XML length:',fl.track_download_length('nanjing'))
