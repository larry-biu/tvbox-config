import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import parents_alert as module


class AlertTests(unittest.TestCase):
    def run_alert(self, report, issue=None):
        calls = []
        def api(repo, path, method='GET', body=None):
            calls.append((path, method, body))
            return [issue] if method == 'GET' and issue else ([] if method == 'GET' else {})
        with TemporaryDirectory() as d:
            root = Path(d)
            (root/'parents-health.json').write_text(json.dumps(report))
            with patch.object(module, 'ROOT', root), patch.object(module, 'request', side_effect=api), patch.dict(os.environ, {'GITHUB_REPOSITORY': 'owner/repo', 'GITHUB_RUN_ID': '1', 'MAINTENANCE_FAILED': 'false'}):
                module.main()
        return calls

    def test_repeated_alert_does_not_notify_again(self):
        reason = 'failed'
        issue = {'title': module.TITLE, 'number': 1, 'state': 'open', 'body': '<!-- parents-reasons:failed -->'}
        self.assertEqual(1, len(self.run_alert({'alert_reasons': [reason]}, issue)))

    def test_no_failure_creates_no_issue(self):
        self.assertEqual(1, len(self.run_alert({'alert_reasons': [], 'healthy_runs': 1})))

    def test_recovery_requires_two_healthy_runs(self):
        issue = {'title': module.TITLE, 'number': 1, 'state': 'open', 'body': 'failure'}
        self.assertEqual(1, len(self.run_alert({'healthy_runs': 1}, issue)))
        calls = self.run_alert({'healthy_runs': 2}, issue)
        self.assertEqual('closed', calls[-1][2]['state'])

    def test_first_actionable_failure_mentions_owner(self):
        calls = self.run_alert({'alert_reasons': ['two failed checks']})
        self.assertIn('@owner', calls[-1][2]['body'])
