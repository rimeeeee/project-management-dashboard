"""
화면 파일 서빙 — 폴더 밖 파일이 새어 나가지 않아야 합니다.

배포 직전 점검에서 실제로 뚫렸던 부분입니다.
  /..%2F..%2F.env  로 .env 파일이 로그인 없이 그대로 읽혔습니다.
  그 안에는 로그인 비밀번호 해시와 SECRET_KEY 가 들어 있습니다.
  (SECRET_KEY 가 새면 남의 로그인 쿠키를 만들어낼 수 있습니다)
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import ROOT
from app.main import DIST, app

pytestmark = pytest.mark.skipif(
    not DIST.is_dir(),
    reason="frontend/dist 가 없으면(빌드 전) 이 검사는 건너뜁니다",
)

# 폴더 밖으로 나가려는 여러 방식. %2F 는 / 를 인코딩한 것입니다.
ESCAPES = [
    "../.env",
    "../../.env",
    "..%2F..%2F.env",
    "%2e%2e%2f%2e%2e%2f.env",
    "assets/../../../.env",
    "../../backend/app/core/security.py",
    "..%2F..%2Fdata%2Fbizdash.db",
]


@pytest.fixture()
def anon():
    return TestClient(app)


@pytest.mark.parametrize("path", ESCAPES)
def test_폴더_밖_파일은_주지_않는다(anon, path):
    r = anon.get(f"/{path}")
    # 화면(index.html)을 돌려주거나 404 여야 합니다. 파일 내용이 나오면 안 됩니다.
    assert r.status_code in (200, 404)
    body = r.text[:400].lower()
    assert "secret_key" not in body
    assert "app_password_hash" not in body
    assert "argon2" not in body
    if r.status_code == 200:
        assert "<!doctype html" in body, f"{path} 가 화면이 아닌 무언가를 돌려줍니다"


def test_env_파일_내용이_어떤_방식으로도_나오지_않는다(anon):
    """실제 .env 에 있는 값이 응답에 섞여 나오는지 직접 대조합니다."""
    env = ROOT / ".env"
    if not env.is_file():
        pytest.skip(".env 가 없는 환경입니다")
    secret = ""
    for line in env.read_text(encoding="utf-8").splitlines():
        if line.startswith("SECRET_KEY="):
            secret = line.split("=", 1)[1].strip()
    if not secret:
        pytest.skip("SECRET_KEY 가 비어 있습니다")

    for path in ESCAPES:
        assert secret not in anon.get(f"/{path}").text, f"{path} 로 SECRET_KEY 가 샙니다"


def test_화면과_정적파일은_정상적으로_나온다(anon):
    assert "<!doctype html" in anon.get("/").text.lower()
    assert anon.get("/brand/logo.svg").status_code == 200
    # 화면에 없는 주소는 index.html 로 돌려줍니다 (프론트엔드가 처리)
    assert "<!doctype html" in anon.get("/아무주소").text.lower()
