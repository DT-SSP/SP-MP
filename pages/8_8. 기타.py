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

# =========================
# 공통 테이블 렌더 (인덱스 숨김 + 중복 컬럼 안전)
# =========================


import re, io, pandas as pd
from urllib.request import urlopen, Request






def rowspan_like_for_index(blocks, level=2, header_rows=1):
    """
    멀티인덱스(행) 열에서, 연속된 행들을 '한 칸처럼' 보이게 하는 CSS 스타일을 만들어줍니다.
    - blocks: [(start_data_row, end_data_row), ...]  # 데이터 기준 0-based, 양끝 포함
    - level:  대상 인덱스 레벨 번호 (구분 레벨이 보통 2)
    - header_rows: tbody 위에 끼운 가짜 헤더 수(보통 1)
    반환: set_table_styles에 append할 dict 리스트
    """
    styles = []
    to_nth = lambda r: r + header_rows + 1  # 0-based 데이터행 → tbody nth-child(1-based)

    for start, end in blocks:
        top = to_nth(start)
        mid = [to_nth(r) for r in range(start + 1, end)]
        bot = to_nth(end)

        # 시작행: 아래 경계 제거
        styles.append({
            'selector': f'tbody tr:nth-child({top}) th.row_heading.level{level}',
            'props': [('border-bottom', '0')]
        })
        # 중간행들: 위/아래 경계 제거 + 텍스트 숨김
        for r in mid:
            styles.append({
                'selector': f'tbody tr:nth-child({r}) th.row_heading.level{level}',
                'props': [('border-top', '0'), ('border-bottom', '0'),
                          ('color', 'transparent'), ('text-shadow', 'none')]
            })
        # 끝행: 위 경계 제거
        styles.append({
            'selector': f'tbody tr:nth-child({bot}) th.row_heading.level{level}',
            'props': [('border-top', '0')]
        })
    return styles

def with_inline_header_row(df: pd.DataFrame,
                           index_names=('', '', '구분'),
                           index_values=('', '', '구분')) -> pd.DataFrame:
    """
    멀티인덱스(행) 위에 '같은 행 높이'로 컬럼명을 보여주기 위해
    본문 첫 행에 '헤더용 가짜 행'을 삽입한다.
    - index_names: df.index.names 를 덮어쓸 이름 (마지막만 '구분'으로 보이게)
    - index_values: 가짜 행의 인덱스 값 튜플 (마지막 칸에 '구분' 텍스트 배치)
    """
    # 1) 원본 인덱스 이름 정리
    if isinstance(df.index, pd.MultiIndex):
        df.index = df.index.set_names(index_names)
    else:
        df.index.name = index_names[-1]

    # 2) 헤더용 1행(컬럼명 그대로 출력) 만들기
    hdr = pd.DataFrame([list(df.columns)], columns=df.columns)
    if isinstance(df.index, pd.MultiIndex):
        hdr.index = pd.MultiIndex.from_tuples([index_values], names=index_names)
    else:
        hdr.index = pd.Index([index_values[-1]], name=index_names[-1])

    # 3) 본문 위에 합치기 (hdr가 첫 행이 됨)
    df2 = pd.concat([hdr, df], axis=0)
    return df2

def display_styled_df(
    df,
    styles=None,
    highlight_cols=None,
    already_flat=False,
    applymap_rules=None, 
):
    """
    - already_flat=True: df가 이미 index 없는 평평한 형태(= reset_index 완료)라고 가정
    - applymap_rules: [(func, (row_indexer, col_indexer)), ...]
        * row_indexer, col_indexer는 '라벨 기반' 인덱서(= df.index/df.columns에서 뽑은 값)여야 함
        * 예) [(neg_red_func, (df.index[2:], df.columns[4:]))]
    """


    if already_flat:
        df_for_style = df.copy()
    else:
        df_for_style = df.reset_index()

    # (중복 컬럼명 고유화)
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

    if styles:
        styled_df = styled_df.set_table_styles(styles)

    if applymap_rules:
        for func, subset in applymap_rules:
            rows, cols = subset  # 라벨 기반 인덱서여야 함
            styled_df = styled_df.applymap(func, subset=pd.IndexSlice[rows, cols])

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
# 안전 로더 (원본 '톤' 단위 그대로)
# =========================
@st.cache_data(ttl=1800)
def load_f40(url: str) -> pd.DataFrame:
    df = pd.read_csv(url, dtype=str)

    # 실적 → float
    if '실적' in df.columns:
        s = df['실적'].str.replace(',', '', regex=False)
        df['실적'] = pd.to_numeric(s, errors='coerce').fillna(0.0)
    else:
        df['실적'] = 0.0

    # 월 → Int64
    if '월' in df.columns:
        m = (df['월'].astype(str).str.replace('월', '', regex=False)
             .str.replace('.', '', regex=False).str.strip()
             .replace({'': np.nan, 'nan': np.nan, 'None': np.nan, 'NULL': np.nan}))
        df['월'] = pd.to_numeric(m, errors='coerce').astype('Int64')
    else:
        df['월'] = pd.Series([pd.NA] * len(df), dtype='Int64')

    # 연도 → Int64 (2자리면 20xx)
    if '연도' in df.columns:
        y = (df['연도'].astype(str).str.extract(r'(\d{4}|\d{2})')[0]
             .replace({'': np.nan, 'nan': np.nan, 'None': np.nan, 'NULL': np.nan}))
        y = y.apply(lambda v: f"20{v}" if isinstance(v, str) and len(v) == 2 else v)
        df['연도'] = pd.to_numeric(y, errors='coerce').astype('Int64')
    else:
        df['연도'] = pd.Series([pd.NA] * len(df), dtype='Int64')

    # 구분 → 문자열
    for c in ['구분1', '구분2', '구분3', '구분4']:
        if c in df.columns:
            df[c] = df[c].fillna('').astype(str)
        else:
            df[c] = ''
    return df

@st.cache_data(ttl=1800)
def load_defect(url: str) -> pd.DataFrame:
    """부적합 데이터 로더"""
    df = pd.read_csv(url, dtype=str)
    # 숫자 형변환
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

t1,= st.tabs(['1. 인원현황'])




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
        hdr2 = meta["hdr2"]


        SPACER = "__sp__"
        disp = disp_raw.copy()
        disp.insert(0, SPACER, "")    

        cols = disp.columns.tolist()


        hdr1_ext = [""] + hdr1
        hdr2_ext = [""] + hdr2

        hdr_df = pd.DataFrame([hdr1_ext, hdr2_ext], columns=cols)
        disp_vis = pd.concat([hdr_df, disp], ignore_index=True)

        # ==== 2. 숫자 포맷 ====
        def fmt_num(v):
            if pd.isna(v):
                return ""
            iv = int(round(float(v)))
            return f"{iv:,}"

        def fmt_diff(v):
            if pd.isna(v):
                return ""
            iv = int(round(float(v)))
            if iv < 0:
                return f'<span style="color:#d62728;">({abs(iv):,})</span>'
            if iv > 0:
                return f"{iv:,}"
            return "0"

        body = disp_vis.copy()
        data_rows = body.index[2:]  # 앞 2줄은 헤더

        diff_cols = ["mom_diff", "plan_diff"]

        for c in base_cols[2:]:
            body.loc[data_rows, c] = body.loc[data_rows, c].apply(
                fmt_diff if c in diff_cols else fmt_num
            )

        # ==== 3. 스타일 ====
        styles = [
            {"selector": "thead", "props": [("display", "none")]},
            
            {
                'selector': 'tbody tr:nth-child(1) td',
                'props': [
                    ('border-top', '3px solid gray !important')
                ]
            },

            {
                "selector": "tbody tr td:nth-child(1)",
                "props": [
                    ("border-right", "2px solid white !important"),
                ],
            },


            # 1행/2행 헤더
            {
                "selector": "tbody tr:nth-child(1) td",
                "props": [("text-align", "center"), ("font-weight", "700")],
            },
            {
                "selector": "tbody tr:nth-child(2) td",
                "props": [
                    ("text-align", "center"),
                    ("font-weight", "700"),
                    ("border-bottom", "3px solid gray !important"),
                ],
            },

            # 3행 이후: 구분1(2열), 구분2(3열)만 왼쪽 정렬
            {
                "selector": "tbody tr:nth-child(n+3) td:nth-child(2),"
                            "tbody tr:nth-child(n+3) td:nth-child(3)",
                "props": [
                    ("text-align", "left"),
                    ("white-space", "nowrap"),
                ],
            },

            # 3행 이후: 4열부터(실제 숫자 시작) 오른쪽 정렬
            {
                "selector": "tbody tr:nth-child(n+3) td:nth-child(n+4)",
                "props": [("text-align", "right")],
            },

            {
                "selector": "tbody tr td:nth-child(3)",
                "props": [
                    ("border-right", "3px solid gray !important"),
                ],
            },
        ]

        spacer_rules1 = [
            {
                'selector': f'tbody tr:nth-child({r})',
                'props': [('border-bottom','3px solid gray !important')]
               
            }
            for r in (3,8,13,18,23,26,27)

        ]

        styles += spacer_rules1

        spacer_rules2 = [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child({i})',
                'props': [('border-bottom','2px solid white !important')]
               
            }
            for r in (4,5,6,7,9,10,11,12,14,15,16,17,19,20,21,22,24,25)
            for i in (1,2)
        ]

        styles += spacer_rules2

        spacer_rules2 = [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child(2)',
                'props': [('border-right','3px solid gray !important')]
               
            }
            for r in (4,5,6,7,9,10,11,12,14,15,16,17,19,20,21,22,24,25)

        ]

        styles += spacer_rules2

        spacer_rules2 = [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child(3)',
                'props': [('border-bottom','3px solid gray !important')]
               
            }
            for r in (7,12,17,22,25)

        ]

        styles += spacer_rules2

        for i in [7,12,17,22,25,26,27]:
            body.iloc[i, 2] = ""

        display_styled_df(body, styles=styles, already_flat=True)

    except Exception as e:
        st.error(f"인원현황 표 생성 오류: {e}")

    st.divider()


# Footer
st.markdown("""
<style>.footer { bottom: 0; left: 0; right: 0; padding: 8px; text-align: center; font-size: 13px; color: #666666;}</style>
<div class="footer">ⓒ 2025 SeAH Special Steel Corp. All rights reserved.</div>
""", unsafe_allow_html=True)