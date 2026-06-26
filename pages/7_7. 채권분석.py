import streamlit as st
import pandas as pd
import warnings
import modules
from auth import require_login

warnings.filterwarnings('ignore')
st.set_page_config(layout="wide", initial_sidebar_state="expanded")
require_login()

modules.create_sidebar()

year = int(st.session_state['year'])
month = int(st.session_state['month'])

st.markdown(f"## {year}년 {month}월 채권 분석")

t1, t2, t3 = st.tabs([
    '외상매출금 및 받을어음 현황',
    '부서별 채권기일 현황',
    '결제조건 초과채권 현황',
])

# ─────────────────────────────────────────────────────────────
# 공통 CSS (모든 표의 시작점과 끝나는 지점 100% 일치 + 7:3 고정)
# ─────────────────────────────────────────────────────────────
COMMON_CSS = """
<style>
/* 1. 표와 메모를 한 줄에 묶어주는 전체 래퍼 */
.report-wrapper {
    display: flex;
    flex-direction: row;
    align-items: flex-start;
    justify-content: flex-start;
    gap: 40px; 
    width: 100%;
    margin-bottom: 25px;
}

/* 2. 테이블 컨테이너 (정확히전체 화면의 70% 구역을 확보) */
.table-container {
    flex-shrink: 0;
    width: 70%; 
    max-width: 70%; 
    overflow-x: auto;
    display: block;
}

/* 3. 테이블 컴포넌트 (★ 너비를 100%로 주어 어떤 표든 끝선이 무조건 컨테이너 끝에 맞닿도록 고정) */
.ar-table {
    width: 100% !important; /* 표가 작아도 강제로 너비 70% 구역을 꽉 채워 끝선을 통일시킵니다. */
    border-collapse: collapse;
    font-family: 'Noto Sans KR', sans-serif;
    font-size: 15px;
}
.ar-table th, .ar-table td {
    border: 1px solid #aaa;
    padding: 8px 16px;
    text-align: right;
    font-weight: 400;
    white-space: nowrap;
}

/* 데이터 열들의 최소 너비를 지정하여 균등 분배 유도 */
.ar-table th:not(:first-child), .ar-table td:not(:first-child) {
    min-width: 100px;
}

/* 첫 번째 구분 열의 최소 너비를 넓게 잡아 시작선 안정감 확보 */
.ar-table td.label-col, .ar-table th:first-child {
    min-width: 150px;
}
.ar-table thead tr {
    border-top: 1px solid #aaa;
    border-bottom: 1px solid #aaa;
    background-color: #fff;
}
.ar-table thead th {
    text-align: center;
    font-weight: 700;
}
.ar-table td.label-col {
    text-align: left;
    font-weight: 400;
}
.ar-table tr.bold-row td {
    font-weight: 700;
}
.ar-table tr:last-child {
    border-bottom: 1px solid #aaa;
}
.ar-table td.red-val {
    color: #c00;
    font-weight: 400;
}
.ar-table tr.bold-row td.red-val {
    color: #c00;
    font-weight: 700;
}
.ar-table td.blue-val {
    color: #2255cc;
    font-weight: 400;
}

/* 4. 우측 메모 스타일 (정확히 나머지 30% 영역 확보 및 헤더와 줄높이 일치) */
.memo-body {
    width: 30%; 
    flex-shrink: 0;
    font-family: 'Noto Sans KR', sans-serif;
    word-spacing: 5px;
    color: #000;
    line-height: 1.6;
    padding-left: 0px;
    margin-left: 0px;
    margin-top: 24px; /* 캡션 높이 보정용 마진 */
}
.memo-body .indent-0 { 
    padding-left: 0px; 
    padding-top: 0px; 
    text-indent: -30px; 
    font-size: 17px; 
    font-weight: 400; 
}
.memo-body .indent-1 { 
    padding-left: 20px; 
    padding-top: 5px; 
    text-indent: -10px; 
    font-size: 17px; 
}
.memo-body .indent-2 { 
    padding-left: 40px; 
    font-size: 17px; 
}
.memo-body .indent-3 { 
    padding-left: 60px; 
    font-size: 12px; 
}
.memo-body p { 
    margin: 0.2rem 0; 
}
</style>
"""

# ─────────────────────────────────────────────────────────────
# 유틸 및 메모 파싱 함수
# ─────────────────────────────────────────────────────────────
def prev_month(y, m, n):
    m -= n
    while m <= 0:
        m += 12
        y -= 1
    return y, m


def fmt(v):
    if pd.isna(v) or v == 0:
        return ""
    return f"{int(round(v)):,}"


def make_col_specs(year, month):
    yend1_y, yend1_m = year - 2, 12
    yend2_y, yend2_m = year - 1, 12
    m2_y, m2_m = prev_month(year, month, 2)
    m1_y, m1_m = prev_month(year, month, 1)
    specs = [
        (yend1_y, yend1_m, f"{str(yend1_y)[-2:]}년말"),
        (yend2_y, yend2_m, f"{str(yend2_y)[-2:]}년말"),
        (m2_y, m2_m, f"{str(m2_y)[-2:]}년 {m2_m}월"),
        (m1_y, m1_m, f"{str(m1_y)[-2:]}년 {m1_m}월"),
        (year, month, f"{str(year)[-2:]}년 {month}월"),
    ]
    seen, unique = {}, []
    for s in specs:
        if s[2] not in seen:
            seen[s[2]] = True
            unique.append(s)
    return unique


def load_memo(secret_key, y, m):
    try:
        url = st.secrets['memos'][secret_key]
        df = pd.read_csv(url, dtype=str)
        df.columns = df.columns.str.strip()
        year_col = '연도' if '연도' in df.columns else ('년도' if '년도' in df.columns else None)
        if year_col is None or '월' not in df.columns:
            return None
        df[year_col] = pd.to_numeric(df[year_col], errors='coerce').astype('Int64')
        df['월'] = pd.to_numeric(df['월'], errors='coerce').astype('Int64')
        row = df[(df[year_col] == y) & (df['월'] == m)]
        if row.empty:
            return None
        memo_cols = [c for c in df.columns if c not in [year_col, '월']]
        if not memo_cols:
            return None
        val = str(row.iloc[0][memo_cols[0]]).strip()
        return val if val and val.lower() != 'nan' else None
    except Exception:
        return None


def render_memo_html(memo_text):
    if not memo_text:
        return ""

    str_list = memo_text.split('\n')
    html_items = []

    for s in str_list:
        s_stripped = s.strip()
        if s.startswith('   ') or s.startswith('\t\t'):
            indent_cls = "indent-2"
        elif s.startswith(' ') or s.startswith('\t'):
            indent_cls = "indent-1"
        else:
            indent_cls = "indent-0"

        html_items.append(f"<p class='{indent_cls}'>{s_stripped}</p>")

    body_content = "".join(html_items)
    return f'<div class="memo-body">{body_content}</div>'


# ─────────────────────────────────────────────────────────────
# TAB 1: 외상매출금 및 받을어음 현황
# ─────────────────────────────────────────────────────────────
with t1:
    st.markdown(COMMON_CSS, unsafe_allow_html=True)
    st.markdown("<h4>1) 외상매출금 및 받을어음 현황</h4>", unsafe_allow_html=True)

    try:
        raw = pd.read_csv(st.secrets['sheets']['f_56'], dtype=str)
        raw.columns = raw.columns.str.strip()

        item_col = None
        for c in ['구분2', '구분1', '구분3']:
            if c in raw.columns:
                vals = raw[c].astype(str).str.strip().unique().tolist()
                if any(v in vals for v in ['원화', '외화', '자수', '타수']):
                    item_col = c
                    break
        if item_col is None:
            st.error("데이터에서 원화/외화/자수/타수 항목을 찾을 수 없습니다.")
            st.stop()

        raw[item_col] = raw[item_col].astype(str).str.strip()
        raw['연도'] = pd.to_numeric(raw['연도'], errors='coerce').astype('Int64')
        raw['월'] = pd.to_numeric(raw['월'], errors='coerce').astype('Int64')
        raw['실적'] = pd.to_numeric(
            raw['실적'].astype(str).str.replace(',', '', regex=False).str.strip(),
            errors='coerce'
        ).fillna(0.0)

        col_specs = make_col_specs(year, month)
        col_labels = [s[2] for s in col_specs]

        def get_val_t1(item, y, m):
            mask = (raw[item_col] == item) & (raw['연도'] == y) & (raw['월'] == m)
            vals = raw.loc[mask, '실적']
            return float(vals.sum()) / 1e8 if not vals.empty else 0.0

        items_t1 = ['원화', '외화', '자수', '타수']
        rd = {it: {l: get_val_t1(it, y, m) for (y, m, l) in col_specs} for it in items_t1}

        sub_ar = {l: rd['원화'][l] + rd['외화'][l] for l in col_labels}
        sub_note = {l: rd['자수'][l] + rd['타수'][l] for l in col_labels}
        total = {l: sub_ar[l] + sub_note[l] for l in col_labels}
        base = total[col_labels[-1]] if total[col_labels[-1]] != 0 else 1

        def comp(v):
            return f"{round(v / base * 100)}%"

        rows_t1 = [
            ('원화', rd['원화'], False, rd['원화'][col_labels[-1]]),
            ('외화', rd['외화'], False, rd['외화'][col_labels[-1]]),
            ('외상매출금', sub_ar, True, sub_ar[col_labels[-1]]),
            ('자수', rd['자수'], False, rd['자수'][col_labels[-1]]),
            ('타수', rd['타수'], False, rd['타수'][col_labels[-1]]),
            ('받을어음', sub_note, True, sub_note[col_labels[-1]]),
            ('합계', total, True, total[col_labels[-1]]),
        ]

        hdr = "<thead><tr><th>구분</th>"
        for l in col_labels:
            hdr += f"<th>{l}</th>"
        hdr += "<th>구성</th></tr></thead>"

        body = "<tbody>"
        for label, dd, bold, cv in rows_t1:
            rc = "bold-row" if bold else ""
            body += f"<tr class='{rc}'><td class='label-col'>{label}</td>"
            for l in col_labels:
                body += f"<td>{fmt(dd[l])}</td>"
            body += f"<td>{comp(cv)}</td></tr>"
        body += "</tbody>"

        memo1 = load_memo('f_56', year, month)
        memo_html = render_memo_html(memo1) if memo1 else ""

        st.markdown(
            f"<div class='report-wrapper'>"
            f"  <div class='table-container'>"
            f"    <table class='ar-table'><caption style='text-align:right; font-size:12px; color:#555; caption-side:top; padding-bottom:4px;'>[단위 : 억원, %]</caption>{hdr}{body}</table>"
            f"  </div>"
            f"  {memo_html}"
            f"</div>",
            unsafe_allow_html=True
        )
    except Exception as e:
        st.error(f"외상매출금 및 받을어음 현황 오류: {e}")


# ─────────────────────────────────────────────────────────────
# TAB 2: 부서별 채권기일 현황
# ─────────────────────────────────────────────────────────────
with t2:
    st.markdown(COMMON_CSS, unsafe_allow_html=True)
    st.markdown("<h4>1) 부서별 채권기일 현황</h4>", unsafe_allow_html=True)

    try:
        raw2 = pd.read_csv(st.secrets['sheets']['f_57'], dtype=str)
        raw2.columns = raw2.columns.str.strip()
        raw2['구분1'] = raw2['구분1'].astype(str).str.strip()
        raw2['구분2'] = raw2['구분2'].astype(str).str.strip()
        raw2['연도'] = pd.to_numeric(raw2['연도'], errors='coerce').astype('Int64')
        raw2['월'] = pd.to_numeric(raw2['월'], errors='coerce').astype('Int64')
        raw2['실적'] = pd.to_numeric(
            raw2['실적'].astype(str).str.replace(',', '', regex=False).str.strip(),
            errors='coerce'
        ).fillna(0.0)

        col_specs2 = make_col_specs(year, month)
        col_labels2 = [s[2] for s in col_specs2]

        def get_val_t2(g1, g2, y, m):
            mask = (
                    (raw2['구분1'] == g1) &
                    (raw2['구분2'] == g2) &
                    (raw2['연도'] == y) &
                    (raw2['월'] == m)
            )
            vals = raw2.loc[mask, '실적']
            return float(vals.sum()) if not vals.empty else 0.0

        depts = list(dict.fromkeys(raw2['구분1'].tolist()))
        type_order = ['매출', '채권', '일수']

        hdr2 = "<thead><tr><th>구분</th>"
        for l in col_labels2:
            hdr2 += f"<th>{l}</th>"
        hdr2 += "<th>참 고</th></tr></thead>"

        body2 = "<tbody>"

        base_depts = ['선재', '봉강', '부산', '대구']
        exist_depts = [d for d in base_depts if d in depts]
        extra_depts = [d for d in depts if d not in base_depts + ['수출']]
        naesu_order = exist_depts + extra_depts

        def render_dept_rows(dept_list):
            rows = ""
            for dept in dept_list:
                for typ in type_order:
                    v_list = [get_val_t2(dept, typ, y, m) for (y, m, _) in col_specs2]
                    rows += "<tr>"
                    rows += f"<td class='label-col'>{dept} {typ}</td>"
                    for v in v_list:
                        if typ in ('매출', '채권'):
                            rows += f"<td>{fmt(v / 1e8)}</td>"
                        else:
                            rows += f"<td class='blue-val'>{fmt(v)}</td>"
                    rows += "<td></td></tr>"
            return rows

        def render_calc_rows(label, dept_list):
            rows = ""
            for typ in type_order:
                rows += "<tr class='bold-row'>"
                rows += f"<td class='label-col'>{label} {typ}</td>"
                for (y, m, _) in col_specs2:
                    if typ == '일수':
                        sum_cw = sum(get_val_t2(d, '채권', y, m) * get_val_t2(d, '일수', y, m) for d in dept_list)
                        sum_c = sum(get_val_t2(d, '채권', y, m) for d in dept_list)
                        v = sum_cw / sum_c if sum_c != 0 else 0
                        rows += f"<td class='blue-val'>{fmt(v)}</td>"
                    else:
                        v_sum = sum(get_val_t2(d, typ, y, m) for d in dept_list)
                        rows += f"<td>{fmt(v_sum / 1e8)}</td>"
                rows += "<td></td></tr>"
            return rows

        naesu_depts = ['선재', '봉강', '부산', '대구']
        all_depts = naesu_depts + ['수출']

        body2 += render_dept_rows(naesu_order)
        body2 += render_calc_rows('내수', naesu_depts)
        body2 += render_dept_rows(['수출'] if '수출' in depts else [])
        body2 += render_calc_rows('전체', all_depts)
        body2 += "</tbody>"

        memo2 = load_memo('f_57', year, month)
        memo2_html = render_memo_html(memo2) if memo2 else ""

        st.markdown(
            f"<div class='report-wrapper'>"
            f"  <div class='table-container'>"
            f"    <table class='ar-table'>"
            f"      <caption style='text-align:right; font-size:12px; color:#555; caption-side:top; padding-bottom:4px;'>[단위 : 억원, 일]</caption>"
            f"      {hdr2}{body2}</table>"
            f"  </div>"
            f"  {memo2_html}"
            f"</div>",
            unsafe_allow_html=True
        )
    except Exception as e:
        st.error(f"부서별 채권기일 현황 오류: {e}")

with t3:
    st.markdown(COMMON_CSS, unsafe_allow_html=True)

    # ── [세트 1] 3. 결제조건 초과채권 현황(내수) ──────────────────────────
    st.markdown("<h4>1) 결제조건 초과채권 현황(내수)</h4>", unsafe_allow_html=True)

    try:
        raw3 = pd.read_csv(st.secrets['sheets']['f_58'], dtype=str)
        raw3.columns = raw3.columns.str.strip()
        raw3['구분1'] = raw3['구분1'].astype(str).str.strip()
        raw3['연도'] = pd.to_numeric(raw3['연도'], errors='coerce').astype('Int64')
        raw3['월'] = pd.to_numeric(raw3['월'], errors='coerce').astype('Int64')
        raw3['실적'] = pd.to_numeric(
            raw3['실적'].astype(str).str.replace(',', '', regex=False).str.strip(),
            errors='coerce'
        ).fillna(0.0)

        col_specs3 = make_col_specs(year, month)
        col_labels3 = [s[2] for s in col_specs3]
        m1_y, m1_m = prev_month(year, month, 1)


        def get_val_t3(g1, y, m):
            mask = (raw3['구분1'] == g1) & (raw3['연도'] == y) & (raw3['월'] == m)
            vals = raw3.loc[mask, '실적']
            return float(vals.sum()) if not vals.empty else 0.0


        rows_t3 = [
            ('외상매출금', '외상매출금', 'money'),
            ('조건초과채권', '조건초과채권', 'money'),
            ('%', '%', 'pct'),
            ('이자비용', '이자비용', 'money'),
        ]

        hdr3 = "<thead><tr><th>구분</th>"
        for l in col_labels3:
            hdr3 += f"<th>{l}</th>"
        hdr3 += "<th>전월대비</th></tr></thead>"

        body3 = "<tbody>"
        for label, key, unit in rows_t3:
            body3 += "<tr>"
            body3 += f"<td class='label-col'>{label}</td>"

            if unit == 'pct':
                for (y, m, _) in col_specs3:
                    ar = get_val_t3('외상매출금', y, m)
                    exc = get_val_t3('조건초과채권', y, m)
                    display = f"{exc / ar * 100:.2f}%" if ar != 0 else ""
                    body3 += f"<td>{display}</td>"
                ar_cur = get_val_t3('외상매출금', year, month)
                exc_cur = get_val_t3('조건초과채권', year, month)
                ar_prv = get_val_t3('외상매출금', m1_y, m1_m)
                exc_prv = get_val_t3('조건초과채권', m1_y, m1_m)
                pct_cur = exc_cur / ar_cur * 100 if ar_cur != 0 else 0
                pct_prv = exc_prv / ar_prv * 100 if ar_prv != 0 else 0
                diff = pct_cur - pct_prv
                diff_display = f"{diff:.2f}%" if diff != 0 else ""

                # ─── [수정] 첫 번째 표와 동일한 빨간색(color:red) 및 굵기(font-weight:700) 적용 ───
                if diff < 0:
                    body3 += f"<td><span style='color:red; font-weight:700;'>{diff_display}</span></td>"
                else:
                    body3 += f"<td>{diff_display}</td>"
            else:
                vals = [get_val_t3(key, y, m) for (y, m, _) in col_specs3]
                for v in vals:
                    display = fmt(v / 1e6) if v != 0 else ""
                    body3 += f"<td>{display}</td>"
                cur = get_val_t3(key, year, month)
                prev = get_val_t3(key, m1_y, m1_m)
                diff = cur - prev
                diff_display = fmt(diff / 1e6) if diff != 0 else ""

                # ─── [수정] 첫 번째 표와 동일한 빨간색(color:red) 및 굵기(font-weight:700) 적용 ───
                if diff < 0:
                    body3 += f"<td><span style='color:red; font-weight:700;'>{diff_display}</span></td>"
                else:
                    body3 += f"<td>{diff_display}</td>"

            body3 += "</tr>"
        body3 += "</tbody>"

        memo3 = load_memo('f_58', year, month)
        memo3_html = render_memo_html(memo3) if memo3 else ""

        st.markdown(
            f"<div class='report-wrapper'>"
            f"  <div class='table-container'>"
            f"    <table class='ar-table'>"
            f"      <caption style='text-align:right; font-size:12px; color:#555; caption-side:top; padding-bottom:4px;'>[단위 : 백만원, %]</caption>"
            f"      {hdr3}{body3}</table>"
            f"  </div>"
            f"  {memo3_html}"
            f"</div>",
            unsafe_allow_html=True
        )
    except Exception as e:
        st.error(f"결제조건 초과채권 현황 오류: {e}")

    st.divider()

    # ── [세트 2] 2. 부서별 결제조건 초과채권 발생/수급 현황 ──────────────────
    st.markdown("<h4>2) 부서별 결제조건 초과채권 발생/수급 현황</h4>", unsafe_allow_html=True)

    try:
        raw4 = pd.read_csv(st.secrets['sheets']['f_59'], dtype=str)
        raw4.columns = raw4.columns.str.strip()

        df_out, prev2_y, prev2_m = modules.build_f59(raw4, year, month)

        curr_label = f"'{str(year)[-2:]}년 {month}월"
        prev2_label = f"'{str(prev2_y)[-2:]}년 {prev2_m}월말"

        # 헤더 내부의 <br> 태그를 제거하고 공백으로 채워 한 줄로 만듭니다.
        col_headers = [
            "'25년말",
            f"결제조건 초과채권 {prev2_label}",
            "결제조건 초과채권 발생",
            "결제조건 초과채권 수금",
            f"결제조건 초과채권 {curr_label}말",
            "결제조건 초과채권 증감",
            "이자비용 (월)",
        ]

        hdr_html = "<thead><tr><th>구분</th>"
        for h in col_headers:
            hdr_html += f"<th>{h}</th>"
        hdr_html += "</tr></thead>"

        data_cols = [c for c in df_out.columns if c != '구분']


        def fmt_cell(v):
            try:
                v = float(str(v).replace(',', ''))
            except Exception:
                return str(v) if str(v) not in ['nan', '0.0', '0'] else "0"
            if v < 0:
                return f'<span style="color:red; font-weight:700;">-{abs(int(round(v))):,}</span>'
            return f"{int(round(v)):,}"


        body_html = "<tbody>"
        for _, row in df_out.iterrows():
            is_total = row['구분'] == '합계'
            fw = "font-weight:700;" if is_total else ""
            border_top = "border-top:1px solid #aaa;" if is_total else ""
            body_html += f"<tr style='{fw}{border_top}'>"
            body_html += f"<td class='label-col' style='{fw}'>{row['gu분' if 'gu분' in row else '구분']}</td>"
            for c in data_cols:
                cell = fmt_cell(row[c])
                body_html += f"<td style='{fw}'>{cell}</td>"
            body_html += "</tr>"
        body_html += "</tbody>"

        memo4 = load_memo('f_59', year, month)
        memo4_html = render_memo_html(memo4) if memo4 else ""

        # 테이블 컨테이너에 가로 스크롤(overflow-x: auto)을 보장하고,
        # 테이블 헤더와 셀들이 절대 줄바꿈되지 않도록 white-space: nowrap 스타일을 추가했습니다.
        st.markdown(
            f"<div class='report-wrapper'>"
            f"  <div class='table-container' style='overflow-x: auto; max-width: 100%;'>"
            f"    <div style='text-align:right; font-size:12px; color:#555; margin-bottom:4px;'>[단위: 백만원]</div>"
            f"    <table class='ar-table' style='white-space: nowrap; width: 100%;'>{hdr_html}{body_html}</table>"
            f"  </div>"
            f"  {memo4_html}"
            f"</div>",
            unsafe_allow_html=True
        )
    except Exception as e:
        st.error(f"부서별 결제조건 초과채권 현황 오류: {e}")

# 푸터 스타일 고정 유지
st.markdown("""
<style>
.footer { 
    position: fixed;
    bottom: 0; 
    left: 0; 
    right: 0; 
    padding: 10px; 
    text-align: center; 
    font-size: 13px; 
    color: #666666;
    background-color: white;
    border-top: 1px solid #eaeaea;
    z-index: 999;
}
</style>
<div class="footer">ⓒ 2026 SeAH Special Steel Corp. All rights reserved.</div>
""", unsafe_allow_html=True)