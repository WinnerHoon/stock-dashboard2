# 아침 주식 브리핑

매일 아침 8시(KST), GitHub Actions가 자동으로:

1. **FinanceDataReader / yfinance** 로 보유 종목 시세 수집
2. **네이버 뉴스 API** (국내) + **yfinance** (해외) 로 뉴스 수집
3. 정적 사이트 생성 → **GitHub Pages** 배포
4. **카카오톡 '나에게 보내기'** 로 브리핑 3통 발송

내 PC가 꺼져 있어도, 어떤 앱이 닫혀 있어도 GitHub 클라우드에서 돌아갑니다.

---

## ⚠️ 먼저 읽어주세요 — 사이트는 공개됩니다

**GitHub Pages는 개인 계정에서 비공개 사이트를 만들 수 없습니다.**
저장소를 private으로 두고 유료 Pro 플랜을 써도 **배포된 사이트 자체는 누구나 볼 수 있습니다.**
접근 제어는 Enterprise Cloud 조직 전용 기능입니다.

이 페이지에는 보유 종목과 총 평가금액이 들어갑니다. 선택지는 셋입니다.

| 방법 | 진짜 비공개? | 난이도 |
|---|---|---|
| **A. Cloudflare Pages + Access** | ✅ 예 | 15분, 무료 |
| **B. 금액 숨김 모드** | 부분적 (비중·%만 노출) | 5분 |
| **C. 그냥 공개** | ❌ 아니오 | 0분 |

`<meta name="robots" content="noindex,nofollow">` 는 넣어뒀지만, 이건 검색엔진에게 부탁하는 것일 뿐
**주소를 아는 사람은 누구나 볼 수 있습니다.**

### A. Cloudflare Access로 진짜 비공개 만들기 (권장)

1. [dash.cloudflare.com](https://dash.cloudflare.com) 가입 (무료)
2. **Workers & Pages → Create → Pages → Connect to Git** → 이 저장소 선택
   - Build command: `pip install -r requirements.txt && python build.py`
   - Build output directory: `dist`
3. **Zero Trust → Access → Applications → Add an application → Self-hosted**
   - 도메인: 방금 만든 `*.pages.dev` 주소
   - Policy: `Action: Allow` / `Include: Emails` → 본인 이메일 입력
4. 끝. 이제 그 주소는 본인 이메일로 일회용 코드를 받아야만 열립니다.

Zero Trust 무료 플랜은 사용자 50명까지 지원합니다. 이 경우 GitHub Pages 배포는 꺼도 됩니다.

### B. 금액 숨김 모드

총액·평가금액·손익을 빼고 **비중(%)과 수익률(%)만** 표시합니다.
누가 주소를 알아내도 얼마를 가졌는지는 알 수 없습니다. 필요하면 요청하세요 — 코드에 옵션을 추가하겠습니다.

---

## 설치

### 1. 저장소에 파일 올리기

이 폴더의 내용을 전부 저장소에 올립니다. GitHub 웹에서 해도 됩니다:

**Add file → Upload files** → 폴더 내용 전체 드래그 → Commit

> `.github/workflows/daily.yml` 은 숨김 폴더라 드래그가 안 될 수 있습니다.
> 그럴 땐 **Add file → Create new file** 로 경로에 `.github/workflows/daily.yml` 을
> 직접 입력하고 내용을 붙여넣으세요.

### 2. GitHub Pages 켜기

**Settings → Pages → Source: `GitHub Actions`** 선택

### 3. Actions 권한 확인

**Settings → Actions → General → Workflow permissions**
→ **Read and write permissions** 선택 후 저장
(워크플로가 `dist/data.json` 을 커밋해야 '전일 대비'가 계산됩니다)

### 4. 시크릿 등록 (전부 선택사항)

**Settings → Secrets and variables → Actions → New repository secret**

| 시크릿 | 용도 | 없으면 |
|---|---|---|
| `NAVER_CLIENT_ID` | 국내 종목 뉴스 | 국내 뉴스만 비어 있음 |
| `NAVER_CLIENT_SECRET` | 〃 | 〃 |
| `KAKAO_REST_KEY` | 카톡 발송 | 카톡 발송 안 함 |
| `KAKAO_REFRESH_TOKEN` | 〃 | 〃 |
| `KRX_ID` / `KRX_PW` | pykrx PER·PBR·배당 | 해당 지표만 비어 있음 |

**하나도 없어도 사이트는 정상 생성됩니다.** 먼저 사이트부터 띄우고 나중에 붙여도 됩니다.

<details>
<summary>네이버 뉴스 API 키 받기</summary>

1. [developers.naver.com/apps/#/register](https://developers.naver.com/apps/#/register)
2. 애플리케이션 이름 아무거나 → 사용 API: **검색** 선택
3. 환경: **WEB 설정** → URL 아무거나 (`https://example.com`)
4. 발급된 Client ID / Client Secret 을 시크릿에 등록
</details>

<details>
<summary>카카오톡 '나에게 보내기' 토큰 받기</summary>

1. [developers.kakao.com](https://developers.kakao.com) → 애플리케이션 추가
2. **앱 키 → REST API 키** 를 `KAKAO_REST_KEY` 로 등록
3. **카카오 로그인 활성화 ON**, Redirect URI `https://example.com/oauth` 등록
4. **동의항목 → 카카오톡 메시지 전송(`talk_message`)** 을 필수 동의로 설정
5. 브라우저에서 아래 주소 접속 후 로그인 → 리다이렉트된 URL의 `code=` 값 복사
   ```
   https://kauth.kakao.com/oauth/authorize?client_id={REST_API_키}&redirect_uri=https://example.com/oauth&response_type=code&scope=talk_message
   ```
6. 그 코드로 refresh token 발급:
   ```
   curl -X POST https://kauth.kakao.com/oauth/token \
     -d "grant_type=authorization_code" \
     -d "client_id={REST_API_키}" \
     -d "redirect_uri=https://example.com/oauth" \
     -d "code={복사한_코드}"
   ```
7. 응답의 `refresh_token` 을 `KAKAO_REFRESH_TOKEN` 으로 등록

> refresh token 유효기간은 2개월입니다. 사용할 때마다 갱신되므로 매일 돌면 만료되지 않습니다.
> 이 값은 본인만 다뤄야 하는 자격증명입니다 — 저장소 코드에 절대 직접 적지 마세요.
</details>

### 5. 실행

**Actions 탭 → 아침 주식 브리핑 → Run workflow** 로 수동 실행해 확인합니다.
이후 평일 오전 8시에 자동으로 돕니다.

---

## 보유 종목 수정

`portfolio.json` 만 고치면 됩니다. 커밋하면 자동으로 다시 빌드됩니다.

```json
{
  "market": "KR",          // KR=국내, US=해외
  "ticker": "005930",      // 국내는 6자리, 해외는 티커
  "name": "삼성전자",
  "shares": 10,
  "avg_price": 72000,      // 국내=원, 해외=달러
  "broker": "토스"
}
```

같은 종목을 여러 증권사에 나눠 보유해도 됩니다 — **자동으로 합산**해서 실제 비중을 보여줍니다.
현재 META·SPYM·NVDA·메리츠금융지주가 그렇게 잡혀 있습니다.

> **해외 종목 평단 주의**: `avg_price`는 달러 기준입니다.
> 현재 값은 원화 평단을 1,430원/USD로 나눈 환산값이라 수익률이 근사치입니다.
> 증권사 앱의 달러 평단을 그대로 넣으면 더 정확해집니다.

---

## 로컬에서 테스트

```bash
pip install -r requirements.txt
python build.py --mock        # 네트워크 없이 가짜 데이터로 화면만 확인
python build.py --no-kakao    # 실제 시세, 카톡은 안 보냄
```

`dist/index.html` 을 브라우저로 열면 됩니다.

---

## 파일 구성

| 파일 | 역할 |
|---|---|
| `portfolio.json` | **보유 종목 — 여기만 고치면 됨** |
| `build.py` | 시세 수집 · 합산 · 손익 계산 |
| `render.py` | HTML 생성 |
| `news.py` | 네이버/야후 뉴스 |
| `kakao.py` | 카톡 3통 발송 |
| `.github/workflows/daily.yml` | 매일 아침 자동 실행 |
| `dist/` | 생성 결과 (사이트) |

---

## 장기 투자 관점 지표

`settings.style`이 `long_term`이라 일간 등락보다 아래를 중심으로 봅니다.

- **종목 합산** — 증권사에 나눠 산 같은 종목을 하나로 합쳐 실제 비중 표시
- **비중** — 전체에서 차지하는 %
- **3개월 · 6개월 · 1년 수익률** — 중장기 추세
- **52주 위치** — 52주 최저~최고 밴드에서 현재가 위치
- **60일 · 200일 이동평균**
- **자산 배분** — 국내/해외, ETF/개별주, 증권사별

카톡 3통은 메시지당 200자 제한 때문입니다 (카카오 API 제약). 상세는 사이트에서 봅니다.

---

## 문제 해결

**특정 종목만 "시세 조회 실패"**
티커 확인. 국내는 6자리(`005930`), 해외는 거래소 티커(`AAPL`). 사이트 하단에 실패 종목이 표시됩니다.

**"전일 대비"가 안 나옴**
직전 실행의 `dist/data.json` 이 있어야 합니다. 이틀째부터 표시됩니다.
계속 안 나오면 Actions 쓰기 권한(설치 3단계)을 확인하세요.

**Actions는 성공했는데 사이트가 안 열림**
Settings → Pages 에서 Source가 `GitHub Actions` 인지 확인.

**카톡이 안 옴**
Actions 로그에서 `카톡 n/3` 줄 확인. refresh token 만료(2개월 미사용)가 가장 흔한 원인입니다.

---

## 면책

정보 정리용 도구입니다. 투자 권유나 자문이 아니며 데이터 지연·오류 가능성이 있습니다.
투자 판단과 그 결과는 본인 책임입니다.
