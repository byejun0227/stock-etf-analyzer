export function scoreColor(score: number): string {
  if (score >= 65) return "#28a745";
  if (score >= 50) return "#fd7e14";
  return "#dc3545";
}

export default function ScorePill({ score, suffix = "점" }: { score: number; suffix?: string }) {
  return (
    <span
      className="text-white text-xs font-bold rounded-full px-3 py-0.5"
      style={{ background: scoreColor(score) }}
    >
      {score}
      {suffix}
    </span>
  );
}
