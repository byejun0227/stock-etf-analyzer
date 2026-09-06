// Shared contract between the Next.js frontend and the Python /api/analyze function.
// Korean dict keys (경기동향 등) are passed through unchanged from analysis.py.

export type TimeSeriesOrText = Record<string, number | null> | string;

export interface PricePoint {
  date: string;
  close: number | null;
  ma20: number | null;
  ma60: number | null;
  ma120: number | null;
  volume: number | null;
}

export interface MarketWeights {
  경기동향: number;
  통화_재정정책: number;
  지정학_불확실성: number;
  자본시장_정책: number;
}

export interface AnalyzeRequest {
  ticker: string;
  fredApiKey?: string;
  fundamentalWeightPct: number;
  marketWeights: MarketWeights;
}

export interface ScoreDetail {
  score: number;
  detail: Record<string, string>;
}

export interface AnalyzeResponse {
  ticker: string;
  resolvedTicker: string;
  name: string;
  isEtf: boolean;
  marketType: string;
  currency: string;
  currentPrice: number | null;
  previousClose: number | null;
  dayChangePct: number | null;

  fundamentalScores: Record<string, number>;
  marketScores: Record<string, number>;
  overall: {
    overallScore: number;
    fundamentalAvg: number;
    marketAvg: number;
    grade: string;
  };

  etf?: ScoreDetail & { raw: Record<string, unknown> };
  internal?: ScoreDetail & { raw: Record<string, TimeSeriesOrText> };
  ratios?: ScoreDetail & { raw: Record<string, TimeSeriesOrText> };
  industry?: ScoreDetail & {
    sector: string;
    industryName: string;
    cycle: string;
    nature: string;
  };
  valuation?: {
    peerTickers: string[];
    table: Record<string, Record<string, number | string | null>>;
  };

  technical: {
    score: number;
    trend: string;
    rsi: number | string;
    sentiment: string;
    volumeSignal: string;
    chart: PricePoint[];
  };

  market: Record<string, Record<string, string | number>>;

  notices: {
    krLimited: boolean;
    globalLimited: boolean;
  };
}

export interface ApiErrorBody {
  error: string;
  kind?: "no_data_kr" | "no_data_generic" | "unknown";
}
