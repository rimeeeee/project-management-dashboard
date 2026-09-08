"""
회의록 초안 만들기 — Google Gemini.

회의명과 메모만 주면 회의내용 bullet 을 6~8줄 써 줍니다.
사람이 그대로 쓰는 것이 아니라, 고쳐 쓸 바탕을 마련하는 것입니다.

키(.env 의 GEMINI_API_KEY)가 없으면 이 기능만 꺼지고 회의록은 그대로 씁니다.
사내망에서 generativelanguage.googleapis.com 이 막혀 있어도 마찬가지입니다.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from app.core.config import get_settings

class AIUnavailable(RuntimeError):
    """키가 없거나 바깥에 나갈 수 없을 때."""


# 초안이라 빠르고 값싼 모델로 충분합니다.
#
# 앞의 것부터 쓰고, 그 모델이 닫혀 있으면(404) 다음 것으로 넘어갑니다.
# 예전에 gemini-2.5-flash 를 적어 두었더니 "신규 사용자에게는 더 이상
# 제공하지 않는다" 며 404 가 났습니다. 모델 이름은 이렇게 바뀌므로,
# 하나만 박아 두면 어느 날 갑자기 기능이 멈춥니다.
MODELS = ["gemini-3.6-flash", "gemini-flash-latest"]
URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"


def _ask(key: str, payload: dict) -> dict:
    """모델을 차례로 시도합니다. 404(닫힌 모델)면 다음 것으로 넘어갑니다."""
    마지막 = None
    for model in MODELS:
        req = urllib.request.Request(
            URL.format(model=model, key=key),
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:          # 이 모델만 닫힌 것이므로 다음을 봅니다
                마지막 = AIUnavailable(f"모델 {model} 을 쓸 수 없습니다.")
                continue
            raise AIUnavailable(f"AI 서버가 거절했습니다 (HTTP {e.code}).") from e
        except OSError as e:
            raise AIUnavailable("AI 서버에 닿지 못했습니다. 바깥 인터넷을 확인해 주세요.") from e
    raise 마지막 or AIUnavailable("쓸 수 있는 AI 모델이 없습니다.")

지침 = """당신은 공공사업 회의록을 정리하는 실무자입니다.
주어진 회의명과 메모로 '회의내용' bullet 을 작성하세요.

규칙
- 6개에서 8개 사이로 씁니다.
- 각 줄은 명사형으로 끝냅니다. (예: "일정 확정", "역할 분담 논의")
  "~했다", "~합니다" 같은 서술형으로 끝내지 마세요.
- 한 줄은 15자에서 40자 사이로 씁니다.
- 회의에서 실제로 오갈 만한 구체적인 내용을 씁니다.
  "회의를 진행함", "의견을 나눔" 같은 빈 말은 쓰지 마세요.
- 메모에 있는 낱말은 반드시 녹여서 씁니다.
- 사업비 지출 증빙에 쓰는 문서이므로 담백하게 씁니다.

결과는 아래 JSON 형식으로만 답하세요. 다른 말을 붙이지 마세요.
{"bullets": ["...", "...", "..."]}"""


def enabled() -> bool:
    return bool((get_settings().gemini_api_key or "").strip())


def draft_bullets(title: str, memo: str = "", place: str = "") -> list[str]:
    key = (get_settings().gemini_api_key or "").strip()
    if not key:
        raise AIUnavailable("AI 키가 설정되지 않았습니다.")

    묻기 = f"회의명: {title}\n"
    if place:
        묻기 += f"장소: {place}\n"
    if memo.strip():
        묻기 += f"추가 메모(반드시 반영): {memo.strip()}\n"

    payload = {
        "systemInstruction": {"parts": [{"text": 지침}]},
        "contents": [{"role": "user", "parts": [{"text": 묻기}]}],
        "generationConfig": {
            "temperature": 0.7,
            "responseMimeType": "application/json",
        },
    }
    data = _ask(key, payload)

    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        bullets = json.loads(text).get("bullets", [])
    except (KeyError, IndexError, ValueError) as e:
        raise AIUnavailable("AI 응답을 알아볼 수 없습니다.") from e

    # 빈 줄·너무 긴 줄을 걷어내고 8개로 자릅니다.
    out: list[str] = []
    for b in bullets:
        b = " ".join(str(b).split()).strip().lstrip("-•· ")
        if b and b not in out:
            out.append(b[:80])
    if not out:
        raise AIUnavailable("AI 가 내용을 만들지 못했습니다.")
    return out[:8]


def title_suggestions(title: str) -> list[str]:
    """회의명 다듬기 — 화면에 칩으로 보여 주고 고르면 바뀝니다."""
    key = (get_settings().gemini_api_key or "").strip()
    if not key:
        raise AIUnavailable("AI 키가 설정되지 않았습니다.")

    payload = {
        "systemInstruction": {"parts": [{"text":
            "공공사업 회의록의 회의명을 다듬습니다. 주어진 이름을 바탕으로 더 정확하고 "
            "격식 있는 회의명 4개를 제안하세요. 각 이름은 30자를 넘기지 마세요. "
            '결과는 {"titles": ["...", "..."]} 형식 JSON 으로만 답하세요.'}]},
        "contents": [{"role": "user", "parts": [{"text": f"회의명: {title}"}]}],
        "generationConfig": {"temperature": 0.8, "responseMimeType": "application/json"},
    }
    try:
        data = _ask(key, payload)
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        titles = json.loads(text).get("titles", [])
    except (KeyError, IndexError, ValueError) as e:
        raise AIUnavailable("회의명 제안을 받지 못했습니다.") from e

    out: list[str] = []
    for x in titles:
        x = " ".join(str(x).split()).strip()
        if x and x != title and x not in out:
            out.append(x[:40])
    return out[:4]
