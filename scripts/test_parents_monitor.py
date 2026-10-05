import unittest
from parents_monitor import check_channel, evaluate, playlists


class MonitorTests(unittest.TestCase):
    def test_independent_backup_recovers_primary_failure(self):
        sources = {'primary': playlists('CCTV1,http://bad#http://bad2\n'),
                   'backup': playlists('CCTV1,http://good\n')}
        row = check_channel('CCTV1', sources, lambda url: url == 'http://good')
        self.assertTrue(row['decoded'])
        self.assertFalse(row['sources'][0]['decoded'])
        self.assertTrue(row['sources'][1]['decoded'])

    def test_missing_and_continuous_failures_raise_only_after_two_runs(self):
        row = check_channel('CCTV13', {'primary': {}}, lambda url: True)
        state, reasons = evaluate({}, [row], [])
        self.assertFalse(reasons)
        state, reasons = evaluate(state, [row], [])
        self.assertTrue(reasons)
        state, reasons = evaluate(state, [{'channel': 'CCTV13', 'decoded': True}], [])
        self.assertFalse(reasons)
        self.assertEqual(0, state['failures']['CCTV13'])

    def test_stale_list_alerts_even_when_video_decodes(self):
        _, reasons = evaluate({}, [{'channel': 'CCTV1', 'decoded': True}], ['primary'])
        self.assertTrue(reasons)
