"""On-demand exhaustive audit with immutable input and reviewable frame evidence."""
import argparse
import concurrent.futures
import hashlib
import json
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from PIL import Image, ImageStat


def snapshot(root, ref):
    root.mkdir(parents=True, exist_ok=True)
    records = []
    hashes = {}
    for family in ('bestfan', 'guovin'):
        raw = subprocess.check_output(['git', 'show', ref+':live/'+family+'.txt'])
        (root/(family+'.txt')).write_bytes(raw)
        hashes[family] = hashlib.sha256(raw).hexdigest()
        group = ''
        for row in raw.decode().splitlines():
            if ',' not in row:
                continue
            name, routes = row.split(',', 1)
            if routes == '#genre#':
                group = name
                continue
            for ordinal, url in enumerate(routes.split('#'), 1):
                records.append({'family': family, 'channel': name, 'group': group,
                                'ordinal': ordinal, 'url': url,
                                'key': hashlib.sha256(url.encode()).hexdigest()[:20]})
    data = {'source_ref': ref, 'playlist_hashes': hashes, 'routes': records}
    (root/'input.json').write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')
    return data


def screen_flags(paths):
    blue, black = [], []
    for path in paths:
        with Image.open(path) as image:
            image = image.convert('RGB').resize((32, 18))
            pixels = list(image.getdata())
            means = ImageStat.Stat(image).mean
            r, g, b = means
            uniform = sum(abs(x-r)<16 and abs(y-g)<16 and abs(z-b)<16 for x, y, z in pixels)/len(pixels)
            blue.append(b>100 and b-r>70 and b-g>30 and uniform>=0.95)
            black.append(sum(max(p)<12 for p in pixels)/len(pixels)>=0.98)
    if len(paths)>=2 and all(blue):
        return 'uniform_blue_suspected'
    if len(paths)>=2 and all(black):
        return 'black_screen_suspected'
    return 'requires_visual_content_review'


def probe(record, phase, root):
    folder = root/phase/record['key']
    folder.mkdir(parents=True, exist_ok=True)
    target = record['url'].split('$', 1)[0]
    started = datetime.now(timezone.utc).isoformat()
    command = ['ffmpeg', '-nostdin', '-hide_banner', '-v', 'error', '-threads', '1',
               '-rw_timeout', '5000000', '-i', target, '-map', '0:v:0', '-an',
               '-vf', 'fps=1/3,scale=320:180', '-frames:v', '3', '-threads', '1',
               '-filter_threads', '1', '-y', str(folder/'frame-%02d.jpg')]
    error = None
    if urlsplit(target).scheme not in ('http', 'https'):
        error = 'unsupported_protocol'
    else:
        try:
            result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=20)
            if result.returncode:
                error = 'decoder_or_network_error'
        except subprocess.TimeoutExpired:
            error = 'timeout'
        except OSError:
            error = 'decoder_unavailable'
    frames = sorted(folder.glob('frame-*.jpg'))
    try:
        status = screen_flags(frames) if len(frames)>=2 else 'insufficient_video_samples'
    except (OSError, ValueError):
        status = 'invalid_image_samples'
    return {'key': record['key'], 'started_at': started, 'frame_count': len(frames),
            'frames': [str(f.relative_to(root)) for f in frames], 'error': error,
            'status': status, 'advertisement_review': 'not_automatically_verified'}


def phase(root, data, name, workers):
    rows = [r for r in data['routes'] if name == 'all_routes' or r['ordinal'] == 1]
    unique = {r['key']: r for r in rows}
    results = {}
    started = time.monotonic()
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(probe, row, name, root): key for key, row in unique.items()}
        for future in concurrent.futures.as_completed(futures):
            results[futures[future]] = future.result()
            if len(results)%20 == 0 or len(results) == len(unique):
                print(name, len(results), '/', len(unique), 'elapsed_seconds', int(time.monotonic()-started), flush=True)
    report = {'phase': name, 'source_ref': data['source_ref'], 'input_hashes': data['playlist_hashes'],
              'scope': 'GitHub runner; not television playback or guarantee against intermittent ads',
              'records': [dict(row, probe=results[row['key']]) for row in rows]}
    (root/(name+'.json')).write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(name, 'complete', len(rows), 'route records', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase', choices=['first_round1', 'first_round2', 'all_routes'], required=True)
    parser.add_argument('--source-ref', required=True)
    parser.add_argument('--root', default='route-audit')
    parser.add_argument('--workers', type=int, default=6)
    args = parser.parse_args()
    if not re.fullmatch(r'[0-9a-f]{40}', args.source_ref):
        raise ValueError('source-ref must be an immutable full commit hash')
    root = Path(args.root)
    data = json.loads((root/'input.json').read_text()) if (root/'input.json').exists() else snapshot(root, args.source_ref)
    assert data["source_ref"] == args.source_ref
    phase(root, data, args.phase, max(1, min(args.workers, 8)))
