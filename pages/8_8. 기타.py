import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
import modules
import io
import re
from itertools import groupby
warnings.filterwarnings('ignore')
st.set_page_config(layout="wide", initial_sidebar_state="expanded")

import re, io, pandas as pd
from urllib.request import urlopen, Request


def rowspan_like_for_index(blocks, level=2, header_rows=1):
    styles = []
    to_nth = lambda r: r + header_rows + 1

    for start, end in blocks:
        top = to_nth(start)
        mid = [to_nth(r) for r in range(start + 1, end)]
        bot = to_nth(end)

        styles.append({
            'selector': f'tbody tr:nth-child({top}) th.row_heading.level{level}',
            'props': [('border-bottom', '0')]
        })
        for r in mid:
            styles.append({
                'selector': f'tbody tr:nth-child({r}) th.row_heading.level{level}',
                'props': [('border-top', '0'), ('border-bottom', '0'),
                          ('color', 'transparent'), ('text-shadow', 'none')]
            })
        styles.append({
            'selector': f'tbody tr:nth-child({bot}) th.row_heading.level{level}',
            'props': [('border-top', '0')]
        })
    return styles

def with_inline_header_row(df: pd.DataFrame,
                           index_names=('', '', '구분'),
                           index_values=('', '', '구분')) -> pd.DataFrame:
    if isinstance(df.index, pd.MultiIndex):
        df.index = df.index.set_names(index_names)
    else:
        df.index.name = index_names[-1]

    hdr = pd.DataFrame([list(df.columns)], columns=df.columns)
    if isinstance(df.index, pd.MultiIndex):
        hdr.index = pd.MultiIndex.from_tuples([index_values], names=index_names)
    else:
        hdr.index = pd.Index([index_values[-1]], name=index_names[-1])

    df2 = pd.concat([hdr, df], axis=0)
    return df2

def display_styled_df(
    df,
    styles=None,
    highlight_cols=None,
    already_flat=False,
    applymap_rules=None,
):
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
        .format(lambda x: f"{x:,.0f}" if isinstance(x, (int,float,np.integer,np.floating)) and pd.notnull(x) else x)
        .set_properties(**{'text-align':'right','font-family':'Noto Sans KR'})
        .apply(highlight_columns, axis=0)
        .hide(axis="index")
    )

    # 기본 검정선 + 추가 styles 합치기
    base_styles = [
        {'selector': 'th, td', 'props': [('border', '1px solid black')]},
        {'selector': 'table', 'props': [('border-collapse', 'collapse')]}
    ]
    all_styles = base_styles + (styles or [])
    styled_df = styled_df.set_table_styles(all_styles)

    if applymap_rules:
        for func, subset in applymap_rules:
            rows, cols = subset
            styled_df = styled_df.map(func, subset=pd.IndexSlice[rows, cols])

    st.markdown(
        f"<div style='display:flex;justify-content:left'>{styled_df.to_html()}</div>",
        unsafe_allow_html=True
    )


# =========================
# 날짜 선택 사이드바
# =========================
this_year = datetime.today().year
current_month = datetime.today().month

def _date_update_callback():
    st.session_state.year = st.session_state.year_selector
    st.session_state.month = st.session_state.month_selector

def create_sidebar():
    with st.sidebar:
        st.title("날짜 선택")
        if 'year' not in st.session_state:
            st.session_state.year = this_year
        if 'month' not in st.session_state:
            st.session_state.month = current_month

        st.selectbox('년(Year)', range(2020, 2031),
                     key='year_selector',
                     index=st.session_state.year - 2020,
                     on_change=_date_update_callback)

        st.selectbox('월(Month)', range(1, 13),
                     key='month_selector',
                     index=st.session_state.month - 1,
                     on_change=_date_update_callback)

        st.info(f"선택된 날짜: {st.session_state.year}년 {st.session_state.month}월")

create_sidebar()

# =========================
# 안전 로더
# =========================
@st.cache_data(ttl=1800)
def load_f40(url: str) -> pd.DataFrame:
    df = pd.read_csv(url, dtype=str)

    if '실적' in df.columns:
        s = df['실적'].str.replace(',', '', regex=False)
        df['실적'] = pd.to_numeric(s, errors='coerce').fillna(0.0)
    else:
        df['실적'] = 0.0

    if '월' in df.columns:
        m = (df['월'].astype(str).str.replace('월', '', regex=False)
             .str.replace('.', '', regex=False).str.strip()
             .replace({'': np.nan, 'nan': np.nan, 'None': np.nan, 'NULL': np.nan}))
        df['월'] = pd.to_numeric(m, errors='coerce').astype('Int64')
    else:
        df['월'] = pd.Series([pd.NA] * len(df), dtype='Int64')

    if '연도' in df.columns:
        y = (df['연도'].astype(str).str.extract(r'(\d{4}|\d{2})')[0]
             .replace({'': np.nan, 'nan': np.nan, 'None': np.nan, 'NULL': np.nan}))
        y = y.apply(lambda v: f"20{v}" if isinstance(v, str) and len(v) == 2 else v)
        df['연도'] = pd.to_numeric(y, errors='coerce').astype('Int64')
    else:
        df['연도'] = pd.Series([pd.NA] * len(df), dtype='Int64')

    for c in ['구분1', '구분2', '구분3', '구분4']:
        if c in df.columns:
            df[c] = df[c].fillna('').astype(str)
        else:
            df[c] = ''
    return df

@st.cache_data(ttl=1800)
def load_defect(url: str) -> pd.DataFrame:
    df = pd.read_csv(url, dtype=str)
    for c in ['연도', '월', '실적']:
        df[c] = pd.to_numeric(df.get(c), errors='coerce')
    for c in ['구분1', '구분2', '구분3', '구분4']:
        if c in df.columns:
            df[c] = df[c].fillna('').astype(str)
        else:
            df[c] = ''
    return df

# =========================
# UI 본문
# =========================
year = int(st.session_state['year'])
month = int(st.session_state['month'])

st.markdown(f"## {year}년 {month}월 기타")

t1, = st.tabs(['1. 인원현황'])

with t1:
    st.markdown("<h4>1) 인원현황 </h4>", unsafe_allow_html=True)
    st.markdown(
        "<div style='text-align:left; font-size:13px; color:#666;'>[단위: 명]</div>",
        unsafe_allow_html=True,
    )

    try:
        file_name = st.secrets["sheets"]["f_60"]
        df_src = pd.read_csv(file_name, dtype=str)

        sel_y = int(st.session_state["year"])
        sel_m = int(st.session_state["month"])

        disp_raw, meta = modules.build_table_60(df_src, sel_y, sel_m)

        base_cols = meta["cols"]
        hdr1 = meta["hdr1"]

        # ✅ 구분1, 구분2 하나의 구분 컬럼으로 합치기
        disp = disp_raw.copy()
        disp["구분"] = disp.apply(
            lambda row: row["구분1"] if str(row["구분2"]).strip() == "" else row["구분2"],
            axis=1
        )
        disp = disp.drop(columns=["구분1", "구분2"])
        num_cols = [c for c in disp.columns if c != "구분"]
        disp = disp[["구분"] + num_cols]

        cols = disp.columns.tolist()

        # ✅ 헤더 1줄 (구분1/구분2 합쳤으므로 hdr1에서 첫 두 항목 합치기)
        hdr1_merged = ["구분"] + hdr1[2:]  # "구분", "" 두 개 → "구분" 하나로
        hdr_df = pd.DataFrame([hdr1_merged], columns=cols)
        disp_vis = pd.concat([hdr_df, disp], ignore_index=True)

        # ==== 2. 숫자 포맷 ====
        def fmt_num(v):
            if pd.isna(v):
                return ""
            try:
                iv = int(round(float(v)))
            except:
                return v
            return f"{iv:,}"

        def fmt_diff(v):
            if pd.isna(v):
                return ""
            try:
                iv = int(round(float(v)))
            except:
                return v
            if iv < 0:
                return f'<span style="color:red;">-{abs(iv):,}</span>'
            if iv > 0:
                return f"{iv:,}"
            return "0"

        body = disp_vis.copy()
        data_rows = body.index[1:]  # 앞 1줄만 헤더

        diff_cols = ["mom_diff", "plan_diff"]

        for c in num_cols:
            body.loc[data_rows, c] = body.loc[data_rows, c].apply(
                fmt_diff if c in diff_cols else fmt_num
            )

        # ==== 3. 스타일 ====
        styles = [
            {"selector": "thead", "props": [("display", "none")]},
            {
                "selector": "tbody tr:nth-child(1) td",
                "props": [("text-align", "center"), ("font-weight", "700"),
                          ("border-bottom", "2px solid black !important")]
            },
            {
                "selector": "tbody tr:nth-child(n+2) td:nth-child(1)",
                "props": [("text-align", "left"), ("white-space", "nowrap")]
            },
            {
                "selector": "tbody tr:nth-child(n+2) td:nth-child(n+2)",
                "props": [("text-align", "right")]
            },
        ]

        display_styled_df(body, styles=styles, already_flat=True)

    except Exception as e:
        st.error(f"인원현황 표 생성 오류: {e}")

    st.divider()


# Footer
st.markdown("""
<style>.footer { bottom: 0; left: 0; right: 0; padding: 8px; text-align: center; font-size: 13px; color: #666666;}</style>
<div class="footer">ⓒ 2025 SeAH Special Steel Corp. All rights reserved.</div>
""", unsafe_allow_html=True)