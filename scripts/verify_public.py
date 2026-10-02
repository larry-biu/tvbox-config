#!/usr/bin/env python3
"""实际匿名回读发布文件；不把Pages部署成功代替内容核验。"""
import argparse
import concurrent.futures
import datetime as dt
import hashlib
import json
from pathlib import Path
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[1]

def verify(base, attempts=6):
    expected=json.loads((ROOT/'manifest.json').read_text())['files']
    results=[]
    for attempt in range(attempts):
        def one(item):
            name,sha=item;row={'path':name}
            try:
                opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
                with opener.open(urllib.request.Request(base.rstrip('/')+'/'+name,headers={'User-Agent':'TVConfigReadback/1.0','Cache-Control':'no-cache'}),timeout=20) as r:
                    body=r.read(32_000_000);actual=hashlib.sha256(body).hexdigest();row.update(status=r.status,bytes=len(body),sha256=actual,matches_expected=actual==sha)
            except Exception as e:row['error']=str(e)[:200]
            return row
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:results=list(pool.map(one,expected.items()))
        good=all(r.get('matches_expected') for r in results)
        receipt={'checked_at':dt.datetime.now(dt.timezone.utc).isoformat(),'base':base,'anonymous':True,'all_match':good,'files':results}
        (ROOT/'public-readback.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
        if good:
            print('匿名公网回读通过：',len(results),'个文件');return receipt
        if attempt+1<attempts:time.sleep(10)
    raise RuntimeError('公网发布内容未匹配候选；失败项：'+str([r['path'] for r in results if not r.get('matches_expected')]))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--base',required=True);p.add_argument('--attempts',type=int,default=6);a=p.parse_args();verify(a.base,a.attempts)
