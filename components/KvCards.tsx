function iconFor(value: string): string {
  if (["개선", "상승추세", "우수", "정상"].some((k) => value.includes(k))) return "✅";
  if (["악화", "하락추세", "없음"].some((k) => value.includes(k))) return "⚠️";
  return "📊";
}

export default function KvCards({ detail }: { detail: Record<string, string> }) {
  const items = Object.entries(detail).filter(([k]) => !k.startsWith("_"));

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
      {items.map(([key, rawValue]) => {
        const value = String(rawValue);
        const label = key.replace(/_/g, " ");
        return (
          <div key={key} className="rounded-lg border border-border bg-panel px-4 py-2.5">
            <div className="text-xs text-muted mb-1">
              {iconFor(value)} {label}
            </div>
            <div className="text-sm font-semibold break-words">
              {value.length > 55 ? `${value.slice(0, 55)}…` : value}
            </div>
          </div>
        );
      })}
    </div>
  );
}
