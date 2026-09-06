import RadarChart from "@/components/RadarChart";
import PriceVolumeChart from "@/components/PriceVolumeChart";
import SectionHeader from "@/components/SectionHeader";
import KvCards from "@/components/KvCards";
import ValuationTable from "@/components/ValuationTable";
import MarketEnvGrid from "@/components/MarketEnvGrid";
import { scoreColor } from "@/components/ScorePill";
import { MARKET_FLAGS, type MarketKey } from "@/lib/marketLabels";
import type { AnalyzeResponse } from "@/lib/types";

interface Props {
  result: AnalyzeResponse;
  mktLabels: Record<MarketKey, string>;
  t: (key: string) => string;
}

export default function ResultView({ result, mktLabels, t }: Props) {
  const {
    name, resolvedTicker, marketType, isEtf, currency,
    currentPrice, dayChangePct,
    fundamentalScores, marketScores, overall,
    etf, internal, ratios, industry, valuation, technical, market, notices,
  } = result;

  const flag = MARKET_FLAGS[marketType] ?? "🌐";
  const radarLabels = [
    ...Object.keys(fundamentalScores),
    ...Object.keys(mktLabels).map((k) => mktLabels[k as MarketKey].split(" (")[0]),
  ];
  const radarValues = [...Object.values(fundamentalScores), ...Object.values(marketScores)];

  return (
    <div className="space-y-8">
      <div>
        <hr className="border-border mb-4" />
        <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold">{name}</h2>
            <p className="text-sm text-muted mt-1">
              <code className="bg-panel rounded px-1.5 py-0.5">{resolvedTicker}</code>{" "}
              &nbsp;|&nbsp; {flag} {marketType} &nbsp;|&nbsp; {isEtf ? t("type_etf") : t("type_stock")} &nbsp;|&nbsp;{" "}
              {currency}
            </p>
          </div>
          {currentPrice != null && (
            <div className="text-right">
              <div className="text-2xl font-bold">
                {currency === "KRW" ? currentPrice.toLocaleString(undefined, { maximumFractionDigits: 0 }) : currentPrice.toFixed(2)}{" "}
                <span className="text-sm font-normal text-muted">{currency}</span>
              </div>
              {dayChangePct != null && (
                <div className={`text-sm font-semibold ${dayChangePct >= 0 ? "text-good" : "text-bad"}`}>
                  {dayChangePct >= 0 ? "+" : ""}
                  {dayChangePct.toFixed(2)}% {t("day_change")}
                </div>
              )}
            </div>
          )}
        </div>

        {marketType === "KR" && (
          <div className="mt-3 space-y-1">
            {notices.krLimited && (
              <p className="text-sm rounded-lg bg-blue-50 text-accent px-3 py-2">ℹ️ {t("kr_limited")}</p>
            )}
            <p className="text-xs text-muted">{t("kr_market_note")}</p>
          </div>
        )}
        {marketType !== "KR" && marketType !== "US" && (
          <div className="mt-3 space-y-1">
            <p className="text-sm rounded-lg bg-blue-50 text-accent px-3 py-2">ℹ️ {t("global_limited")}</p>
            <p className="text-xs text-muted">{t("global_market_note")}</p>
          </div>
        )}
      </div>

      <div>
        <hr className="border-border mb-4" />
        <h2 className="text-xl font-bold mb-1 flex items-center gap-2">
          {t("overall_title")}
          <span
            className="text-white text-sm rounded-full px-4 py-1"
            style={{ background: scoreColor(overall.overallScore) }}
          >
            {overall.overallScore}점 &nbsp;{overall.grade}
          </span>
        </h2>
        {isEtf && <p className="text-xs text-muted mb-3">{t("etf_caption")}</p>}

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
          <Metric label={t("overall_score")} value={`${overall.overallScore}점`} />
          <Metric label={t("fundamental_avg")} value={`${Math.round(overall.fundamentalAvg)}점`} />
          <Metric label={t("market_avg")} value={`${Math.round(overall.marketAvg)}점`} />
          <Metric label={t("grade_label")} value={overall.grade} />
        </div>

        <RadarChart labels={radarLabels} values={radarValues} />
      </div>

      <div>
        <hr className="border-border mb-4" />
        {isEtf && etf ? (
          <>
            <SectionHeader num="①" title={t("section1_etf")} score={etf.score} />
            <p className="text-xs text-muted mb-3">{t("etf_caption")}</p>
            <KvCards detail={etf.detail} />
            <RawDataDetails title={t("etf_raw")} raw={etf.raw} />
          </>
        ) : (
          internal && (
            <>
              <SectionHeader num="①" title={t("section1_stock")} score={internal.score} />
              <KvCards detail={internal.detail} />
              <RawDataDetails title={t("raw_data")} raw={internal.raw} />
            </>
          )
        )}
      </div>

      {!isEtf && ratios && (
        <div>
          <hr className="border-border mb-4" />
          <SectionHeader num="②" title={t("section2")} score={ratios.score} />
          <KvCards detail={ratios.detail} />
          <RawDataDetails title={t("raw_data")} raw={ratios.raw} />

          <h3 className="text-lg font-semibold mt-6 mb-2">{t("valuation_title")}</h3>
          {valuation && Object.keys(valuation.table).length > 0 ? (
            <>
              <ValuationTable resolvedTicker={resolvedTicker} peerTickers={valuation.peerTickers} table={valuation.table} />
              <p className="text-xs text-muted mt-2">
                {valuation.peerTickers.length > 0
                  ? `${t("peers_label")} (${valuation.peerTickers.length}개): ${valuation.peerTickers.join(", ")}`
                  : t("no_peers")}
              </p>
            </>
          ) : (
            <p className="text-sm text-muted">{t("no_valuation")}</p>
          )}
        </div>
      )}

      {!isEtf && industry && (
        <div>
          <hr className="border-border mb-4" />
          <SectionHeader num="③" title={t("section3")} score={industry.score} />
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
            <Metric label={t("sector_label")} value={industry.sector} />
            <Metric label={t("industry_label")} value={industry.industryName.slice(0, 30)} />
            <Metric label={t("cycle_label")} value={industry.cycle} />
            <Metric label={t("nature_label")} value={industry.nature.slice(0, 20)} />
          </div>
          <KvCards detail={industry.detail} />
        </div>
      )}

      <div>
        <hr className="border-border mb-4" />
        <SectionHeader num="④" title={t("section4")} score={technical.score} />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
          <Metric
            label={t("trend_label")}
            value={technical.trend.includes("상승") ? t("trend_up") : t("trend_down")}
            sub={technical.trend.replace("추세 ", "").replace(/[()]/g, "")}
          />
          <Metric
            label={`${typeof technical.rsi === "number" && (technical.rsi > 70 || technical.rsi < 30) ? "🔴" : "🟢"} ${t("rsi_label")}`}
            value={String(technical.rsi)}
          />
          <Metric label={t("sentiment")} value={technical.sentiment} />
          <Metric label={t("volume_label")} value={technical.volumeSignal.includes("급증") ? t("vol_surge") : t("vol_normal")} />
        </div>
        <PriceVolumeChart data={technical.chart} volumeLabel={t("volume_chart")} />
      </div>

      <div>
        <hr className="border-border mb-4" />
        <h3 className="text-lg font-semibold mb-3">{t("market_env")}</h3>
        <MarketEnvGrid marketType={marketType} market={market} marketScores={marketScores} />
      </div>
    </div>
  );
}

function Metric({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-lg border border-border bg-panel px-4 py-3">
      <div className="text-xs text-muted mb-1">{label}</div>
      <div className="text-lg font-bold">{value}</div>
      {sub && <div className="text-xs text-muted mt-0.5">{sub}</div>}
    </div>
  );
}

function RawDataDetails({ title, raw }: { title: string; raw: Record<string, unknown> }) {
  return (
    <details className="mt-3">
      <summary className="text-sm text-muted cursor-pointer">📂 {title}</summary>
      <pre className="mt-2 text-xs bg-panel rounded-lg p-3 overflow-x-auto max-h-96">
        {JSON.stringify(raw, null, 2)}
      </pre>
    </details>
  );
}
