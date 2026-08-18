# -*- coding: utf-8 -*-
"""
정적 HTML 3종 생성 (외부 CDN 의존 없음, 모바일 대응)
  index.html    포트폴리오
  news.html     뉴스 (영문은 한글 번역 병기)
  history.html  일별 변화
"""

import json
import os
from datetime import datetime
from html import escape

PAGES = [("index.html", "포트폴리오"), ("market.html", "시장"), ("news.html", "뉴스"),
         ("history.html", "일별 변화"), ("add.html", "거래 입력")]


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
 var HOLD=%s, FXSYM='KRW=X', BUILT=%s, CASH=%s, PREV=%s;
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
   if(!q||q.price==null) return false;          // 하나라도 빠지면 갱신하지 않음
   var rate=(h.cur==='KRW')?1:fx;
   var val=q.price*h.sh*rate, cst=h.avg*h.sh*rate;
   tot+=val; cost+=cst;
   rows.push({h:h,q:q,val:val,cst:cst,pl:val-cst,
              roi:h.avg?(q.price/h.avg-1)*100:null});
  }
  rows.forEach(function(r){
   var h=r.h,q=r.q,wt=tot?r.val/tot*100:0;
   var pstr=(h.cur==='KRW')?won(q.price)+'원':'$'+q.price.toFixed(2);
   setCell(h.t,'price',pstr+'<div class="s2">'+h.sh.toLocaleString('ko-KR')+'주</div>','','n');
   setCell(h.t,'chg',sg(q.chg),cl(q.chg),'n');
  setCell(h.t,'nr',sg(r.roi),cl(r.roi),'nr');
   setCell(h.t,'roi','<b>'+sg(r.roi)+'</b><div class="s2 '+cl(r.pl)+'">'
     +(r.pl>0?'+':'')+won(r.pl)+'원</div>',cl(r.roi),'n');
   setCell(h.t,'val',won(r.val)+'원','','n');
   setCell(h.t,'w','<b>'+wt.toFixed(1)+'%%</b><div class="wb"><i style="width:'
     +Math.min(100,wt*5).toFixed(0)+'%%"></i></div>','','n');
   // 모바일 카드
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
 var cashKrw=CASH?((CASH.KRW||0)+(CASH.USD||0)*fx):null;
 if(cashKrw!=null){
  if((e=document.getElementById('hNet'))) e.textContent=won(tot+cashKrw)+'원';
  if((e=document.getElementById('hCash'))) e.textContent=won(cashKrw)+'원';
 }
 if(PREV&&(e=document.getElementById('hDelta'))){
  var dv=tot-PREV;
  e.textContent=(e.getAttribute('data-base')||'전일')+' 대비 '+(dv>0?'+':'')+won(dv)+'원 ('+sg(dv/PREV*100)+')';
  e.className='td '+cl(dv);
 }
 if((e=document.getElementById('hFx'))) e.textContent='환율 '+fx.toFixed(2)+'원';
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
 // 탭으로 돌아오면 다시 조회
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
def live_js(d):
    """실시간 시세 갱신 스크립트 (index·news 공용)."""
    C = d.get("consolidated", [])
    hold = [{"t": m["ticker"],
             "y": (m["ticker"] + ".KS") if m["market"] == "KR" else m["ticker"],
             "sh": m["shares"], "avg": m["avg_price"], "cur": m["currency"]}
            for m in C]
    cs = d.get("cash")
    cash = {"KRW": cs.get("KRW", 0), "USD": cs.get("USD", 0)} if cs else None
    return LIVE_JS % (json.dumps(hold, ensure_ascii=False),
                      json.dumps(d["generated_at"]),
                      json.dumps(cash),
                      json.dumps(d["totals"].get("prev_total_krw")))


def page_index(d):
    t, a = d["totals"], d["allocation"]
    C = d.get("consolidated", [])

    delta = ""
    if t.get("delta_krw") is not None:
        base = t.get("prev_base_date") or "전일"
        delta = (f'<div class="td {c(t["delta_krw"])}" id="hDelta" data-base="{escape(base)}">'
                 f'{escape(base)} 대비 {w(t["delta_krw"])}원 '
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

    cashc = ""
    cs = d.get("cash")
    if cs:
        chips = "".join(
            f'<span class="chip">{escape(k)} <b>{v["KRW"]:,}원</b>'
            + (f' + <b>${v["USD"]:,.2f}</b>' if v["USD"] else "") + '</span>'
            for k, v in sorted(cs.get("by_broker", {}).items(),
                               key=lambda x: -x[1]["krw_total"]))
        cashc = (f'<div class="card"><h2>현금 · 총자산</h2><div class="hero">'
                 f'<div><div class="lb">총자산 (주식+현금)</div>'
                 f'<div class="bg" id="hNet">{t.get("net_worth_krw", t["market_value_krw"]):,}원</div></div>'
                 f'<div><div class="lb">현금 합계</div>'
                 f'<div class="bg s" id="hCash">{cs["total_krw"]:,}원</div></div>'
                 f'<div><div class="lb">원화</div><div class="bg s">{cs["KRW"]:,}원</div></div>'
                 f'<div><div class="lb">달러</div><div class="bg s">${cs["USD"]:,.2f}</div></div>'
                 f'</div><div class="chips" style="margin-top:14px">{chips}</div></div>')

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

    body = f"""<header><h1>승훈님의 주식 포트폴리오</h1>
<div class="sb"><span id="live">시세 불러오는 중</span>
<button id="refresh" title="지금 다시 조회">새로고침</button>
<span id="fresh"></span>
<span id="hFx">환율 {t.get('usdkrw','-')}원</span><span>장기 보유 관점</span></div></header>
{hero}{cashc}{alloc}{idxc}
<div class="card"><h2>보유 종목 {t['positions_count']}개 · 증권사 합산</h2>
<table class="resp"><thead><tr><th>종목</th><th>비중</th><th>현재가</th><th>전일비</th><th>수익률</th>
<th>평가금액</th><th>3개월</th><th>1년</th><th>52주</th><th></th></tr></thead><tbody>{rows}</tbody></table>
<div class="cards">{cards}</div></div>
{fail}"""
    return shell("index.html", d, body, live_js(d))


# ── 2. 뉴스 ─────────────────────────────────────────────────
def page_news(d):
    news = d.get("news") or {}
    meta = {m["ticker"]: m for m in d.get("consolidated", [])}

    def item_html(n):
        ko, orig = n.get("title_ko"), n.get("title", "")
        sub = f'<div class="no">{escape(orig)}</div>' if ko else ""
        return (f'<li><a href="{escape(n.get("url") or "#")}" target="_blank" rel="noopener">'
                f'<span class="nt">{escape(ko or orig)}</span>{sub}'
                f'<span class="ns">{escape(n.get("publisher") or "")}</span></a></li>')

    def group(market):
        rows = [(tk, v) for tk, v in news.items()
                if (meta.get(tk, {}).get("market") or "US") == market]
        rows.sort(key=lambda kv: -(meta.get(kv[0], {}).get("weight_pct") or 0))
        out = []
        for i, (tk, v) in enumerate(rows):
            m = meta.get(tk, {})
            w_ = m.get("weight_pct")
            roi = m.get("roi_pct")
            out.append(
                f'<details class="nd"{" open" if i == 0 else ""}><summary data-tk="{escape(tk)}">'
                f'<span class="nn">{escape(v["name"])}</span>'
                f'<span class="ntk">{escape(tk)}</span>'
                + (f'<span class="nw">{w_:.1f}%</span>' if w_ else "")
                + (f'<span class="nr {c(roi)}" data-f="nr">{p(roi)}</span>' if roi is not None else "")
                + f'<span class="nc">{len(v["items"])}건</span>'
                f'<span class="nx"></span></summary>'
                f'<ul class="nl">{"".join(item_html(n) for n in v["items"])}</ul></details>')
        if not out:
            return ""
        label = "한국 주식" if market == "KR" else "미국 주식"
        return (f'<div class="card"><h2>{label} <span class="tk">{len(out)}종목</span></h2>'
                f'{"".join(out)}</div>')

    kr, us = group("KR"), group("US")
    empty = ('<div class="card"><p class="em">수집된 뉴스가 없습니다.</p></div>')

    total = sum(len(v["items"]) for v in news.values())
    tcount = sum(1 for v in news.values() for n in v["items"] if n.get("title_ko"))

    css = """<style>
.nd{border-bottom:1px solid var(--line)}
.nd:last-child{border-bottom:none}
summary{display:flex;align-items:center;gap:9px;padding:14px 2px;cursor:pointer;
list-style:none;user-select:none}
summary::-webkit-details-marker{display:none}
summary:hover .nn{color:var(--c1)}
.nn{font-weight:600;font-size:14.5px;flex:0 1 auto;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.ntk{color:var(--dim);font-size:11px;font-variant-numeric:tabular-nums}
.nw{color:var(--dim);font-size:11.5px;margin-left:auto;font-variant-numeric:tabular-nums}
.nr{font-size:12px;font-weight:600;font-variant-numeric:tabular-nums;min-width:58px;text-align:right}
.nc{color:var(--dim);font-size:11px;border:1px solid var(--line);border-radius:20px;padding:1px 8px}
.nx{width:9px;height:9px;border-right:1.6px solid var(--dim);border-bottom:1.6px solid var(--dim);
transform:rotate(45deg);margin:-4px 3px 0 2px;transition:transform .15s;flex:0 0 auto}
.nd[open] .nx{transform:rotate(225deg);margin-top:2px}
.nl{list-style:none;margin:0 0 10px;padding:0 0 0 2px}
.nl li{border-top:1px solid var(--line)}
.nl a{display:block;padding:11px 2px;color:var(--txt);text-decoration:none}
.nl a:hover .nt{text-decoration:underline}
.nt{display:block;font-size:14px;font-weight:500;line-height:1.45}
.no{color:var(--dim);font-size:11.5px;margin-top:3px;line-height:1.4}
.ns{display:block;color:var(--dim);font-size:11px;margin-top:5px}
@media(max-width:760px){
 .nw{display:none}
 .nn{font-size:14px}
 .nr{min-width:52px;font-size:11.5px;margin-left:auto}
}
</style>"""

    body = f"""{css}<header><h1>뉴스</h1>
<div class="sb"><span id="fresh">갱신 확인 중</span><span>{total}건</span>
<span>{tcount}건 한글 번역</span><span>종목을 누르면 펼쳐집니다</span></div></header>
{kr}{us}{"" if (kr or us) else empty}"""
    return shell("news.html", d, body, live_js(d))


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


def day_txs():
    """거래 원장 전체를 읽어옵니다 (없으면 빈 리스트)."""
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "transactions.json")
    if not os.path.exists(p):
        return []
    try:
        d = json.load(open(p, encoding="utf-8"))
    except Exception:
        return []
    return d.get("transactions", []) if isinstance(d, dict) else d


def _num(v):
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def _chip(label, val, cls):
    return (f'<span class="chip">{escape(label)} '
            f'<span class="{cls}">{escape(val)}</span></span>')


MARK_LABEL = {"deposit": "입금", "withdraw": "출금", "dividend": "배당", "fee": "수수료"}
MARK_SIGN = {"deposit": "+", "withdraw": "-", "dividend": "+", "fee": "-"}
MARK_CLS = {"deposit": "up", "withdraw": "down", "dividend": "up", "fee": "down"}


def day_marks(txs, d0, d1):
    """d0 다음날 ~ d1 사이의 거래를 요약 칩으로 만듭니다 (매수·매도·환전·입금 등)."""
    sel = [t for t in txs if d0 < (t.get("date") or "") <= d1]
    if not sel:
        return ""
    chips = []
    money = {}
    for t in sel:
        ty = t.get("type")
        if ty in MARK_LABEL:
            cur = (t.get("currency") or "KRW").upper()
            money[(ty, cur)] = money.get((ty, cur), 0.0) + _num(t.get("amount"))
    for ty in ("deposit", "withdraw", "dividend", "fee"):
        for cur in ("KRW", "USD"):
            amt = money.get((ty, cur), 0.0)
            if not amt:
                continue
            val = (f"{MARK_SIGN[ty]}{amt:,.0f}원" if cur == "KRW"
                   else f"{MARK_SIGN[ty]}${amt:,.2f}")
            chips.append(_chip(MARK_LABEL[ty], val, MARK_CLS[ty]))
    for t in sel:
        ty = t.get("type")
        if ty in ("buy", "sell"):
            sh = _num(t.get("shares"))
            nm = t.get("name") or t.get("ticker") or ""
            qty = f" {sh:,.0f}주" if sh else ""
            chips.append(_chip("매수" if ty == "buy" else "매도",
                               f"{nm}{qty}", "up" if ty == "buy" else "down"))
        elif ty == "fx":
            frm = (t.get("from") or "KRW").upper()
            to = (t.get("to") or "USD").upper()
            amt, rate = _num(t.get("amount")), _num(t.get("rate"))
            src = f"{amt:,.0f}원" if frm == "KRW" else f"${amt:,.2f}"
            got = ""
            if rate > 0:
                if frm == "KRW" and to == "USD":
                    got = f" → ${amt / rate:,.2f}"
                elif frm == "USD" and to == "KRW":
                    got = f" → {amt * rate:,.0f}원"
            chips.append(_chip("환전", f"{src}{got}", "flat"))
    if not chips:
        return ""
    return '<div class="chips marks">' + "".join(chips) + "</div>"


def rec_at(f):
    """스냅샷이 기록된 시각 (HH:MM)."""
    at = f.get("at") or ""
    return f' · {escape(at[11:16])} 기록' if len(at) >= 16 else ""


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

    ctxs = day_txs()
    days = []
    for f in diffs[:60]:
        movers = [m for m in f["moves"] if m.get("d_val")]
        mv = "".join(
            f'<div class="mv"><span class="mvn">{escape(m["name"][:20])}</span>'
            f'<span class="n {c(m.get("d_roi"))}">{p(m.get("d_roi"))}</span>'
            f'<span class="n {c(m.get("d_val"))}">{w(m.get("d_val"))}원</span></div>'
            for m in movers) or '<p class="em">종목별 변동 없음</p>'
        newly = "".join(f'<span class="chip">신규 {escape(m["name"])}</span>'
                        for m in f["moves"] if m.get("new"))
        gone = "".join(f'<span class="chip">제외 {escape(m["name"])}</span>' for m in f["removed"])
        extra = f'<div class="chips">{newly}{gone}</div>' if (newly or gone) else ""
        days.append(
            f'<details class="card day"><summary>'
            f'<div class="dh">'
            f'<div><b class="dd">{escape(f["date"])}</b>'
            f'<span class="s2">{escape(f["prev_date"])} 대비{rec_at(f)}</span></div>'
            f'<div class="dv {c(f["d_total"])}">{w(f["d_total"])}원'
            f'<span class="dp">{p(f["d_total_pct"])}</span></div></div>'
            f'<div class="dsub">총 {f["total"]:,}원 · 수익률 {p(f["roi"])} '
            f'(<span class="{c(f["d_roi"])}">{p(f["d_roi"])}</span>) · '
            f'환율 {f["fx"]:,.2f} (<span class="{c(f["d_fx"])}">{f["d_fx"]:+.2f}</span>)</div>'
            f'{day_marks(ctxs, f["prev_date"], f["date"])}'
            f'<span class="dx">종목별 변화 {len(movers)}건</span>'
            f'</summary>'
            f'<div class="dbody">{mv}{extra}</div>'
            f'</details>')

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
.chips{margin-top:10px}.marks{margin:0 0 8px}
details.day summary{display:block;list-style:none;cursor:pointer}
details.day summary::-webkit-details-marker{display:none}
.dx{color:var(--dim);font-size:11.5px}
.dx::after{content:" ▾"}
details.day[open] .dx::after{content:" ▴"}
.dbody{margin-top:10px;padding-top:10px;border-top:1px solid var(--line)}
</style>"""

    body = f"""{css}<header><h1>일별 변화</h1>
<div class="sb"><span id="fresh">갱신 확인 중</span><span>최근 {len(diffs)}일 비교</span></div></header>
{summary}{chart}{"".join(days)}"""
    return shell("history.html", d, body)


# ── 4. 거래 입력 ─────────────────────────────────────────────
def page_add(d):
    C = d.get("consolidated", [])
    brokers = sorted({b.split()[0] for m in C for b in (m.get("brokers") or [])})
    opts = "".join(f'<option value="{escape(m["ticker"])}" data-name="{escape(m["name"])}" '
                   f'data-market="{m["market"]}">{escape(m["name"])}</option>' for m in C)
    bopts = "".join(f'<option>{escape(b)}</option>' for b in brokers)

    css = """<style>
form{max-width:520px}
.fg{margin-bottom:14px}
label{display:block;font-size:12px;color:var(--dim);margin-bottom:5px;font-weight:600}
input,select,textarea{width:100%;padding:10px 12px;border:1px solid var(--line);border-radius:9px;
background:var(--bg);color:var(--txt);font:15px/1.4 inherit;font-family:inherit}
input:focus,select:focus{outline:none;border-color:var(--c1)}
.row{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.row3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px}
.types{display:flex;flex-wrap:wrap;gap:7px;margin-bottom:18px}
.types button{padding:9px 15px;border:1px solid var(--line);background:var(--bg);color:var(--dim);
border-radius:20px;font-size:13.5px;cursor:pointer;font-family:inherit;font-weight:600}
.types button.on{background:var(--c1);border-color:var(--c1);color:#fff}
.save{width:100%;padding:14px;border:none;border-radius:10px;background:var(--c1);color:#fff;
font-size:15px;font-weight:700;cursor:pointer;font-family:inherit;margin-top:4px}
.save:disabled{opacity:.5;cursor:default}
#msg{margin-top:12px;font-size:13.5px;padding:11px 13px;border-radius:9px;display:none}
#msg.ok{display:block;background:rgba(63,185,132,.13);color:var(--c3);border:1px solid var(--c3)}
#msg.err{display:block;background:rgba(229,72,77,.11);color:var(--up);border:1px solid var(--up)}
.hide{display:none}
.rt2{font-size:12.5px;border-collapse:collapse;width:100%}
.rt2 td{padding:8px 6px;border-bottom:1px solid var(--line)}
.rt2 .r{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.hint{color:var(--dim);font-size:11.5px;margin-top:5px}
</style>"""

    js = """<script>
(function(){
 var T='buy', pw='';
 var el=function(i){return document.getElementById(i);};
 var LABEL={buy:'매수',sell:'매도',deposit:'입금',withdraw:'출금',fx:'환전',dividend:'배당',fee:'수수료'};

 function show(){
  var stock=(T==='buy'||T==='sell'), fx=(T==='fx'), amt=!stock&&!fx;
  el('gStock').className=stock?'':'hide';
  el('gFx').className=fx?'':'hide';
  el('gAmt').className=amt?'':'hide';
  el('btnSave').textContent=LABEL[T]+' 저장';
  var bs=document.querySelectorAll('.types button');
  for(var i=0;i<bs.length;i++) bs[i].className=(bs[i].dataset.t===T)?'on':'';
 }
 document.querySelectorAll('.types button').forEach(function(b){
   b.onclick=function(){T=b.dataset.t;show();};
 });
 // 보유 종목을 고르면 종목명·시장을 자동으로 채우고, 새 종목이면 그대로 둡니다
 el('ticker').oninput=function(){
   var v=el('ticker').value.trim();
   if(/^[A-Za-z.\\-]+$/.test(v)){ v=v.toUpperCase(); el('ticker').value=v; }
   var o=document.querySelector('#tklist option[value="'+v.replace(/"/g,'')+'"]');
   if(o){ el('name').value=o.dataset.name; el('market').value=o.dataset.market; }
   else if(v){ el('market').value=/^\\d{6}$/.test(v)?'KR':'US'; }
 };
 function msg(t,cls){var m=el('msg');m.textContent=t;m.className=cls;}

 function collect(){
  var tx={type:T,date:el('date').value,broker:el('broker').value,memo:el('memo').value};
  if(T==='buy'||T==='sell'){
   tx.ticker=el('ticker').value; tx.name=el('name').value; tx.market=el('market').value;
   tx.shares=el('shares').value; tx.price=el('price').value; tx.fee=el('fee').value||0;
  } else if(T==='fx'){
   tx.from=el('fxFrom').value; tx.to=(el('fxFrom').value==='KRW')?'USD':'KRW';
   tx.amount=el('fxAmt').value; tx.rate=el('fxRate').value;
  } else {
   tx.currency=el('cur').value; tx.amount=el('amount').value;
  }
  return tx;
 }

 el('btnSave').onclick=function(){
  pw=el('pw').value;
  if(!pw){msg('비밀번호를 입력해 주세요','err');return;}
  var b=el('btnSave'); b.disabled=true; msg('저장 중...','ok');
  fetch('/api/tx',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({password:pw,tx:collect()})})
   .then(function(r){return r.json();})
   .then(function(j){
     b.disabled=false;
     if(!j.ok){msg('실패: '+j.error,'err');return;}
     msg('저장했습니다. 2~3분 뒤 빌드가 끝나면 포트폴리오에 반영됩니다.','ok');
     el('shares').value='';el('price').value='';el('fee').value='';
     el('amount').value='';el('fxAmt').value='';el('memo').value='';
     load();
   })
   .catch(function(e){b.disabled=false;msg('오류: '+e.message,'err');});
 };

 function load(){
  fetch('/api/tx',{cache:'no-store'}).then(function(r){return r.json();}).then(function(j){
   if(!j.ok){el('recent').innerHTML='<p class="em">'+(j.error||'불러오지 못했습니다')+'</p>';return;}
   var rows=j.recent.map(function(t){
    var what=t.name||t.ticker||((t.from||'')+'→'+(t.to||''))||t.currency||'';
    var num=t.shares?(t.shares+'주 x '+Number(t.price).toLocaleString('ko-KR'))
            :(t.amount?Number(t.amount).toLocaleString('ko-KR'):'');
    return '<tr><td>'+t.date+'</td><td>'+(LABEL[t.type]||t.type)+'</td><td>'+what
      +'</td><td class="r">'+num+'</td><td class="r">'+(t.broker||'')+'</td></tr>';
   }).join('');
   el('recent').innerHTML='<table class="rt2"><tbody>'+rows+'</tbody></table>';
   el('cnt').textContent='전체 '+j.count+'건';
  }).catch(function(){el('recent').innerHTML='<p class="em">불러오지 못했습니다</p>';});
 }
 el('date').value=new Date().toISOString().slice(0,10);
 show(); load();
})();
</script>"""

    body = f"""{css}<header><h1>거래 입력</h1>
<div class="sb"><span>매수·매도·입금·환전을 기록하면 수량·평단·현금이 자동으로 계산됩니다</span></div></header>

<div class="card"><form onsubmit="return false">
<div class="types">
<button data-t="buy" class="on">매수</button><button data-t="sell">매도</button>
<button data-t="deposit">입금</button><button data-t="withdraw">출금</button>
<button data-t="fx">환전</button><button data-t="dividend">배당</button>
<button data-t="fee">수수료</button>
</div>

<div class="row">
<div class="fg"><label>날짜</label><input type="date" id="date"></div>
<div class="fg"><label>증권사</label><select id="broker">{bopts}
<option>미래에셋 ISA</option><option>토스</option><option>Super365</option></select></div>
</div>

<div id="gStock">
<div class="fg"><label>종목코드</label>
<input id="ticker" list="tklist" autocapitalize="characters" autocomplete="off"
 placeholder="해외는 티커 (AAPL), 국내는 6자리 (005930)">
<datalist id="tklist">{opts}</datalist>
<div class="hint">보유 종목은 칸을 누르면 목록에서 고를 수 있고, <b>새 종목은 그냥 타이핑하면 됩니다.</b></div></div>
<div class="row"><div class="fg"><label>종목명</label><input id="name" placeholder="예: Apple / 삼성전자"></div>
<div class="fg"><label>시장</label><select id="market"><option value="KR">국내 (KR)</option><option value="US">해외 (US)</option></select></div></div>
<div class="row3">
<div class="fg"><label>수량</label><input id="shares" type="number" step="any" inputmode="decimal"></div>
<div class="fg"><label>단가</label><input id="price" type="number" step="any" inputmode="decimal"></div>
<div class="fg"><label>수수료</label><input id="fee" type="number" step="any" inputmode="decimal" placeholder="0"></div>
</div>
<div class="hint">단가는 <b>국내는 원, 해외는 달러</b> 기준입니다. 해외 티커를 넣으면 시장이 자동으로 US 로, 6자리 숫자면 KR 로 바뀝니다.</div>
</div>

<div id="gAmt" class="hide">
<div class="row">
<div class="fg"><label>통화</label><select id="cur"><option value="KRW">원화 (KRW)</option><option value="USD">달러 (USD)</option></select></div>
<div class="fg"><label>금액</label><input id="amount" type="number" step="any" inputmode="decimal"></div>
</div></div>

<div id="gFx" class="hide">
<div class="row3">
<div class="fg"><label>방향</label><select id="fxFrom"><option value="KRW">원화 → 달러</option><option value="USD">달러 → 원화</option></select></div>
<div class="fg"><label>파는 금액</label><input id="fxAmt" type="number" step="any" inputmode="decimal"></div>
<div class="fg"><label>적용 환율</label><input id="fxRate" type="number" step="any" inputmode="decimal" placeholder="{d['totals'].get('usdkrw','1400')}"></div>
</div>
<div class="hint">원화 → 달러면 "파는 금액"에 원화를, 달러 → 원화면 달러를 넣으세요.</div>
</div>

<div class="fg"><label>메모 (선택)</label><input id="memo" placeholder=""></div>
<div class="fg"><label>비밀번호</label><input id="pw" type="password" placeholder="Vercel 에 등록한 TX_PASSWORD"></div>
<button class="save" id="btnSave">매수 저장</button>
<div id="msg"></div>
</form></div>

<div class="card"><h2>최근 거래 <span class="tk" id="cnt"></span></h2>
<div id="recent"><p class="em">불러오는 중...</p></div></div>
{js}"""
    return shell("add.html", d, body)


# ── 3-1. 시장 ───────────────────────────────────────────────
IDX_GROUPS = ["지수", "환율", "금리·심리", "원자재"]


def ival(i):
    """지표 값 표기 (단위별)"""
    v, u = i.get("price"), i.get("unit") or ""
    if v is None:
        return "-"
    if u == "%":
        return f"{v:,.2f}%"
    if u == "$":
        return f"${v:,.2f}"
    if u == "원":
        return f"{v:,.2f}원"
    return f"{v:,.2f}"


def page_market(d):
    idx = d.get("indices") or []
    cards = []
    for g in IDX_GROUPS:
        rows = [i for i in idx if (i.get("group") or "지수") == g]
        if not rows:
            continue
        cells = "".join(
            f'<div class="mi"><div class="min">{escape(i["name"])}</div>'
            f'<div class="mip">{ival(i)}</div>'
            f'<div class="mic {c(i.get("chg"))}">{p(i.get("chg"))}'
            f'<span class="mis">1개월 {p(i.get("m1"))} · 1년 {p(i.get("y1"))}</span></div>'
            f'{spark(i.get("spark") or [])}</div>'
            for i in rows)
        cards.append(f'<div class="card"><h2>{escape(g)}</h2>'
                     f'<div class="mig">{cells}</div></div>')

    fng = d.get("fear_greed") or {}
    fg = ""
    if fng.get("score") is not None:
        sc = fng["score"]
        fg = (f'<div class="card"><h2>공포 · 탐욕 지수 <span class="s2">CNN</span></h2>'
              f'<div class="fg"><div class="fgv">{sc}</div><div class="fgw">'
              f'<div class="fgr">{escape(str(fng.get("rating") or "-"))}</div>'
              f'<div class="fgb"><i style="left:{min(100, max(0, sc))}%"></i></div>'
              f'<div class="s2">0 극도의 공포 · 50 중립 · 100 극도의 탐욕</div>'
              f'</div></div><div class="chips">'
              f'<span class="chip">전일 <b>{fng.get("prev")}</b></span>'
              f'<span class="chip">1주 전 <b>{fng.get("w1")}</b></span>'
              f'<span class="chip">1개월 전 <b>{fng.get("m1")}</b></span>'
              f'<span class="chip">1년 전 <b>{fng.get("y1")}</b></span></div></div>')

    nl = ""
    for t in d.get("market_news") or []:
        items = "".join(
            f'<a class="ni" href="{escape(n.get("url") or "#")}" target="_blank" rel="noopener">'
            f'<div class="nt">{escape(n.get("title_ko") or n.get("title") or "")}</div>'
            f'<div class="np">{escape(n.get("publisher") or "")}</div></a>'
            for n in t.get("items") or [])
        if items:
            nl += (f'<div class="card"><h2>{escape(t.get("topic") or "")}</h2>'
                   f'<div class="nl">{items}</div></div>')
    if not nl:
        nl = ('<div class="card"><p class="em">시장 뉴스를 불러오지 못했습니다. '
              '네이버 뉴스 API 키를 확인해 주세요.</p></div>')

    css = """<style>
.mig{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:13px}
.mi{border:1px solid var(--line);border-radius:12px;padding:11px 13px}
.min{color:var(--dim);font-size:12px}
.mip{font-size:18px;font-weight:700;font-variant-numeric:tabular-nums;margin:3px 0 2px}
.mic{font-size:13px;font-weight:600}
.mis{display:block;color:var(--dim);font-size:11px;font-weight:400;margin-top:3px}
.mi .spk{width:100%;height:26px;margin-top:6px;opacity:.75}
.fg{display:flex;align-items:center;gap:18px}
.fgv{font-size:42px;font-weight:800;line-height:1;font-variant-numeric:tabular-nums}
.fgw{flex:1;min-width:0}
.fgr{font-size:15px;font-weight:600;margin-bottom:7px}
.fgb{position:relative;height:8px;border-radius:5px;margin-bottom:7px;
background:linear-gradient(90deg,#2563eb,#22c55e,#eab308,#ef4444)}
.fgb i{position:absolute;top:-4px;width:3px;height:16px;background:var(--txt);
border-radius:2px;transform:translateX(-50%)}
.nl{display:flex;flex-direction:column}
.ni{display:block;padding:9px 0;border-top:1px solid var(--line);
text-decoration:none;color:inherit}
.ni:first-child{border-top:none}
.nt{font-size:13.5px;line-height:1.45}
.np{color:var(--dim);font-size:11px;margin-top:3px}
</style>"""
    body = f"""{css}<header><h1>시장</h1>
<div class="sb"><span id="fresh">갱신 확인 중</span><span>지표 {len(idx)}개</span></div></header>
{"".join(cards)}{fg}{nl}"""
    return shell("market.html", d, body)


def render_all(d, hist, diffs):
    return {"index.html": page_index(d),
            "market.html": page_market(d),
            "news.html": page_news(d),
            "history.html": page_history(d, hist, diffs),
            "add.html": page_add(d)}
