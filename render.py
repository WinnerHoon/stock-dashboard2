# -*- coding: utf-8 -*-
"""브리핑 데이터 → 단독 실행 가능한 정적 HTML (외부 의존 없음)"""

from datetime import datetime
from html import escape


def _w(v):
    return "-" if v is None else (f"{v:+,.0f}" if v != 0 else "0")


def _c(v):
    return "flat" if v is None else ("up" if v > 0 else ("down" if v < 0 else "flat"))


def _p(v):
    return "-" if v is None else f"{v:+.2f}%"


def _spark(vals, w=110, h=30):
    if not vals or len(vals) < 2:
        return ""
    lo, hi = min(vals), max(vals)
    rng = (hi - lo) or 1
    st = w / (len(vals) - 1)
    pts = " ".join(f"{i*st:.1f},{h-(v-lo)/rng*(h-4)-2:.1f}" for i, v in enumerate(vals))
    col = "var(--up)" if vals[-1] >= vals[0] else "var(--down)"
    return (f'<svg class="spk" viewBox="0 0 {w} {h}" preserveAspectRatio="none">'
            f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="1.6" '
            f'stroke-linejoin="round"/></svg>')


def _band(pos, frm):
    if pos is None:
        return "-"
    x = max(0, min(100, pos))
    return (f'<div class="rb" title="52주 최고 대비 {_p(frm)}"><div class="rf"></div>'
            f'<div class="rd" style="left:{x:.0f}%"></div></div><span class="rt">{x:.0f}%</span>')


def _price(m):
    v = m.get("price")
    if v is None:
        return "-"
    return f"{v:,.0f}원" if m.get("currency") == "KRW" else f"${v:,.2f}"


def _news(d):
    out = []
    for tk, v in (d.get("news") or {}).items():
        lis = "".join(
            f'<li><a href="{escape(n.get("url") or "#")}" target="_blank" rel="noopener">'
            f'{escape(n["title"])}</a><span class="src">{escape(n.get("publisher") or "")}</span></li>'
            for n in v["items"])
        out.append(f'<div class="ng"><h4>{escape(v["name"])} <span class="tk">{escape(tk)}</span></h4>'
                   f'<ul>{lis}</ul></div>')
    return "".join(out) or '<p class="em">수집된 뉴스가 없습니다. 네이버 뉴스 API 시크릿이 등록되어 있는지 확인해 주세요.</p>'


def page(d):
    t, a = d["totals"], d["allocation"]
    title = f"{d.get('owner','')}님의 주식 포트폴리오".strip()

    idx = "".join(
        f'<div class="ic"><div class="in">{escape(i["name"])}</div>'
        f'<div class="iv">{i["price"]:,.2f}</div>'
        f'<div class="ig {_c(i.get("chg"))}">{_p(i.get("chg"))}</div>'
        f'<div class="is">1년 {_p(i.get("y1"))}</div></div>'
        for i in d.get("indices", []))

    rows = "".join(
        f'<tr><td class="nm"><b>{escape(m["name"])}</b><span class="tk">{escape(m["ticker"])}</span>'
        f'{"<span class=bd-e>ETF</span>" if m.get("is_etf") else ""}'
        f'{"<span class=bd-s>분산</span>" if m.get("split") else ""}'
        f'<div class="s2">{escape(" · ".join(m.get("brokers") or []))}</div></td>'
        f'<td class="n"><b>{m["weight_pct"]:.1f}%</b>'
        f'<div class="wb"><i style="width:{min(100,m["weight_pct"]*5):.0f}%"></i></div></td>'
        f'<td class="n">{_price(m)}<div class="s2">{m["shares"]:,.0f}주</div></td>'
        f'<td class="n {_c(m.get("chg"))}">{_p(m.get("chg"))}</td>'
        f'<td class="n {_c(m.get("roi_pct"))}"><b>{_p(m.get("roi_pct"))}</b>'
        f'<div class="s2 {_c(m.get("pl_krw"))}">{_w(m.get("pl_krw"))}원</div></td>'
        f'<td class="n">{m["market_value_krw"]:,}원</td>'
        f'<td class="n {_c(m.get("m3"))}">{_p(m.get("m3"))}</td>'
        f'<td class="n {_c(m.get("y1"))}">{_p(m.get("y1"))}</td>'
        f'<td class="n rc">{_band(m.get("band_pos"), m.get("from_high"))}</td>'
        f'<td class="sp">{_spark(m.get("spark") or [])}</td></tr>'
        for m in d.get("consolidated", []))

    bars = "".join(
        f'<div class="ab"><div class="ah"><span>{k}</span><b>{a[k]}%</b></div>'
        f'<div class="at"><div class="af" style="width:{a[k]}%;background:var(--{v})"></div></div></div>'
        for k, v in (("국내", "c1"), ("해외", "c2"), ("ETF", "c3"), ("개별주", "c4")))
    chips = "".join(f'<span class="chip">{escape(k)} <b>{v:,}원</b></span>'
                    for k, v in sorted(a.get("by_broker", {}).items(), key=lambda x: -x[1]))

    fails = [p for p in d["positions"] if "error" in p]
    fail = ('<div class="card warn"><h2>시세 조회 실패</h2><p class="em">'
            + ", ".join(f'{escape(p["name"])}({escape(p["ticker"])})' for p in fails)
            + ' — 티커를 확인해 주세요.</p></div>') if fails else ""

    delta = ""
    if t.get("delta_krw") is not None:
        delta = (f'<div class="td {_c(t["delta_krw"])}">전일 대비 {_w(t["delta_krw"])}원 '
                 f'({_p(t.get("delta_pct"))})</div>')

    mock = '<div class="mk">모의 데이터로 생성된 화면입니다</div>' if d.get("mock") else ""

    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow,noarchive">
<title>{escape(title)} · {d['date']}</title>
<style>
:root{{--bg:#0f1115;--card:#171a21;--line:#252a34;--txt:#e6e8ec;--dim:#8b93a1;
--up:#e5484d;--down:#2f81f7;--flat:#8b93a1;--ac:#f0b429;
--c1:#5b8def;--c2:#f0b429;--c3:#3fb984;--c4:#c05fd6}}
@media(prefers-color-scheme:light){{:root{{--bg:#f6f7f9;--card:#fff;--line:#e3e6ea;--txt:#1a1d23;--dim:#6b7280}}}}
*{{box-sizing:border-box}}
body{{margin:0;padding:26px 18px 56px;background:var(--bg);color:var(--txt);
font:15px/1.55 -apple-system,"Segoe UI","Malgun Gothic",sans-serif}}
.wrap{{max-width:1180px;margin:0 auto}}
h1{{font-size:21px;margin:0 0 4px}} .sb{{color:var(--dim);font-size:12.5px;margin-bottom:20px}}
.mk{{background:var(--ac);color:#000;padding:8px 14px;border-radius:8px;margin-bottom:16px;font-weight:600;font-size:13px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:19px;margin-bottom:16px}}
.card.warn{{border-color:var(--ac)}}
h2{{font-size:12px;letter-spacing:.05em;text-transform:uppercase;color:var(--dim);margin:0 0 13px;font-weight:700}}
.hero{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:20px}}
.lb{{color:var(--dim);font-size:11.5px;margin-bottom:3px}}
.bg{{font-size:28px;font-weight:700;letter-spacing:-.02em}} .bg.s{{font-size:21px}}
.td{{font-size:12.5px;margin-top:5px}}
.ics{{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:11px}}
.ic{{background:var(--bg);border:1px solid var(--line);border-radius:10px;padding:11px 13px}}
.in{{color:var(--dim);font-size:11.5px}} .iv{{font-size:17px;font-weight:600;margin:3px 0}}
.ig{{font-size:12.5px;font-weight:600}} .is{{color:var(--dim);font-size:10.5px;margin-top:2px}}
.abs{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:15px;margin-bottom:13px}}
.ah{{display:flex;justify-content:space-between;font-size:12.5px;margin-bottom:5px}}
.at{{height:7px;background:var(--bg);border-radius:4px;overflow:hidden}}
.af{{height:100%;border-radius:4px}}
.chips{{display:flex;flex-wrap:wrap;gap:8px}}
.chip{{background:var(--bg);border:1px solid var(--line);border-radius:20px;padding:5px 12px;font-size:12px;color:var(--dim)}}
.chip b{{color:var(--txt);font-weight:600}}
table{{width:100%;border-collapse:collapse;font-size:13.5px}}
th{{text-align:right;color:var(--dim);font-size:10.5px;text-transform:uppercase;letter-spacing:.03em;
padding:0 8px 9px;font-weight:700;border-bottom:1px solid var(--line);white-space:nowrap}}
th:first-child{{text-align:left}}
td{{padding:11px 8px;border-bottom:1px solid var(--line);vertical-align:middle}}
td.n{{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}}
td.sp{{width:118px;padding-right:0}} td.rc{{width:112px}}
tr:last-child td{{border-bottom:none}}
.tk{{color:var(--dim);font-size:10.5px;margin-left:6px}}
.s2{{color:var(--dim);font-size:10.5px;margin-top:2px;font-weight:400}}
.bd-e,.bd-s{{display:inline-block;margin-left:5px;padding:1px 6px;border-radius:12px;
background:var(--bg);border:1px solid var(--line);font-size:9.5px;vertical-align:middle}}
.bd-e{{border-color:var(--c3);color:var(--c3)}} .bd-s{{border-color:var(--c1);color:var(--c1)}}
.wb{{height:4px;background:var(--line);border-radius:3px;margin-top:4px}}
.wb i{{display:block;height:100%;background:var(--c1);border-radius:3px}}
.rb{{position:relative;height:5px;background:var(--line);border-radius:3px;display:inline-block;width:70px;vertical-align:middle}}
.rf{{height:100%;background:linear-gradient(90deg,var(--down),var(--up));border-radius:3px;opacity:.5}}
.rd{{position:absolute;top:-2.5px;width:3px;height:10px;background:var(--txt);border-radius:2px;transform:translateX(-1.5px)}}
.rt{{color:var(--dim);font-size:10.5px;margin-left:6px}}
.up{{color:var(--up)}} .down{{color:var(--down)}} .flat{{color:var(--flat)}}
.spk{{width:110px;height:30px;display:block}}
.ng{{margin-bottom:17px}} .ng:last-child{{margin-bottom:0}}
.ng h4{{font-size:13px;margin:0 0 7px;font-weight:600}}
.ng ul{{margin:0;padding-left:17px}} .ng li{{margin-bottom:6px;font-size:13.5px}}
.ng a{{color:var(--txt);text-decoration:none;border-bottom:1px solid var(--line)}}
.ng a:hover{{border-bottom-color:var(--txt)}}
.src{{color:var(--dim);font-size:10.5px;margin-left:8px}}
.em{{color:var(--dim);font-size:13px;margin:0}}
footer{{color:var(--dim);font-size:11.5px;text-align:center;margin-top:26px;line-height:1.8}}
@media(max-width:860px){{td.sp,th.sp,td.rc,th.rc{{display:none}}}}
</style></head><body><div class="wrap">
{mock}
<h1>{escape(title)}</h1>
<div class="sb">{d['date']} · {datetime.fromisoformat(d['generated_at']):%H:%M} KST 갱신 · 환율 {t.get('usdkrw','-')}원 · 장기 보유 관점</div>

<div class="card"><div class="hero">
<div><div class="lb">총 평가금액</div><div class="bg">{t['market_value_krw']:,}원</div>{delta}</div>
<div><div class="lb">평가손익</div><div class="bg {_c(t['pl_krw'])}">{_w(t['pl_krw'])}원</div></div>
<div><div class="lb">총 수익률</div><div class="bg {_c(t['roi_pct'])}">{_p(t['roi_pct'])}</div></div>
<div><div class="lb">매입원가</div><div class="bg s">{t['cost_krw']:,}원</div></div>
</div></div>

<div class="card"><h2>자산 배분</h2><div class="abs">{bars}</div><div class="chips">{chips}</div></div>

<div class="card"><h2>시장 지표</h2><div class="ics">{idx or '<p class="em">지수 데이터 없음</p>'}</div></div>

<div class="card"><h2>보유 종목 {t['positions_count']}개 · 증권사 합산</h2>
<table><thead><tr><th>종목</th><th>비중</th><th>현재가</th><th>전일비</th><th>수익률</th>
<th>평가금액</th><th>3개월</th><th>1년</th><th class="rc">52주 위치</th><th class="sp"></th></tr></thead>
<tbody>{rows}</tbody></table></div>

{fail}

<div class="card"><h2>뉴스</h2>{_news(d)}</div>

<footer>매일 아침 GitHub Actions 가 자동으로 갱신합니다 · 시세는 지연될 수 있습니다<br>
해외 종목 평단은 환율 환산 근사치입니다<br>
이 페이지는 정보 제공용이며 투자 권유가 아닙니다. 투자 판단과 책임은 본인에게 있습니다.</footer>
</div></body></html>"""
