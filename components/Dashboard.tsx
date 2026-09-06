"use client";

import { useState, type FormEvent } from "react";

import { useLang } from "@/lib/i18n";
import { MARKET_LABELS, MARKET_LABELS_EN } from "@/lib/marketLabels";
import type { AnalyzeResponse, ApiErrorBody, MarketWeights } from "@/lib/types";
import Sidebar from "@/components/Sidebar";
import LangSwitcher from "@/components/LangSwitcher";
import ResultView from "@/components/ResultView";

interface User {
  name: string;
  email: string;
  provider: "google" | "kakao" | "admin";
  isAdmin: boolean;
}

const DEFAULT_WEIGHTS: MarketWeights = {
  경기동향: 0.25,
  통화_재정정책: 0.25,
  지정학_불확실성: 0.25,
  자본시장_정책: 0.25,
};

function normalizeWeights(w: MarketWeights): MarketWeights {
  const sum = w.경기동향 + w.통화_재정정책 + w.지정학_불확실성 + w.자본시장_정책;
  if (sum <= 0) return DEFAULT_WEIGHTS;
  return {
    경기동향: w.경기동향 / sum,
    통화_재정정책: w.통화_재정정책 / sum,
    지정학_불확실성: w.지정학_불확실성 / sum,
    자본시장_정책: w.자본시장_정책 / sum,
  };
}

export default function Dashboard({ user, defaultFredKey }: { user: User; defaultFredKey: string }) {
  const { t, lang } = useLang();
  const [ticker, setTicker] = useState("");
  const [fredApiKey, setFredApiKey] = useState(defaultFredKey);
  const [fundamentalWeightPct, setFundamentalWeightPct] = useState(60);
  const [marketWeights, setMarketWeights] = useState<MarketWeights>(DEFAULT_WEIGHTS);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<ApiErrorBody | null>(null);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);

  async function handleAnalyze(e?: FormEvent) {
    e?.preventDefault();
    if (!ticker.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ticker: ticker.trim(),
          fredApiKey,
          fundamentalWeightPct,
          marketWeights: normalizeWeights(marketWeights),
        }),
      });
      const body = await res.json();
      if (!res.ok) {
        setError(body as ApiErrorBody);
        return;
      }
      setResult(body as AnalyzeResponse);
    } catch (err) {
      setError({ error: String(err), kind: "unknown" });
    } finally {
      setLoading(false);
    }
  }

  const mktLabels = lang === "en" ? MARKET_LABELS_EN : MARKET_LABELS;

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      <div className="flex justify-end mb-2">
        <LangSwitcher />
      </div>
      <div className="flex flex-col lg:flex-row gap-6">
        <Sidebar
          user={user}
          fredApiKey={fredApiKey}
          onFredApiKeyChange={setFredApiKey}
          fundamentalWeightPct={fundamentalWeightPct}
          onFundamentalWeightPctChange={setFundamentalWeightPct}
          marketWeights={marketWeights}
          onMarketWeightsChange={setMarketWeights}
        />

        <main className="flex-1 min-w-0">
          <h1 className="text-2xl font-bold">📊 {t("app_title")}</h1>
          <p className="text-muted text-sm mt-1 mb-4">{t("app_caption")}</p>

          <form onSubmit={handleAnalyze} className="flex gap-2 mb-6">
            <input
              type="text"
              value={ticker}
              onChange={(e) => setTicker(e.target.value)}
              placeholder={t("search_placeholder")}
              className="flex-1 rounded-lg border border-border px-3 py-2 text-sm"
            />
            <button
              type="submit"
              disabled={loading}
              className="rounded-lg bg-accent text-white font-semibold px-5 text-sm disabled:opacity-60"
            >
              {loading ? t("analyzing") : t("analyze_btn")}
            </button>
          </form>

          {error && <ErrorPanel error={error} ticker={ticker} />}

          {result && <ResultView result={result} mktLabels={mktLabels} t={t} />}

          <hr className="mt-10 border-border" />
          <p className="text-xs text-muted mt-4 whitespace-pre-line">{t("footer")}</p>
        </main>
      </div>
    </div>
  );
}

function ErrorPanel({ error, ticker }: { error: ApiErrorBody; ticker: string }) {
  const { t } = useLang();
  let message: string;
  if (error.kind === "no_data_kr") {
    message = t("no_data_kr").replace("279530", ticker || "279530");
  } else if (error.kind === "no_data_generic") {
    message = t("no_data_generic");
  } else {
    message = `${t("analysis_error")}${error.error}`;
  }
  return (
    <div className="mb-6 rounded-lg bg-red-50 text-bad text-sm px-4 py-3 whitespace-pre-line">
      {message}
      <p className="text-xs mt-2 opacity-80">{t("check_ticker")}</p>
    </div>
  );
}
