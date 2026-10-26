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
    return client.table("products").select("product_id,model_name,product_name,category,remarks").order("model_name").execute().data or []


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


def parse_original_excel(uploaded, boiler_tier='R1'):
    """Parse full/partial workbook, retaining all R1-R7 tiers."""
    import pandas as pd
    import re
    from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
    sheets = pd.read_excel(uploaded, sheet_name=None, header=None, dtype=object)
    records, skipped = {}, []
    def amount(value):
        if value is None or pd.isna(value) or str(value).strip() in ('', '-', 'nan'): return None
        try:
            d=Decimal(str(value).replace(',','').replace('원','').strip())
            return int(d.quantize(Decimal('1'),rounding=ROUND_HALF_UP)) if d.is_finite() and d>=0 else None
        except (InvalidOperation,ValueError): return None
    for sheet_name,df in sheets.items():
        if sheet_name.strip()=='목차':continue
        header_row=None
        for i in range(min(len(df),40)):
            line=[''.join(str(v).split()) if pd.notna(v) else '' for v in df.iloc[i]]
            if any('모델명' in h for h in line) and any('세별도' in h or '세포함' in h for h in line):header_row=i;break
        if header_row is None:skipped.append(f'{sheet_name}: 가격 헤더 없음');continue
        headers=[''.join(str(v).split()) if pd.notna(v) else '' for v in df.iloc[header_row]]
        model_col=next((i for i,h in enumerate(headers) if '모델명' in h),None)
        cat_col=next((i for i,h in enumerate(headers) if '구분' in h),None)
        note_col=next((i for i,h in enumerate(headers) if h=='비고'),None)
        is_tier=sheet_name.strip() in ('RC620, R331S','RCK623, 각방제어')
        tiers={}
        if is_tier:
            for n in range(1,8):
                label=f'R{n}'
                ex=next((i for i,h in enumerate(headers) if re.match(rf'^{label}세별도',h)),None)
                inc=next((i for i,h in enumerate(headers) if re.match(rf'^{label}세포함',h)),None)
                if ex is not None or inc is not None:tiers[label]=(ex,inc)
            ex_col,inc_col=tiers.get('R1',(None,None))
        else:
            ex_col=next((i for i,h in enumerate(headers) if '출하가' in h and '세별도' in h),None)
            inc_col=next((i for i,h in enumerate(headers) if '출하가' in h and '세포함' in h),None)
        if model_col is None or (ex_col is None and inc_col is None):skipped.append(f'{sheet_name}: 가격 열 없음');continue
        last_cat=''
        for idx in range(header_row+1,len(df)):
            row=df.iloc[idx].tolist()
            def cell(i):return row[i] if i is not None and i<len(row) else None
            c=cell(cat_col)
            if c is not None and pd.notna(c) and str(c).strip():last_cat=str(c).strip()
            m=cell(model_col)
            if m is None or pd.isna(m):continue
            model=str(m).strip()
            if not model or '모델명' in model or model.startswith('['):continue
            ex,inc=amount(cell(ex_col)),amount(cell(inc_col))
            if ex is None and inc is None:continue
            if ex is None:ex=int((Decimal(inc)/Decimal('1.1')).quantize(Decimal('1'),rounding=ROUND_HALF_UP))
            if inc is None:inc=int((Decimal(ex)*Decimal('1.1')).quantize(Decimal('1'),rounding=ROUND_HALF_UP))
            note=cell(note_col);note=str(note).strip() if note is not None and pd.notna(note) else ''
            record={'model_name':model,'product_name':model,'category':f'{sheet_name.strip()} / {last_cat}'[:250],
                    'remarks':note[:4000],'price':ex,'price_including_vat':inc}
            if is_tier:
                record['tiers']={}
                for label,(ec,ic) in tiers.items():
                    e,v=amount(cell(ec)),amount(cell(ic))
                    if e is None and v is None:continue
                    derived=e is None
                    if e is None:e=int((Decimal(v)/Decimal('1.1')).quantize(Decimal('1'),rounding=ROUND_HALF_UP))
                    if v is None:v=int((Decimal(e)*Decimal('1.1')).quantize(Decimal('1'),rounding=ROUND_HALF_UP))
                    record['tiers'][label]={'price_excluding_vat':e,'price_including_vat':v,'vat_excluding_derived':derived}
            if model in records:
                old=records[model]
                if old['price']!=ex or old['price_including_vat']!=inc:
                    skipped.append(f'{model}: 중복 모델 가격 불일치, 최초 값 유지')
                continue
            records[model]=record
    return list(records.values()),skipped


def staff_prices_page(client, role):
    st.header('📋 단가표')
    st.caption('출하가(부가세 별도)와 출하가(부가세 포함)를 함께 표시합니다. 직원 변경은 관리자 승인 후 반영됩니다.')
    try:
        lists = get_price_lists(client)
        products = get_products(client)
    except Exception as e:
        st.error(f'단가표 조회 실패: {e}')
        return
    if role == 'admin':
        with st.expander('➕ 단가표 추가 (관리자)'):
            with st.form('new_price_list'):
                name = st.text_input('새 단가표 이름')
                add = st.form_submit_button('단가표 생성')
            if add and name.strip():
                try:
                    client.table('price_lists').insert({'price_list_name':name.strip(),'is_default':False}).execute()
                    st.rerun()
                except Exception as e: st.error(str(e))
        with st.expander('🏪 대리점별 단가표 지정 (관리자)'):
            try:
                dealers = client.table('dealers').select('dealer_id,dealer_name,price_list_id').order('dealer_name').execute().data or []
                if dealers and lists:
                    dealer = st.selectbox('대리점', dealers, format_func=lambda x:x['dealer_name'])
                    assigned = st.selectbox('적용 단가표', lists, format_func=lambda x:x['price_list_name'],key='assign_price_list')
                    if st.button('단가표 지정 저장'):
                        client.table('dealers').update({'price_list_id':assigned['price_list_id']}).eq('dealer_id',dealer['dealer_id']).execute()
                        st.success('지정 완료')
                else: st.info('등록된 대리점이 없습니다.')
            except Exception as e: st.error(str(e))
    if not lists:
        st.warning('단가표가 없습니다.')
        return
    selected = st.selectbox('단가표 선택', lists, format_func=lambda x:x['price_list_name'])
    list_id = selected['price_list_id']
    try:
        current_rows = client.table('price_list_items').select('product_id,price,price_including_vat').eq('price_list_id',list_id).execute().data or []
    except Exception as e:
        st.error(f'가격 조회 실패: {e}. VAT 설정 SQL 실행 여부를 확인하세요.')
        return
    current = {int(r['product_id']):r for r in current_rows}
    by_id = {int(p['product_id']):p for p in products}
    with st.expander('📤 엑셀 업로드 · 신제품 추가 / 가격 변경',expanded=not bool(products)):
        st.info('제품 등록 없이 원본 엑셀을 업로드할 수 있습니다. 업로드는 변경 요청으로 저장되고 관리자 승인 후 제품과 가격이 함께 등록됩니다.')
        tier = 'R1'
        st.caption('RC620 / RCK623 시트는 R1~R7 전 등급을 자동으로 읽습니다. 다른 시트는 기존 방식으로 처리합니다.')
        uploaded = st.file_uploader('엑셀 가격표(.xlsx)',type=['xlsx'],key='rinnai_full_upload')
        reason = st.text_input('변경 사유',value='원본 엑셀 가격표 업로드',key='original_reason')
        if uploaded:
            try:
                records, skipped = parse_original_excel(uploaded,tier)
                st.write(f'인식한 모델: **{len(records):,}개** / 검토 필요: **{len(skipped)}건**')
                if skipped:
                    with st.expander('검토가 필요한 항목'):
                        st.write(skipped[:150])
                st.markdown('#### 업로드 미리보기 확인')
                groups = list(dict.fromkeys(r['category'].split(' / ')[0] for r in records))
                group_choice = st.selectbox('미리보기 제품군', ['전체'] + groups, key='excel_preview_group')
                matching = [r for r in records if group_choice == '전체' or r['category'].split(' / ')[0] == group_choice]
                search_preview = st.text_input('미리보기 모델명 검색', placeholder='예: RC620, RCK623', key='excel_preview_search').strip().lower()
                if search_preview:
                    matching = [r for r in matching if search_preview in r['model_name'].lower() or search_preview in r['category'].lower()]
                tiered = [r for r in matching if r.get('tiers')]
                preview_tier = None
                if tiered:
                    preview_tier = st.selectbox('R1~R7 가격 확인', ['R1','R2','R3','R4','R5','R6','R7'], key='excel_preview_tier')
                    st.caption(f'선택한 제품군에서 R1~R7 가격이 인식된 모델: {len(tiered)}개')
                preview_rows = []
                for r in matching[:100]:
                    tp = r.get('tiers',{}).get(preview_tier) if preview_tier else None
                    preview_rows.append({'제품군':r['category'], '모델명':r['model_name'],
                        '선택 등급':preview_tier if tp else ('등급 없음' if preview_tier else '기본'),
                        'VAT 별도':money(tp['price_excluding_vat'] if tp else r['price']),
                        'VAT 포함':money(tp['price_including_vat'] if tp else r['price_including_vat']),
                        '비고':r['remarks'][:100]})
                st.write(f'현재 조건에 해당하는 모델: **{len(matching):,}개**')
                st.dataframe(preview_rows, hide_index=True, use_container_width=True)
                st.caption('선택한 제품군/검색 결과 중 최대 100개를 표시합니다. R등급이 없는 제품은 기존 기본 가격이 표시됩니다. 미리보기 선택은 실제 업로드 대상에 영향을 주지 않습니다.')
                mode = st.radio('업로드 방식', ['신제품만 추가', '포함된 모델 추가·수정'],horizontal=True,key='excel_import_mode')
                existing_names={p['model_name'] for p in products}
                selected_records=[r for r in records if mode!='신제품만 추가' or r['model_name'] not in existing_names]
                st.caption(f'이번 승인 요청 대상: {len(selected_records):,}개 모델 · 엑셀에 없는 모델은 유지')
                if st.button('엑셀 변경 승인 요청',disabled=not selected_records):
                    if len(selected_records)>3000:
                        st.error('한 번에 최대 3,000개 모델만 처리할 수 있습니다.')
                    else:
                        submit_price_request(client,list_id,'update',selected_records,reason)
            except Exception as e:
                st.error(f'엑셀 분석 실패: {e}')
    with st.expander('➕ 신제품 직접 등록 (엑셀 없이)'):
        with st.form('new_model_manual'):
            new_model=st.text_input('신제품 모델명')
            new_group=st.text_input('제품군 (예: RC620, R331S)')
            new_detail=st.text_input('상세 제품군')
            new_ex=st.number_input('VAT 별도 가격',min_value=0,step=1000,key='new_ex')
            new_inc=st.number_input('VAT 포함 가격 (0이면 자동 계산)',min_value=0,step=1000,key='new_inc')
            new_note=st.text_area('비고',max_chars=4000)
            new_tiers={}
            st.caption('R1~R7 등급 가격 (필요한 등급만 입력, VAT 포함 0이면 별도×1.1)')
            for t in range(1,8):
                c1,c2=st.columns(2)
                with c1:te=st.number_input(f'R{t} 별도',min_value=0,step=1000,key=f'new_tier_ex_{t}')
                with c2:ti=st.number_input(f'R{t} 포함',min_value=0,step=1000,key=f'new_tier_in_{t}')
                if te or ti:
                    from decimal import Decimal,ROUND_HALF_UP
                    if not te:te=int((Decimal(ti)/Decimal('1.1')).quantize(Decimal('1'),rounding=ROUND_HALF_UP))
                    if not ti:ti=int((Decimal(te)*Decimal('1.1')).quantize(Decimal('1'),rounding=ROUND_HALF_UP))
                    new_tiers[f'R{t}']={'price_excluding_vat':te,'price_including_vat':ti,'vat_excluding_derived':False}
            new_reason=st.text_input('등록 사유')
            new_submit=st.form_submit_button('신제품 등록 승인 요청')
        if new_submit:
            if not new_model.strip() or not new_group.strip():st.error('모델명과 제품군을 입력하세요.')
            elif new_model.strip() in {p['model_name'] for p in products}:st.error('이미 존재하는 모델입니다. 기존 모델 수정을 이용하세요.')
            elif not new_ex and not new_tiers:st.error('가격을 입력하세요.')
            else:
                item={'model_name':new_model.strip(),'product_name':new_model.strip(),
                      'category':f'{new_group.strip()} / {new_detail.strip() or "기타"}',
                      'remarks':new_note,'price':int(new_ex or new_tiers.get('R1',{}).get('price_excluding_vat',0)),
                      'price_including_vat':int(new_inc or round((new_ex or new_tiers.get('R1',{}).get('price_excluding_vat',0))*1.1)),
                      'tiers':new_tiers}
                try:submit_price_request(client,list_id,'update',[item],new_reason)
                except Exception as e:st.error(str(e))
    if products:
        with st.expander('✏️ 기존 모델 가격 수정 요청'):
            p = st.selectbox('모델',products,format_func=lambda x:x['model_name'])
            pid=int(p['product_id'])
            old=current.get(pid,{})
            ex=st.number_input('부가세 별도 가격',min_value=0,value=int(old.get('price') or 0),step=1000)
            inc=st.number_input('부가세 포함 가격',min_value=0,value=int(old.get('price_including_vat') or round(ex*1.1)),step=1000)
            note_text = st.text_area('비고 수정', value=p.get('remarks') or '', height=150, max_chars=4000, key=f'edit_remark_{pid}', help='변경 요청 승인 후 제품 비고에 반영됩니다. 비고는 모든 단가표에서 공통으로 표시됩니다.')
            tier_changes={}
            if str(p.get('category') or '').split(' / ')[0].strip() in ('RC620, R331S','RCK623, 각방제어'):
                with st.expander('R1~R7 가격 수정 (변경할 등급만 입력)'):
                    for t in range(1,8):
                        cols=st.columns(2)
                        with cols[0]:tx=st.number_input(f'R{t} VAT 별도',min_value=0,step=1000,key=f'edit_tx_{pid}_{t}')
                        with cols[1]:ti=st.number_input(f'R{t} VAT 포함',min_value=0,step=1000,key=f'edit_ti_{pid}_{t}')
                        if tx or ti:
                            from decimal import Decimal,ROUND_HALF_UP
                            if not tx:tx=int((Decimal(ti)/Decimal('1.1')).quantize(Decimal('1'),rounding=ROUND_HALF_UP))
                            if not ti:ti=int((Decimal(tx)*Decimal('1.1')).quantize(Decimal('1'),rounding=ROUND_HALF_UP))
                            tier_changes[f'R{t}']={'price_excluding_vat':tx,'price_including_vat':ti,'vat_excluding_derived':False}
            reason_single=st.text_input('수정 사유',key='single_reason')
            if st.button('가격·비고 변경 승인 요청'):
                try: submit_price_request(client,list_id,'update',[{'product_id':pid,'price':int(ex),'price_including_vat':int(inc),'remarks':note_text,'tiers':tier_changes}],reason_single)
                except Exception as e: st.error(str(e))
    st.subheader('승인 요청 내역')
    try:
        requests=client.table('price_change_requests').select('request_id,price_list_id,action_type,status,reason,requested_at').order('requested_at',desc=True).limit(100).execute().data or []
        if requests: st.dataframe([{'요청번호':r['request_id'],'단가표 ID':r['price_list_id'],'상태':r['status'],'사유':r.get('reason'),'요청일':format_created_at(r['requested_at'])} for r in requests],hide_index=True,use_container_width=True)
        else: st.info('요청 내역이 없습니다.')
    except Exception as e: st.error(str(e))


def approvals_page(client):
    products = get_products(client)
    by_id = {int(p["product_id"]): p for p in products}
    if True:
        st.subheader('🛡️ 관리자 승인 대기')
        try:
            pending=client.table('price_change_requests').select('request_id,price_list_id,action_type,change_data,reason,requested_by,requested_at').eq('status','pending').order('requested_at').execute().data or []
            if not pending: st.success('승인 대기 요청이 없습니다.')
            for r in pending:
                with st.expander(f"요청 #{r['request_id']} · 단가표 {r['price_list_id']} · {r['action_type']}"):
                    items=r.get('change_data',{}).get('items',[])
                    st.write(f"요청자: {r['requested_by']} / 사유: {r.get('reason') or '-'} / 총 {len(items)}개 모델")
                    st.dataframe([{'모델명':x.get('model_name') or by_id.get(x.get('product_id'),{}).get('model_name',''),'세별도':money(x.get('price')),'세포함':money(x.get('price_including_vat') if x.get('price_including_vat') is not None else round(float(x.get('price',0))*1.1)), '비고 변경':(x.get('remarks') if 'remarks' in x else '(변경 없음)'),'등급':', '.join((x.get('tiers') or {}).keys())} for x in items[:100]],hide_index=True,use_container_width=True)
                    if len(items)>100: st.caption('첫 100개만 미리보기로 표시합니다.')
                    comment=st.text_input('검토 의견',key=f"comment_{r['request_id']}")
                    confirm=st.checkbox('변경 내용을 검토했습니다',key=f"confirm_{r['request_id']}")
                    c1,c2=st.columns(2)
                    with c1:
                        if st.button('승인 및 반영',key=f"approve_{r['request_id']}",disabled=not confirm):
                            try:
                                res=client.rpc('review_price_change',{'p_request_id':r['request_id'],'p_approve':True,'p_comment':comment}).execute()
                                st.success(res.data or '승인 완료');st.rerun()
                            except Exception as e: st.error(f'승인 실패: {e}')
                    with c2:
                        if st.button('반려',key=f"reject_{r['request_id']}"):
                            try:
                                res=client.rpc('review_price_change',{'p_request_id':r['request_id'],'p_approve':False,'p_comment':comment}).execute()
                                st.success(res.data or '반려 완료');st.rerun()
                            except Exception as e: st.error(f'반려 실패: {e}')
        except Exception as e: st.error(str(e))


def price_catalog_page(client, role):
    import html
    import io
    import pandas as pd

    st.header('📋 린나이 제품 단가표')
    try:
        if role == 'dealer':
            rows = client.rpc('get_my_dealer_prices').execute().data or []
            list_name = '내 대리점 단가표'
        else:
            lists = get_price_lists(client)
            if not lists:
                st.info('등록된 단가표가 없습니다.')
                return
            selected = st.selectbox('단가표 선택', lists,
                format_func=lambda x: x['price_list_name'], key='catalog_list')
            list_name = selected['price_list_name']
            items = client.table('price_list_items').select(
                'product_id,price,price_including_vat').eq(
                'price_list_id', selected['price_list_id']).execute().data or []
            products = get_products(client)
            product_map = {int(p['product_id']): p for p in products}
            rows = []
            for item in items:
                product = product_map.get(int(item['product_id']))
                if product:
                    rows.append({**product, **item})

        tier_prices={}
        try:
            if role=='dealer':
                tier_data=client.rpc('get_my_dealer_tier_prices').execute().data or []
            else:
                tier_data=client.table('price_list_tier_items').select('product_id,tier,price_excluding_vat,price_including_vat').eq('price_list_id',selected['price_list_id']).execute().data or []
            tier_prices={(int(t['product_id']),t['tier']):t for t in tier_data}
        except Exception as tier_error:
            st.warning(f'R1~R7 조회 기능을 확인하세요 (SQL 적용 필요): {tier_error}')
        if not rows:
            st.info('등록된 제품 가격이 없습니다.')
            return

        # Imported Excel stores "worksheet / detailed category" in products.category.
        # Split only for display; no database migration or re-upload is needed.
        def category_parts(row):
            raw = str(row.get('category') or '기타').strip()
            if ' / ' in raw:
                main, detail = raw.split(' / ', 1)
                return (main.strip() or '기타', detail.strip() or '기타')
            return (raw or '기타', '기타')

        # Preserve the original Excel workbook tab order, rather than 가나다 sorting.
        workbook_sheet_order = [
            '주방종합', '가전종합', '가스온수기_캐스케이드', '전기온수기',
            'RC620, R331S', 'RCK623, 각방제어', 'AIOT, UFB보일러',
            '업소용1', '업소용2', '조달청판매제품', '인상제품'
        ]
        existing_groups = {category_parts(r)[0] for r in rows}
        main_groups = [g for g in workbook_sheet_order if g in existing_groups]
        main_groups += sorted(existing_groups - set(main_groups))
        st.caption(f'{list_name} · 전체 {len(rows):,}개 모델')
        main_group = st.selectbox('제품군', ['전체 제품군'] + main_groups,
                                  key='catalog_main_group')
        group_rows = [r for r in rows if main_group == '전체 제품군'
                      or category_parts(r)[0] == main_group]
        detail_groups = sorted({category_parts(r)[1] for r in group_rows})
        detail_group = st.selectbox('상세 제품군', ['전체 상세 제품군'] + detail_groups,
                                    key='catalog_detail_group')
        keyword = st.text_input('모델명 · 제품명 · 비고 검색',
                                placeholder='예: RC620, 2구', key='catalog_search')
        keyword = keyword.strip().casefold()
        filtered = [r for r in group_rows
                    if (detail_group == '전체 상세 제품군'
                        or category_parts(r)[1] == detail_group)
                    and (not keyword or keyword in str(r.get('model_name') or '').casefold()
                         or keyword in str(r.get('product_name') or '').casefold()
                         or keyword in str(r.get('remarks') or '').casefold()
                         or keyword in str(r.get('category') or '').casefold())]
        filtered.sort(key=lambda r: (str(r.get('category') or ''),
                                     str(r.get('model_name') or '')))
        has_tiers=any((int(r['product_id']),t) in tier_prices for r in filtered for t in ('R1','R2','R3','R4','R5','R6','R7'))
        selected_tier='R1'
        if has_tiers:
            selected_tier=st.radio('가격 등급 (전체 대리점 조회 가능)', ['R1','R2','R3','R4','R5','R6','R7'],horizontal=True,key='catalog_tier')
            filtered=[{**r,**({'price':tier_prices[(int(r['product_id']),selected_tier)]['price_excluding_vat'],
                    'price_including_vat':tier_prices[(int(r['product_id']),selected_tier)]['price_including_vat']}
                    if (int(r['product_id']),selected_tier) in tier_prices else
                    {'price':None,'price_including_vat':None} if any((int(r['product_id']),t) in tier_prices for t in ('R1','R2','R3','R4','R5','R6','R7')) else {})} for r in filtered]
        st.caption(f'조회 결과 {len(filtered):,}개 모델 · 단위: 원')
        if not filtered:
            st.info('검색 결과가 없습니다. 제품군 또는 검색어를 변경해 주세요.')
            return

        def incl_price(r):
            if r.get('price_including_vat') is not None:
                return r['price_including_vat']
            return round(float(r['price']) * 1.1) if r.get('price') is not None else None

        # Expanded notes live in a separate full-width table row. They never
        # squeeze the 4th column or make model/price cells excessively tall.
        table_rows = []
        for i, r in enumerate(filtered):
            model = html.escape(str(r.get('model_name') or ''))
            raw_remarks = str(r.get('remarks') or '').strip()
            remarks = html.escape(raw_remarks)
            ex = html.escape(money(r.get('price')).replace('원', ''))
            inc = html.escape(money(incl_price(r)).replace('원', ''))
            row_class = 'alt' if i % 2 else ''
            long_note = len(raw_remarks) > 16 or '\n' in raw_remarks
            if long_note:
                remark_cell = '<details class="r-note"><summary>상세보기</summary></details>'
            elif raw_remarks:
                remark_cell = f'<span class="r-note-short">{remarks}</span>'
            else:
                remark_cell = '<span class="r-note-empty">-</span>'
            table_rows.append(
                f'<tr class="r-main-row {row_class}"><td class="model">{model}</td>'
                f'<td class="price">{ex}</td><td class="price incl">{inc}</td>'
                f'<td class="remarks">{remark_cell}</td></tr>')
            if long_note:
                table_rows.append(
                    '<tr class="r-expanded-row"><td colspan="4">'
                    '<div class="r-note-full"><div class="r-note-title">'
                    f'{model} · 비고 상세내용</div><div class="r-note-text">'
                    f'{remarks}</div></div></td></tr>')

        css = '''
        <style>
        .r-price-wrap {width:100%;overflow-x:auto;border:1px solid #e5eaf1;
                       border-radius:14px;background:#fff;box-shadow:0 3px 14px rgba(24,39,64,.045);}
        .r-price-table {width:100%;border-collapse:separate;border-spacing:0;
                        table-layout:fixed;font-family:inherit;color:#243244;}
        .r-price-table th {position:sticky;top:0;z-index:1;background:#263c59;
                           color:white;padding:13px 9px;font-size:15px;
                           font-weight:650;text-align:left;white-space:nowrap;}
        .r-price-table th:nth-child(1) {width:30%;}
        .r-price-table th:nth-child(2),.r-price-table th:nth-child(3) {width:24%;text-align:right;}
        .r-price-table th:nth-child(4) {width:22%;}
        .r-price-table td {padding:11px 9px;border-bottom:1px solid #edf0f4;
                           font-size:16px;vertical-align:middle;overflow-wrap:anywhere;}
        .r-price-table tr.r-main-row.alt td {background:#f7f9fc;}
        .r-price-table td.model {font-weight:700;color:#233f64;}
        .r-price-table td.price {text-align:right;white-space:nowrap;
                                 font-variant-numeric:tabular-nums;font-weight:550;}
        .r-price-table td.incl {color:#12685c;font-weight:750;}
        .r-price-table td.remarks {color:#657286;font-size:14px;}
        .r-note summary {cursor:pointer;color:#1b5e89;font-weight:700;
                         white-space:nowrap;list-style:none;}
        .r-note summary::-webkit-details-marker {display:none;}
        .r-note summary::before {content:'＋ ';font-weight:800;}
        .r-note[open] summary::before {content:'－ ';}
        .r-expanded-row {display:none;}
        .r-main-row:has(.r-note[open]) + .r-expanded-row {display:table-row;}
        .r-expanded-row td {padding:0 10px 14px!important;background:#fff!important;}
        .r-note-full {padding:16px;border:1px solid #dce8f1;border-radius:12px;
                      background:#f3f7fb;color:#243244;}
        .r-note-title {font-size:15px;font-weight:750;color:#263c59;margin-bottom:9px;}
        .r-note-text {font-size:16px;line-height:1.7;white-space:pre-wrap;
                      overflow-wrap:anywhere;word-break:break-word;}
        .r-note-empty {color:#a2adbb;}
        @media(max-width:600px) {
          .r-price-table th {font-size:13px;padding:12px 4px;}
          .r-price-table td {font-size:14px;padding:13px 4px;}
          .r-price-table td.remarks {font-size:13px;}
          .r-price-table td.price {font-size:13px;letter-spacing:-.35px;}
          .r-price-table th:nth-child(1) {width:29%;}
          .r-price-table th:nth-child(2),.r-price-table th:nth-child(3) {width:25%;}
          .r-price-table th:nth-child(4) {width:21%;}
          .r-expanded-row td {padding:0 7px 12px!important;}
          .r-note-full {padding:14px;}
          .r-note-text {font-size:16px;line-height:1.75;}
        }
        </style>
        '''
        st.html(css + '<div class="r-price-wrap"><table class="r-price-table">'
                    '<thead><tr><th>모델명</th><th>VAT 별도</th><th>VAT 포함</th>'
                    '<th>비고</th></tr></thead><tbody>' + ''.join(table_rows) +
                    '</tbody></table></div>')

        export_rows = [{
            '제품군': category_parts(r)[0],
            '상세 제품군': category_parts(r)[1],
            '모델명': r.get('model_name') or '',
            '부가세 별도': r.get('price'),
            '부가세 포함': incl_price(r),
            '비고': r.get('remarks') or '',
        } for r in filtered]
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            pd.DataFrame(export_rows).to_excel(writer, index=False, sheet_name='단가표')
        st.download_button('📥 현재 조회 단가표 엑셀 다운로드',
                           data=output.getvalue(), file_name='rinnai_price_list.xlsx',
                           mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    except Exception as e:
        st.error(f'단가표를 불러오지 못했습니다: {e}')


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

role = st.session_state.role
menus = ["홈", "공지사항", "달력", "단가표"]
if role in ("admin", "staff"):
    menus.append("단가표 관리")
if role == "admin":
    menus.append("승인 관리")
menu = st.radio("메뉴", menus, horizontal=True, label_visibility="collapsed")
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
    price_catalog_page(client, role)
elif menu == "단가표 관리" and role in ("admin", "staff"):
    staff_prices_page(client, role)
elif menu == "승인 관리" and role == "admin":
    approvals_page(client)
st.divider()
st.caption("© RINNAI DAEJEON BRANCH")