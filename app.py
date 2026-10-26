import calendar
import re
import secrets
from datetime import date, datetime

import streamlit as st
from supabase import create_client

st.set_page_config(page_title="대전지사 대리점 HUB", page_icon="🔥", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
<style>
.block-container { max-width: 1100px; padding-top: 1.5rem; }
div.stButton > button { border-radius: 12px; min-height: 44px; }
table.month { width: 100%; border-collapse: collapse; text-align: center; }
table.month th, table.month td { border: 1px solid #ddd; padding: 10px; }
</style>
""", unsafe_allow_html=True)


def get_supabase():
    if "supabase_client" not in st.session_state:
        st.session_state.supabase_client = create_client(
            st.secrets["SUPABASE_URL"].strip().rstrip("/"),
            st.secrets["SUPABASE_KEY"].strip(),
        )
    return st.session_state.supabase_client


def clear_login():
    for key in ("supabase_client", "access_token", "refresh_token", "user_id", "role", "name", "dealer_id"):
        st.session_state.pop(key, None)


def logout():
    try:
        get_supabase().auth.sign_out()
    except Exception:
        pass
    clear_login()
    st.rerun()


def load_profile(client, user_id):
    response = client.table("profiles").select("full_name,role,dealer_id").eq("id", user_id).single().execute()
    return response.data


def save_session(session, user):
    st.session_state.access_token = session.access_token
    st.session_state.refresh_token = session.refresh_token
    st.session_state.user_id = user.id


def refresh_login(client):
    access_token = st.session_state.get("access_token")
    refresh_token = st.session_state.get("refresh_token")
    if not access_token or not refresh_token:
        return False
    try:
        response = client.auth.set_session(access_token, refresh_token)
        if not response.session or not response.user:
            clear_login()
            return False
        save_session(response.session, response.user)
        profile = load_profile(client, response.user.id)
        if not profile:
            clear_login()
            return False
        st.session_state.role = profile["role"]
        st.session_state.name = profile.get("full_name") or "사용자"
        st.session_state.dealer_id = profile.get("dealer_id")
        return True
    except Exception:
        clear_login()
        return False


DEALER_LOGIN_DOMAIN = "dealer-login.invalid"

def login_email(identifier):
    identifier = identifier.strip().lower()
    if "@" in identifier:
        return identifier
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{3,31}", identifier):
        raise ValueError("아이디는 영문 소문자, 숫자, _ 또는 - 를 사용해 4~32자로 입력하세요.")
    return f"{identifier}@{DEALER_LOGIN_DOMAIN}"

def dealer_accounts_page(client):
    st.header("🔑 대리점 계정 발급")
    st.caption("대리점은 이메일 없이 아이디와 비밀번호로 로그인합니다. 관리자만 계정을 발급할 수 있습니다.")
    try:
        dealers = client.table("dealers").select("dealer_id,dealer_name").order("dealer_name").execute().data or []
    except Exception:
        st.error("대리점 목록을 불러올 수 없습니다.")
        return
    if not dealers:
