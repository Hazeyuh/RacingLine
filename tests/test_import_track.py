import copy, importlib.util, json, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('import_track',ROOT/'tools/import_track.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class TrackImportTests(unittest.TestCase):
    def setUp(self):self.trace=json.loads((ROOT/'tracks/templates/tablet-trace.json').read_text())
    def test_reproducible_build_and_width(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);a=module.build(self.trace,p);first=(p/'tablet-demo.xml').read_bytes()
            b=module.build(self.trace,p);self.assertEqual(first,(p/'tablet-demo.xml').read_bytes())
            self.assertEqual(a['geometry_sha256'],b['geometry_sha256'])
            self.assertAlmostEqual(a['m_per_px'],.1);self.assertGreater(a['minimum_corridor_width_m'],6)
            wide=copy.deepcopy(self.trace);wide['vehicle_width_m']=1.8;c=module.build(wide,p)
            self.assertLess(c['minimum_corridor_width_m'],a['minimum_corridor_width_m'])
    def test_missing_or_zero_scale_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.trace['calibration']['length_m']=0
            with self.assertRaises(ValueError):module.build(self.trace,Path(tmp))
    def test_self_crossing_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.trace['centerline_px']=[[100,100],[400,400],[700,700],[700,100],[400,400],[100,700]]
            with self.assertRaises(ValueError):module.build(self.trace,Path(tmp))
    def test_reserved_id_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.trace['id']='nanjing'
            with self.assertRaises(ValueError):module.build(self.trace,Path(tmp))
