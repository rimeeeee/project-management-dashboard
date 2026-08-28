"""
바깥 서버에 요청할 때 쓰는 공통 설정.

macOS 에 python.org 배포판을 설치하면 시스템 인증서를 못 찾아
  [SSL: CERTIFICATE_VERIFY_FAILED]
가 납니다. 공고 수집이 통째로 실패하는 원인이 되므로, 파이썬 패키지로 함께
설치되는 인증서 목록(certifi)을 쓰도록 한 곳에서 정해 둡니다.

운영 서버(리눅스/도커)에서는 시스템 인증서가 정상이라 어느 쪽이든 동작합니다.
"""
from __future__ import annotations

import ssl

try:
    import certifi

    _CA_FILE: str | None = certifi.where()
except ImportError:      # certifi 가 없으면 시스템 인증서를 씁니다
    _CA_FILE = None


def ssl_context() -> ssl.SSLContext:
    return ssl.create_default_context(cafile=_CA_FILE)
