"""
NTIS 통합공고 RSS 가 실제로 어떤 필드를 주는지 확인합니다.

    .venv/bin/python scripts/probe/ntis.py

XSL 샘플(unRndRss.xsl)에는 author/title/link/pubDate 만 쓰여 있고
마감일·공고금액에 해당하는 태그가 없습니다. 실제로 있는지 없는지는
원문을 받아 봐야 알 수 있어서 이 스크립트로 먼저 확인합니다.
"""
from __future__ import annotations

import sys
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.collector.fetch import HEADERS, decode  # noqa: E402
from app.core.http import ssl_context            # noqa: E402

BASE = "http://www.ntis.go.kr/rndgate/unRndRss.xml"
OUT = ROOT / "docs" / "ntis"

TRIES = [
    ("옵션 없음", BASE),
    ("prt=5 (개수)", f"{BASE}?prt=5"),
    ("prt=5&bbs=true (본문 포함)", f"{BASE}?prt=5&bbs=true"),
    ("prt=100&bbs=true", f"{BASE}?prt=100&bbs=true"),
]


def get(url: str, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout, context=ssl_context()) as res:
        return res.read()


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    ok_url, ok_raw = None, None

    for label, url in TRIES:
        print(f"\n▶ {label}\n  {url}")
        try:
            raw = get(url)
        except Exception as e:  # noqa: BLE001
            print(f"  실패: {type(e).__name__}: {e}")
            continue
        text = decode(raw)
        print(f"  받음: {len(raw):,} 바이트")
        try:
            root = ET.fromstring(text.encode("utf-8"))
        except ET.ParseError as e:
            print(f"  XML 파싱 실패: {e}")
            print(f"  앞부분: {text[:200]!r}")
            continue
        items = [n for n in root.iter() if n.tag.lower().endswith("item")]
        print(f"  item {len(items)}개")
        if items and ok_url is None:
            ok_url, ok_raw = url, text

    if ok_raw is None:
        print("\n어떤 주소로도 공고를 받지 못했습니다.")
        return 1

    # 원문을 파일로 남깁니다 — 나중에 매핑을 고칠 때 근거가 됩니다
    path = OUT / "unRndRss-원문.xml"
    path.write_text(ok_raw, encoding="utf-8")
    print(f"\n원문 저장: {path.relative_to(ROOT)}")

    root = ET.fromstring(ok_raw.encode("utf-8"))
    items = [n for n in root.iter() if n.tag.lower().endswith("item")]

    print("\n" + "=" * 62)
    print(f" item 안에 실제로 있는 태그 ({len(items)}건 기준)")
    print("=" * 62)
    tags = Counter()
    samples: dict[str, str] = {}
    for it in items:
        for c in it:
            tags[c.tag] += 1
            v = (c.text or "").strip()
            if v and c.tag not in samples:
                samples[c.tag] = v[:160].replace("\n", " ")
    for tag, n in tags.most_common():
        print(f"\n  <{tag}>  ({n}/{len(items)}건)")
        print(f"    예: {samples.get(tag, '(빈 값)')}")

    print("\n" + "=" * 62)
    print(" 첫 번째 공고 전체")
    print("=" * 62)
    print(ET.tostring(items[0], encoding="unicode")[:2500])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
