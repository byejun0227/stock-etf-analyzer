import { getGoogleAuthUrl, getKakaoAuthUrl } from "@/lib/auth-urls";
import { getSession } from "@/lib/session";
import LoginView from "@/components/LoginView";
import Dashboard from "@/components/Dashboard";

export default async function Page({
  searchParams,
}: {
  searchParams: Promise<{ oauthError?: string }>;
}) {
  const [session, params] = await Promise.all([getSession(), searchParams]);

  if (!session) {
    return (
      <LoginView
        googleUrl={getGoogleAuthUrl()}
        kakaoUrl={getKakaoAuthUrl()}
        oauthError={params.oauthError === "1"}
      />
    );
  }

  return (
    <Dashboard
      user={{
        name: session.name,
        email: session.email,
        provider: session.provider,
        isAdmin: session.isAdmin,
      }}
      defaultFredKey={process.env.FRED_API_KEY?.trim() ?? ""}
    />
  );
}
