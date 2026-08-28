"""로그인 · 로그아웃 · 로그인 상태 확인"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from app.core.config import Settings, get_settings
from app.core import security

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginBody(BaseModel):
    password: str = Field(default="")
    remember: bool = False


class SessionInfo(BaseModel):
    authenticated: bool
    # .env 에 비밀번호를 설정하지 않고 기본값으로 돌고 있는지 —
    # 화면 위에 눈에 띄게 알려 주려고 함께 내려보냅니다.
    using_default_password: bool = False


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.get("/session", response_model=SessionInfo)
def read_session(
    request: Request, settings: Settings = Depends(get_settings)
) -> SessionInfo:
    ok = security.has_valid_session(request, settings)
    return SessionInfo(
        authenticated=ok,
        using_default_password=ok and settings.using_dev_password,
    )


@router.post("/login", response_model=SessionInfo)
def login(
    body: LoginBody,
    request: Request,
    response: Response,
    settings: Settings = Depends(get_settings),
) -> SessionInfo:
    ip = _client_ip(request)

    wait = security.throttle.check(ip)
    if wait:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"비밀번호를 여러 번 틀렸습니다. {wait}초 뒤에 다시 시도해 주세요.",
        )

    if not security.verify_password(body.password, settings):
        security.throttle.fail(ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="비밀번호가 맞지 않습니다.",
        )

    security.throttle.succeed(ip)
    security.issue_session(response, settings, remember=body.remember)
    return SessionInfo(authenticated=True, using_default_password=settings.using_dev_password)


@router.post("/logout", response_model=SessionInfo)
def logout(response: Response) -> SessionInfo:
    security.clear_session(response)
    return SessionInfo(authenticated=False)
