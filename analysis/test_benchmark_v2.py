"""Adversarial invariants for research controls; no production-safety claim."""
import unittest
import numpy as np
from benchmark_rolling_v2 import Booking, Day, Trip, safe_slots, run_policy, rolling_quota, make_day, features


class ForecastStub:
    kernels=[np.ones(6),np.ones(6)]
    def demand(self,day,t,kind):return np.ones((2,6))*20
    def remaining(self,active,now,horizons,kind):return np.zeros(len(horizons))


class GuardTests(unittest.TestCase):
    def test_departure_prediction_cannot_create_current_capacity(self):
        self.assertEqual(safe_slots(10,8,0),0)
        self.assertEqual(safe_slots(10,5,3),0)
        active=[(Trip(0,9999),0,9999) for _ in range(8)]
        quota,_,failed=rolling_quota(10,0,active,0,100,np.ones((2,6))*100,ForecastStub(),'ml')
        self.assertEqual((quota,failed),(0,0))

    def test_all_policies_preserve_promises_with_long_stays(self):
        day=make_day(30001,scenario='long_stays')
        for policy in ['fixed5','fixed10','reactive','rolling_average','rolling_ml','oracle_reference']:
            r,_=run_policy(day,25,policy,ForecastStub())
            self.assertEqual((r['failed'],r['physical_violations'],r['claim_violations']),(0,0,0),policy)
            self.assertEqual(r['accepted']+r['rejected'],r['requests'])

    def test_no_show_releases_after_grace_and_late_is_separate(self):
        late=Booking(0,1,3,True,600.,120)
        no_show=Booking(0,1,1,False,600.,120)
        b=[() for _ in range(26)];b[0]=(late,no_show)
        d=Day(1,0,tuple(() for _ in range(26)),tuple(b))
        r,_=run_policy(d,10,'fixed5',ForecastStub())
        self.assertEqual((r['accepted'],r['fulfilled'],r['late_expired'],r['failed']),(2,0,1,0))

    def test_fault_pauses_new_acceptance_but_preserves_existing_arrival(self):
        booked=Booking(9,10,10,True,120.,120)
        new=Booking(10,11,11,True,120.,120)
        b=[() for _ in range(26)];b[9]=(booked,);b[10]=(new,)
        d=Day(1,0,tuple(() for _ in range(26)),tuple(b))
        r,_=run_policy(d,20,'fixed5',ForecastStub(),scenario='outage')
        self.assertEqual((r['accepted'],r['rejected'],r['fulfilled'],r['fault_paused_requests']),(1,1,1,1))

    def test_seed_replay_is_identical(self):
        a,b=make_day(30000),make_day(30000)
        self.assertEqual(a,b)
        self.assertNotEqual(a,make_day(30001))

    def test_future_event_counts_do_not_leak_into_features(self):
        d=make_day(30000)
        modified=Day(d.seed,d.weekend,d.walkins[:5]+tuple(() for _ in range(21)),d.bookings[:5]+tuple(() for _ in range(21)))
        self.assertEqual(features(d,4,6),features(modified,4,6))

    def test_negative_control_exposes_broken_count_assumption(self):
        # Busy batch, then eight missing occupied-car records and new promises.
        walks=[() for _ in range(26)];walks[9]=tuple(Trip(9,600.) for _ in range(100))
        bookings=[() for _ in range(26)];bookings[10]=tuple(Booking(10,11,11,True,600.+i,120) for i in range(8))
        d=Day(1,0,tuple(walks),tuple(bookings))
        r,_=run_policy(d,30,'fixed0',ForecastStub(),scenario='undetected_drift')
        self.assertGreater(r['failed'],0)
        self.assertGreater(r['claim_violations'],0)
        self.assertEqual(r['physical_violations'],0)


if __name__=='__main__':unittest.main()
