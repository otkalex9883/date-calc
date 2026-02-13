import streamlit as st
import datetime
import locale
import inspect

from streamlit_date_picker import date_picker

# ---------------------------
# Locale (server-side formatting helper)
# ---------------------------
try:
    locale.setlocale(locale.LC_TIME, "ko_KR.UTF-8")
except locale.Error:
    pass

# ---------------------------
# Data
# ---------------------------
product_db = {
    "아삭 오이 피클": 6,                      # months
    "스위트앤사워소스(대만 맥도날드)": "d120",  # days
}

# ---------------------------
# Styles (popup clipping/z-index fix)
# ---------------------------
st.markdown(
    """
    <style>
    .main {background-color: #fff;}
    div.stTextInput > label, div.stDateInput > label {font-weight: bold;}
    input[data-testid="stTextInput"] {background-color: #eee;}
    .title {font-size:36px; font-weight:bold;}

    /* ✅ Fix: date picker popup gets clipped/hidden (overflow/z-index issues) */
    html, body { overflow: visible !important; }
    div[data-testid="stAppViewContainer"],
    section.main,
    div.block-container,
    div[data-testid="stVerticalBlock"],
    div[data-testid="stHorizontalBlock"] {
        overflow: visible !important;
    }

    /* Popover layers used by many datepickers */
    .react-datepicker-popper,
    .react-datepicker,
    [role="dialog"],
    [data-reach-dialog-overlay],
    [data-reach-dialog-content] {
        z-index: 999999 !important;
    }

    /* Autocomplete list */
    .scroll-list {
        max-height: 180px;
        overflow-y: auto;
        border:1px solid #ddd;
        padding:5px;
        margin-bottom:5px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# NOTE:
# 기존에 사용하던 아래 CSS는 팝업형 컴포넌트(달력)와 충돌/잘림을 일으킬 수 있어 제거했습니다.
# section.main > div {max-width: 390px; min-width: 390px;}

st.markdown('<div class="title">일부인 계산기</div>', unsafe_allow_html=True)
st.write("")

# ---------------------------
# KST today (stable default)
# ---------------------------
KST = datetime.timezone(datetime.timedelta(hours=9))
today_kst_date = datetime.datetime.now(KST).date()

# ---------------------------
# Session state
# ---------------------------
st.session_state.setdefault("product_input", "")
st.session_state.setdefault("auto_complete_show", False)
st.session_state.setdefault("selected_product_name", "")
st.session_state.setdefault("confirm_success", False)
st.session_state.setdefault("target_date_value", "")
st.session_state.setdefault("date_input", today_kst_date)  # store as date for calculations

def reset_all():
    st.session_state.product_input = ""
    st.session_state.selected_product_name = ""
    st.session_state.auto_complete_show = False
    st.session_state.confirm_success = False
    st.session_state.target_date_value = ""
    st.session_state.date_input = today_kst_date

def safe_call_date_picker(**kwargs):
    sig = inspect.signature(date_picker)
    supported = set(sig.parameters.keys())
    filtered = {k: v for k, v in kwargs.items() if k in supported}
    return date_picker(**filtered)

def to_datetime_at_midnight(d: datetime.date) -> datetime.datetime:
    return datetime.datetime.combine(d, datetime.time(0, 0, 0))

def normalize_picked_to_date(picked):
    if isinstance(picked, datetime.datetime):
        return picked.date()
    if isinstance(picked, datetime.date):
        return picked
    if isinstance(picked, (int, float)):
        try:
            return datetime.datetime.fromtimestamp(picked).date()
        except Exception:
            return None
    if isinstance(picked, str):
        s = picked.strip()
        try:
            return datetime.date.fromisoformat(s[:10])
        except Exception:
            return None
    return None

# ---------------------------
# Product input + autocomplete
# ---------------------------
st.write("제품명을 입력하세요")

def on_change_input():
    st.session_state.auto_complete_show = True
    st.session_state.selected_product_name = ""

st.text_input(
    label="제품명",
    value=st.session_state.product_input,
    key="product_input",
    on_change=on_change_input,
    label_visibility="collapsed",
)

input_value = st.session_state.product_input
matching_products = [
    name for name in product_db.keys()
    if input_value.strip() and input_value.strip() in name
]

def select_product(name: str):
    st.session_state.product_input = name
    st.session_state.selected_product_name = name
    st.session_state.auto_complete_show = False

if input_value.strip() and st.session_state.auto_complete_show:
    st.write("입력한 내용과 일치하는 제품명:")
    st.markdown('<div class="scroll-list">', unsafe_allow_html=True)
    for name in matching_products:
        col1, col2 = st.columns([8, 1])
        col1.button(
            name,
            key=f"btn_{name}",
            on_click=select_product,
            args=(name,),
            use_container_width=True,
        )
        col2.write("")
    st.markdown("</div>", unsafe_allow_html=True)
elif not input_value.strip():
    st.session_state.selected_product_name = ""
    st.session_state.auto_complete_show = False

# ---------------------------
# Date picker (Korean calendar)
# ---------------------------
st.write("제조일자")

current_date = st.session_state.date_input
if not isinstance(current_date, datetime.date):
    current_date = today_kst_date
st.session_state.date_input = current_date

picked = safe_call_date_picker(
    value=to_datetime_at_midnight(st.session_state.date_input),  # component expects datetime (timestamp())
    locale="ko",
    language="ko",
)

picked_date = normalize_picked_to_date(picked)
if isinstance(picked_date, datetime.date):
    st.session_state.date_input = picked_date

# Keep showing selected date in app format
st.write(st.session_state.date_input.strftime("%Y.%m.%d"))

# ---------------------------
# Buttons
# ---------------------------
col1, col2 = st.columns([1, 1])
confirm = col1.button("확인", key="confirm", use_container_width=True)
reset = col2.button("새로고침", key="reset", on_click=reset_all, use_container_width=True)

# ---------------------------
# Expiration rules
# ---------------------------
def is_leap_year(year: int) -> bool:
    return (year % 4 == 0) and ((year % 100 != 0) or (year % 400 == 0))

def get_last_day(year: int, month: int) -> int:
    if month in (1, 3, 5, 7, 8, 10, 12):
        return 31
    if month in (4, 6, 9, 11):
        return 30
    return 29 if is_leap_year(year) else 28

def get_target_date(start_date: datetime.date, months: int) -> datetime.date:
    y, m, d = start_date.year, start_date.month, start_date.day
    new_month = m + months
    new_year = y + (new_month - 1) // 12
    new_month = ((new_month - 1) % 12) + 1
    last_day = get_last_day(new_year, new_month)

    if d <= last_day:
        if d == 1:
            return datetime.date(new_year, new_month, 1)
        return datetime.date(new_year, new_month, d - 1)

    return datetime.date(new_year, new_month, last_day)

def parse_shelf_life(value):
    if isinstance(value, int):
        return ("month", value)

    if isinstance(value, str):
        v = value.strip()
        if len(v) >= 2 and v[0].lower() == "d":
            num = v[1:].strip()
            if num.isdigit():
                return ("day", int(num))
        if v.isdigit():
            return ("month", int(v))

    raise ValueError(f"소비기한 형식 오류: {value!r} (예: 120 또는 'd120')")

def get_target_date_by_days(start_date: datetime.date, days: int) -> datetime.date:
    if days <= 0:
        raise ValueError(f"일 단위 소비기한은 1 이상이어야 합니다: d{days}")
    # Naver-style inclusive count: start_date is day 1
    return start_date + datetime.timedelta(days=days - 1)

# ---------------------------
# Confirm action
# ---------------------------
if confirm:
    pname = st.session_state.product_input.strip()
    dt = st.session_state.date_input

    if pname not in product_db:
        st.warning("제품명을 정확하게 입력하거나 목록에서 선택하세요.")
    elif not isinstance(dt, datetime.date):
        st.warning("제조일자를 입력하세요.")
    else:
        try:
            unit, amount = parse_shelf_life(product_db[pname])
            if unit == "day":
                target_date = get_target_date_by_days(dt, amount)
                st.success(f"목표일부인: {target_date.strftime('%Y.%m.%d')}", icon="✅")
                st.write(f"제품명: {pname}")
                st.write(f"제조일자: {dt.strftime('%Y.%m.%d')}")
                st.write(f"소비기한(일): {amount}")
            else:
                target_date = get_target_date(dt, amount)
                st.success(f"목표일부인: {target_date.strftime('%Y.%m.%d')}", icon="✅")
                st.write(f"제품명: {pname}")
                st.write(f"제조일자: {dt.strftime('%Y.%m.%d')}")
                st.write(f"소비기한(개월): {amount}")
        except Exception as e:
            st.warning(str(e))
