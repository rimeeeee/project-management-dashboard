"""
로그인 비밀번호를 정하고 .env 에 넣어 줍니다.

    .venv/bin/python scripts/set_password.py

비밀번호 자체는 저장하지 않고 해시만 남깁니다.
"""
from __future__ import annotations

import getpass
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.security import hash_password  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / ".env"


def main() -> int:
    pw = getpass.getpass("새 비밀번호: ")
    if not pw:
        print("비밀번호를 입력해 주세요.")
        return 1
    if len(pw) < 8:
        print("참고: 8자 미만이라 짐작하기 쉽습니다. 그대로 진행합니다.")
    if pw != getpass.getpass("한 번 더 입력: "):
        print("두 번 입력한 비밀번호가 다릅니다.")
        return 1

    digest = hash_password(pw)

    if not ENV.exists():
        example = ROOT / ".env.example"
        ENV.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
        print(".env 파일이 없어 .env.example 을 복사해 만들었습니다.")

    text = ENV.read_text(encoding="utf-8")
    line = f"APP_PASSWORD_HASH={digest}"
    if re.search(r"^APP_PASSWORD_HASH=.*$", text, flags=re.M):
        text = re.sub(r"^APP_PASSWORD_HASH=.*$", line, text, flags=re.M)
    else:
        text = text.rstrip("\n") + "\n" + line + "\n"
    ENV.write_text(text, encoding="utf-8")

    print("비밀번호를 저장했습니다. 서버를 다시 시작하면 적용됩니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
