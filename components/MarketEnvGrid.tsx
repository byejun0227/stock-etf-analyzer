"use client";

import { useState } from "react";

import { useLang } from "@/lib/i18n";
import { MARKET_INDEX_DESC, MARKET_KEYS, MARKET_LABELS, MARKET_LABELS_EN, type MarketKey } from "@/lib/marketLabels";
import { scoreColor } from "@/components/ScorePill";

interface Props {
  marketType: string;
  market: Record<string, Record<string, string | number>>;
  marketScores: Record<string, number>;
}

export default function MarketEnvGrid({ marketType, market, marketScores }: Props) {
  const { lang } = useLang();
  const labels = lang === "en" ? MARKET_LABELS_EN : MARKET_LABELS;
  const descMap = MARKET_INDEX_DESC[marketType] ?? MARKET_INDEX_DESC.DEFAULT;
  const [openKey, setOpenKey] = useState<MarketKey | null>(null);

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {MARKET_KEYS.map((key) => {
          const item = market[key] ?? {};
          const verdict = String(item["판정"] ?? item["안내"] ?? item["오류"] ?? "N/A");
          const score = marketScores[key] ?? 50;
          const shortLabel = labels[key].split(" (")[0];
          return (
            <div key={key} className="rounded-lg border border-border bg-panel p-3 text-center">
              <div className="text-xs text-muted mb-1">{shortLabel}</div>
              <div className="text-sm font-semibold mb-1.5 truncate" title={verdict}>
                {verdict.length > 22 ? `${verdict.slice(0, 22)}…` : verdict}
              </div>
              <span
                className="text-white text-xs rounded-full px-2.5 py-0.5"
                style={{ background: scoreColor(score) }}
              >
                {score}점
              </span>
            </div>
          );
        })}
      </div>

      <div className="space-y-2">
        {MARKET_KEYS.map((key) => {
          const isOpen = openKey === key;
          return (
            <div key={key} className="rounded-lg border border-border">
              <button
                type="button"
                onClick={() => setOpenKey(isOpen ? null : key)}
                className="w-full text-left px-4 py-2.5 text-sm font-medium flex items-center justify-between"
              >
                <span>🔍 {labels[key]}</span>
                <span className="text-muted">{isOpen ? "▾" : "▸"}</span>
              </button>
              {isOpen && (
                <div className="px-4 pb-4 text-sm space-y-3">
                  <p className="whitespace-pre-line text-muted">{descMap[key]}</p>
                  <hr className="border-border" />
                  <MarketDetail data={market[key] ?? {}} />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function MarketDetail({ data }: { data: Record<string, string | number> }) {
  return (
    <div className="space-y-1.5">
      {Object.entries(data).map(([key, val]) => {
        if (key === "판정") return null;
        if (key === "참고") {
          return (
            <p key={key} className="text-xs text-accent">
              ℹ️ {val}
            </p>
          );
        }
        if (key === "오류") {
          return (
            <p key={key} className="text-xs text-bad">
              ⚠️ 데이터 조회 실패: {val}
            </p>
          );
        }
        if (key === "안내") {
          return (
            <p key={key} className="text-xs text-warn">
              {val}
            </p>
          );
        }
        return (
          <div key={key} className="grid grid-cols-5 gap-2 text-xs">
            <div className="col-span-2 font-medium">{key}</div>
            <div className="col-span-3">{String(val)}</div>
          </div>
        );
      })}
    </div>
  );
}
