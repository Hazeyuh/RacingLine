#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from common import ROOT,UPSTREAM,write_json
from nanjing import track_for_width
xml,meta=track_for_width();out=ROOT/'tracks/nanjing';(out/'nanjing.xml').write_bytes(xml);write_json(out/'metadata.json',meta)
sys.path.insert(0,str(UPSTREAM/'examples/python'));import fastest_lap as fl
fl.create_track_from_xml('nanjing',str(out/'nanjing.xml'));assert abs(fl.track_download_length('nanjing')-meta['track_length_m'])<1e-5
print('Native reader verified',meta)
