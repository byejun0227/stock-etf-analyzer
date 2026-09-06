"use client";

import { useState, type FormEvent } from "react";

import { useLang } from "@/lib/i18n";
import LangSwitcher from "@/components/LangSwitcher";

interface Props {
  googleUrl: string;
  kakaoUrl: string;
  oauthError: boolean;
}

export default function LoginView({ googleUrl, kakaoUrl, oauthError }: Props) {
  const { t } = useLang();
  const [showAdmin, setShowAdmin] = useState(false);
  const [id, setId] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function handleAdminLogin(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(false);
    try {
      const res = await fetch("/api/auth/admin", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id, password }),
      });
      if (!res.ok) {
        setError(true);
        return;
      }
      window.location.href = "/";
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen flex flex-col">
      <div className="flex justify-end p-4">
        <LangSwitcher />
      </div>
      <div className="flex-1 flex items-start justify-center px-4">
        <div className="w-full max-w-md mt-10 rounded-card border border-border bg-white p-8 shadow-sm">
          <h1 className="text-2xl font-bold mb-1">📊 {t("login_title")}</h1>
          <p className="text-muted text-sm mb-6">{t("login_subtitle")}</p>

          {oauthError && (
            <div className="mb-4 rounded-lg bg-red-50 text-bad text-sm px-4 py-3">{t("oauth_error")}</div>
          )}

          <AuthButton href={googleUrl} label={t("google_login")} help={t("oauth_not_configured")} />
          <div className="h-2" />
          <AuthButton href={kakaoUrl} label={t("kakao_login")} help={t("oauth_not_configured")} />

          <hr className="my-5 border-border" />

          <button
            type="button"
            className="text-sm text-muted hover:text-accent"
            onClick={() => setShowAdmin((v) => !v)}
          >
            {showAdmin ? "▾" : "▸"} {t("admin_login")}
          </button>

          {showAdmin && (
            <form onSubmit={handleAdminLogin} className="mt-3 space-y-2">
              <input
                type="text"
                placeholder={t("username")}
                value={id}
                onChange={(e) => setId(e.target.value)}
                className="w-full rounded-lg border border-border px-3 py-2 text-sm"
              />
              <input
                type="password"
                placeholder={t("password")}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-lg border border-border px-3 py-2 text-sm"
              />
              {error && <p className="text-bad text-sm">{t("login_error")}</p>}
              <button
                type="submit"
                disabled={submitting}
                className="w-full rounded-lg bg-accent text-white font-semibold py-2 text-sm disabled:opacity-60"
              >
                {t("login_btn")}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}

function AuthButton({ href, label, help }: { href: string; label: string; help: string }) {
  if (!href) {
    return (
      <button
        type="button"
        disabled
        title={help}
        className="w-full rounded-lg border border-border bg-panel text-muted font-medium py-2.5 text-sm cursor-not-allowed"
      >
        {label}
      </button>
    );
  }
  return (
    <a
      href={href}
      className="block w-full text-center rounded-lg border border-border bg-white hover:bg-panel font-medium py-2.5 text-sm transition-colors"
    >
      {label}
    </a>
  );
}
