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
st.session_state.setdefault("date_input", today_kst)
st.session_state.setdefault("date_display_raw", today_kst.strftime("%Y.%m.%d"))

def set_query_params(**kwargs):
    qp = st.query_params
    for k, v in kwargs.items():
        if v is None:
            if k in qp:
                del qp[k]
        else:
            qp[k] = str(v)

def reset_all():
    st.session_state.product_input = ""
    st.session_state.selected_product_name = ""
    st.session_state.auto_complete_show = False
    st.session_state.date_input = today_kst
    st.session_state.date_display_raw = today_kst.strftime("%Y.%m.%d")
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

def parse_date_text(s: str):
    if not isinstance(s, str):
        return None
    t = s.strip()
    if not t:
        return None

    # allow: YYYY.MM.DD, YYYY-MM-DD, YYYY/MM/DD, YYYYMMDD
    for sep in (".", "-", "/"):
        if sep in t:
            parts = t.split(sep)
            if len(parts) == 3 and all(p.isdigit() for p in parts):
                try:
                    y, m, d = map(int, parts)
                    return datetime.date(y, m, d)
                except Exception:
                    return None

    if len(t) == 8 and t.isdigit():
        try:
            y = int(t[0:4])
            m = int(t[4:6])
            d = int(t[6:8])
            return datetime.date(y, m, d)
        except Exception:
            return None

    return None

# -----------------------------
# Product input + autocomplete
# -----------------------------
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

# -----------------------------
# Date picker (two-way sync)
# -----------------------------
st.write("제조일자")

qp_key_date = "mfg"
qp_key_cal = "cal"

# A) Apply date from query (calendar selection updates query -> rerun -> sync here)
if qp_key_date in st.query_params:
    try:
        qd = datetime.date.fromisoformat(st.query_params[qp_key_date])
        if qd != st.session_state.date_input:
            st.session_state.date_input = qd
            st.session_state.date_display_raw = qd.strftime("%Y.%m.%d")
    except Exception:
        pass

default_iso = st.session_state.date_input.isoformat()
cal_open = (qp_key_cal in st.query_params) and (str(st.query_params[qp_key_cal]) == "1")

# B) Text input change -> parse -> update session + query (sync to calendar)
def on_change_date_text():
    d = parse_date_text(st.session_state.date_display_raw)
    if d is None:
        return
    st.session_state.date_input = d
    st.session_state.date_display_raw = d.strftime("%Y.%m.%d")
    set_query_params(mfg=d.isoformat(), cal="1")  # keep calendar open so user sees it moved

st.text_input(
    label="제조일자",
    value=st.session_state.date_display_raw,
    key="date_display_raw",
    label_visibility="collapsed",
    placeholder="YYYY.MM.DD",
    on_change=on_change_date_text,
)

# Focus input -> open calendar expander
open_cal_js = f"""
<script>
(function() {{
  const parentDoc = window.parent.document;
  parentDoc.addEventListener("focusin", (e) => {{
    const el = e.target;
    if (!el) return;
    if (el.tagName !== "INPUT") return;
    if ((el.getAttribute("placeholder") || "") !== "YYYY.MM.DD") return;

    const url = new URL(parentDoc.location.href);
    url.searchParams.set("{qp_key_cal}", "1");
    parentDoc.history.replaceState({{}}, "", url.toString());
    window.parent.dispatchEvent(new Event("popstate"));
  }}, true);
}})();
</script>
"""
components.html(open_cal_js, height=0)

with st.expander("달력", expanded=cal_open):
    cal_html = f"""
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/flatpickr/dist/flatpickr.min.css">
    <script src="https://cdn.jsdelivr.net/npm/flatpickr"></script>
    <script src="https://cdn.jsdelivr.net/npm/flatpickr/dist/l10n/ko.js"></script>

    <style>
      body {{
        margin: 0;
        padding: 0;
        background: transparent;
      }}
      #wrap {{
        margin: 0;
        padding: 0;
      }}
      #inline_holder {{
        margin-top: 6px;
      }}
      .flatpickr-calendar {{
        z-index: 999999 !important;
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
      <div id="inline_holder"></div>
    </div>

    <script>
    (function() {{
      const input = document.getElementById("odin_date");
      const holder = document.getElementById("inline_holder");

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

      flatpickr(input, {{
        locale: "ko",
        dateFormat: "Y.m.d",
        defaultDate: "{default_iso}",
        inline: true,
        appendTo: holder,
        disableMobile: true,
        onChange: function(selectedDates) {{
          const d = selectedDates[0];
          const yyyy = d.getFullYear();
          const mm = String(d.getMonth() + 1).padStart(2, "0");
          const dd = String(d.getDate()).padStart(2, "0");
          const iso = `${{yyyy}}-${{mm}}-${{dd}}`;

          // calendar -> query -> python sync -> text input sync
          setQuery({{
            "{qp_key_date}": iso,
            "{qp_key_cal}": null
          }});
        }}
      }});
    }})();
    </script>
    """
    components.html(cal_html, height=360)

# -----------------------------
# Buttons
# -----------------------------
col1, col2 = st.columns([1, 1])
confirm = col1.button("확인", key="confirm", use_container_width=True)
reset = col2.button("새로고침", key="reset", on_click=reset_all, use_container_width=True)

# -----------------------------
# Confirm action
# -----------------------------
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
