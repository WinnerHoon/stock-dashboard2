# -*- coding: utf-8 -*-
"""
일별 변화 이력 관리
dist/history.json 에 하루 한 건씩 스냅샷을 누적합니다.
같은 날 여러 번 빌드하면 그 날짜 항목을 최신값으로 덮어씁니다.
"""

import json
import os

KEEP_DAYS = 400          # 보관 기간
FILE = "history.json"


def path(dist):
    return os.path.join(dist, FILE)


def load(dist):
    p = path(dist)
    if not os.path.exists(p):
        return {"snapshots": []}
    try:
        d = json.load(open(p, encoding="utf-8"))
        if isinstance(d.get("snapshots"), list):
            return d
    except Exception as e:
        print(f"  ! history.json 읽기 실패, 새로 시작: {type(e).__name__}")
    return {"snapshots": []}


def snapshot(data):
    """오늘치 한 건 만들기"""
    t = data["totals"]
    return {
        "date": data["date"],
        "at": data["generated_at"],
        "total": t["market_value_krw"],
        "cost": t["cost_krw"],
        "pl": t["pl_krw"],
        "roi": t["roi_pct"],
        "fx": t["usdkrw"],
        "alloc": {k: v for k, v in data["allocation"].items() if k != "by_broker"},
        "indices": {i["name"]: i["price"] for i in data.get("indices", [])},
        "positions": {
            m["ticker"]: {
                "name": m["name"], "w": m["weight_pct"], "roi": m["roi_pct"],
                "price": m["price"], "val": m["market_value_krw"], "pl": m["pl_krw"],
            } for m in data.get("consolidated", [])
        },
    }


def update(dist, data):
    """이력 갱신 후 (전체 이력, 일별 변화 리스트) 반환"""
    h = load(dist)
    snaps = [s for s in h["snapshots"] if s.get("date") != data["date"]]
    snaps.append(snapshot(data))
    snaps.sort(key=lambda s: s["date"])
    snaps = snaps[-KEEP_DAYS:]
    h["snapshots"] = snaps

    os.makedirs(dist, exist_ok=True)
    json.dump(h, open(path(dist), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"  · 이력 {len(snaps)}일치 저장")
    return h, diffs(snaps)


def diffs(snaps):
    """연속한 두 날 사이의 변화"""
    out = []
    for prev, cur in zip(snaps, snaps[1:]):
        dv = cur["total"] - prev["total"]
        base = prev["total"] or 1
        moves = []
        for tk, p in cur["positions"].items():
            q = prev["positions"].get(tk)
            if not q:
                moves.append({"ticker": tk, "name": p["name"], "new": True,
                              "d_roi": None, "d_val": None})
                continue
            moves.append({
                "ticker": tk, "name": p["name"], "new": False,
                "d_roi": round((p["roi"] or 0) - (q["roi"] or 0), 2),
                "d_val": round(p["val"] - q["val"]),
                "roi": p["roi"], "w": p["w"],
            })
        moves.sort(key=lambda m: abs(m["d_val"] or 0), reverse=True)
        gone = [{"ticker": tk, "name": q["name"]}
                for tk, q in prev["positions"].items() if tk not in cur["positions"]]
        out.append({
            "date": cur["date"], "prev_date": prev["date"],
            "total": cur["total"], "d_total": round(dv),
            "d_total_pct": round(dv / base * 100, 2),
            "roi": cur["roi"], "d_roi": round((cur["roi"] or 0) - (prev["roi"] or 0), 2),
            "fx": cur["fx"], "d_fx": round((cur["fx"] or 0) - (prev["fx"] or 0), 2),
            "moves": moves, "removed": gone,
        })
    out.reverse()          # 최신이 위로
    return out
