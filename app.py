import streamlit as st
import datetime
import io
import os
import re
import sys
import locale

# --- 한글 달력 및 요일을 위한 locale 설정 ---
try:
    locale.setlocale(locale.LC_TIME, 'ko_KR.UTF-8')
except locale.Error:
    pass  # 환경에 한글 Locale이 없을 때는 무시

product_db = {
    "KFC 딸기쨈 (디스펜팩)": 6,
    "Light Sugar 딸기쨈(조흥)": 3,
    "Light Sugar 사과쨈(조흥)": 3,
    "LIGHT&JOY 당을 줄인 김천자두쨈": 12,
    "LIGHT&JOY 당을 줄인 논산딸기쨈": 12,
    "LIGHT&JOY 당을 줄인 청송사과쨈": 12,
}

st.markdown(
    """
    <style>
    .main {background-color: #fff;}
    div.stTextInput > label, div.stDateInput > label {font-weight: bold;}
    input[data-testid="stTextInput"] {background-color: #eee;}
    .yellow-button button {
      background-color: #FFD600 !important;
      color: black !important;
      font-weight: bold;
    }
    .title {font-size:36px; font-weight:bold;}
    .big-blue {font-size:36px; font-weight:bold; color:#1976D2;}
    .big-red {font-size:36px; font-weight:bold; color:#d32f2f;}
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown(
    """
    <style>
        section.main > div {max-width: 390px; min-width: 390px;}
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown('<div class="title">일부인 계산기</div>', unsafe_allow_html=True)
st.write("")

# 세션 상태 변수 초기화
if "product_input" not in st.session_state:
    st.session_state.product_input = ""
if "auto_complete_show" not in st.session_state:
    st.session_state.auto_complete_show = False
if "selected_product_name" not in st.session_state:
    st.session_state.selected_product_name = ""
if "reset_triggered" not in st.session_state:
    st.session_state.reset_triggered = False
if "confirm_success" not in st.session_state:
    st.session_state.confirm_success = False
if "target_date_value" not in st.session_state:
    st.session_state.target_date_value = ""
if "ocr_result" not in st.session_state:
    st.session_state.ocr_result = None

def reset_all():
    st.session_state.product_input = ""
    st.session_state.selected_product_name = ""
    st.session_state.date_input = None
    st.session_state.auto_complete_show = False
    st.session_state.reset_triggered = True
    st.session_state.confirm_success = False
    st.session_state.target_date_value = ""
    st.session_state.ocr_result = None

# --- 제품명 입력과 자동완성 ---
st.write("제품명을 입력하세요")

def on_change_input():
    st.session_state.auto_complete_show = True
    st.session_state.selected_product_name = ""

product_input = st.text_input(
    "",
    value=st.session_state.product_input,
    key="product_input",
    on_change=on_change_input
)

input_value = st.session_state.product_input
matching_products = [
    name for name in product_db.keys()
    if input_value.strip() and input_value.strip() in name
]

def select_product(name):
    st.session_state.product_input = name
    st.session_state.selected_product_name = name
    st.session_state.auto_complete_show = False

if input_value.strip() and st.session_state.auto_complete_show:
    st.write("입력한 내용과 일치하는 제품명:")
    st.markdown("""
    <style>
        .scroll-list {
            max-height: 180px;
            overflow-y: auto;
            border:1px solid #ddd;
            padding:5px;
            margin-bottom:5px;
        }
    </style>
    """, unsafe_allow_html=True)
    st.markdown('<div class="scroll-list">', unsafe_allow_html=True)
    for name in matching_products:
        col1, col2 = st.columns([8, 1])
        col1.button(
            name,
            key=f"btn_{name}",
            on_click=select_product,
            args=(name,),
            use_container_width=True
        )
        col2.write("")
    st.markdown('</div>', unsafe_allow_html=True)
elif not input_value.strip():
    st.session_state.selected_product_name = ""
    st.session_state.auto_complete_show = False

# --- 제조일자 입력 ---
st.write("제조일자")
date_input = st.date_input(
    "",
    key="date_input",
    format="YYYY.MM.DD"
)

col1, col2 = st.columns([1, 1])
confirm = col1.button("확인", key="confirm", help="제품명과 제조일자를 확인합니다.", use_container_width=True)
reset = col2.button("새로고침", key="reset", on_click=reset_all, use_container_width=True)

def is_leap_year(year):
    return (year % 4 == 0) and ((year % 100 != 0) or (year % 400 == 0))

def get_last_day(year, month):
    if month in [1,3,5,7,8,10,12]: return 31
    elif month in [4,6,9,11]: return 30
    elif month == 2: return 29 if is_leap_year(year) else 28
    else: return 30

def get_target_date(start_date, months):
    y, m, d = start_date.year, start_date.month, start_date.day
    new_month = m + months
    new_year = y + (new_month - 1) // 12
    new_month = ((new_month - 1) % 12) + 1
    last_day = get_last_day(new_year, new_month)
    if d <= last_day:
        if d == 1:
            return datetime.date(new_year, new_month, 1)
        else:
            return datetime.date(new_year, new_month, d-1)
    else:
        return datetime.date(new_year, new_month, last_day)

# =========================
# 추가 로직(일 단위 소비기한 지원)
# - product_db 값이 int(또는 숫자)면 "개월"
# - product_db 값이 'd120' 같은 문자열이면 "일"
# - 일 단위일 경우(네이버 날짜계산기와 동일한 포함 방식):
#     목표일부인 = 제조일자 + (일수 - 1)일
# =========================
def parse_shelf_life(value):
    """
    반환:
      - ("month", 개월수:int)  예: 120 -> ("month", 120)
      - ("day", 일수:int)      예: "d120" -> ("day", 120)
    """
    # 1) int로 들어오면 개월로 처리
    if isinstance(value, int):
        return ("month", value)

    # 2) 문자열 처리
    if isinstance(value, str):
        v = value.strip()

        # 'd' 또는 'D'로 시작하는 경우: 일 단위
        if (len(v) >= 2) and (v[0].lower() == "d"):
            num = v[1:].strip()
            if num.isdigit():
                return ("day", int(num))

        # 숫자 문자열이면 개월로 처리(호환)
        if v.isdigit():
            return ("month", int(v))

    # 3) 그 외는 오류로 처리
    raise ValueError(f"소비기한 형식 오류: {value!r} (예: 120 또는 'd120')")

def get_target_date_by_days(start_date, days):
    """
    일 단위 소비기한(네이버와 동일한 포함 계산):
    - 제조일을 1일째로 포함해서 계산
    - 목표일부인 = 제조일자 + (days - 1)일
      예) 2025.12.31, d120 -> 2026.04.29

    방어 로직:
    - days <= 0 이면 형식상 비정상으로 보고 오류 처리
    """
    if days <= 0:
        raise ValueError(f"일 단위 소비기한은 1 이상이어야 합니다: d{days}")
    return start_date + datetime.timedelta(days=days - 1)
# =========================

if confirm:
    pname = st.session_state.product_input
    dt = st.session_state.date_input

    if pname not in product_db.keys():
        st.warning("제품명을 정확하게 입력하거나 목록에서 선택하세요.")
        st.session_state.confirm_success = False
    elif dt is None:
        st.warning("제조일자를 입력하세요.")
        st.session_state.confirm_success = False
    else:
        shelf_life_value = product_db[pname]

        try:
            unit, amount = parse_shelf_life(shelf_life_value)
        except ValueError as e:
            st.warning(str(e))
            st.session_state.confirm_success = False
        else:
            if unit == "day":
                try:
                    target_date = get_target_date_by_days(dt, amount)
                except ValueError as e:
                    st.warning(str(e))
                    st.session_state.confirm_success = False
                else:
                    st.session_state.target_date_value = target_date.strftime('%Y.%m.%d')
                    st.session_state.confirm_success = True
                    st.session_state.ocr_result = None  # OCR 결과 초기화
                    st.success(
                        f"목표일부인: {target_date.strftime('%Y.%m.%d')}",
                        icon="✅"
                    )
                    st.write(f"제품명: {pname}")
                    st.write(f"제조일자: {dt.strftime('%Y.%m.%d')}")
                    st.write(f"소비기한(일): {amount}")
            else:
                # 기존 개월 로직 그대로
                months = amount
                target_date = get_target_date(dt, months)
                st.session_state.target_date_value = target_date.strftime('%Y.%m.%d')
                st.session_state.confirm_success = True
                st.session_state.ocr_result = None  # OCR 결과 초기화
                st.success(
                    f"목표일부인: {target_date.strftime('%Y.%m.%d')}",
                    icon="✅"
                )
                st.write(f"제품명: {pname}")
                st.write(f"제조일자: {dt.strftime('%Y.%m.%d')}")
                st.write(f"소비기한(개월): {months}")

if reset:
    st.experimental_rerun()
