"use client";

import dynamic from "next/dynamic";
import type { CSSProperties, ReactElement } from "react";

// Plotly touches `window`/`document` at import time, so it must never be
// pulled into the server render — load it client-only. Cast to a loose
// component type since @types/react-plotly.js pulls in the full Plotly.js
// type surface (not installed here) for its `data`/`layout` props.
type PlotComponent = (props: {
  data: unknown[];
  layout?: Record<string, unknown>;
  config?: Record<string, unknown>;
  style?: CSSProperties;
  useResizeHandler?: boolean;
}) => ReactElement;

const Plot = dynamic(() => import("react-plotly.js"), { ssr: false }) as unknown as PlotComponent;

export default Plot;
