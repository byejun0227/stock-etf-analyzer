"use client";

import Plot from "@/components/Plot";

export default function RadarChart({ labels, values }: { labels: string[]; values: number[] }) {
  const r = [...values, values[0]];
  const theta = [...labels, labels[0]];

  return (
    <Plot
      data={[
        {
          type: "scatterpolar",
          r,
          theta,
          fill: "toself",
          fillcolor: "rgba(78,141,245,0.18)",
          line: { color: "#4e8df5", width: 2 },
          name: "평가 점수",
        },
      ]}
      layout={{
        polar: { radialaxis: { visible: true, range: [0, 100], tickfont: { size: 10 } } },
        showlegend: false,
        height: 400,
        margin: { l: 50, r: 50, t: 20, b: 20 },
        paper_bgcolor: "rgba(0,0,0,0)",
      }}
      config={{ displayModeBar: false, responsive: true }}
      style={{ width: "100%" }}
      useResizeHandler
    />
  );
}
