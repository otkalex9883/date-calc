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

    /* ✅ 핵심: Streamlit 레이아웃이 iframe/달력을 잘라먹는 것 방지 */
    div[data-testid="stAppViewContainer"],
    div[data-testid="stMain"],
    section.main,
    div.block-container,
    div[data-testid="stVerticalBlock"],
    div[data-testid="stHorizontalBlock"],
    div[data-testid="column"],
    div[data-testid="stContainer"],
    div.element-container {
        overflow: visible !important;
    }

    iframe {
        overflow: visible !important;
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
st.session_state.setdefault("date_input", today_kst)

def reset_all():
    st.session_state.product_input = ""
    st.session_state.selected_product_name = ""
    st.session_state.auto_complete_show = False
    st.session_state.date_input = today_kst
    st.query_params.clear()

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

qp = st.query_params
qp_key_date = "mfg"
qp_key_open = "picker"

if qp_key_date in qp:
    try:
        st.session_state.date_input = datetime.date.fromisoformat(qp[qp_key_date])
    except Exception:
        pass

default_iso = st.session_state.date_input.isoformat()
is_open = (qp_key_open in qp) and (str(qp[qp_key_open]) == "1")

# open 상태면 넉넉하게(클리핑은 CSS로 풀고, 높이도 충분히)
iframe_height = 520 if is_open else 90

# ✅ 달력은 columns와 완전히 분리된 컨테이너에 둠(클리핑 최소화)
picker_container = st.container()

with picker_container:
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

      function setQuery(params) {{
        const url = new URL(window.parent.location.href);
        Object.keys(params).forEach((k) => {{
          const v = params[k];
          if (v === null || v === undefined) url.searchParams.delete(k);
          else url.searchParams.set(k, v);
        }});
        window.parent.history.replaceState({{}}, "", url.toString());
        window.parent.dispatchEvent(new Event("popstate"));
      }}

      const fp = flatpickr(input, {{
        locale: "ko",
        dateFormat: "Y.m.d",
        defaultDate: "{default_iso}",
        disableMobile: true,
        onOpen: function() {{
          setQuery({{ "{qp_key_open}": "1" }});
        }},
        onClose: function() {{
          setQuery({{ "{qp_key_open}": null }});
        }},
        onChange: function(selectedDates) {{
          const d = selectedDates[0];
          const yyyy = d.getFullYear();
          const mm = String(d.getMonth() + 1).padStart(2, "0");
          const dd = String(d.getDate()).padStart(2, "0");
          const iso = `${{yyyy}}-${{mm}}-${{dd}}`;

          // 날짜 선택 시에도 open 유지(짤림 방지)
          setQuery({{
            "{qp_key_date}": iso,
            "{qp_key_open}": "1"
          }});
        }}
      }});

      if ({str(is_open).lower()}) {{
        setTimeout(() => fp.open(), 0);
      }}
    }})();
    </script>
    """
    components.html(picker_html, height=iframe_height)

# 버튼(달력보다 '아래'에 위치시키되, 달력이 위를 덮어도 잘리지 않게 overflow를 풀어둠)
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
