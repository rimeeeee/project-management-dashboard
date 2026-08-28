"""
공고 목록에서 제목·게시일·마감일을 읽어냅니다.

공고수집 스크립트 v9 의 파싱 부분을 그대로 옮긴 것입니다.
실제 운영 데이터(약 57건)로 검증을 마친 로직이라 손대지 않습니다.
각 함수의 주석도 원문 그대로입니다 — 왜 그렇게 했는지가 적혀 있습니다.
"""
from __future__ import annotations

import datetime
import hashlib
import re
from html.parser import HTMLParser

from app.core.calc import today

DATE_RE = re.compile(r"(20\d{2})[.\-/년\s]*(\d{1,2})[.\-/월\s]*(\d{1,2})")


def datestr(d: datetime.date) -> str:
    return d.strftime("%Y-%m-%d")


def uid(*parts: object) -> str:
    h = hashlib.md5("|".join(str(x) for x in parts).encode("utf-8")).hexdigest()
    return "c" + h[:10]


def find_dates(text: str) -> list[str]:
    """글 안에 있는 날짜를 나온 순서대로 모두 돌려줍니다."""
    if not text:
        return []
    out = []
    for m in DATE_RE.finditer(str(text)):
        try:
            out.append(datestr(datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))))
        except ValueError:
            continue
    return out


def first_date(text: str) -> str:
    lst = find_dates(text)
    return lst[0] if lst else ""


def date_from_no(post_no: object) -> str:
    """
    글 번호가 'YYYYMMDDHHMMSS...' 형태면 그 앞 8자리가 곧 게시일입니다.
    (한국보건복지인재원이 이 방식이며, HTML 을 뒤지는 것보다 정확합니다.)
    글 번호가 단순 일련번호인 곳(진흥원 linkId 등)에서는 빈 값을 돌려줍니다.
    """
    no = str(post_no or "")
    if len(no) < 14 or not no.isdigit():
        return ""
    try:
        d = datetime.date(int(no[:4]), int(no[4:6]), int(no[6:8]))
    except ValueError:
        return ""
    if d.year < 2000 or d > today():
        return ""
    return datestr(d)


def find_posted(body: str, title: str, post_no: str) -> str:
    """
    이 글의 게시일을 찾습니다. 순서대로 시도합니다.

    1) 글 번호가 날짜 형태면 그대로 사용 (가장 정확)
    2) 목록 HTML 에서 제목을 찾아 그 주변의 날짜를 사용

    2)에서 주의할 점 두 가지
      - 제목 조각은 '길게' 잡아야 합니다. 앞부분이 같은 공고가 두 건 있으면
        (예: "…K-VIP… 통합 연장 공고" / "…K-VIP… 통합 공고")
        짧은 조각으로는 둘 다 첫 번째 글에 걸려 같은 날짜가 들어갑니다.
      - 제목 안에 든 행사 날짜(예: "개최(2026.9.11)")는 게시일이 아니므로 제외합니다.
        게시판 게시일은 미래일 수도 없으므로 오늘 이후 날짜도 제외합니다.
    """
    d = date_from_no(post_no)
    if d:
        return d

    base = today()
    in_title = set(find_dates(title))

    def pick(near: str) -> str:
        for x in find_dates(near):
            if x in in_title:
                continue
            if datetime.datetime.strptime(x, "%Y-%m-%d").date() <= base:
                return x
        return ""

    for length in (80, 60, 40, 20, 12):
        piece = (title or "")[:length]
        if not piece:
            continue
        at = body.find(piece)
        if at < 0:
            continue
        d = pick(body[at: at + 2000])
        if d:
            return d

    # 제목을 목록에서 못 찾는 경우(특수문자·줄바꿈 등)에는 글 번호를 기준으로 찾습니다
    if post_no:
        at = body.find(str(post_no))
        if at >= 0:
            return pick(body[at: at + 2000])
    return ""


def find_due(title: str, posted: str) -> tuple[str, str]:
    """
    제목에 적힌 마감 표기에서 날짜와 시각을 뽑습니다.
      "~8월 28일(금) 18:00까지" → ("2026-08-28", "18:00")
      "(~9/11)"                → ("2026-09-11", "")
      "(7.8(수), 18시까지)"     → ("2026-07-08", "18:00")
    찾지 못하면 ("", "") 을 돌려줍니다.
    """
    if not title:
        return "", ""
    # 1순위: '~' 뒤의 날짜   2순위: '까지' 앞의 날짜
    m = re.search(r"[~〜]\s*(\d{1,2})\s*(?:월|[./])\s*(\d{1,2})\s*일?\.?", title)
    if not m:
        # '까지' 앞. 사이에 '(수), 18시' 같은 글자가 끼어도 잡히도록 넉넉히 봅니다.
        m = re.search(r"(\d{1,2})\s*(?:월|[./])\s*(\d{1,2})\s*일?\.?.{0,15}?까지", title)
    if not m:
        return "", ""

    month, day = int(m.group(1)), int(m.group(2))
    if not (1 <= month <= 12 and 1 <= day <= 31):
        return "", ""

    # 연도는 제목에 없으므로 게시일 기준으로 추정합니다
    try:
        base = datetime.datetime.strptime(posted, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        base = today()
    year = base.year
    if month < base.month - 6:      # 게시일보다 훨씬 앞선 달이면 다음 해로 봅니다
        year += 1
    try:
        due = datetime.date(year, month, day)
    except ValueError:
        return "", ""

    # 시각: '일' 숫자 바로 뒤 25자 안에서 'HH:MM' 또는 'HH시'
    tail = title[m.end(2): m.end(2) + 25]
    t = re.search(r"(\d{1,2})\s*:\s*(\d{2})", tail) or re.search(r"(\d{1,2})\s*시", tail)
    hhmm = ""
    if t:
        hour = int(t.group(1))
        minute = int(t.group(2)) if (t.lastindex or 0) >= 2 and t.group(2) else 0
        if 0 <= hour <= 23:
            hhmm = "%02d:%02d" % (hour, minute)
    return datestr(due), hhmm


def item(title: str, url: str, posted: str, agency: str, ministry: str,
         source: str, post_no: str = "") -> dict:
    """공고 한 건. 제목에서 마감일을 뽑아 채웁니다."""
    title = re.sub(r"\s+", " ", title).strip()
    due, due_time = find_due(title, posted)
    return {
        "id": uid(source, post_no or url or title),
        "ministry": ministry,          # 카드 상단 배지
        "agency": agency,
        "no": "",
        "title": title,
        "program": "",
        "posted": posted,
        "openFrom": posted,            # 목록에 접수 시작일이 없어 게시일을 씁니다
        "due": due,                    # 제목에서 못 뽑으면 빈 값 → 화면에 '기간 미확인'
        "dueTime": due_time,
        "amount": 0,
        "contact": "",
        "url": url,
        "source": source,
        "_key": post_no or url or title,   # 중복 판정용 (저장 전에 지웁니다)
    }


class LinkCollector(HTMLParser):
    """<a> 태그의 (속성값 전체, 화면에 보이는 글자) 쌍을 모읍니다."""

    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._attrs: str | None = None
        self._buf: list[str] = []

    def handle_starttag(self, tag, attrs):  # noqa: ANN001
        if tag == "a":
            self._attrs = " ".join(v or "" for _, v in attrs)
            self._buf = []

    def handle_data(self, data):  # noqa: ANN001
        if self._attrs is not None:
            self._buf.append(data)

    def handle_endtag(self, tag):  # noqa: ANN001
        if tag == "a" and self._attrs is not None:
            text = re.sub(r"\s+", " ", "".join(self._buf)).strip()
            self.links.append((self._attrs, text))
            self._attrs = None


def rss_date(text: str) -> str:
    if not text:
        return ""
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S"):
        try:
            return datestr(datetime.datetime.strptime(text.strip(), fmt).date())
        except ValueError:
            pass
    return first_date(text)
