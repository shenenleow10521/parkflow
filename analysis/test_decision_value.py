"""Information isolation and promise protection in the event-driven harness."""
import unittest
import numpy as np
from benchmark_decision_value import Day, Event, END, H, history_features, hard_slots, simulate, make_day, plan_protection


class Stub:
    matrix=np.zeros((H,2*H))
    for h in range(H):
        for k in range(h+1):matrix[h,k]=matrix[h,H+k]=1.
    def remaining(self,visible,now):return np.zeros(H)+len(visible)


def empty_predictions():return {k:np.zeros((END//15,H)) for k in ['mean','adaptive','linear','ml','oracle','public']}


class EventTests(unittest.TestCase):
    def test_asof_features_exclude_current_and_future_events(self):
        d=make_day(61000);requests=d.requests.copy();walks=d.walkins.copy()
        requests[100:]+=100;walks[100:]+=100
        alternative=Day(d.seed,d.weekend,d.events,requests,walks)
        np.testing.assert_array_equal(history_features(d,100),history_features(alternative,100))

    def test_future_prediction_does_not_authorize_promise(self):
        self.assertEqual(hard_slots(10,7,1),0)
        reserve,failed,_=plan_protection(10,1,[(0,False,120)]*7,30,np.ones(H)*100,np.ones(H)*100,Stub(),5)
        self.assertEqual((reserve,failed),(0,0))

    def test_event_interleaving_respects_recorded_order(self):
        # Three physical slots (two spare): a walk-in uses the only bookable
        # slot before a request, so that request must be rejected, not reordered.
        a=Event(1,0,False,.1,120.)
        b=Event(2,0,True,.2,120.,20,20,True,120)
        d=Day(1,0,(a,b),np.r_[1,np.zeros(END-1)],np.r_[1,np.zeros(END-1)])
        r,_,_=simulate(d,3,'guard',empty_predictions(),Stub())
        self.assertEqual((r['walkins'],r['accepted'],r['rejected']),(1,0,1))

    def test_accepted_claim_survives_long_stay_pressure(self):
        b=Event(1,0,True,.1,9999.,180,180,True,120)
        w=tuple(Event(2+i,1,False,i/100,9999.) for i in range(30))
        d=Day(1,0,(b,*w),np.zeros(END),np.zeros(END))
        for policy in ['guard','fixed5','lp_mean','lp_ml']:
            r,_,_=simulate(d,10,policy,empty_predictions(),Stub())
            self.assertEqual((r['fulfilled'],r['failed'],r['claim_violations'],r['physical_violations']),(1,0,0,0),policy)

    def test_no_show_and_expired_late_are_distinct(self):
        events=(Event(1,0,True,.1,120.,20,20,False),Event(2,0,True,.2,120.,20,45,True))
        d=Day(1,0,events,np.zeros(END),np.zeros(END))
        r,_,_=simulate(d,10,'guard',empty_predictions(),Stub())
        self.assertEqual((r['accepted'],r['no_shows'],r['expired_late'],r['failed']),(2,1,1,0))

    def test_generated_streams_are_immutable_and_replayable(self):
        a,b=make_day(61000),make_day(61000)
        self.assertEqual(a.events,b.events)
        self.assertFalse(a.requests.flags.writeable)
        self.assertTrue(all(e.due<END for e in a.events if e.request))


if __name__=='__main__':unittest.main()
