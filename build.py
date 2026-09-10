#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
아침 주식 브리핑 — 빌드 스크립트
GitHub Actions 에서 매일 아침 실행됩니다.

  portfolio.json 읽기
    → FinanceDataReader / yfinance 로 시세 수집
    → 뉴스 수집 (네이버 뉴스 API + yfinance)
    → dist/index.html (사이트) + dist/data.json 생성
    → 카카오톡 발송 (선택)

로컬 테스트:
  python build.py --mock      네트워크 없이 가짜 데이터
  python build.py --no-kakao  카톡 발송 없이 사이트만
"""

import argparse
import json
import math
import os
import random
import sys
import traceback
from datetime import datetime, timedelta, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(BASE, "dist")
CONFIG = os.path.join(BASE, "portfolio.json")
KST = timezone(timedelta(hours=9))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def log(m):
    print(f"[{datetime.now(KST):%H:%M:%S}] {m}", flush=True)


def pct(new, old):
    try:
        if old in (None, 0) or new is None:
            return None
        return (float(new) - float(old)) / float(old) * 100.0
    except Exception:
        return None


def safe(fn, default=None, label=""):
    try:
        return fn()
    except Exception as e:
        log(f"  ! {label} 실패: {type(e).__name__}: {str(e)[:110]}")
        return default


ETF_HINTS = ("ETF", "TIGER", "KODEX", "ACE ", "RISE ", "SOL ", "PLUS ", "KOSEF",
             "ARIRANG", "HANARO", "INDXX", "S&P", "NASDAQ", "다우존스")


def is_etf(name, ticker=""):
    return any(h.upper() in (name or "").upper() for h in ETF_HINTS)


# ────────────────────────────────────────────────────────────
# 시세 수집
# ────────────────────────────────────────────────────────────

def _lookback(c, n):
    if len(c) < 2:
        return None
    v = pct(c[-1], c[-min(n, len(c))])
    return round(v, 2) if v is not None else None


def summarize(closes):
    closes = [float(c) for c in closes
              if c is not None and not (isinstance(c, float) and math.isnan(c))]
    if not closes:
        return None
    cur = closes[-1]
    prev = closes[-2] if len(closes) >= 2 else cur
    yr = closes[-252:] if len(closes) >= 252 else closes
    hi, lo = max(yr), min(yr)
    return {
        "price": round(cur, 4),
        "prev_close": round(prev, 4),
        "chg": round(pct(cur, prev), 2) if pct(cur, prev) is not None else None,
        "w1": _lookback(closes, 6),
        "m1": _lookback(closes, 22),
        "m3": _lookback(closes, 63),
        "m6": _lookback(closes, 126),
        "y1": _lookback(closes, 252),
        "high_52w": round(hi, 4),
        "low_52w": round(lo, 4),
        "from_high": round(pct(cur, hi), 2) if pct(cur, hi) is not None else None,
        "band_pos": round((cur - lo) / (hi - lo) * 100, 1) if hi > lo else None,
        "ma60": round(sum(closes[-60:]) / len(closes[-60:]), 2) if len(closes) >= 20 else None,
        "ma200": round(sum(closes[-200:]) / len(closes[-200:]), 2) if len(closes) >= 100 else None,
        "spark": [round(c, 4) for c in closes[-120:]],
    }


def fetch_kr(ticker, days):
    """국내 — FinanceDataReader (KRX 계정 불필요)"""
    import FinanceDataReader as fdr
    start = (datetime.now(KST) - timedelta(days=days)).strftime("%Y-%m-%d")
    df = fdr.DataReader(ticker, start)
    if df is None or df.empty:
        return None
    col = "Close" if "Close" in df.columns else df.columns[-1]
    return summarize(df[col].dropna().tolist())


def fetch_us(ticker, days):
    """해외 — yfinance 우선, 실패 시 FinanceDataReader"""
    try:
        import yfinance as yf
        df = yf.Ticker(ticker).history(period=f"{max(days, 30)}d", auto_adjust=False)
        if df is not None and not df.empty:
            return summarize(df["Close"].dropna().tolist())
    except Exception as e:
        log(f"  · yfinance {ticker} 실패 → FDR 재시도 ({type(e).__name__})")
    import FinanceDataReader as fdr
    start = (datetime.now(KST) - timedelta(days=days)).strftime("%Y-%m-%d")
    df = fdr.DataReader(ticker, start)
    if df is None or df.empty:
        return None
    return summarize(df["Close"].dropna().tolist())


def fetch_pykrx_extra(ticker):
    """pykrx 보조 지표 — KRX_ID/KRX_PW 시크릿이 있을 때만 동작"""
    if not (os.getenv("KRX_ID") and os.getenv("KRX_PW")):
        return None
    from pykrx import stock
    today = datetime.now(KST).strftime("%Y%m%d")
    start = (datetime.now(KST) - timedelta(days=10)).strftime("%Y%m%d")
    df = stock.get_market_fundamental(start, today, ticker)
    if df is None or df.empty:
        return None
    r = df.iloc[-1]
    return {"per": float(r.get("PER", 0)) or None,
            "pbr": float(r.get("PBR", 0)) or None,
            "div_yield": float(r.get("DIV", 0)) or None}


# ────────────────────────────────────────────────────────────
# 모의 데이터
# ────────────────────────────────────────────────────────────

def mock(base):
    random.seed(abs(hash(str(base))) % 9999)
    p, out = float(base), []
    for _ in range(260):
        p *= (1 + random.uniform(-0.022, 0.024))
        out.append(p)
    return summarize(out)


# ────────────────────────────────────────────────────────────
# 조립
# ────────────────────────────────────────────────────────────

FNG_URL = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
FNG_RATING = {"extreme fear": "극도의 공포", "fear": "공포", "neutral": "중립",
              "greed": "탐욕", "extreme greed": "극도의 탐욕"}


def fetch_fear_greed():
    """CNN 공포·탐욕 지수 (0=극도의 공포, 100=극도의 탐욕)"""
    import requests
    ua = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
    r = requests.get(FNG_URL, timeout=15, headers={"User-Agent": ua})
    r.raise_for_status()
    g = r.json().get("fear_and_greed") or {}
    if g.get("score") is None:
        return None

    def _r(x):
        return round(float(x)) if x is not None else None

    return {"score": _r(g.get("score")),
            "rating": FNG_RATING.get(str(g.get("rating") or "").lower(),
                                     g.get("rating") or "-"),
            "prev": _r(g.get("previous_close")),
            "w1": _r(g.get("previous_1_week")),
            "m1": _r(g.get("previous_1_month")),
            "y1": _r(g.get("previous_1_year"))}


_DPS_CACHE = {}


def fetch_dps(ticker, market):
    """최근 12개월 주당배당금(현지통화). 조회 실패나 무배당이면 0."""
    key = (ticker, market)
    if key in _DPS_CACHE:
        return _DPS_CACHE[key]
    val = 0.0
    try:
        import yfinance as yf
        sym = ticker + ".KS" if market == "KR" else ticker
        ser = yf.Ticker(sym).dividends
        if ser is not None and len(ser):
            cut = (datetime.now(KST) - timedelta(days=365)).strftime("%Y-%m-%d")
            val = float(sum(float(x) for dt, x in ser.items() if str(dt)[:10] >= cut))
    except Exception as e:
        log(f"  · {ticker} 배당 조회 실패 ({type(e).__name__})")
    _DPS_CACHE[key] = val
    return val


def build(cfg, use_mock=False):
    s = cfg.get("settings", {})
    days = int(s.get("history_days", 400))

    # 거래 원장이 있으면 그걸로 보유종목·현금을 계산합니다.
    # 없으면 예전처럼 portfolio.json 의 holdings 를 그대로 씁니다.
    import ledger
    _led = ledger.build_holdings(os.path.join(BASE, "transactions.json"))
    led_hold, led_cash, led_realized, led_warn = _led[:4]
    led_events = _led[4] if len(_led) > 4 else []
    if led_hold:
        log(f"거래 원장에서 보유 {len(led_hold)}건 계산")
        for m in led_warn:
            log(f"  ⚠ {m}")
    holdings_src = led_hold if led_hold else cfg.get("holdings", [])

    prev = None
    p = os.path.join(DIST, "data.json")
    if os.path.exists(p):
        prev = safe(lambda: json.load(open(p, encoding="utf-8")), None, "이전 데이터")
    prev_pos = {f'{x["ticker"]}|{x.get("broker","")}': x
                for x in (prev or {}).get("positions", [])}

    # 지수 · 환율
    log("지수·환율")
    indices, fx = [], None
    for i in cfg.get("indices", []):
        code, name = i["code"], i["name"]
        getter = fetch_us if (i.get("source") or "kr").lower() == "us" else fetch_kr
        d = mock(1400 if "USD" in code else 2800) if use_mock else \
            safe(lambda c=code, fn=getter: fn(c, days), None, f"지수 {name}")
        if d:
            indices.append({"code": code, "name": name, "unit": i.get("unit"),
                            "group": i.get("group") or "지수", **d})
            if code.upper().replace("/", "") == "USDKRW":
                fx = d["price"]
    if not fx:
        fx = float(s.get("fallback_fx", 1430))
        log(f"  ! 환율 조회 실패 → {fx}원으로 가정")

    # 보유 종목
    log("보유 종목")
    positions = []
    for h in holdings_src:
        mk = h.get("market", "KR").upper()
        tk, nm = str(h["ticker"]), h.get("name", h["ticker"])
        log(f"  - {nm} ({tk})")
        d = mock(h.get("avg_price", 100)) if use_mock else \
            safe(lambda: fetch_kr(tk, days) if mk == "KR" else fetch_us(tk, days), None, nm)
        if not d:
            positions.append({"market": mk, "ticker": tk, "name": nm, "error": "시세 조회 실패",
                              "shares": h.get("shares"), "avg_price": h.get("avg_price"),
                              "broker": h.get("broker", "")})
            continue
        sh, avg = float(h.get("shares") or 0), float(h.get("avg_price") or 0)
        rate = 1.0 if mk == "KR" else float(fx)
        val, cost = d["price"] * sh, avg * sh
        pos = {
            "market": mk, "ticker": tk, "name": nm, "broker": h.get("broker", ""),
            "currency": "KRW" if mk == "KR" else "USD",
            "shares": sh, "avg_price": avg,
            "market_value": round(val, 2), "cost": round(cost, 2),
            "roi_pct": round(pct(d["price"], avg), 2) if avg else None,
            "market_value_krw": round(val * rate), "cost_krw": round(cost * rate),
            "pl_krw": round((val - cost) * rate), **d,
        }
        old = prev_pos.get(f'{tk}|{h.get("broker","")}')
        if old and old.get("roi_pct") is not None and pos["roi_pct"] is not None:
            pos["roi_delta"] = round(pos["roi_pct"] - old["roi_pct"], 2)
        dps = 0.0 if use_mock else (safe(lambda: fetch_dps(tk, mk), 0.0, nm + " 배당") or 0.0)
        pos["dps"] = round(dps, 4)
        pos["div_annual"] = round(dps * sh, 2)
        pos["div_annual_krw"] = round(dps * sh * rate)
        positions.append(pos)

    ok = [x for x in positions if "error" not in x]
    tv = sum(x["market_value_krw"] for x in ok)
    tc = sum(x["cost_krw"] for x in ok)

    # 종목 합산 (증권사 분산 통합)
    merged = {}
    for x in ok:
        m = merged.setdefault(x["ticker"], {
            "ticker": x["ticker"], "name": x["name"], "market": x["market"],
            "currency": x["currency"], "price": x["price"], "chg": x.get("chg"),
            "is_etf": is_etf(x["name"], x["ticker"]),
            "m3": x.get("m3"), "y1": x.get("y1"), "from_high": x.get("from_high"),
            "band_pos": x.get("band_pos"), "ma200": x.get("ma200"), "spark": x.get("spark"),
            "shares": 0.0, "cost": 0.0, "market_value_krw": 0, "cost_krw": 0, "brokers": [],
            "dps": x.get("dps", 0.0), "div_annual": 0.0, "div_annual_krw": 0,
        })
        m["shares"] += x["shares"]
        m["cost"] += x["cost"]
        m["market_value_krw"] += x["market_value_krw"]
        m["cost_krw"] += x["cost_krw"]
        m["div_annual"] += x.get("div_annual", 0.0)
        m["div_annual_krw"] += x.get("div_annual_krw", 0)
        if x.get("broker"):
            m["brokers"].append(f'{x["broker"]} {x["shares"]:,.0f}주')

    consolidated = []
    for m in merged.values():
        m["avg_price"] = round(m["cost"] / m["shares"], 2) if m["shares"] else 0
        m["pl_krw"] = round(m["market_value_krw"] - m["cost_krw"])
        m["roi_pct"] = round(pct(m["price"], m["avg_price"]), 2) if m["avg_price"] else None
        m["weight_pct"] = round(m["market_value_krw"] / tv * 100, 2) if tv else 0
        m["div_yield_pct"] = (round(m["dps"] / m["price"] * 100, 2)
                              if (m["price"] and m["dps"]) else None)
        m["split"] = len(m["brokers"]) > 1
        consolidated.append(m)
    consolidated.sort(key=lambda x: -x["market_value_krw"])

    def share(f):
        v = sum(m["market_value_krw"] for m in consolidated if f(m))
        return round(v / tv * 100, 1) if tv else 0

    allocation = {
        "국내": share(lambda m: m["market"] == "KR"),
        "해외": share(lambda m: m["market"] == "US"),
        "ETF": share(lambda m: m["is_etf"]),
        "개별주": share(lambda m: not m["is_etf"]),
        "by_broker": {},
    }
    for x in ok:
        b = x.get("broker") or "미지정"
        allocation["by_broker"][b] = round(
            allocation["by_broker"].get(b, 0) + x["market_value_krw"])

    # 현금 잔고 (거래 원장이 있을 때만)
    cash = ledger.summarize_cash(led_cash, float(fx)) if led_cash else None

    totals = {
        "market_value_krw": round(tv), "cost_krw": round(tc), "pl_krw": round(tv - tc),
        "roi_pct": round((tv - tc) / tc * 100, 2) if tc else None,
        "usdkrw": round(float(fx), 2),
        "positions_count": len(consolidated), "failed_count": len(positions) - len(ok),
        "div_annual_krw": round(sum(m.get("div_annual_krw", 0) for m in consolidated)),
    }
    if cash:
        totals["cash_krw"] = cash["total_krw"]
        totals["net_worth_krw"] = round(tv + cash["total_krw"])
        log(f'현금 {cash["total_krw"]:,}원 (원화 {cash["KRW"]:,} / 달러 {cash["USD"]:,.2f})')
    if led_realized:
        totals["realized"] = {k: round(v, 2) for k, v in led_realized.items()}
    today = os.getenv("FAKE_DATE") or datetime.now(KST).strftime("%Y-%m-%d")
    # 전일 대비 기준: dist/history.json 에서 오늘 이전 날짜의 마지막 스냅샷을 씁니다.
    # 직전 빌드는 같은 날일 수 있어 그대로 쓰면 '전일 대비'가 되지 않습니다.
    pv, pv_date = None, None
    hp = os.path.join(DIST, "history.json")
    if os.path.exists(hp):
        try:
            older = [sn for sn in json.load(open(hp, encoding="utf-8")).get("snapshots", [])
                     if sn.get("date") and sn["date"] < today and sn.get("total")]
            if older:
                pv, pv_date = older[-1]["total"], older[-1]["date"]
        except Exception as e:
            log(f"  ! history.json 읽기 실패: {type(e).__name__}")
    if not pv:
        pv = (prev or {}).get("totals", {}).get("market_value_krw")
        pv_date = (prev or {}).get("date")
    if pv:
        totals["prev_total_krw"] = round(pv)
        totals["prev_base_date"] = pv_date
        totals["delta_krw"] = round(tv - pv)
        totals["delta_pct"] = round(pct(tv, pv), 2)

    # 실현손익 (매도 차익 + 배당 − 수수료) — 기간·연도별
    realized_sum = (ledger.summarize_realized(led_events, float(fx), today)
                    if led_events else None)
    if realized_sum:
        log(f'실현손익 {realized_sum["windows"]["all"]["krw_total"]:,}원 '
            f'({realized_sum["windows"]["all"]["count"]}건)')

    # 시장 심리 (CNN 공포·탐욕 지수)
    fng = None if use_mock else safe(fetch_fear_greed, None, "공포·탐욕 지수")

    # 뉴스 + 번역
    log("뉴스 수집")
    if use_mock:
        news = {m["ticker"]: {"name": m["name"], "items": [{
            "title": f"[Mock] {m['name']} reports record quarterly revenue growth",
            "url": "https://example.com", "publisher": "MockWire",
            "summary": "Placeholder summary for offline rendering test.", "published": ""}]}
            for m in consolidated[:4] if not m["is_etf"]}
        for v in news.values():
            for n in v["items"]:
                n["title_ko"] = "[모의] " + v["name"] + " 분기 매출 사상 최대 기록"
        market_news = []
    else:
        import news as news_mod
        news = news_mod.collect(consolidated, int(s.get("news_per_ticker", 3)))
        market_news = safe(lambda: news_mod.collect_market(int(s.get("market_news", 4))),
                           [], "시장 뉴스")
        if news:
            log("뉴스 번역")
            import translate
            news = translate.apply_to_news(news)

    return {
        "generated_at": datetime.now(KST).isoformat(timespec="seconds"),
        "date": today,
        "owner": cfg.get("owner", ""), "style": s.get("style", "long_term"),
        "mock": use_mock, "totals": totals, "allocation": allocation, "cash": cash,
        "indices": indices, "consolidated": consolidated, "positions": positions,
        "news": news, "market_news": market_news, "fear_greed": fng,
        "realized": realized_sum,
        "prev_date": (prev or {}).get("date"),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--no-kakao", action="store_true")
    a = ap.parse_args()
    try:
        cfg = json.load(open(CONFIG, encoding="utf-8"))
        data = build(cfg, a.mock)
        os.makedirs(DIST, exist_ok=True)

        import history
        import render
        log("이력 갱신")
        hist, day_diffs = history.update(DIST, data)
        import ledger as _lg
        data["twr"] = safe(lambda: _lg.summarize_twr(
            hist.get("snapshots", []),
            _lg.load(os.path.join(BASE, "transactions.json")),
            data["date"]), None, "운용 성과(TWR)")

        json.dump(data, open(os.path.join(DIST, "data.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        for name, html in render.render_all(data, hist, day_diffs).items():
            open(os.path.join(DIST, name), "w", encoding="utf-8").write(html)
            log(f"  · {name} ({len(html):,} bytes)")
        open(os.path.join(DIST, ".nojekyll"), "w").write("")

        t = data["totals"]
        log(f"평가 {t['market_value_krw']:,}원 / 손익 {t['pl_krw']:+,}원 ({t['roi_pct']}%)")
        if t["failed_count"]:
            log(f"⚠ {t['failed_count']}개 종목 시세 실패")

        if not a.no_kakao and not a.mock:
            import kakao
            kakao.send_brief(data)
    except Exception:
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
