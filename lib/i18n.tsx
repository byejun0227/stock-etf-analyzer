"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

export type Lang = "ko" | "en";

const TRANSLATIONS: Record<Lang, Record<string, string>> = {
  ko: {
    app_title: "한국·미국·글로벌 주식/ETF 펀더멘탈 & 시장환경 분석기",
    app_caption: "과거 5년 데이터를 기반으로 펀더멘탈 4개 항목 + 시장환경 4개 항목을 평가하는 프로토타입입니다.",
    search_placeholder: "예: AAPL, SPY, 005930, 삼성전자, 엔비디아, 도요타, 텐센트, TSMC, ASML",
    analyze_btn: "🔍 분석",
    analyzing: "데이터 수집 및 분석 중...",
    language: "Language",

    login_title: "로그인",
    login_subtitle: "서비스를 이용하려면 로그인하세요.",
    google_login: "🔵  Google로 로그인",
    kakao_login: "💛  카카오로 로그인",
    admin_login: "관리자 로그인",
    username: "아이디",
    password: "비밀번호",
    login_btn: "로그인",
    login_error: "아이디 또는 비밀번호가 올바르지 않습니다.",
    oauth_error: "로그인 처리 중 오류가 발생했습니다. 다시 시도해주세요.",
    logout_btn: "로그아웃",
    welcome: "환영합니다",
    logged_in_as: "로그인: ",
    oauth_not_configured: "OAuth 미설정 (환경변수에 키 추가 필요)",
    email: "이메일",
    name: "이름",
    confirm_password: "비밀번호 확인",
    signup_btn: "회원가입",
    login_with_email: "이메일로 로그인",
    no_account: "계정이 없으신가요?",
    have_account: "이미 계정이 있으신가요?",
    go_signup: "회원가입",
    go_login: "로그인",
    signup_error_invalid_email: "올바른 이메일 형식이 아닙니다.",
    signup_error_weak_password: "비밀번호는 8자 이상이어야 합니다.",
    signup_error_name_required: "이름을 입력해주세요.",
    signup_error_email_taken: "이미 가입된 이메일입니다.",
    signup_error_password_mismatch: "비밀번호가 일치하지 않습니다.",
    signup_error_generic: "회원가입 중 오류가 발생했습니다.",
    login_error_generic: "이메일 또는 비밀번호가 올바르지 않습니다.",

    settings_title: "⚙️ 설정",
    settings_locked: "🔒 설정",
    admin_mode: "✅ 관리자 모드",
    fred_api_key: "FRED API 키",
    fred_help: "https://fred.stlouisfed.org/docs/api/api_key.html 에서 무료 발급",
    fred_caption: "시장환경 분석(경기동향/통화정책/지정학) 계산에 필요합니다.",
    score_weights: "종합점수 가중치",
    fund_vs_market: "펀더멘탈 vs 시장환경 비중",
    fund_vs_market_help: "슬라이더 값이 펀더멘탈 비중(%)입니다. 나머지는 시장환경 비중.",
    market_detail_weights: "시장환경 세부 가중치 (선택)",
    market_weight_auto: "4개 항목의 상대적 중요도 (자동 정규화)",
    fund_pct: "펀더멘탈",
    market_pct: "시장환경",
    input_guide:
      "종목 입력 방법\n- 한글: 삼성전자, 도요타, 텐센트, ASML\n- 코드: 005930, 7203.T, 0700.HK, 2330.TW\n- 미국 ETF: KODEX 200, SPY, QQQ\n- 미국 주식: AAPL, NVDA, TSLA\n- 일본(.T) / 중국(.SS/.SZ) / 홍콩(.HK)\n- 대만(.TW) / 인도(.NS) / 유럽(.DE/.L/.PA/.AS/.SW)\n- ⚠️ ETN·신규상장 종목은 미지원일 수 있음",

    overall_title: "🏆 종합 평가",
    overall_score: "🏆 종합 점수",
    fundamental_avg: "📋 펀더멘탈 평균",
    market_avg: "🌍 시장환경 평균",
    grade_label: "🎯 등급",
    section1_stock: "① 기업 내부요인 평가",
    section1_etf: "① ETF 구성 분석",
    section2: "② 재무지표 평가",
    section3: "③ 산업동향 평가",
    section4: "④ 기술적 분석",
    market_env: "🌍 시장환경 분석",
    raw_data: "📂 추이 원시 데이터 (연도별)",
    etf_raw: "ETF 원시 데이터",
    valuation_title: "📊 밸류에이션 멀티플 비교 — PER / PBR / PSR / EPS / ROE",
    valuation_guide: "지표 해석 가이드",
    no_valuation: "밸류에이션 지표 데이터를 가져오지 못했습니다.",
    no_peers: "동종업계 비교 대상을 찾지 못했습니다. 현재 미국 대형주 업종만 지원됩니다.",
    peers_label: "비교 대상",

    trend_label: "📈 추세",
    rsi_label: "RSI(14)",
    sentiment: "🧠 투자심리",
    volume_label: "📦 거래량",
    sector_label: "🏭 섹터",
    industry_label: "🔬 세부산업",
    cycle_label: "📈 산업주기",
    nature_label: "🔄 산업특성",
    volume_chart: "거래량",
    day_change: "전일 대비",
    type_etf: "ETF",
    type_stock: "개별주식",
    trend_up: "상승",
    trend_down: "하락",
    vol_surge: "급증",
    vol_normal: "보통",

    no_data_kr:
      "데이터를 가져오지 못했습니다.\n\n한국 상품 검색 안내:\n- 6자리 종목코드로 입력 (예: 279530)\n- ETN(상장지수채권)은 yfinance 미지원\n- 레버리지/인버스 ETF는 정확한 상품명으로 입력",
    no_data_generic: "가격 데이터를 가져오지 못했습니다. 종목코드/티커를 확인해주세요.",
    analysis_error: "분석 중 오류가 발생했습니다: ",
    check_ticker: "티커가 올바른지, 또는 yfinance가 해당 종목 데이터를 제공하는지 확인해주세요.",
    error_detail: "🔍 상세 오류 정보 (디버깅용)",
    kr_limited: "ℹ️ 한국 개별주식은 yfinance 재무제표 범위가 제한적입니다. ①② 일부 항목은 DART 원문을 확인하세요.",
    kr_market_note: "🇰🇷 시장환경 분석은 KOSPI·BOK 기준금리·VKOSPI 등 한국 지표를 사용합니다.",
    global_limited: "ℹ️ 해외 종목은 yfinance 제공 데이터에 따라 일부 항목이 N/A일 수 있습니다.",
    global_market_note: "🌐 시장환경은 미국 지표를 대리 표시합니다 (해당국 전용 지표 미지원).",
    etf_caption: "⚠️ ETF는 재무제표 대신 운용보수·순자산·집중도 기반 ETF구성 점수를 사용합니다.",

    footer:
      "⚠️ 이 도구는 프로토타입이며 투자 조언이 아닙니다. 점수/등급은 규칙 기반 근사치로, 재무데이터는 yfinance 기준이라 실제 공시와 차이가 있을 수 있으니 투자 판단 시 원문 공시를 반드시 확인하세요.",
  },
  en: {
    app_title: "Korea · US · Global Stock/ETF Fundamental & Market Analysis",
    app_caption: "A prototype evaluating 4 fundamental + 4 market environment factors based on 5-year historical data.",
    search_placeholder: "e.g.: AAPL, SPY, Samsung, Nvidia, Toyota, Tencent, TSMC, ASML, 7203.T",
    analyze_btn: "🔍 Analyze",
    analyzing: "Fetching data and analyzing...",
    language: "Language",

    login_title: "Login",
    login_subtitle: "Please log in to use the service.",
    google_login: "🔵  Sign in with Google",
    kakao_login: "💛  Sign in with Kakao",
    admin_login: "Admin Login",
    username: "Username",
    password: "Password",
    login_btn: "Login",
    login_error: "Incorrect username or password.",
    oauth_error: "An error occurred during login. Please try again.",
    logout_btn: "Logout",
    welcome: "Welcome",
    logged_in_as: "Logged in as: ",
    oauth_not_configured: "OAuth not configured (add keys to environment variables)",
    email: "Email",
    name: "Name",
    confirm_password: "Confirm Password",
    signup_btn: "Sign Up",
    login_with_email: "Sign in with Email",
    no_account: "Don't have an account?",
    have_account: "Already have an account?",
    go_signup: "Sign up",
    go_login: "Log in",
    signup_error_invalid_email: "Please enter a valid email address.",
    signup_error_weak_password: "Password must be at least 8 characters.",
    signup_error_name_required: "Please enter your name.",
    signup_error_email_taken: "This email is already registered.",
    signup_error_password_mismatch: "Passwords do not match.",
    signup_error_generic: "An error occurred while signing up.",
    login_error_generic: "Incorrect email or password.",

    settings_title: "⚙️ Settings",
    settings_locked: "🔒 Settings",
    admin_mode: "✅ Admin Mode",
    fred_api_key: "FRED API Key",
    fred_help: "Get a free key at https://fred.stlouisfed.org/docs/api/api_key.html",
    fred_caption: "Required for market environment analysis.",
    score_weights: "Score Weights",
    fund_vs_market: "Fundamental vs Market Weight",
    fund_vs_market_help: "Slider value is the fundamental weight (%). Remainder is market weight.",
    market_detail_weights: "Market Sub-weights (optional)",
    market_weight_auto: "Relative importance of 4 factors (auto-normalized)",
    fund_pct: "Fundamental",
    market_pct: "Market",
    input_guide:
      "How to enter tickers\n- Korean name: 삼성전자, 도요타, 텐센트\n- Direct code: 005930, 7203.T, 0700.HK\n- US ETFs: SPY, QQQ, KODEX 200\n- US stocks: AAPL, NVDA, TSLA\n- Japan(.T) / China(.SS/.SZ) / HK(.HK)\n- Taiwan(.TW) / India(.NS) / Europe(.DE/.L/.PA/.AS/.SW)\n- ⚠️ ETNs and newly listed stocks may be unsupported",

    overall_title: "🏆 Overall Rating",
    overall_score: "🏆 Overall Score",
    fundamental_avg: "📋 Fundamental Avg",
    market_avg: "🌍 Market Env Avg",
    grade_label: "🎯 Grade",
    section1_stock: "① Internal Factors",
    section1_etf: "① ETF Composition",
    section2: "② Financial Ratios",
    section3: "③ Industry Trends",
    section4: "④ Technical Analysis",
    market_env: "🌍 Market Environment",
    raw_data: "📂 Raw Data (Annual)",
    etf_raw: "ETF Raw Data",
    valuation_title: "📊 Valuation Multiples — PER / PBR / PSR / EPS / ROE",
    valuation_guide: "Metric Interpretation Guide",
    no_valuation: "Could not retrieve valuation metrics.",
    no_peers: "No peer companies found. Only US large-cap sectors are currently supported.",
    peers_label: "Peers",

    trend_label: "📈 Trend",
    rsi_label: "RSI(14)",
    sentiment: "🧠 Sentiment",
    volume_label: "📦 Volume",
    sector_label: "🏭 Sector",
    industry_label: "🔬 Industry",
    cycle_label: "📈 Industry Cycle",
    nature_label: "🔄 Industry Type",
    volume_chart: "Volume",
    day_change: "vs prev close",
    type_etf: "ETF",
    type_stock: "Stock",
    trend_up: "Rising",
    trend_down: "Falling",
    vol_surge: "Surge",
    vol_normal: "Normal",

    no_data_kr:
      "Could not fetch data.\n\nKorean stock tips:\n- Use 6-digit code (e.g. 279530)\n- ETNs are not supported by yfinance\n- Use exact product names for leveraged/inverse ETFs",
    no_data_generic: "Could not fetch price data. Please verify the ticker/code.",
    analysis_error: "An error occurred during analysis: ",
    check_ticker: "Please verify the ticker or check if yfinance provides data for this symbol.",
    error_detail: "🔍 Error Details (debugging)",
    kr_limited: "ℹ️ Financial data for Korean stocks is limited via yfinance. Check DART for official filings.",
    kr_market_note: "🇰🇷 Market analysis uses Korean indicators (KOSPI, BOK rate, VKOSPI).",
    global_limited: "ℹ️ Some fields may be N/A for foreign stocks depending on yfinance coverage.",
    global_market_note: "🌐 Market environment uses US indicators as proxy (country-specific indicators not yet supported).",
    etf_caption: "⚠️ ETF uses expense ratio, AUM, and concentration score instead of financial statements.",

    footer:
      "⚠️ This tool is a prototype and not investment advice. Scores/grades are rule-based approximations. Financial data is sourced from yfinance and may differ from official filings.",
  },
};

function translate(key: string, lang: Lang): string {
  return TRANSLATIONS[lang]?.[key] ?? TRANSLATIONS.ko[key] ?? key;
}

interface LangContextValue {
  lang: Lang;
  setLang: (lang: Lang) => void;
  t: (key: string) => string;
}

const LangContext = createContext<LangContextValue | null>(null);

const STORAGE_KEY = "stock-analyzer-lang";

export function LangProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>("ko");

  useEffect(() => {
    try {
      const saved = window.localStorage.getItem(STORAGE_KEY);
      if (saved === "ko" || saved === "en") setLangState(saved);
    } catch {
      // localStorage unavailable — keep default
    }
  }, []);

  const setLang = useCallback((next: Lang) => {
    setLangState(next);
    try {
      window.localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // ignore
    }
  }, []);

  const t = useCallback((key: string) => translate(key, lang), [lang]);

  const value = useMemo(() => ({ lang, setLang, t }), [lang, setLang, t]);

  return <LangContext.Provider value={value}>{children}</LangContext.Provider>;
}

export function useLang(): LangContextValue {
  const ctx = useContext(LangContext);
  if (!ctx) throw new Error("useLang must be used within LangProvider");
  return ctx;
}
