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


def calendar_page(client, can_manage):
    st.header("📅 지사 일정")
    today = date.today()
    year_options = list(range(2025, 2036))
    col_year, col_month = st.columns(2)
    with col_year:
        year = st.selectbox("연도", year_options, index=year_options.index(min(max(today.year, 2025), 2035)))
    with col_month:
        month = st.selectbox("월", list(range(1, 13)), index=today.month - 1)

    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])

    if can_manage:
        with st.expander("➕ 새 일정 등록"):
            with st.form("new_calendar_event", clear_on_submit=True):
                title = st.text_input("일정 제목", max_chars=150)
                description = st.text_area("상세 내용 (선택)")
                start_date = st.date_input("시작일", value=today)
                end_date = st.date_input("종료일", value=today)
                submitted = st.form_submit_button("일정 등록")
            if submitted:
                if not title.strip():
                    st.warning("일정 제목을 입력하세요.")
                elif end_date < start_date:
                    st.warning("종료일은 시작일보다 빠를 수 없습니다.")
                else:
                    try:
                        client.table("calendar_events").insert({
                            "title": title.strip(),
                            "description": description.strip(),
                            "start_date": start_date.isoformat(),
                            "end_date": end_date.isoformat(),
                            "author_id": st.session_state.user_id,
                        }).execute()
                        st.success("일정을 등록했습니다.")
                        st.rerun()
                    except Exception:
                        st.error("일정 등록에 실패했습니다. 테이블 권한과 RLS 정책을 확인하세요.")

    try:
        response = (
            client.table("calendar_events")
            .select("id,title,description,start_date,end_date,author_id")
            .lte("start_date", last_day.isoformat())
            .gte("end_date", first_day.isoformat())
            .order("start_date")
            .execute()
        )
        events = response.data or []
    except Exception:
        st.error("일정을 불러오지 못했습니다. Supabase 권한을 확인하세요.")
        return

    st.caption("날짜별 일정 표시 · 여러 날에 걸친 일정은 해당 날짜 모두에 표시됩니다.")
    weekday_labels = ["일", "월", "화", "수", "목", "금", "토"]
    header_cols = st.columns(7)
    for i, label in enumerate(weekday_labels):
        header_cols[i].markdown(f"**{label}**")

    weeks = calendar.Calendar(firstweekday=6).monthdatescalendar(year, month)
    for week in weeks:
        day_cols = st.columns(7)
        for i, day in enumerate(week):
            with day_cols[i]:
                if day.month != month:
                    st.caption("·")
                    continue
                st.markdown(f"**{day.day}**")
                day_events = [e for e in events if e["start_date"] <= day.isoformat() <= e["end_date"]]
                for event in day_events[:2]:
                    st.caption("• " + event["title"][:18])
                if len(day_events) > 2:
                    st.caption(f"외 {len(day_events) - 2}건")
        st.divider()

    st.subheader("이번 달 일정 목록")
    if not events:
        st.info("이번 달에 등록된 일정이 없습니다.")
        return

    for event in events:
        event_id = event["id"]
        period = event["start_date"]
        if event["end_date"] != event["start_date"]:
            period += " ~ " + event["end_date"]
        with st.expander(f"📍 {period} | {event['title']}"):
            st.write(event.get("description") or "상세 내용 없음")
            if not can_manage:
                continue
            with st.form(f"edit_event_{event_id}"):
                new_title = st.text_input("일정 제목 수정", value=event["title"], max_chars=150)
                new_description = st.text_area("상세 내용 수정", value=event.get("description") or "")
                new_start = st.date_input("시작일 수정", value=date.fromisoformat(event["start_date"]))
                new_end = st.date_input("종료일 수정", value=date.fromisoformat(event["end_date"]))
                update_clicked = st.form_submit_button("수정 저장")
            if update_clicked:
                if not new_title.strip():
                    st.warning("일정 제목을 입력하세요.")
                elif new_end < new_start:
                    st.warning("종료일은 시작일보다 빠를 수 없습니다.")
                else:
                    try:
                        client.table("calendar_events").update({
                            "title": new_title.strip(),
                            "description": new_description.strip(),
                            "start_date": new_start.isoformat(),
                            "end_date": new_end.isoformat(),
                        }).eq("id", event_id).execute()
                        st.success("일정을 수정했습니다.")
                        st.rerun()
                    except Exception:
                        st.error("일정 수정에 실패했습니다.")
            confirmed = st.checkbox("삭제 확인", key=f"confirm_event_{event_id}")
            if st.button("이 일정 삭제", key=f"delete_event_{event_id}", disabled=not confirmed):
                try:
                    client.table("calendar_events").delete().eq("id", event_id).execute()
                    st.success("일정을 삭제했습니다.")
                    st.rerun()
                except Exception:
                    st.error("일정 삭제에 실패했습니다.")


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
    calendar_page(client, can_manage)
elif menu == "단가표":
    st.header("📋 단가표")
    st.warning("대리점별 단가표 연결 준비 중입니다.")
    if role == "dealer":
        st.write("본인 대리점 단가표만 조회할 수 있습니다.")
st.divider()
st.caption("© RINNAI DAEJEON BRANCH")
