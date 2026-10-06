import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from tracks import track_info,TRACK_PATHS
import json,numpy as np
from shapely.geometry import LineString,Polygon,Point
class NanjingGeometry(unittest.TestCase):
    def test_closed_simple_geometry(self):
        g=json.loads((TRACK_PATHS['nanjing'].parent/'geometry.json').read_text())
        for key in ['center_px','left_px','right_px']:
            p=np.array(g[key]);self.assertTrue(LineString(np.r_[p,p[:1]]).is_simple,key)
        self.assertFalse(LineString(g['left_px']).intersects(LineString(g['right_px'])))
    def test_traceable_scale_and_envelope(self):
        m=track_info('nanjing');cal=m['calibration'];pairs=cal['pairs']
        dist=lambda p:np.linalg.norm(np.subtract(p[1],p[0]))
        scale=25/dist(pairs['scale'])*dist(pairs['satellite_width'])/dist(pairs['diagram_width'])
        self.assertAlmostEqual(m['m_per_px'],scale)
        self.assertAlmostEqual(m['inset_per_side_m'],m['vehicle_envelope_m']/2+m['safety_margin_per_side_m']+m.get('discretization_guard_per_side_m',0))
        self.assertGreater(m['minimum_corridor_width_m'],.4)
    def test_width_changes_solver_corridor(self):
        from nanjing import track_for_width
        import xml.etree.ElementTree as ET
        small,sm=track_for_width(1.1);large,lm=track_for_width(1.6)
        self.assertEqual(sm['geometry_sha256'],lm['geometry_sha256'])
        self.assertNotEqual(sm['xml_sha256'],lm['xml_sha256'])
        for path in ['data/nl','data/nr']:
            a=np.fromstring(ET.fromstring(small).find(path).text,sep=',')
            b=np.fromstring(ET.fromstring(large).find(path).text,sep=',')
            self.assertTrue(np.all(b<=a+1e-6))
        self.assertLess(lm['minimum_corridor_width_m'],sm['minimum_corridor_width_m'])
    def test_kerbs_and_reference_coordinates(self):
        from nanjing import track_for_width
        import xml.etree.ElementTree as ET
        g=json.loads((TRACK_PATHS['nanjing'].parent/'geometry.json').read_text())
        road=Polygon(g['left_px']).difference(Polygon(g['right_px']))
        for p in [[157,280],[446,258],[558,262],[497,318],[805,308],[900,254]]:
            self.assertTrue(road.covers(Point(p)),p)
        for p in [[155,325],[450,320],[720,272],[550,500]]:
            self.assertFalse(road.covers(Point(p)),p)
        xml,_=track_for_width(1.4);tree=ET.fromstring(xml)
        arr=lambda key:np.fromstring(tree.find('data/'+key).text,sep=',')
        self.assertGreater(np.min(1+arr('yaw_dot')*arr('nl')),.1)
        self.assertGreater(np.min(1-arr('yaw_dot')*arr('nr')),.1)
    def test_unknown_track(self):
        with self.assertRaises(ValueError):track_info('../../README')
