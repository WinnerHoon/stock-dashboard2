# -*- coding: utf-8 -*-
"""
거래 원장 → 보유종목 · 현금 잔고 계산

transactions.json 의 거래를 날짜순으로 재생해서
  - 종목별 (증권사별) 보유수량 / 이동평균 평단
  - 증권사별 원화 · 달러 현금 잔고
  - 실현손익
을 만들어 냅니다.

거래 종류
  open      기초잔고     ticker, shares, price, broker   (현금에 영향 없음)
  buy       매수         ticker, shares, price, fee, broker
  sell      매도         ticker, shares, price, fee, broker
  deposit   입금         currency, amount, broker
  withdraw  출금         currency, amount, broker
  fx        환전         from, to, amount, rate, broker
  dividend  배당         currency, amount, broker, (ticker)
  fee       기타수수료   currency, amount, broker
"""

import json
import os
from collections import defaultdict
from datetime import date

TYPES = ("open", "buy", "sell", "deposit", "withdraw", "fx", "dividend", "fee")


def load(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    tx = d.get("transactions", d if isinstance(d, list) else [])
    return sorted(tx, key=lambda t: (t.get("date", ""), t.get("seq", 0)))


def _f(v):
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def replay(tx):
    """거래를 순서대로 재생. (보유종목, 현금, 실현손익, 경고) 반환"""
    pos = {}                                   # (ticker, broker) -> dict
    cash = defaultdict(lambda: defaultdict(float))   # broker -> currency -> amount
    realized = defaultdict(float)              # ticker -> 실현손익 (현지통화)
    warn = []
    events = []                                # 실현 이벤트 (매도·배당·수수료)

    for i, t in enumerate(tx):
        ty = t.get("type")
        br = t.get("broker") or "미지정"
        if ty not in TYPES:
            warn.append(f"{i+1}번째: 알 수 없는 거래유형 {ty!r}")
            continue

        if ty in ("open", "buy", "sell"):
            tk = str(t.get("ticker") or "")
            if not tk:
                warn.append(f"{i+1}번째: ticker 없음")
                continue
            key = (tk, br)
            p = pos.setdefault(key, {
                "ticker": tk, "broker": br,
                "market": (t.get("market") or "KR").upper(),
                "name": t.get("name") or tk,
                "shares": 0.0, "avg_price": 0.0,
            })
            if t.get("name"):
                p["name"] = t["name"]
            if t.get("market"):
                p["market"] = t["market"].upper()

            qty, px, fee = _f(t.get("shares")), _f(t.get("price")), _f(t.get("fee"))
            cur = "KRW" if p["market"] == "KR" else "USD"

            if ty in ("open", "buy"):
                total_cost = p["avg_price"] * p["shares"] + px * qty + fee
                p["shares"] += qty
                p["avg_price"] = (total_cost / p["shares"]) if p["shares"] else 0.0
                if ty == "buy":
                    cash[br][cur] -= px * qty + fee
            else:                                     # sell
                if qty > p["shares"] + 1e-9:
                    warn.append(f'{i+1}번째: {p["name"]} 보유 {p["shares"]:g}주보다 많은 {qty:g}주 매도')
                    qty = p["shares"]
                gain = (px - p["avg_price"]) * qty - fee
                realized[tk] += gain
                events.append({"date": t.get("date"), "seq": t.get("seq") or i,
                               "type": "sell", "market": p["market"], "currency": cur,
                               "ticker": tk, "name": p["name"], "broker": br,
                               "amount": round(gain, 2), "shares": qty,
                               "price": px, "avg_price": p["avg_price"]})
                p["shares"] -= qty
                cash[br][cur] += px * qty - fee
                if p["shares"] <= 1e-9:
                    p["shares"] = 0.0                 # 평단은 남겨둠 (재매수 시 새로 계산)

        elif ty == "deposit":
            cash[br][(t.get("currency") or "KRW").upper()] += _f(t.get("amount"))
        elif ty == "withdraw":
            cash[br][(t.get("currency") or "KRW").upper()] -= _f(t.get("amount"))
        elif ty == "dividend":
            dc = (t.get("currency") or "KRW").upper()
            cash[br][dc] += _f(t.get("amount"))
            events.append({"date": t.get("date"), "seq": t.get("seq") or i,
                           "type": "dividend", "market": "KR" if dc == "KRW" else "US",
                           "currency": dc, "ticker": t.get("ticker") or "",
                           "name": t.get("name") or "", "broker": br,
                           "amount": round(_f(t.get("amount")), 2)})
        elif ty == "fee":
            fc = (t.get("currency") or "KRW").upper()
            cash[br][fc] -= _f(t.get("amount"))
            events.append({"date": t.get("date"), "seq": t.get("seq") or i,
                           "type": "fee", "market": "KR" if fc == "KRW" else "US",
                           "currency": fc, "ticker": t.get("ticker") or "",
                           "name": t.get("name") or "", "broker": br,
                           "amount": -round(_f(t.get("amount")), 2)})

        elif ty == "fx":
            src = (t.get("from") or "KRW").upper()
            dst = (t.get("to") or "USD").upper()
            amt = _f(t.get("amount"))            # 파는 통화 기준 금액
            rate = _f(t.get("rate"))             # 항상 원/달러
            if rate <= 0:
                warn.append(f"{i+1}번째: 환전 rate 가 없습니다")
                continue
            got = amt / rate if (src == "KRW" and dst == "USD") else \
                  amt * rate if (src == "USD" and dst == "KRW") else None
            if got is None:
                warn.append(f"{i+1}번째: 지원하지 않는 환전 {src}→{dst}")
                continue
            cash[br][src] -= amt
            cash[br][dst] += got

    holdings = [p for p in pos.values() if p["shares"] > 1e-9]
    holdings.sort(key=lambda p: (p["market"], p["ticker"]))
    return holdings, cash, dict(realized), warn, events


def summarize_cash(cash, fx):
    """증권사별 현금 → 합계(원화 환산) 요약"""
    by_broker, krw, usd = {}, 0.0, 0.0
    for br, cur in cash.items():
        k, u = round(cur.get("KRW", 0.0)), round(cur.get("USD", 0.0), 2)
        if abs(k) < 1 and abs(u) < 0.01:
            continue
        by_broker[br] = {"KRW": k, "USD": u, "krw_total": round(k + u * fx)}
        krw += k
        usd += u
    return {
        "by_broker": by_broker,
        "KRW": round(krw),
        "USD": round(usd, 2),
        "total_krw": round(krw + usd * fx),
    }


def build_holdings(path):
    """build.py 가 쓰는 진입점. portfolio.json 의 holdings 와 같은 형태로 반환."""
    tx = load(path)
    if not tx:
        return None, None, None, [], []
    holdings, cash, realized, warn, events = replay(tx)
    out = [{"market": p["market"], "ticker": p["ticker"], "name": p["name"],
            "shares": round(p["shares"], 6), "avg_price": round(p["avg_price"], 4),
            "broker": p["broker"]} for p in holdings]
    return out, cash, realized, warn, events


def _months_ago(ds, n):
    """YYYY-MM-DD 에서 n개월 전 날짜 (없는 날짜는 그 달의 마지막 날로 보정)"""
    y, m, dd = int(ds[0:4]), int(ds[5:7]), int(ds[8:10])
    m -= n
    while m <= 0:
        m += 12
        y -= 1
    while dd > 0:
        try:
            return date(y, m, dd).isoformat()
        except ValueError:
            dd -= 1
    return f"{y:04d}-{m:02d}-01"


def summarize_realized(events, fx, today):
    """실현손익 요약 — 누적·기간별·연도별. 국내(원화)/해외(달러)를 나눠서 집계합니다.

    해외분의 원화 환산은 매매 당시가 아니라 '현재 환율' 기준입니다 (과거 환율 미보관).
    """
    rate = float(fx or 0)

    def bucket():
        return {"KRW": 0.0, "USD": 0.0,
                "sell_KRW": 0.0, "sell_USD": 0.0,
                "dividend_KRW": 0.0, "dividend_USD": 0.0,
                "fee_KRW": 0.0, "fee_USD": 0.0, "count": 0}

    def add(b, e):
        cur = e.get("currency") or "KRW"
        amt = _f(e.get("amount"))
        b[cur] = b.get(cur, 0.0) + amt
        key = str(e.get("type")) + "_" + cur
        if key in b:
            b[key] += amt
        b["count"] += 1

    def close(b):
        out = {k: (round(v) if k.endswith("KRW") else round(v, 2))
               for k, v in b.items() if k != "count"}
        out["count"] = b["count"]
        out["krw_total"] = round(b["KRW"] + b["USD"] * rate)
        return out

    windows = {}
    ball = bucket()
    for e in events:
        add(ball, e)
    windows["all"] = close(ball)
    windows["all"]["since"] = None
    for key, months in (("m1", 1), ("m3", 3), ("y1", 12)):
        since = _months_ago(today, months)
        b = bucket()
        for e in events:
            if (e.get("date") or "") >= since:
                add(b, e)
        windows[key] = close(b)
        windows[key]["since"] = since

    years = {}
    for e in events:
        y = (e.get("date") or "")[:4]
        if not y:
            continue
        years.setdefault(y, bucket())
        add(years[y], e)
    by_year = []
    for y in sorted(years, reverse=True):
        row = close(years[y])
        row["year"] = y
        by_year.append(row)

    ev = sorted(events, key=lambda e: ((e.get("date") or ""), e.get("seq") or 0),
                reverse=True)[:120]
    return {"fx": round(rate, 2) if rate else None, "today": today,
            "windows": windows, "by_year": by_year, "events": ev}
