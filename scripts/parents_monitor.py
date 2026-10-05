"""Bounded cloud video-decode checks; never equate runner reachability with TV UAT."""
import concurrent.futures
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def playlists(text):
    result = {}
    for line in text.splitlines():
        if ',' not in line:
            continue
        name, routes = line.split(',', 1)
        if routes == '#genre#':
            continue
        result.setdefault(name, []).extend(routes.split('#'))
    return result


def decode(url):
    # Real decoded video frames, not merely HTTP 200 or a playable-looking playlist.
    try:
        p = subprocess.run([
            'ffmpeg', '-nostdin', '-v', 'error', '-rw_timeout', '5000000',
            '-i', url.split('$', 1)[0], '-map', '0:v:0', '-an', '-t', '5',
            '-progress', 'pipe:1', '-nostats', '-f', 'null', '-'
        ], capture_output=True, text=True, timeout=15)
        frames = [int(x.split('=', 1)[1]) for x in p.stdout.splitlines()
                  if x.startswith('frame=') and x.split('=', 1)[1].strip().isdigit()]
        return max(frames, default=0) >= 25
    except (OSError, subprocess.TimeoutExpired):
        return False


def check_channel(name, sources, probe=decode):
    checks = []
    for family, channels in sources.items():
        good = False
        attempts = 0
        for url in channels.get(name, [])[:3]:
            attempts += 1
            if probe(url):
                good = True
                break
        checks.append({'source': family, 'decoded': good, 'attempts': attempts})
    return {'channel': name, 'decoded': any(x['decoded'] for x in checks), 'sources': checks}


def evaluate(previous, results, stale):
    failures = [x['channel'] for x in results if not x['decoded']]
    counts = {x['channel']: (previous.get('failures', {}).get(x['channel'], 0) + 1
                            if not x['decoded'] else 0) for x in results}
    reasons = ['频道连续两轮无法解码：' + name for name, count in counts.items() if count >= 2]
    reasons += ['清单更新超过18小时：' + name for name in stale]
    clean = not failures and not stale
    healthy_runs = previous.get('healthy_runs', 0) + 1 if clean else 0
    return {'failures': counts, 'healthy_runs': healthy_runs}, reasons


def main():
    config = json.loads((ROOT/'source/parents-monitor.json').read_text())
    now = datetime.now(timezone.utc)
    path = ROOT/'source/parents-monitor-state.json'
    previous = json.loads(path.read_text()) if path.exists() else {}
    sources = {name: playlists((ROOT/'live'/filename).read_text())
               for name, filename in config['playlists'].items()}
    stale = []
    receipts = {}
    for name, filename in config['receipts'].items():
        receipt = json.loads((ROOT/'source'/filename).read_text())
        stamp = datetime.fromisoformat(receipt['checked_at'])
        age = (now-stamp).total_seconds()/3600
        receipts[name] = {'last_refresh_at': stamp.isoformat(), 'age_hours': round(age, 2)}
        if age > 18:
            stale.append(name)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda name: check_channel(name, sources), config['channels']))
    state, reasons = evaluate(previous, results, stale)
    state['checked_at'] = now.isoformat()
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2)+'\n')
    report = {'schema': 1, 'checked_at': now.isoformat(), 'scope': 'GitHub runner video decode; not television playback',
              'channels': results, 'refresh': receipts, 'alert_reasons': reasons,
              'healthy_runs': state['healthy_runs'], 'tv_acceptance': 'separate'}
    (ROOT/'parents-health.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
