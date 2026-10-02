import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('maintenance', Path(__file__).with_name('maintenance.py'))
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


class FakeNetwork:
    def __init__(self, root):
        selection = json.loads((root/'source/selection.json').read_text())
        assets = json.loads((root/'source/asset-manifest.json').read_text())
        self.responses = {}
        self.upstream = {'spider': 'https://upstream.example/luban.jar', 'sites': []}
        reverse = {'非凡影视': 'feifan', '如意影视': 'ruyi'}
        for name, asset in assets.items(): self.responses['https://upstream.example/'+name] = (root/'assets'/asset['file']).read_bytes()
        def replace(x):
            if isinstance(x, str) and x.startswith('asset:'): return 'https://upstream.example/'+x[6:]
            if isinstance(x,dict): return {k:replace(v) for k,v in x.items()}
            if isinstance(x,list): return [replace(v) for v in x]
            return x
        for site in selection['sites']:
            site=replace(copy.deepcopy(site)); site['key']=reverse.get(site['key'],site['key'])
            self.upstream['sites'].append(site)
        self.mode=None
    def get(self, url, **kwargs):
        if url in self.responses:
            if self.mode=='badjar' and url.endswith('luban.jar'): return b'<html>expired</html>',url
            return self.responses[url], url
        if '/provide/vod' in url:
            if self.mode=='catalogs_down': raise ValueError('fixture API unavailable')
            return json.dumps({'list':[{'vod_id': 'fixture-1', 'vod_play_url': 'fixture$https://example.org/not-played.m3u8'}]}).encode(),url
        return json.dumps(self.upstream).encode(), 'https://upstream.example/config.json'
    def sample(self,url): return {'sample_bytes':32,'http_status':200,'media_decoded':False}


class MaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)/'repo'
        shutil.copytree(m.ROOT,self.root,ignore=shutil.ignore_patterns('.git','__pycache__'))
        self.network=FakeNetwork(self.root)
    def tearDown(self): self.temp.cleanup()
    def hash(self):return hashlib.sha256((self.root/'config-pages.json').read_bytes()).hexdigest()
    def test_jsonc_keeps_url_and_commented_example_strings(self):
        self.assertEqual(m.jsonc('{/*注释*/"url":"https://a.test/x//y",//注释\n"s":"a,}",}'),{'url':'https://a.test/x//y','s':'a,}'})
    def test_reject_local_addresses_and_embedded_credentials(self):
        for url in ['file:///tmp/a','http://127.0.0.1/a','http://192.168.1.1/a','http://localhost/a','https://name:secret@example.com/a']:
            with self.assertRaises(ValueError):m.public_url(url)
        self.assertIn('xn--',m.public_url('http://www.影视仓.com'))
    def test_refresh_preserves_names_categories_and_ext_shape(self):
        upstream,origin,_=m.load_upstream(self.network,json.loads((self.root/'source/maintenance-policy.json').read_text()))
        chosen=json.loads((self.root/'source/selection.json').read_text());old=json.loads((self.root/'source/asset-sources.json').read_text())
        selected,sources,warnings=m.asset_specs(chosen,upstream,origin,old,{'core_site_keys':{'非凡影视':'feifan','如意影视':'ruyi'}})
        self.assertEqual([(s['key'],s['name']) for s in selected['sites']],[(s['key'],s['name']) for s in chosen['sites']])
        self.assertEqual(selected['sites'][0]['categories'],chosen['sites'][0]['categories'])
        self.assertIsInstance(next(s for s in selected['sites'] if s['key']=='哔哩哔哩')['ext'],str)
    def test_shared_cookie_is_not_adopted(self):
        upstream,origin,_=m.load_upstream(self.network,json.loads((self.root/'source/maintenance-policy.json').read_text()))
        next(s for s in upstream['sites'] if s['key']=='玩偶哥哥')['ext']['cookie']='fixture-shared-secret'
        selected,_,warnings=m.asset_specs(json.loads((self.root/'source/selection.json').read_text()),upstream,origin,json.loads((self.root/'source/asset-sources.json').read_text()),{'core_site_keys':{}})
        self.assertFalse(m.has_secret(selected));self.assertTrue(warnings)
    def test_invalid_jar_retains_all_published_config_bytes(self):
        before={p.name:p.read_bytes() for p in self.root.glob('*config*.json')};self.network.mode='badjar'
        status=m.execute(self.root,self.network,check_live=False)
        self.assertEqual(status['state'],'retained');self.assertEqual(before,{p.name:p.read_bytes() for p in self.root.glob('*config*.json')})
    def test_all_catalogs_unavailable_retains_last_good(self):
        before=self.hash();self.network.mode='catalogs_down';status=m.execute(self.root,self.network,check_live=False)
        self.assertEqual(status['state'],'retained');self.assertEqual(before,self.hash())
    def test_successful_refresh_then_failed_run_retains_success_and_live(self):
        live=(self.root/'live/channels.json').read_bytes();status=m.execute(self.root,self.network,check_live=True)
        self.assertEqual(status['state'],'healthy');self.assertEqual(len(status['catalogs']),3)
        before=self.hash();success=status['last_success_at']
        failed=m.execute(self.root,self.network,fail_for_test=True,check_live=False)
        self.assertEqual(failed['state'],'retained');self.assertEqual(failed['last_success_at'],success);self.assertEqual(before,self.hash())
        self.assertEqual(live,(self.root/'live/channels.json').read_bytes())

if __name__=='__main__':unittest.main()
