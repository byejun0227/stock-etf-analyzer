import ScorePill from "@/components/ScorePill";

export default function SectionHeader({ num, title, score }: { num: string; title: string; score: number }) {
  return (
    <h3 className="text-lg font-semibold mb-1.5 flex items-center gap-2">
      <span>
        {num} {title}
      </span>
      <ScorePill score={score} />
    </h3>
  );
}
