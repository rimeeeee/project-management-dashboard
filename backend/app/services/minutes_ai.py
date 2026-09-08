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

# 두 곳(초안 만들기·요청 사항만 다시 쓰기)에서 같은 규칙을 써야 해서 따로 둡니다.
_공통 = """당신은 공공사업 회의록을 정리하는 실무자입니다.
사업비 지출 증빙에 쓰는 문서이므로 담백하게 씁니다.

공통 규칙
- 각 줄은 명사형으로 끝냅니다. (예: "일정 확정", "역할 분담 논의")
  "~했다", "~합니다" 같은 서술형으로 끝내지 마세요.
- 한 줄은 15자에서 40자 사이로 씁니다.
- "회의를 진행함", "의견을 나눔" 같은 빈 말은 쓰지 마세요."""

지침 = _공통 + """

'회의내용' 과 '요청 및 예정 사항' 을 함께 작성하세요.

회의내용
- 6개에서 8개 사이로 씁니다.
- 회의에서 실제로 오갈 만한 구체적인 내용을 씁니다.
- 메모에 있는 낱말은 반드시 녹여서 씁니다.

요청 및 예정 사항
- 2개에서 4개 사이로 씁니다.
- 회의내용에서 이어지는 '앞으로 할 일' 만 씁니다.
  이미 끝난 일을 다시 적지 마세요.
- 누가·언제까지가 드러나면 함께 적습니다. (예: "협조 공문 발송 (~9월 말)")

결과는 아래 JSON 형식으로만 답하세요. 다른 말을 붙이지 마세요.
{"bullets": ["...", "..."], "nextSteps": ["...", "..."]}"""

# 회의내용을 사람이 고친 뒤 요청 사항만 다시 뽑을 때 씁니다.
지침_예정 = _공통 + """

주어진 '회의내용' 을 바탕으로 '요청 및 예정 사항' 만 작성하세요.

- 2개에서 4개 사이로 씁니다.
- 회의내용에서 이어지는 '앞으로 할 일' 만 씁니다.
  회의내용에 이미 적힌 문장을 그대로 옮기지 마세요.
- 누가·언제까지가 드러나면 함께 적습니다. (예: "협조 공문 발송 (~9월 말)")

결과는 아래 JSON 형식으로만 답하세요. 다른 말을 붙이지 마세요.
{"nextSteps": ["...", "..."]}"""


def enabled() -> bool:
    return bool((get_settings().gemini_api_key or "").strip())


def _key() -> str:
    key = (get_settings().gemini_api_key or "").strip()
    if not key:
        raise AIUnavailable("AI 키가 설정되지 않았습니다.")
    return key


def _lines(raw, 최대: int) -> list[str]:
    """AI 가 준 줄을 다듬습니다. 빈 줄·겹치는 줄·글머리 기호를 걷어냅니다."""
    out: list[str] = []
    for b in raw or []:
        b = " ".join(str(b).split()).strip().lstrip("-•· ")
        if b and b not in out:
            out.append(b[:80])
    return out[:최대]


def _json_of(data: dict) -> dict:
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(text)
    except (KeyError, IndexError, ValueError) as e:
        raise AIUnavailable("AI 응답을 알아볼 수 없습니다.") from e


def draft(title: str, memo: str = "", place: str = "") -> dict[str, list[str]]:
    """
    회의내용과 요청 및 예정 사항을 한 번에 받습니다.

    따로 두 번 묻지 않는 이유는, 요청 사항이 회의내용에서 이어져야 하는데
    따로 물으면 서로 아귀가 맞지 않는 글이 나오기 때문입니다.
    """
    묻기 = f"회의명: {title}\n"
    if place:
        묻기 += f"장소: {place}\n"
    if memo.strip():
        묻기 += f"추가 메모(반드시 반영): {memo.strip()}\n"

    got = _json_of(_ask(_key(), {
        "systemInstruction": {"parts": [{"text": 지침}]},
        "contents": [{"role": "user", "parts": [{"text": 묻기}]}],
        "generationConfig": {"temperature": 0.7, "responseMimeType": "application/json"},
    }))

    bullets = _lines(got.get("bullets"), 8)
    if not bullets:
        raise AIUnavailable("AI 가 내용을 만들지 못했습니다.")
    return {"bullets": bullets, "nextSteps": _lines(got.get("nextSteps"), 4)}


def draft_next_steps(title: str, bullets: list[str], memo: str = "") -> list[str]:
    """
    이미 적힌 회의내용만 보고 요청 및 예정 사항을 씁니다.

    회의내용을 사람이 손본 뒤에 쓰라고 따로 둡니다. 고친 내용이 아니라
    처음 만든 내용을 바탕으로 할 일이 나오면 앞뒤가 맞지 않습니다.
    """
    줄 = [str(b).strip() for b in (bullets or []) if str(b).strip()]
    if not 줄:
        raise AIUnavailable("회의내용을 먼저 채워 주세요.")

    묻기 = f"회의명: {title}\n회의내용:\n" + "\n".join(f"- {b}" for b in 줄)
    if memo.strip():
        묻기 += f"\n추가 메모: {memo.strip()}"

    got = _json_of(_ask(_key(), {
        "systemInstruction": {"parts": [{"text": 지침_예정}]},
        "contents": [{"role": "user", "parts": [{"text": 묻기}]}],
        "generationConfig": {"temperature": 0.7, "responseMimeType": "application/json"},
    }))
    steps = _lines(got.get("nextSteps"), 4)
    if not steps:
        raise AIUnavailable("AI 가 요청 및 예정 사항을 만들지 못했습니다.")
    return steps


def title_suggestions(title: str) -> list[str]:
    """회의명 다듬기 — 화면에 칩으로 보여 주고 고르면 바뀝니다."""
    payload = {
        "systemInstruction": {"parts": [{"text":
            "공공사업 회의록의 회의명을 다듬습니다. 주어진 이름을 바탕으로 더 정확하고 "
            "격식 있는 회의명 4개를 제안하세요. 각 이름은 30자를 넘기지 마세요. "
            '결과는 {"titles": ["...", "..."]} 형식 JSON 으로만 답하세요.'}]},
        "contents": [{"role": "user", "parts": [{"text": f"회의명: {title}"}]}],
        "generationConfig": {"temperature": 0.8, "responseMimeType": "application/json"},
    }
    try:
        data = _ask(_key(), payload)
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
