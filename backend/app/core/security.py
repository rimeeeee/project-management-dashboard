"""
로그인 — 비밀번호 한 개로 들어가는 방식입니다.

담당자 계정을 따로 두지 않기로 했으므로, 이 파일이 하는 일은 두 가지뿐입니다.
  1) 입력한 비밀번호가 맞는지 확인 (해시 비교)
  2) 통과했다는 사실을 서명된 쿠키에 담아 두고, 이후 요청에서 확인

나중에 사내 계정(LDAP/SSO)을 붙이게 되면 이 파일만 갈아끼우면 되도록,
나머지 코드는 '세션이 있다/없다'만 보게 해 두었습니다.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError
from fastapi import Depends, HTTPException, Request, Response, status
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.core.config import DEV_PASSWORD, Settings, get_settings

COOKIE_NAME = "bizdash_session"
_SALT = "bizdash.session.v1"

_hasher = PasswordHasher()


def hash_password(raw: str) -> str:
    return _hasher.hash(raw)


def verify_password(raw: str, settings: Settings) -> bool:
    """비밀번호가 맞는지 확인합니다."""
    stored = settings.app_password_hash.strip()

    # .env 에 해시를 넣지 않은 상태 — 개발용 기본 비밀번호로 동작합니다.
    if not stored:
        return raw == DEV_PASSWORD

    try:
        return _hasher.verify(stored, raw)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


# ---------------------------------------------------------------------
# 무차별 대입 막기
#   비밀번호가 하나뿐이라 계정 잠금이라는 개념이 없습니다.
#   그래서 같은 IP 에서 연달아 틀리면 잠깐씩 쉬게 합니다.
# ---------------------------------------------------------------------
@dataclass
class _Attempts:
    fails: int = 0
    blocked_until: float = 0.0


@dataclass
class LoginThrottle:
    by_ip: dict[str, _Attempts] = field(default_factory=dict)
    max_fails: int = 5
    block_seconds: int = 60

    def check(self, ip: str) -> int:
        """막혀 있으면 남은 초를, 아니면 0 을 돌려줍니다."""
        rec = self.by_ip.get(ip)
        if not rec:
            return 0
        left = rec.blocked_until - time.monotonic()
        return int(left) + 1 if left > 0 else 0

    def fail(self, ip: str) -> None:
        rec = self.by_ip.setdefault(ip, _Attempts())
        rec.fails += 1
        if rec.fails >= self.max_fails:
            rec.blocked_until = time.monotonic() + self.block_seconds
            rec.fails = 0

    def succeed(self, ip: str) -> None:
        self.by_ip.pop(ip, None)


throttle = LoginThrottle()


# ---------------------------------------------------------------------
# 세션 쿠키
# ---------------------------------------------------------------------
def _serializer(settings: Settings) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.secret_key, salt=_SALT)


def issue_session(response: Response, settings: Settings, remember: bool) -> None:
    max_age = (
        settings.remember_days * 86400 if remember else settings.session_hours * 3600
    )
    token = _serializer(settings).dumps({"ok": True})
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=max_age,
        httponly=True,          # 자바스크립트가 읽지 못하게 합니다
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
    )


def clear_session(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/")


def has_valid_session(request: Request, settings: Settings) -> bool:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return False
    max_age = settings.remember_days * 86400
    try:
        _serializer(settings).loads(token, max_age=max_age)
        return True
    except (BadSignature, SignatureExpired):
        return False


def require_session(
    request: Request, settings: Settings = Depends(get_settings)
) -> None:
    """로그인이 필요한 API 앞에 붙입니다."""
    if not has_valid_session(request, settings):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="로그인이 필요합니다."
        )
