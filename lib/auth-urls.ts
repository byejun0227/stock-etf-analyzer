// Server-only helpers — builds OAuth authorization URLs from env vars.
// Ported from the original auth.py (get_google_auth_url / get_kakao_auth_url).

export function getRedirectUri(): string {
  return process.env.REDIRECT_URI?.trim() || "http://localhost:3000";
}

function callbackUrl(): string {
  return `${getRedirectUri().replace(/\/$/, "")}/api/auth/callback`;
}

export function getGoogleAuthUrl(): string {
  const clientId = process.env.GOOGLE_CLIENT_ID?.trim();
  if (!clientId) return "";
  const params = new URLSearchParams({
    client_id: clientId,
    redirect_uri: callbackUrl(),
    response_type: "code",
    scope: "openid email profile",
    access_type: "offline",
    state: "google",
    prompt: "select_account",
  });
  return `https://accounts.google.com/o/oauth2/v2/auth?${params.toString()}`;
}

export function getKakaoAuthUrl(): string {
  const appKey = process.env.KAKAO_REST_API_KEY?.trim();
  if (!appKey) return "";
  const params = new URLSearchParams({
    client_id: appKey,
    redirect_uri: callbackUrl(),
    response_type: "code",
    state: "kakao",
  });
  return `https://kauth.kakao.com/oauth/authorize?${params.toString()}`;
}

export { callbackUrl as getOAuthCallbackUrl };
