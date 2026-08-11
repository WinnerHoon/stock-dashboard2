# -*- coding: utf-8 -*-
"""
카카오톡 '나에게 보내기' 발송
필요한 시크릿: KAKAO_REST_KEY, KAKAO_REFRESH_TOKEN
없으면 조용히 건너뜁니다 (사이트 빌드는 정상 진행).

메시지당 200자 제한이 있어 3통으로 나눠 보냅니다.
"""

import os

TOKEN_URL = "https://kauth.kakao.com/oauth/token"
SEND_URL = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
LIMIT = 200


def _man(v):
    return f"{round(v/10000):,}만"


def _sg(v):
    return "-" if v is None else f"{v:+.1f}%"


def compose(d):
    """3통 구성. 각 통 200자 이내."""
    t, a = d["totals"], d["allocation"]
    C = d["consolidated"]
    date = d["date"][5:].replace("-", "/")

    m1 = (f"📊 {date} 포트폴리오\n"
          f"총 {_man(t['market_value_krw'])}원 ({_sg(t['roi_pct'])})\n"
          f"평가손익 {'+' if t['pl_krw']>=0 else ''}{_man(t['pl_krw'])}원")
    if t.get("delta_krw") is not None:
        m1 += f" / 전일 {'+' if t['delta_krw']>=0 else ''}{_man(t['delta_krw'])}"
    m1 += (f"\n국내{a['국내']:.0f}% 해외{a['해외']:.0f}% · ETF{a['ETF']:.0f}%\n"
           f"환율 {t['usdkrw']:,.0f}원")

    m2 = "📈 비중 상위\n" + "\n".join(
        f"{m['name'][:11]} {m['weight_pct']:.0f}% {_sg(m['roi_pct'])}"
        for m in C[:5])

    lines = []
    heads = []
    for v in list(d.get("news", {}).values())[:2]:
        if v["items"]:
            heads.append(f"· {v['items'][0]['title'][:38]}")
    if heads:
        lines.append("📰 뉴스\n" + "\n".join(heads))
    best = max(C, key=lambda x: x["roi_pct"] or -1e9)
    worst = min(C, key=lambda x: x["roi_pct"] or 1e9)
    lines.append(f"💡 관찰 포인트\n"
                 f"최고 {best['name'][:11]} {_sg(best['roi_pct'])}\n"
                 f"최저 {worst['name'][:11]} {_sg(worst['roi_pct'])}\n"
                 f"(투자 권유 아님)")
    m3 = "\n\n".join(lines)

    return [m[:LIMIT - 3] + "..." if len(m) > LIMIT else m for m in (m1, m2, m3)]


def _access_token():
    import requests
    key, rt = os.getenv("KAKAO_REST_KEY"), os.getenv("KAKAO_REFRESH_TOKEN")
    if not (key and rt):
        return None
    r = requests.post(TOKEN_URL, timeout=15, data={
        "grant_type": "refresh_token", "client_id": key, "refresh_token": rt})
    r.raise_for_status()
    return r.json().get("access_token")


def send_brief(d):
    import json
    import requests
    try:
        tok = _access_token()
    except Exception as e:
        print(f"  ! 카카오 토큰 발급 실패: {type(e).__name__}: {str(e)[:110]}")
        return
    if not tok:
        print("  · 카카오 시크릿 없음 — 발송 건너뜀")
        return

    for i, msg in enumerate(compose(d), 1):
        try:
            r = requests.post(SEND_URL, timeout=15,
                              headers={"Authorization": f"Bearer {tok}"},
                              data={"template_object": json.dumps({
                                  "object_type": "text", "text": msg,
                                  "link": {"web_url": os.getenv("SITE_URL", "https://github.com")}
                              }, ensure_ascii=False)})
            if r.status_code == 200:
                print(f"  ✓ 카톡 {i}/3 발송 ({len(msg)}자)")
            else:
                print(f"  ! 카톡 {i}/3 실패 {r.status_code}: {r.text[:110]}")
        except Exception as e:
            print(f"  ! 카톡 {i}/3 오류: {type(e).__name__}: {str(e)[:110]}")
