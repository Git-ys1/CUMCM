import unittest
import numpy as np
from Codex.solve.forecast import OnlinePVForecaster
from Codex.solve.io_data import read_attachment1,read_attachment2
from Codex.solve.lp_core import solve_dispatch,SOC_MIN,SOC_MAX
from Codex.solve.settle import execute_with_realtime_storage_feedback

class Q2Tests(unittest.TestCase):
    def test_attachment2_dimensions(self):
        data=read_attachment2()
        self.assertEqual(data.load_kw.shape,(365,144))
        self.assertEqual(data.pv_kw.shape,(365,144))
        self.assertEqual(len(data.dates),365)

    def test_forecast_is_sequential(self):
        price=np.ones(144); forecaster=OnlinePVForecaster(price)
        first=forecaster.predict()
        self.assertEqual(first.history_days_used,0)
        self.assertTrue(np.all(first.forecast_kw==0))
        actual=np.r_[np.zeros(40),np.ones(60)*100,np.zeros(44)]
        forecaster.observe(first,actual)
        second=forecaster.predict()
        self.assertEqual(second.history_days_used,1)
        self.assertTrue(np.allclose(second.bases["persistence"],actual))
        with self.assertRaises(ValueError):
            forecaster.observe(first,actual)

    def test_realtime_controller_constraints(self):
        day=read_attachment1()
        plan=solve_dispatch(day.load_kw,np.zeros(144),day.price,soc_initial=6000,soc_terminal=6000)
        actual=np.maximum(day.pv_kw*1.3,0)
        execution=execute_with_realtime_storage_feedback(plan,day.load_kw,actual,soc_initial=6000)
        balance=execution.grid+actual/6+execution.discharge+execution.emergency-day.load_kw/6-execution.charge-execution.curtail
        self.assertLess(float(np.max(np.abs(balance))),1e-7)
        self.assertGreaterEqual(float(execution.soc.min()),SOC_MIN-1e-7)
        self.assertLessEqual(float(execution.soc.max()),SOC_MAX+1e-7)
        self.assertLess(float(np.max(np.minimum(execution.charge,execution.discharge))),1e-7)

if __name__=="__main__": unittest.main()
