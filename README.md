# 한국·미국 주식/ETF 펀더멘탈 & 시장환경 분석기

과거 5년 데이터를 기반으로 펀더멘탈 4개 항목 + 시장환경 4개 항목을 평가하는 프로토타입입니다.
Next.js(프론트엔드) + Vercel Python Function(분석 백엔드)으로 구성되어 있으며, Vercel에 직접
배포할 수 있습니다.

## 파일 구조

```
app/                        # Next.js App Router (프론트엔드)
  page.tsx                    # 세션 확인 후 로그인/대시보드 분기
  api/auth/*/route.ts         # OAuth 콜백, 관리자 로그인, 로그아웃 (Node.js 런타임)
components/                  # React UI 컴포넌트
lib/                        # i18n, 세션(JWT), OAuth URL 빌더, 타입, 상수
api/
  index.py                    # FastAPI 앱 — POST /api/analyze (Vercel Python Function)
  analysis.py                 # 순수 계산/점수화 로직 (외부 의존성 없음 → 테스트 대상)
  data_sources.py              # yfinance/FRED API 등 외부 데이터 수집
test_analysis.py             # analysis.py 단위테스트 (43개, 표준 unittest만 사용)
requirements.txt             # Python 함수 의존성
vercel.json                  # Python 함수 설정 (maxDuration 등)
```

`analysis.py`/`data_sources.py`는 예전 Streamlit 버전과 동일한 로직이며, `api/index.py`가
프론트엔드 요청을 받아 이 모듈들을 호출해 결과를 JSON으로 반환합니다.

---

## 1. 로컬에서 실행하기

```bash
npm install
pip install -r requirements.txt
cp .env.example .env.local   # 값 채우기 (최소 SESSION_SECRET 필요)
vercel dev
```

`vercel dev`는 Next.js 프론트엔드와 `api/index.py`(Python) Function을 함께 구동합니다.
Vercel CLI가 없다면 `npm i -g vercel`로 설치하세요. `http://localhost:3000`에서 확인할 수 있습니다.

---

## 2. 테스트 실행하기

핵심 로직(점수 계산, 티커 정규화, 등급 판정 등)에 대한 단위테스트가 포함되어 있습니다.
yfinance 설치 없이도 실행 가능합니다 (pandas/numpy만 있으면 됩니다).

```bash
python -m unittest test_analysis.py -v
```

현재 **43개 테스트가 모두 통과**하도록 작성되어 있습니다. 커버 범위:
- 티커 정규화 (한국 종목코드, ETF 이름 매핑, 미국 티커)
- 재무제표 기반 내부요인/재무지표 점수화 (개선/악화 케이스, 데이터 누락 케이스)
- 산업동향 점수화 (성장기/방어적 산업과 경기국면 정합성)
- 기술적분석 (상승/하락 추세, 거래량 급증 감지)
- ETF 스코어링 (통화별 임계값, 데이터 누락 시 중립값)
- 시장환경 판정 → 점수 변환 (긍정/부정/중립 키워드)
- 종합점수 계산 (가중치 반영 여부)

코드를 수정한 뒤에는 이 명령어로 다시 돌려서 회귀(regression)가 없는지 확인하세요.

> `data_sources.py`는 실제 네트워크 호출이 필요해 이 저장소에는 자동테스트가 없습니다.
> 배포 전에는 `vercel dev`로 직접 몇 개 종목을 조회해 정상 동작을 확인하시길 권장합니다.

---

## 3. Vercel에 배포하기

1. GitHub 저장소를 Vercel 프로젝트로 import (Framework Preset: Next.js — 자동 감지됨)
2. **Project Settings → Environment Variables**에 아래 값을 등록 (`.env.example` 참고):
   - `SESSION_SECRET` (필수 — 로그인 세션 서명용 임의의 긴 문자열)
   - `FRED_API_KEY` (선택 — 없으면 시장환경 분석이 "데이터 없음"으로 표시됨)
   - `ADMIN_ID` / `ADMIN_PW` (선택 — 기본값 admin/admin1234)
   - `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`, `KAKAO_REST_API_KEY` (선택 — 없으면 해당 로그인
     버튼이 비활성화된 채로 표시됨)
   - `REDIRECT_URI` = 배포 도메인 (예: `https://your-app.vercel.app`). Google/Kakao 콘솔의
     승인된 리디렉션 URI에는 `${REDIRECT_URI}/api/auth/callback` 을 등록해야 합니다.
3. Deploy

### 알려진 제약
- Python 함수(`api/index.py`)는 종목당 여러 외부 API(yfinance, FRED)를 순차/병렬 호출하므로
  **Hobby 플랜의 10초 실행시간 제한에 걸릴 수 있습니다.** 경쟁사 비교가 포함된 개별주식 분석은
  Pro 플랜(최대 60초, `vercel.json`에서 `maxDuration` 설정) 사용을 권장합니다.
- 서버리스 특성상 워커 인스턴스가 재사용될 때만 유효한 in-memory 캐시를 사용하므로, 매 요청마다
  캐시가 보장되지는 않습니다 (원본 Streamlit의 `st.cache_data`와 동일한 의도의 best-effort 최적화).

---

## 알려진 한계

- yfinance 무료 API는 재무제표를 최근 4개년 정도만 제공합니다 (5년 전체는 유료 API 필요할 수 있음)
- 한국 개별주식은 yfinance의 재무데이터 커버리지가 낮습니다 — 정확한 판단은 DART 공시 원문을 확인하세요
- 시장환경 분석(경기동향/통화정책/지정학)은 현재 미국 매크로 지표만 사용합니다 — 한국 종목에는 근사치로만 참고하세요
- 점수/등급은 규칙 기반 근사치이며 투자 조언이 아닙니다
