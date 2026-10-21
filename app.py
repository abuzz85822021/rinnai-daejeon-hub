
import streamlit as st
from datetime import date
import calendar

st.set_page_config(
    page_title="대전지사 대리점 HUB",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    .block-container {
        padding-top: 1.5rem;
        max-width: 1100px;
    }
    h1, h2, h3 {
        letter-spacing: -1px;
    }
    div.stButton > button {
        border-radius: 12px;
        min-height: 48px;
    }
</style>
""", unsafe_allow_html=True)

if "menu" not in st.session_state:
    st.session_state.menu = "홈"

st.title("🔥 대전지사 대리점 HUB")
st.caption("RINNAI DAEJEON BRANCH")

menus = ["홈", "공지사항", "달력", "단가표"]

selected = st.radio(
    "메뉴",
    menus,
    index=menus.index(st.session_state.menu),
    horizontal=True,
    label_visibility="collapsed"
)
st.session_state.menu = selected

st.divider()

if selected == "홈":
    st.header("대전지사 안내")
    st.info("대전지사 대리점 전용 업무 안내 웹앱입니다.")

    st.subheader("주요 메뉴")
    col1, col2 = st.columns(2)

    with col1:
        st.success("📢 공지사항")
        st.info("📅 달력")

    with col2:
        st.success("📋 단가표")
        st.info("🏠 홈")

    st.subheader("최근 공지사항")
    st.write("• 동절기 대리점 운영 안내")
    st.write("• 10월 주요 업무 안내")

elif selected == "공지사항":
    st.header("📢 공지사항")
    st.caption("대전지사에서 전달하는 공지사항입니다.")

    with st.expander("동절기 대리점 운영 안내"):
        st.write("공지사항 내용을 등록할 예정입니다.")

    with st.expander("10월 주요 업무 안내"):
        st.write("공지사항 내용을 등록할 예정입니다.")

elif selected == "달력":
    st.header("📅 일정 달력")

    today = date.today()
    year = st.selectbox(
        "연도", range(2025, 2036),
        index=max(0, min(today.year - 2025, 10))
    )
    month = st.selectbox(
        "월", range(1, 13),
        index=today.month - 1
    )

    cal = calendar.HTMLCalendar(firstweekday=6)
    html = cal.formatmonth(year, month)

    st.markdown("""
    <style>
    table.month {
        width: 100%;
        border-collapse: collapse;
        text-align: center;
    }
    table.month th, table.month td {
        border: 1px solid #ddd;
        padding: 12px 4px;
    }
    table.month th {
        background: #f2f2f2;
        color: #333;
    }
    table.month td {
        height: 48px;
    }
    </style>
    """ + html, unsafe_allow_html=True)

    st.info("행사 및 교육 일정 등록 기능은 다음 단계에서 추가합니다.")

elif selected == "단가표":
    st.header("📋 대리점 단가표")
    st.warning("대리점별 로그인 및 단가표 연결 준비 중입니다.")
    st.write("각 대리점은 로그인 후 본인의 단가표만 조회할 수 있습니다.")

st.divider()
st.caption("© RINNAI DAEJEON BRANCH | Dealer HUB v1.0")
