import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from common import validate_params,parse_iterations
from vehicles import vehicle_config,CURVES
class CoreTests(unittest.TestCase):
    def test_vehicle_mass_and_power(self):
        for key,power in [('200cc',4.8),('270cc',6.3)]:
            p,v=vehicle_config({'vehicle_preset':key})
            self.assertEqual(p['mass'],170);self.assertEqual(p['power_kw'],power)
        p,v=vehicle_config({'driver_mass_kg':80,'kart_mass_kg':110,'power_kw':5.2})
        self.assertEqual(p['mass'],190);self.assertTrue(v['modified'])
        for data in [{'driver_mass_kg':float('nan')},{'kart_mass_kg':-1},{'vehicle_preset':'unknown'}]:
            with self.assertRaises(ValueError):vehicle_config(data)
    def test_reference_curves_and_rpm_settings(self):
        for c in CURVES.values():
            self.assertLess(c['fit_max_error_nm'],.15)
            self.assertEqual(c['rpm'][0],2000)
            self.assertEqual(c['rpm'][-1],3600)
            self.assertAlmostEqual(c['torque_nm'][-1]*3600*3.141592653589793/30/1000,c['rated_power_kw'])
        _,v=vehicle_config({'limit_rpm':3000,'gear_ratio':6,'engine_curve':'GX270'})
        self.assertEqual(v['limit_rpm'],3000);self.assertEqual(v['gear_ratio'],6);self.assertEqual(v['engine_curve'],'GX200')
        _,small=vehicle_config({'vehicle_preset':'200cc','power_kw':8})
        _,large=vehicle_config({'vehicle_preset':'270cc','power_kw':8})
        self.assertEqual(small['curve'],large['curve']);self.assertEqual(small['power_kw'],8)
        with self.assertRaises(ValueError):vehicle_config({'limit_rpm':2500,'clutch_rpm':2600})
    def test_bad_input(self):
        for value in [float('nan'),-1,10000]:
            with self.assertRaises(ValueError):validate_params({'mass':value})
    def test_native_iteration_log(self):
        log='''iter    objective    inf_pr   inf_du lg(mu)
   0  7.3152901e+01 3.27e+00 1.02e-01 0.0
  12r 6.0234923e+01 5.32e-03 2.13e+01 -1.0
Number of Iterations....: 12'''
        r=parse_iterations(log)
        self.assertEqual(len(r),2);self.assertEqual(r[1]['iteration'],12)
        self.assertAlmostEqual(r[1]['constraint_error'],.00532)
if __name__=='__main__':unittest.main()
