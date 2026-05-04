import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
import modules

warnings.filterwarnings('ignore')
st.set_page_config(layout="wide", initial_sidebar_state="expanded")

# =========================
# display_styled_df (기존 pages와 동일)
# =========================
def display_styled_df(df, styles=None, highlight_cols=None, already_flat=False, applymap_rules=None):
    if already_flat:
        df_for_style = df.copy()
    else:
        df_for_style = df.reset_index()

    new_cols, seen = [], {}
    for c in df_for_style.columns:
        c_str = str(c)
        seen[c_str] = seen.get(c_str, 0) + 1
        new_cols.append(c_str if seen[c_str] == 1 else f"{c_str}.{seen[c_str]-1}")
    df_for_style.columns = new_cols

    hi_set = set(map(str, (highlight_cols or [])))
    def highlight_columns(col):
        return ['background-color: #f0f0f0'] * len(col) if str(col.name) in hi_set else [''] * len(col)

    styled_df = (
        df_for_style.style
        .format(lambda x: f"{x:,.0f}" if isinstance(x, (int, float, np.integer, np.floating)) and pd.notnull(x) else x)
        .set_properties(**{'text-align': 'right', 'font-family': 'Noto Sans KR'})
        .apply(highlight_columns, axis=0)
        .hide(axis="index")
    )

    if styles:
        styled_df = styled_df.set_table_styles(styles)

    if applymap_rules:
        for func, subset in applymap_rules:
            rows, cols = subset
            styled_df = styled_df.map(func, subset=pd.IndexSlice[rows, cols])

    st.markdown(
        f"<div style='display:flex;justify-content:left'>{styled_df.to_html()}</div>",
        unsafe_allow_html=True
    )


# =========================
# 사이드바
# =========================
modules.create_sidebar()

year  = int(st.session_state['year'])
month = int(st.session_state['month'])

st.markdown(f"## {year}년 {month}월 채권 분석")

t1, = st.tabs(['외상매출금 및 받을어음 현황'])

# =========================
# 1. 외상매출금 및 받을어음 현황
# =========================
with t1:
    st.markdown("<h4>1) 외상매출금 및 받을어음 현황</h4>", unsafe_allow_html=True)
    st.markdown(
        "<div style='text-align:right; font-size:13px; color:#666;'>[단위 : 억원, %]</div>",
        unsafe_allow_html=True,
    )

    try:
        file_name = st.secrets['sheets']['f_56']
        raw = pd.read_csv(file_name, dtype=str)

        # ── 숫자 변환 ──
        raw['연도'] = pd.to_numeric(raw['연도'], errors='coerce').astype('Int64')
        raw['월']   = pd.to_numeric(raw['월'],   errors='coerce').astype('Int64')
        raw['실적'] = pd.to_numeric(
            raw['실적'].astype(str).str.replace(',', '', regex=False),
            errors='coerce'
        ).fillna(0.0)

        # ── 열 구성: 연말 2개 + 최근 3개월 ──
        # 연말: (year-2)년 12월, (year-1)년 12월
        # 월별: 기준월 기준 3개월 전 ~ 기준월
        def prev_month(y, m, n):
            """n개월 전 (year, month) 반환"""
            m -= n
            while m <= 0:
                m += 12
                y -= 1
            return y, m

        yend1_y, yend1_m = year - 2, 12
        yend2_y, yend2_m = year - 1, 12

        m2_y, m2_m = prev_month(year, month, 2)
        m1_y, m1_m = prev_month(year, month, 1)
        m0_y, m0_m = year, month

        col_specs = [
            (yend1_y, yend1_m, f"'{str(yend1_y)[-2:]}년 12월"),
            (yend2_y, yend2_m, f"'{str(yend2_y)[-2:]}년 12월"),
            (m2_y,    m2_m,    f"'{str(m2_y)[-2:]}년 {m2_m}월"),
            (m1_y,    m1_m,    f"'{str(m1_y)[-2:]}년 {m1_m}월"),
            (m0_y,    m0_m,    f"'{str(m0_y)[-2:]}년 {m0_m}월"),
        ]

        # 중복 라벨 방지 (연말이 월별과 겹칠 경우)
        seen_labels, unique_specs = {}, []
        for spec in col_specs:
            label = spec[2]
            if label not in seen_labels:
                seen_labels[label] = True
                unique_specs.append(spec)
        col_specs = unique_specs

        col_labels = [s[2] for s in col_specs]

        # ── 구분2 기준 데이터 pivot ──
        def get_val(구분2, y, m):
            mask = (
                (raw['구분2'] == 구분2) &
                (raw['연도']  == y) &
                (raw['월']    == m)
            )
            vals = raw.loc[mask, '실적']
            if vals.empty:
                return 0.0
            return float(vals.sum()) / 1e8   # 원 → 억원

        rows_def = [
            ('외상매출금', '원화',   '원화'),
            ('외상매출금', '외화',   '외화'),
            ('외상매출금', '외상매출금', None),   # 소계 행
            ('받을어음',   '자수',   '자수'),
            ('받을어음',   '타수',   '타수'),
            ('받을어음',   '받을어음',  None),   # 소계 행
            ('합계',       '합계',   None),
        ]

        # ── 표 데이터 생성 ──
        table_rows = []
        subtotal_ar  = {l: 0.0 for l in col_labels}   # 외상매출금 소계
        subtotal_note = {l: 0.0 for l in col_labels}  # 받을어음 소계
        grand_total  = {l: 0.0 for l in col_labels}   # 합계

        raw_data = {}  # 구분2 → {라벨: 값}

        target_items = ['원화', '외화', '자수', '타수']
        for item in target_items:
            raw_data[item] = {}
            for (y, m, label) in col_specs:
                raw_data[item][label] = get_val(item, y, m)

        # 외상매출금 소계 = 원화 + 외화
        subtotal_ar = {l: raw_data['원화'][l] + raw_data['외화'][l] for l in col_labels}
        # 받을어음 소계 = 자수 + 타수
        subtotal_note = {l: raw_data['자수'][l] + raw_data['타수'][l] for l in col_labels}
        # 합계
        grand_total = {l: subtotal_ar[l] + subtotal_note[l] for l in col_labels}

        # 구성(%) 계산 기준: 기준월 합계
        base_total = grand_total[col_labels[-1]] if grand_total[col_labels[-1]] != 0 else 1

        def composition(val):
            return f"{round(val / base_total * 100)}%"

        # ── 포맷 함수 ──
        def fmt(v):
            if v == 0:
                return ""
            return f"{int(round(v)):,}"

        # ── 행 구성 ──
        def make_row(label, data_dict, is_subtotal=False, comp_val=None):
            row = {'구분': label}
            for l in col_labels:
                row[l] = fmt(data_dict[l])
            row['구성'] = composition(comp_val) if comp_val is not None else ""
            return row

        table_data = [
            make_row('원화',        raw_data['원화'],   comp_val=raw_data['원화'][col_labels[-1]]),
            make_row('외화',        raw_data['외화'],   comp_val=raw_data['외화'][col_labels[-1]]),
            make_row('외상매출금',  subtotal_ar,        comp_val=subtotal_ar[col_labels[-1]]),
            make_row('자수',        raw_data['자수'],   comp_val=raw_data['자수'][col_labels[-1]]),
            make_row('타수',        raw_data['타수'],   comp_val=raw_data['타수'][col_labels[-1]]),
            make_row('받을어음',    subtotal_note,      comp_val=subtotal_note[col_labels[-1]]),
            make_row('합계',        grand_total,        comp_val=grand_total[col_labels[-1]]),
        ]

        disp = pd.DataFrame(table_data)

        # ── 스페이서 컬럼 ──
        SPACER = "__spacer__"
        disp.insert(0, SPACER, "")

        cols = disp.columns.tolist()

        # ── 헤더 행 ──
        hdr1 = [''] * len(cols)
        hdr2 = [''] * len(cols)

        c_idx = {c: i for i, c in enumerate(cols)}

        hdr1[c_idx['구분']] = '구분'
        for l in col_labels:
            hdr1[c_idx[l]] = l
        hdr1[c_idx['구성']] = '구성'

        hdr_df   = pd.DataFrame([hdr1], columns=cols)
        disp_vis = pd.concat([hdr_df, disp], ignore_index=True)

        # ── 스타일 ──
        styles = [
            {'selector': 'thead', 'props': [('display', 'none')]},
            {'selector': 'table', 'props': [('border-collapse', 'collapse'), ('width', '100%')]},

            # 헤더 행 (1번째)
            {'selector': 'tbody tr:nth-child(1) td',
             'props': [('text-align', 'center'), ('font-weight', '700'),
                       ('padding', '8px 8px'), ('border-top', '3px solid gray !important'),
                       ('border-bottom', '3px solid gray !important')]},

            # 본문 (2행 이후) 우측 정렬
            {'selector': 'tbody tr:nth-child(n+2) td',
             'props': [('text-align', 'right'), ('padding', '6px 10px')]},

            # 구분 열 (2번째 td) 좌측 정렬
            {'selector': 'tbody tr td:nth-child(2)',
             'props': [('text-align', 'left'), ('white-space', 'nowrap')]},

            # 스페이서 열 (1번째 td)
            {'selector': 'tbody td:nth-child(1)',
             'props': [('width', '8px'), ('border-right', '0')]},
        ]

        # 외상매출금 소계 행 (3행 = hdr1행 + 원화 + 외화 → tbody 4번째)
        styles += [
            {'selector': 'tbody tr:nth-child(4) td',
             'props': [('font-weight', '600'), ('border-top', '2px solid #aaa')]},
        ]

        # 받을어음 소계 행 (7행)
        styles += [
            {'selector': 'tbody tr:nth-child(7) td',
             'props': [('font-weight', '600'), ('border-top', '2px solid #aaa')]},
        ]

        # 합계 행 (8행) - 굵은 하단 테두리
        styles += [
            {'selector': 'tbody tr:nth-child(8) td',
             'props': [('font-weight', '700'),
                       ('border-top', '2px solid #aaa'),
                       ('border-bottom', '3px solid gray !important')]},
        ]

        display_styled_df(disp_vis, styles=styles, already_flat=True)

    except Exception as e:
        st.error(f"외상매출금 및 받을어음 현황 표 생성 중 오류: {e}")