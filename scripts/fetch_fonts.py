"""
IBM Plex Sans KR 글꼴을 저장소 안에 내려받습니다.

    .venv/bin/python scripts/fetch_fonts.py

프로토타입은 이 글꼴을 Google Fonts CDN 에서 받습니다. 병원 내부망에서 CDN 이
막히면 다른 글꼴로 떨어져 글자 굵기·자간이 전부 달라 보입니다.
글씨 크기는 50~60대가 보기 편하도록 맞춰 둔 것이라 이 부분이 어긋나면 안 됩니다.

한글은 글자가 많아 Google 이 유니코드 구간별로 잘게 나눠 보냅니다.
브라우저는 그중 실제로 쓰는 조각만 받으므로, 전부 받아 두어도 사용자가
내려받는 양은 늘지 않습니다.
"""
from __future__ import annotations

import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.http import ssl_context  # noqa: E402
FONT_DIR = ROOT / "frontend" / "public" / "fonts"
CSS_OUT = ROOT / "frontend" / "src" / "styles" / "fonts.css"

CSS_URL = (
    "https://fonts.googleapis.com/css2"
    "?family=IBM+Plex+Sans+KR:wght@400;500;600;700&display=swap"
)
# woff2 를 받으려면 최신 브라우저인 척해야 합니다.
# 옛 User-Agent 로 요청하면 용량이 훨씬 큰 ttf 를 내려줍니다.
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30, context=ssl_context()) as res:
        return res.read()


def main() -> int:
    FONT_DIR.mkdir(parents=True, exist_ok=True)
    print("Google Fonts 에서 글꼴 정의를 받습니다…")
    try:
        css = get(CSS_URL).decode("utf-8")
    except Exception as e:  # noqa: BLE001
        print(f"실패: {type(e).__name__}: {e}")
        print("인터넷에 나갈 수 없는 환경이면, 인터넷이 되는 PC 에서 이 스크립트를 돌린 뒤")
        print("frontend/public/fonts/ 와 frontend/src/styles/fonts.css 를 옮겨 주세요.")
        return 1

    urls = sorted(set(re.findall(r"url\((https://fonts\.gstatic\.com/[^)]+)\)", css)))
    print(f"글꼴 조각 {len(urls)}개를 받습니다…")

    total = 0
    for i, u in enumerate(urls, 1):
        name = u.rsplit("/", 1)[-1].split("?")[0]
        # 파일 이름이 겹치지 않도록 앞에 번호를 붙입니다
        fname = f"plex-kr-{i:03d}-{name}"
        path = FONT_DIR / fname
        if not path.exists():
            data = get(u)
            path.write_bytes(data)
            total += len(data)
        css = css.replace(u, f"/fonts/{fname}")
        if i % 40 == 0:
            print(f"  {i}/{len(urls)} …")

    header = (
        "/* IBM Plex Sans KR — Google Fonts 에서 받아 저장소에 담아 둔 것입니다.\n"
        "   병원 내부망에서 CDN 이 막혀도 프로토타입과 같은 글꼴로 보이게 하기 위해서입니다.\n"
        "   다시 받으려면: .venv/bin/python scripts/fetch_fonts.py\n"
        "   직접 고치지 마세요 — 스크립트가 덮어씁니다. */\n\n"
    )
    CSS_OUT.write_text(header + css, encoding="utf-8")

    print(f"완료: 조각 {len(urls)}개 · {total/1024/1024:.1f}MB")
    print(f"  글꼴  {FONT_DIR}")
    print(f"  정의  {CSS_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
