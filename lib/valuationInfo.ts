// Ported from analysis.py VALUATION_METRIC_INFO.
export const VALUATION_METRIC_INFO: Record<string, { name: string; desc: string; direction: "low_good" | "high_good" }> = {
  PER: { name: "주가수익비율", desc: "낮을수록 수익 대비 저평가. 업종·성장성에 따라 다르게 해석.", direction: "low_good" },
  PBR: { name: "주가순자산비율", desc: "낮을수록 자산 대비 저평가. 1배 미만은 청산가치 이하.", direction: "low_good" },
  PSR: { name: "주가매출비율", desc: "낮을수록 매출 대비 저평가. 적자·성장 기업 평가에 유용.", direction: "low_good" },
  EPS: { name: "주당순이익", desc: "높을수록 주당 이익이 크고 PER 계산의 기반.", direction: "high_good" },
  "ROE(%)": { name: "자기자본이익률", desc: "높을수록 자본 활용 효율이 우수. 15% 이상이 양호 기준.", direction: "high_good" },
};

export const VALUATION_METRIC_ORDER = ["PER", "PBR", "PSR", "EPS", "ROE(%)"];
