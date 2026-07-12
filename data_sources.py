"""
data_sources.py — 외부 데이터 수집 모듈

yfinance, FRED API 등 네트워크 호출이 필요한 함수를 모아둡니다.
계산/판정 로직은 analysis.py에 있으며, 이 모듈은 원본 데이터를 가져와
필요한 경우 analysis.py의 함수로 넘겨주는 역할만 합니다.

네트워크가 필요하므로 이 모듈의 함수들은 실제 인터넷 연결 환경에서만
테스트할 수 있습니다 (test_data_sources.py의 통합테스트 참고, 기본은 skip 처리됨).
"""

import re
from datetime import datetime, timedelta

import pandas as pd
import requests
import yfinance as yf

from analysis import normalize_ticker_input, summarize_etf_fundamentals

FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"


# =========================================================
# 1. 종목 판별 (한국/미국 시장 자동 감지)
# =========================================================
def classify_ticker(ticker: str):
    """티커를 조회해서 시장(한국/미국)과 유형(ETF/개별주식)을 판별.
    한국 종목코드의 경우 .KS(코스피) 조회가 실패하면 .KQ(코스닥)로 재시도."""
    normalized = normalize_ticker_input(ticker)
    is_korean_code = re.fullmatch(r"\d{6}\.(KS|KQ)", normalized) is not None

    t = yf.Ticker(normalized)
    info = t.info

    if is_korean_code and (not info or info.get("regularMarketPrice") is None):
        alt = normalized.replace(".KS", ".KQ")
        t_alt = yf.Ticker(alt)
        info_alt = t_alt.info
        if info_alt and info_alt.get("regularMarketPrice") is not None:
            t, info, normalized = t_alt, info_alt, alt

    quote_type = info.get("quoteType", "").upper()
    is_etf = quote_type == "ETF"
    market = "KR" if normalized.upper().endswith((".KS", ".KQ")) else "US"
    currency = info.get("currency", "USD" if market == "US" else "KRW")

    return {
        "is_etf": is_etf,
        "info": info,
        "ticker_obj": t,
        "market": market,
        "currency": currency,
        "resolved_ticker": normalized,
    }


# =========================================================
# 2. 가격/재무 데이터 수집
# =========================================================
def get_price_history(ticker_obj, years: int = 5) -> pd.DataFrame:
    end = datetime.today()
    start = end - timedelta(days=365 * years)
    return ticker_obj.history(start=start, end=end)


def get_financials(ticker_obj):
    """연간 재무제표 반환 (yfinance는 최근 4개년 정도만 제공)"""
    return ticker_obj.financials, ticker_obj.balance_sheet, ticker_obj.cashflow


def fetch_etf_raw_data(ticker_obj, info: dict) -> dict:
    """ETF의 top_holdings/sector_weightings를 가져와 analysis.summarize_etf_fundamentals로 가공"""
    top_holdings_df = None
    try:
        top_holdings_df = ticker_obj.funds_data.top_holdings
    except Exception:
        top_holdings_df = None

    sector_weights = None
    try:
        sector_weights = ticker_obj.funds_data.sector_weightings
    except Exception:
        sector_weights = None
    if not sector_weights:
        sector_weights = info.get("sectorWeightings")

    return summarize_etf_fundamentals(top_holdings_df, sector_weights, info)


# =========================================================
# 3. 시장환경 분석 (FRED API 연동)
# =========================================================
def fetch_fred_series(series_id: str, api_key: str, start: str = "2019-01-01") -> pd.Series:
    """FRED에서 시계열 하나를 가져와 pd.Series(date index)로 반환"""
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "observation_start": start,
    }
    resp = requests.get(FRED_BASE_URL, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()["observations"]
    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["value"]).set_index("date")
    return df["value"]


def analyze_business_cycle(api_key: str) -> dict:
    """경기동향: 경기활황(성장기대감) vs 경기불황(불확실성)"""
    result = {}
    try:
        lead = fetch_fred_series("USSLIND", api_key)
        lead_latest = lead.iloc[-1]
        lead_6m_ago = lead.iloc[-6] if len(lead) >= 6 else lead.iloc[0]
        lead_trend = "개선" if lead_latest > lead_6m_ago else "악화"

        unrate = fetch_fred_series("UNRATE", api_key)
        unrate_latest = unrate.iloc[-1]
        unrate_6m_ago = unrate.iloc[-6] if len(unrate) >= 6 else unrate.iloc[0]
        unrate_trend = "하락(개선)" if unrate_latest < unrate_6m_ago else "상승(악화)"

        judgement = "경기활황(성장기대감)" if lead_trend == "개선" and "하락" in unrate_trend else \
                    "경기불황(불확실성)" if lead_trend == "악화" and "상승" in unrate_trend else \
                    "혼재(지표간 상충 - 추가 확인 필요)"

        result["판정"] = judgement
        result["Leading Index 추이"] = f"{lead_6m_ago:.2f} → {lead_latest:.2f} ({lead_trend})"
        result["실업률 추이(%)"] = f"{unrate_6m_ago:.2f} → {unrate_latest:.2f} ({unrate_trend})"
    except Exception as e:
        result["오류"] = f"FRED 데이터 조회 실패: {e}"
    return result


def analyze_monetary_fiscal_policy(api_key: str) -> dict:
    """통화/재정정책: 완화(금리인하,확장재정) vs 긴축(금리인상,긴축재정)"""
    result = {}
    try:
        ff = fetch_fred_series("FEDFUNDS", api_key)
        ff_latest = ff.iloc[-1]
        ff_6m_ago = ff.iloc[-6] if len(ff) >= 6 else ff.iloc[0]
        rate_direction = "긴축(금리 인상 기조)" if ff_latest > ff_6m_ago else \
                          "완화(금리 인하 기조)" if ff_latest < ff_6m_ago else "동결(변화 없음)"

        m2 = fetch_fred_series("M2SL", api_key)
        m2_yoy = (m2.iloc[-1] / m2.iloc[-13] - 1) * 100 if len(m2) >= 13 else None

        result["판정"] = rate_direction
        result["기준금리 추이(%)"] = f"{ff_6m_ago:.2f} → {ff_latest:.2f}"
        if m2_yoy is not None:
            result["M2 통화량 증가율(YoY,%)"] = round(m2_yoy, 2)
    except Exception as e:
        result["오류"] = f"FRED 데이터 조회 실패: {e}"
    return result


def analyze_geopolitical_risk(api_key: str) -> dict:
    """지정학적 불확실성: 위험발생 vs 위험해소 (EPU 지수를 근접 프록시로 사용)"""
    result = {}
    try:
        epu = fetch_fred_series("USEPUINDXD", api_key)
        epu_monthly = epu.resample("ME").mean()
        latest = epu_monthly.iloc[-1]
        baseline = epu_monthly.iloc[-37:-1].mean() if len(epu_monthly) >= 37 else epu_monthly.mean()

        judgement = "위험발생(불확실성 확대)" if latest > baseline * 1.15 else \
                    "위험해소(불확실성 완화)" if latest < baseline * 0.85 else "평이한 수준"

        result["판정"] = judgement
        result["최근 EPU 지수"] = round(latest, 1)
        result["3년 평균 대비"] = f"{round((latest / baseline - 1) * 100, 1)}%"
        result["참고"] = "이 지수는 정책 불확실성 프록시입니다. 실제 지정학 리스크는 뉴스 모니터링 병행 권장"
    except Exception as e:
        result["오류"] = f"FRED 데이터 조회 실패: {e}"
    return result


def analyze_capital_market_policy() -> dict:
    """자본시장 정책 변화: 주가에 긍정적 vs 부정적 (VIX를 간접 프록시로 사용)"""
    result = {}
    try:
        vix = yf.Ticker("^VIX").history(period="3mo")["Close"]
        latest = vix.iloc[-1]
        month_ago = vix.iloc[-21] if len(vix) >= 21 else vix.iloc[0]
        direction = "부정적(변동성 확대)" if latest > month_ago * 1.1 else \
                    "긍정적(변동성 축소)" if latest < month_ago * 0.9 else "중립"
        result["판정"] = direction
        result["VIX 추이"] = f"{month_ago:.2f} → {latest:.2f}"
        result["참고"] = "VIX는 간접 프록시입니다. 실제 자본시장 정책(공매도 규제, 세제 등)은 뉴스 확인 필요"
    except Exception as e:
        result["오류"] = f"VIX 데이터 조회 실패: {e}"
    return result


def analyze_market_environment(fred_api_key: str) -> dict:
    """시장환경 4개 항목 종합"""
    results = {}
    if fred_api_key:
        results["경기동향"] = analyze_business_cycle(fred_api_key)
        results["통화_재정정책"] = analyze_monetary_fiscal_policy(fred_api_key)
        results["지정학_불확실성"] = analyze_geopolitical_risk(fred_api_key)
    else:
        no_key_msg = {"안내": "FRED API 키가 없어 조회할 수 없습니다. 사이드바에 키를 입력해주세요."}
        results["경기동향"] = no_key_msg
        results["통화_재정정책"] = no_key_msg
        results["지정학_불확실성"] = no_key_msg

    results["자본시장_정책"] = analyze_capital_market_policy()
    return results
