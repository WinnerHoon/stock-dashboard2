# -*- coding: utf-8 -*-
"""
영문 → 한글 번역

우선순위
  1. DeepL      — DEEPL_API_KEY 시크릿이 있으면 사용 (품질 가장 좋음, 월 50만자 무료)
  2. MyMemory   — 키 불필요 무료 API (일 1,000단어). 익명이라 한도가 작습니다
  3. 원문 유지  — 둘 다 실패하면 번역 없이 원문만 보여줍니다

어떤 경우에도 예외를 밖으로 던지지 않습니다. 번역 실패가 사이트 빌드를 막으면 안 됩니다.
"""

import os
import re
import time

DEEPL_FREE = "https://api-free.deepl.com/v2/translate"
DEEPL_PRO = "https://api.deepl.com/v2/translate"
MYMEMORY = "https://api.mymemory.translated.net/get"

_cache = {}


def _has_hangul(s):
    return bool(re.search(r"[가-힣]", s or ""))


def _deepl(texts):
    key = os.getenv("DEEPL_API_KEY")
    if not key:
        return None
    import requests
    url = DEEPL_FREE if key.endswith(":fx") else DEEPL_PRO
    r = requests.post(url, timeout=20,
                      headers={"Authorization": f"DeepL-Auth-Key {key}"},
                      data=[("text", t) for t in texts] +
                           [("target_lang", "KO"), ("source_lang", "EN")])
    r.raise_for_status()
    return [x["text"] for x in r.json()["translations"]]


def _mymemory(text):
    import requests
    params = {"q": text[:480], "langpair": "en|ko"}
    email = os.getenv("MYMEMORY_EMAIL")
    if email:
        params["de"] = email          # 이메일을 넣으면 한도가 5만 단어로 늘어납니다
    r = requests.get(MYMEMORY, params=params, timeout=20)
    r.raise_for_status()
    j = r.json()
    if str(j.get("responseStatus")) != "200":
        raise RuntimeError(str(j.get("responseDetails"))[:80])
    out = (j.get("responseData") or {}).get("translatedText") or ""
    # MyMemory 는 실패 시 경고문을 본문에 담아 돌려주기도 합니다
    if not out or "MYMEMORY WARNING" in out.upper() or "QUERY LENGTH LIMIT" in out.upper():
        raise RuntimeError("사용량 한도 또는 빈 응답")
    return out


def translate_many(texts):
    """영문 리스트 → 한글 리스트. 실패한 항목은 None."""
    texts = [t or "" for t in texts]
    todo = [t for t in texts if t and not _has_hangul(t) and t not in _cache]

    if todo:
        try:
            got = _deepl(todo)
            if got:
                for src, dst in zip(todo, got):
                    _cache[src] = dst
                todo = []
                print(f"  · DeepL 번역 {len(got)}건")
        except Exception as e:
            print(f"  ! DeepL 실패 → MyMemory 로 전환: {type(e).__name__}: {str(e)[:80]}")

    fails = 0
    for t in todo:
        if fails >= 3:                 # 연속 실패하면 한도 소진으로 보고 중단
            break
        try:
            _cache[t] = _mymemory(t)
            fails = 0
            time.sleep(0.4)            # 무료 API 예의상 간격
        except Exception as e:
            fails += 1
            print(f"  ! 번역 실패: {str(e)[:70]}")

    return [(_cache.get(t) if t and not _has_hangul(t) else t) or None for t in texts]


def apply_to_news(news):
    """news 딕셔너리의 제목·요약에 ko 필드를 채웁니다."""
    items = [n for v in news.values() for n in v["items"]]
    if not items:
        return news

    titles = translate_many([n.get("title", "") for n in items])
    for n, ko in zip(items, titles):
        n["title_ko"] = ko if (ko and ko != n.get("title")) else None

    # 요약은 분량이 많아 DeepL 키가 있을 때만 번역합니다
    if os.getenv("DEEPL_API_KEY"):
        summaries = translate_many([n.get("summary", "") for n in items])
        for n, ko in zip(items, summaries):
            n["summary_ko"] = ko if (ko and ko != n.get("summary")) else None

    done = sum(1 for n in items if n.get("title_ko"))
    print(f"  · 뉴스 제목 번역 {done}/{len(items)}건")
    return news
