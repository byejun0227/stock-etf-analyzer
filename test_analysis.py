"""
test_analysis.py — analysis.py 순수 로직에 대한 단위테스트

외부 패키지 없이 표준 라이브러리 unittest + pandas/numpy만으로 동작합니다.
(yfinance, streamlit, requests 설치 없이도 실행 가능)

실행 방법:
    python -m unittest test_analysis.py -v
"""

import os
import sys
import unittest

import pandas as pd

# analysis.py는 Vercel Python 함수 번들링을 위해 api/_lib/ 아래로 이동했습니다.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "api", "_lib"))

import analysis


# =========================================================
# 테스트용 가짜(fake) 데이터 생성 헬퍼
# yfinance의 재무제표는 columns=연도(최근->과거), index=계정과목 형태입니다.
# =========================================================
def make_income_statement(revenues, op_incomes, interest_expenses=None, ebit=None):
    """revenues/op_incomes는 [최근값, ..., 가장 오래된 값] 순서의 리스트"""
    years = [f"202{4 - i}" for i in range(len(revenues))]
    data = {
        "Total Revenue": revenues,
        "Operating Income": op_incomes,
    }
    if interest_expenses is not None:
        data["Interest Expense"] = interest_expenses
    if ebit is not None:
        data["EBIT"] = ebit
    df = pd.DataFrame(data, index=years).T
    return df


def make_balance_sheet(total_assets, total_liabilities):
    years = [f"202{4 - i}" for i in range(len(total_assets))]
    df = pd.DataFrame(
        {"Total Assets": total_assets, "Total Liabilities Net Minority Interest": total_liabilities},
        index=years,
    ).T
    return df


def make_cashflow(ocf):
    years = [f"202{4 - i}" for i in range(len(ocf))]
    df = pd.DataFrame({"Operating Cash Flow": ocf}, index=years).T
    return df


def make_price_history(closes, volumes=None):
    """RSI/이평선 계산에 충분한 길이(120일 이상)의 가짜 가격 시계열 생성"""
    n = len(closes)
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    if volumes is None:
        volumes = [1_000_000] * n
    return pd.DataFrame({"Close": closes, "Volume": volumes}, index=dates)


# =========================================================
# 1. 티커 정규화 테스트
# =========================================================
class TestNormalizeTickerInput(unittest.TestCase):
    def test_us_ticker_uppercased(self):
        self.assertEqual(analysis.normalize_ticker_input("aapl"), "AAPL")

    def test_us_ticker_already_uppercase(self):
        self.assertEqual(analysis.normalize_ticker_input("SPY"), "SPY")

    def test_korean_6digit_code_appends_ks(self):
        self.assertEqual(analysis.normalize_ticker_input("005930"), "005930.KS")

    def test_korean_etf_name_lookup(self):
        self.assertEqual(analysis.normalize_ticker_input("KODEX 200"), "069500.KS")
        self.assertEqual(analysis.normalize_ticker_input("TIGER 200"), "102110.KS")

    def test_already_suffixed_ks_preserved(self):
        self.assertEqual(analysis.normalize_ticker_input("005930.ks"), "005930.KS")

    def test_already_suffixed_kq_preserved(self):
        self.assertEqual(analysis.normalize_ticker_input("123456.KQ"), "123456.KQ")

    def test_unknown_korean_name_falls_back_to_us_style(self):
        # 매핑 테이블에 없는 이름은 미국 티커처럼 그대로 대문자 반환 (호출부에서 실패 처리)
        self.assertEqual(analysis.normalize_ticker_input("존재하지않는ETF"), "존재하지않는ETF")

    def test_empty_input(self):
        self.assertEqual(analysis.normalize_ticker_input(""), "")

    def test_whitespace_trimmed(self):
        self.assertEqual(analysis.normalize_ticker_input("  aapl  "), "AAPL")


# =========================================================
# 2. 재무제표 기반 분석/점수 테스트
# =========================================================
class TestInternalFactorsScoring(unittest.TestCase):
    def test_improving_company_scores_high(self):
        # 매출 증가, 영업현금흐름 증가, 부채비율 감소 -> 좋은 점수 기대
        balance = make_balance_sheet(
            total_assets=[1000, 900, 800],
            total_liabilities=[300, 350, 400],  # 최근이 더 낮음 -> 부채비율 개선
        )
        income = make_income_statement(
            revenues=[500, 450, 400],  # 최근이 더 큼 -> 매출 증가
            op_incomes=[100, 80, 60],
        )
        cashflow = make_cashflow(ocf=[120, 90, 70])  # 최근이 더 큼 -> OCF 증가

        score, detail = analysis.score_internal_factors(balance, income, cashflow)
        self.assertEqual(score, 75)  # 세 항목 모두 개선 -> 75점 평균
        self.assertEqual(detail["부채비율_추이"], "개선")
        self.assertEqual(detail["매출_추이"], "개선")
        self.assertEqual(detail["영업현금흐름_추이"], "개선")

    def test_deteriorating_company_scores_low(self):
        balance = make_balance_sheet(
            total_assets=[1000, 900, 800],
            total_liabilities=[600, 400, 300],  # 최근이 더 높음 -> 부채비율 악화
        )
        income = make_income_statement(
            revenues=[300, 400, 500],  # 최근이 더 작음 -> 매출 감소
            op_incomes=[50, 60, 70],
        )
        cashflow = make_cashflow(ocf=[40, 60, 80])  # 최근이 더 작음 -> OCF 감소

        score, detail = analysis.score_internal_factors(balance, income, cashflow)
        self.assertEqual(score, 30)
        self.assertEqual(detail["부채비율_추이"], "악화")

    def test_missing_data_returns_neutral_and_does_not_crash(self):
        empty_df = pd.DataFrame()
        score, detail = analysis.score_internal_factors(empty_df, empty_df, empty_df)
        self.assertEqual(score, 50)  # sub_scores가 비어 기본값 50
        self.assertEqual(detail["부채비율_추이"], "데이터 없음")


class TestFinancialRatiosScoring(unittest.TestCase):
    def test_high_margin_high_coverage_high_growth(self):
        income = make_income_statement(
            revenues=[1000, 800],
            op_incomes=[250, 150],  # 영업이익률 25% -> 90점
            interest_expenses=[10, 10],  # EBIT/이자 = 25 -> 90점
            ebit=[250, 150],
        )
        score, detail = analysis.score_financial_ratios(income)
        self.assertGreaterEqual(score, 80)
        self.assertIn("90점", detail["영업이익률"])

    def test_negative_margin_scores_low(self):
        income = make_income_statement(
            revenues=[1000, 1000],
            op_incomes=[-50, 0],  # 영업이익률 -5% -> 10점
        )
        score, detail = analysis.score_financial_ratios(income)
        self.assertIn("10점", detail["영업이익률"])

    def test_revenue_growth_thresholds(self):
        # 매출 20% 증가 -> 90점 구간
        income = make_income_statement(revenues=[1200, 1000], op_incomes=[100, 100])
        _, detail = analysis.score_financial_ratios(income)
        self.assertIn("90점", detail["매출증가율"])


class TestIndustryScoring(unittest.TestCase):
    def test_growth_sector_gets_bonus(self):
        industry = {"산업주기": "성장기", "산업특성": "경기순응적"}
        score, _ = analysis.score_industry(industry, business_cycle_verdict="")
        self.assertEqual(score, 75)  # 60 base + 15 성장기

    def test_cyclical_sector_in_boom_gets_extra_bonus(self):
        industry = {"산업주기": "성장기", "산업특성": "경기순응적"}
        score, detail = analysis.score_industry(industry, business_cycle_verdict="경기활황(성장기대감)")
        self.assertEqual(score, 90)  # 60 + 15(성장기) + 15(경기순응+활황 정합)
        self.assertIn("활황", detail["산업특성_반영"])

    def test_defensive_sector_in_recession_gets_bonus(self):
        industry = {"산업주기": "성숙기/안정기", "산업특성": "경기방어적"}
        score, _ = analysis.score_industry(industry, business_cycle_verdict="경기불황(불확실성)")
        self.assertEqual(score, 75)  # 60 + 0(성장기 아님) + 15(방어+불황 정합)

    def test_score_capped_at_100(self):
        industry = {"산업주기": "성장기", "산업특성": "경기순응적"}
        score, _ = analysis.score_industry(industry, business_cycle_verdict="경기활황(성장기대감)")
        self.assertLessEqual(score, 100)


class TestAnalyzeIndustry(unittest.TestCase):
    def test_technology_sector_is_growth(self):
        result = analysis.analyze_industry({"sector": "Technology", "industry": "Semiconductors"})
        self.assertEqual(result["산업주기"], "성장기")

    def test_utilities_is_defensive(self):
        result = analysis.analyze_industry({"sector": "Utilities", "industry": "Electric"})
        self.assertEqual(result["산업특성"], "경기방어적")

    def test_unknown_sector_handled_gracefully(self):
        result = analysis.analyze_industry({})
        self.assertEqual(result["섹터"], "Unknown")


# =========================================================
# 3. 기술적 분석 테스트
# =========================================================
class TestTechnicalAnalysis(unittest.TestCase):
    def test_uptrend_detected(self):
        # 150일간 꾸준히 상승하는 가격 시계열
        closes = [100 + i * 0.5 for i in range(150)]
        hist = make_price_history(closes)
        tech = analysis.analyze_technical(hist)
        self.assertIn("상승", tech["추세"])

        score, detail = analysis.score_technical(tech)
        self.assertGreaterEqual(score, 50)  # 상승추세는 가점

    def test_downtrend_detected(self):
        closes = [200 - i * 0.5 for i in range(150)]
        hist = make_price_history(closes)
        tech = analysis.analyze_technical(hist)
        self.assertIn("하락", tech["추세"])

        score, _ = analysis.score_technical(tech)
        self.assertLess(score, 50)

    def test_volume_spike_detected(self):
        closes = [100 + i * 0.1 for i in range(150)]
        volumes = [1_000_000] * 149 + [5_000_000]  # 마지막날 거래량 급증
        hist = make_price_history(closes, volumes)
        tech = analysis.analyze_technical(hist)
        self.assertIn("급증", tech["수급_거래량"])


# =========================================================
# 4. ETF 스코어링 테스트
# =========================================================
class TestEtfScoring(unittest.TestCase):
    def test_low_expense_large_aum_diversified_scores_high(self):
        etf_data = {
            "운용보수(Expense Ratio)": 0.0015,  # 0.15%
            "순자산총액": 50_000_000_000,  # $50B
            "상위10종목_비중합(%)": 25,
        }
        score, detail = analysis.score_etf_fundamentals(etf_data, currency="USD")
        self.assertGreaterEqual(score, 80)

    def test_krw_threshold_scaling(self):
        # 원화 250억원(약 $19M)은 소형 ETF -> 낮은 점수여야 함
        etf_data = {"순자산총액": 25_000_000_000}  # 250억원
        score, detail = analysis.score_etf_fundamentals(etf_data, currency="KRW")
        self.assertIn("원", detail["순자산_반영"])

    def test_krw_large_fund_scores_well(self):
        # KODEX 200 실제 규모(약 21조원)에 준하는 값
        etf_data = {"순자산총액": 21_000_000_000_000}  # 21조원
        score, detail = analysis.score_etf_fundamentals(etf_data, currency="KRW")
        self.assertGreaterEqual(score, 80)

    def test_missing_all_data_returns_neutral(self):
        score, detail = analysis.score_etf_fundamentals({}, currency="USD")
        self.assertEqual(score, 50)
        self.assertIn("안내", detail)

    def test_high_concentration_penalized(self):
        etf_data = {"상위10종목_비중합(%)": 85}
        score, detail = analysis.score_etf_fundamentals(etf_data, currency="USD")
        self.assertIn("25점", detail["집중도_반영"])


class TestSummarizeEtfFundamentals(unittest.TestCase):
    def test_missing_holdings_flagged_in_quality(self):
        info = {"annualReportExpenseRatio": 0.001, "totalAssets": 1_000_000}
        result = analysis.summarize_etf_fundamentals(None, None, info)
        self.assertIn("상위보유종목: 실패", result["_데이터품질"])
        self.assertIn("섹터비중: 실패", result["_데이터품질"])

    def test_present_holdings_computes_concentration(self):
        holdings_df = pd.DataFrame({"Holding Percent": [0.1, 0.08, 0.07]},
                                    index=["AAPL", "MSFT", "NVDA"])
        info = {"totalAssets": 1_000_000}
        result = analysis.summarize_etf_fundamentals(holdings_df, {"Technology": 0.5}, info)
        self.assertEqual(result["상위10종목_비중합(%)"], 25.0)
        self.assertIn("상위보유종목: 정상", result["_데이터품질"])


# =========================================================
# 5. 시장환경 판정 -> 점수 변환 테스트
# =========================================================
class TestMarketItemScore(unittest.TestCase):
    def test_positive_keywords(self):
        for text in ["경기활황(성장기대감)", "완화(금리 인하 기조)", "위험해소(불확실성 완화)", "긍정적(변동성 축소)"]:
            self.assertEqual(analysis.score_market_item(text), 80, msg=f"failed for: {text}")

    def test_negative_keywords(self):
        for text in ["경기불황(불확실성)", "긴축(금리 인상 기조)", "위험발생(불확실성 확대)", "부정적(변동성 확대)"]:
            self.assertEqual(analysis.score_market_item(text), 20, msg=f"failed for: {text}")

    def test_neutral_or_unknown(self):
        self.assertEqual(analysis.score_market_item("동결(변화 없음)"), 50)
        self.assertEqual(analysis.score_market_item(""), 50)
        self.assertEqual(analysis.score_market_item(None), 50)


# =========================================================
# 6. 등급 라벨 경계값 테스트
# =========================================================
class TestGradeLabel(unittest.TestCase):
    def test_boundaries(self):
        self.assertEqual(analysis.grade_label(100), "매우 긍정적 (A)")
        self.assertEqual(analysis.grade_label(80), "매우 긍정적 (A)")
        self.assertEqual(analysis.grade_label(79), "긍정적 (B)")
        self.assertEqual(analysis.grade_label(65), "긍정적 (B)")
        self.assertEqual(analysis.grade_label(64), "중립 (C)")
        self.assertEqual(analysis.grade_label(50), "중립 (C)")
        self.assertEqual(analysis.grade_label(49), "주의 (D)")
        self.assertEqual(analysis.grade_label(35), "주의 (D)")
        self.assertEqual(analysis.grade_label(34), "부정적 (E)")
        self.assertEqual(analysis.grade_label(0), "부정적 (E)")


# =========================================================
# 7. 종합점수 계산 테스트
# =========================================================
class TestComputeOverallScore(unittest.TestCase):
    def setUp(self):
        self.fundamental_scores = {"내부요인": 80, "재무지표": 80, "산업동향": 80, "기술적분석": 80}
        self.market_scores = {"경기동향": 20, "통화_재정정책": 20, "지정학_불확실성": 20, "자본시장_정책": 20}
        self.equal_weights = {"경기동향": 0.25, "통화_재정정책": 0.25, "지정학_불확실성": 0.25, "자본시장_정책": 0.25}

    def test_equal_weight_split(self):
        result = analysis.compute_overall_score(
            self.fundamental_scores, self.market_scores, self.equal_weights, fundamental_weight_pct=50
        )
        self.assertEqual(result["fundamental_avg"], 80)
        self.assertEqual(result["market_avg"], 20)
        self.assertEqual(result["overall_score"], 50)  # (80*0.5 + 20*0.5)

    def test_fundamental_heavy_weight(self):
        result = analysis.compute_overall_score(
            self.fundamental_scores, self.market_scores, self.equal_weights, fundamental_weight_pct=100
        )
        self.assertEqual(result["overall_score"], 80)

    def test_market_heavy_weight(self):
        result = analysis.compute_overall_score(
            self.fundamental_scores, self.market_scores, self.equal_weights, fundamental_weight_pct=0
        )
        self.assertEqual(result["overall_score"], 20)

    def test_grade_matches_score(self):
        result = analysis.compute_overall_score(
            self.fundamental_scores, self.market_scores, self.equal_weights, fundamental_weight_pct=100
        )
        self.assertEqual(result["grade"], analysis.grade_label(result["overall_score"]))

    def test_uneven_market_weights_shift_result(self):
        # 지정학만 100% 가중치를 주면 market_avg는 지정학 점수(20)와 동일해야 함
        skewed_weights = {"경기동향": 0, "통화_재정정책": 0, "지정학_불확실성": 1.0, "자본시장_정책": 0}
        result = analysis.compute_overall_score(
            self.fundamental_scores, self.market_scores, skewed_weights, fundamental_weight_pct=0
        )
        self.assertEqual(result["overall_score"], 20)

    def test_empty_fundamental_scores_raises(self):
        with self.assertRaises(ValueError):
            analysis.compute_overall_score({}, self.market_scores, self.equal_weights, 50)

    def test_empty_market_scores_raises(self):
        with self.assertRaises(ValueError):
            analysis.compute_overall_score(self.fundamental_scores, {}, self.equal_weights, 50)


if __name__ == "__main__":
    unittest.main(verbosity=2)
