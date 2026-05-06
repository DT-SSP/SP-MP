import streamlit as st
import pandas as pd
import warnings
import modules

warnings.filterwarnings('ignore')
st.set_page_config(layout="wide", initial_sidebar_state="expanded")

modules.create_sidebar()

year  = int(st.session_state['year'])
month = int(st.session_state['month'])

st.markdown(f"## {year}년 {month}월 채권 분석")

t1, t2, t3, t4 = st.tabs([
    '외상매출금 및 받을어음 현황',
    '부서별 채권기일 현황',
    '결제조건 초과채권 현황',
    '부서별 결제조건 초과채권 현황'
])

# ─────────────────────────────────────────────────────────────
# 공통 CSS
# ─────────────────────────────────────────────────────────────
COMMON_CSS = """
<style>
.ar-table {
    border-collapse: collapse;
    font-family: 'Noto Sans KR', sans-serif;
    font-size: 15px;
}
.ar-table th, .ar-table td {
    border: 1px solid #aaa;
    padding: 8px 16px;
    text-align: right;
    font-weight: 400;
    min-width: 120px;
    white-space: nowrap;
}
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
    font-weight: 400;
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
.unit-text {
    text-align: right;
    font-size: 12px;
    color: #555;
    margin-bottom: 4px;
}
.memo-box {
    background: #fafafa;
    border: 1px solid #ddd;
    border-radius: 4px;
    padding: 10px 14px;
    font-size: 13px;
    font-family: 'Noto Sans KR', sans-serif;
    white-space: pre-wrap;
    margin-top: 12px;
    color: #333;
}
</style>
"""

# ─────────────────────────────────────────────────────────────
# 유틸 함수
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
    m2_y,    m2_m    = prev_month(year, month, 2)
    m1_y,    m1_m    = prev_month(year, month, 1)
    specs = [
        (yend1_y, yend1_m, f"{str(yend1_y)[-2:]}년말"),
        (yend2_y, yend2_m, f"{str(yend2_y)[-2:]}년말"),
        (m2_y,    m2_m,    f"{str(m2_y)[-2:]}년 {m2_m}월"),
        (m1_y,    m1_m,    f"{str(m1_y)[-2:]}년 {m1_m}월"),
        (year,    month,   f"{str(year)[-2:]}년 {month}월"),
    ]
    seen, unique = {}, []
    for s in specs:
        if s[2] not in seen:
            seen[s[2]] = True
            unique.append(s)
    return unique

def load_memo(secret_key, y, m):
    try:
        url = st.secrets['sheets'][secret_key]
        df  = pd.read_csv(url, dtype=str)
        df.columns = df.columns.str.strip()
        if '연도' not in df.columns or '월' not in df.columns:
            return None
        df['연도'] = pd.to_numeric(df['연도'], errors='coerce').astype('Int64')
        df['월']   = pd.to_numeric(df['월'],   errors='coerce').astype('Int64')
        row = df[(df['연도'] == y) & (df['월'] == m)]
        if row.empty:
            return None
        memo_cols = [c for c in df.columns if c not in ['연도', '월']]
        if not memo_cols:
            return None
        val = str(row.iloc[0][memo_cols[0]]).strip()
        return val if val and val.lower() != 'nan' else None
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────
# TAB 1: 외상매출금 및 받을어음 현황
# ─────────────────────────────────────────────────────────────
with t1:
    st.markdown(COMMON_CSS, unsafe_allow_html=True)
    st.markdown("<h4>1. 외상매출금 및 받을어음 현황</h4>", unsafe_allow_html=True)

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
        raw['월']   = pd.to_numeric(raw['월'],   errors='coerce').astype('Int64')
        raw['실적'] = pd.to_numeric(
            raw['실적'].astype(str).str.replace(',', '', regex=False).str.strip(),
            errors='coerce'
        ).fillna(0.0)

        col_specs  = make_col_specs(year, month)
        col_labels = [s[2] for s in col_specs]

        def get_val_t1(item, y, m):
            mask = (raw[item_col] == item) & (raw['연도'] == y) & (raw['월'] == m)
            vals = raw.loc[mask, '실적']
            return float(vals.sum()) / 1e8 if not vals.empty else 0.0

        items_t1 = ['원화', '외화', '자수', '타수']
        rd = {it: {l: get_val_t1(it, y, m) for (y, m, l) in col_specs} for it in items_t1}

        sub_ar   = {l: rd['원화'][l] + rd['외화'][l] for l in col_labels}
        sub_note = {l: rd['자수'][l] + rd['타수'][l] for l in col_labels}
        total    = {l: sub_ar[l] + sub_note[l] for l in col_labels}
        base     = total[col_labels[-1]] if total[col_labels[-1]] != 0 else 1

        def comp(v):
            return f"{round(v / base * 100)}%"

        rows_t1 = [
            ('원화',       rd['원화'],  False, rd['원화'][col_labels[-1]]),
            ('외화',       rd['외화'],  False, rd['외화'][col_labels[-1]]),
            ('외상매출금', sub_ar,      True,  sub_ar[col_labels[-1]]),
            ('자수',       rd['자수'],  False, rd['자수'][col_labels[-1]]),
            ('타수',       rd['타수'],  False, rd['타수'][col_labels[-1]]),
            ('받을어음',   sub_note,    True,  sub_note[col_labels[-1]]),
            ('합계',       total,       True,  total[col_labels[-1]]),
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

        st.markdown(
            f"<table class='ar-table' style='width:auto;'><caption style='text-align:right; font-size:12px; color:#555; caption-side:top; padding-bottom:4px;'>[단위 : 억원, %]</caption>{hdr}{body}</table>",
            unsafe_allow_html=True
        )

    except Exception as e:
        st.error(f"외상매출금 및 받을어음 현황 오류: {e}")


# ─────────────────────────────────────────────────────────────
# TAB 2: 부서별 채권기일 현황
# ─────────────────────────────────────────────────────────────
with t2:
    st.markdown(COMMON_CSS, unsafe_allow_html=True)
    st.markdown("<h4>2. 부서별 채권기일 현황</h4>", unsafe_allow_html=True)

    try:
        raw2 = pd.read_csv(st.secrets['sheets']['f_57'], dtype=str)
        raw2.columns = raw2.columns.str.strip()
        raw2['구분1'] = raw2['구분1'].astype(str).str.strip()
        raw2['구분2'] = raw2['구분2'].astype(str).str.strip()
        raw2['연도']  = pd.to_numeric(raw2['연도'], errors='coerce').astype('Int64')
        raw2['월']    = pd.to_numeric(raw2['월'],   errors='coerce').astype('Int64')
        raw2['실적']  = pd.to_numeric(
            raw2['실적'].astype(str).str.replace(',', '', regex=False).str.strip(),
            errors='coerce'
        ).fillna(0.0)

        col_specs2  = make_col_specs(year, month)
        col_labels2 = [s[2] for s in col_specs2]

        def get_val_t2(g1, g2, y, m):
            mask = (
                (raw2['구분1'] == g1) &
                (raw2['구분2'] == g2) &
                (raw2['연도']  == y)  &
                (raw2['월']    == m)
            )
            vals = raw2.loc[mask, '실적']
            return float(vals.sum()) if not vals.empty else 0.0

        # 데이터에서 부서 순서 유지
        depts = list(dict.fromkeys(raw2['구분1'].tolist()))
        type_order = ['매출', '채권', '일수']

        hdr2 = "<thead><tr><th>구분</th>"
        for l in col_labels2:
            hdr2 += f"<th>{l}</th>"
        hdr2 += "<th>참 고</th></tr></thead>"

        body2 = "<tbody>"

        # 선재, 봉강, 부산, 대구 순서로 출력
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
                rows += "<tr>"
                rows += f"<td class='label-col'>{label} {typ}</td>"
                for (y, m, _) in col_specs2:
                    if typ == '일수':
                        sum_cw = sum(get_val_t2(d, '채권', y, m) * get_val_t2(d, '일수', y, m) for d in dept_list)
                        sum_c  = sum(get_val_t2(d, '채권', y, m) for d in dept_list)
                        v = sum_cw / sum_c if sum_c != 0 else 0
                        rows += f"<td class='blue-val'>{fmt(v)}</td>"
                    else:
                        v_sum = sum(get_val_t2(d, typ, y, m) for d in dept_list)
                        rows += f"<td>{fmt(v_sum / 1e8)}</td>"
                rows += "<td></td></tr>"
            return rows

        naesu_depts = ['선재', '봉강', '부산', '대구']
        all_depts   = naesu_depts + ['수출']

        # 순서: 선재/봉강/부산/대구 → 내수 → 수출 → 전체
        body2 += render_dept_rows(naesu_order)
        body2 += render_calc_rows('내수', naesu_depts)
        body2 += render_dept_rows(['수출'] if '수출' in depts else [])
        body2 += render_calc_rows('전체', all_depts)

        body2 += "</tbody>"

        st.markdown(
            f"<table class='ar-table' style='width:auto;'>"
            f"<caption style='text-align:right; font-size:12px; color:#555; caption-side:top; padding-bottom:4px;'>[단위 : 억원, 일]</caption>"
            f"{hdr2}{body2}</table>",
            unsafe_allow_html=True
        )

        # 메모 (f_57_memo - 내용 없으면 표시 안 함)
        memo2 = load_memo('f_57_memo', year, month)
        if memo2:
            st.markdown(f"<div class='memo-box'>{memo2}</div>", unsafe_allow_html=True)

    except Exception as e:
        st.error(f"부서별 채권기일 현황 오류: {e}")


# ─────────────────────────────────────────────────────────────
# TAB 3: 결제조건 초과채권 현황
# ─────────────────────────────────────────────────────────────
with t3:
    st.markdown(COMMON_CSS, unsafe_allow_html=True)
    st.markdown("<h4>3. 결제조건 초과채권 현황(내수)</h4>", unsafe_allow_html=True)

    try:
        raw3 = pd.read_csv(st.secrets['sheets']['f_58'], dtype=str)
        raw3.columns = raw3.columns.str.strip()
        raw3['구분1'] = raw3['구분1'].astype(str).str.strip()
        raw3['연도']  = pd.to_numeric(raw3['연도'], errors='coerce').astype('Int64')
        raw3['월']    = pd.to_numeric(raw3['월'],   errors='coerce').astype('Int64')
        raw3['실적']  = pd.to_numeric(
            raw3['실적'].astype(str).str.replace(',', '', regex=False).str.strip(),
            errors='coerce'
        ).fillna(0.0)

        col_specs3  = make_col_specs(year, month)
        col_labels3 = [s[2] for s in col_specs3]
        m1_y, m1_m  = prev_month(year, month, 1)

        def get_val_t3(g1, y, m):
            mask = (raw3['구분1'] == g1) & (raw3['연도'] == y) & (raw3['월'] == m)
            vals = raw3.loc[mask, '실적']
            return float(vals.sum()) if not vals.empty else 0.0

        # 행 정의: (표시명, 데이터키, 단위구분)
        # 단위구분: 'money'=백만원, 'pct'=%, 'money_small'=백만원(이자비용)
        rows_t3 = [
            ('외상매출금',   '외상매출금',   'money'),
            ('조건초과채권', '조건초과채권', 'money'),
            ('%',            '%',            'pct'),
            ('이자비용',     '이자비용',     'money'),
        ]

        hdr3 = "<thead><tr><th>구분</th>"
        for l in col_labels3:
            hdr3 += f"<th>{l}</th>"
        hdr3 += "<th>전월대비</th></tr></thead>"

        body3 = "<tbody>"
        body3 = "<tbody>"
        for label, key, unit in rows_t3:
            body3 += "<tr>"
            body3 += f"<td class='label-col'>{label}</td>"

            if unit == 'pct':
                # % = 조건초과채권 / 외상매출금 × 100 (DB에서 직접 계산)
                for (y, m, _) in col_specs3:
                    ar  = get_val_t3('외상매출금',   y, m)
                    exc = get_val_t3('조건초과채권', y, m)
                    display = f"{exc / ar * 100:.2f}%" if ar != 0 else ""
                    body3 += f"<td>{display}</td>"
                # 전월대비
                ar_cur  = get_val_t3('외상매출금',   year, month)
                exc_cur = get_val_t3('조건초과채권', year, month)
                ar_prv  = get_val_t3('외상매출금',   m1_y, m1_m)
                exc_prv = get_val_t3('조건초과채권', m1_y, m1_m)
                pct_cur = exc_cur / ar_cur * 100 if ar_cur != 0 else 0
                pct_prv = exc_prv / ar_prv * 100 if ar_prv != 0 else 0
                diff    = pct_cur - pct_prv
                diff_display = f"{diff:.2f}%" if diff != 0 else ""
                red_cls = "red-val" if diff < 0 else ""
                body3 += f"<td class='{red_cls}'>{diff_display}</td>"
            else:
                vals = [get_val_t3(key, y, m) for (y, m, _) in col_specs3]
                for v in vals:
                    display = fmt(v / 1e6) if v != 0 else ""
                    body3 += f"<td>{display}</td>"
                # 전월대비
                cur  = get_val_t3(key, year, month)
                prev = get_val_t3(key, m1_y, m1_m)
                diff = cur - prev
                diff_display = fmt(diff / 1e6) if diff != 0 else ""
                red_cls = "red-val" if diff < 0 else ""
                body3 += f"<td class='{red_cls}'>{diff_display}</td>"

            body3 += "</tr>"
        body3 += "</tbody>"

        st.markdown(
            f"<table class='ar-table' style='width:auto;'><caption style='text-align:right; font-size:12px; color:#555; caption-side:top; padding-bottom:4px;'>[단위 : 백만원, %]</caption>{hdr3}{body3}</table>",
            unsafe_allow_html=True
        )

        # 메모 (f_58_memo)
        memo3 = load_memo('f_58_memo', year, month)
        if memo3:
            st.markdown(f"<div class='memo-box'>{memo3}</div>", unsafe_allow_html=True)

    except Exception as e:
        st.error(f"결제조건 초과채권 현황 오류: {e}")


# ─────────────────────────────────────────────────────────────
# TAB 4: 부서별 결제조건 초과채권 현황
# ─────────────────────────────────────────────────────────────
with t4:
    st.markdown(COMMON_CSS, unsafe_allow_html=True)
    st.markdown("<h4>4. 부서별 결제조건 초과채권 발생/수급 현황</h4>", unsafe_allow_html=True)

    try:
        raw4 = pd.read_csv(st.secrets['sheets']['f_59'], dtype=str)
        raw4.columns = raw4.columns.str.strip()

        # 데이터 행이 실제로 있는지 확인
        data_rows = raw4.dropna(how='all')
        if data_rows.empty or len(data_rows) == 0:
            st.info("현재 등록된 데이터가 없습니다.")
        else:
            raw4['구분1'] = raw4['구분1'].astype(str).str.strip()
            raw4['구분2'] = raw4['구분2'].astype(str).str.strip()
            raw4['구분3'] = raw4['구분3'].astype(str).str.strip()
            raw4['연도']  = pd.to_numeric(raw4['연도'], errors='coerce').astype('Int64')
            raw4['월']    = pd.to_numeric(raw4['월'],   errors='coerce').astype('Int64')
            raw4['실적']  = pd.to_numeric(
                raw4['실적'].astype(str).str.replace(',', '', regex=False).str.strip(),
                errors='coerce'
            ).fillna(0.0)

            # 데이터가 생기면 아래 표 구성 로직 추가 예정
            st.info("데이터가 입력되면 자동으로 표가 표시됩니다.")

    except Exception as e:
        st.error(f"부서별 결제조건 초과채권 현황 오류: {e}")