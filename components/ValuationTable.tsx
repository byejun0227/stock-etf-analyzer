import { VALUATION_METRIC_INFO, VALUATION_METRIC_ORDER } from "@/lib/valuationInfo";

interface Props {
  resolvedTicker: string;
  peerTickers: string[];
  table: Record<string, Record<string, number | string | null>>;
}

function fmt(value: number | string | null | undefined): string {
  if (value === null || value === undefined) return "N/A";
  if (typeof value === "number") return value.toFixed(2);
  return value;
}

function evalClass(value: string | undefined): string {
  if (!value) return "";
  if (value.includes("✅")) return "bg-green-100 text-green-800 font-semibold";
  if (value.includes("⚠️")) return "bg-red-100 text-red-800 font-semibold";
  if (value.includes("➖")) return "bg-gray-100 text-gray-600";
  return "";
}

export default function ValuationTable({ resolvedTicker, peerTickers, table }: Props) {
  const rows = VALUATION_METRIC_ORDER.filter((k) => k in table);
  const columns = [resolvedTicker, "업계평균", ...peerTickers];

  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="min-w-full text-sm">
        <thead className="bg-panel">
          <tr>
            <th className="text-left px-3 py-2 font-medium">지표</th>
            <th className="text-left px-3 py-2 font-medium">설명</th>
            {columns.map((c) => (
              <th key={c} className="text-right px-3 py-2 font-medium">
                {c}
              </th>
            ))}
            <th className="text-center px-3 py-2 font-medium">평가</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((key) => {
            const row = table[key];
            const info = VALUATION_METRIC_INFO[key];
            return (
              <tr key={key} className="border-t border-border">
                <td className="px-3 py-2 font-semibold">{key}</td>
                <td className="px-3 py-2 text-muted text-xs">{info?.desc}</td>
                {columns.map((c) => (
                  <td key={c} className="px-3 py-2 text-right tabular-nums">
                    {fmt(row?.[c])}
                  </td>
                ))}
                <td className={`px-3 py-2 text-center ${evalClass(row?.["평가"] as string)}`}>
                  {row?.["평가"] ?? "N/A"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
