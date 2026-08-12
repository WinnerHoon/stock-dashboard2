# -*- coding: utf-8 -*-
"""
정적 HTML 3종 생성 (외부 CDN 의존 없음, 모바일 대응)
  index.html    포트폴리오
  news.html     뉴스 (영문은 한글 번역 병기)
  history.html  일별 변화
"""

import json
from datetime import datetime
from html import escape

PAGES = [("index.html", "포트폴리오"), ("news.html", "뉴스"), ("history.html", "일별 변화")]


# ── 포맷 헬퍼 ────────────────────────────────────────────────
def w(v):
    return "-" if v is None else (f"{v:+,.0f}" if v != 0 else "0")


def c(v):
    return "flat" if v is None else ("up" if v > 0 else ("down" if v < 0 else "flat"))


def p(v):
    return "-" if v is None else f"{v:+.2f}%"


def man(v):
    if v is None:
        return "-"
    s = "+" if v > 0 else ("-" if v < 0 else "")
    return f"{s}{abs(v)/10000:,.0f}만"


def spark(vals, W=110, H=30):
    if not vals or len(vals) < 2:
        return ""
    lo, hi = min(vals), max(vals)
    rng = (hi - lo) or 1
    st = W / (len(vals) - 1)
    pts = " ".join(f"{i*st:.1f},{H-(v-lo)/rng*(H-4)-2:.1f}" for i, v in enumerate(vals))
    col = "var(--up)" if vals[-1] >= vals[0] else "var(--down)"
    return (f'<svg class="spk" viewBox="0 0 {W} {H}" preserveAspectRatio="none">'
            f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="1.6"/></svg>')


def band(pos, frm):
    if pos is None:
        return "-"
    x = max(0, min(100, pos))
    return (f'<span class="rb" title="52주 최고 대비 {p(frm)}"><i class="rf"></i>'
            f'<i class="rd" style="left:{x:.0f}%"></i></span><span class="rt">{x:.0f}%</span>')


def price(m):
    v = m.get("price")
    if v is None:
        return "-"
    return f"{v:,.0f}원" if m.get("currency") == "KRW" else f"${v:,.2f}"


ETF_BADGE = '<span class="bd e">ETF</span>'
SPLIT_BADGE = '<span class="bd s">분산</span>'


def badges(m):
    return (ETF_BADGE if m.get("is_etf") else "") + (SPLIT_BADGE if m.get("split") else "")


# ── 공통 셸 ─────────────────────────────────────────────────
CSS = """
:root{color-scheme:light dark;--bg:#0f1115;--card:#171a21;--line:#252a34;--txt:#e6e8ec;--dim:#8b93a1;
--up:#e5484d;--down:#2f81f7;--flat:#8b93a1;--ac:#f0b429;
--c1:#5b8def;--c2:#f0b429;--c3:#3fb984;--c4:#c05fd6;--hl:#1e222b}
@media(prefers-color-scheme:light){:root{--bg:#f6f7f9;--card:#fff;--line:#e3e6ea;--txt:#1a1d23;--dim:#6b7280;--hl:#f0f2f5}}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
body{margin:0;padding:0 0 60px;background:var(--bg);color:var(--txt);
font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI","Malgun Gothic",sans-serif;
-webkit-text-size-adjust:100%}
.wrap{max-width:1180px;margin:0 auto;padding:0 16px}
nav{position:sticky;top:0;z-index:20;background:var(--bg);border-bottom:1px solid var(--line);
padding:0 16px;display:flex;gap:2px;overflow-x:auto;-webkit-overflow-scrolling:touch}
nav a{flex:0 0 auto;padding:14px 16px;color:var(--dim);text-decoration:none;font-size:14px;
font-weight:600;border-bottom:2px solid transparent;white-space:nowrap}
nav a.on{color:var(--txt);border-bottom-color:var(--c1)}
header{padding:20px 0 4px}
h1{font-size:20px;margin:0 0 4px}
.sb{color:var(--dim);font-size:12.5px;margin-bottom:16px;display:flex;flex-wrap:wrap;gap:6px 10px;align-items:center}
#fresh,#live{border:1px solid var(--line);border-radius:20px;padding:2px 10px;font-size:11.5px}
#live.on{border-color:var(--c3);color:var(--c3)}
#live.off{border-color:var(--ac);color:var(--ac)}
#refresh{background:none;border:1px solid var(--line);border-radius:20px;padding:2px 10px;
font-size:11.5px;color:var(--dim);cursor:pointer;font-family:inherit}
#refresh:hover{color:var(--txt);border-color:var(--dim)}
#refresh:active{transform:scale(.96)}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px;margin-bottom:14px}
h2{font-size:12px;letter-spacing:.05em;text-transform:uppercase;color:var(--dim);margin:0 0 13px;font-weight:700}
.hero{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:18px}
.lb{color:var(--dim);font-size:11.5px;margin-bottom:3px}
.bg{font-size:27px;font-weight:700;letter-spacing:-.02em}
.bg.s{font-size:20px}
.td{font-size:12.5px;margin-top:5px}
.ics{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px}
.ic{background:var(--bg);border:1px solid var(--line);border-radius:10px;padding:10px 12px}
.in{color:var(--dim);font-size:11.5px}
.iv{font-size:16px;font-weight:600;margin:3px 0}
.ig{font-size:12.5px;font-weight:600}
.is{color:var(--dim);font-size:10.5px}
.abs{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:14px;margin-bottom:12px}
.ah{display:flex;justify-content:space-between;font-size:12.5px;margin-bottom:5px}
.at{height:7px;background:var(--bg);border-radius:4px;overflow:hidden}
.af{height:100%;border-radius:4px}
.chips{display:flex;flex-wrap:wrap;gap:7px}
.chip{background:var(--bg);border:1px solid var(--line);border-radius:20px;padding:5px 11px;font-size:12px;color:var(--dim)}
.chip b{color:var(--txt);font-weight:600}
table{width:100%;border-collapse:collapse;font-size:13.5px}
th{text-align:right;color:var(--dim);font-size:10.5px;text-transform:uppercase;letter-spacing:.03em;
padding:0 8px 9px;font-weight:700;border-bottom:1px solid var(--line);white-space:nowrap}
th:first-child{text-align:left}
td{padding:11px 8px;border-bottom:1px solid var(--line);vertical-align:middle}
td.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
tr:last-child td{border-bottom:none}
.tk{color:var(--dim);font-size:10.5px;margin-left:6px}
.s2{color:var(--dim);font-size:10.5px;margin-top:2px;font-weight:400}
.bd{display:inline-block;margin-left:5px;padding:1px 6px;border-radius:12px;background:var(--bg);
border:1px solid var(--line);font-size:9.5px;vertical-align:middle}
.bd.e{border-color:var(--c3);color:var(--c3)}
.bd.s{border-color:var(--c1);color:var(--c1)}
.wb{height:4px;background:var(--line);border-radius:3px;margin-top:4px}
.wb i{display:block;height:100%;background:var(--c1);border-radius:3px}
.rb{position:relative;height:5px;background:var(--line);border-radius:3px;display:inline-block;width:64px;vertical-align:middle}
.rf{position:absolute;inset:0;background:linear-gradient(90deg,var(--down),var(--up));border-radius:3px;opacity:.5}
.rd{position:absolute;top:-2.5px;width:3px;height:10px;background:var(--txt);border-radius:2px}
.rt{color:var(--dim);font-size:10.5px;margin-left:6px}
.up{color:var(--up)}.down{color:var(--down)}.flat{color:var(--flat)}
.spk{width:110px;height:30px;display:block}
.em{color:var(--dim);font-size:13px;margin:0}
footer{color:var(--dim);font-size:11.5px;text-align:center;margin-top:22px;line-height:1.8;padding:0 16px}
.cards{display:none}
@media(max-width:760px){
 .wrap{padding:0 12px}
 h1{font-size:18px}
 .bg{font-size:23px}
 .hero{grid-template-columns:1fr 1fr;gap:14px}
 .card{padding:14px;border-radius:12px}
 table.resp{display:none}
 .cards{display:block}
 nav a{padding:13px 13px;font-size:13.5px}
}
.mc{border-bottom:1px solid var(--line);padding:13px 0}
.mc:last-child{border-bottom:none}
.mc-t{display:flex;justify-content:space-between;align-items:baseline;gap:10px}
.mc-n{font-weight:600;font-size:14.5px}
.mc-r{font-size:15px;font-weight:700;white-space:nowrap}
.mc-g{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-top:8px;font-size:11.5px}
.mc-g div{color:var(--dim)}
.mc-g b{display:block;color:var(--txt);font-size:12.5px;font-variant-numeric:tabular-nums;font-weight:600}
"""

JS = """
(function(){
 var BAKED=%s, KEY='reloaded-'+BAKED;
 var el=document.getElementById('fresh');
 function ago(iso){
  var d=(Date.now()-new Date(iso).getTime())/60000;
  if(d<1)return '방금';
  if(d<60)return Math.floor(d)+'분 전';
  if(d<1440)return Math.floor(d/60)+'시간 전';
  return Math.floor(d/1440)+'일 전';
 }
 if(el) el.textContent='갱신 '+ago(BAKED);
 // 방문할 때마다 최신 데이터가 있는지 확인하고, 있으면 새 페이지를 받아옵니다
 fetch('data.json?t='+Date.now(),{cache:'no-store'})
  .then(function(r){return r.ok?r.json():null;})
  .then(function(j){
    if(!j||j.generated_at===BAKED) return;
    if(sessionStorage.getItem(KEY)) return;   // 무한 새로고침 방지
    sessionStorage.setItem(KEY,'1');
    location.reload();
  }).catch(function(){});
})();
"""


LIVE_JS = """
// ── 방문할 때마다 실시간 시세로 갱신 ─────────────────────────
// 브라우저에서 야후를 직접 부르면 CORS 에 막히므로 /api/quotes 서버리스 함수를 거칩니다.
(function(){
 var HOLD=%s, FXSYM='KRW=X', BUILT=%s;
 var won=function(v){return Math.round(v).toLocaleString('ko-KR');};
 var sg=function(v){return v==null?'-':(v>0?'+':'')+v.toFixed(2)+'%%';};
 var cl=function(v){return v==null?'flat':(v>0?'up':(v<0?'down':'flat'));};
 var badge=document.getElementById('live');

 function setCell(tk,f,html,klass,base){
  var el=document.querySelector('[data-tk="'+tk+'"] [data-f="'+f+'"]');
  if(!el) return;
  el.innerHTML=html;
  if(klass!=null) el.className=(base||'')+' '+klass;
 }

 function paint(Q,fx,at){
  var tot=0,cost=0,rows=[];
  for(var i=0;i<HOLD.length;i++){
   var h=HOLD[i], q=Q[h.y];
   if(!q||q.price==null) return false;
   var rate=(h.cur==='KRW')?1:fx;
   var val=q.price*h.sh*rate, cst=h.avg*h.sh*rate;
   tot+=val; cost+=cst;
   rows.push({h:h,q:q,val:val,cst:cst,pl:val-cst,
              roi:h.avg?(q.price/h.avg-1)*100:null});
  }
  rows.forEach(function(r){
   var h=r.h,q=r.q,wt=tot?r.val/tot*100:0;
   var pstr=(h.cur==='KRW')?won(q.price)+'원':String.fromCharCode(36)+q.price.toFixed(2);
   setCell(h.t,'price',pstr+'<div class="s2">'+h.sh.toLocaleString('ko-KR')+'주</div>','','n');
   setCell(h.t,'chg',sg(q.chg),cl(q.chg),'n');
   setCell(h.t,'roi','<b>'+sg(r.roi)+'</b><div class="s2 '+cl(r.pl)+'">'
     +(r.pl>0?'+':'')+won(r.pl)+'원</div>',cl(r.roi),'n');
   setCell(h.t,'val',won(r.val)+'원','','n');
   setCell(h.t,'w','<b>'+wt.toFixed(1)+'%%</b><div class="wb"><i style="width:'
     +Math.min(100,wt*5).toFixed(0)+'%%"></i></div>','','n');
   setCell(h.t,'mprice',pstr,null);
   setCell(h.t,'mroi',sg(r.roi),cl(r.roi),'mc-r');
   setCell(h.t,'mw',wt.toFixed(1)+'%%',null);
   setCell(h.t,'mval',won(r.val/10000)+'만원',null);
   setCell(h.t,'mpl',(r.pl>0?'+':'')+won(r.pl),cl(r.pl));
   setCell(h.t,'mchg',sg(q.chg),cl(q.chg));
  });
  var pl=tot-cost, roi=cost?(pl/cost*100):null;
  var e;
  if((e=document.getElementById('hTot'))) e.textContent=won(tot)+'원';
  if((e=document.getElementById('hPl'))){e.textContent=(pl>0?'+':'')+won(pl)+'원';e.className='bg '+cl(pl);}
  if((e=document.getElementById('hRoi'))){e.textContent=sg(roi);e.className='bg '+cl(roi);}
  if((e=document.getElementById('hCost'))) e.textContent=won(cost)+'원';
  if(badge){
   var d=new Date(at);
   badge.textContent='실시간 '+d.toLocaleTimeString('ko-KR',{hour:'2-digit',minute:'2-digit'});
   badge.className='on';
  }
  return true;
 }

 function run(){
  if(badge){badge.textContent='시세 불러오는 중';badge.className='';}
  var syms=HOLD.map(function(h){return h.y;}).concat([FXSYM]).join(',');
  fetch('/api/quotes?t='+encodeURIComponent(syms),{cache:'no-store'})
   .then(function(r){return r.ok?r.json():null;})
   .then(function(j){
     if(!j||!j.ok||!j.quotes[FXSYM]){throw new Error('no data');}
     if(!paint(j.quotes,j.quotes[FXSYM].price,j.at)) throw new Error('incomplete');
   })
   .catch(function(){
     if(badge){badge.textContent='빌드 시점 기준 ('+BUILT.slice(11,16)+')';badge.className='off';}
   });
 }
 run();
 var btn=document.getElementById('refresh');
 if(btn) btn.onclick=run;
 document.addEventListener('visibilitychange',function(){
   if(!document.hidden) run();
 });
})();
"""


def shell(active, data, body, extra_js=""):
    nav = "".join(
        f'<a href="{h}" class="{"on" if h == active else ""}">{escape(t)}</a>'
        for h, t in PAGES)
    gen = data["generated_at"]
    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="robots" content="noindex,nofollow,noarchive">
<meta name="theme-color" content="#0f1115" media="(prefers-color-scheme:dark)">
<meta name="theme-color" content="#f6f7f9" media="(prefers-color-scheme:light)">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="내 주식">
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<title>{escape(dict(PAGES)[active])} · 승훈님의 주식</title>
<style>{CSS}</style></head><body>
<nav>{nav}</nav>
<div class="wrap">
{body}
<footer>매 정시(장중) GitHub Actions 가 자동 갱신 · 시세는 지연될 수 있습니다<br>
해외 종목 평단은 환율 환산 근사치이며, 뉴스 번역은 기계번역입니다<br>
정보 제공용이며 투자 권유가 아닙니다. 투자 판단과 책임은 본인에게 있습니다.</footer>
</div>
<script>{JS % json.dumps(gen)}{extra_js}</script></body></html>"""


# ── 1. 포트폴리오 ────────────────────────────────────────────
def page_index(d):
    t, a = d["totals"], d["allocation"]
    C = d.get("consolidated", [])

    delta = ""
    if t.get("delta_krw") is not None:
        delta = (f'<div class="td {c(t["delta_krw"])}">전일 대비 {w(t["delta_krw"])}원 '
                 f'({p(t.get("delta_pct"))})</div>')

    hero = (f'<div class="card"><div class="hero">'
            f'<div><div class="lb">총 평가금액</div>'
            f'<div class="bg" id="hTot">{t["market_value_krw"]:,}원</div>{delta}</div>'
            f'<div><div class="lb">평가손익</div>'
            f'<div class="bg {c(t["pl_krw"])}" id="hPl">{w(t["pl_krw"])}원</div></div>'
            f'<div><div class="lb">총 수익률</div>'
            f'<div class="bg {c(t["roi_pct"])}" id="hRoi">{p(t["roi_pct"])}</div></div>'
            f'<div><div class="lb">매입원가</div>'
            f'<div class="bg s" id="hCost">{t["cost_krw"]:,}원</div></div>'
            f'</div></div>')

    bars = "".join(
        f'<div><div class="ah"><span>{k}</span><b>{a[k]}%</b></div>'
        f'<div class="at"><div class="af" style="width:{a[k]}%;background:var(--{v})"></div></div></div>'
        for k, v in (("국내", "c1"), ("해외", "c2"), ("ETF", "c3"), ("개별주", "c4")))
    chips = "".join(f'<span class="chip">{escape(k)} <b>{v:,}원</b></span>'
                    for k, v in sorted(a.get("by_broker", {}).items(), key=lambda x: -x[1]))
    alloc = f'<div class="card"><h2>자산 배분</h2><div class="abs">{bars}</div><div class="chips">{chips}</div></div>'

    idx = "".join(
        f'<div class="ic"><div class="in">{escape(i["name"])}</div>'
        f'<div class="iv">{i["price"]:,.2f}</div>'
        f'<div class="ig {c(i.get("chg"))}">{p(i.get("chg"))}</div>'
        f'<div class="is">1년 {p(i.get("y1"))}</div></div>' for i in d.get("indices", []))
    idxc = f'<div class="card"><h2>시장 지표</h2><div class="ics">{idx or "<p class=em>없음</p>"}</div></div>'

    rows = "".join(
        f'<tr data-tk="{escape(m["ticker"])}">'
        f'<td><b>{escape(m["name"])}</b><span class="tk">{escape(m["ticker"])}</span>'
        f'{badges(m)}'
        f'<div class="s2">{escape(" · ".join(m.get("brokers") or []))}</div></td>'
        f'<td class="n" data-f="w"><b>{m["weight_pct"]:.1f}%</b>'
        f'<div class="wb"><i style="width:{min(100,m["weight_pct"]*5):.0f}%"></i></div></td>'
        f'<td class="n" data-f="price">{price(m)}<div class="s2">{m["shares"]:,.0f}주</div></td>'
        f'<td class="n {c(m.get("chg"))}" data-f="chg">{p(m.get("chg"))}</td>'
        f'<td class="n {c(m.get("roi_pct"))}" data-f="roi"><b>{p(m.get("roi_pct"))}</b>'
        f'<div class="s2 {c(m.get("pl_krw"))}">{w(m.get("pl_krw"))}원</div></td>'
        f'<td class="n" data-f="val">{m["market_value_krw"]:,}원</td>'
        f'<td class="n {c(m.get("m3"))}">{p(m.get("m3"))}</td>'
        f'<td class="n {c(m.get("y1"))}">{p(m.get("y1"))}</td>'
        f'<td class="n">{band(m.get("band_pos"), m.get("from_high"))}</td>'
        f'<td>{spark(m.get("spark") or [])}</td></tr>' for m in C)

    cards = "".join(
        f'<div class="mc" data-tk="{escape(m["ticker"])}"><div class="mc-t">'
        f'<span class="mc-n">{escape(m["name"])}{badges(m)}</span>'
        f'<span class="mc-r {c(m.get("roi_pct"))}" data-f="mroi">{p(m.get("roi_pct"))}</span></div>'
        f'<div class="s2">{escape(m["ticker"])} · {m["shares"]:,.0f}주 · '
        f'<span data-f="mprice">{price(m)}</span> · {escape(" · ".join(m.get("brokers") or []))}</div>'
        f'<div class="mc-g">'
        f'<div>비중<b data-f="mw">{m["weight_pct"]:.1f}%</b></div>'
        f'<div>평가금액<b data-f="mval">{m["market_value_krw"]/10000:,.0f}만원</b></div>'
        f'<div>손익<b class="{c(m.get("pl_krw"))}" data-f="mpl">{w(m.get("pl_krw"))}</b></div>'
        f'<div>전일비<b class="{c(m.get("chg"))}" data-f="mchg">{p(m.get("chg"))}</b></div>'
        f'<div>3개월<b class="{c(m.get("m3"))}">{p(m.get("m3"))}</b></div>'
        f'<div>1년<b class="{c(m.get("y1"))}">{p(m.get("y1"))}</b></div>'
        f'</div></div>' for m in C)

    fails = [x for x in d["positions"] if "error" in x]
    fail = ('<div class="card"><h2>시세 조회 실패</h2><p class="em">' +
            ", ".join(f'{escape(x["name"])}({escape(x["ticker"])})' for x in fails) +
            '</p></div>') if fails else ""

    hold = [{"t": m["ticker"],
             "y": (m["ticker"] + ".KS") if m["market"] == "KR" else m["ticker"],
             "sh": m["shares"], "avg": m["avg_price"], "cur": m["currency"]}
            for m in C]

    body = f"""<header><h1>승훈님의 주식 포트폴리오</h1>
<div class="sb"><span id="live">시세 불러오는 중</span>
<button id="refresh" title="지금 다시 조회">새로고침</button>
<span id="fresh"></span>
<span>환율 {t.get('usdkrw','-')}원</span><span>장기 보유 관점</span></div></header>
{hero}{alloc}{idxc}
<div class="card"><h2>보유 종목 {t['positions_count']}개 · 증권사 합산</h2>
<table class="resp"><thead><tr><th>종목</th><th>비중</th><th>현재가</th><th>전일비</th><th>수익률</th>
<th>평가금액</th><th>3개월</th><th>1년</th><th>52주</th><th></th></tr></thead><tbody>{rows}</tbody></table>
<div class="cards">{cards}</div></div>
{fail}"""
    return shell("index.html", d, body,
                 LIVE_JS % (json.dumps(hold, ensure_ascii=False),
                            json.dumps(d["generated_at"])))


# ── 2. 뉴스 ─────────────────────────────────────────────────
def page_news(d):
    news = d.get("news") or {}
    order = {m["ticker"]: m["weight_pct"] for m in d.get("consolidated", [])}
    groups = sorted(news.items(), key=lambda kv: -order.get(kv[0], 0))

    blocks = []
    for tk, v in groups:
        items = []
        for n in v["items"]:
            ko, orig = n.get("title_ko"), n.get("title", "")
            head = escape(ko or orig)
            sub = f'<div class="s2">{escape(orig)}</div>' if ko else ""
            summ = n.get("summary_ko") or n.get("summary") or ""
            sm = f'<div class="nsum">{escape(summ[:220])}</div>' if summ else ""
            src = escape(n.get("publisher") or "")
            url = escape(n.get("url") or "#")
            items.append(f'<li><a href="{url}" target="_blank" rel="noopener">{head}</a>'
                         f'{sub}{sm}<div class="s2 nsrc">{src}</div></li>')
        w_ = order.get(tk)
        wt = f'<span class="tk">비중 {w_:.1f}%</span>' if w_ else ""
        blocks.append(f'<div class="card"><h2>{escape(v["name"])} '
                      f'<span class="tk">{escape(tk)}</span>{wt}</h2>'
                      f'<ul class="nl">{"".join(items)}</ul></div>')

    empty = ('<div class="card"><p class="em">수집된 뉴스가 없습니다.<br><br>'
             '국내 종목 뉴스는 <b>NAVER_CLIENT_ID</b> / <b>NAVER_CLIENT_SECRET</b> 시크릿이 필요합니다.<br>'
             '해외 뉴스는 yfinance 로 자동 수집됩니다.</p></div>')

    tcount = sum(1 for v in news.values() for n in v["items"] if n.get("title_ko"))
    total = sum(len(v["items"]) for v in news.values())
    note = (f'<div class="sb"><span id="fresh">갱신 확인 중</span>'
            f'<span>{total}건</span>'
            f'<span>{tcount}건 한글 번역</span></div>')

    css = """<style>
.nl{list-style:none;margin:0;padding:0}
.nl li{padding:13px 0;border-bottom:1px solid var(--line)}
.nl li:last-child{border-bottom:none}
.nl a{color:var(--txt);text-decoration:none;font-weight:600;font-size:14.5px;line-height:1.45}
.nl a:hover{text-decoration:underline}
.nsum{color:var(--dim);font-size:12.5px;margin-top:6px;line-height:1.6}
.nsrc{margin-top:6px}
</style>"""

    body = f"""{css}<header><h1>뉴스</h1>{note}</header>
{"".join(blocks) if blocks else empty}"""
    return shell("news.html", d, body)


# ── 3. 일별 변화 ─────────────────────────────────────────────
def line_chart(pts, W=1000, H=170):
    """pts = [(date, value)]"""
    if len(pts) < 2:
        return '<p class="em">데이터가 2일 이상 쌓이면 그래프가 나타납니다.</p>'
    vals = [v for _, v in pts]
    lo, hi = min(vals), max(vals)
    rng = (hi - lo) or 1
    st = W / (len(pts) - 1)
    xy = [(i * st, H - (v - lo) / rng * (H - 24) - 12) for i, (_, v) in enumerate(pts)]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in xy)
    area = f"0,{H} " + line + f" {W},{H}"
    up = vals[-1] >= vals[0]
    col = "var(--up)" if up else "var(--down)"
    dots = f'<circle cx="{xy[-1][0]:.1f}" cy="{xy[-1][1]:.1f}" r="4" fill="{col}"/>'
    return (f'<svg class="lc" viewBox="0 0 {W} {H}" preserveAspectRatio="none">'
            f'<polygon points="{area}" fill="{col}" opacity="0.10"/>'
            f'<polyline points="{line}" fill="none" stroke="{col}" stroke-width="2.5" '
            f'stroke-linejoin="round" stroke-linecap="round"/>{dots}</svg>'
            f'<div class="lcx"><span>{escape(pts[0][0])}</span>'
            f'<span>{hi/10000:,.0f}만 최고 · {lo/10000:,.0f}만 최저</span>'
            f'<span>{escape(pts[-1][0])}</span></div>')


def page_history(d, hist, diffs):
    snaps = hist.get("snapshots", [])
    pts = [(s["date"], s["total"]) for s in snaps]

    first, last = (snaps[0], snaps[-1]) if snaps else (None, None)
    summary = ""
    if first and last and len(snaps) >= 2:
        dv = last["total"] - first["total"]
        summary = (f'<div class="card"><div class="hero">'
                   f'<div><div class="lb">기록 기간</div><div class="bg s">{len(snaps)}일</div>'
                   f'<div class="s2">{first["date"]} ~ {last["date"]}</div></div>'
                   f'<div><div class="lb">기간 중 변화</div><div class="bg s {c(dv)}">{w(dv)}원</div></div>'
                   f'<div><div class="lb">최고 평가액</div><div class="bg s">{max(s["total"] for s in snaps):,}원</div></div>'
                   f'<div><div class="lb">최저 평가액</div><div class="bg s">{min(s["total"] for s in snaps):,}원</div></div>'
                   f'</div></div>')

    chart = f'<div class="card"><h2>총 평가금액 추이</h2>{line_chart(pts)}</div>'

    days = []
    for f in diffs[:60]:
        movers = [m for m in f["moves"] if m.get("d_val")][:5]
        mv = "".join(
            f'<div class="mv"><span class="mvn">{escape(m["name"][:20])}</span>'
            f'<span class="n {c(m.get("d_roi"))}">{p(m.get("d_roi"))}</span>'
            f'<span class="n {c(m.get("d_val"))}">{w(m.get("d_val"))}원</span></div>'
            for m in movers) or '<p class="em">종목별 변동 없음</p>'
        newly = "".join(f'<span class="chip">신규 {escape(m["name"])}</span>'
                        for m in f["moves"] if m.get("new"))
        gone = "".join(f'<span class="chip">제외 {escape(m["name"])}</span>' for m in f["removed"])
        days.append(
            f'<div class="card"><div class="dh">'
            f'<div><b class="dd">{escape(f["date"])}</b>'
            f'<span class="s2">{escape(f["prev_date"])} 대비</span></div>'
            f'<div class="dv {c(f["d_total"])}">{w(f["d_total"])}원'
            f'<span class="dp">{p(f["d_total_pct"])}</span></div></div>'
            f'<div class="dsub">총 {f["total"]:,}원 · 수익률 {p(f["roi"])} '
            f'(<span class="{c(f["d_roi"])}">{p(f["d_roi"])}</span>) · '
            f'환율 {f["fx"]:,.2f} (<span class="{c(f["d_fx"])}">{f["d_fx"]:+.2f}</span>)</div>'
            f'{mv}{f"<div class=chips>{newly}{gone}</div>" if (newly or gone) else ""}</div>')

    if not days:
        days = ['<div class="card"><p class="em">아직 비교할 이전 기록이 없습니다.<br>'
                '내일 빌드가 한 번 더 돌면 일별 변화가 표시됩니다.</p></div>']

    css = """<style>
.lc{width:100%;height:170px;display:block}
.lcx{display:flex;justify-content:space-between;color:var(--dim);font-size:11px;margin-top:6px}
.dh{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;margin-bottom:6px}
.dd{font-size:15px}
.dh .s2{display:inline;margin-left:8px}
.dv{font-size:17px;font-weight:700;text-align:right;white-space:nowrap}
.dp{display:block;font-size:11.5px;font-weight:500}
.dsub{color:var(--dim);font-size:11.5px;margin-bottom:11px;padding-bottom:11px;border-bottom:1px solid var(--line)}
.mv{display:grid;grid-template-columns:1fr auto auto;gap:12px;padding:6px 0;font-size:13px;align-items:baseline}
.mv .n{font-variant-numeric:tabular-nums;text-align:right;min-width:74px}
.mvn{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.chips{margin-top:10px}
</style>"""

    body = f"""{css}<header><h1>일별 변화</h1>
<div class="sb"><span id="fresh">갱신 확인 중</span><span>최근 {len(diffs)}일 비교</span></div></header>
{summary}{chart}{"".join(days)}"""
    return shell("history.html", d, body)


def render_all(d, hist, diffs):
    return {"index.html": page_index(d),
            "news.html": page_news(d),
            "history.html": page_history(d, hist, diffs)}
