"use client";

import Plot from "@/components/Plot";
import type { PricePoint } from "@/lib/types";

export default function PriceVolumeChart({
  data,
  volumeLabel,
}: {
  data: PricePoint[];
  volumeLabel: string;
}) {
  const dates = data.map((d) => d.date);
  const close = data.map((d) => d.close);
  const ma20 = data.map((d) => d.ma20);
  const ma60 = data.map((d) => d.ma60);
  const ma120 = data.map((d) => d.ma120);
  const volume = data.map((d) => d.volume);

  return (
    <Plot
      data={[
        { type: "scatter", mode: "lines", x: dates, y: close, name: "종가", line: { color: "#4e8df5", width: 2 }, xaxis: "x", yaxis: "y" },
        { type: "scatter", mode: "lines", x: dates, y: ma20, name: "MA20", line: { color: "#fd7e14", width: 1, dash: "dot" }, opacity: 0.85, xaxis: "x", yaxis: "y" },
        { type: "scatter", mode: "lines", x: dates, y: ma60, name: "MA60", line: { color: "#28a745", width: 1, dash: "dot" }, opacity: 0.85, xaxis: "x", yaxis: "y" },
        { type: "scatter", mode: "lines", x: dates, y: ma120, name: "MA120", line: { color: "#dc3545", width: 1.5 }, xaxis: "x", yaxis: "y" },
        { type: "bar", x: dates, y: volume, name: volumeLabel, marker: { color: "#adb5bd" }, opacity: 0.6, xaxis: "x2", yaxis: "y2" },
      ]}
      layout={{
        height: 500,
        margin: { l: 45, r: 20, t: 10, b: 30 },
        legend: { orientation: "h", y: 1.02, x: 1, xanchor: "right", yanchor: "bottom" },
        hovermode: "x unified",
        paper_bgcolor: "rgba(0,0,0,0)",
        plot_bgcolor: "rgba(248,249,250,1)",
        xaxis: { anchor: "y", matches: "x2", rangeslider: { visible: false } },
        xaxis2: { anchor: "y2" },
        yaxis: { domain: [0.3, 1], gridcolor: "#e9ecef" },
        yaxis2: { domain: [0, 0.22], gridcolor: "#e9ecef" },
      }}
      config={{ displayModeBar: false, responsive: true }}
      style={{ width: "100%" }}
      useResizeHandler
    />
  );
}
