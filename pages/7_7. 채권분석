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

    # [문제2 수정] 단위 표시를 표 제목 바로 아래, 우측 정렬
    st.markdown(
        "<div style='text-align:right; font-size:13px; color:#666;'>[단위 : 억원, %]</div>",
        unsafe_allow_html=True,
    )

    try:
        file_name = st.secrets['sheets']['f_56']
        raw = pd.read_csv(file_name, dtype=str)

        # ── [문제1 수정] 데이터 컬럼 확인 후 필터 키 자동 탐지 ──
        # 어떤 컬럼에 원화/외화/자수/타수가 들어있는지 확인
        item_col = None
        for c in ['구분2', '구분1', '구분3']:
            if c in raw.columns:
                unique_vals = raw[c].astype(str).str.strip().unique().tolist()
                if any(v in unique_vals for v in ['원화', '외화', '자수', '타수']):
                    item_col = c
                    break

        if item_col is None:
            st.error("데이터에서 원화/외화/자수/타수 항목을 찾을 수 없습니다. 컬럼명을 확인하세요.")
            st.stop()

        # 공백 제거
        raw[item_col] = raw[item_col].astype(str).str.strip()

        # 숫자 변환
        raw['연도'] = pd.to_numeric(raw['연도'], errors='coerce').astype('Int64')
        raw['월']   = pd.to_numeric(raw['월'],   errors='coerce').astype('Int64')
        raw['실적'] = pd.to_numeric(
            raw['실적'].astype(str).str.replace(',', '', regex=False).str.strip(),
            errors='coerce'
        ).fillna(0.0)

        # ── 열 구성: 연말 2개 + 최근 3개월 ──
        def prev_month(y, m, n):
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

        # 중복 라벨 방지 (연말이 월별과 겹칠 경우 ex. 선택월=12월)
        seen_labels, unique_specs = {}, []
        for spec in col_specs:
            label = spec[2]
            if label not in seen_labels:
                seen_labels[label] = True
                unique_specs.append(spec)
        col_specs = unique_specs
        col_labels = [s[2] for s in col_specs]

        # ── 값 조회 함수 ──
        def get_val(item, y, m):
            mask = (
                (raw[item_col] == item) &
                (raw['연도']   == y) &
                (raw['월']     == m)
            )
            vals = raw.loc[mask, '실적']
            if vals.empty:
                return 0.0
            return float(vals.sum()) / 1e8   # 원 → 억원

        # ── 각 항목 데이터 수집 ──
        target_items = ['원화', '외화', '자수', '타수']
        raw_data = {}
        for item in target_items:
            raw_data[item] = {label: get_val(item, y, m) for (y, m, label) in col_specs}

        # 소계 / 합계 계산
        subtotal_ar   = {l: raw_data['원화'][l] + raw_data['외화'][l] for l in col_labels}
        subtotal_note = {l: raw_data['자수'][l] + raw_data['타수'][l] for l in col_labels}
        grand_total   = {l: subtotal_ar[l] + subtotal_note[l] for l in col_labels}

        # 구성(%) 기준: 기준월 합계
        base_total = grand_total[col_labels[-1]] if grand_total[col_labels[-1]] != 0 else 1

        def composition(val):
            return f"{round(val / base_total * 100)}%"

        def fmt(v):
            if v == 0:
                return ""
            return f"{int(round(v)):,}"

        def make_row(label, data_dict, comp_val=None):
            row = {'구분': label}
            for l in col_labels:
                row[l] = fmt(data_dict[l])
            row['구성'] = composition(comp_val) if comp_val is not None else ""
            return row

        table_data = [
            make_row('원화',       raw_data['원화'],  comp_val=raw_data['원화'][col_labels[-1]]),
            make_row('외화',       raw_data['외화'],  comp_val=raw_data['외화'][col_labels[-1]]),
            make_row('외상매출금', subtotal_ar,       comp_val=subtotal_ar[col_labels[-1]]),
            make_row('자수',       raw_data['자수'],  comp_val=raw_data['자수'][col_labels[-1]]),
            make_row('타수',       raw_data['타수'],  comp_val=raw_data['타수'][col_labels[-1]]),
            make_row('받을어음',   subtotal_note,     comp_val=subtotal_note[col_labels[-1]]),
            make_row('합계',       grand_total,       comp_val=grand_total[col_labels[-1]]),
        ]

        disp = pd.DataFrame(table_data)

        # [문제3 수정] 스페이서 컬럼 제거 → 구분 열이 첫 번째 열
        cols = disp.columns.tolist()
        c_idx = {c: i for i, c in enumerate(cols)}

        # ── 헤더 행 ──
        hdr = [''] * len(cols)
        hdr[c_idx['구분']] = '구분'
        for l in col_labels:
            hdr[c_idx[l]] = l
        hdr[c_idx['구성']] = '구성'

        hdr_df   = pd.DataFrame([hdr], columns=cols)
        disp_vis = pd.concat([hdr_df, disp], ignore_index=True)

        # [문제4 수정] 표 내부 선을 겉 테두리와 동일하게 통일
        styles = [
            {'selector': 'thead', 'props': [('display', 'none')]},
            {'selector': 'table', 'props': [('border-collapse', 'collapse'), ('width', '100%')]},

            # 모든 셀 테두리 통일
            {'selector': 'tbody td',
             'props': [('border', '1px solid #333'), ('padding', '6px 10px')]},

            # 헤더 행 (1번째)
            {'selector': 'tbody tr:nth-child(1) td',
             'props': [('text-align', 'center'), ('font-weight', '700'),
                       ('padding', '8px 8px'),
                       ('border-top', '3px solid #333 !important'),
                       ('border-bottom', '3px solid #333 !important')]},

            # 본문 (2행 이후) 우측 정렬
            {'selector': 'tbody tr:nth-child(n+2) td',
             'props': [('text-align', 'right'), ('padding', '6px 10px')]},

            # 구분 열 좌측 정렬
            {'selector': 'tbody tr td:nth-child(1)',
             'props': [('text-align', 'left'), ('white-space', 'nowrap')]},
        ]

        # 외상매출금 소계 행 (tbody 4번째: hdr + 원화 + 외화 + 외상매출금)
        styles += [
            {'selector': 'tbody tr:nth-child(4) td',
             'props': [('font-weight', '700'),
                       ('border-top', '2px solid #333 !important'),
                       ('border-bottom', '2px solid #333 !important')]},
        ]

        # 받을어음 소계 행 (tbody 7번째)
        styles += [
            {'selector': 'tbody tr:nth-child(7) td',
             'props': [('font-weight', '700'),
                       ('border-top', '2px solid #333 !important'),
                       ('border-bottom', '2px solid #333 !important')]},
        ]

        # 합계 행 (tbody 8번째)
        styles += [
            {'selector': 'tbody tr:nth-child(8) td',
             'props': [('font-weight', '700'),
                       ('border-top', '2px solid #333 !important'),
                       ('border-bottom', '3px solid #333 !important')]},
        ]

        display_styled_df(disp_vis, styles=styles, already_flat=True)

    except Exception as e:
        st.error(f"외상매출금 및 받을어음 현황 표 생성 중 오류: {e}")