"""One repository issue for actionable failures; no repeated unchanged comments."""
import json
import os
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TITLE = '父母电视直播：云端巡检异常'


def request(repo, endpoint, method='GET', body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request('https://api.github.com/repos/'+repo+endpoint, data=data, method=method,
                                 headers={'Authorization': 'Bearer '+os.environ['GH_TOKEN'],
                                          'Accept': 'application/vnd.github+json', 'User-Agent': 'parents-live-monitor'})
    with urllib.request.urlopen(req, timeout=25) as response:
        return json.load(response)


def main():
    repo = os.environ['GITHUB_REPOSITORY']
    run = 'https://github.com/'+repo+'/actions/runs/'+os.environ['GITHUB_RUN_ID']
    failed = os.environ.get('MAINTENANCE_FAILED') == 'true'
    report_file = ROOT/'parents-health.json'
    report = json.loads(report_file.read_text()) if report_file.exists() else {}
    reasons = ['云端维护或发布失败，需要查看本轮日志'] if failed else report.get('alert_reasons', [])
    issues = request(repo, '/issues?state=all&per_page=100')
    issue = next((x for x in issues if x['title'] == TITLE and 'pull_request' not in x), None)
    owner = repo.split('/')[0]
    signature = '\n'.join(reasons)
    body = ('@'+owner+' 云端检测出现以下问题：\n\n'+
            '\n'.join('- '+x for x in reasons)+'\n\n'+
            '检测来自 GitHub 运行环境，不能据此判定家中电视故障。旧清单保留，自动恢复仍在运行。\n\n'+
            '[本轮日志]('+run+')\n\n<!-- parents-reasons:'+signature+' -->')
    marker = '<!-- parents-reasons:'+signature+' -->'
    if reasons:
        if issue is None:
            request(repo, '/issues', 'POST', {'title': TITLE, 'body': body})
        elif issue['state'] == 'closed':
            request(repo, '/issues/'+str(issue['number']), 'PATCH', {'state': 'open', 'body': body})
            request(repo, '/issues/'+str(issue['number'])+'/comments', 'POST', {'body': body})
        elif marker not in (issue.get('body') or ''):
            request(repo, '/issues/'+str(issue['number']), 'PATCH', {'body': body})
            request(repo, '/issues/'+str(issue['number'])+'/comments', 'POST', {'body': body})
        print('alert active; unchanged state produces no repeat comments')
    elif issue and issue['state'] == 'open' and report.get('healthy_runs', 0) >= 2:
        request(repo, '/issues/'+str(issue['number'])+'/comments', 'POST',
                {'body': '云端重点频道连续两轮恢复解码，清单刷新正常，关闭告警。电视实播仍需单独验收。\n\n[日志]('+run+')'})
        request(repo, '/issues/'+str(issue['number']), 'PATCH', {'state': 'closed'})
        print('alert recovered')
    else:
        print('no actionable change; no notification')


if __name__ == '__main__':
    main()
