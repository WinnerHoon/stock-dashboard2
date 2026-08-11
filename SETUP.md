# 설치 따라하기

`https://github.com/WinnerHoon/stock-dashboard` 기준입니다.
브라우저 탭 하나 열어두고 순서대로 따라오세요. 전부 하면 15~20분입니다.

---

## 0단계 · 저장소 준비 (이미 있으면 건너뛰기)

레포가 아직 없다면:

1. [github.com/new](https://github.com/new) 접속
2. **Repository name**: `stock-dashboard`
3. **Private** 선택 (코드는 감춰집니다. 단, 배포된 사이트는 공개 — README 경고 참고)
4. **Add a README file** ✅ 체크 ← **중요**. 체크해야 빈 저장소가 아니게 되어 업로드 버튼이 생깁니다
5. **Create repository**

---

## 1단계 · 파일 업로드

올릴 파일은 **9개**입니다.

```
build.py
render.py
news.py
kakao.py
portfolio.json
requirements.txt
README.md
.gitignore
.github/workflows/daily.yml      ← 이것만 따로 처리
```

### 1-1. 일반 파일 8개 올리기

1. 레포 메인 화면에서 **Add file ▾** → **Upload files**
2. 탐색기에서 `바탕화면\주식\stock-dashboard` 폴더 열기
3. `.github` 폴더를 **뺀** 나머지 8개 파일을 전부 선택 (`Ctrl+A` 후 `.github`만 `Ctrl+클릭`으로 해제)
4. 브라우저 점선 영역으로 **드래그**
5. 아래 **Commit changes** 버튼 클릭

> `README.md`가 이미 있다고 나와도 그냥 덮어쓰면 됩니다.

### 1-2. 워크플로 파일 만들기

`.github` 폴더는 드래그로 안 올라가는 경우가 많습니다. 직접 만듭니다.

1. 레포 메인 → **Add file ▾** → **Create new file**
2. 파일명 칸에 아래를 **그대로** 입력:
   ```
   .github/workflows/daily.yml
   ```
   > `/`를 칠 때마다 폴더가 자동으로 만들어지며 칸이 나뉩니다. 정상입니다.
3. 아래 큰 편집창에 `바탕화면\주식\stock-dashboard\.github\workflows\daily.yml`
   내용을 **전부 복사해서 붙여넣기** (메모장으로 열면 됩니다)
4. 우측 상단 **Commit changes...** → **Commit changes**

**확인**: 레포 메인에 `.github` 폴더가 보이면 성공입니다.

---

## 2단계 · Actions 쓰기 권한 켜기

⚠️ **Pages 설정보다 이걸 먼저** 하세요. 안 하면 첫 실행이 권한 오류로 실패합니다.

1. 레포 상단 **Settings** 탭 (톱니바퀴 아이콘)
2. 왼쪽 사이드바 아래쪽 **Actions** → **General**
3. 페이지 맨 아래 **Workflow permissions** 항목까지 스크롤
4. **Read and write permissions** 라디오 버튼 선택
5. **Save** 클릭

> 이게 필요한 이유: 워크플로가 `dist/data.json`을 저장소에 다시 커밋해야
> 다음 날 "전일 대비"를 계산할 수 있습니다.

---

## 3단계 · Pages 켜기

1. **Settings** → 왼쪽 사이드바 **Pages**
2. **Build and deployment** → **Source** 드롭다운
3. `Deploy from a branch` → **`GitHub Actions`** 로 변경
4. 자동 저장됩니다 (별도 버튼 없음)

> 이 시점엔 "아직 배포된 사이트가 없다"고 나오는 게 정상입니다.

---

## 4단계 · 첫 실행

1. 레포 상단 **Actions** 탭
2. 처음이면 **"I understand my workflows, go ahead and enable them"** 초록 버튼이 뜹니다 → 클릭
3. 왼쪽 목록에서 **아침 주식 브리핑** 클릭
4. 오른쪽 **Run workflow ▾** → 파란 **Run workflow** 버튼
5. 5초쯤 뒤 페이지 새로고침 → 노란 점(진행 중)이 도는 실행 항목이 생깁니다
6. 클릭해서 들어가면 실시간 로그를 볼 수 있습니다

**소요 시간**: 첫 실행은 패키지 설치 때문에 3~5분. 이후엔 1~2분.

### 성공하면

- `build` / `deploy` 두 작업 모두 ✅ 초록 체크
- **Settings → Pages** 상단에 사이트 주소가 뜹니다:
  ```
  https://winnerhoon.github.io/stock-dashboard/
  ```

---

## 자주 막히는 곳

| 증상 | 원인과 해결 |
|---|---|
| Actions 탭에 워크플로가 안 보임 | `.github/workflows/daily.yml` 경로 오타. `workflow`(단수) 아닌 **`workflows`**(복수) 확인 |
| `Permission to ... denied` / `403` | 2단계를 안 했거나 저장을 안 누름. Read and write permissions 재확인 |
| `remote: Write access ... not granted` | 위와 동일 |
| `deploy` 작업이 `Not Found`로 실패 | 3단계 Pages Source가 `GitHub Actions`가 아님 |
| `ModuleNotFoundError` | `requirements.txt` 업로드 누락 |
| `FileNotFoundError: portfolio.json` | `portfolio.json` 업로드 누락 |
| 사이트는 뜨는데 종목이 "시세 조회 실패" | 티커 오타. 국내 6자리, 해외 거래소 티커 |
| 뉴스 칸이 비어 있음 | 정상입니다. 네이버 API 시크릿을 아직 안 넣었을 뿐 |
| 카톡이 안 옴 | 정상입니다. 카카오 시크릿을 아직 안 넣었을 뿐 |

로그에서 에러를 찾는 법: 실패한 작업 클릭 → 빨간 ❌ 표시된 단계 클릭 → 펼쳐진 로그 맨 아래쪽

---

## 5단계 · (선택) 시크릿 넣기

사이트가 잘 뜨는 걸 확인한 다음에 하세요. 하나도 없어도 사이트는 정상 동작합니다.

**Settings → Secrets and variables → Actions → New repository secret**

이름과 값을 넣고 **Add secret**. 넣을 때마다 반복합니다.

| Name | 용도 |
|---|---|
| `NAVER_CLIENT_ID` | 국내 종목 뉴스 |
| `NAVER_CLIENT_SECRET` | 〃 |
| `KAKAO_REST_KEY` | 카톡 발송 |
| `KAKAO_REFRESH_TOKEN` | 〃 |

발급 방법은 `README.md`의 접힌 섹션에 단계별로 적어뒀습니다.

시크릿을 넣은 뒤엔 **Actions → Run workflow**로 다시 한 번 돌려서 확인하세요.

---

## 6단계 · 자동 실행 확인

여기까지 하면 **평일 오전 8시(KST)**에 자동으로 돕니다. 따로 할 건 없습니다.

> GitHub 무료 플랜의 cron은 서버 부하에 따라 **5~30분 지연**될 수 있습니다.
> 8시 정각을 보장하진 않으니, 정확한 시각이 중요하면 cron을 `0 22 * * 0-4`(7시)로
> 앞당겨 두는 편이 낫습니다. `.github/workflows/daily.yml` 3번째 줄 근처를 고치면 됩니다.

또 하나: **60일간 저장소에 아무 커밋이 없으면 GitHub가 스케줄을 자동으로 멈춥니다.**
이 워크플로는 매일 `dist/data.json`을 커밋하므로 해당사항 없습니다.

---

## 보유 종목을 바꾸고 싶을 때

1. 레포에서 `portfolio.json` 클릭
2. 오른쪽 위 연필 아이콘 ✏️
3. 수정 후 **Commit changes**
4. 저장하면 워크플로가 자동으로 다시 돌아 사이트가 갱신됩니다

JSON 문법 주의: 마지막 항목 뒤에는 쉼표가 없어야 하고, 따옴표는 `"` 여야 합니다.
