"use client";

import { useLang } from "@/lib/i18n";

export default function LangSwitcher() {
  const { lang, setLang } = useLang();

  return (
    <div className="inline-flex rounded-full border border-border overflow-hidden text-sm">
      <button
        type="button"
        onClick={() => setLang("ko")}
        className={`px-3 py-1 ${lang === "ko" ? "bg-accent text-white" : "bg-white text-muted"}`}
      >
        🇰🇷 한국어
      </button>
      <button
        type="button"
        onClick={() => setLang("en")}
        className={`px-3 py-1 ${lang === "en" ? "bg-accent text-white" : "bg-white text-muted"}`}
      >
        🇺🇸 English
      </button>
    </div>
  );
}
