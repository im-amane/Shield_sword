"""Tests for bounded token-bucket request limiting."""
import unittest

from app.rate_limit import TokenBucketLimiter


class FakeClock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class RequestRateLimitTests(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.limiter = TokenBucketLimiter(clock=self.clock)

    def test_allows_initial_burst_then_rejects_excess(self):
        for _ in range(5):
            self.assertTrue(self.limiter.allow(
                ("user", 1), capacity=5, refill_per_second=0.5
            ))
        self.assertFalse(self.limiter.allow(
            ("user", 1), capacity=5, refill_per_second=0.5
        ))

    def test_refills_at_configured_rate(self):
        for _ in range(5):
            self.limiter.allow(("user", 1), capacity=5, refill_per_second=0.5)
        self.clock.advance(2)
        self.assertTrue(self.limiter.allow(
            ("user", 1), capacity=5, refill_per_second=0.5
        ))
        self.assertFalse(self.limiter.allow(
            ("user", 1), capacity=5, refill_per_second=0.5
        ))

    def test_users_have_independent_buckets(self):
        for _ in range(5):
            self.limiter.allow(("user", 1), capacity=5, refill_per_second=0.5)
        self.assertTrue(self.limiter.allow(
            ("user", 2), capacity=5, refill_per_second=0.5
        ))

    def test_group_bucket_can_be_shared_across_users(self):
        self.assertTrue(self.limiter.allow(
            ("group", -100), capacity=2, refill_per_second=1
        ))
        self.assertTrue(self.limiter.allow(
            ("group", -100), capacity=2, refill_per_second=1
        ))
        self.assertFalse(self.limiter.allow(
            ("group", -100), capacity=2, refill_per_second=1
        ))

    def test_idle_state_is_pruned(self):
        self.limiter.allow(("old", 1), capacity=1, refill_per_second=1)
        self.clock.advance(181)
        for index in range(255):
            self.limiter.allow(("new", index), capacity=1000, refill_per_second=1)
        self.limiter.allow(("trigger-prune",), capacity=1, refill_per_second=1)
        self.assertNotIn(("old", 1), self.limiter._buckets)


if __name__ == "__main__":
    unittest.main()
