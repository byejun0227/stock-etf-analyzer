// Ported from app.py MARKET_LABELS / MARKET_LABELS_EN / MARKET_INDEX_DESC / MARKET_FLAGS.

export const MARKET_KEYS = ["경기동향", "통화_재정정책", "지정학_불확실성", "자본시장_정책"] as const;
export type MarketKey = (typeof MARKET_KEYS)[number];

export const MARKET_LABELS: Record<MarketKey, string> = {
  경기동향: "경기동향 (경기활황 vs 경기불황)",
  통화_재정정책: "통화/재정정책 (완화 vs 긴축)",
  지정학_불확실성: "지정학적 불확실성 (위험발생 vs 위험해소)",
  자본시장_정책: "자본시장 정책 변화 (긍정 vs 부정)",
};

export const MARKET_LABELS_EN: Record<MarketKey, string> = {
  경기동향: "Business Cycle (Boom vs Recession)",
  통화_재정정책: "Monetary Policy (Easing vs Tightening)",
  지정학_불확실성: "Geopolitical Risk (Rising vs Easing)",
  자본시장_정책: "Capital Market Policy (Positive vs Negative)",
};

export const MARKET_FLAGS: Record<string, string> = {
  KR: "🇰🇷", US: "🇺🇸",
  JP: "🇯🇵", CN: "🇨🇳", HK: "🇭🇰",
  TW: "🇹🇼", IN: "🇮🇳",
  DE: "🇩🇪", UK: "🇬🇧", FR: "🇫🇷",
  NL: "🇳🇱", IT: "🇮🇹", CH: "🇨🇭",
  BE: "🇧🇪", ES: "🇪🇸", NO: "🇳🇴", SE: "🇸🇪",
};

export const MARKET_INDEX_DESC: Record<string, Record<MarketKey, string>> = {
  US: {
    경기동향:
      "📈 사용 지표 (미국)\n- USSLIND (미국 경기선행지수) — Conference Board 발표. 향후 6~12개월 경기 방향을 예측.\n- UNRATE (실업률) — 미국 노동시장 건전성 지표.",
    통화_재정정책:
      "📈 사용 지표 (미국)\n- FEDFUNDS (미국 기준금리) — 연준(Fed) 단기 정책금리. 인상 시 긴축, 인하 시 완화.\n- M2SL (M2 통화량) — 광의 통화량. 증가율이 높으면 유동성 확대.",
    지정학_불확실성: "📈 사용 지표 (미국)\n- USEPUINDXD (경제정책 불확실성 지수, EPU) — 뉴스 기사 빈도 기반 산출. 높을수록 불확실성 확대.",
    자본시장_정책: "📈 사용 지표 (미국)\n- VIX (CBOE 변동성 지수) — S&P 500 옵션 기반 공포 지수. 20 이하 안정, 30 이상 불안.",
  },
  KR: {
    경기동향:
      "📈 사용 지표 (한국)\n- KOSPI 지수 추이 — 6개월 전 대비 등락으로 경기 방향성 파악.\n- 한국 실업률 (LRHUTTTTKSM156S) — OECD 기준 조화 실업률.",
    통화_재정정책:
      "📈 사용 지표 (한국)\n- 한국 기준금리 (IRSTCB01KRM156N) — 한국은행(BOK) 정책금리.\n- 한국 M2 통화량 (MYAGKRM052S) — 광의 통화량 YoY 증가율.",
    지정학_불확실성: "📈 사용 지표 (한국)\n- 글로벌 EPU 지수 (USEPUINDXD) — 한국 전용 지수 제한으로 글로벌 EPU 대리 사용.",
    자본시장_정책: "📈 사용 지표 (한국)\n- VKOSPI — 코스피200 기반 한국판 공포 지수. 데이터 미제공 시 KOSPI 20일 변동성으로 대체.",
  },
  DEFAULT: {
    경기동향: "📈 사용 지표 (미국 대리)\n- 해당 시장 전용 지표가 지원되지 않아 미국 지표(USSLIND, UNRATE)를 대리 표시합니다.",
    통화_재정정책: "📈 사용 지표 (미국 대리)\n- 해당 시장 전용 지표가 지원되지 않아 미국 지표(FEDFUNDS, M2SL)를 대리 표시합니다.",
    지정학_불확실성: "📈 사용 지표 (미국 대리)\n- 해당 시장 전용 지표가 지원되지 않아 미국 EPU 지수를 대리 표시합니다.",
    자본시장_정책: "📈 사용 지표 (미국 대리)\n- 해당 시장 전용 지표가 지원되지 않아 VIX를 대리 표시합니다.",
  },
};
