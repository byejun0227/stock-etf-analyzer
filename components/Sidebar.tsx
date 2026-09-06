"use client";

import { useLang } from "@/lib/i18n";
import type { MarketWeights } from "@/lib/types";

interface User {
  name: string;
  email: string;
  provider: "google" | "kakao" | "admin";
  isAdmin: boolean;
}

interface Props {
  user: User;
  fredApiKey: string;
  onFredApiKeyChange: (value: string) => void;
  fundamentalWeightPct: number;
  onFundamentalWeightPctChange: (value: number) => void;
  marketWeights: MarketWeights;
  onMarketWeightsChange: (value: MarketWeights) => void;
}

const PROVIDER_ICON: Record<User["provider"], string> = {
  google: "🔵",
  kakao: "💛",
  admin: "🔑",
};

export default function Sidebar({
  user,
  fredApiKey,
  onFredApiKeyChange,
  fundamentalWeightPct,
  onFundamentalWeightPctChange,
  marketWeights,
  onMarketWeightsChange,
}: Props) {
  const { t } = useLang();

  async function handleLogout() {
    await fetch("/api/auth/logout", { method: "POST" });
    window.location.href = "/";
  }

  function updateWeight(key: keyof MarketWeights, raw: number) {
    const next = { ...marketWeights, [key]: raw };
    onMarketWeightsChange(next);
  }

  const weightSum =
    marketWeights.경기동향 + marketWeights.통화_재정정책 + marketWeights.지정학_불확실성 + marketWeights.자본시장_정책;

  return (
    <aside className="w-full lg:w-72 shrink-0 space-y-4">
      <div className="rounded-card border border-border bg-panel p-4">
        <div className="font-semibold">
          {PROVIDER_ICON[user.provider]} {user.name}
        </div>
        {user.email && <div className="text-xs text-muted mt-0.5">{user.email}</div>}
        <button
          type="button"
          onClick={handleLogout}
          className="mt-3 w-full rounded-lg border border-border bg-white py-1.5 text-sm hover:bg-panel"
        >
          {t("logout_btn")}
        </button>
      </div>

      {user.isAdmin ? (
        <div className="rounded-card border border-border bg-panel p-4 space-y-4">
          <div className="text-good text-sm font-medium">{t("admin_mode")}</div>

          <div>
            <label className="text-xs font-medium text-muted">{t("fred_api_key")}</label>
            <input
              type="password"
              value={fredApiKey}
              onChange={(e) => onFredApiKeyChange(e.target.value)}
              className="mt-1 w-full rounded-lg border border-border px-2 py-1.5 text-sm"
            />
            <p className="text-xs text-muted mt-1">{t("fred_caption")}</p>
          </div>

          <hr className="border-border" />

          <div>
            <div className="text-sm font-semibold mb-1">{t("score_weights")}</div>
            <label className="text-xs text-muted">{t("fund_vs_market")}</label>
            <input
              type="range"
              min={0}
              max={100}
              step={5}
              value={fundamentalWeightPct}
              onChange={(e) => onFundamentalWeightPctChange(Number(e.target.value))}
              className="w-full"
            />
            <p className="text-xs text-muted">
              {t("fund_pct")} {fundamentalWeightPct}% : {t("market_pct")} {100 - fundamentalWeightPct}%
            </p>
          </div>

          <details>
            <summary className="text-xs font-medium text-muted cursor-pointer">{t("market_detail_weights")}</summary>
            <div className="mt-2 space-y-2">
              <p className="text-xs text-muted">{t("market_weight_auto")}</p>
              <WeightSlider label="경기동향" value={marketWeights.경기동향} onChange={(v) => updateWeight("경기동향", v)} />
              <WeightSlider
                label="통화/재정정책"
                value={marketWeights.통화_재정정책}
                onChange={(v) => updateWeight("통화_재정정책", v)}
              />
              <WeightSlider
                label="지정학적 불확실성"
                value={marketWeights.지정학_불확실성}
                onChange={(v) => updateWeight("지정학_불확실성", v)}
              />
              <WeightSlider
                label="자본시장 정책"
                value={marketWeights.자본시장_정책}
                onChange={(v) => updateWeight("자본시장_정책", v)}
              />
              <p className="text-xs text-muted">sum: {weightSum.toFixed(2)} (자동 정규화됨)</p>
            </div>
          </details>
        </div>
      ) : (
        <div className="rounded-card border border-border bg-panel p-4 text-sm text-muted">{t("fred_caption")}</div>
      )}

      <div className="rounded-card border border-border bg-panel p-4 text-xs text-muted whitespace-pre-line">
        {t("input_guide")}
      </div>
    </aside>
  );
}

function WeightSlider({ label, value, onChange }: { label: string; value: number; onChange: (v: number) => void }) {
  const pct = Math.round(value * 100);
  return (
    <div>
      <label className="text-xs">
        {label} ({pct})
      </label>
      <input
        type="range"
        min={0}
        max={100}
        value={pct}
        onChange={(e) => onChange(Number(e.target.value) / 100)}
        className="w-full"
      />
    </div>
  );
}
