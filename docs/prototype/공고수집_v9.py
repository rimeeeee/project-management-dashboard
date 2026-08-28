# -*- coding: utf-8 -*-
"""
사업 공고 수집 스크립트 (사업관리 대시보드용)   v9
=====================================================

무엇을 하는 스크립트인가
  아래 소스에서 공고 목록을 읽어와, 대시보드의 [수집 데이터 불러오기]에
  붙여넣을 수 있는 JSON 파일 하나를 만듭니다.

    1. NTIS 국가R&D 통합공고 RSS  (전 부처 R&D 공고 — RSS 주소 발급 후 아래에 입력)
    2. 한국보건의료정보원(KHIS) 공고 RSS
    3. 한국보건복지인재원(KOHI) 게시판
    4. 한국보건산업진흥원(KHIDI) 게시판

v9에서 달라진 점
  - 인재원 목록을 한 쪽에 50건씩 받습니다. 이 사이트는 좌측 메뉴가 커서 글 목록이
    페이지의 75% 지점에서 시작하는데, 끊기는 자리가 딱 그 부근입니다. 한 번 받을 때
    글을 많이 실을수록 잘려도 건지는 글이 많아집니다.
  - 수집기간을 벗어난 글만 나오는 쪽에 닿으면 더 읽지 않습니다(불필요한 요청 제거).

v8에서 달라진 점
  - 응답이 끊긴 쪽을 '글이 없는 쪽'으로 오해해 일찍 멈추던 문제를 고쳤습니다.
    (v7에서 인재원 건수가 오히려 줄어든 원인)
  - 끊기는 서버도 다시 받아 보고 그중 가장 많이 받은 응답을 씁니다(최대 4회).
  - 끊김이 있으면 쪽별 수집 건수와 첫 쪽 원본(debug 파일)을 남깁니다.

v7에서 달라진 점
  - 인재원 목록을 한 쪽에 5건씩 나눠 받습니다(q_rowPerPage). 응답이 끊기기 전에
    목록이 끝나므로, 실행할 때마다 건수가 달라지던 문제를 줄입니다.
  - 게시판을 최대 8쪽까지 읽되, 새 글이 두 쪽 연속 안 나오면 알아서 멈춥니다.

v6에서 달라진 점
  - 응답이 중간에 끊기면 다시 받아 봅니다(최대 3회). 끝까지 받은 응답이 있으면
    그것을 쓰고, 끝내 못 받으면 가장 많이 받은 것을 쓰면서 경고를 남깁니다.
    → 인재원 수집 건수가 실행할 때마다 달라지던(12 → 19 → 9건) 문제 대응.
  - 끊긴 응답에서 몇 자를 받았는지 화면에 남깁니다.

v5에서 달라진 점
  - 게시일을 '글 번호'에서 먼저 읽습니다. 한국보건복지인재원은 글 번호가
    20260825145002017 처럼 날짜+시각이라 HTML을 뒤지는 것보다 정확합니다.
    → 인재원 공고의 게시일이 대부분 비던 문제 해결.
  - 제목이 비슷한 공고를 구분하려고 제목 조각을 길게(80자부터) 맞춰봅니다.
  - 제목 안에 든 행사 날짜(예: "개최(2026.9.11)")는 게시일에서 제외합니다.

v4에서 달라진 점
  - 게시일이 오늘보다 미래면 무시합니다(게시판 게시일은 미래일 수 없음).
  - 제목을 목록 HTML에서 못 찾는 경우 글 번호를 기준으로 게시일을 다시 찾습니다.

v3에서 달라진 점
  - 서버가 응답을 끝까지 보내지 않고 끊어도(IncompleteRead) 받은 만큼으로 계속 진행합니다.
    → 한국보건복지인재원이 이 오류로 통째로 실패하던 문제 해결.
  - 목록 페이지 하나가 실패해도 나머지 페이지는 계속 읽습니다.
  - 제목의 마감 표기 중 "(7.8(수), 18시까지)" 처럼 물결표(~)가 없는 형태도 인식합니다.

v2에서 달라진 점
  - 제목에 적힌 마감일(예: "~8월 28일(금) 18:00까지")을 자동으로 뽑아 접수 마감일로 넣습니다.
  - 같은 공고가 상단 고정 + 일반 목록에 중복되던 문제를 해결했습니다(글 번호 기준).
  - 게시판 링크가 자바스크립트로 되어 있어도 글 번호를 찾도록 파서를 고쳤습니다.
  - 수집 결과가 너무 적으면 원본 HTML을 debug 파일로 남겨 원인을 찾을 수 있게 했습니다.

실행 방법 (Windows 기준)
  1) Python 설치: https://www.python.org/downloads  (설치 시 "Add to PATH" 체크)
  2) 이 파일을 더블클릭하거나, 명령창에서:  python 공고수집.py
  3) 같은 폴더에 생기는  공고데이터.json  파일을 메모장으로 열어 전체 복사
  4) 대시보드 > 사업 현황(공고) > [수집 데이터 불러오기] 에 붙여넣기

문제가 생기면
  화면에 나오는 메시지 전체와, 생겼다면 debug_*.html 파일을 개발 담당에게 전달해 주세요.
  소스 하나가 실패해도 나머지는 계속 수집됩니다.

주의
  - 외부 라이브러리 없이 Python 기본 기능만 사용합니다 (pip 설치 불필요).
  - 목록 페이지 1~2쪽만 가볍게 읽습니다. 서버에 부담을 주지 않도록 페이지 수를 늘리지 마세요.
"""

import json
import re
import ssl
import sys
import time
import hashlib
import datetime
import http.client
import zlib
import urllib.request
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

# ======================================================================
# 설정 — 필요한 부분만 고쳐 쓰세요
# ======================================================================

설정 = {
    # NTIS 통합공고 RSS 주소.  발급받으면 따옴표 안에 넣으세요.
    "NTIS_RSS_URL": "",

    # 포함 키워드: 제목에 하나라도 들어 있으면 수집. 비워두면([]) 전부 수집.
    # 건수가 많은 NTIS 통합공고에만 적용됩니다.
    # (기관 게시판은 건수가 적으므로 전량 수집하고, 걸러보기는 대시보드에서 합니다.)
    "키워드": ["병원", "의료", "임상", "보건", "바이오", "디지털치료", "헬스"],

    # 며칠 전 게시물까지 가져올지
    "수집기간_일": 90,

    # 게시판을 몇 쪽까지 읽을지.
    # 인재원처럼 응답이 중간에 끊기는 곳이 있어, 한 쪽에 적은 건수만 담아
    # 여러 쪽을 겹쳐 읽습니다. 새 공고가 더 나오지 않으면 알아서 멈춥니다.
    "게시판_페이지수": 8,

    # 소스별 켜기/끄기
    "소스": {
        "ntis": True,
        "khis": True,    # 한국보건의료정보원 (RSS)
        "kohi": True,    # 한국보건복지인재원 (게시판)
        "khidi": True,   # 한국보건산업진흥원 (게시판)
    },
}

출력파일 = "공고데이터.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; SHR-BizDash-Collector/3.0)",
    "Accept-Language": "ko",
    # 압축을 쓰지 않습니다. 응답이 중간에 끊겼을 때 압축본은 뒷부분을 거의
    # 살릴 수 없지만, 압축하지 않은 본문은 받은 만큼 그대로 읽을 수 있습니다.
    "Accept-Encoding": "identity",
    "Connection": "close",
}


# ======================================================================
# 공통 도구
# ======================================================================

def 오늘():
    return datetime.date.today()


def 날짜문자(d):
    return d.strftime("%Y-%m-%d")


def 디코드(raw):
    """받은 바이트를 문자열로 (utf-8 → euc-kr → cp949 순서로 해석)"""
    for enc in ("utf-8", "euc-kr", "cp949"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def 압축풀기(raw, 인코딩):
    """gzip/deflate 응답을 풉니다. 중간에 끊긴 압축도 받은 만큼 풀어냅니다."""
    인코딩 = (인코딩 or "").lower()
    if 인코딩 in ("gzip", "x-gzip"):
        해제기 = zlib.decompressobj(16 + zlib.MAX_WBITS)
    elif 인코딩 == "deflate":
        해제기 = zlib.decompressobj()
    else:
        return raw
    try:
        return 해제기.decompress(raw)
    except zlib.error:
        return raw


끊긴서버 = set()   # 응답이 잘리는 것으로 이미 확인된 서버 (재시도·경고를 줄입니다)


def 받아오기(url, timeout=25, 재시도=3):
    """
    URL의 본문을 (본문, 잘렸는지) 로 돌려줍니다.

    한국보건복지인재원 서버는 응답을 끝까지 보내지 않고 끊는 일이 잦습니다
    (IncompleteRead). 받은 만큼만 쓰면 목록 뒷부분이 사라지고, 끊기는 지점이
    매번 달라서 수집 건수가 들쭉날쭉해집니다. 그래서 이렇게 처리합니다.

      1) 끝까지 받았으면 그대로 사용
      2) 끊겼으면 다시 받아 보고, 그중 '가장 많이 받은' 응답을 사용
      3) 끝까지 못 받았다는 사실을 함께 돌려줌
         (부르는 쪽에서 '이 쪽은 못 믿는다'고 판단할 수 있도록)
    """
    호스트 = re.sub(r"^https?://([^/]+).*$", r"\1", url)
    최선, 마지막오류 = "", None

    for 시도 in range(재시도 + 1):
        req = urllib.request.Request(url, headers=HEADERS)
        ctx = ssl.create_default_context()
        try:
            완전 = True
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as res:
                인코딩 = res.headers.get("Content-Encoding")
                try:
                    raw = res.read()
                except http.client.IncompleteRead as e:
                    raw, 완전 = e.partial, False
            본문 = 디코드(압축풀기(raw, 인코딩))
            if 완전:
                return 본문, False
            if len(본문) > len(최선):
                최선 = 본문
        except http.client.IncompleteRead as e:
            본문 = 디코드(e.partial or b"")
            if len(본문) > len(최선):
                최선 = 본문
            마지막오류 = e
        except Exception as e:  # noqa: BLE001 - 한 번 더 시도해 봅니다
            마지막오류 = e
        if 시도 < 재시도:
            time.sleep(1.0)

    if 최선:
        if 호스트 not in 끊긴서버:      # 같은 서버 경고는 한 번만 보여 줍니다
            끊긴서버.add(호스트)
            print("  [주의] %s 서버가 응답을 끝까지 보내지 않습니다 (%d자 수신)."
                  % (호스트, len(최선)))
        return 최선, True
    raise 마지막오류


def 가져오기(url, timeout=25, 재시도=3):
    """본문만 필요할 때 쓰는 간단한 형태 (RSS 등)."""
    return 받아오기(url, timeout, 재시도)[0]


def 고유번호(*부분):
    h = hashlib.md5("|".join(str(x) for x in 부분).encode("utf-8")).hexdigest()
    return "c" + h[:10]


날짜패턴 = re.compile(r"(20\d{2})[.\-/년\s]*(\d{1,2})[.\-/월\s]*(\d{1,2})")


def 날짜정리(text):
    """'2026-08-25', '2026/08/25', '2026.08.25' → '2026-08-25' (첫 번째 것만)"""
    목록 = 날짜들(text)
    return 목록[0] if 목록 else ""


def 날짜들(text):
    """글 안에 있는 날짜를 나온 순서대로 모두 돌려줍니다."""
    if not text:
        return []
    결과 = []
    for m in 날짜패턴.finditer(str(text)):
        try:
            결과.append(날짜문자(
                datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))))
        except ValueError:
            continue
    return 결과


def 번호날짜(글번호):
    """
    글 번호가 'YYYYMMDDHHMMSS...' 형태면 그 앞 8자리가 곧 게시일입니다.
    (한국보건복지인재원이 이 방식이며, HTML을 뒤지는 것보다 정확합니다.)
    글 번호가 단순 일련번호인 곳(진흥원 linkId 등)에서는 빈 값을 돌려줍니다.
    """
    번호 = str(글번호 or "")
    if len(번호) < 14 or not 번호.isdigit():
        return ""
    try:
        d = datetime.date(int(번호[:4]), int(번호[4:6]), int(번호[6:8]))
    except ValueError:
        return ""
    if d.year < 2000 or d > 오늘():
        return ""
    return 날짜문자(d)


def 게시일찾기(본문, 제목, 글번호):
    """
    이 글의 게시일을 찾습니다. 순서대로 시도합니다.

    1) 글 번호가 날짜 형태면 그대로 사용 (가장 정확)
    2) 목록 HTML에서 제목을 찾아 그 주변의 날짜를 사용

    2)에서 주의할 점 두 가지
      - 제목 조각은 '길게' 잡아야 합니다. 앞부분이 같은 공고가 두 건 있으면
        (예: "…K-VIP… 통합 연장 공고" / "…K-VIP… 통합 공고")
        짧은 조각으로는 둘 다 첫 번째 글에 걸려 같은 날짜가 들어갑니다.
      - 제목 안에 든 행사 날짜(예: "개최(2026.9.11)")는 게시일이 아니므로 제외합니다.
        게시판 게시일은 미래일 수도 없으므로 오늘 이후 날짜도 제외합니다.
    """
    d = 번호날짜(글번호)
    if d:
        return d

    기준일 = 오늘()
    제목날짜 = set(날짜들(제목))

    def 고르기(근처):
        for d in 날짜들(근처):
            if d in 제목날짜:
                continue
            if datetime.datetime.strptime(d, "%Y-%m-%d").date() <= 기준일:
                return d
        return ""

    for 길이 in (80, 60, 40, 20, 12):
        조각 = (제목 or "")[:길이]
        if not 조각:
            continue
        위치 = 본문.find(조각)
        if 위치 < 0:
            continue
        d = 고르기(본문[위치: 위치 + 2000])
        if d:
            return d

    # 제목을 목록에서 못 찾는 경우(특수문자·줄바꿈 등)에는 글 번호를 기준으로 찾습니다
    if 글번호:
        위치 = 본문.find(str(글번호))
        if 위치 >= 0:
            return 고르기(본문[위치: 위치 + 2000])
    return ""


def 기간내(posted):
    if not posted:
        return True  # 날짜를 모르면 일단 포함
    try:
        d = datetime.datetime.strptime(posted, "%Y-%m-%d").date()
    except ValueError:
        return True
    return (오늘() - d).days <= 설정["수집기간_일"]


def 키워드통과(title):
    kws = 설정["키워드"]
    return (not kws) or any(k in title for k in kws)


def 마감일추출(title, posted):
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
    후보 = re.search(r"[~〜]\s*(\d{1,2})\s*(?:월|[./])\s*(\d{1,2})\s*일?\.?", title)
    if not 후보:
        # '까지' 앞. 사이에 '(수), 18시' 같은 글자가 끼어도 잡히도록 넉넉히 봅니다.
        후보 = re.search(r"(\d{1,2})\s*(?:월|[./])\s*(\d{1,2})\s*일?\.?.{0,15}?까지", title)
    if not 후보:
        return "", ""

    월, 일 = int(후보.group(1)), int(후보.group(2))
    if not (1 <= 월 <= 12 and 1 <= 일 <= 31):
        return "", ""

    # 연도는 제목에 없으므로 게시일 기준으로 추정합니다
    try:
        기준 = datetime.datetime.strptime(posted, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        기준 = 오늘()
    연도 = 기준.year
    if 월 < 기준.month - 6:      # 게시일보다 훨씬 앞선 달이면 다음 해로 봅니다
        연도 += 1
    try:
        마감 = datetime.date(연도, 월, 일)
    except ValueError:
        return "", ""

    # 시각: '일' 숫자 바로 뒤 25자 안에서 'HH:MM' 또는 'HH시'
    # ('까지'까지 포함해 잡힌 경우에도 시각을 놓치지 않도록 날짜 끝을 기준으로 봅니다)
    꼬리 = title[후보.end(2):후보.end(2) + 25]
    t = re.search(r"(\d{1,2})\s*:\s*(\d{2})", 꼬리) or re.search(r"(\d{1,2})\s*시", 꼬리)
    시각 = ""
    if t:
        시 = int(t.group(1))
        분 = int(t.group(2)) if (t.lastindex or 0) >= 2 and t.group(2) else 0
        if 0 <= 시 <= 23:
            시각 = "%02d:%02d" % (시, 분)
    return 날짜문자(마감), 시각


def 항목(title, url, posted, 기관, 부처표시, source, 글번호=""):
    """대시보드 공고 형식 한 건. 제목에서 마감일을 뽑아 채웁니다."""
    title = re.sub(r"\s+", " ", title).strip()
    마감, 시각 = 마감일추출(title, posted)
    return {
        "id": 고유번호(source, 글번호 or url or title),
        "ministry": 부처표시,      # 카드 상단 배지
        "agency": 기관,
        "no": "",
        "title": title,
        "program": "",
        "posted": posted,
        "openFrom": posted,        # 목록에 접수 시작일이 없어 게시일을 씁니다
        "due": 마감,               # 제목에서 못 뽑으면 빈 값 → 대시보드에 '기간 미확인'
        "dueTime": 시각,
        "amount": 0,
        "contact": "",
        "url": url,
        "source": source,
        "_key": 글번호 or url or title,   # 중복 판정용 (저장 전에 지웁니다)
    }


# ======================================================================
# RSS 읽기 (NTIS, KHIS 공용)
# ======================================================================

def RSS날짜(text):
    if not text:
        return ""
    for 형식 in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S"):
        try:
            return 날짜문자(datetime.datetime.strptime(text.strip(), 형식).date())
        except ValueError:
            pass
    return 날짜정리(text)


def RSS수집(rss_url, 기관, 부처표시, source, 키워드적용=False):
    본문 = 가져오기(rss_url)
    root = ET.fromstring(본문.encode("utf-8"))
    결과 = []
    for item in root.iter():
        if not item.tag.lower().endswith("item"):
            continue
        제목, 링크, 게시일 = "", "", ""
        for c in item:
            t = c.tag.lower()
            v = (c.text or "").strip()
            if t.endswith("title"):
                제목 = re.sub(r"<[^>]+>", "", v)
            elif t.endswith("link"):
                링크 = v
            elif t.endswith("pubdate") or t.endswith("date") or t.endswith("regdate"):
                게시일 = 게시일 or RSS날짜(v)
        if not 제목:
            continue
        if 키워드적용 and not 키워드통과(제목):
            continue
        if not 기간내(게시일):
            continue
        결과.append(항목(제목, 링크, 게시일, 기관, 부처표시, source))
    return 결과


# ======================================================================
# 게시판 목록 읽기
#   링크가 <a href="..."> 든 <a href="#" onclick="fn_view('123')"> 든
#   글 번호만 찾으면 되도록, a 태그의 모든 속성값을 뒤집니다.
# ======================================================================

class 링크수집기(HTMLParser):
    """<a> 태그의 (속성값 전체, 화면에 보이는 글자) 쌍을 모읍니다."""

    def __init__(self):
        super().__init__()
        self.links = []
        self._attrs = None
        self._buf = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._attrs = " ".join(v or "" for _, v in attrs)
            self._buf = []

    def handle_data(self, data):
        if self._attrs is not None:
            self._buf.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._attrs is not None:
            글자 = re.sub(r"\s+", " ", "".join(self._buf)).strip()
            self.links.append((self._attrs, 글자))
            self._attrs = None


def 게시판수집(이름, 목록URL만들기, 글번호패턴, 상세URL만들기, 기관, 부처표시, source,
           제외패턴=None):
    """
    목록URL만들기: 쪽 번호(1부터) → 목록 페이지 주소
    글번호패턴  : a 태그 속성값에서 글 번호를 찾아내는 정규식 (그룹 1이 번호)
    상세URL만들기: 글번호 → 상세 페이지 주소
    제외패턴    : 이 정규식에 걸리는 링크는 건너뜁니다 (다른 게시판 링크 등)

    한 쪽씩 읽어 나가다가 새 글이 더 안 나오면 멈춥니다.
    단, 응답이 중간에 끊긴 쪽은 '글이 없다'고 볼 수 없으므로 중단 근거로 쓰지
    않습니다. (끊긴 쪽을 빈 쪽으로 오해해 일찍 멈추면 오히려 덜 걷힙니다.)

    끊기는 게시판이 있으면 마지막에 쪽별 수집 건수를 남깁니다.
    쪽당 몇 건씩 들어오는지 보면 목록 개수 설정이 먹히는지 알 수 있습니다.
    """
    결과, 본문첫장, 본번호 = [], None, set()
    연속빈쪽, 쪽별기록, 잘린적있음 = 0, [], False

    for 쪽 in range(1, 설정["게시판_페이지수"] + 1):
        url = 목록URL만들기(쪽)
        # 한 쪽이 실패해도 나머지 쪽은 계속 읽습니다.
        try:
            본문, 잘림 = 받아오기(url)
        except Exception as e:  # noqa: BLE001
            print("  [주의] %s: 목록 %d쪽을 못 읽었습니다 (%s) — 나머지는 계속합니다."
                  % (이름, 쪽, type(e).__name__))
            쪽별기록.append("%d쪽 실패" % 쪽)
            continue
        잘린적있음 = 잘린적있음 or 잘림
        if 본문첫장 is None:
            본문첫장 = 본문
        p = 링크수집기()
        p.feed(본문)

        이번쪽새글, 이번쪽기간내 = 0, 0
        for 속성, 글자 in p.links:
            if 제외패턴 and re.search(제외패턴, 속성):
                continue      # 다른 게시판·메뉴 링크
            m = re.search(글번호패턴, 속성)
            if not m:
                continue
            번호 = m.group(1)
            if 번호 in 본번호:          # 상단 고정 + 다른 쪽 중복 제거
                continue
            if len(글자) < 8:           # '새글', 아이콘, 페이지 번호 등 제외
                continue

            본번호.add(번호)            # 기간을 벗어나도 '본 글'로 기록해 둡니다
            이번쪽새글 += 1

            # 글 제목 뒤쪽에서 게시일을 찾습니다
            게시일 = 게시일찾기(본문, 글자, 번호)
            if not 기간내(게시일):
                continue

            이번쪽기간내 += 1
            결과.append(항목(글자, 상세URL만들기(번호), 게시일,
                          기관, 부처표시, source, 글번호=번호))

        쪽별기록.append("%d쪽 %d건%s" % (쪽, 이번쪽새글, "(잘림)" if 잘림 else ""))

        # 멈출 때를 정합니다. 잘린 쪽은 내용을 다 못 봤으므로 판단에 쓰지 않습니다.
        if 잘림:
            연속빈쪽 = 0
        else:
            # 새 글은 있는데 전부 수집기간을 벗어났다면 그만큼 과거로 온 것입니다
            if 이번쪽새글 > 0 and 이번쪽기간내 == 0:
                break
            연속빈쪽 = 연속빈쪽 + 1 if 이번쪽새글 == 0 else 0
            if 연속빈쪽 >= 2:
                break
        time.sleep(0.5)   # 서버 부담을 줄이기 위해 잠깐 쉽니다

    if 잘린적있음:
        print("  [진단] %s 쪽별 수집: %s" % (이름, " · ".join(쪽별기록)))
        # 첫 쪽 원본을 남겨 둡니다. 목록이 몇 건씩 나오는지, 어디서 잘렸는지
        # 이 파일을 보면 알 수 있습니다.
        파일 = "debug_%s_1쪽.html" % source
        try:
            with open(파일, "w", encoding="utf-8") as f:
                f.write(본문첫장 or "")
            print("         %s 파일을 개발 담당에게 보내주시면 원인을 맞출 수 있습니다."
                  % 파일)
        except OSError:
            pass

    # 결과가 너무 적으면 구조가 바뀐 것일 수 있으니 원본을 남깁니다
    if len(결과) < 3 and 본문첫장:
        파일 = "debug_%s.html" % source
        try:
            with open(파일, "w", encoding="utf-8") as f:
                f.write(본문첫장)
            print("  [확인필요] %s: %d건만 찾았습니다. 목록 구조가 다를 수 있습니다."
                  % (이름, len(결과)))
            print("             %s 파일을 개발 담당에게 보내주세요." % 파일)
        except OSError:
            pass
    return 결과


# ======================================================================
# 소스 정의
# ======================================================================

def 수집_NTIS():
    if not 설정["NTIS_RSS_URL"]:
        print("  [건너뜀] NTIS: RSS 주소가 아직 설정되지 않았습니다. (설정의 NTIS_RSS_URL)")
        return []
    return RSS수집(설정["NTIS_RSS_URL"], "NTIS 통합공고", "NTIS 통합공고",
                   "ntis-rss", 키워드적용=True)


def 수집_KHIS():
    return RSS수집(
        "https://www.khis.kr/rss/board.es?mid=a10301000000&bid=0001",
        "한국보건의료정보원", "보건의료정보원", "khis-rss")


def 수집_KOHI():
    """
    한국보건복지인재원 — 링크가 자바스크립트라 글번호(q_bbscttSn)로 찾습니다.

    이 서버는 응답을 끝까지 보내지 않고 끊는 일이 잦습니다. 실제 페이지를 확인해
    보니 좌측 메뉴가 워낙 커서 **글 목록이 페이지의 75% 지점에서야 시작**하고,
    끊기는 자리가 딱 그 부근입니다. 즉 한 번 받을 때마다 무거운 메뉴를 다 받고
    정작 필요한 목록에서 잘리는 구조입니다.

    그래서 한 쪽에 적게 담는 대신 **많이 담습니다**(q_rowPerPage=50).
    메뉴 부분은 어차피 한 번 받아야 하므로, 같은 한 번에 글이 많이 실릴수록
    잘리더라도 건지는 글이 많아집니다. 쪽 수도 3쪽이면 충분해집니다.
    (q_rowPerPage 는 실제로 동작함을 확인했습니다 — 5로 두었을 때 목록에
     '전체 1051건, 현재페이지 1/211'로 표시되어 쪽당 5건이 맞았습니다.)
    """
    목록 = (lambda 쪽:
            "https://www.kohi.or.kr/user/bbs/BD_selectBbsList.do"
            "?q_bbsCode=1013&q_rowPerPage=50&q_currPage=%d" % 쪽)
    상세 = (lambda 번호:
            "https://www.kohi.or.kr/user/bbs/BD_selectBbs.do"
            "?q_bbsCode=1013&q_bbscttSn=%s" % 번호)
    # 글번호는 '20260714140713580' 같은 14~20자리 숫자입니다.
    # href 든 onclick 함수 인자든 상관없이 잡습니다.
    패턴 = r"(\d{14,20})"
    # 다른 게시판(q_bbsCode=1013 이 아닌 링크)은 제외합니다.
    제외 = r"q_bbsCode=(?!1013\b)\d+"
    return 게시판수집("한국보건복지인재원", 목록, 패턴, 상세,
                  "한국보건복지인재원", "보건복지인재원", "kohi-board",
                  제외패턴=제외)


def 수집_KHIDI():
    """한국보건산업진흥원 — linkId 가 글 고유번호입니다."""
    목록 = (lambda 쪽:
            "https://www.khidi.or.kr/board?menuId=MENU01108&pageNum=%d" % 쪽)
    상세 = (lambda 번호:
            "https://www.khidi.or.kr/board/view?linkId=%s&menuId=MENU01108" % 번호)
    패턴 = r"linkId=(\d+)"
    return 게시판수집("한국보건산업진흥원", 목록, 패턴, 상세,
                  "한국보건산업진흥원", "보건산업진흥원", "khidi-board")


# ======================================================================
# 실행
# ======================================================================

def main():
    print("=" * 56)
    print(" 사업 공고 수집을 시작합니다  (%s)" % 날짜문자(오늘()))
    print("=" * 56)

    소스들 = [
        ("ntis",  "NTIS 통합공고",     수집_NTIS),
        ("khis",  "한국보건의료정보원", 수집_KHIS),
        ("kohi",  "한국보건복지인재원", 수집_KOHI),
        ("khidi", "한국보건산업진흥원", 수집_KHIDI),
    ]

    전체, 오류 = [], []
    for 키, 이름, 함수 in 소스들:
        if not 설정["소스"].get(키):
            print("  [건너뜀] %s (설정에서 꺼짐)" % 이름)
            continue
        try:
            건들 = 함수()
            마감있음 = sum(1 for a in 건들 if a["due"])
            print("  [완료] %-12s %2d건  (마감일 자동 추출 %d건)"
                  % (이름, len(건들), 마감있음))
            전체.extend(건들)
        except Exception as e:  # noqa: BLE001 - 소스 하나가 죽어도 나머지는 계속
            오류.append((이름, e))
            print("  [실패] %s → %s: %s" % (이름, type(e).__name__, e))

    # 중복 제거: 글 번호 우선, 없으면 제목+게시일
    본목록, 본키 = [], set()
    for a in 전체:
        키값 = (a["source"].split("-")[0], a.pop("_key"))
        제목키 = (a["title"], a["posted"])
        if 키값 in 본키 or 제목키 in 본키:
            continue
        본키.add(키값)
        본키.add(제목키)
        본목록.append(a)

    본목록.sort(key=lambda a: a["posted"], reverse=True)

    with open(출력파일, "w", encoding="utf-8") as f:
        json.dump({"announcements": 본목록, "collectedAt": 날짜문자(오늘())},
                  f, ensure_ascii=False, indent=2)

    print("-" * 56)
    print(" 총 %d건 수집 → %s 파일 저장" % (len(본목록), 출력파일))
    print(" 이 파일을 메모장으로 열어 전체 복사한 뒤,")
    print(" 대시보드 > 사업 현황(공고) > [수집 데이터 불러오기]에 붙여넣으세요.")
    if 오류:
        print("-" * 56)
        print(" 실패한 소스가 있습니다. 아래 내용을 개발 담당에게 전달해 주세요:")
        for 이름, e in 오류:
            print("   - %s: %s: %s" % (이름, type(e).__name__, e))
    print("=" * 56)
    if sys.platform.startswith("win"):
        input(" 엔터를 누르면 창이 닫힙니다...")


if __name__ == "__main__":
    main()
