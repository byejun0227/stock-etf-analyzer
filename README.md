# 한국·미국 주식/ETF 펀더멘탈 & 시장환경 분석기

과거 5년 데이터를 기반으로 펀더멘탈 4개 항목 + 시장환경 4개 항목을 평가하는 Streamlit 프로토타입입니다.

## 파일 구조

```
app.py             # Streamlit UI (화면 표시만 담당)
analysis.py        # 순수 계산/점수화 로직 (외부 의존성 없음 → 테스트 대상)
data_sources.py     # yfinance/FRED API 등 외부 데이터 수집
test_analysis.py   # analysis.py 단위테스트 (43개, 표준 unittest만 사용)
requirements.txt   # 필요 패키지 목록
.streamlit/config.toml  # 테마 설정
```

`app.py`는 화면 표시만 하고, `data_sources.py`가 데이터를 가져오면, `analysis.py`가 계산합니다.
이렇게 나눈 이유는 **`analysis.py`는 yfinance/streamlit 없이도 테스트할 수 있게** 하기 위해서입니다.

---

## 1. 로컬에서 실행하기

```bash
pip install -r requirements.txt
streamlit run app.py
```

브라우저가 자동으로 열리며 `http://localhost:8501` 에서 확인할 수 있습니다.

---

## 2. 테스트 실행하기

핵심 로직(점수 계산, 티커 정규화, 등급 판정 등)에 대한 단위테스트가 포함되어 있습니다.
yfinance나 streamlit 설치 없이도 실행 가능합니다 (pandas/numpy만 있으면 됩니다).

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
> 배포 전에는 `streamlit run app.py`로 직접 몇 개 종목을 조회해 정상 동작을 확인하시길 권장합니다.

---

## 3. 웹에 배포하기 (Streamlit Community Cloud, 무료)

가장 쉬운 방법은 Streamlit이 공식 제공하는 무료 호스팅입니다. 공개 저장소 기준으로 카드 등록 없이 배포됩니다.

1. 이 폴더를 GitHub 저장소에 올립니다 (public 저장소 권장 — free tier는 공개 앱만 지원)
   ```bash
   git init
   git add .
   git commit -m "최초 커밋"
   git remote add origin <본인의 GitHub 저장소 URL>
   git push -u origin main
   ```
2. https://share.streamlit.io 접속 → GitHub 계정으로 로그인
3. **"Create app"** → **"Deploy a public app from GitHub"** 선택
4. Repository / Branch / 메인 파일 경로(`app.py`)를 지정
5. **Advanced settings**에서 FRED API 키를 Secrets로 등록 (선택):
   ```toml
   FRED_API_KEY = "발급받은_키"
   ```
   등록해두면 앱이 `os.environ.get("FRED_API_KEY")`로 자동으로 읽어옵니다. (코드 수정 불필요)
6. **Deploy** 클릭 → 1~3분 후 `https://<your-app-name>.streamlit.app` 형태의 공개 URL이 발급됩니다.

이후 GitHub 저장소에 커밋을 푸시할 때마다 앱이 자동으로 재배포됩니다.

### 무료 티어 참고사항
- 앱은 반드시 **공개(public)** 상태여야 합니다.
- 앱당 리소스 한도는 약 2.7GB이며, 개인 계정 기준 비공개 앱은 1개까지 가능합니다.
- FRED API 키처럼 민감한 값은 코드에 직접 넣지 말고 반드시 Secrets 기능을 사용하세요.

### 다른 배포 옵션
Streamlit Community Cloud 외에도 Docker로 패키징해 AWS/GCP/Azure의 컨테이너 서비스나 Hugging Face Spaces,
Render/Railway 등에 배포할 수 있습니다. 개인 프로토타입 단계에서는 Community Cloud가 가장 간단합니다.

---

## 알려진 한계

- yfinance 무료 API는 재무제표를 최근 4개년 정도만 제공합니다 (5년 전체는 유료 API 필요할 수 있음)
- 한국 개별주식은 yfinance의 재무데이터 커버리지가 낮습니다 — 정확한 판단은 DART 공시 원문을 확인하세요
- 시장환경 분석(경기동향/통화정책/지정학)은 현재 미국 매크로 지표만 사용합니다 — 한국 종목에는 근사치로만 참고하세요
- 점수/등급은 규칙 기반 근사치이며 투자 조언이 아닙니다
