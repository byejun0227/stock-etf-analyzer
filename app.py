"""
app.py — Streamlit UI (한국·미국 주식/ETF 펀더멘탈 & 시장환경 분석기)
"""

import os

import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from analysis import (
    KOREAN_ETF_NAME_MAP,
    KOREAN_STOCK_NAME_MAP,
    VALUATION_METRIC_INFO,
    analyze_internal_factors,
    analyze_financial_ratios,
    analyze_industry,
    analyze_technical,
    extract_valuation_metrics,
    compare_valuation_vs_peers,
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
    get_peer_info_list,
    fetch_etf_raw_data,
    analyze_market_environment,
)

st.set_page_config(page_title="한국·미국 주식/ETF 분석기", page_icon="📊", layout="wide")

MARKET_LABELS = {
    "경기동향": "경기동향 (경기활황 vs 경기불황)",
    "통화_재정정책": "통화/재정정책 (완화 vs 긴축)",
    "지정학_불확실성": "지정학적 불확실성 (위험발생 vs 위험해소)",
    "자본시장_정책": "자본시장 정책 변화 (긍정 vs 부정)",
}

MARKET_INDEX_DESC = {
    "US": {
        "경기동향": (
            "**📈 사용 지표 (미국)**\n"
            "- **USSLIND (미국 경기선행지수)** — Conference Board 발표. 향후 6~12개월 경기 방향을 예측하는 종합 선행지표.\n"
            "- **UNRATE (실업률)** — 미국 노동시장 건전성 지표. 하락하면 고용 개선(경기 호황), 상승하면 경기 둔화 신호."
        ),
        "통화_재정정책": (
            "**📈 사용 지표 (미국)**\n"
            "- **FEDFUNDS (미국 기준금리)** — 연준(Fed) 단기 정책금리. 인상 시 긴축, 인하 시 완화.\n"
            "- **M2SL (M2 통화량)** — 광의 통화량. 증가율이 높으면 유동성 확대, 감소하면 긴축 기조."
        ),
        "지정학_불확실성": (
            "**📈 사용 지표 (미국)**\n"
            "- **USEPUINDXD (경제정책 불확실성 지수, EPU)** — 뉴스 기사 빈도 기반 산출. 높을수록 정치·정책 불확실성 확대. "
            "실제 지정학 리스크의 직접 지표는 아닌 정책 불확실성 대리 지표."
        ),
        "자본시장_정책": (
            "**📈 사용 지표 (미국)**\n"
            "- **VIX (CBOE 변동성 지수)** — S&P 500 옵션 기반 시장 기대 변동성. '공포 지수'. "
            "20 이하 시장 안정, 30 이상 높은 불안감. 공매도 규제·세제 등 실제 자본시장 정책의 간접 프록시."
        ),
    },
    "KR": {
        "경기동향": (
            "**📈 사용 지표 (한국)**\n"
            "- **KOSPI 지수 추이** — 6개월 전 대비 등락으로 경기 방향성 파악. 상승하면 경기 회복 기대, 하락하면 둔화 신호.\n"
            "- **한국 실업률 (LRHUTTTTKSM156S)** — OECD 기준 조화 실업률. 하락하면 고용 개선(경기 호황), 상승하면 경기 둔화 신호."
        ),
        "통화_재정정책": (
            "**📈 사용 지표 (한국)**\n"
            "- **한국 기준금리 (IRSTCB01KRM156N)** — 한국은행(BOK) 정책금리. 인상 시 긴축(대출 억제), 인하 시 완화(유동성 공급).\n"
            "- **한국 M2 통화량 (MYAGKRM052S)** — 광의 통화량. YoY 증가율이 높으면 유동성 확대, 감소하면 긴축 기조."
        ),
        "지정학_불확실성": (
            "**📈 사용 지표 (한국)**\n"
            "- **글로벌 EPU 지수 (USEPUINDXD)** — 한국 전용 지정학 지수가 제한적이어서 글로벌(미국) EPU를 대리 지표로 사용. "
            "북한 리스크·한반도 긴장 등 한국 특수 지정학 요인은 뉴스 모니터링 병행 권장."
        ),
        "자본시장_정책": (
            "**📈 사용 지표 (한국)**\n"
            "- **VKOSPI** — 코스피200 옵션 기반 한국판 공포 지수. 데이터 미제공 시 KOSPI 20일 변동성(연환산)으로 대체. "
            "상승하면 시장 불안 확대, 하락하면 안정. 공매도 규제·세제 등 실제 자본시장 정책의 간접 프록시."
        ),
    },
}

# =========================================================
# 디자인 헬퍼
# =========================================================
st.markdown("""
<style>
[data-testid="metric-container"] {
    background: #f8f9fa;
    border: 1px solid #e9ecef;
    border-radius: 10px;
    padding: 14px 16px;
}
div[data-testid="stMetricValue"] { font-size: 1.2rem !important; }
</style>
""", unsafe_allow_html=True)


def _score_color(s: int) -> str:
    return "#28a745" if s >= 65 else ("#fd7e14" if s >= 50 else "#dc3545")


def score_pill(s: int) -> str:
    c = _score_color(s)
    return (f'<span style="background:{c};color:#fff;padding:2px 14px;'
            f'border-radius:20px;font-size:0.88em;font-weight:700;">{s}점</span>')


def section_header(num: str, title: str, score: int):
    st.markdown(
        f'<h3 style="margin-bottom:6px">{num} {title} &nbsp;{score_pill(score)}</h3>',
        unsafe_allow_html=True,
    )


def kv_cards(score_detail: dict, ncols: int = 3):
    """score_detail dict를 카드형 metric으로 시각화"""
    items = [(k, v) for k, v in score_detail.items() if not str(k).startswith("_")]
    for i in range(0, len(items), ncols):
        chunk = items[i:i + ncols]
        cols = st.columns(ncols)
        for col, (key, val) in zip(cols, chunk):
            vs = str(val)
            if any(x in vs for x in ["개선", "상승추세", "우수", "정상"]):
                icon = "✅"
            elif any(x in vs for x in ["악화", "하락추세", "없음"]):
                icon = "⚠️"
            else:
                icon = "📊"
            label = key.replace("_", " ")
            col.metric(f"{icon} {label}", vs[:55] if len(vs) > 55 else vs)


def render_ts_detail(data: dict):
    """내부요인/재무지표 추이 dict를 연도별 테이블로 시각화"""
    series_cols = {}
    no_data = []
    for key, val in data.items():
        if isinstance(val, dict) and val:
            series_cols[key] = val
        else:
            no_data.append(f"**{key}**: {val}")
    if series_cols:
        combined = pd.DataFrame(series_cols)
        combined.index.name = "날짜"
        combined = combined.sort_index(ascending=False)
        st.dataframe(
            combined.style.format("{:,.2f}", na_rep="N/A"),
            use_container_width=True,
        )
    for msg in no_data:
        st.caption(msg)


def render_market_detail(data: dict):
    """시장환경 항목 dict를 구조화해서 표시"""
    for key, val in data.items():
        if key == "판정":
            continue
        elif key == "참고":
            st.info(f"ℹ️ {val}")
        elif key == "오류":
            st.error(f"⚠️ 데이터 조회 실패: {val}")
        elif key == "안내":
            st.warning(val)
        else:
            c1, c2 = st.columns([2, 3])
            c1.markdown(f"**{key}**")
            c2.markdown(str(val))


# =========================================================
# 기본값 (로그인 여부와 무관하게 항상 정의)
# =========================================================
def _load_secret(key: str, default: str = "") -> str:
    """st.secrets → os.environ → default 순으로 조회. 타입·공백 안전."""
    try:
        v = st.secrets[key]
        if v is not None:
            return str(v).strip()
    except Exception:
        pass
    v = os.environ.get(key, "")
    return v.strip() if v else default

_default_fred_key = _load_secret("FRED_API_KEY", "")
_admin_id = _load_secret("ADMIN_ID", "admin")
_admin_pw = _load_secret("ADMIN_PW", "admin1234")

fred_api_key = _default_fred_key
fundamental_weight_pct = 60
market_weights = {"경기동향": 0.25, "통화_재정정책": 0.25, "지정학_불확실성": 0.25, "자본시장_정책": 0.25}

# =========================================================
# 사이드바
# =========================================================
with st.sidebar:
    _unlocked = st.session_state.get("settings_unlocked", False)

    if not _unlocked:
        st.title("🔒 설정")
        st.caption("관리자만 설정을 변경할 수 있습니다.")
        st.divider()
        _input_id = st.text_input("아이디", placeholder="관리자 아이디", key="login_id")
        _input_pw = st.text_input("비밀번호", type="password", placeholder="비밀번호", key="login_pw")
        if st.button("🔓 로그인", use_container_width=True, key="login_btn"):
            if _input_id.strip() == _admin_id and _input_pw.strip() == _admin_pw:
                st.session_state.settings_unlocked = True
                st.rerun()
            else:
                st.error("아이디 또는 비밀번호가 올바르지 않습니다.")
        st.divider()
        st.caption(
            "**한국 종목 입력 방법**\n"
            "- 한글 이름: " + ", ".join(list(KOREAN_STOCK_NAME_MAP.keys())[:5]) + " 등\n"
            "- 6자리 종목코드 (예: 005930 = 삼성전자)\n"
            "- ETF명: " + ", ".join(KOREAN_ETF_NAME_MAP.keys()) + "\n"
            "- 그 외 ETF는 종목코드로 입력 (KIND 조회)"
        )
    else:
        _hdr, _logout_col = st.columns([3, 2])
        _hdr.markdown("### ⚙️ 설정")
        if _logout_col.button("로그아웃", use_container_width=True):
            st.session_state.settings_unlocked = False
            st.rerun()

        st.success("✅ 관리자 모드")
        fred_api_key = st.text_input(
            "FRED API 키",
            value=_default_fred_key,
            type="password",
            help="https://fred.stlouisfed.org/docs/api/api_key.html 에서 무료 발급",
        )
        st.caption("시장환경 분석(경기동향/통화정책/지정학) 계산에 필요합니다.")
        st.divider()
        st.caption(
            "**한국 종목 입력 방법**\n"
            "- 한글 이름: " + ", ".join(list(KOREAN_STOCK_NAME_MAP.keys())[:5]) + " 등\n"
            "- 6자리 종목코드 (예: 005930 = 삼성전자)\n"
            "- ETF명: " + ", ".join(KOREAN_ETF_NAME_MAP.keys()) + "\n"
            "- 그 외 ETF는 종목코드로 입력 (KIND 조회)"
        )
        st.divider()
        st.subheader("종합점수 가중치")
        fundamental_weight_pct = st.slider(
            "펀더멘탈 vs 시장환경 비중", 0, 100, 60, step=5,
            help="슬라이더 값이 펀더멘탈 비중(%)입니다. 나머지는 시장환경 비중.",
        )
        st.caption(f"펀더멘탈 {fundamental_weight_pct}% : 시장환경 {100 - fundamental_weight_pct}%")
        with st.expander("시장환경 세부 가중치 (선택)"):
            st.caption("4개 항목의 상대적 중요도 (자동 정규화)")
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


# =========================================================
# 메인 헤더 & 입력
# =========================================================
st.title("📊 한국·미국 주식/ETF 펀더멘탈 & 시장환경 분석기")
st.caption("과거 5년 데이터를 기반으로 펀더멘탈 4개 항목 + 시장환경 4개 항목을 평가하는 프로토타입입니다.")

col_input, col_btn = st.columns([5, 1])
with col_input:
    ticker_input = st.text_input(
        "종목 입력",
        placeholder="예: AAPL, SPY, 005930, KODEX 200, 엔비디아, 삼성전자, 로켓랩",
        label_visibility="collapsed",
    ).strip()
with col_btn:
    analyze_btn = st.button("🔍 분석", use_container_width=True, type="primary")


# =========================================================
# 분석 실행
# =========================================================
if analyze_btn and ticker_input:
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

            # ---- 종목 헤더 ----
            market_flag = "🇰🇷" if market_type == "KR" else "🇺🇸"
            type_label = "ETF" if is_etf else "개별주식"
            cur_price = info.get("currentPrice") or info.get("regularMarketPrice")
            prev_close = info.get("previousClose") or info.get("regularMarketPreviousClose")
            day_chg = ((cur_price - prev_close) / prev_close * 100) if (cur_price and prev_close) else None

            st.markdown("---")
            h_left, h_right = st.columns([3, 2])
            with h_left:
                st.header(f"{info.get('longName', ticker_input)}")
                st.markdown(
                    f"`{resolved_ticker}` &nbsp;|&nbsp; {market_flag} {market_type} "
                    f"&nbsp;|&nbsp; {type_label} &nbsp;|&nbsp; {currency}"
                )
            with h_right:
                if cur_price:
                    fmt = f"{cur_price:,.0f}" if currency == "KRW" else f"{cur_price:,.2f}"
                    chg_color = "#28a745" if (day_chg or 0) >= 0 else "#dc3545"
                    chg_str = f"{day_chg:+.2f}%" if day_chg is not None else ""
                    st.markdown(
                        f'<div style="text-align:right;padding-top:12px">'
                        f'<div style="font-size:1.9rem;font-weight:700;line-height:1.2">'
                        f'{fmt} <span style="font-size:1rem;color:#6c757d">{currency}</span></div>'
                        f'<div style="font-size:1rem;font-weight:600;color:{chg_color}">'
                        f'{chg_str} 전일 대비</div></div>',
                        unsafe_allow_html=True,
                    )

            if market_type == "KR" and not is_etf:
                st.info("ℹ️ 한국 개별주식은 yfinance 재무제표 범위가 제한적입니다. ①② 일부 항목은 DART 원문을 확인하세요.")
            if market_type == "KR":
                st.caption("🇰🇷 시장환경 분석은 KOSPI·BOK 기준금리·VKOSPI 등 한국 지표를 사용합니다.")

            # ---- 사전 계산 ----
            market = analyze_market_environment(fred_api_key, market=market_type)
            business_cycle_verdict = market.get("경기동향", {}).get("판정", "")
            market_scores = {key: score_market_item(market.get(key, {}).get("판정", "")) for key in MARKET_LABELS}

            tech = analyze_technical(hist)
            tech_score, tech_score_detail = score_technical(tech)

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
            overall = compute_overall_score(fundamental_scores, market_scores, market_weights, fundamental_weight_pct)
            ov_score = overall["overall_score"]
            ov_color = _score_color(ov_score)

            # ---- 종합 평가 ----
            st.markdown("---")
            st.markdown(
                f'<h2 style="margin-bottom:4px">🏆 종합 평가 &nbsp;'
                f'<span style="background:{ov_color};color:#fff;padding:4px 22px;'
                f'border-radius:24px;font-size:1rem;">'
                f'{ov_score}점 &nbsp;{overall["grade"]}</span></h2>',
                unsafe_allow_html=True,
            )
            if is_etf:
                st.caption("⚠️ ETF는 재무제표 대신 운용보수·순자산·집중도 기반 ETF구성 점수를 사용합니다.")

            sc1, sc2, sc3, sc4 = st.columns(4)
            sc1.metric("🏆 종합 점수", f"{ov_score}점")
            sc2.metric("📋 펀더멘탈 평균", f"{round(overall['fundamental_avg'])}점")
            sc3.metric("🌍 시장환경 평균", f"{round(overall['market_avg'])}점")
            sc4.metric("🎯 등급", overall["grade"])

            # 레이더 차트
            radar_labels = (
                list(fundamental_scores.keys())
                + [MARKET_LABELS[k].split(" (")[0] for k in MARKET_LABELS]
            )
            radar_values = list(fundamental_scores.values()) + list(market_scores.values())
            radar_fig = go.Figure()
            radar_fig.add_trace(go.Scatterpolar(
                r=radar_values + [radar_values[0]],
                theta=radar_labels + [radar_labels[0]],
                fill="toself",
                fillcolor="rgba(78,141,245,0.18)",
                line=dict(color="#4e8df5", width=2),
                name="평가 점수",
            ))
            radar_fig.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 100], tickfont=dict(size=10))),
                showlegend=False, height=400,
                margin=dict(l=50, r=50, t=20, b=20),
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(radar_fig, use_container_width=True)
            st.markdown("---")

            # =========================================================
            # 펀더멘탈 상세
            # =========================================================
            if is_etf:
                section_header("①", "ETF 구성 분석", etf_score)
                st.caption("재무제표 대신 운용보수·순자산·집중도로 평가합니다.")
                kv_cards(etf_score_detail)
                with st.expander("ETF 원시 데이터"):
                    st.json({k: v for k, v in etf_data.items() if k != "_데이터품질"}, expanded=False)
            else:
                # ① 기업 내부요인
                section_header("①", "기업 내부요인 평가", internal_score)
                kv_cards(internal_score_detail)
                with st.expander("📂 추이 원시 데이터 (연도별)"):
                    render_ts_detail(internal)

                st.markdown("")

                # ② 재무지표
                section_header("②", "재무지표 평가", ratios_score)
                kv_cards(ratios_score_detail)
                with st.expander("📂 재무지표 원시 데이터 (연도별)"):
                    render_ts_detail(ratios)

                st.markdown("")

                # 밸류에이션 비교
                st.markdown("### 📊 밸류에이션 멀티플 비교 — PER / PBR / PSR / EPS / ROE")
                main_metrics = extract_valuation_metrics(info)
                peers_raw = get_peer_info_list(info, resolved_ticker, max_peers=5)
                peers_data_v = [
                    {"ticker": p["ticker"], "metrics": extract_valuation_metrics(p["info"])}
                    for p in peers_raw
                ]
                valuation = compare_valuation_vs_peers(resolved_ticker, main_metrics, peers_data_v)
                rows_table = valuation["지표_테이블"]
                peer_list = valuation["비교종목"]

                if rows_table:
                    col_order = [resolved_ticker, "업계평균"] + peer_list + ["평가"]
                    df_val = pd.DataFrame(rows_table).T
                    df_val.index.name = "지표"
                    df_val.insert(0, "설명", [
                        VALUATION_METRIC_INFO.get(k, ("", "", ""))[0] for k in df_val.index
                    ])
                    avail_cols = ["설명"] + [c for c in col_order if c in df_val.columns]

                    def _color_eval(val):
                        if not isinstance(val, str): return ""
                        if "✅" in val: return "background-color:#d4edda;color:#155724;font-weight:600"
                        if "⚠️" in val: return "background-color:#f8d7da;color:#721c24;font-weight:600"
                        if "➖" in val: return "background-color:#e9ecef;color:#495057"
                        return ""

                    numeric_cols = [c for c in avail_cols if c not in ("설명", "평가")]
                    for nc in numeric_cols:
                        df_val[nc] = pd.to_numeric(df_val[nc], errors="coerce")
                    styled_val = df_val[avail_cols].style
                    if "평가" in avail_cols:
                        styled_val = styled_val.applymap(_color_eval, subset=["평가"])
                    if numeric_cols:
                        styled_val = styled_val.format("{:.2f}", subset=numeric_cols, na_rep="N/A")
                    st.dataframe(styled_val, use_container_width=True)

                    if peer_list:
                        st.caption(f"비교 대상 ({len(peer_list)}개): {', '.join(peer_list)}")
                    else:
                        st.info("동종업계 비교 대상을 찾지 못했습니다. 현재 미국 대형주 업종만 지원됩니다.")

                    with st.expander("지표 해석 가이드"):
                        for key, (name, desc, direction) in VALUATION_METRIC_INFO.items():
                            good = "낮을수록 유리" if direction == "low_good" else "높을수록 유리"
                            st.markdown(f"**{key}** ({name}): {desc} _{good}_")
                else:
                    st.info("밸류에이션 지표 데이터를 가져오지 못했습니다.")

                st.markdown("")

                # ③ 산업동향
                section_header("③", "산업동향 평가", industry_score)
                ind1, ind2, ind3, ind4 = st.columns(4)
                ind1.metric("🏭 섹터", industry.get("섹터", "N/A"))
                ind2.metric("🔬 세부산업", industry.get("세부산업", "N/A")[:30])
                ind3.metric("📈 산업주기", industry.get("산업주기", "N/A"))
                ind4.metric("🔄 산업특성", industry.get("산업특성", "N/A")[:20])
                kv_cards(industry_score_detail)

            st.markdown("")

            # ④ 기술적 분석
            section_header("④", "기술적 분석", tech_score)
            t1, t2, t3, t4 = st.columns(4)
            trend_short = "상승" if "상승" in tech["추세"] else "하락"
            t1.metric("📈 추세", trend_short, tech["추세"].replace("추세 ", "").replace("(", "").replace(")", ""))
            rsi_val = tech["RSI(14)"]
            rsi_icon = "🔴" if isinstance(rsi_val, float) and (rsi_val > 70 or rsi_val < 30) else "🟢"
            t2.metric(f"{rsi_icon} RSI(14)", rsi_val)
            t3.metric("🧠 투자심리", tech["투자심리"])
            vol_short = "급증" if "급증" in tech["수급_거래량"] else "보통"
            t4.metric("📦 거래량", vol_short)

            # 가격 차트 (거래량 서브플롯 포함)
            chart_data = tech["chart_data"]
            price_fig = make_subplots(
                rows=2, cols=1, shared_xaxes=True,
                row_heights=[0.72, 0.28], vertical_spacing=0.04,
                subplot_titles=("", "거래량"),
            )
            price_fig.add_trace(go.Scatter(
                x=chart_data.index, y=chart_data["Close"],
                name="종가", line=dict(color="#4e8df5", width=2)
            ), row=1, col=1)
            price_fig.add_trace(go.Scatter(
                x=chart_data.index, y=chart_data["MA20"],
                name="MA20", line=dict(color="#fd7e14", width=1, dash="dot"), opacity=0.85
            ), row=1, col=1)
            price_fig.add_trace(go.Scatter(
                x=chart_data.index, y=chart_data["MA60"],
                name="MA60", line=dict(color="#28a745", width=1, dash="dot"), opacity=0.85
            ), row=1, col=1)
            price_fig.add_trace(go.Scatter(
                x=chart_data.index, y=chart_data["MA120"],
                name="MA120", line=dict(color="#dc3545", width=1.5)
            ), row=1, col=1)
            price_fig.add_trace(go.Bar(
                x=chart_data.index, y=chart_data["Volume"],
                name="거래량", marker_color="#adb5bd", opacity=0.6
            ), row=2, col=1)
            price_fig.update_layout(
                height=500,
                margin=dict(l=20, r=20, t=30, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                hovermode="x unified",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(248,249,250,1)",
            )
            price_fig.update_yaxes(gridcolor="#e9ecef")
            price_fig.update_xaxes(rangeslider_visible=False)
            st.plotly_chart(price_fig, use_container_width=True)

            st.markdown("---")

            # ---- 시장환경 ----
            st.markdown("### 🌍 시장환경 분석")
            m_cols = st.columns(4)
            for i, (key, label) in enumerate(MARKET_LABELS.items()):
                data_m = market.get(key, {})
                verdict = data_m.get("판정") or data_m.get("안내") or data_m.get("오류") or "N/A"
                sc = market_scores[key]
                short_label = label.split(" (")[0]
                badge_color = _score_color(sc)
                m_cols[i].markdown(
                    f'<div style="background:#f8f9fa;border:1px solid #e9ecef;border-radius:10px;'
                    f'padding:14px;text-align:center">'
                    f'<div style="font-size:0.8rem;color:#6c757d;margin-bottom:4px">{short_label}</div>'
                    f'<div style="font-size:0.95rem;font-weight:600;margin-bottom:6px">{verdict[:22]}</div>'
                    f'<span style="background:{badge_color};color:#fff;padding:1px 10px;'
                    f'border-radius:12px;font-size:0.8rem">{sc}점</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            st.markdown("")
            _desc_map = MARKET_INDEX_DESC.get(market_type, MARKET_INDEX_DESC["US"])
            for key, label in MARKET_LABELS.items():
                with st.expander(f"🔍 {label}"):
                    st.markdown(_desc_map.get(key, ""), unsafe_allow_html=False)
                    st.divider()
                    render_market_detail(market.get(key, {}))

        except Exception as e:
            st.error(f"분석 중 오류가 발생했습니다: {e}")
            st.info("티커가 올바른지, 또는 yfinance가 해당 종목 데이터를 제공하는지 확인해주세요.")

st.markdown("---")
st.caption(
    "⚠️ 이 도구는 프로토타입이며 투자 조언이 아닙니다. 점수/등급은 규칙 기반 근사치로, "
    "재무데이터는 yfinance 기준이라 실제 공시와 차이가 있을 수 있으니 투자 판단 시 원문 공시를 반드시 확인하세요."
)
