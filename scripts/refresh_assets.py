#!/usr/bin/env python3
"""显式更新第三方依赖快照。下载不执行JAR；失败时不覆盖清单，旧文件可回退。"""
import hashlib
import io
import json
from pathlib import Path
import urllib.parse
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]

def sanitize(value):
    if isinstance(value,dict): return {k: ('' if k.lower() in ('cookie','token','authorization','password','appkey') else sanitize(v)) for k,v in value.items()}
    if isinstance(value,list): return [sanitize(v) for v in value]
    return value

def main():
    sources = json.loads((ROOT/'source/asset-sources.json').read_text())
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    assets = {}
    pending = []
    for logical,url in sources.items():
        u=urllib.parse.urlsplit(url)
        url=urllib.parse.urlunsplit((u.scheme,u.netloc,urllib.parse.quote(urllib.parse.unquote(u.path)),u.query,u.fragment))
        with opener.open(urllib.request.Request(url,headers={'User-Agent':'okhttp/3.15'}),timeout=20) as r:
            raw=r.read(30_000_001)
            if len(raw)>30_000_000: raise ValueError('资产超过30MB')
            final=r.geturl()
        if logical.endswith('.jar'):
            if not zipfile.is_zipfile(io.BytesIO(raw)): raise ValueError(logical+'不是JAR')
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                dex=b''.join(z.read(n) for n in z.namelist() if n.endswith('.dex'))
                required=['Bili'] if logical=='bili.jar' else ['Wogg','PanWebShare','Bili','Config','LocalFile']
                for cls in required:
                    if ('/spider/'+cls+';').encode() not in dex: raise ValueError('JAR缺失'+cls)
        else:
            value=sanitize(json.loads(raw))
            if not ('classes' in value or 'class' in value): raise ValueError('分类JSON结构改变')
            raw=(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode()
        sha=hashlib.sha256(raw).hexdigest();name=Path(logical).stem+'-'+sha[:16]+Path(logical).suffix
        pending.append((name,raw));assets[logical]={'file':name,'sha256':sha,'md5':hashlib.md5(raw).hexdigest(),'origin':sources[logical],'resolved_origin':final}
    for name,raw in pending:(ROOT/'assets'/name).write_bytes(raw)
    (ROOT/'source/asset-manifest.json').write_text(json.dumps(assets,ensure_ascii=False,indent=2)+'\n')
    print('依赖快照更新完成；需运行build.py、审查差异后再提交推送。第三方JAR升级仍需设备验收。')

if __name__=='__main__':main()
