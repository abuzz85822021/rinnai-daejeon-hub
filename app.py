import calendar
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


def show_login(client):
    st.title("🔥 대전지사 대리점")
    st.caption("RINNAI DAEJEON BRANCH")
    st.subheader("로그인")
    with st.form("login_form"):
        email = st.text_input("이메일")
        password = st.text_input("비밀번호", type="password")
        submitted = st.form_submit_button("로그인", use_container_width=True)
    if not submitted:
        return
    if not email.strip() or not password:
        st.warning("이메일과 비밀번호를 입력하세요.")
        return
    try:
        result = client.auth.sign_in_with_password({"email": email.strip(), "password": password})
        if not result.user or not result.session:
            st.error("로그인에 실패했습니다.")
            return
        profile = load_profile(client, result.user.id)
        if not profile:
            client.auth.sign_out()
            st.error("사용자 권한이 등록되지 않았습니다. 관리자에게 문의하세요.")
            return
        save_session(result.session, result.user)
        st.session_state.role = profile["role"]
        st.session_state.name = profile.get("full_name") or "사용자"
        st.session_state.dealer_id = profile.get("dealer_id")
        st.rerun()
    except Exception:
        st.error("로그인할 수 없습니다. 계정 정보 또는 서버 설정을 확인하세요.")


def format_created_at(value):
    if not value:
        return ""
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone().strftime("%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return str(value)[:16]


def notices_page(client, can_manage):
    st.header("📢 공지사항")
    if can_manage:
        with st.expander("✏️ 새 공지사항 등록"):
            with st.form("new_notice", clear_on_submit=True):
                title = st.text_input("제목", max_chars=150)
                content = st.text_area("내용", height=180)
                submitted = st.form_submit_button("공지사항 등록")
            if submitted:
                if not title.strip() or not content.strip():
                    st.warning("제목과 내용을 모두 입력하세요.")
                else:
                    try:
                        client.table("notices").insert({
                            "title": title.strip(),
                            "content": content.strip(),
                            "author_id": st.session_state.user_id,
                        }).execute()
                        st.success("공지사항을 등록했습니다.")
                        st.rerun()
                    except Exception:
                        st.error("등록에 실패했습니다. 관리자에게 데이터베이스 권한을 확인해 달라고 요청하세요.")
    try:
        result = client.table("notices").select("id,title,content,author_id,created_at").order("created_at", desc=True).execute()
        notices = result.data or []
    except Exception:
        st.error("공지사항을 불러오지 못했습니다. 데이터베이스 접근 권한을 확인하세요.")
        return
    if not notices:
        st.info("등록된 공지사항이 없습니다.")
        return
    st.caption(f"총 {len(notices)}건의 공지사항")
    for notice in notices:
        notice_id = notice["id"]
        with st.expander(f"📌 {notice['title']}  ·  {format_created_at(notice.get('created_at'))}"):
            st.write(notice["content"])
            if can_manage:
                with st.form(f"edit_notice_{notice_id}"):
                    new_title = st.text_input("제목 수정", value=notice["title"], max_chars=150)
                    new_content = st.text_area("내용 수정", value=notice["content"], height=150)
                    save_clicked = st.form_submit_button("수정 저장")
                if save_clicked:
                    if not new_title.strip() or not new_content.strip():
                        st.warning("제목과 내용을 모두 입력하세요.")
                    else:
                        try:
                            client.table("notices").update({
                                "title": new_title.strip(),
                                "content": new_content.strip(),
                                "updated_at": datetime.now().astimezone().isoformat(),
                            }).eq("id", notice_id).execute()
                            st.success("수정했습니다.")
                            st.rerun()
                        except Exception:
                            st.error("공지사항 수정에 실패했습니다.")
                confirm = st.checkbox("삭제를 확인합니다", key=f"confirm_delete_{notice_id}")
                if st.button("이 공지사항 삭제", key=f"delete_notice_{notice_id}", disabled=not confirm):
                    try:
                        client.table("notices").delete().eq("id", notice_id).execute()
                        st.success("삭제했습니다.")
                        st.rerun()
                    except Exception:
                        st.error("공지사항 삭제에 실패했습니다.")


client = get_supabase()
if not refresh_login(client):
    show_login(get_supabase())
    st.stop()

st.title("🔥 대전지사 대리점")
st.caption("RINNAI DAEJEON BRANCH")
col1, col2 = st.columns([4, 1])
with col1:
    st.write(f"**{st.session_state.name}**님, 환영합니다.")
with col2:
    if st.button("로그아웃"):
        logout()

menu = st.radio("메뉴", ["홈", "공지사항", "달력", "단가표"], horizontal=True, label_visibility="collapsed")
st.divider()
role = st.session_state.role
can_manage = role in ("admin", "staff")

if menu == "홈":
    st.header("🏠 홈")
    st.info("대전지사 대리점 전용 웹앱입니다.")
    st.write("공지사항과 주요 일정을 확인하세요.")
elif menu == "공지사항":
    notices_page(client, can_manage)
elif menu == "달력":
    st.header("📅 달력")
    today = date.today()
    year_options = list(range(2025, 2036))
    year = st.selectbox("연도", year_options, index=year_options.index(min(max(today.year, 2025), 2035)))
    month = st.selectbox("월", list(range(1, 13)), index=today.month - 1)
    cal = calendar.HTMLCalendar(firstweekday=6)
    st.markdown(cal.formatmonth(year, month), unsafe_allow_html=True)
    if can_manage:
        st.button("일정 등록", disabled=True)
elif menu == "단가표":
    st.header("📋 단가표")
    st.warning("대리점별 단가표 연결 준비 중입니다.")
    if role == "dealer":
        st.write("본인 대리점 단가표만 조회할 수 있습니다.")
st.divider()
st.caption("© RINNAI DAEJEON BRANCH")
