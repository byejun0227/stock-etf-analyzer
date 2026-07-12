"""
app.py — Streamlit UI (한국·미국 주식/ETF 펀더멘탈 & 시장환경 분석기)

실행 방법:
    pip install -r requirements.txt
    streamlit run app.py

구조:
    - analysis.py      : 순수 계산/점수화 로직 (yfinance/streamlit 의존성 없음, 단위테스트 대상)
    - data_sources.py   : yfinance/FRED API 등 외부 데이터 수집
    - app.py (이 파일)  : Streamlit UI, 위 두 모듈을 불러와 화면에 표시만 함

테스트:
    python -m unittest test_analysis.py -v

배포:
    Streamlit Community Cloud 무료 배포 방법은 README.md 참고
"""

import os

import streamlit as st
import plotly.graph_objects as go

from analysis import (
    KOREAN_ETF_NAME_MAP,
    analyze_internal_factors,
    analyze_financial_ratios,
    analyze_industry,
    analyze_technical,
    score_internal_factors,
    score_financial_ratios,
    score_industry,
    score_technical,
    score_etf_fundamentals,
    score_market_item,
    grade_label,
    compute_overall_score,
)
from data_sources import (
    classify_ticker,
    get_price_history,
    get_financials,
    fetch_etf_raw_data,
    analyze_market_environment,
)

st.set_page_config(page_title="한국·미국 주식/ETF 분석기", layout="wide")

MARKET_LABELS = {
    "경기동향": "경기동향 (경기활황 vs 경기불황)",
    "통화_재정정책": "통화/재정정책 (완화 vs 긴축)",
    "지정학_불확실성": "지정학적 불확실성 (위험발생 vs 위험해소)",
    "자본시장_정책": "자본시장 정책 변화 (긍정 vs 부정)",
}


# =========================================================
# 사이드바
# =========================================================
st.title("📊 한국·미국 주식/ETF 펀더멘탈 & 시장환경 분석기")
st.caption("과거 5년 데이터를 기반으로 펀더멘탈 4개 항목 + 시장환경 4개 항목을 평가하는 프로토타입입니다.")

with st.sidebar:
    st.subheader("설정")
    fred_api_key = st.text_input(
        "FRED API 키",
        value=os.environ.get("FRED_API_KEY", ""),
        type="password",
        help="https://fred.stlouisfed.org/docs/api/api_key.html 에서 무료 발급",
    )
    st.caption("시장환경 분석(경기동향/통화정책/지정학) 계산에 필요합니다. 없으면 해당 항목은 건너뜁니다.")
    st.divider()
    st.caption(
        "**한국 종목 입력 방법**\n"
        "- 6자리 종목코드 직접 입력 (예: 005930 = 삼성전자)\n"
        "- 지원되는 ETF명 직접 입력: " + ", ".join(KOREAN_ETF_NAME_MAP.keys()) + "\n"
        "- 그 외 ETF명은 종목코드로 입력해주세요 (한국거래소 KIND에서 조회 가능)"
    )
    st.divider()
    st.subheader("종합점수 가중치")
    fundamental_weight_pct = st.slider(
        "펀더멘탈 vs 시장환경 비중",
        min_value=0, max_value=100, value=60, step=5,
        help="슬라이더 값이 펀더멘탈 비중(%)입니다. 나머지는 시장환경 비중으로 자동 계산됩니다.",
    )
    st.caption(f"펀더멘탈 {fundamental_weight_pct}% : 시장환경 {100 - fundamental_weight_pct}%")

    with st.expander("시장환경 세부 가중치 (선택)"):
        st.caption("시장환경 4개 항목의 상대적 중요도를 조절합니다. (자동으로 비율 정규화됩니다)")
        w_biz = st.slider("경기동향", 0, 100, 25, key="w_biz")
        w_mon = st.slider("통화/재정정책", 0, 100, 25, key="w_mon")
        w_geo = st.slider("지정학적 불확실성", 0, 100, 25, key="w_geo")
        w_cap = st.slider("자본시장 정책", 0, 100, 25, key="w_cap")
        _w_sum = max(w_biz + w_mon + w_geo + w_cap, 1)
        market_weights = {
            "경기동향": w_biz / _w_sum,
            "통화_재정정책": w_mon / _w_sum,
            "지정학_불확실성": w_geo / _w_sum,
            "자본시장_정책": w_cap / _w_sum,
        }

ticker_input = st.text_input(
    "티커 또는 종목코드를 입력하세요 (예: AAPL, SPY, 005930, KODEX 200)", value="AAPL"
).strip()


# =========================================================
# 분석 실행
# =========================================================
if st.button("분석 시작") and ticker_input:
    with st.spinner("데이터 수집 및 분석 중..."):
        try:
            classification = classify_ticker(ticker_input)
            info = classification["info"]
            ticker_obj = classification["ticker_obj"]
            is_etf = classification["is_etf"]
            market_type = classification["market"]
            currency = classification["currency"]
            resolved_ticker = classification["resolved_ticker"]

            hist = get_price_history(ticker_obj)
            if hist.empty:
                st.error("가격 데이터를 가져오지 못했습니다. 종목코드/티커를 확인해주세요.")
                st.stop()

            st.header(f"{info.get('longName', ticker_input)} ({resolved_ticker})")
            market_label = "🇰🇷 한국" if market_type == "KR" else "🇺🇸 미국"
            st.write(f"**시장**: {market_label} | **유형**: {'ETF' if is_etf else '개별주식'} | **통화**: {currency}")
            if market_type == "KR" and not is_etf:
                st.info("ℹ️ 한국 개별주식은 yfinance의 재무제표 제공 범위가 제한적입니다. "
                        "①②번 항목 일부가 비어있을 수 있으니 DART 공시 원문 확인을 권장합니다.")

            # ---- 시장환경 분석 (산업동향 점수에서 경기국면 참조를 위해 먼저 계산) ----
            market = analyze_market_environment(fred_api_key)
            business_cycle_verdict = market.get("경기동향", {}).get("판정", "")
            if market_type == "KR":
                st.caption(
                    "⚠️ 현재 시장환경 분석은 미국 매크로 지표(FRED, VIX)를 사용합니다. "
                    "한국 시장에 미국 지표를 그대로 적용하는 것은 근사치일 뿐이며, "
                    "정확한 판단을 위해서는 한국은행 ECOS 연동이 필요합니다."
                )

            market_scores = {key: score_market_item(market.get(key, {}).get("판정", "")) for key in MARKET_LABELS}

            # ---- 기술적 분석 ----
            tech = analyze_technical(hist)
            tech_score, tech_score_detail = score_technical(tech)

            # ---- 펀더멘탈 분석 (ETF/개별주 분기) ----
            fundamental_scores = {}
            if is_etf:
                etf_data = fetch_etf_raw_data(ticker_obj, info)
                etf_score, etf_score_detail = score_etf_fundamentals(etf_data, currency)
                fundamental_scores["ETF구성"] = etf_score
            else:
                income, balance, cashflow = get_financials(ticker_obj)
                internal = analyze_internal_factors(balance, income, cashflow)
                internal_score, internal_score_detail = score_internal_factors(balance, income, cashflow)
                fundamental_scores["내부요인"] = internal_score

                ratios = analyze_financial_ratios(income)
                ratios_score, ratios_score_detail = score_financial_ratios(income)
                fundamental_scores["재무지표"] = ratios_score

                industry = analyze_industry(info)
                industry_score, industry_score_detail = score_industry(industry, business_cycle_verdict)
                fundamental_scores["산업동향"] = industry_score

            fundamental_scores["기술적분석"] = tech_score

            # ---- 종합 점수 ----
            overall = compute_overall_score(fundamental_scores, market_scores, market_weights, fundamental_weight_pct)

            st.subheader("🏆 종합 평가")
            b1, b2, b3 = st.columns(3)
            b1.metric("종합 점수", f"{overall['overall_score']}점", overall["grade"])
            b2.metric("펀더멘탈 평균", f"{round(overall['fundamental_avg'])}점")
            b3.metric("시장환경 평균", f"{round(overall['market_avg'])}점")
            if is_etf:
                st.caption("⚠️ ETF는 전통적 재무제표가 없어 운용보수·순자산·집중도 기반 ETF구성 점수로 대체했습니다.")

            radar_labels = list(fundamental_scores.keys()) + [MARKET_LABELS[k].split(" (")[0] for k in MARKET_LABELS]
            radar_values = list(fundamental_scores.values()) + list(market_scores.values())
            radar_fig = go.Figure()
            radar_fig.add_trace(go.Scatterpolar(r=radar_values + [radar_values[0]],
                                                 theta=radar_labels + [radar_labels[0]],
                                                 fill="toself", name="평가 점수"))
            radar_fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                                     showlegend=False, height=420, margin=dict(l=40, r=40, t=30, b=30))
            st.plotly_chart(radar_fig, use_container_width=True)

            st.divider()

            # ---- 펀더멘탈 상세 ----
            if is_etf:
                st.subheader(f"① ETF 구성 분석 — {etf_score}점 (재무제표 대체)")
                st.write(etf_score_detail)
                st.json(etf_data, expanded=False)
            else:
                st.subheader(f"① 기업 내부요인 평가 — {internal_score}점")
                st.write(internal_score_detail)
                st.json(internal, expanded=False)

                st.subheader(f"② 재무지표 평가 — {ratios_score}점")
                st.write(ratios_score_detail)
                st.json(ratios, expanded=False)

                st.subheader(f"③ 산업동향 평가 — {industry_score}점")
                st.write(industry)
                st.write(industry_score_detail)

            st.subheader(f"④ 기술적 분석 — {tech_score}점")
            col1, col2, col3 = st.columns(3)
            col1.metric("추세", tech["추세"])
            col2.metric("RSI(14)", tech["RSI(14)"])
            col3.metric("투자심리", tech["투자심리"])
            st.write(f"**수급(거래량)**: {tech['수급_거래량']}")

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=tech["chart_data"].index, y=tech["chart_data"]["Close"], name="종가"))
            fig.add_trace(go.Scatter(x=tech["chart_data"].index, y=tech["chart_data"]["MA120"], name="MA120(장기추세)"))
            fig.update_layout(height=400, margin=dict(l=20, r=20, t=30, b=20))
            st.plotly_chart(fig, use_container_width=True)

            # ---- 시장환경 상세 ----
            st.subheader("🌍 시장환경 분석")
            cols = st.columns(4)
            for i, (key, label) in enumerate(MARKET_LABELS.items()):
                data = market.get(key, {})
                verdict = data.get("판정") or data.get("안내") or data.get("오류") or "N/A"
                cols[i].metric(f"{label.split(' (')[0]} ({market_scores[key]}점)", verdict)

            for key, label in MARKET_LABELS.items():
                with st.expander(label):
                    st.write(market.get(key, {}))

        except Exception as e:
            st.error(f"분석 중 오류가 발생했습니다: {e}")
            st.info("티커가 올바른지, 또는 yfinance가 해당 종목 데이터를 제공하는지 확인해주세요.")

st.divider()
st.caption(
    "⚠️ 이 도구는 프로토타입이며 투자 조언이 아닙니다. 점수/등급은 규칙 기반 근사치로, "
    "재무데이터는 yfinance 기준이라 실제 공시와 차이가 있을 수 있으니 투자 판단 시 원문 공시를 반드시 확인하세요."
)
