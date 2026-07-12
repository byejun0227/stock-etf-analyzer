"""
analysis.py — 순수 계산/판정 로직 모듈

이 모듈은 yfinance, streamlit, requests에 의존하지 않습니다.
이미 가져온 데이터(pandas DataFrame/Series, dict)를 입력받아 분석/점수화만 수행하므로
네트워크 없이도 단위테스트가 가능합니다. (test_analysis.py 참고)

데이터 수집(yfinance, FRED API 호출)은 data_sources.py에 있습니다.
"""

import re
import pandas as pd
import numpy as np


# =========================================================
# 한국 ETF 이름 -> 종목코드 매핑
# =========================================================
# 직접 검색으로 검증된 항목만 등재. 여기 없는 종목은 6자리 종목코드를 직접 입력하세요.
KOREAN_ETF_NAME_MAP = {
    "KODEX 200": "069500",
    "TIGER 200": "102110",
    "TIGER 반도체TOP10": "396500",
}


# =========================================================
# 1. 티커 정규화
# =========================================================
def normalize_ticker_input(user_input: str) -> str:
    """사용자 입력을 yfinance가 이해하는 티커 표기로 정규화.
    - 이미 .KS/.KQ가 붙어 있으면 그대로 사용
    - 한국 ETF 이름(매핑 테이블에 있는 경우) -> 종목코드.KS로 변환
    - 6자리 숫자면 한국 종목코드로 간주하고 .KS로 변환 (실패 시 호출부에서 .KQ 재시도)
    - 그 외에는 미국 티커로 간주하고 대문자로 반환
    """
    raw = (user_input or "").strip()
    upper = raw.upper()

    if upper.endswith(".KS") or upper.endswith(".KQ"):
        return upper

    if raw in KOREAN_ETF_NAME_MAP:
        return KOREAN_ETF_NAME_MAP[raw] + ".KS"

    if re.fullmatch(r"\d{6}", raw):
        return raw + ".KS"

    return upper


# =========================================================
# 2. 펀더멘탈 분석 (원본 데이터 -> 사람이 읽는 요약)
# =========================================================
def analyze_internal_factors(balance: pd.DataFrame, income: pd.DataFrame, cashflow: pd.DataFrame) -> dict:
    """① 자산/부채, 매출/비용/수익/현금흐름, 재무구조 추이"""
    results = {}

    try:
        total_assets = balance.loc["Total Assets"]
        total_liab = balance.loc["Total Liabilities Net Minority Interest"]
        debt_ratio = (total_liab / total_assets * 100).round(2)
        results["부채비율_추이(%)"] = debt_ratio.to_dict()
    except Exception:
        results["부채비율_추이(%)"] = "데이터 없음"

    try:
        revenue = income.loc["Total Revenue"]
        results["매출_추이"] = revenue.to_dict()
    except Exception:
        results["매출_추이"] = "데이터 없음"

    try:
        ocf = cashflow.loc["Operating Cash Flow"]
        results["영업현금흐름_추이"] = ocf.to_dict()
    except Exception:
        results["영업현금흐름_추이"] = "데이터 없음"

    return results


def analyze_financial_ratios(income: pd.DataFrame) -> dict:
    """② 영업이익률, 이자보상비율, 매출증가율"""
    results = {}

    try:
        revenue = income.loc["Total Revenue"]
        op_income = income.loc["Operating Income"]
        op_margin = (op_income / revenue * 100).round(2)
        results["영업이익률(%)"] = op_margin.to_dict()
    except Exception:
        results["영업이익률(%)"] = "데이터 없음"

    try:
        ebit = income.loc["EBIT"] if "EBIT" in income.index else income.loc["Operating Income"]
        interest_exp = income.loc["Interest Expense"]
        interest_coverage = (ebit / interest_exp.abs()).round(2)
        results["이자보상비율(배)"] = interest_coverage.to_dict()
    except Exception:
        results["이자보상비율(배)"] = "데이터 없음 (무차입 기업이거나 항목 미제공)"

    try:
        revenue = income.loc["Total Revenue"]
        growth = revenue.pct_change(-1) * 100  # yfinance는 최근->과거 순서
        results["매출증가율(%)"] = growth.round(2).to_dict()
    except Exception:
        results["매출증가율(%)"] = "데이터 없음"

    return results


def analyze_industry(info: dict) -> dict:
    """③ 산업주기(성장기/쇠퇴기), 산업특성(경기순응적/경기방어적) - 규칙 기반 룩업"""
    sector = info.get("sector", "Unknown")
    industry = info.get("industry", "Unknown")

    growth_sectors = {"Technology", "Communication Services"}
    defensive_sectors = {"Consumer Defensive", "Utilities", "Healthcare"}
    cyclical_sectors = {"Consumer Cyclical", "Industrials", "Financial Services", "Basic Materials", "Energy"}

    cycle = "성장기" if sector in growth_sectors else "성숙기/안정기"
    if sector in defensive_sectors:
        nature = "경기방어적"
    elif sector in cyclical_sectors:
        nature = "경기순응적"
    else:
        nature = "중립/추가 판단 필요"

    return {"섹터": sector, "세부산업": industry, "산업주기": cycle, "산업특성": nature}


def analyze_technical(hist: pd.DataFrame) -> dict:
    """④ 내재가치 변동(이평선 대비 위치), 시장수급/투자심리(RSI, 거래량)"""
    results = {}
    hist = hist.copy()
    hist["MA20"] = hist["Close"].rolling(20).mean()
    hist["MA60"] = hist["Close"].rolling(60).mean()
    hist["MA120"] = hist["Close"].rolling(120).mean()

    delta = hist["Close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = -delta.clip(upper=0).rolling(14).mean()
    rs = gain / loss
    hist["RSI"] = 100 - (100 / (1 + rs))

    latest = hist.iloc[-1]
    trend = "상승추세 (MA120 상회)" if latest["Close"] > latest["MA120"] else "하락추세 (MA120 하회)"
    rsi_val = latest["RSI"]
    momentum = "과매수" if rsi_val > 70 else ("과매도" if rsi_val < 30 else "중립")

    vol_avg_20 = hist["Volume"].rolling(20).mean().iloc[-1]
    vol_latest = latest["Volume"]
    vol_signal = "거래량 급증 (평균 대비 1.5배 이상)" if vol_latest > vol_avg_20 * 1.5 else "평이한 수준"

    results["추세"] = trend
    results["RSI(14)"] = round(rsi_val, 2) if not np.isnan(rsi_val) else "N/A"
    results["투자심리"] = momentum
    results["수급_거래량"] = vol_signal
    results["chart_data"] = hist

    return results


def summarize_etf_fundamentals(top_holdings_df, sector_weights, info: dict) -> dict:
    """ETF 원본 데이터(top_holdings_df, sector_weights, info)를 요약.
    데이터 수집(funds_data 접근)은 data_sources.py에서 하고, 여기서는 가공만 담당."""
    results = {}
    data_quality = []

    if top_holdings_df is not None and not top_holdings_df.empty:
        results["상위보유종목"] = top_holdings_df.to_dict()
        try:
            weight_col = next((c for c in top_holdings_df.columns
                                if "percent" in c.lower() or "weight" in c.lower()), None)
            if weight_col:
                total_weight = top_holdings_df[weight_col].sum()
                total_weight_pct = total_weight * 100 if total_weight <= 1 else total_weight
                results["상위10종목_비중합(%)"] = round(total_weight_pct, 1)
        except Exception:
            pass
        data_quality.append("상위보유종목: 정상")
    else:
        results["상위보유종목"] = ("데이터 없음 - yfinance 미지원 ETF일 수 있습니다. "
                                    "운용사 홈페이지(예: ishares.com, ssga.com) 확인을 권장합니다")
        data_quality.append("상위보유종목: 실패")

    if sector_weights:
        results["섹터비중"] = sector_weights
        data_quality.append("섹터비중: 정상")
    else:
        results["섹터비중"] = "데이터 없음"
        data_quality.append("섹터비중: 실패")

    results["운용보수(Expense Ratio)"] = info.get("annualReportExpenseRatio", info.get("netExpenseRatio", "N/A"))
    results["순자산총액"] = info.get("totalAssets", "N/A")
    results["배당수익률(%)"] = info.get("yield", "N/A")
    results["카테고리"] = info.get("category", "N/A")
    results["운용사"] = info.get("fundFamily", "N/A")
    results["_데이터품질"] = data_quality

    return results


# =========================================================
# 3. 스코어링 (0~100점 환산)
# =========================================================
def _trend_score(series: pd.Series, better_if_increasing: bool = True):
    """시계열의 최근값 vs 가장 오래된값 비교로 개선/악화 판정 (yfinance는 최근->과거 순서)"""
    vals = series.dropna().tolist() if hasattr(series, "dropna") else []
    if len(vals) < 2:
        return 50, "데이터 부족"
    recent, oldest = vals[0], vals[-1]
    increased = recent > oldest
    good = increased if better_if_increasing else not increased
    return (75 if good else 30), ("개선" if good else "악화")


def score_internal_factors(balance: pd.DataFrame, income: pd.DataFrame, cashflow: pd.DataFrame):
    """① 내부요인 점수: 부채비율(감소 우수), 매출(증가 우수), 영업현금흐름(증가 우수)"""
    sub_scores = []
    detail = {}
    try:
        debt_ratio = (balance.loc["Total Liabilities Net Minority Interest"] / balance.loc["Total Assets"] * 100)
        s, label = _trend_score(debt_ratio, better_if_increasing=False)
        sub_scores.append(s)
        detail["부채비율_추이"] = label
    except Exception:
        detail["부채비율_추이"] = "데이터 없음"

    try:
        s, label = _trend_score(income.loc["Total Revenue"], better_if_increasing=True)
        sub_scores.append(s)
        detail["매출_추이"] = label
    except Exception:
        detail["매출_추이"] = "데이터 없음"

    try:
        s, label = _trend_score(cashflow.loc["Operating Cash Flow"], better_if_increasing=True)
        sub_scores.append(s)
        detail["영업현금흐름_추이"] = label
    except Exception:
        detail["영업현금흐름_추이"] = "데이터 없음"

    score = round(sum(sub_scores) / len(sub_scores)) if sub_scores else 50
    return score, detail


def score_financial_ratios(income: pd.DataFrame):
    """② 재무지표 점수: 영업이익률, 이자보상비율, 매출증가율 (최신값 기준 절대수준 평가)"""
    sub_scores = []
    detail = {}

    try:
        revenue = income.loc["Total Revenue"]
        op_margin = (income.loc["Operating Income"] / revenue * 100).dropna().iloc[0]
        if op_margin >= 20:
            s = 90
        elif op_margin >= 10:
            s = 75
        elif op_margin >= 5:
            s = 55
        elif op_margin >= 0:
            s = 35
        else:
            s = 10
        sub_scores.append(s)
        detail["영업이익률"] = f"{op_margin:.1f}% ({s}점)"
    except Exception:
        detail["영업이익률"] = "데이터 없음"

    try:
        ebit = income.loc["EBIT"] if "EBIT" in income.index else income.loc["Operating Income"]
        interest_exp = income.loc["Interest Expense"].abs()
        coverage = (ebit / interest_exp).dropna().iloc[0]
        if coverage >= 5:
            s = 90
        elif coverage >= 2:
            s = 70
        elif coverage >= 1:
            s = 40
        else:
            s = 10
        sub_scores.append(s)
        detail["이자보상비율"] = f"{coverage:.1f}배 ({s}점)"
    except Exception:
        detail["이자보상비율"] = "데이터 없음 (무차입 가능성 - 미반영)"

    try:
        revenue = income.loc["Total Revenue"]
        growth = (revenue.pct_change(-1) * 100).dropna().iloc[0]
        if growth >= 15:
            s = 90
        elif growth >= 5:
            s = 70
        elif growth >= 0:
            s = 50
        else:
            s = 20
        sub_scores.append(s)
        detail["매출증가율"] = f"{growth:.1f}% ({s}점)"
    except Exception:
        detail["매출증가율"] = "데이터 없음"

    score = round(sum(sub_scores) / len(sub_scores)) if sub_scores else 50
    return score, detail


def score_industry(industry: dict, business_cycle_verdict: str = ""):
    """③ 산업동향 점수: 성장기 우대 + 현재 경기국면과 산업특성의 정합성 반영"""
    score = 60
    detail = {}

    if industry.get("산업주기") == "성장기":
        score += 15
    detail["산업주기_반영"] = industry.get("산업주기", "N/A")

    nature = industry.get("산업특성", "")
    if "활황" in business_cycle_verdict and nature == "경기순응적":
        score += 15
    elif "불황" in business_cycle_verdict and nature == "경기방어적":
        score += 15
    detail["산업특성_반영"] = f"{nature} (현재 경기: {business_cycle_verdict or '판정불가'})"

    score = max(0, min(100, score))
    return score, detail


def score_technical(tech: dict):
    """④ 기술적분석 점수: 추세, RSI, 거래량 신호 종합"""
    score = 50
    detail = {}

    if "상승" in tech.get("추세", ""):
        score += 20
        trend_up = True
    else:
        score -= 20
        trend_up = False
    detail["추세_반영"] = tech.get("추세", "N/A")

    rsi = tech.get("RSI(14)")
    if isinstance(rsi, (int, float)):
        if rsi > 70 or rsi < 30:
            score -= 10  # 과매수/과매도는 변동성 리스크로 감점
        detail["RSI_반영"] = f"{rsi}"

    if "급증" in tech.get("수급_거래량", ""):
        score += 10 if trend_up else -10
    detail["거래량_반영"] = tech.get("수급_거래량", "N/A")

    score = max(0, min(100, round(score)))
    return score, detail


def score_etf_fundamentals(etf_data: dict, currency: str = "USD"):
    """ETF 구성 점수: 운용보수(낮을수록 우수), 순자산규모(클수록 안정적), 상위종목 집중도(적정 분산)
    순자산 임계값은 통화에 따라 스케일 조정 (KRW는 USD 대비 약 1300배 근사치 적용)"""
    scores = []
    detail = {}
    fx_scale = 1300 if currency == "KRW" else 1

    expense = etf_data.get("운용보수(Expense Ratio)")
    if isinstance(expense, (int, float)):
        expense_pct = expense * 100 if expense < 1 else expense
        if expense_pct <= 0.2:
            s = 90
        elif expense_pct <= 0.5:
            s = 70
        elif expense_pct <= 1.0:
            s = 50
        else:
            s = 25
        detail["운용보수_반영"] = f"{expense_pct:.2f}% ({s}점)"
        scores.append(s)
    else:
        detail["운용보수_반영"] = "데이터 없음 - 미반영"

    aum = etf_data.get("순자산총액")
    if isinstance(aum, (int, float)):
        if aum >= 10_000_000_000 * fx_scale:
            s = 85
        elif aum >= 1_000_000_000 * fx_scale:
            s = 70
        elif aum >= 100_000_000 * fx_scale:
            s = 50
        else:
            s = 30
        unit = "원" if currency == "KRW" else "$"
        detail["순자산_반영"] = f"{unit}{aum:,.0f} ({s}점)"
        scores.append(s)
    else:
        detail["순자산_반영"] = "데이터 없음 - 미반영"

    conc = etf_data.get("상위10종목_비중합(%)")
    if isinstance(conc, (int, float)):
        if conc <= 30:
            s = 80
        elif conc <= 50:
            s = 60
        elif conc <= 70:
            s = 40
        else:
            s = 25
        detail["집중도_반영"] = f"상위종목 비중합 {conc:.1f}% ({s}점)"
        scores.append(s)
    else:
        detail["집중도_반영"] = "데이터 없음 - 미반영"

    if not scores:
        detail["안내"] = "핵심 데이터가 모두 없어 중립값(50점)을 부여했습니다"
        return 50, detail

    score = round(sum(scores) / len(scores))
    return score, detail


def score_market_item(verdict_text: str) -> int:
    """시장환경 판정 문구를 점수로 변환"""
    positive_kw = ["활황", "완화", "해소", "긍정", "개선"]
    negative_kw = ["불황", "긴축", "위험발생", "부정", "악화"]
    text = verdict_text or ""
    if any(k in text for k in positive_kw):
        return 80
    if any(k in text for k in negative_kw):
        return 20
    return 50


def grade_label(score: float) -> str:
    if score >= 80:
        return "매우 긍정적 (A)"
    elif score >= 65:
        return "긍정적 (B)"
    elif score >= 50:
        return "중립 (C)"
    elif score >= 35:
        return "주의 (D)"
    else:
        return "부정적 (E)"


def compute_overall_score(fundamental_scores: dict, market_scores: dict, market_weights: dict,
                           fundamental_weight_pct: float) -> dict:
    """펀더멘탈/시장환경 점수를 사이드바 가중치로 종합.
    fundamental_scores: {"내부요인": 70, "재무지표": 60, ...} 형태의 dict (항목 수는 종목 유형에 따라 다름)
    market_scores: {"경기동향": 80, "통화_재정정책": 20, ...}
    market_weights: 각 시장환경 항목의 정규화된 가중치 (합계 1.0)
    fundamental_weight_pct: 0~100 사이, 펀더멘탈에 부여할 비중(%)
    """
    if not fundamental_scores:
        raise ValueError("fundamental_scores가 비어 있습니다")
    if not market_scores:
        raise ValueError("market_scores가 비어 있습니다")

    fundamental_avg = sum(fundamental_scores.values()) / len(fundamental_scores)
    market_avg = sum(market_scores[k] * market_weights.get(k, 0) for k in market_scores)
    overall = round(fundamental_avg * (fundamental_weight_pct / 100)
                     + market_avg * (1 - fundamental_weight_pct / 100))

    return {
        "fundamental_avg": fundamental_avg,
        "market_avg": market_avg,
        "overall_score": overall,
        "grade": grade_label(overall),
    }
