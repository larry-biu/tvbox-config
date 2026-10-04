#!/usr/bin/env python3
"""Convert the public best-fan GitHub playlist to TVBox TXT; retain on failure."""
import argparse
import hashlib
import json
import os
import re
import urllib.request
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path

UPSTREAM = "https://raw.githubusercontent.com/best-fan/iptv-sources/main/cn_all.m3u8"
ROOT = Path(__file__).resolve().parents[1]

def convert(body):
    groups = OrderedDict()
    name, group = "", "其他"
    for raw in body.splitlines():
        line = raw.strip()
        if line.startswith("#EXTINF:"):
            name = line.rsplit(",", 1)[-1].strip()
            match = re.search(r'group-title="([^"]*)"', line)
            group = match.group(1) if match else "其他"
            cctv = re.match(r"^CCTV[- _]?(\d+)(\+)?", name, re.I)
            if cctv:
                name = "CCTV" + cctv.group(1) + (cctv.group(2) or "")
                group = "央视"
            elif "卫视" in name:
                group = "卫视"
        elif line.startswith(("http://", "https://")) and name:
            channels = groups.setdefault(group, OrderedDict())
            routes = channels.setdefault(name, [])
            if line not in routes:
                routes.append(line)
            name = ""
    count = sum(len(channels) for channels in groups.values())
    if count < 20 or "CCTV1" not in groups.get("央视", {}):
        raise ValueError("upstream missing required channels")
    lines = []
    for group, channels in groups.items():
        lines.append(group + ",#genre#")
        for name, routes in channels.items():
            lines.append(name + "," + "#".join(routes))
    return "\n".join(lines) + "\n", count

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path)
    args = parser.parse_args()
    output = ROOT / "live/bestfan.txt"
    try:
        body = args.input.read_text() if args.input else urllib.request.urlopen(
            urllib.request.Request(UPSTREAM, headers={"User-Agent": "Larry-TVConfig/1.0"}), timeout=25
        ).read(4 * 1024 * 1024).decode("utf-8-sig")
        converted, count = convert(body)
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_suffix(".tmp")
        temporary.write_text(converted, encoding="utf-8")
        os.replace(temporary, output)
        receipt = {"upstream": UPSTREAM, "checked_at": datetime.now(timezone.utc).isoformat(),
                   "channels": count, "sha256": hashlib.sha256(converted.encode()).hexdigest()}
        (ROOT / "source/bestfan-live-receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
        print("bestfan TXT refreshed:", count, "channels")
    except Exception as error:
        if not output.exists():
            raise
        print("bestfan update failed; previous TXT retained:", type(error).__name__)

if __name__ == "__main__":
    main()
