# -*- coding: utf-8 -*-
"""
뉴스 수집
  국내 — 네이버 뉴스 검색 API (NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 시크릿 필요)
  해외 — yfinance

시크릿이 없으면 국내 뉴스는 건너뜁니다. 사이트 빌드는 정상 진행됩니다.
"""

import os
import re
from datetime import datetime

NAVER_URL = "https://openapi.naver.com/v1/search/news.json"
TAG = re.compile(r"<[^>]+>")


def _clean(s):
    return (TAG.sub("", s or "")
            .replace("&quot;", '"').replace("&amp;", "&")
            .replace("&lt;", "<").replace("&gt;", ">").replace("&apos;", "'").strip())


def naver_news(query, limit=3):
    cid, sec = os.getenv("NAVER_CLIENT_ID"), os.getenv("NAVER_CLIENT_SECRET")
    if not (cid and sec):
        return []
    import requests
    r = requests.get(NAVER_URL,
                     headers={"X-Naver-Client-Id": cid, "X-Naver-Client-Secret": sec},
                     params={"query": query, "display": limit * 3, "sort": "date"},
                     timeout=15)
    r.raise_for_status()
    out = []
    for it in r.json().get("items", [])[:limit * 3]:
        title = _clean(it.get("title"))
        # 장기 투자에 무의미한 단순 시황 기사 제외
        if re.search(r"(상한가|하한가|급등|급락|특징주|장중|개장|마감|시황)", title):
            continue
        out.append({"title": title,
                    "url": it.get("originallink") or it.get("link", ""),
                    "publisher": "네이버뉴스",
                    "summary": _clean(it.get("description"))[:300],
                    "published": it.get("pubDate", "")})
        if len(out) >= limit:
            break
    return out


def yahoo_news(ticker, limit=3):
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


def collect(consolidated, limit=3):
    """보유 종목별 뉴스. 지수추종 ETF는 개별 뉴스가 무의미하므로 제외."""
    news = {}
    for m in consolidated:
        if m.get("is_etf"):
            continue
        tk, nm = m["ticker"], m["name"]
        try:
            items = naver_news(nm, limit) if m["market"] == "KR" else yahoo_news(tk, limit)
            if items:
                news[tk] = {"name": nm, "items": items}
        except Exception as e:
            print(f"  ! 뉴스 {nm}: {type(e).__name__}: {str(e)[:90]}")
    return news
