"""
app.py — Streamlit UI (한국·미국·글로벌 주식/ETF 펀더멘탈 & 시장환경 분석기)
"""

import os
import re
import traceback

import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from auth import (
    get_google_auth_url,
    get_kakao_auth_url,
    exchange_google_code,
    exchange_kakao_code,
    check_admin_login,
    make_admin_user,
)
from i18n import t as _t
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
    _YF_SESSION,
)
import yfinance as yf

# =========================================================
# 페이지 설정 (항상 첫 번째 st 호출)
# =========================================================
st.set_page_config(
    page_title="Global Stock/ETF Analyzer",
    page_icon="📊",
    layout="wide",
)

# =========================================================
# 언어 초기화 (session_state에 저장)
# =========================================================
if "lang" not in st.session_state:
    st.session_state["lang"] = "ko"


def t(key: str) -> str:
    """현재 세션 언어로 번역."""
    return _t(key, st.session_state["lang"])


# =========================================================
# OAuth 콜백 처리 (URL query params 확인)
# 페이지 렌더링 전에 처리해야 함
# =========================================================
_qp = st.query_params
_oauth_code = _qp.get("code", "")
_oauth_state = _qp.get("state", "")

if _oauth_code and _oauth_state and "user" not in st.session_state:
    with st.spinner("로그인 처리 중..." if st.session_state["lang"] == "ko" else "Processing login..."):
        _user = None
        if _oauth_state == "google":
            _user = exchange_google_code(_oauth_code)
        elif _oauth_state == "kakao":
            _user = exchange_kakao_code(_oauth_code)

        if _user:
            st.session_state["user"] = _user
        else:
            st.session_state["oauth_error"] = True

    st.query_params.clear()
    st.rerun()


# =========================================================
# 캐시된 데이터 수집 함수
# =========================================================
@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_all(ticker_input: str, fred_key: str):
    """yfinance/FRED 데이터를 한 번만 가져와 1시간 캐싱."""
    c = classify_ticker(ticker_input)
    info = c["info"]
    ticker_obj = c["ticker_obj"]
    resolved = c["resolved_ticker"]

    hist = get_price_history(ticker_obj)

    financials = balance = cashflow = None
    etf_data = None
    peers_raw = []

    if c["is_etf"]:
        etf_data = fetch_etf_raw_data(ticker_obj, info)
    else:
        financials, balance, cashflow = get_financials(ticker_obj)
        peers_raw = get_peer_info_list(info, resolved, max_peers=5)

    market = analyze_market_environment(fred_key, market=c["market"])

    return {
        "info": info,
        "hist": hist,
        "is_etf": c["is_etf"],
        "market_type": c["market"],
        "currency": c["currency"],
        "resolved_ticker": resolved,
        "financials": financials,
        "balance": balance,
        "cashflow": cashflow,
        "etf_data": etf_data,
        "peers_raw": peers_raw,
        "market": market,
    }


# =========================================================
# 글로벌 시장 플래그 & 레이블
# =========================================================
MARKET_FLAGS: dict[str, str] = {
    "KR": "🇰🇷", "US": "🇺🇸",
    "JP": "🇯🇵", "CN": "🇨🇳", "HK": "🇭🇰",
    "TW": "🇹🇼", "IN": "🇮🇳",
    "DE": "🇩🇪", "UK": "🇬🇧", "FR": "🇫🇷",
    "NL": "🇳🇱", "IT": "🇮🇹", "CH": "🇨🇭",
    "BE": "🇧🇪", "ES": "🇪🇸", "NO": "🇳🇴", "SE": "🇸🇪",
}

MARKET_LABELS = {
    "경기동향":       "경기동향 (경기활황 vs 경기불황)",
    "통화_재정정책":  "통화/재정정책 (완화 vs 긴축)",
    "지정학_불확실성": "지정학적 불확실성 (위험발생 vs 위험해소)",
    "자본시장_정책":  "자본시장 정책 변화 (긍정 vs 부정)",
}

MARKET_LABELS_EN = {
    "경기동향":       "Business Cycle (Boom vs Recession)",
    "통화_재정정책":  "Monetary Policy (Easing vs Tightening)",
    "지정학_불확실성": "Geopolitical Risk (Rising vs Easing)",
    "자본시장_정책":  "Capital Market Policy (Positive vs Negative)",
}

MARKET_INDEX_DESC = {
    "US": {
        "경기동향": (
            "**📈 사용 지표 (미국)**\n"
            "- **USSLIND (미국 경기선행지수)** — Conference Board 발표. 향후 6~12개월 경기 방향을 예측.\n"
            "- **UNRATE (실업률)** — 미국 노동시장 건전성 지표."
        ),
        "통화_재정정책": (
            "**📈 사용 지표 (미국)**\n"
            "- **FEDFUNDS (미국 기준금리)** — 연준(Fed) 단기 정책금리. 인상 시 긴축, 인하 시 완화.\n"
            "- **M2SL (M2 통화량)** — 광의 통화량. 증가율이 높으면 유동성 확대."
        ),
        "지정학_불확실성": (
            "**📈 사용 지표 (미국)**\n"
            "- **USEPUINDXD (경제정책 불확실성 지수, EPU)** — 뉴스 기사 빈도 기반 산출. 높을수록 불확실성 확대."
        ),
        "자본시장_정책": (
            "**📈 사용 지표 (미국)**\n"
            "- **VIX (CBOE 변동성 지수)** — S&P 500 옵션 기반 공포 지수. 20 이하 안정, 30 이상 불안."
        ),
    },
    "KR": {
        "경기동향": (
            "**📈 사용 지표 (한국)**\n"
            "- **KOSPI 지수 추이** — 6개월 전 대비 등락으로 경기 방향성 파악.\n"
            "- **한국 실업률 (LRHUTTTTKSM156S)** — OECD 기준 조화 실업률."
        ),
        "통화_재정정책": (
            "**📈 사용 지표 (한국)**\n"
            "- **한국 기준금리 (IRSTCB01KRM156N)** — 한국은행(BOK) 정책금리.\n"
            "- **한국 M2 통화량 (MYAGKRM052S)** — 광의 통화량 YoY 증가율."
        ),
        "지정학_불확실성": (
            "**📈 사용 지표 (한국)**\n"
            "- **글로벌 EPU 지수 (USEPUINDXD)** — 한국 전용 지수 제한으로 글로벌 EPU 대리 사용."
        ),
        "자본시장_정책": (
            "**📈 사용 지표 (한국)**\n"
            "- **VKOSPI** — 코스피200 기반 한국판 공포 지수. 데이터 미제공 시 KOSPI 20일 변동성으로 대체."
        ),
    },
    "DEFAULT": {
        "경기동향": (
            "**📈 사용 지표 (미국 대리)**\n"
            "- 해당 시장 전용 지표가 지원되지 않아 미국 지표(USSLIND, UNRATE)를 대리 표시합니다."
        ),
        "통화_재정정책": (
            "**📈 사용 지표 (미국 대리)**\n"
            "- 해당 시장 전용 지표가 지원되지 않아 미국 지표(FEDFUNDS, M2SL)를 대리 표시합니다."
        ),
        "지정학_불확실성": (
            "**📈 사용 지표 (미국 대리)**\n"
            "- 해당 시장 전용 지표가 지원되지 않아 미국 EPU 지수를 대리 표시합니다."
        ),
        "자본시장_정책": (
            "**📈 사용 지표 (미국 대리)**\n"
            "- 해당 시장 전용 지표가 지원되지 않아 VIX를 대리 표시합니다."
        ),
    },
}


# =========================================================
# CSS 스타일
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
.login-card {
    background: #ffffff;
    border: 1px solid #e9ecef;
    border-radius: 16px;
    padding: 32px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.07);
}
</style>
""", unsafe_allow_html=True)


# =========================================================
# 유틸 함수
# =========================================================
def _load_secret(key: str, default: str = "") -> str:
    try:
        v = st.secrets[key]
        if v is not None:
            return str(v).strip()
    except Exception:
        pass
    v = os.environ.get(key, "")
    return v.strip() if v else default


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
# 로그인 페이지
# =========================================================
def show_login_page():
    lang = st.session_state["lang"]

    # OAuth 오류 메시지
    if st.session_state.pop("oauth_error", False):
        st.error(t("oauth_error"))

    _, center, _ = st.columns([1, 2, 1])
    with center:
        st.markdown(f"## 📊 {t('login_title')}")
        st.caption(t("login_subtitle"))
        st.markdown("")

        google_url = get_google_auth_url()
        kakao_url = get_kakao_auth_url()

        if google_url:
            st.link_button(t("google_login"), google_url, use_container_width=True)
        else:
            st.button(t("google_login"), disabled=True,
                      use_container_width=True, help=t("oauth_not_configured"))

        if kakao_url:
            st.link_button(t("kakao_login"), kakao_url, use_container_width=True)
        else:
            st.button(t("kakao_login"), disabled=True,
                      use_container_width=True, help=t("oauth_not_configured"))

        st.markdown("---")

        with st.expander(t("admin_login")):
            _input_id = st.text_input(t("username"), placeholder=t("username"), key="login_id")
            _input_pw = st.text_input(t("password"), type="password", key="login_pw")
            if st.button(t("login_btn"), use_container_width=True, key="admin_btn", type="primary"):
                if check_admin_login(_input_id, _input_pw):
                    st.session_state["user"] = make_admin_user()
                    st.rerun()
                else:
                    st.error(t("login_error"))


# =========================================================
# 기본값
# =========================================================
_default_fred_key = _load_secret("FRED_API_KEY", "")
fred_api_key = _default_fred_key
fundamental_weight_pct = 60
market_weights = {"경기동향": 0.25, "통화_재정정책": 0.25, "지정학_불확실성": 0.25, "자본시장_정책": 0.25}


# =========================================================
# 상단 언어 스위처 & 로그인 체크
# =========================================================
_top_left, _top_right = st.columns([5, 1])
with _top_left:
    pass  # 타이틀은 아래에서 렌더링
with _top_right:
    _lang_choice = st.radio(
        t("language"),
        ["🇰🇷 한국어", "🇺🇸 English"],
        index=0 if st.session_state["lang"] == "ko" else 1,
        horizontal=True,
        label_visibility="collapsed",
        key="lang_radio",
    )
    _new_lang = "ko" if "한국어" in _lang_choice else "en"
    if _new_lang != st.session_state["lang"]:
        st.session_state["lang"] = _new_lang
        st.rerun()

# 로그인 여부 확인
if "user" not in st.session_state:
    show_login_page()
    st.stop()

_user = st.session_state["user"]


# =========================================================
# 사이드바 (로그인 후)
# =========================================================
with st.sidebar:
    # 사용자 정보
    _provider_icon = {"google": "🔵", "kakao": "💛", "admin": "🔑"}.get(_user["provider"], "👤")
    st.markdown(f"{_provider_icon} **{_user['name']}**")
    if _user["email"]:
        st.caption(_user["email"])
    if st.button(t("logout_btn"), use_container_width=True):
        del st.session_state["user"]
        st.rerun()
    st.divider()

    if _user.get("is_admin"):
        st.success(t("admin_mode"))
        fred_api_key = st.text_input(
            t("fred_api_key"),
            value=_default_fred_key,
            type="password",
            help=t("fred_help"),
        )
        st.caption(t("fred_caption"))
        st.divider()
        st.subheader(t("score_weights"))
        fundamental_weight_pct = st.slider(
            t("fund_vs_market"), 0, 100, 60, step=5,
            help=t("fund_vs_market_help"),
        )
        st.caption(f"{t('fund_pct')} {fundamental_weight_pct}% : {t('market_pct')} {100 - fundamental_weight_pct}%")
        with st.expander(t("market_detail_weights")):
            st.caption(t("market_weight_auto"))
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
    else:
        st.info(t("fred_caption"))

    st.divider()
    st.caption(t("input_guide"))


# =========================================================
# 메인 헤더 & 입력
# =========================================================
st.title(f"📊 {t('app_title')}")
st.caption(t("app_caption"))

col_input, col_btn = st.columns([5, 1])
with col_input:
    ticker_input = st.text_input(
        "종목 입력",
        placeholder=t("search_placeholder"),
        label_visibility="collapsed",
    ).strip()
with col_btn:
    analyze_btn = st.button(t("analyze_btn"), use_container_width=True, type="primary")


# =========================================================
# 분석 실행
# =========================================================
if analyze_btn and ticker_input:
    with st.spinner(t("analyzing")):
        try:
            data = _fetch_all(ticker_input, fred_api_key or "")
            info = data["info"]
            ticker_obj = yf.Ticker(data["resolved_ticker"], session=_YF_SESSION)
            is_etf = data["is_etf"]
            market_type = data["market_type"]
            currency = data["currency"]
            resolved_ticker = data["resolved_ticker"]

            hist = data["hist"]
            if hist.empty:
                is_kr_input = (
                    re.fullmatch(r"\d{6}(\.KS|\.KQ)?", ticker_input.strip(), re.IGNORECASE)
                    or any(c in ticker_input for c in "가나다라마바사아자차카타파하")
                )
                if is_kr_input:
                    st.error(t("no_data_kr").replace("'{ticker_input}'", f"**'{ticker_input}'**"))
                else:
                    st.error(t("no_data_generic"))
                st.stop()

            # ---- 종목 헤더 ----
            market_flag = MARKET_FLAGS.get(market_type, "🌐")
            type_label = t("type_etf") if is_etf else t("type_stock")
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
                        f'{chg_str} {t("day_change")}</div></div>',
                        unsafe_allow_html=True,
                    )

            # 시장별 안내 메시지
            if market_type == "KR":
                if not is_etf:
                    st.info(t("kr_limited"))
                st.caption(t("kr_market_note"))
            elif market_type != "US":
                st.info(t("global_limited"))
                st.caption(t("global_market_note"))

            # ---- 사전 계산 ----
            market = data["market"]
            business_cycle_verdict = market.get("경기동향", {}).get("판정", "")
            market_scores = {
                key: score_market_item(market.get(key, {}).get("판정", ""))
                for key in MARKET_LABELS
            }

            tech = analyze_technical(hist)
            tech_score, tech_score_detail = score_technical(tech)

            fundamental_scores = {}
            if is_etf:
                etf_data = data["etf_data"]
                etf_score, etf_score_detail = score_etf_fundamentals(etf_data, currency)
                fundamental_scores["ETF구성"] = etf_score
            else:
                income, balance, cashflow = data["financials"], data["balance"], data["cashflow"]
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
            overall = compute_overall_score(
                fundamental_scores, market_scores, market_weights, fundamental_weight_pct
            )
            ov_score = overall["overall_score"]
            ov_color = _score_color(ov_score)

            # ---- 종합 평가 ----
            st.markdown("---")
            st.markdown(
                f'<h2 style="margin-bottom:4px">{t("overall_title")} &nbsp;'
                f'<span style="background:{ov_color};color:#fff;padding:4px 22px;'
                f'border-radius:24px;font-size:1rem;">'
                f'{ov_score}점 &nbsp;{overall["grade"]}</span></h2>',
                unsafe_allow_html=True,
            )
            if is_etf:
                st.caption(t("etf_caption"))

            sc1, sc2, sc3, sc4 = st.columns(4)
            sc1.metric(t("overall_score"), f"{ov_score}점")
            sc2.metric(t("fundamental_avg"), f"{round(overall['fundamental_avg'])}점")
            sc3.metric(t("market_avg"), f"{round(overall['market_avg'])}점")
            sc4.metric(t("grade_label"), overall["grade"])

            # 레이더 차트
            _mkt_labels = MARKET_LABELS_EN if st.session_state["lang"] == "en" else MARKET_LABELS
            radar_labels = (
                list(fundamental_scores.keys())
                + [_mkt_labels[k].split(" (")[0] for k in _mkt_labels]
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
                section_header("①", t("section1_etf"), etf_score)
                st.caption(t("etf_caption"))
                kv_cards(etf_score_detail)
                with st.expander(t("etf_raw")):
                    st.json({k: v for k, v in etf_data.items() if k != "_데이터품질"}, expanded=False)
            else:
                # ① 기업 내부요인
                section_header("①", t("section1_stock"), internal_score)
                kv_cards(internal_score_detail)
                with st.expander(t("raw_data")):
                    render_ts_detail(internal)

                st.markdown("")

                # ② 재무지표
                section_header("②", t("section2"), ratios_score)
                kv_cards(ratios_score_detail)
                with st.expander(t("raw_data")):
                    render_ts_detail(ratios)

                st.markdown("")

                # 밸류에이션 비교
                st.markdown(f"### {t('valuation_title')}")
                main_metrics = extract_valuation_metrics(info, ticker_obj=ticker_obj)
                peers_raw = data["peers_raw"]
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
                        if not isinstance(val, str):
                            return ""
                        if "✅" in val:
                            return "background-color:#d4edda;color:#155724;font-weight:600"
                        if "⚠️" in val:
                            return "background-color:#f8d7da;color:#721c24;font-weight:600"
                        if "➖" in val:
                            return "background-color:#e9ecef;color:#495057"
                        return ""

                    numeric_cols = [c for c in avail_cols if c not in ("설명", "평가")]
                    for nc in numeric_cols:
                        df_val[nc] = pd.to_numeric(df_val[nc], errors="coerce")
                    styled_val = df_val[avail_cols].style
                    if "평가" in avail_cols:
                        styled_val = styled_val.map(_color_eval, subset=["평가"])
                    if numeric_cols:
                        styled_val = styled_val.format("{:.2f}", subset=numeric_cols, na_rep="N/A")
                    st.dataframe(styled_val, use_container_width=True)

                    if peer_list:
                        st.caption(f"{t('peers_label')} ({len(peer_list)}개): {', '.join(peer_list)}")
                    else:
                        st.info(t("no_peers"))

                    with st.expander(t("valuation_guide")):
                        for key, (name, desc, direction) in VALUATION_METRIC_INFO.items():
                            good = "낮을수록 유리" if direction == "low_good" else "높을수록 유리"
                            st.markdown(f"**{key}** ({name}): {desc} _{good}_")
                else:
                    st.info(t("no_valuation"))

                st.markdown("")

                # ③ 산업동향
                section_header("③", t("section3"), industry_score)
                ind1, ind2, ind3, ind4 = st.columns(4)
                ind1.metric(t("sector_label"), industry.get("섹터", "N/A"))
                ind2.metric(t("industry_label"), industry.get("세부산업", "N/A")[:30])
                ind3.metric(t("cycle_label"), industry.get("산업주기", "N/A"))
                ind4.metric(t("nature_label"), industry.get("산업특성", "N/A")[:20])
                kv_cards(industry_score_detail)

            st.markdown("")

            # ④ 기술적 분석
            section_header("④", t("section4"), tech_score)
            t1, t2, t3, t4 = st.columns(4)
            trend_short = t("trend_up") if "상승" in tech["추세"] else t("trend_down")
            t1.metric(t("trend_label"), trend_short,
                      tech["추세"].replace("추세 ", "").replace("(", "").replace(")", ""))
            rsi_val = tech["RSI(14)"]
            rsi_icon = "🔴" if isinstance(rsi_val, float) and (rsi_val > 70 or rsi_val < 30) else "🟢"
            t2.metric(f"{rsi_icon} {t('rsi_label')}", rsi_val)
            t3.metric(t("sentiment"), tech["투자심리"])
            vol_short = t("vol_surge") if "급증" in tech["수급_거래량"] else t("vol_normal")
            t4.metric(t("volume_label"), vol_short)

            # 가격 차트
            chart_data = tech["chart_data"]
            price_fig = make_subplots(
                rows=2, cols=1, shared_xaxes=True,
                row_heights=[0.72, 0.28], vertical_spacing=0.04,
                subplot_titles=("", t("volume_chart")),
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
                name=t("volume_chart"), marker_color="#adb5bd", opacity=0.6
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
            st.markdown(f"### {t('market_env')}")
            _mkt_label_map = MARKET_LABELS_EN if st.session_state["lang"] == "en" else MARKET_LABELS
            m_cols = st.columns(4)
            for i, (key, label) in enumerate(_mkt_label_map.items()):
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
            _desc_map = MARKET_INDEX_DESC.get(market_type, MARKET_INDEX_DESC["DEFAULT"])
            for key, label in _mkt_label_map.items():
                with st.expander(f"🔍 {label}"):
                    st.markdown(_desc_map.get(key, ""), unsafe_allow_html=False)
                    st.divider()
                    render_market_detail(market.get(key, {}))

        except Exception as e:
            st.error(f"{t('analysis_error')}{e}")
            st.info(t("check_ticker"))
            with st.expander(t("error_detail")):
                st.code(traceback.format_exc())

st.markdown("---")
st.caption(t("footer"))
