"""
auth.py — 인증 모듈 (Google OAuth / Kakao OAuth / 관리자 로그인)

필요한 secrets.toml 키:
    GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
    KAKAO_REST_API_KEY
    REDIRECT_URI   (예: https://your-app.railway.app   로컬: http://localhost:8501)
    ADMIN_ID, ADMIN_PW
"""

import os
import urllib.parse

import requests as _requests


# =========================================================
# 공통 유틸
# =========================================================
def _load_secret(key: str, default: str = "") -> str:
    """st.secrets → os.environ → default 순으로 조회."""
    try:
        import streamlit as st
        v = st.secrets.get(key)
        if v is not None:
            return str(v).strip()
    except Exception:
        pass
    v = os.environ.get(key, "")
    return v.strip() if v else default


def get_redirect_uri() -> str:
    return _load_secret("REDIRECT_URI", "http://localhost:8501")


# =========================================================
# Google OAuth
# =========================================================
def get_google_auth_url() -> str:
    """Google OAuth 2.0 인증 URL 생성. GOOGLE_CLIENT_ID 미설정 시 빈 문자열."""
    client_id = _load_secret("GOOGLE_CLIENT_ID")
    if not client_id:
        return ""
    params = {
        "client_id": client_id,
        "redirect_uri": get_redirect_uri(),
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "state": "google",
        "prompt": "select_account",
    }
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)


def exchange_google_code(code: str) -> dict | None:
    """Google 인증 코드를 사용자 정보 dict로 교환."""
    client_id = _load_secret("GOOGLE_CLIENT_ID")
    client_secret = _load_secret("GOOGLE_CLIENT_SECRET")
    if not client_id or not client_secret:
        return None
    try:
        token_resp = _requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": get_redirect_uri(),
            },
            timeout=10,
        )
        token = token_resp.json()
        if "access_token" not in token:
            return None
        info = _requests.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {token['access_token']}"},
            timeout=10,
        ).json()
        return {
            "provider": "google",
            "email": info.get("email", ""),
            "name": info.get("name", ""),
            "picture": info.get("picture", ""),
            "is_admin": False,
        }
    except Exception:
        return None


# =========================================================
# Kakao OAuth
# =========================================================
def get_kakao_auth_url() -> str:
    """Kakao OAuth 인증 URL 생성. KAKAO_REST_API_KEY 미설정 시 빈 문자열."""
    app_key = _load_secret("KAKAO_REST_API_KEY")
    if not app_key:
        return ""
    params = {
        "client_id": app_key,
        "redirect_uri": get_redirect_uri(),
        "response_type": "code",
        "state": "kakao",
    }
    return "https://kauth.kakao.com/oauth/authorize?" + urllib.parse.urlencode(params)


def exchange_kakao_code(code: str) -> dict | None:
    """Kakao 인증 코드를 사용자 정보 dict로 교환."""
    app_key = _load_secret("KAKAO_REST_API_KEY")
    if not app_key:
        return None
    try:
        token_resp = _requests.post(
            "https://kauth.kakao.com/oauth/token",
            data={
                "grant_type": "authorization_code",
                "client_id": app_key,
                "redirect_uri": get_redirect_uri(),
                "code": code,
            },
            timeout=10,
        )
        token = token_resp.json()
        if "access_token" not in token:
            return None
        user_resp = _requests.get(
            "https://kapi.kakao.com/v2/user/me",
            headers={"Authorization": f"Bearer {token['access_token']}"},
            timeout=10,
        )
        user = user_resp.json()
        account = user.get("kakao_account", {})
        profile = account.get("profile", {})
        return {
            "provider": "kakao",
            "email": account.get("email", ""),
            "name": profile.get("nickname", ""),
            "picture": profile.get("profile_image_url", ""),
            "is_admin": False,
        }
    except Exception:
        return None


# =========================================================
# 관리자 로그인
# =========================================================
def check_admin_login(input_id: str, input_pw: str) -> bool:
    """관리자 아이디/비밀번호 검증."""
    expected_id = _load_secret("ADMIN_ID", "admin")
    expected_pw = _load_secret("ADMIN_PW", "admin1234")
    return input_id.strip() == expected_id and input_pw.strip() == expected_pw


def make_admin_user() -> dict:
    return {
        "provider": "admin",
        "email": "",
        "name": "관리자",
        "picture": "",
        "is_admin": True,
    }
