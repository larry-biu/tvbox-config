import datetime as dt
import unittest
from watchdog import recovery_reason


class WatchdogTests(unittest.TestCase):
    def test_recovery_and_concurrency(self):
        current = dt.datetime(2026, 10, 2, tzinfo=dt.timezone.utc)
        workflow = {'state': 'active'}
        run = {'status': 'completed', 'conclusion': 'success', 'created_at': '2026-10-01T22:00:00Z'}
        self.assertIsNone(recovery_reason(workflow, [run], current))
        self.assertIsNotNone(recovery_reason({'state': 'disabled_inactivity'}, [run], current))
        self.assertIsNotNone(recovery_reason(workflow, [], current))
        self.assertIsNotNone(recovery_reason(workflow, [dict(run, conclusion='failure')], current))
        self.assertIsNotNone(recovery_reason(workflow, [dict(run, created_at='2026-10-01T01:00:00Z')], current))
        self.assertIsNone(recovery_reason(workflow, [dict(run, status='in_progress')], current))
