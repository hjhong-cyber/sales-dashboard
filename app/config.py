"""멀티 프로젝트 × 멀티 채널 자격증명 관리"""
import os
from dotenv import load_dotenv

load_dotenv()

def _get_env(key: str, default: str = None) -> str | None:
    """os.environ 또는 Streamlit secrets에서 값 읽기"""
    val = os.getenv(key)
    if val:
        return val
    try:
        import streamlit as st
        return st.secrets.get(key, default)
    except Exception:
        return default

# ── 공통 ──────────────────────────────────────────
FETCH_DAYS = int(_get_env("FETCH_DAYS", "30"))

# ── 프로젝트 레지스트리 ───────────────────────────
# channels: 현재 연동된 채널 목록 (자격증명이 있는 것만)
PROJECTS = {
    "glener":      {"name": "글리너"},
    "gravyploof":  {"name": "그래비플러프"},
    "ballwatch":   {"name": "볼워치"},
    "xexymix":     {"name": "젝시믹스"},
    "groupbuy":    {"name": "공동구매"},
    "themango":    {"name": "더망고"},
    "lecture":     {"name": "강의사업"},
}

# ── 채널별 자격증명 로더 ─────────────────────────

def get_naver_creds(project: str) -> dict | None:
    """프로젝트의 네이버 자격증명 반환. 없으면 None."""
    prefix = project.upper()
    client_id     = _get_env(f"{prefix}_NAVER_CLIENT_ID")
    client_secret = _get_env(f"{prefix}_NAVER_CLIENT_SECRET")
    if client_id and client_secret:
        return {"client_id": client_id, "client_secret": client_secret}
    return None


def get_cafe24_creds(project: str) -> dict | None:
    prefix = project.upper()
    mall_id       = _get_env(f"{prefix}_CAFE24_MALL_ID")
    client_id     = _get_env(f"{prefix}_CAFE24_CLIENT_ID")
    client_secret = _get_env(f"{prefix}_CAFE24_CLIENT_SECRET")
    if mall_id and client_id and client_secret:
        return {"mall_id": mall_id, "client_id": client_id, "client_secret": client_secret}
    return None


def get_coupang_creds(project: str) -> dict | None:
    prefix = project.upper()
    access_key = _get_env(f"{prefix}_COUPANG_ACCESS_KEY")
    secret_key = _get_env(f"{prefix}_COUPANG_SECRET_KEY")
    vendor_id  = _get_env(f"{prefix}_COUPANG_VENDOR_ID")
    if access_key and secret_key and vendor_id:
        return {"access_key": access_key, "secret_key": secret_key, "vendor_id": vendor_id}
    return None


def get_shopify_creds(project: str) -> dict | None:
    prefix = project.upper()
    shop_domain   = _get_env(f"{prefix}_SHOPIFY_SHOP_DOMAIN")
    access_token  = _get_env(f"{prefix}_SHOPIFY_ACCESS_TOKEN")
    if shop_domain and access_token:
        return {"shop_domain": shop_domain, "access_token": access_token}
    return None


# 자격증명 getter 맵
CHANNEL_CREDS = {
    "naver":   get_naver_creds,
    "cafe24":  get_cafe24_creds,
    "coupang": get_coupang_creds,
    "shopify": get_shopify_creds,
}


def get_active_channels(project: str) -> list[str]:
    """자격증명이 설정된 채널만 반환"""
    return [ch for ch, fn in CHANNEL_CREDS.items() if fn(project) is not None]
