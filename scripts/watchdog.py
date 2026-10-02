#!/usr/bin/env python3
"""GitHub云端检查维护任务；无本机调度、无外部账号凭证。"""
import datetime as dt
import json
import os
import urllib.request


def recovery_reason(workflow, runs, current):
    if workflow['state'] != 'active':
        return 'maintenance workflow is disabled'
    if not runs:
        return 'no maintenance run exists'
    latest = runs[0]
    if latest['status'] != 'completed':
        return None
    if latest['conclusion'] != 'success':
        return 'latest maintenance run failed'
    created = dt.datetime.fromisoformat(latest['created_at'].replace('Z', '+00:00'))
    if current - created > dt.timedelta(hours=12):
        return 'maintenance has not run for over 12 hours'
    return None


def main():
    repo = os.environ['GITHUB_REPOSITORY']
    token = os.environ['GH_TOKEN']
    def api(path, method='GET', body=None):
        request = urllib.request.Request('https://api.github.com/repos/'+repo+'/'+path,
            data=json.dumps(body).encode() if body is not None else None,
            headers={'Authorization': 'Bearer '+token, 'Accept': 'application/vnd.github+json',
                     'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'TVConfigCloudWatchdog'}, method=method)
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read()
        return json.loads(raw) if raw else None
    workflow = api('actions/workflows/maintain.yml')
    runs = api('actions/workflows/maintain.yml/runs?branch=main&per_page=1')['workflow_runs']
    reason = recovery_reason(workflow, runs, dt.datetime.now(dt.timezone.utc))
    if workflow['state'] != 'active':
        api('actions/workflows/maintain.yml/enable', method='PUT')
    if reason:
        api('actions/workflows/maintain.yml/dispatches', method='POST', body={'ref': 'main'})
    print(json.dumps({'maintenance_state': workflow['state'], 'latest_run': runs[0]['id'] if runs else None,
                      'recovery_dispatched': bool(reason), 'reason': reason}, ensure_ascii=False))


if __name__ == '__main__':
    main()
