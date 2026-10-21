
import streamlit as st
from supabase import create_client
from datetime import date
import calendar

st.set_page_config(
    page_title="대전지사 대리점",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Supabase 연결
@st.cache_resource
def get_supabase():
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"]
    )

supabase = get_supabase()

# 기본 디자인
st.markdown("""
<style>
.block-container {
    max-width: 1100px;
    padding-top: 1.5rem;
}
div.stButton > button {
    border-radius: 12px;
    min-height: 45px;
}
</style>
""", unsafe_allow_html=True)

# 로그인 상태 초기화
if "session" not in st.session_state:
    st.session_state.session = None

if "role" not in st.session_state:
    st.session_state.role = None

# 로그인 화면
if st.session_state.session is None:
    st.title("🔥 대전지사 대리점")
    st.caption("RINNAI DAEJEON BRANCH")

    st.subheader("로그인")

    with st.form("login_form"):
        email = st.text_input("이메일")
        password = st.text_input(
            "비밀번호", type="password"
        )
        login = st.form_submit_button(
            "로그인", use_container_width=True
        )

    if login:
        try:
            result = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })

            user = result.user
            session = result.session

            if user is None or session is None:
                st.error("로그인에 실패했습니다.")
                st.stop()

            # 사용자 토큰으로 프로필 조회
            client = create_client(
                st.secrets["SUPABASE_URL"],
                st.secrets["SUPABASE_KEY"]
            )
            client.auth.set_session(
                session.access_token,
                session.refresh_token
            )

            profile = (
                client.table("profiles")
                .select("role, full_name, dealer_id")
                .eq("id", user.id)
                .single()
                .execute()
            )

            if not profile.data:
                st.error("등록되지 않은 사용자입니다.")
                st.stop()

            st.session_state.session = session
            st.session_state.role = profile.data["role"]
            st.session_state.name = (
                profile.data.get("full_name") or "사용자"
            )
            st.session_state.dealer_id = (
                profile.data.get("dealer_id")
            )

            st.rerun()

        except Exception:
            st.error(
                "로그인에 실패했습니다. "
                "이메일, 비밀번호 또는 계정 등록 상태를 확인하세요."
            )

    st.stop()

# 로그인 후 화면
st.title("🔥 대전지사 대리점")
st.caption("RINNAI DAEJEON BRANCH")

col1, col2 = st.columns([4, 1])

with col1:
    st.write(
        f"**{st.session_state.name}**님, 환영합니다."
    )

with col2:
    if st.button("로그아웃"):
        st.session_state.clear()
        st.rerun()

menu = st.radio(
    "메뉴",
    ["홈", "공지사항", "달력", "단가표"],
    horizontal=True,
    label_visibility="collapsed"
)

st.divider()

if menu == "홈":
    st.header("🏠 홈")
    st.info("대전지사 대리점 전용 웹앱입니다.")
    st.write("공지사항과 주요 일정을 확인하세요.")

elif menu == "공지사항":
    st.header("📢 공지사항")
    st.info("공지사항 조회 및 등록 기능을 준비 중입니다.")

    if st.session_state.role in ["admin", "staff"]:
        st.button("공지사항 등록", disabled=True)

elif menu == "달력":
    st.header("📅 달력")

    today = date.today()
    year = st.selectbox(
        "연도",
        list(range(2025, 2036)),
        index=max(0, min(today.year - 2025, 10))
    )
    month = st.selectbox(
        "월", list(range(1, 13)),
        index=today.month - 1
    )

    cal = calendar.HTMLCalendar(firstweekday=6)
    st.markdown(
        cal.formatmonth(year, month),
        unsafe_allow_html=True
    )

    if st.session_state.role in ["admin", "staff"]:
        st.button("일정 등록", disabled=True)

elif menu == "단가표":
    st.header("📋 단가표")
    st.warning("대리점별 단가표 연결 준비 중입니다.")

    if st.session_state.role == "dealer":
        st.write("본인 대리점 단가표만 조회할 수 있습니다.")

st.divider()
st.caption("© RINNAI DAEJEON BRANCH")
