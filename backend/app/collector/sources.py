"""
공고를 어디서 어떻게 읽어오는지.

공고수집 스크립트 v9 의 `게시판수집` / `RSS수집` 과 소스 정의를 그대로 옮겼습니다.

원본과 달라진 점은 하나입니다.
수집 단계에서 키워드로 버리지 않고 **전량 저장**합니다. 걸러내기는 화면에서만 합니다.
나중에 "그때 그 공고 있었는데 왜 없지?" 하는 일을 막기 위해서입니다.
"""
from __future__ import annotations

import datetime
import logging
import re
import time
import xml.etree.ElementTree as ET
from collections.abc import Callable
from dataclasses import dataclass, field

from app.collector import parse
from app.collector.fetch import fetch, get
from app.core.calc import today

log = logging.getLogger("bizdash.collector")

# 며칠 전 게시물까지 가져올지
COLLECT_DAYS = 90
# 게시판을 몇 쪽까지 읽을지.
# 인재원처럼 응답이 중간에 끊기는 곳이 있어, 여러 쪽을 겹쳐 읽습니다.
# 새 공고가 더 나오지 않으면 알아서 멈춥니다.
BOARD_PAGES = 8


@dataclass
class SourceResult:
    key: str
    name: str
    items: list[dict] = field(default_factory=list)
    error: str = ""
    truncated: bool = False
    notes: list[str] = field(default_factory=list)


def in_period(posted: str) -> bool:
    if not posted:
        return True  # 날짜를 모르면 일단 포함
    try:
        d = datetime.datetime.strptime(posted, "%Y-%m-%d").date()
    except ValueError:
        return True
    return (today() - d).days <= COLLECT_DAYS


# ======================================================================
# RSS 읽기
# ======================================================================
def collect_rss(rss_url: str, agency: str, ministry: str, source: str) -> list[dict]:
    body = get(rss_url)
    root = ET.fromstring(body.encode("utf-8"))
    out = []
    for node in root.iter():
        if not node.tag.lower().endswith("item"):
            continue
        title, link, posted = "", "", ""
        for c in node:
            t = c.tag.lower()
            v = (c.text or "").strip()
            if t.endswith("title"):
                title = re.sub(r"<[^>]+>", "", v)
            elif t.endswith("link"):
                link = v
            elif t.endswith("pubdate") or t.endswith("date") or t.endswith("regdate"):
                posted = posted or parse.rss_date(v)
        if not title:
            continue
        if not in_period(posted):
            continue
        out.append(parse.item(title, link, posted, agency, ministry, source))
    return out


# ======================================================================
# 게시판 목록 읽기
#   링크가 <a href="..."> 든 <a href="#" onclick="fn_view('123')"> 든
#   글 번호만 찾으면 되도록, a 태그의 모든 속성값을 뒤집니다.
# ======================================================================
def collect_board(
    name: str,
    list_url: Callable[[int], str],
    no_pattern: str,
    detail_url: Callable[[str], str],
    agency: str,
    ministry: str,
    source: str,
    exclude: str | None = None,
) -> SourceResult:
    """
    한 쪽씩 읽어 나가다가 새 글이 더 안 나오면 멈춥니다.
    단, 응답이 중간에 끊긴 쪽은 '글이 없다'고 볼 수 없으므로 중단 근거로 쓰지
    않습니다. (끊긴 쪽을 빈 쪽으로 오해해 일찍 멈추면 오히려 덜 걷힙니다.)
    """
    res = SourceResult(key=source, name=name)
    seen_no: set[str] = set()
    empty_streak = 0
    per_page: list[str] = []

    for page in range(1, BOARD_PAGES + 1):
        url = list_url(page)
        # 한 쪽이 실패해도 나머지 쪽은 계속 읽습니다.
        try:
            body, truncated = fetch(url)
        except Exception as e:  # noqa: BLE001
            log.warning("%s: 목록 %d쪽을 못 읽었습니다 (%s) — 나머지는 계속합니다.",
                        name, page, type(e).__name__)
            per_page.append(f"{page}쪽 실패")
            continue
        res.truncated = res.truncated or truncated

        p = parse.LinkCollector()
        p.feed(body)

        new_here, in_period_here = 0, 0
        for attrs, text in p.links:
            if exclude and re.search(exclude, attrs):
                continue      # 다른 게시판·메뉴 링크
            m = re.search(no_pattern, attrs)
            if not m:
                continue
            no = m.group(1)
            if no in seen_no:          # 상단 고정 + 다른 쪽 중복 제거
                continue
            if len(text) < 8:          # '새글', 아이콘, 페이지 번호 등 제외
                continue

            seen_no.add(no)            # 기간을 벗어나도 '본 글'로 기록해 둡니다
            new_here += 1

            posted = parse.find_posted(body, text, no)
            if not in_period(posted):
                continue

            in_period_here += 1
            res.items.append(parse.item(text, detail_url(no), posted, agency, ministry, source, post_no=no))

        per_page.append(f"{page}쪽 {new_here}건" + ("(잘림)" if truncated else ""))

        # 멈출 때를 정합니다. 잘린 쪽은 내용을 다 못 봤으므로 판단에 쓰지 않습니다.
        if truncated:
            empty_streak = 0
        else:
            # 새 글은 있는데 전부 수집기간을 벗어났다면 그만큼 과거로 온 것입니다
            if new_here > 0 and in_period_here == 0:
                break
            empty_streak = empty_streak + 1 if new_here == 0 else 0
            if empty_streak >= 2:
                break
        time.sleep(0.5)   # 서버 부담을 줄이기 위해 잠깐 쉽니다

    if res.truncated:
        res.notes.append("쪽별 수집: " + " · ".join(per_page))
    if len(res.items) < 3:
        res.notes.append(f"{len(res.items)}건만 찾았습니다. 목록 구조가 바뀌었을 수 있습니다.")
    return res


# ======================================================================
# 소스 정의
# ======================================================================
def khis() -> SourceResult:
    """한국보건의료정보원 — RSS"""
    r = SourceResult(key="khis-rss", name="한국보건의료정보원")
    r.items = collect_rss(
        "https://www.khis.kr/rss/board.es?mid=a10301000000&bid=0001",
        "한국보건의료정보원", "보건의료정보원", "khis-rss")
    return r


def kohi() -> SourceResult:
    """
    한국보건복지인재원 — 링크가 자바스크립트라 글번호(q_bbscttSn)로 찾습니다.

    이 서버는 응답을 끝까지 보내지 않고 끊는 일이 잦습니다. 실제 페이지를 확인해
    보니 좌측 메뉴가 워낙 커서 **글 목록이 페이지의 75% 지점에서야 시작**하고,
    끊기는 자리가 딱 그 부근입니다.

    그래서 한 쪽에 적게 담는 대신 **많이 담습니다**(q_rowPerPage=50).
    메뉴 부분은 어차피 한 번 받아야 하므로, 같은 한 번에 글이 많이 실릴수록
    잘리더라도 건지는 글이 많아집니다.
    """
    return collect_board(
        "한국보건복지인재원",
        lambda page: ("https://www.kohi.or.kr/user/bbs/BD_selectBbsList.do"
                      f"?q_bbsCode=1013&q_rowPerPage=50&q_currPage={page}"),
        # 글번호는 '20260714140713580' 같은 14~20자리 숫자입니다.
        r"(\d{14,20})",
        lambda no: ("https://www.kohi.or.kr/user/bbs/BD_selectBbs.do"
                    f"?q_bbsCode=1013&q_bbscttSn={no}"),
        "한국보건복지인재원", "보건복지인재원", "kohi-board",
        # 다른 게시판(q_bbsCode=1013 이 아닌 링크)은 제외합니다.
        exclude=r"q_bbsCode=(?!1013\b)\d+",
    )


def khidi() -> SourceResult:
    """한국보건산업진흥원 — linkId 가 글 고유번호입니다."""
    return collect_board(
        "한국보건산업진흥원",
        lambda page: f"https://www.khidi.or.kr/board?menuId=MENU01108&pageNum={page}",
        r"linkId=(\d+)",
        lambda no: f"https://www.khidi.or.kr/board/view?linkId={no}&menuId=MENU01108",
        "한국보건산업진흥원", "보건산업진흥원", "khidi-board",
    )


# ======================================================================
# NTIS 국가R&D 통합공고
# ======================================================================
NTIS_URL = "http://www.ntis.go.kr/rndgate/unRndRss.xml"

# prt 는 최대 100 입니다 (200·500 을 넣어도 100건만 옵니다).
# Fi 는 '전체에서 몇 번째부터'가 아니라 'prt 로 가져온 묶음 안의 시작 행'이라
# 100건 너머로는 넘어갈 수 없습니다. 더 과거를 가져오려면 dt=YYYYMMDD 로
# 날짜별로 받아야 합니다 (scripts/ntis_backfill.py).
NTIS_MAX = 100


def _ntis_items(url: str) -> list[dict]:
    """
    NTIS 는 마감일(appdue)과 공고금액(budget)을 직접 줍니다.
    기관 게시판처럼 제목에서 뽑아낼 필요가 없어 훨씬 정확합니다.
    (XSL 샘플에는 이 태그들이 없어서 없을 줄 알았는데, 실제로는 있었습니다.
     docs/ntis/unRndRss-원문.xml 참고)
    """
    body = get(url, timeout=60)
    root = ET.fromstring(body.encode("utf-8"))
    out = []
    for node in root.iter():
        if not node.tag.lower().endswith("item"):
            continue
        g = {c.tag: (c.text or "").strip() for c in node}
        title = re.sub(r"<[^>]+>", "", g.get("title", "")).strip()
        if not title:
            continue

        posted = parse.first_date(g.get("pubDate", ""))      # 2026.08.21 형태
        open_from = parse.first_date(g.get("appbegin", "")) or posted
        due = parse.first_date(g.get("appdue", ""))
        # 마감일이 비어 있는 공고만 제목에서 뽑아 봅니다
        due_time = ""
        if not due:
            due, due_time = parse.find_due(title, posted)

        try:
            amount = max(0, int(float(g.get("budget") or 0)))
        except ValueError:
            amount = 0

        link = g.get("link", "")
        out.append({
            "id": parse.uid("ntis-rss", link or title),
            "ministry": g.get("author", "") or "NTIS 통합공고",   # 공고기관(부처)
            "agency": g.get("category", ""),                      # 전문기관
            "no": "",
            "title": title,
            "program": "",
            "posted": posted,
            "openFrom": open_from,
            "due": due,
            "dueTime": due_time,
            "amount": amount,
            "contact": "",
            "url": link,
            "source": "ntis-rss",
            "_key": link or title,
        })
    return out


def ntis() -> SourceResult:
    """
    NTIS 통합공고 — 최신 100건.

    전 부처라 건수가 많지만(전체 1만 건이 넘습니다) 하루에 새로 올라오는 것은
    두어 건 수준입니다. 주 2회 수집이면 최신 100건으로 충분히 덮습니다.

    수집 단계에서 키워드로 버리지 않고 전량 저장합니다. 걸러내기는 화면에서만 합니다.
    """
    r = SourceResult(key="ntis-rss", name="NTIS 통합공고")
    items = _ntis_items(f"{NTIS_URL}?prt={NTIS_MAX}")
    kept = [a for a in items if in_period(a["posted"])]
    if len(kept) < len(items):
        r.notes.append(f"{len(items)}건 중 수집기간({COLLECT_DAYS}일) 안의 {len(kept)}건만 담았습니다.")
    # 최신 100건을 꽉 채워 받았다면 그 너머에 더 있을 수 있다는 뜻입니다
    if len(items) >= NTIS_MAX and all(in_period(a["posted"]) for a in items):
        r.notes.append("최신 100건이 모두 수집기간 안입니다 — 그 이전 공고는 "
                       "scripts/ntis_backfill.py 로 채워 주세요.")
    r.items = kept
    return r


def ntis_by_date(day: datetime.date) -> list[dict]:
    """특정 공고일의 NTIS 공고 (과거를 채울 때 씁니다)"""
    return _ntis_items(f"{NTIS_URL}?prt={NTIS_MAX}&dt={day.strftime('%Y%m%d')}")


# 순서대로 돌립니다. 하나가 실패해도 나머지는 계속 수집됩니다.
SOURCES: list[tuple[str, str, Callable[[], SourceResult]]] = [
    ("khis", "한국보건의료정보원", khis),
    ("kohi", "한국보건복지인재원", kohi),
    ("khidi", "한국보건산업진흥원", khidi),
    ("ntis", "NTIS 통합공고", ntis),
]
