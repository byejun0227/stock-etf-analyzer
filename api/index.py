"""
api/index.py — Vercel Python Function (FastAPI)

프론트엔드(Next.js)가 POST /api/analyze 로 티커를 보내면, 기존 analysis.py/data_sources.py의
로직을 그대로 호출해 종목 분석 결과 전체를 JSON 하나로 반환한다. 원본 app.py(Streamlit)가
하던 오케스트레이션(=_fetch_all + 각종 score_* 호출 순서)을 그대로 옮긴 것이며, 계산 로직
자체는 변경하지 않았다 (analysis.py는 test_analysis.py의 43개 unittest로 검증됨).
"""

import math
import os
import re
import sys
import time
from typing import Any

# Vercel's Python loader (importlib.util.spec_from_file_location) does not add
# this file's own directory to sys.path, so `from _lib... import` fails at
# import time unless we add it ourselves first.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import jwt
import numpy as np
import pandas as pd
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from _lib.analysis import (
    analyze_financial_ratios,
    analyze_industry,
    analyze_internal_factors,
    analyze_technical,
    compare_valuation_vs_peers,
    compute_overall_score,
    extract_valuation_metrics,
    score_etf_fundamentals,
    score_financial_ratios,
    score_industry,
    score_internal_factors,
    score_market_item,
    score_technical,
)
from _lib.data_sources import (
    analyze_market_environment,
    classify_ticker,
    fetch_etf_raw_data,
    get_financials,
    get_peer_info_list,
    get_price_history,
)

app = FastAPI()

MARKET_KEYS = ["경기동향", "통화_재정정책", "지정학_불확실성", "자본시장_정책"]

# 워커 인스턴스가 재사용되는 동안(Fluid Compute warm invocation)만 유효한 best-effort 캐시.
# 서버리스 특성상 보장되지 않으므로 순수 성능 최적화 용도로만 사용한다.
_CACHE: dict[str, tuple[float, Any]] = {}
_CACHE_TTL_SECONDS = 3600


def _cache_get(key: str):
    hit = _CACHE.get(key)
    if not hit:
        return None
    ts, value = hit
    if time.time() - ts > _CACHE_TTL_SECONDS:
        _CACHE.pop(key, None)
        return None
    return value


def _cache_set(key: str, value: Any) -> None:
    _CACHE[key] = (time.time(), value)


class MarketWeights(BaseModel):
    경기동향: float = 0.25
    통화_재정정책: float = 0.25
    지정학_불확실성: float = 0.25
    자본시장_정책: float = 0.25


class AnalyzeRequest(BaseModel):
    ticker: str
    fredApiKey: str = ""
    fundamentalWeightPct: float = 60
    marketWeights: MarketWeights = MarketWeights()


def _is_authorized(request: Request) -> bool:
    """lib/session.ts가 발급하는 세션 쿠키(JWT, HS256)를 검증.

    프론트엔드 page.tsx의 로그인 게이트와 동일한 인증을 이 엔드포인트에도
    적용해, 로그인 없이 직접 POST /api/analyze를 호출하는 것을 막는다.
    """
    secret = os.environ.get("SESSION_SECRET")
    if not secret:
        return False
    token = request.cookies.get("session")
    if not token:
        return False
    try:
        jwt.decode(token, secret, algorithms=["HS256"])
        return True
    except jwt.PyJWTError:
        return False


def _is_kr_input(raw: str) -> bool:
    raw = raw.strip()
    if re.fullmatch(r"\d{6}(\.KS|\.KQ)?", raw, re.IGNORECASE):
        return True
    return any("가" <= c <= "힣" for c in raw)


def _json_safe(obj: Any) -> Any:
    """numpy/pandas 스칼라, NaN 등을 표준 JSON 타입으로 재귀 변환."""
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        v = float(obj)
        return None if math.isnan(v) or math.isinf(v) else v
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, float):
        return None if math.isnan(obj) or math.isinf(obj) else obj
    if isinstance(obj, pd.Timestamp):
        return obj.strftime("%Y-%m-%d")
    return obj


def _price_chart(hist_with_indicators: pd.DataFrame) -> list[dict]:
    cols = ["Close", "MA20", "MA60", "MA120", "Volume"]
    sub = hist_with_indicators[cols].reset_index()
    sub = sub.rename(columns={
        sub.columns[0]: "date",
        "Close": "close", "MA20": "ma20", "MA60": "ma60",
        "MA120": "ma120", "Volume": "volume",
    })
    sub["date"] = sub["date"].apply(
        lambda d: d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d)
    )
    return sub.to_dict("records")


@app.get("/api/health")
def health():
    return {"ok": True}


def _gather_ticker_data(ticker_input: str):
    """classify/hist/재무/피어 조회를 워커 인스턴스 수명 동안 캐싱 (best-effort)."""
    cache_key = f"ticker:{ticker_input.upper()}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    c = classify_ticker(ticker_input)
    hist = get_price_history(c["ticker_obj"])

    financials = balance = cashflow = None
    etf_data = None
    peers_raw: list = []
    if not hist.empty:
        if c["is_etf"]:
            etf_data = fetch_etf_raw_data(c["ticker_obj"], c["info"])
        else:
            financials, balance, cashflow = get_financials(c["ticker_obj"])
            peers_raw = get_peer_info_list(c["info"], c["resolved_ticker"], max_peers=5)

    bundle = {
        "c": c, "hist": hist,
        "financials": financials, "balance": balance, "cashflow": cashflow,
        "etf_data": etf_data, "peers_raw": peers_raw,
    }
    _cache_set(cache_key, bundle)
    return bundle


def _gather_market(fred_api_key: str, market_type: str):
    """FRED/VIX 등 시장환경 조회를 (시장, 키) 단위로 캐싱 (best-effort)."""
    cache_key = f"market:{market_type}:{fred_api_key}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    market = analyze_market_environment(fred_api_key or "", market=market_type)
    _cache_set(cache_key, market)
    return market


@app.post("/api/analyze")
def analyze(req: AnalyzeRequest, request: Request):
    if not _is_authorized(request):
        return JSONResponse(status_code=401, content={"error": "login required", "kind": "unknown"})

    ticker_input = req.ticker.strip()
    if not ticker_input:
        return JSONResponse(status_code=400, content={"error": "ticker is required", "kind": "unknown"})

    try:
        bundle = _gather_ticker_data(ticker_input)
    except Exception as e:
        return JSONResponse(status_code=502, content={"error": str(e), "kind": "unknown"})

    c = bundle["c"]
    info = c["info"]
    resolved = c["resolved_ticker"]
    is_etf = c["is_etf"]
    market_type = c["market"]
    currency = c["currency"]
    hist = bundle["hist"]

    if hist.empty:
        kind = "no_data_kr" if _is_kr_input(ticker_input) else "no_data_generic"
        return JSONResponse(status_code=404, content={"error": "no price data available", "kind": kind})

    financials, balance, cashflow = bundle["financials"], bundle["balance"], bundle["cashflow"]
    etf_data = bundle["etf_data"]
    peers_raw = bundle["peers_raw"]

    try:
        market = _gather_market(req.fredApiKey or "", market_type)

        business_cycle_verdict = market.get("경기동향", {}).get("판정", "")
        market_scores = {
            key: score_market_item(market.get(key, {}).get("판정", "")) for key in MARKET_KEYS
        }

        tech = analyze_technical(hist)
        tech_score, tech_score_detail = score_technical(tech)

        fundamental_scores: dict[str, int] = {}
        etf_payload = internal_payload = ratios_payload = industry_payload = valuation_payload = None

        if is_etf:
            etf_score, etf_detail = score_etf_fundamentals(etf_data, currency)
            fundamental_scores["ETF구성"] = etf_score
            etf_payload = {
                "score": etf_score,
                "detail": etf_detail,
                "raw": {k: v for k, v in etf_data.items() if k != "_데이터품질"},
            }
        else:
            internal = analyze_internal_factors(balance, financials, cashflow)
            internal_score, internal_detail = score_internal_factors(balance, financials, cashflow)
            fundamental_scores["내부요인"] = internal_score
            internal_payload = {"score": internal_score, "detail": internal_detail, "raw": internal}

            ratios = analyze_financial_ratios(financials)
            ratios_score, ratios_detail = score_financial_ratios(financials)
            fundamental_scores["재무지표"] = ratios_score
            ratios_payload = {"score": ratios_score, "detail": ratios_detail, "raw": ratios}

            industry = analyze_industry(info)
            industry_score, industry_detail = score_industry(industry, business_cycle_verdict)
            fundamental_scores["산업동향"] = industry_score
            industry_payload = {
                "score": industry_score,
                "detail": industry_detail,
                "sector": industry.get("섹터", "N/A"),
                "industryName": industry.get("세부산업", "N/A"),
                "cycle": industry.get("산업주기", "N/A"),
                "nature": industry.get("산업특성", "N/A"),
            }

            main_metrics = extract_valuation_metrics(info, ticker_obj=c["ticker_obj"])
            peers_data_v = [
                {"ticker": p["ticker"], "metrics": extract_valuation_metrics(p["info"])}
                for p in peers_raw
            ]
            valuation = compare_valuation_vs_peers(resolved, main_metrics, peers_data_v)
            valuation_payload = {
                "peerTickers": valuation["비교종목"],
                "table": valuation["지표_테이블"],
            }

        fundamental_scores["기술적분석"] = tech_score

        weights_dict = req.marketWeights.model_dump()
        overall = compute_overall_score(
            fundamental_scores, market_scores, weights_dict, req.fundamentalWeightPct
        )

        cur_price = info.get("currentPrice") or info.get("regularMarketPrice")
        prev_close = info.get("previousClose") or info.get("regularMarketPreviousClose")
        day_chg = (
            (cur_price - prev_close) / prev_close * 100
            if (cur_price and prev_close)
            else None
        )

        response = {
            "ticker": ticker_input,
            "resolvedTicker": resolved,
            "name": info.get("longName", ticker_input),
            "isEtf": is_etf,
            "marketType": market_type,
            "currency": currency,
            "currentPrice": cur_price,
            "previousClose": prev_close,
            "dayChangePct": day_chg,
            "fundamentalScores": fundamental_scores,
            "marketScores": market_scores,
            "overall": {
                "overallScore": overall["overall_score"],
                "fundamentalAvg": overall["fundamental_avg"],
                "marketAvg": overall["market_avg"],
                "grade": overall["grade"],
            },
            "etf": etf_payload,
            "internal": internal_payload,
            "ratios": ratios_payload,
            "industry": industry_payload,
            "valuation": valuation_payload,
            "technical": {
                "score": tech_score,
                "trend": tech["추세"],
                "rsi": tech["RSI(14)"],
                "sentiment": tech["투자심리"],
                "volumeSignal": tech["수급_거래량"],
                "chart": _price_chart(tech["chart_data"]),
            },
            "market": market,
            "notices": {
                "krLimited": market_type == "KR" and not is_etf,
                "globalLimited": market_type not in ("KR", "US"),
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "kind": "unknown"},
        )

    return JSONResponse(content=_json_safe(response))
