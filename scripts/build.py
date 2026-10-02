#!/usr/bin/env python3
"""生成固定 GitHub/Pages 入口；所有辅助配置和 JAR 均在本仓库。"""
import base64
import copy
import hashlib
import json
from pathlib import Path
import urllib.parse
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RAW = 'https://raw.githubusercontent.com/larry-biu/tvbox-config/main'
PAGES = 'https://larry-biu.github.io/tvbox-config'

def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

def materialize(value, base, assets):
    if isinstance(value, dict): return {k: materialize(v, base, assets) for k, v in value.items()}
    if isinstance(value, list): return [materialize(v, base, assets) for v in value]
    if isinstance(value, str) and value.startswith('asset:'):
        record = assets[value[6:]]
        suffix = ';md5;' + record['md5'] if value.endswith('.jar') else ''
        return base + '/assets/' + record['file'] + suffix
    return value

def build():
    selection = json.loads((ROOT / 'source/selection.json').read_text())
    assets = json.loads((ROOT / 'source/asset-manifest.json').read_text())
    live = json.loads((ROOT / 'live/channels.json').read_text())
    for suffix, base in [('', RAW), ('-pages', PAGES)]:
        conf = materialize(copy.deepcopy(selection), base, assets)
        conf['spider'] = materialize('asset:luban.jar', base, assets)
        conf['lives'] = [{'name': '家庭直播', 'type': 0, 'url': base + '/live/live.txt'}]
        conf['rules'] = []
        write(ROOT / ('config' + suffix + '.json'), conf)
        write(ROOT / ('fongmi' + suffix + '.json'), conf)
        legacy = copy.deepcopy(conf)
        ext = base64.urlsafe_b64encode((base + '/live/live.txt').encode()).decode().rstrip('=')
        legacy['lives'] = [{'name': '家庭直播', 'group': '家庭直播', 'channels': [
            {'name': '家庭直播', 'urls': ['proxy://do=live&type=txt&ext=' + ext]}]}]
        write(ROOT / ('tvbox' + suffix + '.json'), legacy)
        write(ROOT / ('warehouse' + suffix + '.json'), {'urls': [
            {'name': 'Larry·影视仓', 'url': base + '/config' + suffix + '.json'},
            {'name': 'Larry·TVBox旧版', 'url': base + '/tvbox' + suffix + '.json'},
            {'name': 'Larry·FongMi', 'url': base + '/fongmi' + suffix + '.json'}]})
    manifest = {'schema': 1, 'site_count': len(selection['sites']),
                'channel_count': sum(len(g['channels']) for g in live),
                'groups': {g['group']: len(g['channels']) for g in live},
                'device_playback': '未验收', 'files': {}}
    for path in sorted(ROOT.glob('*.json')) + sorted((ROOT/'assets').glob('*')) + sorted((ROOT/'live').glob('*')):
        if path.name == 'manifest.json': continue
        if path.is_file(): manifest['files'][path.relative_to(ROOT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    write(ROOT / 'manifest.json', manifest)
    validate()
    print(json.dumps({k: v for k, v in manifest.items() if k != 'files'}, ensure_ascii=False))

def validate():
    manifest = json.loads((ROOT / 'manifest.json').read_text())
    for name, sha in manifest['files'].items():
        path = ROOT / name
        if not path.resolve().is_relative_to(ROOT.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest() != sha:
            raise ValueError('发布文件哈希错误：' + name)
    for name in ['config.json', 'config-pages.json', 'tvbox.json', 'tvbox-pages.json', 'fongmi.json', 'fongmi-pages.json']:
        data = json.loads((ROOT / name).read_text())
        keys = [s['key'] for s in data['sites']]
        if len(set(keys)) != len(keys) or not keys: raise ValueError('点播 key 不完整／重复')
        if data.get('parses') or data.get('flags'): raise ValueError('未采用第三方付费解析')
        def scan(x):
            if isinstance(x, dict):
                for k, v in x.items():
                    if k.lower() in ('cookie','token','authorization','password','appkey') and v:
                        raise ValueError('不允许发布共享凭证')
                    scan(v)
            elif isinstance(x, list):
                for v in x: scan(v)
            elif isinstance(x, str):
                if x.startswith('asset:') or any(t in x for t in ('192.168.', '127.0.0.1', 'localhost', 'mirror.ghproxy', 'github.moeyy')):
                    raise ValueError('仍含本机地址或旧镜像')
                if x.startswith(('https://raw.githubusercontent.com/larry-biu/tvbox-config/main/', 'https://larry-biu.github.io/tvbox-config/')):
                    url, *md5 = x.split(';md5;')
                    path = urllib.parse.urlsplit(url).path
                    prefix = '/larry-biu/tvbox-config/main/' if 'raw.githubusercontent.com' in url else '/tvbox-config/'
                    relative = path.removeprefix(prefix)
                    if not (ROOT / relative).is_file(): raise ValueError('自己的仓库资源缺失：' + relative)
                    if md5 and hashlib.md5((ROOT / relative).read_bytes()).hexdigest() != md5[0]: raise ValueError('JAR MD5不符')
        scan(data)
    assets = json.loads((ROOT/'source/asset-manifest.json').read_text())
    for logical, record in assets.items():
        path = ROOT / 'assets' / record['file']
        if logical.endswith('.jar'):
            if not zipfile.is_zipfile(path): raise ValueError('JAR不是ZIP')
        else:
            scan(json.loads(path.read_text()))
    groups = json.loads((ROOT/'live/channels.json').read_text())
    if sum(len(g['channels']) for g in groups) != manifest['channel_count']: raise ValueError('直播数量不符')
    for g in groups:
        for c in g['channels']:
            if not c['name'] or not c['urls']: raise ValueError('直播条目缺失')
            for url in c['urls']:
                url = url.split('$',1)[0].split('|',1)[0]
                if not url.startswith(('https://','http://')): raise ValueError('非公开HTTP直播地址')
                scan(url)

if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(); p.add_argument('--check', action='store_true'); a = p.parse_args()
    validate() if a.check else build()
