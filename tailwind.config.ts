import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        accent: "#4e8df5",
        good: "#28a745",
        warn: "#fd7e14",
        bad: "#dc3545",
        panel: "#f8f9fa",
        border: "#e9ecef",
        muted: "#6c757d",
      },
      borderRadius: {
        card: "16px",
      },
    },
  },
  plugins: [],
};

export default config;
