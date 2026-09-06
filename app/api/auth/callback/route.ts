import { NextRequest, NextResponse } from "next/server";

import { getOAuthCallbackUrl } from "@/lib/auth-urls";
import { createSessionToken, SESSION_COOKIE, SESSION_COOKIE_OPTIONS, sessionConfigured, type SessionUser } from "@/lib/session";

// Ported from the original auth.py exchange_google_code / exchange_kakao_code.

async function exchangeGoogleCode(code: string): Promise<SessionUser | null> {
  const clientId = process.env.GOOGLE_CLIENT_ID?.trim();
  const clientSecret = process.env.GOOGLE_CLIENT_SECRET?.trim();
  if (!clientId || !clientSecret) return null;
  try {
    const tokenRes = await fetch("https://oauth2.googleapis.com/token", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        client_id: clientId,
        client_secret: clientSecret,
        code,
        grant_type: "authorization_code",
        redirect_uri: getOAuthCallbackUrl(),
      }),
    });
    const token = await tokenRes.json();
    if (!token.access_token) return null;
    const infoRes = await fetch("https://www.googleapis.com/oauth2/v3/userinfo", {
      headers: { Authorization: `Bearer ${token.access_token}` },
    });
    const info = await infoRes.json();
    return {
      provider: "google",
      email: info.email ?? "",
      name: info.name ?? "",
      isAdmin: false,
    };
  } catch {
    return null;
  }
}

async function exchangeKakaoCode(code: string): Promise<SessionUser | null> {
  const appKey = process.env.KAKAO_REST_API_KEY?.trim();
  if (!appKey) return null;
  try {
    const tokenRes = await fetch("https://kauth.kakao.com/oauth/token", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        grant_type: "authorization_code",
        client_id: appKey,
        redirect_uri: getOAuthCallbackUrl(),
        code,
      }),
    });
    const token = await tokenRes.json();
    if (!token.access_token) return null;
    const userRes = await fetch("https://kapi.kakao.com/v2/user/me", {
      headers: { Authorization: `Bearer ${token.access_token}` },
    });
    const user = await userRes.json();
    const account = user.kakao_account ?? {};
    const profile = account.profile ?? {};
    return {
      provider: "kakao",
      email: account.email ?? "",
      name: profile.nickname ?? "",
      isAdmin: false,
    };
  } catch {
    return null;
  }
}

export async function GET(request: NextRequest) {
  const url = new URL(request.url);
  const code = url.searchParams.get("code") ?? "";
  const state = url.searchParams.get("state") ?? "";
  const redirectTo = new URL("/", request.url);

  if (!sessionConfigured()) {
    redirectTo.searchParams.set("oauthError", "1");
    return NextResponse.redirect(redirectTo);
  }

  let user: SessionUser | null = null;
  if (code && state === "google") user = await exchangeGoogleCode(code);
  else if (code && state === "kakao") user = await exchangeKakaoCode(code);

  if (!user) {
    redirectTo.searchParams.set("oauthError", "1");
    return NextResponse.redirect(redirectTo);
  }

  const token = await createSessionToken(user);
  const response = NextResponse.redirect(redirectTo);
  response.cookies.set(SESSION_COOKIE, token, SESSION_COOKIE_OPTIONS);
  return response;
}
