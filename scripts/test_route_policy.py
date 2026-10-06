import unittest
from route_policy import apply


class RoutePolicyTests(unittest.TestCase):
    def test_preferred_is_restored_and_stays_first_after_upstream_shuffle(self):
        p = {'preferred_routes': {'CCTV1': ['http://good/1']}}
        self.assertEqual(['http://good/1', 'http://other/1'], apply('CCTV1', ['http://other/1'], p))
        self.assertEqual(['http://good/1', 'http://other/1'], apply('CCTV1', ['http://other/1', 'http://good/1'], p))

    def test_ad_provider_quarantine_applies_across_channels(self):
        p = {'blocked_route_hosts': ['ads.example']}
        self.assertEqual(['http://good/2'], apply('CCTV2', ['http://ads.example:82/cctv2', 'http://good/2'], p))

    def test_cctv1_blue_exception_does_not_block_other_channels(self):
        p = {'blocked_channel_routes': {'CCTV1': ['http://provider/1']}}
        self.assertEqual([], apply('CCTV1', ['http://provider/1'], p))
        self.assertEqual(['http://provider/1', 'http://provider/2'], apply('CCTV2', ['http://provider/1', 'http://provider/2'], p))

    def test_blacklist_overrides_pinned_preference(self):
        p = {'preferred_routes': {'CCTV1': ['http://ads/1']}, 'blocked_route_hosts': ['ads']}
        self.assertEqual(['http://good/1'], apply('CCTV1', ['http://good/1'], p))
