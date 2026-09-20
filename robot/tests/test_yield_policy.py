import unittest

from yield_policy import YieldAction, YieldPolicy


class YieldPolicyTests(unittest.TestCase):
    def test_clear_above_trigger(self):
        policy = YieldPolicy()
        self.assertEqual(
            policy.decide(front_min_m=1.21, rear_min_m=1.0, sample_age_s=0.01),
            YieldAction.CLEAR,
        )

    def test_retreat_below_trigger_when_rear_is_clear(self):
        policy = YieldPolicy()
        self.assertEqual(
            policy.decide(front_min_m=1.19, rear_min_m=1.0, sample_age_s=0.01),
            YieldAction.RETREAT,
        )

    def test_stop_below_trigger_when_rear_is_blocked(self):
        policy = YieldPolicy()
        self.assertEqual(
            policy.decide(front_min_m=1.19, rear_min_m=0.59, sample_age_s=0.01),
            YieldAction.STOP,
        )

    def test_latch_releases_only_at_release_distance(self):
        policy = YieldPolicy()
        policy.decide(front_min_m=1.19, rear_min_m=1.0, sample_age_s=0.01)
        self.assertEqual(
            policy.decide(front_min_m=1.30, rear_min_m=1.0, sample_age_s=0.01),
            YieldAction.RETREAT,
        )
        self.assertEqual(
            policy.decide(front_min_m=1.40, rear_min_m=1.0, sample_age_s=0.01),
            YieldAction.CLEAR,
        )

    def test_stale_or_missing_ranges_fail_safe(self):
        policy = YieldPolicy()
        self.assertEqual(
            policy.decide(front_min_m=2.0, rear_min_m=2.0, sample_age_s=0.26),
            YieldAction.STOP,
        )
        policy = YieldPolicy()
        self.assertEqual(
            policy.decide(front_min_m=None, rear_min_m=2.0, sample_age_s=0.01),
            YieldAction.STOP,
        )


if __name__ == "__main__":
    unittest.main()
