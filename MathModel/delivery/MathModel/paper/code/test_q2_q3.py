import unittest
import numpy as np
from ..solve.io_data import read_attachment1,read_attachment2,read_attachment3,read_attachment4,hourly_to_ten_min
from ..solve.forecast import OnlinePVForecaster
from ..solve.lp_core import solve_dispatch,solve_adjustment_dispatch,SOC_MIN,SOC_MAX
from ..solve.q3 import run_q3
from ..solve.settle import execute_with_realtime_storage_feedback
class Q2Q3Tests(unittest.TestCase):
    def test_attachment_dimensions(self):
        data=read_attachment2(); forecast=read_attachment3(); prices=read_attachment4()
        self.assertEqual(data.load_kw.shape,(365,144)); self.assertEqual(data.pv_kw.shape,(365,144))
        self.assertEqual(forecast.hourly_kw.shape,(365,4,24)); self.assertEqual(prices.price.shape,(365,144))
        step=hourly_to_ten_min(forecast.hourly_kw[0,0],"step")
        self.assertAlmostEqual(float(step.sum()/6),float(forecast.hourly_kw[0,0].sum()),places=9)
    def test_forecast_is_sequential(self):
        f=OnlinePVForecaster(np.ones(144)); first=f.predict(); self.assertEqual(first.history_days_used,0)
        actual=np.r_[np.zeros(40),np.ones(60)*100,np.zeros(44)]; f.observe(first,actual)
        second=f.predict(); self.assertEqual(second.history_days_used,1)
        self.assertTrue(np.allclose(second.bases["persistence"],actual))
        with self.assertRaises(ValueError): f.observe(first,actual)
    def test_realtime_controller_constraints(self):
        day=read_attachment1(); plan=solve_dispatch(day.load_kw,np.zeros(144),day.price,soc_initial=6000,soc_terminal=6000)
        actual=np.maximum(day.pv_kw*1.3,0); execution=execute_with_realtime_storage_feedback(plan,day.load_kw,actual,soc_initial=6000)
        balance=execution.grid+actual/6+execution.discharge+execution.emergency-day.load_kw/6-execution.charge-execution.curtail
        self.assertLess(float(np.max(np.abs(balance))),1e-7)
        self.assertGreaterEqual(float(execution.soc.min()),SOC_MIN-1e-7)
        self.assertLessEqual(float(execution.soc.max()),SOC_MAX+1e-7)
        self.assertLess(float(np.max(np.minimum(execution.charge,execution.discharge))),1e-7)
    def test_adjustment_linearization(self):
        gp=np.array([900.0,900.0,700.0]); ga=np.array([700.0,900.0,900.0])
        b=np.maximum(ga-gp,0); linear=0.5*gp+0.5*ga+b
        piece=np.minimum(gp,ga)+0.5*np.maximum(gp-ga,0)+1.5*np.maximum(ga-gp,0)
        self.assertTrue(np.allclose(linear,[800,900,1000])); self.assertTrue(np.allclose(linear,piece))
    def test_adjustment_solver_balance(self):
        day=read_attachment1(); base=solve_dispatch(day.load_kw,day.pv_kw,day.price,soc_initial=6000,soc_terminal=6000)
        result=solve_adjustment_dispatch(day.load_kw,day.pv_kw*0.9,day.price,base.grid,np.ones(144,dtype=bool),
                                         soc_initial=6000,soc_terminal=6000)
        d=result.dispatch
        residual=d.grid+day.pv_kw*0.9/6+d.discharge-day.load_kw/6-d.charge-d.curtail
        self.assertLess(float(np.max(np.abs(residual))),1e-7)
        self.assertLess(float(np.max(np.abs(result.increase-np.maximum(d.grid-base.grid,0)))),1e-6)
    def test_additive_milp_enforces_storage_exclusivity(self):
        day=read_attachment1(); base=solve_dispatch(day.load_kw,day.pv_kw,day.price,soc_initial=6000,soc_terminal=6000)
        result=solve_adjustment_dispatch(day.load_kw,day.pv_kw*0.9,day.price,base.grid,np.ones(144,dtype=bool),
                                         soc_initial=6000,soc_terminal=6000,settlement_mode="additive")
        self.assertLess(float(np.max(np.minimum(result.dispatch.charge,result.dispatch.discharge))),1e-9)
    def test_disabled_nodes_keep_latest_active_plan(self):
        result=run_q3(max_days=2,write_outputs=False,update_nodes=(0,36),settlement_mode="replacement")
        record=result["records"][-1]
        self.assertTrue(np.all(record["plan_source_nodes"][:36]==0))
        self.assertTrue(np.all(record["plan_source_nodes"][36:]==36))
        self.assertLess(float(np.max(np.abs(record["adjusted_grid"][72:]-record["revisions"][1,72:]))),1e-9)
if __name__=="__main__": unittest.main()
