
import calendar
from datetime import date

import streamlit as st
from supabase import create_client


# ==========================================
# 1. 기본 설정
# ==========================================
st.set_page_config(
    page_title="대전지사 대리점 HUB",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
.block-container {
    max-width: 1100px;
    padding-top: 1.5rem;
}
div.stButton > button {
    border-radius: 12px;
    min-height: 44px;
}
table.month {
    width: 100%;
    border-collapse: collapse;
    text-align: center;
}
table.month th,
table.month td {
    border: 1px solid #ddd;
    padding: 10px;
}
</style>
""", unsafe_allow_html=True)


# ==========================================
# 2. 사용자별 Supabase 연결
# ==========================================
def get_supabase():
    if "supabase_client" not in st.session_state:
        st.session_state.supabase_client = create_client(
            st.secrets["SUPABASE_URL"].strip().rstrip("/"),
            st.secrets["SUPABASE_KEY"].strip(),
        )

    return st.session_state.supabase_client


supabase = get_supabase()


# ==========================================
# 3. 로그인 상태 관리
# ==========================================
def clear_login():
    for key in [
        "supabase_client",
        "access_token",
        "refresh_token",
        "user_id",
        "role",
        "name",
        "dealer_id",
    ]:
        st.session_state.pop(key, None)


def logout():
    try:
        supabase.auth.sign_out()
    except Exception:
        pass

    clear_login()
    st.rerun()


def load_profile(user_id):
    result = (
        supabase.table("profiles")
        .select("full_name, role, dealer_id")
        .eq("id", user_id)
        .single()
        .execute()
    )

    return result.data


def save_session(session, user):
    st.session_state.access_token = session.access_token
    st.session_state.refresh_token = session.refresh_token
    st.session_state.user_id = user.id


def refresh_login():
    access_token = st.session_state.get("access_token")
    refresh_token = st.session_state.get("refresh_token")

    if not access_token or not refresh_token:
        return False

    try:
        response = supabase.auth.set_session(
            access_token,
            refresh_token,
        )

        if not response.session or not response.user:
            clear_login()
            return False

        save_session(response.session, response.user)

        # 프로필을 다시 읽어 권한 변경도 반영
        profile = load_profile(response.user.id)

        if not profile:
            clear_login()
            return False

        st.session_state.role = profile["role"]
        st.session_state.name = (
            profile.get("full_name") or "사용자"
        )
        st.session_state.dealer_id = (
            profile.get("dealer_id")
        )

        return True

    except Exception:
        clear_login()
        return False


# ==========================================
# 4. 로그인 화면
# ==========================================
def show_login():
    st.title("🔥 대전지사 대리점")
    st.caption("RINNAI DAEJEON BRANCH")

    st.subheader("로그인")

    with st.form("login_form"):
        email = st.text_input("이메일")
        password = st.text_input(
            "비밀번호",
            type="password",
        )

        submitted = st.form_submit_button(
            "로그인",
            use_container_width=True,
        )

    if submitted:
        if not email.strip() or not password:
            st.warning("이메일과 비밀번호를 입력하세요.")
            return

        try:
            result = supabase.auth.sign_in_with_password({
                "email": email.strip(),
                "password": password,
            })

            if not result.user or not result.session:
                st.error("로그인에 실패했습니다.")
                return

            profile = load_profile(result.user.id)

            if not profile:
                try:
                    supabase.auth.sign_out()
                except Exception:
                    pass

                st.error(
                    "사용자 권한이 등록되지 않았습니다. "
                    "관리자에게 문의하세요."
                )
                return

            save_session(result.session, result.user)

            st.session_state.role = profile["role"]
            st.session_state.name = (
                profile.get("full_name") or "사용자"
            )
            st.session_state.dealer_id = (
                profile.get("dealer_id")
            )

            st.rerun()

        except Exception:
            st.error(
                "로그인할 수 없습니다. "
                "계정 정보 또는 서버 설정을 확인하세요."
            )


# ==========================================
# 5. 인증 확인
# ==========================================
if not refresh_login():
    show_login()
    st.stop()


# ==========================================
# 6. 로그인 후 화면
# ==========================================
st.title("🔥 대전지사 대리점")
st.caption("RINNAI DAEJEON BRANCH")

col1, col2 = st.columns([4, 1])

with col1:
    st.write(
        f"**{st.session_state.name}**님, 환영합니다."
    )

with col2:
    if st.button("로그아웃"):
        logout()


menu = st.radio(
    "메뉴",
    ["홈", "공지사항", "달력", "단가표"],
    horizontal=True,
    label_visibility="collapsed",
)

st.divider()

role = st.session_state.role
can_manage = role in ("admin", "staff")


# ==========================================
# 7. 홈
# ==========================================
if menu == "홈":
    st.header("🏠 홈")
    st.info("대전지사 대리점 전용 웹앱입니다.")
    st.write("공지사항과 주요 일정을 확인하세요.")


# ==========================================
# 8. 공지사항
# ==========================================
elif menu == "공지사항":
    st.header("📢 공지사항")
    st.info(
        "공지사항 등록 및 조회 기능은 "
        "다음 단계에서 연결합니다."
    )

    if can_manage:
        st.button(
            "공지사항 등록",
            disabled=True,
        )


# ==========================================
# 9. 달력
# ==========================================
elif menu == "달력":
    st.header("📅 달력")

    today = date.today()

    year_options = list(range(2025, 2036))

    year = st.selectbox(
        "연도",
        year_options,
        index=year_options.index(
            min(max(today.year, 2025), 2035)
        ),
    )

    month = st.selectbox(
        "월",
        list(range(1, 13)),
        index=today.month - 1,
    )

    cal = calendar.HTMLCalendar(firstweekday=6)

    st.markdown(
        cal.formatmonth(year, month),
        unsafe_allow_html=True,
    )

    if can_manage:
        st.button(
            "일정 등록",
            disabled=True,
        )


# ==========================================
# 10. 단가표
# ==========================================
elif menu == "단가표":
    st.header("📋 단가표")
    st.warning(
        "대리점별 단가표 연결 준비 중입니다."
    )

    if role == "dealer":
        st.write(
            "본인 대리점 단가표만 조회할 수 있습니다."
        )


# ==========================================
# 11. 하단
# ==========================================
st.divider()
st.caption("© RINNAI DAEJEON BRANCH")
