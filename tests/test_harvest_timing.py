import unittest

from astrafactory.harvest_timing import summarize_timing


class HarvestTimingTests(unittest.TestCase):
    def test_concurrent_arms_share_clock_and_count_timeout(self):
        rows = [dict(sim_s=.02, coordinator_phase='both', active_policies=['a', 'b']),
                dict(sim_s=.06, coordinator_phase='both'),
                dict(sim_s=.08, coordinator_phase='retreat', net_hold_steps=25)]
        out = summarize_timing(rows, dict(is_success=False))
        self.assertAlmostEqual(sum(p['duration_s'] for p in out['phases']), .08)
        self.assertAlmostEqual(out['phases'][0]['duration_s'], .06)
        self.assertEqual(out['first_sustained_net_retention_s'], .08)
        self.assertIsNone(out['accepted_harvest_to_placement_s'])

    def test_reset_start_placement_is_not_full_harvest(self):
        out = summarize_timing([dict(sim_s=2., placement_success=True)],
                               dict(is_success=True, placement_success=True))
        self.assertEqual(out['first_settled_placement_s'], 2.)
        self.assertFalse(out['full_harvest_completed'])
        self.assertIsNone(out['operational_good_fruit_per_hour'])

    def test_prior_invalid_cannot_be_hidden_by_final_success(self):
        rows = [dict(sim_s=1., invalid=True), dict(sim_s=2., placement_success=True)]
        result = dict(full_harvest_success=True, placement_success=True, invalid=False)
        self.assertIsNone(summarize_timing(rows, result)['accepted_harvest_to_placement_s'])

    def test_full_completion_requires_recorded_placement(self):
        result = dict(full_harvest_success=True, placement_success=True)
        self.assertFalse(summarize_timing([dict(sim_s=2.)], result)['full_harvest_completed'])
        out = summarize_timing([dict(sim_s=2., placement_success=True)], result)
        self.assertEqual(out['accepted_harvest_to_placement_s'], 2.)

    def test_bad_clocks_fail_closed(self):
        for times in [[1., 1.], [2., 1.], [float('nan')], [float('inf')]]:
            with self.assertRaises(ValueError):
                summarize_timing([dict(sim_s=t) for t in times], {})


if __name__ == '__main__':
    unittest.main()
