#!/usr/bin/env python3
"""GitHub云端维护：更新允许的上游、核验、发布候选；失败保留旧配置。"""
import argparse
import concurrent.futures
import copy
import datetime as dt
import hashlib
import importlib.util
import io
import ipaddress
import json
from pathlib import Path
import re
import shutil
import socket
import tempfile
import time
import urllib.parse
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SECRET_KEYS = {'cookie', 'token', 'authorization', 'password', 'appkey', 'access_token', 'refresh_token'}


def now(): return dt.datetime.now(dt.timezone.utc).isoformat()
def dump(path, data): path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def jsonc(data):
    text = data.decode('utf-8-sig') if isinstance(data, bytes) else data
    token = re.compile(r'("(?:\\.|[^"\\])*")|(/\*.*?\*/|//[^\r\n]*)', re.S)
    text = token.sub(lambda m: m.group(1) or '', text)
    text = re.sub(r'("(?:\\.|[^"\\])*")|(,)(\s*[}\]])', lambda m: m.group(1) if m.group(1) else m.group(3), text)
    return json.loads(text)


def sanitize(value):
    if isinstance(value, dict): return {k: ('' if k.lower() in SECRET_KEYS else sanitize(v)) for k, v in value.items()}
    if isinstance(value, list): return [sanitize(v) for v in value]
    return value


def has_secret(value):
    if isinstance(value, dict): return any((k.lower() in SECRET_KEYS and bool(v)) or has_secret(v) for k, v in value.items())
    if isinstance(value, list): return any(has_secret(v) for v in value)
    return False


def public_url(url):
    parts = urllib.parse.urlsplit(url)
    if parts.scheme not in ('http', 'https') or not parts.hostname or parts.username or parts.password:
        raise ValueError('只接受无凭证的公开HTTP地址')
    host = parts.hostname.encode('idna').decode()
    if host in ('localhost',) or host.endswith(('.local', '.localhost')): raise ValueError('拒绝本地地址')
    try:
        if not ipaddress.ip_address(host).is_global: raise ValueError('拒绝非公网IP')
    except ValueError as e:
        if str(e) == '拒绝非公网IP': raise
    netloc = ('[' + host + ']' if ':' in host else host) + (':' + str(parts.port) if parts.port else '')
    return urllib.parse.urlunsplit((parts.scheme, netloc, urllib.parse.quote(urllib.parse.unquote(parts.path)), parts.query, ''))


class PublicRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return super().redirect_request(req, fp, code, msg, headers, public_url(newurl))


class Network:
    def __init__(self, timeout=15, attempts=2):
        self.timeout = timeout; self.attempts = attempts
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), PublicRedirect())
    def get(self, url, limit=30_000_000, attempts=None, timeout=None):
        url = public_url(url)
        last = None
        for attempt in range(attempts or self.attempts):
            try:
                with self.opener.open(urllib.request.Request(url, headers={'User-Agent': 'okhttp/3.15'}), timeout=timeout or self.timeout) as response:
                    final = public_url(response.geturl()); raw = response.read(limit + 1)
                    if len(raw) > limit: raise ValueError('响应超出大小限制')
                    return raw, final
            except Exception as error:
                last = error
                if attempt + 1 < (attempts or self.attempts): time.sleep(0.5)
        raise ValueError(type(last).__name__ + ': ' + str(last)[:180])
    def sample(self, url):
        url = public_url(url)
        with self.opener.open(urllib.request.Request(url, headers={'User-Agent': 'okhttp/3.15', 'Range': 'bytes=0-4095', 'Icy-MetaData': '0'}), timeout=5) as r:
            public_url(r.geturl()); raw = r.read(4096)
            if not raw: raise ValueError('空响应')
            if raw.lstrip().lower().startswith((b'<html', b'<!doctype html')): raise ValueError('响应为HTML')
            return {'http_status': r.status, 'sample_bytes': len(raw), 'media_decoded': False}


def load_upstream(network, policy):
    failures = []
    for url in policy['upstreams']:
        try:
            raw, origin = network.get(url, limit=4_000_000)
            data = jsonc(raw)
            if not isinstance(data, dict) or not isinstance(data.get('sites'), list) or not data.get('spider'):
                raise ValueError('不是单线路点播配置')
            keys = [s.get('key') for s in data['sites']]
            if len(keys) != len(set(keys)): raise ValueError('上游站点key重复')
            return data, origin, {'input': url, 'origin': origin, 'sha256': hashlib.sha256(raw).hexdigest(), 'failed_entrances': failures}
        except Exception as e: failures.append({'entrance': url, 'reason': str(e)[:200]})
    raise ValueError('全部上游入口读取失败：' + json.dumps(failures, ensure_ascii=False))


def asset_specs(selection, upstream, origin, old_sources, policy):
    chosen = copy.deepcopy(selection)
    sources = dict(old_sources)
    sources['luban.jar'] = urllib.parse.urljoin(origin, upstream['spider'])
    lookup = {s['key']: s for s in upstream['sites']}
    warnings = []
    for site in chosen['sites']:
        original_key = policy.get('core_site_keys', {}).get(site['key'], site['key'])
        source = lookup.get(original_key)
        if source is None:
            if site['type'] == 3: warnings.append({'site': site['key'], 'reason': '上游缺少该key，保留已有定义'})
            continue
        if has_secret(source):
            warnings.append({'site': site['key'], 'reason': '上游带共享凭证，保留已有定义'})
            continue
        if source.get('type') != site['type']: raise ValueError('上游站点类型改变：' + site['key'])
        if site['type'] == 1:
            site['api'] = public_url(urllib.parse.urljoin(origin, source['api']))
            continue
        if not str(source.get('api', '')).startswith('csp_'): raise ValueError('选定爬虫接口结构改变')
        site['api'] = source['api']
        if isinstance(site.get('ext'), str) and site['ext'].startswith('asset:'):
            value = source.get('ext')
            if not isinstance(value, str): raise ValueError('分类ext从字符串变为其他类型')
            sources[site['ext'][6:]] = urllib.parse.urljoin(origin, value)
        elif isinstance(site.get('ext'), dict) and str(site['ext'].get('json', '')).startswith('asset:'):
            value = source.get('ext')
            if not isinstance(value, dict) or not isinstance(value.get('json'), str): raise ValueError('分类ext.json结构改变')
            sources[site['ext']['json'][6:]] = urllib.parse.urljoin(origin, value['json'])
        else:
            site['ext'] = sanitize(copy.deepcopy(source.get('ext', '')))
            if isinstance(site['ext'], dict) and isinstance(site['ext'].get('site'), list):
                site['ext']['site'] = [public_url(u.strip()) for u in site['ext']['site']]
        # 保持原JAR归属；同一逻辑JAR若被上游拆分，拒绝不兼容的合并。
        logical = site.get('jar', 'asset:luban.jar')[6:]
        jar = source.get('jar', upstream['spider'])
        jar = urllib.parse.urljoin(origin, jar)
        if logical == 'luban.jar' and jar != sources['luban.jar']: raise ValueError('上游将主JAR站点拆成独立JAR，需修复适配')
        if logical == 'bili.jar':
            if 'bili.jar' in sources and sources['bili.jar'] != old_sources['bili.jar'] and sources['bili.jar'] != jar:
                raise ValueError('B站分组JAR来源不一致')
            sources['bili.jar'] = jar
    return chosen, sources, warnings


def fetch_assets(network, sources, selection):
    payloads = {}; manifest = {}
    for logical, spec in sources.items():
        parts = spec.split(';md5;', 1); raw, final = network.get(parts[0])
        if len(parts) == 2 and hashlib.md5(raw).hexdigest() != parts[1]: raise ValueError('上游JAR声明MD5不符：' + logical)
        if logical.endswith('.jar'):
            if not zipfile.is_zipfile(io.BytesIO(raw)): raise ValueError('不是JAR：' + logical)
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                if sum(n.file_size for n in z.infolist()) > 100_000_000: raise ValueError('JAR解压超出限制')
                dex = b''.join(z.read(n) for n in z.namelist() if n.endswith('.dex'))
                for s in selection['sites']:
                    if s['type'] != 3 or s.get('jar', 'asset:luban.jar') != 'asset:' + logical: continue
                    cls = s['api'][4:]
                    if ('/spider/' + cls + ';').encode() not in dex: raise ValueError('JAR缺少所选爬虫类：' + cls)
        else:
            data = sanitize(jsonc(raw))
            if not isinstance(data, dict) or not ('classes' in data or 'class' in data): raise ValueError('分类JSON结构改变：' + logical)
            raw = (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode()
        sha = hashlib.sha256(raw).hexdigest()
        filename = Path(logical).stem + '-' + sha[:16] + Path(logical).suffix
        payloads[filename] = raw
        manifest[logical] = {'file': filename, 'sha256': sha, 'md5': hashlib.md5(raw).hexdigest(), 'origin': spec, 'resolved_origin': final}
    return payloads, manifest


def check_catalogs(network, selection, policy):
    rows = []
    for s in selection['sites']:
        if s['type'] != 1: continue
        row = {'key': s['key'], 'healthy': False}
        try:
            base = s['api']
            def api(query):
                url = base + ('&' if '?' in base else '?') + urllib.parse.urlencode(query)
                raw, final = network.get(url, limit=2_000_000)
                d = json.loads(raw)
                if not isinstance(d, dict) or not d.get('list'): raise ValueError('资源API未返回列表')
                return d, {'response_sha256': hashlib.sha256(raw).hexdigest(), 'result_count': len(d['list'])}
            category, ce = api({'ac': 'list', 't': '13'})
            search, se = api({'ac': 'list', 'wd': policy['search_sample']})
            detail, de = api({'ac': 'videolist', 'ids': search['list'][0]['vod_id']})
            if not detail['list'][0].get('vod_play_url'): raise ValueError('详情无剧集地址')
            row.update(healthy=True, category=ce, search=se, detail=de, media_playback=False)
        except Exception as e: row['reason'] = str(e)[:200]
        rows.append(row)
    if sum(r['healthy'] for r in rows) < policy['minimum_healthy_catalogs']:
        raise ValueError('当前运行网络下全部主资源API不可读，保留旧配置')
    return rows


def audit_live(network, root):
    groups = json.loads((root / 'live/channels.json').read_text())
    urls = list(dict.fromkeys(u.split('$', 1)[0].split('|', 1)[0] for g in groups for c in g['channels'] for u in c['urls']))
    def check(url):
        row = {'url_sha256': hashlib.sha256(url.encode()).hexdigest()}
        try: row.update(network.sample(url), accessible=True)
        except Exception as e: row.update(accessible=False, reason=type(e).__name__)
        return row
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool: rows = list(pool.map(check, urls))
    return {'scope': '任务运行网络，仅清单/小段HTTP读取，不是家庭联通或实播证明',
            'checked_endpoints': len(rows), 'accessible': sum(r['accessible'] for r in rows),
            'channel_count': sum(len(g['channels']) for g in groups), 'removed_channels': 0,
            'policy': '地区限制或外网不可达不自动删节目；地址仍由原权威维护流程提供', 'results': rows}


def builder(root):
    spec = importlib.util.spec_from_file_location('candidate_builder', root / 'scripts/build.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    module.build()


def execute(root=ROOT, network=None, fail_for_test=False, check_live=True):
    started = now(); policy = json.loads((root / 'source/maintenance-policy.json').read_text())
    network = network or Network(policy['request_timeout_seconds'], policy['request_attempts'])
    before = hashlib.sha256((root/'config-pages.json').read_bytes()).hexdigest()
    status = {'schema': 1, 'checked_at': started, 'scope': '配置自动维护，不代表电视实播',
              'schedule_hours': policy['schedule_hours'], 'configuration_changed': False,
              'last_good_config_sha256': before, 'device_playback': '未验收'}
    try:
        if fail_for_test: raise ValueError('测试模拟上游失效')
        upstream, origin, evidence = load_upstream(network, policy)
        selection = json.loads((root/'source/selection.json').read_text())
        sources = json.loads((root/'source/asset-sources.json').read_text())
        selection, sources, warnings = asset_specs(selection, upstream, origin, sources, policy)
        payloads, assets = fetch_assets(network, sources, selection)
        catalogs = check_catalogs(network, selection, policy)
        # 可用资源API置前，故障源留作候选，不删除其配置；至少一个主资源API通过才发布。
        healthy = {r['key'] for r in catalogs if r['healthy']}
        selection['sites'] = sorted(selection['sites'], key=lambda s: 0 if s['key'] in healthy else (1 if s['type'] == 1 else 2))
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory)/'candidate'
            shutil.copytree(root, candidate, ignore=shutil.ignore_patterns('.git', '__pycache__'))
            dump(candidate/'source/selection.json', selection)
            dump(candidate/'source/asset-sources.json', sources)
            dump(candidate/'source/asset-manifest.json', assets)
            for name, raw in payloads.items(): (candidate/'assets'/name).write_bytes(raw)
            builder(candidate)
            after = hashlib.sha256((candidate/'config-pages.json').read_bytes()).hexdigest()
            # 校验完毕才将候选带回checkout；Git推送才是远端事务提交边界。
            for folder in ['source', 'assets']:
                for p in (candidate/folder).iterdir():
                    if p.is_file(): shutil.copy2(p, root/folder/p.name)
            for p in candidate.glob('*.json'): shutil.copy2(p, root/p.name)
        status.update(state='healthy' if all(r['healthy'] for r in catalogs) and not warnings else 'degraded',
                      configuration_changed=before != after, last_good_config_sha256=after,
                      last_success_at=now(), upstream=evidence, catalogs=catalogs, warnings=warnings,
                      dependencies=len(assets), jar_execution='仅ZIP/DEX类与校验值检查；未执行第三方JAR')
    except Exception as e:
        status.update(state='retained', reason=str(e)[:1200])
        previous_path = root/'health.json'
        if previous_path.exists():
            previous = json.loads(previous_path.read_text()); status['last_success_at'] = previous.get('last_success_at')
        if hashlib.sha256((root/'config-pages.json').read_bytes()).hexdigest() != before:
            raise RuntimeError('失败保留不变量被破坏') from e
    if check_live:
        try: status['live_audit'] = audit_live(network, root)
        except Exception as e: status['live_audit'] = {'state': 'unavailable', 'reason': str(e)[:200]}
    dump(root/'health.json', status)
    builder(root)
    print(json.dumps({'state': status['state'], 'configuration_changed': status['configuration_changed'], 'reason': status.get('reason')}, ensure_ascii=False))
    return status


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--simulate-upstream-failure', action='store_true'); p.add_argument('--skip-live-audit', action='store_true')
    a = p.parse_args(); execute(fail_for_test=a.simulate_upstream_failure, check_live=not a.skip_live_audit)
