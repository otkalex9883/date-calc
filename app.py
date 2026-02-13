import streamlit as st
import datetime
import locale
import streamlit.components.v1 as components

try:
    locale.setlocale(locale.LC_TIME, "ko_KR.UTF-8")
except locale.Error:
    pass

product_db = {
    "아삭 오이 피클": 6,
    "스위트앤사워소스(대만 맥도날드)": "d120",
}

st.markdown(
    """
    <style>
    .main {background-color: #fff;}
    div.stTextInput > label {font-weight: bold;}
    input[data-testid="stTextInput"] {background-color: #eee;}
    .title {font-size:36px; font-weight:bold;}

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

st.markdown('<div class="title">일부인 계산기</div>', unsafe_allow_html=True)
st.write("")

KST = datetime.timezone(datetime.timedelta(hours=9))
today_kst = datetime.datetime.now(KST).date()

st.session_state.setdefault("product_input", "")
st.session_state.setdefault("auto_complete_show", False)
st.session_state.setdefault("selected_product_name", "")
st.session_state.setdefault("target_date_value", "")
st.session_state.setdefault("date_input", today_kst)
st.session_state.setdefault("picker_open", False)

def reset_all():
    st.session_state.product_input = ""
    st.session_state.selected_product_name = ""
    st.session_state.auto_complete_show = False
    st.session_state.target_date_value = ""
    st.session_state.date_input = today_kst
    st.session_state.picker_open = False

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

def get_target_date_by_days(start_date: datetime.date, days: int) -> datetime.date:
    if days <= 0:
        raise ValueError(f"일 단위 소비기한은 1 이상이어야 합니다: d{days}")
    return start_date + datetime.timedelta(days=days - 1)

# 제품명
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
        col1.button(name, key=f"btn_{name}", on_click=select_product, args=(name,), use_container_width=True)
        col2.write("")
    st.markdown("</div>", unsafe_allow_html=True)
elif not input_value.strip():
    st.session_state.selected_product_name = ""
    st.session_state.auto_complete_show = False

# 제조일자
st.write("제조일자")

toggle_label = "달력 닫기" if st.session_state.picker_open else "달력 열기"
st.button(
    toggle_label,
    key="toggle_picker",
    on_click=lambda: st.session_state.__setitem__("picker_open", not st.session_state.picker_open),
)

qp = st.query_params
qp_key = "mfg"
if qp_key in qp:
    v = qp[qp_key]
    try:
        st.session_state.date_input = datetime.date.fromisoformat(v)
    except Exception:
        pass

default_iso = st.session_state.date_input.isoformat()
iframe_height = 650 if st.session_state.picker_open else 90
inline_mode = "true" if st.session_state.picker_open else "false"

picker_html = f"""
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/flatpickr/dist/flatpickr.min.css">
<script src="https://cdn.jsdelivr.net/npm/flatpickr"></script>
<script src="https://cdn.jsdelivr.net/npm/flatpickr/dist/l10n/ko.js"></script>

<style>
  body {{
    margin: 0;
    padding: 0;
    background: transparent;
    overflow: visible;
  }}
  #wrap {{
    padding-top: 2px;
    overflow: visible;
  }}
  .flatpickr-calendar {{
    z-index: 999999 !important;
    box-shadow: 0 10px 30px rgba(0,0,0,0.35);
  }}
</style>

<div id="wrap">
  <input id="odin_date" type="text" style="
      width: 160px;
      padding: 8px 10px;
      border-radius: 6px;
      border: 1px solid #666;
      background: #fff;
      color: #000;
    " />
</div>

<script>
(function() {{
  const input = document.getElementById("odin_date");

  function fitHeight() {{
    const cal = document.querySelector(".flatpickr-calendar");
    const wrap = document.getElementById("wrap");
    const extra = 20;

    let h = wrap.getBoundingClientRect().height + extra;
    if (cal) {{
      h = wrap.getBoundingClientRect().height + cal.getBoundingClientRect().height + extra;
    }}

    document.body.style.height = Math.ceil(h) + "px";
    document.documentElement.style.height = Math.ceil(h) + "px";
  }}

  const fp = flatpickr(input, {{
    locale: "ko",
    dateFormat: "Y.m.d",
    defaultDate: "{default_iso}",
    inline: {inline_mode},
    disableMobile: true,
    onReady: function() {{
      setTimeout(fitHeight, 0);
      setTimeout(fitHeight, 50);
      setTimeout(fitHeight, 200);
    }},
    onOpen: function() {{
      setTimeout(fitHeight, 0);
      setTimeout(fitHeight, 50);
      setTimeout(fitHeight, 200);
    }},
    onMonthChange: function() {{
      setTimeout(fitHeight, 0);
      setTimeout(fitHeight, 50);
    }},
    onYearChange: function() {{
      setTimeout(fitHeight, 0);
      setTimeout(fitHeight, 50);
    }},
    onChange: function(selectedDates) {{
      const d = selectedDates[0];
      const yyyy = d.getFullYear();
      const mm = String(d.getMonth() + 1).padStart(2, "0");
      const dd = String(d.getDate()).padStart(2, "0");
      const iso = `${{yyyy}}-${{mm}}-${{dd}}`;

      const url = new URL(window.parent.location.href);
      url.searchParams.set("{qp_key}", iso);
      window.parent.history.replaceState({{}}, "", url.toString());
      window.parent.dispatchEvent(new Event("popstate"));
    }}
  }});

  // initial
  setTimeout(fitHeight, 0);
  setTimeout(fitHeight, 50);
  setTimeout(fitHeight, 200);
}})();
</script>
"""

components.html(picker_html, height=iframe_height)

col1, col2 = st.columns([1, 1])
confirm = col1.button("확인", key="confirm", use_container_width=True)
reset = col2.button("새로고침", key="reset", on_click=reset_all, use_container_width=True)

if confirm:
    pname = st.session_state.product_input.strip()
    dt = st.session_state.date_input

    if pname not in product_db:
        st.warning("제품명을 정확하게 입력하거나 목록에서 선택하세요.")
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
