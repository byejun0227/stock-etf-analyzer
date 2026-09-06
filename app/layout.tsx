import type { Metadata } from "next";
import type { ReactNode } from "react";

import { LangProvider } from "@/lib/i18n";
import "./globals.css";

export const metadata: Metadata = {
  title: "Global Stock/ETF Analyzer",
  description: "한국·미국·글로벌 주식/ETF 펀더멘탈 & 시장환경 분석기",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ko">
      <body>
        <LangProvider>{children}</LangProvider>
      </body>
    </html>
  );
}
