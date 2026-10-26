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




# --- 단가표 관리 ---
def money(value):
    return f"{int(value):,}원" if value is not None else "-"


def get_price_lists(client):
    return client.table("price_lists").select("price_list_id,price_list_name,is_default").order("price_list_id").execute().data or []


def get_products(client):
    return client.table("products").select("product_id,model_name,product_name,category").order("model_name").execute().data or []


def get_price_items(client, list_id):
    return client.table("price_list_items").select("product_id,price").eq("price_list_id", list_id).execute().data or []


def submit_price_request(client, list_id, action, items, reason):
    if not items:
        st.warning("변경할 제품이 없습니다.")
        return
    client.table("price_change_requests").insert({
        "price_list_id": list_id,
        "action_type": action,
        "change_data": {"version": 1, "items": items},
        "reason": reason.strip(),
        "requested_by": st.session_state.user_id,
    }).execute()
    st.success("승인 요청을 등록했습니다. 관리자가 승인하면 실제 단가에 반영됩니다.")
    st.rerun()


def staff_prices_page(client, role):
    st.header("📋 단가표")
    st.caption("직원 변경 요청은 관리자 승인 후 실제 가격에 반영됩니다.")
    try:
        lists = get_price_lists(client)
        products = get_products(client)
    except Exception:
        st.error("단가표 조회 권한이 없습니다. 함께 제공된 SQL 보안 설정을 먼저 적용하세요.")
        return
    if role == "admin":
        with st.expander("➕ 단가표 추가 (관리자)"):
            with st.form("new_price_list"):
                name = st.text_input("새 단가표 이름", placeholder="예: 특별 대리점 A 단가표")
                add = st.form_submit_button("단가표 생성")
            if add and name.strip():
                try:
                    client.table("price_lists").insert({"price_list_name": name.strip(), "is_default": False}).execute()
                    st.success("단가표를 만들었습니다.")
                    st.rerun()
                except Exception as e:
                    st.error(f"단가표 생성 실패: {e}")
        with st.expander("🏪 대리점별 단가표 지정 (관리자)"):
            try:
                dealers = client.table("dealers").select("dealer_id,dealer_name,price_list_id").order("dealer_name").execute().data or []
                if not dealers:
                    st.info("등록된 대리점이 없습니다. 대리점 등록 기능은 다음 단계에서 연결합니다.")
                elif lists:
                    dealer_index = st.selectbox("대리점", range(len(dealers)), format_func=lambda i: f"{dealers[i]['dealer_name']} ({dealers[i]['dealer_id']})")
                    list_index = st.selectbox("적용할 단가표", range(len(lists)), format_func=lambda i: lists[i]["price_list_name"], key="assign_list")
                    if st.button("단가표 지정 저장"):
                        client.table("dealers").update({"price_list_id": lists[list_index]["price_list_id"]}).eq("dealer_id", dealers[dealer_index]["dealer_id"]).execute()
                        st.success("대리점 단가표를 지정했습니다.")
                        st.rerun()
            except Exception as e:
                st.error(f"대리점 조회/지정 실패: {e}")
    if not lists:
        st.info("등록된 단가표가 없습니다.")
        return
    selected = st.selectbox("단가표 선택", lists, format_func=lambda r: r["price_list_name"])
    list_id = selected["price_list_id"]
    try:
        current = {int(r["product_id"]): int(r["price"]) for r in get_price_items(client, list_id)}
    except Exception as e:
        st.error(f"가격 조회 실패: {e}")
        return
    product_by_id = {int(p["product_id"]): p for p in products}
    st.subheader("현재 승인된 가격")
    rows = [{"모델명": p["model_name"], "제품명": p["product_name"], "공급단가": money(current[pid])}
            for pid, p in product_by_id.items() if pid in current]
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("아직 승인된 제품 가격이 없습니다.")
    if products:
        with st.expander("✏️ 제품별 가격 등록·수정 요청"):
            with st.form("single_price_request"):
                p = st.selectbox("제품 모델", products, format_func=lambda x: f"{x['model_name']} · {x['product_name']}")
                old = current.get(int(p["product_id"]))
                st.caption(f"현재 가격: {money(old)}")
                price = st.number_input("요청 공급단가 (원)", min_value=0, value=old or 0, step=1000)
                reason = st.text_input("변경 사유", max_chars=300)
                submit = st.form_submit_button("관리자 승인 요청")
            if submit:
                try:
                    submit_price_request(client, list_id, "update", [{"product_id": int(p["product_id"]), "price": int(price)}], reason)
                except Exception as e:
                    st.error(f"승인 요청 등록 실패: {e}")
        with st.expander("🗑️ 제품 가격 삭제 요청"):
            if current:
                with st.form("delete_price_request"):
                    pid = st.selectbox("가격을 삭제할 제품", list(current), format_func=lambda x: product_by_id.get(x, {}).get("model_name", str(x)))
                    reason = st.text_input("삭제 사유", key="delete_reason")
                    confirm = st.checkbox("선택한 제품 가격 삭제를 요청합니다")
                    submit = st.form_submit_button("삭제 승인 요청")
                if submit:
                    if not confirm:
                        st.warning("삭제 확인을 선택하세요.")
                    else:
                        try:
                            submit_price_request(client, list_id, "delete", [{"product_id": int(pid)}], reason)
                        except Exception as e:
                            st.error(f"삭제 요청 실패: {e}")
            else:
                st.info("삭제할 가격이 없습니다.")
        with st.expander("📤 엑셀·CSV 가격 일괄 변경 요청"):
            st.caption("열 이름은 '모델명', '공급단가'로 작성하세요. 파일에 포함된 모델만 변경하며, 빠진 모델은 삭제하지 않습니다.")
            st.caption("제품 모델은 먼저 products 테이블에 등록되어 있어야 합니다. 엑셀(.xlsx)은 openpyxl 패키지가 필요합니다.")
            uploaded = st.file_uploader("가격 파일", type=["xlsx", "csv"], key="price_upload")
            reason = st.text_input("일괄 변경 사유", key="bulk_reason")
            if uploaded is not None:
                try:
                    import pandas as pd
                    df = pd.read_csv(uploaded, dtype=str, encoding="utf-8-sig") if uploaded.name.lower().endswith(".csv") else pd.read_excel(uploaded, dtype=str)
                    if not {"모델명", "공급단가"}.issubset(df.columns):
                        raise ValueError("'모델명', '공급단가' 열이 필요합니다.")
                    by_model = {str(p["model_name"]).strip(): int(p["product_id"]) for p in products}
                    changes, seen = [], set()
                    for _, row in df.iterrows():
                        model = str(row["모델명"]).strip()
                        if model not in by_model:
                            raise ValueError(f"등록되지 않은 모델명: {model}")
                        if model in seen:
                            raise ValueError(f"중복 모델명: {model}")
                        seen.add(model)
                        raw = str(row["공급단가"]).strip().replace(",", "")
                        if not raw.isdigit():
                            raise ValueError(f"가격은 0 이상의 정수여야 합니다: {model}")
                        changes.append({"product_id": by_model[model], "price": int(raw)})
                    st.write(f"검증 완료: {len(changes)}개 모델")
                    st.dataframe(df[["모델명", "공급단가"]], hide_index=True, use_container_width=True)
                    if st.button("이 파일로 승인 요청", disabled=not changes):
                        submit_price_request(client, list_id, "update", changes, reason)
                except Exception as e:
                    st.error(f"파일 검증 실패: {e}")
    else:
        st.info("등록된 제품이 없습니다. products 테이블에 제품을 먼저 등록하세요.")
    st.subheader("내 승인 요청")
    try:
        q = client.table("price_change_requests").select("request_id,action_type,status,reason,requested_at,price_list_id").order("requested_at", desc=True).limit(100).execute()
        mine = [r for r in (q.data or []) if r["status"]]
        if mine:
            st.dataframe([{"요청번호": r["request_id"], "단가표 ID": r["price_list_id"], "구분": r["action_type"], "상태": r["status"], "사유": r.get("reason") or "", "요청일": format_created_at(r["requested_at"])} for r in mine], use_container_width=True, hide_index=True)
        else:
            st.info("등록된 요청이 없습니다.")
    except Exception as e:
        st.error(f"요청 내역 조회 실패: {e}")
    if role == "admin":
        st.subheader("🛡️ 관리자 승인 대기")
        try:
            pending = client.table("price_change_requests").select("request_id,price_list_id,action_type,change_data,reason,requested_by,requested_at").eq("status", "pending").order("requested_at").execute().data or []
            if not pending:
                st.success("승인 대기 중인 요청이 없습니다.")
            for r in pending:
                with st.expander(f"요청 #{r['request_id']} · 단가표 {r['price_list_id']} · {r['action_type']}"):
                    st.write(f"요청자 ID: {r['requested_by']}")
                    st.write(f"요청 사유: {r.get('reason') or '없음'}")
                    st.write(f"요청일: {format_created_at(r['requested_at'])}")
                    items = r.get("change_data", {}).get("items", [])
                    preview = []
                    for item in items:
                        pid = int(item.get("product_id", 0))
                        p = product_by_id.get(pid, {})
                        preview.append({"모델명": p.get("model_name", f"ID {pid}"), "요청 가격": money(item.get("price")) if "price" in item else "삭제"})
                    st.dataframe(preview, hide_index=True, use_container_width=True)
                    comment = st.text_input("검토 의견", key=f"comment_{r['request_id']}")
                    confirmed = st.checkbox("변경 내용을 검토했습니다", key=f"approve_confirm_{r['request_id']}")
                    a, b = st.columns(2)
                    with a:
                        if st.button("승인 및 실제 반영", key=f"approve_{r['request_id']}", disabled=not confirmed):
                            try:
                                result = client.rpc("review_price_change", {"p_request_id": r["request_id"], "p_approve": True, "p_comment": comment}).execute()
                                st.success(result.data or "승인 완료")
                                st.rerun()
                            except Exception as e:
                                st.error(f"승인 실패: {e}")
                    with b:
                        if st.button("반려", key=f"reject_{r['request_id']}"):
                            try:
                                result = client.rpc("review_price_change", {"p_request_id": r["request_id"], "p_approve": False, "p_comment": comment}).execute()
                                st.success(result.data or "반려 완료")
                                st.rerun()
                            except Exception as e:
                                st.error(f"반려 실패: {e}")
        except Exception as e:
            st.error(f"승인 요청 조회 실패: {e}")


def dealer_prices_page(client):
    st.header("📋 내 단가표")
    try:
        response = client.rpc("get_my_dealer_prices").execute()
        items = response.data or []
        if not items:
            st.info("배정된 단가표가 없거나 가격이 아직 등록되지 않았습니다. 지사에 문의하세요.")
            return
        st.dataframe([{"모델명": r["model_name"], "제품명": r["product_name"], "공급단가": money(r["price"])} for r in items], use_container_width=True, hide_index=True)
    except Exception:
        st.warning("대리점 단가 조회 보안 함수 설정이 필요합니다. 관리자에게 문의하세요.")


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
    if role in ("admin", "staff"):
        staff_prices_page(client, role)
    else:
        dealer_prices_page(client)
st.divider()
st.caption("© RINNAI DAEJEON BRANCH")