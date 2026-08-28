"""
바깥 서버에서 문서를 받아옵니다.

공고수집 스크립트 v9 의 `받아오기` / `가져오기` 를 그대로 옮긴 것입니다.
한국보건복지인재원(kohi.or.kr) 서버가 응답을 끝까지 보내지 않고 끊는 일이
잦은데, 이 대응이 여기 들어 있습니다. **지우지 마세요.**

  1) 끝까지 받았으면 그대로 사용
  2) 끊겼으면 다시 받아 보고, 그중 '가장 많이 받은' 응답을 사용
  3) 끝까지 못 받았다는 사실을 함께 돌려줌
     (부르는 쪽에서 '이 쪽은 못 믿는다'고 판단할 수 있도록)
"""
from __future__ import annotations

import http.client
import logging
import re
import time
import urllib.request
import zlib

from app.core.http import ssl_context

log = logging.getLogger("bizdash.collector")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; SHR-BizDash-Collector/3.0)",
    "Accept-Language": "ko",
    # 압축을 쓰지 않습니다. 응답이 중간에 끊겼을 때 압축본은 뒷부분을 거의
    # 살릴 수 없지만, 압축하지 않은 본문은 받은 만큼 그대로 읽을 수 있습니다.
    "Accept-Encoding": "identity",
    "Connection": "close",
}

# 응답이 잘리는 것으로 이미 확인된 서버 (경고를 한 번만 남깁니다)
_truncating: set[str] = set()


def decode(raw: bytes) -> str:
    """받은 바이트를 문자열로 (utf-8 → euc-kr → cp949 순서로 해석)"""
    for enc in ("utf-8", "euc-kr", "cp949"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def decompress(raw: bytes, encoding: str | None) -> bytes:
    """gzip/deflate 응답을 풉니다. 중간에 끊긴 압축도 받은 만큼 풀어냅니다."""
    enc = (encoding or "").lower()
    if enc in ("gzip", "x-gzip"):
        d = zlib.decompressobj(16 + zlib.MAX_WBITS)
    elif enc == "deflate":
        d = zlib.decompressobj()
    else:
        return raw
    try:
        return d.decompress(raw)
    except zlib.error:
        return raw


def fetch(url: str, timeout: int = 25, retries: int = 3) -> tuple[str, bool]:
    """URL 의 본문을 (본문, 잘렸는지) 로 돌려줍니다."""
    host = re.sub(r"^https?://([^/]+).*$", r"\1", url)
    best, last_error = "", None

    for attempt in range(retries + 1):
        req = urllib.request.Request(url, headers=HEADERS)
        try:
            complete = True
            with urllib.request.urlopen(req, timeout=timeout, context=ssl_context()) as res:
                encoding = res.headers.get("Content-Encoding")
                try:
                    raw = res.read()
                except http.client.IncompleteRead as e:
                    raw, complete = e.partial, False
            body = decode(decompress(raw, encoding))
            if complete:
                return body, False
            if len(body) > len(best):
                best = body
        except http.client.IncompleteRead as e:
            body = decode(e.partial or b"")
            if len(body) > len(best):
                best = body
            last_error = e
        except Exception as e:  # noqa: BLE001 - 한 번 더 시도해 봅니다
            last_error = e
        if attempt < retries:
            time.sleep(1.0)

    if best:
        if host not in _truncating:      # 같은 서버 경고는 한 번만
            _truncating.add(host)
            log.warning("%s 서버가 응답을 끝까지 보내지 않습니다 (%d자 수신).", host, len(best))
        return best, True
    raise last_error if last_error else RuntimeError(f"{url} 을 읽지 못했습니다.")


def get(url: str, timeout: int = 25, retries: int = 3) -> str:
    """본문만 필요할 때 쓰는 간단한 형태 (RSS 등)."""
    return fetch(url, timeout, retries)[0]
