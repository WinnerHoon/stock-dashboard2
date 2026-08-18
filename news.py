# -*- coding: utf-8 -*-
"""
뉴스 수집

국내 (우선순위 순)
  1. 네이버 뉴스 검색 API — NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 시크릿이 있을 때
  2. 구글 뉴스 RSS — 키 불필요. 위가 없거나 실패하면 자동으로 이쪽을 씁니다
해외
  yfinance → 실패 시 구글 뉴스 RSS (영문)

어떤 경로든 실패하면 그 종목만 건너뜁니다. 사이트 빌드는 멈추지 않습니다.
"""

import os
import re
import urllib.parse
import xml.etree.ElementTree as ET
from html import unescape

NAVER_URL = "https://openapi.naver.com/v1/search/news.json"
GNEWS_URL = "https://news.google.com/rss/search"
TAG = re.compile(r"<[^>]+>")

# 장기 투자에 의미 없는 단순 시황 기사 제외
NOISE = re.compile(r"(상한가|하한가|급등|급락|특징주|장중|개장|마감|시황|테마주|"
                   r"오늘의 주식|증시 브리핑)")


def _clean(s):
    """HTML 태그 제거 + 엔티티 복원"""
    return unescape(TAG.sub("", unescape(s or ""))).strip()


def naver_news(query, limit=3, keep_noise=False):
    """국내 1순위 — 네이버 검색 API (키 필요)"""
    cid, sec = os.getenv("NAVER_CLIENT_ID"), os.getenv("NAVER_CLIENT_SECRET")
    if not (cid and sec):
        return []
    import requests
    r = requests.get(NAVER_URL, timeout=15,
                     headers={"X-Naver-Client-Id": cid, "X-Naver-Client-Secret": sec},
                     params={"query": query, "display": limit * 4, "sort": "date"})
    r.raise_for_status()
    out = []
    for it in r.json().get("items", []):
        title = _clean(it.get("title"))
        if not title or (not keep_noise and NOISE.search(title)):
            continue
        out.append({"title": title,
                    "url": it.get("originallink") or it.get("link", ""),
                    "publisher": "네이버뉴스",
                    "summary": _clean(it.get("description"))[:300],
                    "published": it.get("pubDate", "")})
        if len(out) >= limit:
            break
    return out


def google_news(query, limit=3, lang="ko", keep_noise=False):
    """키 불필요 폴백 — 구글 뉴스 RSS"""
    import requests
    params = ({"q": query, "hl": "ko", "gl": "KR", "ceid": "KR:ko"} if lang == "ko"
              else {"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"})
    r = requests.get(GNEWS_URL + "?" + urllib.parse.urlencode(params), timeout=15,
                     headers={"User-Agent": "Mozilla/5.0 (compatible; stock-dashboard/1.0)"})
    r.raise_for_status()
    root = ET.fromstring(r.content)
    out = []
    for item in root.iterfind(".//item"):
        title = _clean(item.findtext("title") or "")
        if not title or (not keep_noise and NOISE.search(title)):
            continue
        src = item.findtext("{http://news.google.com/}source") or ""
        if not src and " - " in title:
            title, _, src = title.rpartition(" - ")
        out.append({"title": title.strip(),
                    "url": item.findtext("link") or "",
                    "publisher": src.strip() or "Google News",
                    "summary": _clean(item.findtext("description") or "")[:300],
                    "published": item.findtext("pubDate") or ""})
        if len(out) >= limit:
            break
    return out


def yahoo_news(ticker, limit=3):
    """해외 1순위 — yfinance"""
    import yfinance as yf
    out = []
    for it in (yf.Ticker(ticker).news or [])[:limit]:
        c = it.get("content", it) or {}
        url = ""
        for k in ("canonicalUrl", "clickThroughUrl"):
            v = c.get(k)
            if isinstance(v, dict) and v.get("url"):
                url = v["url"]
                break
        prov = c.get("provider")
        title = c.get("title") or it.get("title") or ""
        if title:
            out.append({"title": title,
                        "url": url or it.get("link", ""),
                        "publisher": prov.get("displayName") if isinstance(prov, dict) else "",
                        "summary": (c.get("summary") or "")[:300],
                        "published": c.get("pubDate") or ""})
    return out


def _try(label, fn):
    try:
        got = fn()
        if got:
            print("  · " + label + " " + str(len(got)) + "건")
        return got
    except Exception as e:
        print("  ! " + label + " 실패: " + type(e).__name__ + ": " + str(e)[:80])
        return []


def collect(consolidated, limit=3):
    """보유 종목별 뉴스. 지수추종 ETF 는 개별 뉴스가 무의미하므로 제외."""
    news = {}
    has_naver = bool(os.getenv("NAVER_CLIENT_ID") and os.getenv("NAVER_CLIENT_SECRET"))
    if not has_naver:
        print("  · 네이버 키 없음 → 국내 뉴스는 구글 뉴스 RSS 사용")

    for m in consolidated:
        if m.get("is_etf"):
            continue
        tk, nm = m["ticker"], m["name"]

        if m["market"] == "KR":
            items = _try(nm + " 네이버", lambda: naver_news(nm, limit)) if has_naver else []
            if not items:
                items = _try(nm + " 구글", lambda: google_news(nm + " 주가", limit, "ko"))
        else:
            items = _try(nm + " 야후", lambda: yahoo_news(tk, limit))
            if not items:
                items = _try(nm + " 구글", lambda: google_news(tk + " stock", limit, "en"))

        if items:
            news[tk] = {"name": nm, "items": items}
    return news


# ── 시장 전반 뉴스 ─────────────────────────────────────────
# 보유 종목과 무관하게 시장 흐름을 훑기 위한 주제별 검색어입니다.
MARKET_TOPICS = [
    ("증시 시황", ["코스피 마감", "뉴욕증시 마감"]),
    ("금리·연준·물가", ["연준 기준금리", "한국은행 기준금리", "소비자물가 상승률"]),
    ("환율", ["원달러 환율"]),
    ("반도체·AI", ["반도체 업황", "AI 반도체"]),
]


def collect_market(limit=4):
    """시장 전반 뉴스를 주제별로 모읍니다 (보유 종목과 무관).

    종목 뉴스와 달리 '마감·시황' 같은 단어를 걸러내지 않습니다 —
    시장 뉴스에서는 그게 오히려 핵심이기 때문입니다.
    """
    has_naver = bool(os.getenv("NAVER_CLIENT_ID") and os.getenv("NAVER_CLIENT_SECRET"))
    out, seen = [], set()
    for topic, queries in MARKET_TOPICS:
        items = []
        for q in queries:
            got = []
            if has_naver:
                got = _try("시장 " + topic + " · " + q,
                           lambda q=q: naver_news(q, limit, keep_noise=True))
            if not got:
                got = _try("시장 " + topic + " · " + q + " (구글)",
                           lambda q=q: google_news(q, limit, keep_noise=True))
            for it in got:
                key = (it.get("title") or "")[:35]
                if not key or key in seen:
                    continue
                seen.add(key)
                items.append(it)
            if len(items) >= limit:
                break
        if items:
            out.append({"topic": topic, "items": items[:limit]})
    print("  · 시장 뉴스 " + str(sum(len(t["items"]) for t in out)) + "건")
    return out
