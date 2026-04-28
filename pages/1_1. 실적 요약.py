import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
import modules  

warnings.filterwarnings('ignore')
st.set_page_config(layout="wide", initial_sidebar_state="expanded")

# =========================
# 공통 테이블 렌더 (인덱스 숨김 + 중복 컬럼 안전)
# =========================
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

def display_styled_df(df, styles=None, highlight_cols=None, already_flat=False):
    """
    - already_flat=True: df가 이미 index 없는 평평한 형태(= reset_index 완료)라고 가정
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

    st.markdown(styled_df.to_html(), unsafe_allow_html=True)


##### 메모 #####
def create_indented_html(s):
    """문자열의 앞 공백을 기반으로 들여쓰기된 HTML <p> 태그를 생성합니다."""
    content = s.lstrip(' ')
    num_spaces = len(s) - len(content)
    indent_level = num_spaces // 2
    return f'<p class="indent-{indent_level}">{content}</p>'



def display_memo(memo_file_key, year, month,):
    """메모 파일 키와 년/월을 받아 해당 메모를 화면에 표시합니다."""
    file_name = st.secrets['memos'][memo_file_key]
    try:
        df_memo = pd.read_csv(file_name)

        # 년도/월 기준으로 필터
        df_filtered = df_memo[(df_memo['년도'] == year) & (df_memo['월'] == month)]

        if df_filtered.empty:
            st.warning(f"{year}년 {month}월 메모를 찾을 수 없습니다.")
            return

        # 여러 행이 있을 경우, 일단 첫 번째 행 사용 (원하면 join 가능)
        memo_text = df_filtered.iloc[0]['메모']

        # 기존 로직 유지
        str_list = memo_text.split('\n')
        html_items = [create_indented_html(s) for s in str_list]
        body_content = "".join(html_items)

        html_code = f"""
        <style>
            .memo-body {{
                font-family: 'Noto Sans KR', sans-serif;
                word-spacing: 5px;
            }}
            .memo-body .indent-0 {{ padding-left: 0px; padding-top: 10px; text-indent: -30px; font-size: 17px; font-weight: bold; }}
            .memo-body .indent-1 {{ padding-left: 20px; padding-top: 5px; text-indent: -10px; font-size: 17px; }}
            .memo-body .indent-2 {{ padding-left: 40px; font-size: 17px; }}
            .memo-body .indent-3 {{ padding-left: 60px; font-size: 12px; }}
            .memo-body p {{ margin: 0.2rem 0; }}
        </style>
        <div class="memo-body">{body_content}</div>
        """
        st.markdown(html_code, unsafe_allow_html=True)

    except (FileNotFoundError, KeyError):
        st.warning(f"메모 파일을 찾을 수 없습니다: {memo_file_key}")

####################


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

st.markdown(f"## {year}년 {month}월 실적 요약")
t1, t2, t3 = st.tabs(['주요경영지표', '주요경영지표(본사)', '연간사업계획'])
st.divider()

# =========================
# 주요경영지표
# =========================

with t1:
    st.markdown("<h4>1) 손익 (연결) </h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 톤, 백만원, %]</div>", unsafe_allow_html=True)

    try:
        file_name = st.secrets["sheets"]["f_1"]
        df_src = pd.read_csv(file_name)

        base = modules.create_connected_profit(
            year=int(st.session_state['year']),
            month=int(st.session_state['month']),
            data=df_src
        )

        # ===== 표시용 DF 준비 =====
        # 인덱스(% → '%')를 '구분' 컬럼으로 빼기
        disp = base.copy()
        disp.insert(0, '구분', disp.index.map(lambda x: '%' if str(x).startswith('%') else x))
        disp = disp.reset_index(drop=True)

        cols = disp.columns.tolist()
        c_idx = {c: i for i, c in enumerate(cols)}

        # ===== 3단 가짜 헤더 생성 =====
        hdr1 = [''] * len(cols)  # 1행: 전전월/전월/당월/계획대비 라벨
        hdr2 = [''] * len(cols)  # 2행: 본사/중국/태국
        hdr3 = [''] * len(cols)  # 3행: 남통/천진

        # 1행: 전전월 실적 ~ 계획 대비
        for c in ['구분','전전월 실적', '전월 실적', '당월 계획', '당월 실적','본사', '중국', '태국', '전월 실적 대비', '계획 대비']:
            if c in c_idx:
                hdr1[c_idx[c]] = c



        # 3행: 남통, 천진
        for c in ['남통', '천진']:
            if c in c_idx:
                hdr2[c_idx[c]] = c

        hdr_df   = pd.DataFrame([hdr1, hdr2], columns=cols)
        disp_vis = pd.concat([hdr_df, disp], ignore_index=True)  

        # ===== 스타일 / 하이라이트 =====
        highlight_cols = ['전월 실적', '당월 계획', '당월 실적', '전월 실적 대비', '계획 대비']

        styles = [

            {'selector': 'thead', 'props': [('display', 'none')]},

            # 1행
            {'selector': 'tbody tr:nth-child(1) td',
             'props': [('text-align','center'),
                       ('padding','8px 8px'),
                       ('line-height','1.2'),
                       ('font-weight','600')]},

            # 2행
            {'selector': 'tbody tr:nth-child(2) td',
             'props': [('text-align','center'),
                       ('padding','10px 8px'),
                       ('line-height','1'),
                       ('font-weight','600')]},


        ]

        spacer_rules1 = [
            {
                'selector': f'tbody tr:nth-child({r})',
                'props': [('border-top','3px solid gray !important')]
               
            }
            for r in (1,3)

        ]

        styles += spacer_rules1



        spacer_rules2 = [
            {
                'selector': f' td:nth-child(1)',
                'props': [('border-right','2px solid gray !important')]
               
            }

        ]

        styles += spacer_rules2

        spacer_rules2 = [
            {
                'selector': f'tbody tr:nth-child(1) td:nth-child({r})',
                'props': [('border-right','3px solid gray !important')]
               
            }
            for r in (5,6,9,10)
        ]

        styles += spacer_rules2

        spacer_rules2 = [
            {
                'selector': f'tbody tr:nth-child(2) td:nth-child({r})',
                'props': [('border-right','3px solid gray !important')]
               
            }
            for r in (5,6,7,9,10)
        ]

        styles += spacer_rules2

        spacer_rules2 = [
            {
                'selector': f'tbody tr:nth-child(2) td:nth-child({r})',
                'props': [('border-top','3px solid gray !important')]
               
            }
            for r in (8,9)
        ]

        styles += spacer_rules2

        spacer_rules2 = [
            {
                'selector': f'tbody tr:nth-child(1) td:nth-child({r})',
                'props': [('border-right','2px solid white !important')]
               
            }
            for r in (7,8)
        ]

        styles += spacer_rules2

        


        display_styled_df(
            disp_vis,
            styles=styles,
            already_flat=True,

        )

        st.caption("각 %는 계산")
        display_memo('f_1', year, month)

    except Exception as e:
        st.error(f"손익 연결 생성 중 오류: {e}")

    st.divider()


    ##### no2 현금흐름표 #####

    st.markdown("<h4>2) 현금흐름표</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 백만원]</div>", unsafe_allow_html=True)

    try:
        file_name = st.secrets["sheets"]["f_2"]  
        raw = pd.read_csv(file_name, dtype=str)

        # ─ 연산(구분 기준) ─
        base = modules.create_cashflow_by_gubun(
            year=int(st.session_state['year']),
            month=int(st.session_state['month']),
            data=raw
        )

        # ─ 표시용 숫자 포맷 ─
        def fmt_cell(x):
            if pd.isna(x):
                return ""
            try:
                v = float(x)
            except Exception:
                return x
            return f"({abs(int(round(v))):,})" if v < 0 else f"{int(round(v)):,}"

        disp = base.copy().fillna(0)
        for c in disp.columns:
            disp[c] = disp[c].apply(fmt_cell)

        # ─ 구분을 2열로: 스페이서 컬럼 추가 ─
        disp = disp.reset_index()   # '구분' 컬럼 생성
        SPACER_COL = "__spacer__"
        disp.insert(0, SPACER_COL, "")

        # ─ 3단 헤더 구성 ─
        cols = disp.columns.tolist()
        c_idx = {c: i for i, c in enumerate(cols)}   # 라벨→0-based

        month_i = c_idx['당월']
        acc_i   = c_idx['당월누적']

        # 🔹 연도 컬럼 자동 탐색: "'25", "'26" 같은 것들
        year_cols = [c for c in cols if isinstance(c, str) and c.startswith("'")]
        year_cols_sorted = sorted(year_cols, key=lambda s: int(s[1:])) if year_cols else []

        # 전년도 누계 컬럼 (modules 쪽에서 prev_full_year = year-1)
        prev_year_col = year_cols_sorted[0] if year_cols_sorted else None
        # 선택연도 전월누계 컬럼 (보통 두 번째)
        curr_prev_cum_col = year_cols_sorted[-1] if len(year_cols_sorted) >= 2 else prev_year_col

        cur_y = int(st.session_state['year'])
        cur_m = int(st.session_state['month'])

        # (전월, 당월) 쌍 계산 (기존 로직 그대로)
        month_pairs = []
        for k in (1, 0):   # 1: 전월, 0: 당월
            y0 = cur_y
            m0 = cur_m - k
            while m0 <= 0:
                y0 -= 1
                m0 += 12
            month_pairs.append((y0, m0))

        (prev_y, prev_m), (used_y, used_m) = month_pairs

        # 헤더에 쓸 라벨
        top_label = f"'{str(used_y)[-2:]} {used_m}월"   # 당월 상단 라벨
        prev_text = f"'{str(prev_y)[-2:]} {prev_m}월"   # 전월 라벨

        hdr1 = [''] * len(cols)
        hdr2 = [''] * len(cols)
        hdr3 = [''] * len(cols)

        # 1행: 상단 그룹 (당월 쪽에만 표시)
        hdr1[month_i] = top_label

        # 2행: 구분 + 전년도 누계 + 전월누계 + 당월 + 누적
        hdr2[c_idx['구분']] = '구분'

        # 전년도 누계 컬럼 라벨 (예: '25)
        if prev_year_col is not None:
            hdr2[c_idx[prev_year_col]] = prev_year_col

        # 전월 누계 컬럼 라벨 (예: '26 4월)
        if curr_prev_cum_col is not None:
            hdr2[c_idx[curr_prev_cum_col]] = prev_text

        hdr2[month_i] = '당월'
        hdr2[acc_i]   = '당월누적'

        # 3행: 회사 라벨
        for k in ['본사','남통','천진','태국']:
            if k in c_idx:
                hdr3[c_idx[k]] = k

        hdr_df   = pd.DataFrame([hdr1, hdr2, hdr3], columns=cols)
        disp_vis = pd.concat([hdr_df, disp], ignore_index=True)

        # 회사 마지막 열 위치(경계선용)
        company_idxs = [c_idx[k] for k in ['본사','남통','천진','태국'] if k in c_idx]
        last_company_i = max(company_idxs) if company_idxs else month_i




        # ── CSS ──
        styles = [
            # 원래 thead 숨김
            {'selector': 'thead', 'props': [('display','none')]},

            # 헤더 1·2·3행
            {'selector': 'tbody tr:nth-child(1) td', 'props': [('text-align','center'), ('padding','8px 8px'),  ('line-height','1.2'), ('font-weight','600')]},
            {'selector': 'tbody tr:nth-child(2) td', 'props': [('text-align','center'), ('padding','10px 8px'), ('line-height','1'), ('font-weight','600')]},
            {'selector': 'tbody tr:nth-child(2) td:nth-child(2)', 'props': [('text-align','center')]},
            {'selector': 'tbody tr:nth-child(3) td', 'props': [('text-align','center'), ('padding','10px 8px'), ('line-height','1.2'), ('font-weight','600')]},

            # 스페이서 열 전체(모든 행)
            {'selector': 'tbody td:nth-child(1)', 'props': [('width','8px'), ('border-right','0')]},
            


            {'selector': 'tbody td:nth-child(4) td:nth-child(1)',
            'props': [('border-top','3px solid gray !important')]},


            {'selector': 'tbody td:nth-child(1)',
            'props': [('border-right','2px solid white !important')]},




            

        ]

        spacer_rules1 = [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child(2)',
                'props': [('text-align','left')]
               
            }
            for r in (4,5,6,9,15,16,17,20,24,25,26,27)
        ]

        styles += spacer_rules1

        spacer_rules2 = [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child(1)',
                'props': [('border-right','3px solid gray !important')]
               
            }
            for r in (5,6,7,8,9,10,11,12,13,14,15,16,18,19,21,22,23)
        ]

        styles += spacer_rules2

        spacer_rules2_1 = [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child(1)',
                'props': [('border-bottom','2px solid white !important')]
               
            }
            for r in (4,5,6,7,8,9,10,11,12,13,14,15,17,18,20,21,22)
            # for r in (5,6)
        ]

        styles += spacer_rules2_1
        
        spacer_rules3 = [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child(2)',
                'props': [('border-top','3px solid gray !important')]
               
            }

            for r in (4,5,6,9,15,16,17,18,19,20,21,24,25,26,27)
        ]

        styles += spacer_rules3
        
        spacer_rules3_1 = [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child(1)',
                'props': [('border-top','3px solid gray !important')]
               
            }

            for r in (4,17,20,24,25,26,27)
        ]

        styles += spacer_rules3_1



        spacer_rules4 = [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child(2)',
                'props': [('border-top','2px solid white !important')]
               
            }

            for r in (7,8,10,11,12,13,14,19,22,23)
        ]

        styles += spacer_rules4


        ####feature 구분####

        #행 구분

        spacer_rules5 = [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child({j})',
                'props': [('border-top','2px solid white ')]
               
            }
            # for r in (4,5,8,14,15)
            for r in (2,3)
            for j in (1,2,3,4)
        ]


        styles += spacer_rules5

        spacer_rules5 = [
            {
                'selector': f'tbody tr:nth-child(2) td:nth-child(10)',
                'props': [('border-top','3px solid gray ')]
               
            }


        ]
        

        styles += spacer_rules5

        spacer_rules5 = [
            {
                'selector': f'tbody tr:nth-child(2) td:nth-child(5)',
                'props': [('border-top','2px solid white ')]
               
            }


        ]
        

        styles += spacer_rules5

        spacer_rules5 = [
            {
                'selector': f'tbody tr:nth-child(1) ',
                'props': [('border-top','3px solid gray ')]
               
            }


        ]
        

        styles += spacer_rules5




        spacer_rules5 = [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child(3)',
                'props': [('border-left','3px solid gray ')]
               
            }

            for r in range(4,28)
        ]
        

        styles += spacer_rules5


        spacer_rules5 = [
            {
                'selector': f'tbody tr:nth-child(3) td:nth-child({j})',
                'props': [('border-top','3px solid gray ')]
               
            }

            for j in range (6,10)
        ]

        styles += spacer_rules5

        spacer_rules5 = [
            {
                'selector': f'tbody tr:nth-child(4) td:nth-child({j})',
                'props': [('border-top','3px solid gray ')]
               
            }

            for j in range(3,11)
        ]
        

        styles += spacer_rules5

        spacer_rules5 = [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child({j})',
                'props': [('border-right','3px solid gray ')]
               
            }

            for r in range (1,4)
            for j in range (2,5)
        ]
        styles += spacer_rules5


        spacer_rules5 = [
            {
                'selector': f'tbody tr:nth-child(1) td:nth-child(5)',
                'props': [('border-right','3px solid gray ')]
               
            }

        ]
        styles += spacer_rules5


        spacer_rules5 = [
            {
                'selector': f'tbody tr:nth-child(3) td:nth-child({j})',
                'props': [('border-top','2px solid white ')]
               
            }

            for j in (5,10)
        ]
        styles += spacer_rules5


        spacer_rules5 = [
            {
                'selector': f'tbody tr:nth-child(2) td:nth-child(5)',
                'props': [('border-right','3px solid gray ')],
                
            }



        ]
        styles += spacer_rules5

        spacer_rules5 = [
            {
                
                'selector': f'tbody tr:nth-child(2) td:nth-child(10)',
                'props': [('border-left','3px solid gray ')]
               
            }



        ]
        styles += spacer_rules5

        spacer_rules5 = [
            {
                'selector': f'tbody tr:nth-child(2) td:nth-child({j})',
                'props': [('border-right','2px solid white ')],
                
            }

            for j in range(6,9)



        ]
        styles += spacer_rules5


        spacer_rules5 = [
            {
                'selector': f'tbody tr:nth-child(1) td:nth-child({j})',
                'props': [('border-right','2px solid white ')],
                
            }

            for j in range(6,10)

        ]
        styles += spacer_rules5


        spacer_rules5 = [
            {
                'selector': f'tbody tr:nth-child(2) td:nth-child({j})',
                'props': [('border-top','2px solid white ')],
                
            }

            for j in range(6,10)

        ]
        styles += spacer_rules5

        
        display_styled_df(
            disp_vis,
            styles=styles,
            already_flat=True
        )
        display_memo('f_2', year, month)

    except Exception as e:
        st.error(f"현금흐름표 생성 중 오류: {e}")

    st.divider()


    ##### 재무상태표 #####


    st.markdown("<h4>3) 재무상태표</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 백만원]</div>", unsafe_allow_html=True)

    try:
        # 데이터 로드
        file_name = st.secrets["sheets"]["f_3"]
        raw = pd.read_csv(file_name, dtype=str)

        # 원하는 행 순서(=구분3 값)
        item_order = [
            '현금및현금성자산','매출채권','재고자산','유형자산','기타','자산총계',
            '매입채무','차입금','기타','부채총계',
            '자본금','이익잉여금','기타','자본총계','부채 및 자본 총계'
        ]

        # ─ 연산: 구분3만으로 집계 ─
        base = modules.create_bs_by_items(
            year=int(st.session_state['year']),
            month=int(st.session_state['month']),
            data=raw,
            item_order=item_order
        )

        # ─ 표시용 숫자 포맷 ─
        def fmt_cell(x):
            if pd.isna(x):
                return ""
            try:
                v = float(x)
            except Exception:
                return x
            return f"({abs(int(round(v))):,})" if v < 0 else f"{int(round(v)):,}"

        disp = base.copy().fillna(0)
        for c in disp.columns:
            disp[c] = disp[c].apply(fmt_cell)

        # ─ 구분을 2열로: 스페이서 컬럼 추가 ─
        disp = disp.reset_index()   # '구분' 컬럼 생성
        SPACER = "__spacer__"
        disp.insert(0, SPACER, "")

        cols = disp.columns.tolist()
        c_idx = {c: i for i, c in enumerate(cols)}

        gu_i    = c_idx['구분']
        month_i = c_idx['당월']
        diff_i  = c_idx['전월비 증감']

        year_cols = [c for c in cols if isinstance(c, str) and c.startswith("'")]


        prev_year_col = None
        prev_month_col = None
        if year_cols:

            year_cols_sorted = sorted(year_cols, key=len)
            prev_year_col = year_cols_sorted[0]
            if len(year_cols_sorted) > 1:
                prev_month_col = year_cols_sorted[1]
            else:
                prev_month_col = prev_year_col

        cur_y = int(st.session_state['year'])
        cur_m = int(st.session_state['month'])

        # 전월, 당월 (y,m) 쌍
        month_pairs = []
        for k in (1, 0):   # 1: 전월, 0: 당월
            y0 = cur_y
            m0 = cur_m - k
            while m0 <= 0:
                y0 -= 1
                m0 += 12
            month_pairs.append((y0, m0))

        (prev_y, prev_m), (used_y, used_m) = month_pairs

        # 헤더 라벨
        top_label = f"'{str(used_y)[-2:]} {used_m}월"    # 당월
        prev_text = f"'{str(prev_y)[-2:]} {prev_m}월"    # 전월

        # 회사 컬럼들: 스페이서/구분/연도/당월/전월비 증감 제외
        company_labels = [
            c for c in cols
            if c not in [SPACER, '구분', '당월', '전월비 증감'] and c not in year_cols
        ]

        # ─ 3단 헤더 ─
        # 1행: 상단 그룹 (당월 위치에만 표시)
        hdr1 = [''] * len(cols)
        hdr1[month_i] = top_label

        # 2행: '구분' + 전년도 + 전월 + 당월 + 전월비 증감
        hdr2 = [''] * len(cols)
        hdr2[gu_i] = '구분'
        if prev_year_col is not None:
            hdr2[c_idx[prev_year_col]] = prev_year_col
        if prev_month_col is not None:
            hdr2[c_idx[prev_month_col]] = prev_text
        hdr2[month_i] = '당월'
        hdr2[diff_i]  = '전월비 증감'

        # 3행: 회사 라벨
        hdr3 = [''] * len(cols)
        for k in company_labels:
            hdr3[c_idx[k]] = k

        hdr_df   = pd.DataFrame([hdr1, hdr2, hdr3], columns=cols)
        disp_vis = pd.concat([hdr_df, disp], ignore_index=True)

        # 회사 마지막 열 위치(경계선용)
        last_company_i = max((c_idx[k] for k in company_labels), default=month_i)


        # ─ CSS ─
        styles = [
            {'selector': 'thead', 'props': [('display','none')]},

            # 헤더 1·2·3행
            {'selector': 'tbody tr:nth-child(1) td', 'props': [('text-align','center'), ('padding','8px 8px'),  ('line-height','1.1'), ('font-weight','600')]},
            {'selector': 'tbody tr:nth-child(2) td', 'props': [('text-align','center'), ('padding','10px 8px'), ('line-height','1.4'), ('font-weight','600')]},
            {'selector': 'tbody tr:nth-child(2) td:nth-child(2)', 'props': [('text-align','center')]},
            {'selector': 'tbody tr:nth-child(3) td', 'props': [('text-align','center'), ('padding','14px 10px'), ('line-height','1.7'), ('font-weight','600')]},

            # 1열 얇게
            {'selector': 'tbody td:nth-child(1)', 'props': [('width','8px'), ('border-right','0')]},


            # 본문
            {'selector': 'tbody tr:nth-child(n+4) td', 'props': [('line-height','1.45'), ('padding','8px 10px'), ('text-align','right')]},
            {'selector': 'tbody tr:nth-child(n+4) td:nth-child(2)', 'props': [('text-align','left')]},
        ]

        spacer_rules1 = [
                    {
                        'selector': f'tbody tr:nth-child({r}) td:nth-child(2)',
                        'props': [('text-align','left')]
                    
                    }
                    for r in range(4,19)
                ]
        
        styles += spacer_rules1
        

        spacer_rules2 = [
                    {
                        'selector': f'tbody tr:nth-child({r}) td:nth-child(2)',
                        'props': [('border-left','3px solid gray ')],
                    
                    }
                    for r in (4,5,6,7,8,10,11,12,14,15,16)
                ]
        
        
        styles  += spacer_rules2

        spacer_rules2 = [
                    {
                        'selector': f'tbody tr:nth-child({r}) td:nth-child(2)',
                        'props': [('border-left','2px solid white ')],
                    
                    }
                    for r in (9,13,17,18)
                ]
        
        
        styles  += spacer_rules2

        spacer_rules3 = [
                    {
                        'selector': f'tbody tr:nth-child({r}) td:nth-child(2)',
                        'props': [('border-top','3px solid gray ')],
                    
                    }
                    for r in (9,10,13,14,17,18)
                ]
        
        styles  += spacer_rules3

        spacer_rules4 = [
                    {
                        'selector': f'tbody tr:nth-child({r}) td:nth-child(1)',
                        'props': [('border-bottom','2px solid white ')],
                    
                    }
                    for r in range(4,18)
                ]
        
        styles  += spacer_rules4

        spacer_rules5 = [
                    {
                        'selector': f'tbody tr:nth-child({r}) td:nth-child(1)',
                        'props': [('border-bottom','3px solid gray ')],
                    
                    }
                    for r in (3,9,13,17)
                ]
        
        styles  += spacer_rules5

        spacer_rules5 = [
                    {
                        'selector': f'tbody tr:nth-child(3) td:nth-child(2)',
                        'props': [('border-bottom','3px solid gray ')],
                    
                    }

                ]
        
        styles  += spacer_rules5        

        spacer_rules5 = [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child(3)',
                'props': [('border-left','3px solid gray ')]
               
            }

            for r in range(4,19)
        ]
        

        styles += spacer_rules5


        ####feature 구분####

        #행 구분

        spacer_rules5 = [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child({j})',
                'props': [('border-top','2px solid white ')]
               
            }
            # for r in (4,5,8,14,15)
            for r in (2,3)
            for j in (1,2,3,4)
        ]


        styles += spacer_rules5

        spacer_rules5 = [
            {
                'selector': f'tbody tr:nth-child(2) td:nth-child(10)',
                'props': [('border-top','3px solid gray ')]
               
            }


        ]
        

        styles += spacer_rules5

        spacer_rules5 = [
            {
                'selector': f'tbody tr:nth-child(2) td:nth-child(5)',
                'props': [('border-top','2px solid white ')]
               
            }


        ]
        

        styles += spacer_rules5

        spacer_rules5 = [
            {
                'selector': f'tbody tr:nth-child(1) ',
                'props': [('border-top','3px solid gray ')]
               
            }


        ]
        

        styles += spacer_rules5




        spacer_rules5 = [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child(3)',
                'props': [('border-left','3px solid gray ')]
               
            }

            for r in range(4,28)
        ]
        

        styles += spacer_rules5


        spacer_rules5 = [
            {
                'selector': f'tbody tr:nth-child(3) td:nth-child({j})',
                'props': [('border-top','3px solid gray ')]
               
            }

            for j in range (6,10)
        ]

        styles += spacer_rules5

        spacer_rules5 = [
            {
                'selector': f'tbody tr:nth-child(4) td:nth-child({j})',
                'props': [('border-top','3px solid gray ')]
               
            }

            for j in range(3,11)
        ]
        

        styles += spacer_rules5

        spacer_rules5 = [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child({j})',
                'props': [('border-right','3px solid gray ')]
               
            }

            for r in range (1,4)
            for j in range (2,5)
        ]
        styles += spacer_rules5


        spacer_rules5 = [
            {
                'selector': f'tbody tr:nth-child(1) td:nth-child(5)',
                'props': [('border-right','3px solid gray ')]
               
            }

        ]
        styles += spacer_rules5


        spacer_rules5 = [
            {
                'selector': f'tbody tr:nth-child(3) td:nth-child({j})',
                'props': [('border-top','2px solid white ')]
               
            }

            for j in (5,10)
        ]
        styles += spacer_rules5


        spacer_rules5 = [
            {
                'selector': f'tbody tr:nth-child(2) td:nth-child(5)',
                'props': [('border-right','3px solid gray ')],
                
            }



        ]
        styles += spacer_rules5

        spacer_rules5 = [
            {
                
                'selector': f'tbody tr:nth-child(2) td:nth-child(10)',
                'props': [('border-left','3px solid gray ')]
               
            }



        ]
        styles += spacer_rules5

        spacer_rules5 = [
            {
                'selector': f'tbody tr:nth-child(2) td:nth-child({j})',
                'props': [('border-right','2px solid white ')],
                
            }

            for j in range(6,9)



        ]
        styles += spacer_rules5


        spacer_rules5 = [
            {
                'selector': f'tbody tr:nth-child(1) td:nth-child({j})',
                'props': [('border-right','2px solid white ')],
                
            }

            for j in range(6,10)

        ]
        styles += spacer_rules5


        spacer_rules5 = [
            {
                'selector': f'tbody tr:nth-child(2) td:nth-child({j})',
                'props': [('border-top','2px solid white ')],
                
            }

            for j in range(6,10)

        ]
        styles += spacer_rules5


        spacer_rules5 = [
            {
                'selector': f'tbody tr:nth-child({j}) td:nth-child(1)',
                'props': [('border-right','2px solid white ')],
                
            }

            for j in range(1,4)

        ]
        styles += spacer_rules5

        






        display_styled_df(
            disp_vis,
            styles=styles,
            already_flat=True
        )

        display_memo('f_3', year, month)

    except Exception as e:
        st.error(f"재무상태표 생성 중 오류: {e}")
##


    st.divider()





    st.markdown(
        """
        <style>
        /* 메인 컨테이너를 왼쪽에 고정 + 최소 가로폭 지정 */
        .block-container {
            min-width: 1600px;                  /* 두 표 다 들어가는 최소 폭으로 조정 */
            margin-left: 0 !important;          /* 가운데 정렬 깨고 왼쪽에 딱 붙이기 */
            margin-right: auto !important;
        }

        /* 메인 영역에 가로 스크롤 허용 */
        .main {
            overflow-x: auto;
        }
        </style>
        """,
        unsafe_allow_html=True
    )


    col_left, col_mid, col_right = st.columns([1, 0.05, 1])

    with col_left:

        st.markdown("<h4>4) 회전일 (연결)</h4>", unsafe_allow_html=True)



        try:
            file_name = st.secrets["sheets"]["f_4"] 
            raw = pd.read_csv(file_name, dtype=str)

            # 최신 modules 반영
            import importlib
            importlib.invalidate_caches()
            importlib.reload(modules)

            # 1) 모듈 연산
            snap = modules.create_turnover(
                year=year,
                month=month,
                data=raw
            )

            # 2) 표시용 포맷
            def fmt1(x):
                try:
                    v = float(x)
                except Exception:
                    return x
                return f"{v:.1f}" if pd.notnull(v) else ""

            disp = snap.copy().applymap(fmt1)

            # 3) 인덱스를 컬럼으로, 스페이서 추가
            disp = disp.reset_index()
            SP = "__spacer__"
            disp.insert(0, SP, "")

            cols = disp.columns.tolist()
            c_idx = {c: i for i, c in enumerate(cols)}

            # 4) 당월/전월 연·월 정보 (attrs 우선, 없으면 직접 계산)
            base_year = int(getattr(snap, "attrs", {}).get("base_year", year))
            used_y = int(snap.attrs.get("used_year", year))
            used_m = int(snap.attrs.get("used_month", month))

            prev_y = snap.attrs.get("prev_year", None)
            prev_m = snap.attrs.get("prev_month", None)

            if prev_y is None or prev_m is None:
                # 연도 경계 포함 전월 계산
                py, pm = used_y, used_m - 1
                while pm <= 0:
                    py -= 1
                    pm += 12
                prev_y, prev_m = py, pm
            else:
                prev_y = int(prev_y)
                prev_m = int(prev_m)

            # 5) 서브컬럼(기간 구분) 추출
            # snap.columns: MultiIndex 가정 → level 1 이름 리스트
            if isinstance(snap.columns, pd.MultiIndex):
                sub_order = list(snap.columns.get_level_values(1).unique())
            else:
                # 혹시 단일 인덱스면, 숫자 열만 서브컬럼으로 처리 (백업용)
                sub_order = [c for c in snap.columns if c not in disp.columns[:2]]

            # 컬럼 위치 계산 (0: spacer, 1: 구분, 2~: 왼쪽 그룹, 그 뒤 오른쪽 그룹)
            left_group_start = 2
            left_group_end   = left_group_start + len(sub_order) - 1
            right_group_start = left_group_end + 1
            right_group_end   = right_group_start + len(sub_order) - 1

            # 6) 가짜 헤더 2행 구성
            hdr1 = [''] * len(cols)
            hdr2 = [''] * len(cols)

            # 1행: 당월 / 전월비 헤더
            hdr1[left_group_start]  = f"'{used_y % 100:02d} {used_m}월"
            hdr1[right_group_start] = f"전월비"

            # 2행: 구분 + 서브컬럼 이름
            hdr2[1] = "구분"
            for j, name in enumerate(sub_order):
                # 왼쪽 그룹(당월)
                col_idx_left = left_group_start + j
                if col_idx_left < len(hdr2):
                    hdr2[col_idx_left] = name

                # 오른쪽 그룹(전월비)
                col_idx_right = right_group_start + j
                if col_idx_right < len(hdr2):
                    hdr2[col_idx_right] = name

            hdr_df = pd.DataFrame([hdr1, hdr2], columns=cols)
            disp_vis = pd.concat([hdr_df, disp], ignore_index=True)




            def css_overlay_text(r, c, text, strong=True):
                # TD를 기준 위치로
                base = {
                    'selector': f'tbody tr:nth-child({r}) td:nth-child({c})',
                    'props': [('position', 'relative')],
                }
                # 그 위에 텍스트 올리기
                overlay = {
                    'selector': f'tbody tr:nth-child({r}) td:nth-child({c})::after',
                    'props': [
                        ('content', f'"{text}"'),
                        ('position', 'absolute'), ('left', '50%'), ('top', '50%'),
                        ('transform', 'translate(-50%, -50%)'),
                        ('white-space', 'nowrap'),
                        ('background', 'transparent'),
                        ('font-weight', '400' if strong else 'normal'),
                    ],
                }
                return [base, overlay]

            styles = [
                {'selector': 'thead', 'props': [('display','none')]},

                # 헤더 두 행
                {'selector': 'tbody tr:nth-child(1) td', 'props': [('text-align','center'), ('padding','8px 8px'), ('font-weight','600')]},
                {'selector': 'tbody tr:nth-child(2) td', 'props': [('text-align','center'), ('padding','10px 8px'), ('font-weight','600')]},
                {'selector': 'tbody tr:nth-child(2) td:nth-child(2)', 'props': [('text-align','center')]},

                # 스페이서(1열)
                {'selector': 'tbody td:nth-child(1)', 'props': [('width','8px'), ('border-right','0')]},

                # 본문(3행 이후)
                {'selector': 'tbody tr:nth-child(n+3) td', 'props': [('text-align','right'), ('padding','8px 10px')]},
                {'selector': 'tbody tr:nth-child(n+3) td:nth-child(2)', 'props': [('text-align','center')]},
            ]

            spacer_rules1 = [
                {
                    'selector': f'tbody tr:nth-child(1)',
                    'props': [('border-top','3px solid gray !important')]
                
                }


            ]

            styles += spacer_rules1

            spacer_rules1 = [
                {
                    'selector': f'tbody tr:nth-child({r}) td:nth-child(1)',
                    'props': [('border-bottom','2px solid white ')],
                }
                for r in (1,3,4,5)
            ]
            styles  += spacer_rules1

            spacer_rules2 = [
                {
                    'selector': f'tbody tr:nth-child(1) td:nth-child(2)',
                    'props': [('border-bottom','2px solid white ')],
                }
            ]
            styles  += spacer_rules2

            spacer_rules3 = [
                {
                    'selector': f'tbody tr:nth-child(1) td:nth-child({r})',
                    'props': [('border-right','2px solid white ')],
                }
                for r in (1,4,5,6,9,10,11)
            ]
            styles  += spacer_rules3

            spacer_rules4 = [
                {
                    'selector': f'tbody tr:nth-child(2) td:nth-child(1)',
                    'props': [('border-right','2px solid white ')],
                }
            ]
            styles  += spacer_rules4

            spacer_rules5 = [
                {
                    'selector': f'tbody tr:nth-child(2) td:nth-child({r})',
                    'props': [('border-top','3px solid gray ')],
                }
                for r in (1,2,4,5,6,7,9,10,11,12)
            ]
            styles  += spacer_rules5

            spacer_rules6 = [
                {
                    'selector': f'tbody tr:nth-child(2) td:nth-child({r})',
                    'props': [('border-bottom','3px solid gray ')],
                }
                for r in range(1,13)
            ]
            styles  += spacer_rules6

            spacer_rules7 = [
                {
                    'selector': f'tbody tr:nth-child(1) td:nth-child({r})',
                    'props': [('border-top','3px solid gray ')],
                }
                for r in (3,8)
            ]
            styles  += spacer_rules7

            spacer_rules7 = [
                {
                    'selector': f'tbody tr:nth-child(1) td:nth-child({r})',
                    'props': [('border-left','3px solid gray ')],
                }
                for r in (3,8,9)
            ]
            styles  += spacer_rules7

            spacer_rules7 = [
                {
                    'selector': f'tbody tr:nth-child(1) td:nth-child(3)',
                    'props': [('border-right','3px solid gray ')],
                }
            ]
            styles  += spacer_rules7

            spacer_rules7 = [
                {
                    'selector': f'tbody tr:nth-child(2) td:nth-child({r})',
                    'props': [('border-right','3px solid gray ')],
                }
                for r in (2,7)
            ]
            styles  += spacer_rules7

            spacer_rules1 = [
                {
                    'selector': f'tbody td:nth-child(2)',
                    'props': [('border-right','3px solid gray !important')]
                
                }

            ]

            styles += spacer_rules1

            display_styled_df(disp_vis, styles=styles, already_flat=True)
            display_memo('f_4', year, month)

        except Exception as e:
            st.error(f"회전일 표 생성 중 오류: {e}")


    with col_mid:
        st.markdown("<div class='v-divider'></div>", unsafe_allow_html=True)


    with col_right:


        try:
            st.markdown("<h4>5) ROE</h4>", unsafe_allow_html=True)
            st.markdown(
                "<div style='text-align:left; font-size:13px; color:#666;'>[단위: 백만원]</div>",
                unsafe_allow_html=True
            )

            file_name = st.secrets["sheets"]["f_5"]  
            raw = pd.read_csv(file_name, dtype=str)

            import importlib
            importlib.invalidate_caches()
            importlib.reload(modules)

            base = modules.create_roe_table(
                year=year,
                month=month,
                data=raw
            )


            disp = base.reset_index().rename(columns={"index": "구분"})

            styles = [
                {
                    'selector': 'thead th',
                    'props': [
                        ('text-align','center'),
                        ('padding','10px 8px'),
                        ('font-weight','600'),
                        ('border-top','3px solid gray !important'),
                        
                    ]
                },
                {
                    'selector': 'tbody td',
                    'props': [
                        ('padding','8px 10px'),
                        ('text-align','right')
                    ]
                },
                {
                    # '구분' 컬럼 좌정렬
                    'selector': 'tbody td:nth-child(1)',
                    'props': [('text-align','left')]
                },
            ]
            spacer_rules1 = [
                {
                    'selector': f'tbody tr:nth-child(1)',
                    'props': [('border-top','3px solid gray !important')]
                
                }
 

            ]

            styles += spacer_rules1

            spacer_rules1 = [
                {
                    'selector': f'tbody td:nth-child(2)',
                    'props': [('border-left','3px solid gray !important')]
                
                }

            ]

            styles += spacer_rules1

            display_styled_df(
                disp,
                styles=styles,
                highlight_cols=None,
                already_flat=True  
            )

            st.markdown(
                "<div style='text-align:left; font-size:13px; color:#666;'>* ROE = 당기순이익/ 자본총계, 연결기준</div>",
                unsafe_allow_html=True
            )
            st.markdown(
                "<div style='text-align:left; font-size:13px; color:#666;'>* 유효법인세율 20% 반영</div>",
                unsafe_allow_html=True
            )

            display_memo('f_5', year, month)

        except Exception as e:
            st.error(f"ROE 표 생성 중 오류: {e}")


    # ─ 가로 스크롤 래퍼 닫기 ─
    st.markdown(
        """
        </div>
        </div>
        """,
        unsafe_allow_html=True
    )




with t2:

    st.markdown("<h4>1) 손익(별도)</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 톤, 백만원, %]</div>", unsafe_allow_html=True)

    try:
        file_name = st.secrets["sheets"]["f_1"]   
        raw = pd.read_csv(file_name, dtype=str)

        base = modules.create_pl_separate_hq(
            year=int(st.session_state['year']),
            month=int(st.session_state['month']),
            data=raw
        )

        disp = base.reset_index().rename(columns={"index":"구분"})
        SP = "__sp__"; disp.insert(0, SP, "")

        cols = disp.columns.tolist(); c = {k:i for i,k in enumerate(cols)}
        hdr1 = ['']*len(cols)
        hdr1[c["구분"]]  = "구분"

        hdr1[c['당월 계획']] = '당월'
        hdr1[c['누적 계획']] = '누적'

        hdr2 = ['']*len(cols)
        for k in ['전월','당월 계획','당월 실적','당월 계획대비','당월 전월대비','누적 계획','누적 실적','누적 계획대비']:
            hdr2[c[k]] = k.split()[-1] if k.startswith('당월') or k.startswith('누적') else '전월'
        
        header_df = pd.DataFrame([hdr1,hdr2], columns=cols)
        disp_vis  = pd.concat([header_df, disp], ignore_index=True)

        # ─────────────────────────────
        #  여기부터: 행별 포맷 + 판매량만 천단위 반올림
        # ─────────────────────────────
        from decimal import Decimal, ROUND_HALF_UP
        import math

        amt_rows = ["매출액", "영업이익", "순금융비용", "경상이익"]
        qty_rows = ["판매량"]
        pct_rows = ["%(영업)", "%(경상)"]

        # "(1,234)" 같은 문자열 → float
        def _to_float(x):
            try:
                s = str(x).strip()
                if s == "" or s.lower() == "nan":
                    return math.nan
                neg = s.startswith("(") and s.endswith(")")
                s = s.replace("(", "").replace(")", "").replace(",", "")
                v = float(s)
                return -abs(v) if neg else v
            except Exception:
                return math.nan

        # 금액: 그대로 정수 반올림 + 천단위 + 음수 괄호
        def fmt_amount(x):
            v = _to_float(x)
            if math.isnan(v):
                return x
            r = int(Decimal(str(v)).quantize(Decimal("0"), rounding=ROUND_HALF_UP))
            s = f"{abs(r):,}"
            return f"({s})" if r < 0 else s

        #단위

        def fmt_qty(x):
            v = _to_float(x)
            if math.isnan(v):
                return x

            v_thousand = v / 1000.0  
            r = int(Decimal(str(v_thousand)).quantize(Decimal("0"), rounding=ROUND_HALF_UP))

            s = f"{abs(r):,}"
            return f"({s})" if r < 0 else s


        def fmt_pct(x):
            v = _to_float(x)
            if math.isnan(v):
                return x
            r = float(Decimal(str(v)).quantize(Decimal("0.0"), rounding=ROUND_HALF_UP))
            s = f"{abs(r):.1f}"
            return f"({s})" if r < 0 else s

        # 헤더 2행 제외한 본문만 포맷
        body = disp_vis.iloc[2:].copy()
        num_cols = cols[2:]   # SP, 구분 제외

        mask_amt = body["구분"].isin(amt_rows)
        mask_qty = body["구분"].isin(qty_rows)
        mask_pct = body["구분"].isin(pct_rows)

        body.loc[mask_amt, num_cols] = body.loc[mask_amt, num_cols].applymap(fmt_amount)
        body.loc[mask_qty, num_cols] = body.loc[mask_qty, num_cols].applymap(fmt_qty)
        body.loc[mask_pct, num_cols] = body.loc[mask_pct, num_cols].applymap(fmt_pct)

        disp_vis = pd.concat([disp_vis.iloc[:2], body], ignore_index=True)


        styles = [
            {'selector':'thead','props':[('display','none')]},
            {'selector':'tbody tr:nth-child(1) td','props':[('text-align','center'),('font-weight','600')]},
            {'selector':'tbody tr:nth-child(2) td','props':[('text-align','center'),('font-weight','600')]},
            {'selector':'tbody td:nth-child(1)','props':[('width','8px'),('border-right','0')]},
            {'selector':'tbody tr:nth-child(n+3) td','props':[('text-align','right')]},
            {'selector':'tbody tr:nth-child(n+3) td:nth-child(2)','props':[('text-align','left')]},
        ]

        spacer_rules1 = [
                    {
                        'selector': f'tbody tr:nth-child(1) td:nth-child({r})',
                        'props': [('border-right','2px solid white ')],
                    
                    }
                    for r in (1,2,5,6,9)
                ]
        
        styles  += spacer_rules1

        spacer_rules3 = [
                    {
                        'selector': f'tbody tr:nth-child(2) td:nth-child(1)',
                        'props': [('border-right','3px solid gray ')],
                    }
                    for j in (5,6)
                    
                ]
        
        styles  += spacer_rules3

        spacer_rules2 = [
                    {
                        'selector': f'tbody tr:nth-child({j}) td:nth-child(1)',
                        'props': [('border-right','2px solid white ')],
                    }
                    for j in range (2,10)
                    
                ]
        
        styles  += spacer_rules2

        spacer_rules3 = [
                    {
                        'selector': f'tbody tr:nth-child(2) td:nth-child({j})',
                        'props': [('border-top','3px solid gray ')],
                    }
                    for j in (5,6,7,9,10)
                    
                ]
        
        styles  += spacer_rules3

        spacer_rules4 = [
                    {
                        'selector': f'tbody tr:nth-child(1) td:nth-child({j})',
                        'props': [('border-right','3px solid gray ')],
                    }
                    for j in (4,8)
                    
                ]
        
        styles  += spacer_rules4

        spacer_rules5 = [
                    {
                        'selector': f'tbody tr:nth-child(1) td:nth-child({j})',
                        'props': [('border-top','3px solid gray ')],
                    }
                    for j in (4,8)
                    
                ]
        
        styles  += spacer_rules5

        spacer_rules4 = [
                    {
                        'selector': f'tbody tr:nth-child(1) td:nth-child({j})',
                        'props': [('border-left','3px solid gray ')],
                    }
                    for j in (4,8)
                    
                ]
        
        styles  += spacer_rules4

        spacer_rules6 = [
                    {
                        'selector': f'tbody tr:nth-child(2) td:nth-child({j})',
                        'props': [('border-left','3px solid gray ')],
                    }
                    for j in (3,4,8)
                    
                ]
        
        styles  += spacer_rules6     


        spacer_rules7 = [
                    {
                        'selector': f'tbody tr:nth-child({r})',
                        'props': [('border-top','3px solid gray ')],
                    }
                    for r in (1,3)

                ]
        
        styles  += spacer_rules7   

        spacer_rules7 = [
                    {
                        'selector': f'tbody tr:nth-child(2) td:nth-child(3))',
                        'props': [('border-right','2px solid white !important')],
                    }

                ]
        
        styles  += spacer_rules7

        spacer_rules7 = [
                    {
                        'selector': f'tbody tr:nth-child(2) td:nth-child({r})',
                        'props': [('border-top','2px solid white ')],
                    }
                    for r in (1,2,3,4,8)

                ]
        
        styles  += spacer_rules7


        spacer_rules9 = [
                    {
                        'selector': f'td:nth-child(2)',
                        'props': [('border-right','3px solid gray !important')],
                    }


                    
                ]
        
        styles  += spacer_rules9


        display_styled_df(disp_vis, styles=styles, already_flat=True)
        display_memo('f_1_2', year, month)

    except Exception as e:
        st.error(f"손익 별도 생성 중 오류: {e}")

    st.divider()

    st.markdown("<h4>2) 품목손익 (별도)</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 톤, 백만원, %]</div>", unsafe_allow_html=True)


    try:
        file_name = st.secrets["sheets"]["f_7"]   
        raw = pd.read_csv(file_name, dtype=str)             

        year  = int(st.session_state["year"])
        month = int(st.session_state["month"])

        base = modules.create_item_pl_from_flat(
            data=raw, year=year, month=month,
            main_items=("CHQ","CD","STS","BTB","PB"),   
            filter_tag="품목손익"                        
        )


        # 3) 화면용: 행 라벨을 '구분' 컬럼으로 승격
        disp = base.reset_index().rename(columns={"index": "구분"}) 
        # 표 컬럼 순서 고정
        disp = disp[["구분","합계","CHQ","CD","STS","BTB","PB","상품 등"]]


        SP = "__sp__"
        disp.insert(0, SP, "")  
        cols = disp.columns.tolist(); c = {k:i for i,k in enumerate(cols)}

        # (1행) 그룹 라벨: CHQ~PB 위에만 '품목' 표시
        hdr1 = [''] * len(cols)
        hdr1[c["STS"]] = "품목"   

        # (2행) 개별 열 라벨
        hdr2 = [''] * len(cols)
        hdr2[c[SP]]   = ""
        hdr1[c["구분"]]  = "구분"
        hdr2[c["합계"]]  = "합계"
        for k in ["CHQ","CD","STS","BTB","PB","상품 등"]:
            hdr2[c[k]] = k

        header_df = pd.DataFrame([hdr1, hdr2], columns=cols)
        disp_vis  = pd.concat([header_df, disp], ignore_index=True)

        # 5) 숫자/퍼센트 포맷(음수 괄호, 천단위, % 1자리)
        amt_rows = ["매출액","영업이익","경상이익"]
        qty_rows = ["판매량"]
        pct_rows = ["%(영업)","%(경상)"]

        def fmt_amount(x):
            try:
                v = float(x)
                s = f"{abs(int(round(v))):,}"
                return f"({s})" if v < 0 else s
            except: return x

        def fmt_qty(x):
            try:
                v = float(x)
                s = f"{abs(int(round(v))):,}"
                return f"({s})" if v < 0 else s
            except: return x

        def fmt_pct(x):
            try:
                v = float(x)
                s = f"{abs(v):.1f}"
                return f"({s})" if v < 0 else s
            except: return x

        body = disp_vis.iloc[2:].copy()
        mask_amt = body["구분"].isin(amt_rows)
        mask_qty = body["구분"].isin(qty_rows)
        mask_pct = body["구분"].isin(pct_rows)

        body.loc[mask_amt, cols[2:]] = body.loc[mask_amt, cols[2:]].applymap(fmt_amount)
        body.loc[mask_qty, cols[2:]] = body.loc[mask_qty, cols[2:]].applymap(fmt_qty)
        body.loc[mask_pct, cols[2:]] = body.loc[mask_pct, cols[2:]].applymap(fmt_pct)

        disp_vis = pd.concat([disp_vis.iloc[:2], body], ignore_index=True)


        styles = [

            {'selector':'thead','props':[('display','none')]},

            {'selector':'tbody tr:nth-child(1) td',
             'props':[('text-align','center'),('font-weight','600'),('padding','8px 6px')]},

            {'selector':'tbody tr:nth-child(2) td',
             'props':[('text-align','center'),('font-weight','600'),('padding','8px 6px')]},

            {'selector':'tbody tr:nth-child(n+3) td', 'props':[('text-align','right')]},
            {'selector':'tbody tr:nth-child(n+3) td:nth-child(%d)' % (c["구분"]+1),
             'props':[('text-align','center')]},

        ]

        spacer_rules1 = [
                    {
                        'selector': f'tbody tr:nth-child(2) td:nth-child({j})',
                        'props': [('border-bottom','3px solid gray ')],
                    }
                    for j in range(1,10)
                    
                ]
        
        styles  += spacer_rules1

        spacer_rules2 = [
                    {
                        'selector': f'tbody tr:nth-child(1) td:nth-child({j})',
                        'props': [('border-top','3px solid gray ')],
                    }
                    for j in range(1,10)
                    
                ]
        
        styles  += spacer_rules2

        spacer_rules3 = [
                    {
                        'selector': f'tbody tr:nth-child(1) td:nth-child({j})',
                        'props': [('border-right','2px solid white ')],
                    }
                    for j in range(3,9)
                    
                ]
        
        styles  += spacer_rules3




        spacer_rules4 = [
                    {
                        'selector': f'td:nth-child(1)',
                        'props': [('border-right','2px solid white ')],
                    }

                    
                ]
        
        styles  += spacer_rules4

        spacer_rules5 = [
                    {
                        'selector': f'tbody tr:nth-child({j}) td:nth-child(1)',
                        'props': [('border-bottom','2px solid white ')],
                    }
                    for j in (5,7)
                    
                ]
        
        styles  += spacer_rules5

        spacer_rules6 = [
                    {
                        'selector': f'tbody tr:nth-child({j}) td:nth-child(2)',
                        'props': [('border-bottom','2px solid white ')],
                    }
                    for j in (5,7)
                    
                ]
        
        styles  += spacer_rules6

        spacer_rules7 = [
                    {
                        'selector': f'tbody tr:nth-child(1) td:nth-child({r})',
                        'props': [('border-bottom','2px solid white ')],
                    }

                    for r in (1,2)
                ]
        
        styles  += spacer_rules7                


        spacer_rules8 = [
                    {
                        'selector': f'td:nth-child(2)',
                        'props': [('border-right','3px solid gray ')],
                    }


                    
                ]
        
        styles  += spacer_rules8    


        display_styled_df(disp_vis, styles=styles, already_flat=True)

        display_memo('f_7', year, month)

    except Exception as e:
        st.error(f"품목손익 (별도) 생성 중 오류: {e}")

    st.divider()

    st.markdown("<h4>3) 수정원가기준 손익 (별도)</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 톤, 백만원, %]</div>", unsafe_allow_html=True)


    try:
        file_name = st.secrets["sheets"]["f_8"]   # 업로드하신 CSV 경로
        raw = pd.read_csv(file_name, dtype=str)

        year  = int(st.session_state["year"])
        month = int(st.session_state["month"])

        base = modules.create_item_change_cost_from_flat(
            data=raw, year=year, month=month,
            col_order=("계","CHQ","CD","STS","BTB","PB","내수","수출")  
        )



        disp = base.reset_index().rename(columns={"index":"구분"})
        disp = disp[["구분","계","CHQ","CD","STS","BTB","PB","내수","수출"]]


        SP = "__sp__"
        disp.insert(0, SP, "")

        cols = disp.columns.tolist()
        c = {k:i for i,k in enumerate(cols)}

        hdr1 = [""] * len(cols)
        hdr1[c["계"]]  = "계"     
        hdr1[c["구분"]] = "구분"

        hdr2 = [""] * len(cols)
        hdr2[c["계"]]   = ""      
        for k in ["CHQ","CD","STS","BTB","PB","내수","수출"]:
            hdr2[c[k]] = k

        header_df = pd.DataFrame([hdr1, hdr2], columns=cols)
        disp_vis  = pd.concat([header_df, disp], ignore_index=True).fillna("")


        # === 포맷 ===
        amt_rows = ["매출액","X등급 및 재고평가","영업이익","한계이익"]
        qty_rows = ["판매량"]
        pct_rows = ["%(영업)","%(한계)"]

        def fmt_amount(x):
            try:
                v = float(x); s = f"{abs(int(round(v))):,}"
                return f"({s})" if v < 0 else s
            except: return x

        def fmt_qty(x):
            try:
                v = float(x); s = f"{abs(int(round(v))):,}"
                return f"({s})" if v < 0 else s
            except: return x

        def fmt_pct(x):
            try:
                v = float(x); s = f"{abs(v):.1f}"
                return f"({s})" if v < 0 else s
            except: return x

        body = disp_vis.iloc[2:].copy()
        num_cols = cols[2:]  # SP, 구분 제외
        mask_amt = body["구분"].isin(amt_rows)
        mask_qty = body["구분"].isin(qty_rows)
        mask_pct = body["구분"].isin(pct_rows)

        body.loc[mask_amt, num_cols] = body.loc[mask_amt, num_cols].applymap(fmt_amount)
        body.loc[mask_qty, num_cols] = body.loc[mask_qty, num_cols].applymap(fmt_qty)
        body.loc[mask_pct, num_cols] = body.loc[mask_pct, num_cols].applymap(fmt_pct)

        disp_vis = pd.concat([disp_vis.iloc[:2], body], ignore_index=True)

        styles = [

            {'selector':'thead','props':[('display','none')]},

            {'selector':'tbody tr:nth-child(1) td','props':[('text-align','center'),('font-weight','600')]},
            {'selector':'tbody tr:nth-child(2) td','props':[('text-align','center'),('font-weight','600')]},

            {'selector':'tbody tr:nth-child(n+3) td','props':[('text-align','right')]},
            {'selector':f'tbody tr:nth-child(n+3) td:nth-child({c["구분"]+1})','props':[('text-align','left')]},

        ]


        spacer_rules1 = [
                    {
                        'selector': f'tbody tr:nth-child(2)',
                        'props': [('border-bottom','3px solid gray ')],
                    }
  
                    
                ]
        
        styles  += spacer_rules1

        spacer_rules2 = [
                    {
                        'selector': f'tbody tr:nth-child(2) td:nth-child({j})',
                        'props': [('border-top','3px solid gray ')],
                    }
                    for j in range(4,11)
                    
                ]
        
        styles  += spacer_rules2

        spacer_rules3 = [
                    {
                        'selector': f'tbody tr:nth-child(1) td:nth-child({j})',
                        'props': [('border-right','2px solid white ')],
                    }
                    for j in range(3,10)
                    
                ]
        
        styles  += spacer_rules3




        spacer_rules4 = [
                    {
                        'selector': f'tbody tr:nth-child({j}) td:nth-child(1)',
                        'props': [('border-right','2px solid white ')],
                    }
                    for j in range(1,10)
                    
                ]
        
        styles  += spacer_rules4

        spacer_rules5 = [
                    {
                        'selector': f'tbody tr:nth-child({j}) td:nth-child(1)',
                        'props': [('border-bottom','2px solid white ')],
                    }
                    for j in (6,8)
                    
                ]
        
        styles  += spacer_rules5

        spacer_rules6 = [
                    {
                        'selector': f'tbody tr:nth-child({j}) td:nth-child(2)',
                        'props': [('border-bottom','2px solid white ')],
                    }
                    for j in (6,8)
                    
                ]
        
        spacer_rules6 = [
                    {
                        'selector': f'tbody tr:nth-child(1) ',
                        'props': [('border-top','3px solid gray ')],
                    }

                    
                ]
        
        styles  += spacer_rules6        


        spacer_rules7 = [
                    {
                        'selector': f'tbody tr:nth-child(1) td:nth-child(3)',
                        'props': [('border-right','3px solid gray ')],
                    }
                    for j in (6,8)
                    
                ]
        
        styles  += spacer_rules7        

        spacer_rules8 = [
                    {
                        'selector': f'tbody tr:nth-child(1) td:nth-child({r})',
                        'props': [('border-bottom','2px solid white ')],
                    }
                    for r in (1,2)

                    
                ]
        
        styles  += spacer_rules8                


        spacer_rules8 = [
                    {
                        'selector': f'td:nth-child(2)',
                        'props': [('border-right','3px solid gray ')],
                    }


                    
                ]
        
        styles  += spacer_rules8    


        display_styled_df(disp_vis, styles=styles, already_flat=True)
        





    except Exception as e:
        st.error(f"수정원가기준  (별도) 생성 중 오류: {e}")

    st.divider()

    ##### 원재료 입고-기초 단가 차이 #####

    st.markdown("<h4>4) 원재료 입고-기초 단가 차이</h4>", unsafe_allow_html=True)


    try:
        file_name = st.secrets["sheets"]["f_9"]
        raw = pd.read_csv(file_name, dtype=str)

        year = int(st.session_state["year"])
        month = int(st.session_state["month"])

        ar = modules.create_9(year=year, month=month, data=raw)
        disp = ar.copy()

        # 숫자 변환(계산용)
        for c in ["중량", "금액", "단가"]:
            disp[c] = pd.to_numeric(disp[c].astype(str).str.replace(",", ""), errors="coerce").fillna(0)

        # 단위 정리
        def round_then_drop(v: float, divisor: int) -> int:
            """
            v/divisor -> 소수 1자리 반올림 -> 소수 버리고 정수만(= int, 0쪽으로 절사)
            """
            x = round(v / divisor, 1)  # 소수 1자리 반올림
            return int(x)              
        

        def fmt_int_plain(n: int) -> str:

            return f"{n:,}"

        # 표시값 만들기
        disp["중량"] = disp["중량"].apply(lambda v: fmt_int_plain(round_then_drop(v, 1_000)))
        disp["금액"] = disp["금액"].apply(lambda v: fmt_int_plain(round_then_drop(v, 1_000_000)))



        cols = disp.columns.tolist()
        c_idx = {c: i for i, c in enumerate(cols)}

        hdr1 = [""] * len(cols)
        hdr1[c_idx["메이커"]] = "메이커"
        hdr1[c_idx["중량"]] = "중량"
        hdr1[c_idx["금액"]] = "금액"
        hdr1[c_idx["단가"]] = "단가"

        hdr_df = pd.DataFrame([hdr1], columns=cols)
        disp_vis = pd.concat([hdr_df, disp], ignore_index=True)



        styles = [
            {"selector": "thead", "props": [("display", "none")]},

            {
                "selector": "tbody tr:nth-child(1) td",
                "props": [
                    ("text-align", "center"),
                    ("padding", "6px 8px"),
                    ("font-weight", "700"),
                    ("border-bottom", "3px solid gray"),
                ],
            },

            {"selector": "tbody tr:nth-child(n+2) td:nth-child(1)", "props": [("text-align", "left")]},
            {"selector": "tbody tr:nth-child(n+2) td:nth-child(n+2)", "props": [("text-align", "right")]},
            {"selector": "tbody td:nth-child(1)", "props": [("border-right", "3px solid gray")]},


        ]

        spacer_rules1 = [
                {
                    'selector': f'tbody tr:nth-child(1)',
                    'props': [('border-top','3px solid gray !important')]
                
                }


            ]

        styles += spacer_rules1

        display_styled_df(disp_vis, styles=styles, already_flat=True)

    except Exception as e:
        st.error(f"원재료 입고-기초 단가 차이 표 생성 중 오류: {e}")



    ##### 원재료 입고-기초 단가 차이 거래처 기준 #####
    st.divider()

    st.markdown("<h4>5) 원재료 입고-기초 단가 차이 거래처 기준</h4>", unsafe_allow_html=True)

    try:
        file_name = st.secrets["sheets"]["f_10"]
        raw = pd.read_csv(file_name, dtype=str)

        year = int(st.session_state["year"])
        month = int(st.session_state["month"])

        ar = modules.create_10(year=year, month=month, data=raw)
        disp = ar.copy()

        # 숫자 변환(계산용)
        for c in ["금액", "단가"]:
            disp[c] = pd.to_numeric(disp[c].astype(str).str.replace(",", ""), errors="coerce").fillna(0)

        # 단위 정리
        def round_then_drop(v: float, divisor: int) -> int:
            """
            v/divisor -> 소수 1자리 반올림 -> 소수 버리고 정수만(= int, 0쪽으로 절사)
            """
            x = round(v / divisor, 1)  # 소수 1자리 반올림
            return int(x)              
        

        def fmt_int_plain(n: int) -> str:

            return f"{n:,}"

        # 표시값 만들기
        disp["금액"] = disp["금액"].apply(lambda v: fmt_int_plain(round_then_drop(v, 1_000_000)))




        cols = disp.columns.tolist()
        c_idx = {c: i for i, c in enumerate(cols)}

        hdr1 = [""] * len(cols)
        hdr1[c_idx["메이커"]] = "메이커"
        hdr1[c_idx["금액"]] = "금액"
        hdr1[c_idx["단가"]] = "단가"

        hdr_df = pd.DataFrame([hdr1], columns=cols)
        disp_vis = pd.concat([hdr_df, disp], ignore_index=True)



        styles = [
            {"selector": "thead", "props": [("display", "none")]},

            {
                "selector": "tbody tr:nth-child(1) td",
                "props": [
                    ("text-align", "center"),
                    ("padding", "6px 8px"),
                    ("font-weight", "700"),
                    ("border-bottom", "3px solid gray"),
                ],
            },

            {"selector": "tbody tr:nth-child(n+2) td:nth-child(1)", "props": [("text-align", "left")]},
            {"selector": "tbody tr:nth-child(n+2) td:nth-child(n+2)", "props": [("text-align", "right")]},
            {"selector": "tbody td:nth-child(1)", "props": [("border-right", "3px solid gray")]},


        ]

        spacer_rules1 = [
                {
                    'selector': f'tbody tr:nth-child(1)',
                    'props': [('border-top','3px solid gray !important')]
                
                }


            ]

        styles += spacer_rules1

        display_styled_df(disp_vis, styles=styles, already_flat=True)

    except Exception as e:
        st.error(f"원재료 입고-기초 단가 차이 거래처 기준 표 생성 중 오류: {e}")


    st.divider()

    st.markdown("<h4>6) 제품수불표</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 백만원]</div>", unsafe_allow_html=True)



    try:
        file_name = st.secrets["sheets"]["f_11"]   
        df_src = pd.read_csv(file_name, dtype=str)


        pf_base = modules.create_product_flow_base(
            year=int(st.session_state['year']),
            month=int(st.session_state['month']),
            data=df_src,
            
            amount_div=1_000_000  # 원 → 백만원
        )

        # --- 화면용 변환(가짜 헤더 3줄 삽입) ---
        yy = str(int(st.session_state['year']))[-2:]
        mm = int(st.session_state['month'])

        # 본문 숫자 포맷(표시는 여기서)
        def _fmt(x, nd=1):
            try: v = float(x)
            except: return x
            s = f"{v:,.{nd}f}"
            return s  # 괄호표기 원하면: return f"({abs(v):,.{nd}f})" if v < 0 else s

        body = pf_base.copy()
        body["입고-기초_단가"]    = body["입고-기초_단가"].map(lambda v: _fmt(v, 1))
        body["입고-기초_금액"]    = body["입고-기초_금액"].map(lambda v: _fmt(v, 1))
        body["매출원가-기초_단가"] = body["매출원가-기초_단가"].map(lambda v: _fmt(v, 1))
        body["매출원가-기초_금액"] = body["매출원가-기초_금액"].map(lambda v: _fmt(v, 1))


        cols = ["__spacer__", "입고-기초_단가", "입고-기초_금액", "매출원가-기초_단가", "매출원가-기초_금액"]
        body = body.reindex(columns=cols[1:])  # 동일 순서 보장
        disp = body.copy()
        disp.insert(0, "__spacer__", "")

        hdr1 = ["", f"{mm}월", "", "", ""]
        hdr2 = ["", "입고-기초", "", "매출원가-기초", ""]
        hdr3 = ["", "단가", "금액", "단가", "금액"]
        hdr_df = pd.DataFrame([hdr1, hdr2, hdr3], columns=cols)
        disp_vis = pd.concat([hdr_df, disp], ignore_index=True)

        # --- 스타일(CSS) ---
        styles = [


            {'selector': 'thead', 'props': [('display','none')]},
            {'selector': 'table', 'props': [('border-collapse','collapse'), ('width','100%')]},
            # {'selector': 'tbody td', 'props': [('border','1px solid #333'), ('padding','6px 10px')]},

            # 상단 3줄
            {'selector': 'tbody tr:nth-child(1) td', 'props': [('text-align','center'), ('font-weight','700')]},
            {'selector': 'tbody tr:nth-child(2) td, tbody tr:nth-child(3) td',
            'props': [('text-align','center'), ('font-weight','600')]},

            # 단가 금액 강조
            {'selector': 'tbody tr:nth-child(4) td', 'props': [('text-align','right'), ('font-weight','700')]},
            {'selector': 'tbody tr:nth-child(4) td:nth-child(1)', 'props': [('text-align','left')]},
            {'selector': 'tbody tr:nth-child(4) td:nth-child(n+2)', 'props': [('background','#f0f0f0')]},

            # 좌측 스페이서
            {'selector': 'tbody td:nth-child(1)', 'props': [('width','8px'), ('border-right','0')]},

            # 입고-기초
            {'selector': 'tbody tr:nth-child(2) td:nth-child(2), tbody tr:nth-child(2) td:nth-child(3)',
            'props': [('border-top','3px solid gray')]},
            {'selector': 'tbody tr:nth-child(4) td:nth-child(2), tbody tr:nth-child(4) td:nth-child(3)',
            'props': [('border-bottom','3px solid gray')]},
            {'selector': 'tbody tr:nth-child(n+2) td:nth-child(2)', 'props': [('border-left','3px solid gray')]},
            {'selector': 'tbody tr:nth-child(n+2) td:nth-child(3)', 'props': [('border-right','3px solid gray')]},

            # 매출원가-기초
            {'selector': 'tbody tr:nth-child(2) td:nth-child(4), tbody tr:nth-child(2) td:nth-child(5)',
            'props': [('border-top','3px solid gray')]},
            {'selector': 'tbody tr:nth-child(4) td:nth-child(4), tbody tr:nth-child(4) td:nth-child(5)',
            'props': [('border-bottom','3px solid gray')]},
            {'selector': 'tbody tr:nth-child(n+2) td:nth-child(4)', 'props': [('border-left','3px solid gray')]},
            {'selector': 'tbody tr:nth-child(n+2) td:nth-child(5)', 'props': [('border-right','3px solid gray')]},

            {'selector': 'tbody tr:nth-child(1) td:nth-child(2)', 'props': [('border-right','2px solid white')]},
            {'selector': 'tbody tr:nth-child(1) td:nth-child(3)', 'props': [('border-right','2px solid white')]},
            {'selector': 'tbody tr:nth-child(1) td:nth-child(4)', 'props': [('border-right','2px solid white')]},
            # {'selector': 'tbody tr:nth-child(1) td:nth-child(6)', 'props': [('border-right','2px solid white')]},
            # 1열 빈칸 삭제
            {
                'selector': 'tbody td:nth-child(1), tbody tr:nth-child(1) td:nth-child(1), tbody tr:nth-child(2) td:nth-child(1), tbody tr:nth-child(3) td:nth-child(1)',
                'props': [('display','none')]
            },
        ]
        spacer_rules1 = [
                {
                    'selector': f'tbody tr:nth-child(1)',
                    'props': [('border-top','3px solid gray !important')]
                
                }


            ]

        styles += spacer_rules1

        
        display_styled_df(disp_vis, styles=styles, already_flat=True)

    except Exception as e:
        st.error(f"제품 수불표 생성 중 오류: {e}")



    
    st.divider()

    st.markdown("<h4>7) 현금흐름표 손익 (별도)</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 톤, 백만원, %]</div>", unsafe_allow_html=True)


    try:
        file_name = st.secrets["sheets"]["f_12"]
        raw = pd.read_csv(file_name, dtype=str)


        # 1) 유틸
        def _to_num(s: pd.Series) -> pd.Series:
            s = s.fillna("").astype(str).str.replace(",", "", regex=False).str.strip()
            v = pd.to_numeric(s, errors="coerce")
            return v.fillna(0.0)

        def _clean_cf_sep(df_raw: pd.DataFrame) -> pd.DataFrame:
            df = df_raw.copy()
            need = {"구분1","구분2","연도","월","실적"}
            miss = need - set(df.columns)
            if miss:
                raise ValueError(f"필수 컬럼 누락: {miss}")
            for c in ["구분1","구분2","구분3","구분4"]:
                if c in df.columns:
                    df[c] = (
                        df[c]
                        .astype(str)
                        .str.strip()
                        .str.replace(r"\s+", " ", regex=True)
                    )
            df["연도"] = pd.to_numeric(df["연도"], errors="coerce").astype("Int64")
            df["월"]   = pd.to_numeric(df["월"],   errors="coerce").astype("Int64")
            df["실적"] = _to_num(df["실적"])
            # 현금흐름표_별도만 사용
            df = df[df["구분1"] == "현금흐름표_별도"].copy()
            # 원본 순서 보존 (중복 라벨의 N번째 구분용)
            df["__ord__"] = range(len(df))
            return df

        df0   = _clean_cf_sep(raw)
        year  = int(st.session_state["year"])
        month = int(st.session_state["month"])

        # 2) 원하는 행 순서(= 구분2 값 순서)
        item_order = [
            "영업활동현금흐름",
            "당기순이익",
            "조정",
            "감가상각비",
            "기타",                            
            "자산부채증감",
            "매출채권 감소(증가)",
            "재고자산 감소(증가)",
            "기타자산 감소(증가)",
            "매입채무 증가(감소)",
            "기타채무 증가(감소)",
            "법인세납부",
            "투자활동현금흐름",
            "투자활동 현금유출",
            "투자활동 현금유입",
            "재무활동현금흐름",
            "차입금의 증가(감소)",
            "기타",                              # 2번째 기타(재무 영역 위치)
            "배당금의 지급",
            "리스부채의 증감",
            "현금성자산의 증감",
            "기초현금",
            "기말현금",
        ]

        # (중요) 같은 라벨의 N번째 등장만 집계하도록 번호 부여
        name_counts = {}
        order_with_n = []
        for name in item_order:
            name_counts[name] = name_counts.get(name, 0) + 1
            order_with_n.append((name, name_counts[name]))  # ('기타',1), ('기타',2) ...

        index_labels = [nm for nm, _ in order_with_n]

        # 컬럼 라벨 (연도 컬럼 명부터 먼저 정의)
        col_prev2_label   = f"{str(year-2)[-2:]}년"       # '23년
        col_prev1_label   = f"{str(year-1)[-2:]}년"       # '24년
        col_currsum_label = f"{str(year)[-2:]}년누적"     # '25년누적

        # 3) 선택월 + item_order에 해당하는 데이터 존재 여부 체크
        sel_month = df0[
            (df0["연도"] == year)
            & (df0["월"] == month)
            & (df0["구분2"].isin(item_order))
        ]

        used_m = month  # 헤더에 표시할 선택월은 그대로 사용

        if sel_month.empty:
            base = pd.DataFrame(
                {
                    col_prev2_label:   [np.nan] * len(index_labels),
                    col_prev1_label:   [np.nan] * len(index_labels),
                    "전월누적":         [np.nan] * len(index_labels),
                    "당월":             [np.nan] * len(index_labels),
                    col_currsum_label: [np.nan] * len(index_labels),
                },
                index=pd.Index(index_labels, name="구분"),
                dtype=float
            )

        else:
            def _sum_item_nth(name: str, nth: int, years, months):
                sub = df0[(df0["연도"].isin(years)) & (df0["월"].isin(months))]
                total = 0.0
                # (연,월)마다 해당 라벨의 n번째 행만 더한다
                for (_, _), g in sub.groupby(["연도","월"], sort=False):
                    gg = g[g["구분2"] == name].sort_values("__ord__", kind="stable")
                    if len(gg) >= nth:
                        total += float(gg.iloc[nth - 1]["실적"])
                return total

            def _block(years, months):
                return [_sum_item_nth(nm, nth, years, months) for (nm, nth) in order_with_n]

            # 5) 컬럼별 값 계산 & 표 생성
            vals_23   = _block([year-2], range(1, 13))
            vals_24   = _block([year-1], range(1, 13))
            prev_ms   = range(1, used_m) if used_m > 1 else []
            vals_prev = _block([year], prev_ms) if prev_ms else [0.0] * len(order_with_n)
            vals_ytd  = _block([year], range(1, used_m + 1))
            vals_curr = (np.array(vals_ytd) - np.array(vals_prev)).tolist() 

            base = pd.DataFrame(
                {
                    col_prev2_label: vals_23,
                    col_prev1_label: vals_24,
                    "전월누적": vals_prev,
                    "당월": vals_curr,               # 당월
                    col_currsum_label: vals_ytd,     # '25년누적 등, 누적합은 유지
                },
                index=pd.Index(index_labels, name="구분"),
                dtype=float
            )

        # 6) 표시 포맷(괄호표기) – NaN이면 ""로 보이게
        def fmt_cell(x):
            if pd.isna(x): 
                return ""
            try:
                v = float(x)
            except Exception:
                return x
            return f"({abs(int(round(v))):,})" if v < 0 else f"{int(round(v)):,}"

        disp = base.copy()
        for c in disp.columns:
            disp[c] = disp[c].apply(fmt_cell)

        # 7) 스페이서 + 2단 헤더
        disp = disp.reset_index()
        SPACER = "__spacer__"
        disp.insert(0, SPACER, "")

        cols = disp.columns.tolist()
        c_idx = {c:i for i,c in enumerate(cols)}
        yy = str(year)[-2:]
        top_label = f"'{yy} {used_m}월"

        hdr1 = [''] * len(cols)
        hdr2 = [''] * len(cols)

        hdr1[c_idx['구분']]             = '구분'
        hdr1[c_idx[col_prev2_label]]   = col_prev2_label
        hdr1[c_idx[col_prev1_label]]   = col_prev1_label
        hdr2[c_idx['전월누적']]         = '전월누적'
        hdr2[c_idx['당월']]             = '당월'
        hdr1[c_idx[col_currsum_label]] = col_currsum_label

        hdr_df   = pd.DataFrame([hdr1, hdr2], columns=cols)
        disp_vis = pd.concat([hdr_df, disp], ignore_index=True)
        # 26년 1월을 

        # 8) 스타일(심플) – 기존 그대로
        styles = [
            {'selector': 'thead', 'props': [('display','none')]},
            {'selector': 'tbody tr:nth-child(1) td', 'props': [('text-align','center'), ('padding','8px 8px'), ('font-weight','600')]},
            {'selector': 'tbody tr:nth-child(2) td', 'props': [('text-align','center'), ('padding','10px 8px'), ('font-weight','600')]},
            {'selector': 'tbody td:nth-child(1)', 'props': [('width','8px'), ('border-right','0')]},
            {'selector': 'tbody tr:nth-child(n+3) td', 'props': [('text-align','right'), ('padding','8px 10px')]},
            {'selector': 'tbody tr:nth-child(n+3) td:nth-child(2)', 'props': [('text-align','left')]},
            {'selector': 'tbody tr:nth-child(3) td', 'props': [('border-top','3px solid gray')]},
            {'selector': 'tbody tr:nth-child(1) td', 'props': [('border-top','3px solid gray')]},
            {'selector': 'td:nth-child(2)', 'props': [('border-right','3px solid gray')]},
        ]

        # 구분 너비 확장
        styles.append({
            'selector': 'tbody td:nth-child(2)',
            'props': [
                ('min-width','220px !important'),
                ('width','220px !important'),
                ('white-space','nowrap')
            ]
        })

        spacer_rules1 = [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child(2)',
                'props': [('text-align','right')]
            }
            for r in (6,7,9,10,11,12,13,20,21,22)
        ]
        styles += spacer_rules1    

        spacer_rules2 = [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child(1)',
                'props': [('border-right','3px solid gray !important')]
            }
            for r in (4,5,6,7,8,9,10,11,12,13,14,16,17,19,20,21,22)
        ]
        styles += spacer_rules2

        spacer_rules2 = [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child(1)',
                'props': [('border-right','2px solid white !important')]
            }
            for r in (1,2,3,15,18,23,24,25)
        ]
        styles += spacer_rules2

        spacer_rules2 = [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child(2)',
                'props': [('border-bottom','3px solid gray !important')]
            }
            for r in (3,14,15,17,18,22,23,24)
        ]
        styles += spacer_rules2

        spacer_rules4 = [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child(2)',
                'props': [('border-top','2px solid white !important')]
            }
            for r in (6,7,9,10,11,12,13,17,20,21,22)
        ]
        styles += spacer_rules4

        spacer_rules5 = [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child(1)',
                'props': [('border-bottom','2px solid white !important')]
            }
            for r in range(1,24)
        ]
        styles += spacer_rules5

        spacer_rules6 = [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child(1)',
                'props': [('border-bottom','3px solid gray !important')]
            }
            for r in (14,17,22,23,24)
        ]
        styles += spacer_rules6

        spacer_rules6 = [
            {
                'selector': f'tbody tr:nth-child(2) td:nth-child({r})',
                'props': [('border-top','2px solid white !important')]
            }
            for r in (2,3,4,7)
        ]
        styles += spacer_rules6

        spacer_rules6 = [
            {
                'selector': f'tbody tr:nth-child(1) td:nth-child({r})',
                'props': [('border-right','2px solid white !important')]
            }
            for r in (5,6)
        ]
        styles += spacer_rules6

        spacer_rules6 = [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child(4)',
                'props': [('border-right','3px solid gray !important')]
            }
            for r in (1,2)
        ]
        styles += spacer_rules6

        spacer_rules6 = [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child(3)',
                'props': [('border-right','3px solid gray !important')]
            }
            for r in (1,2)
        ]
        styles += spacer_rules6

        spacer_rules6 = [
            {
                'selector': f'tbody tr:nth-child(1) td:nth-child({r})',
                'props': [('border-bottom','2px solid white !important')]
            }
            for r in (5,6)
        ]
        styles += spacer_rules6

        spacer_rules6 = [
            {
                'selector': f'tbody tr:nth-child(2) td:nth-child({r})',
                'props': [('border-right','2px solid white !important')]
            }
            for r in (5,6)
        ]
        styles += spacer_rules6

        display_styled_df(disp_vis, styles=styles, already_flat=True)
        display_memo('f_12', year, month)

    except Exception as e:
        st.error(f"현금흐름표 (별도) 생성 중 오류: {e}")




    st.divider()

    st.markdown("<h4>8) 재무상태표 (별도)</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 백만원]</div>", unsafe_allow_html=True)

    
    try:
        # 데이터 로드
        file_name = st.secrets["sheets"]["f_3"]
        raw = pd.read_csv(file_name, dtype=str)

        # 모듈 갱신(수정 반영)
        import importlib
        importlib.invalidate_caches(); importlib.reload(modules)

        # 원하는 행 순서(=구분3 값)
        item_order = [
            '현금및현금성자산','매출채권','재고자산','유형자산','기타','자산총계',
            '매입채무','차입금','기타','부채총계',
            '자본금','이익잉여금','기타','자본총계','부채 및 자본 총계'
        ]

        base = modules.create_bs_from_teuksugang(
            year=int(st.session_state['year']),   
            month=int(st.session_state['month']), 
            data=raw,
            item_order=item_order
        )


        # ─ 표시용 숫자 포맷 ─
        def fmt_cell(x):
            if pd.isna(x):
                return ""
            try:
                v = float(x)
            except Exception:
                return x

            # 0은 표시하지 않고 빈 칸으로
            if v == 0:
                return ""

            # 음수(v < 0) → 괄호, 양수 → 정수 포맷
            return f"({abs(int(round(v))):,})" if v < 0 else f"{int(round(v)):,}"


        disp = base.copy()
        for c in disp.columns:
            disp[c] = disp[c].apply(fmt_cell)

        # ─ 구분을 2열로: 스페이서 컬럼 추가 ─
        disp = disp.reset_index()   # '구분' 컬럼 생성
        SPACER = "__spacer__"
        disp.insert(0, SPACER, "")

        # ─ 3단 헤더(가짜 헤더 3행 삽입) ─
        cols = disp.columns.tolist()
        c_idx = {c: i for i, c in enumerate(cols)}

        gu_i    = c_idx['구분']
        month_i = c_idx['당월']
        diff_i  = c_idx['전월비 증감']

        def _safe_int(x, default=None):
            try:
                return int(x)
            except Exception:
                return default

        # 기준 연도
        year_int = int(st.session_state['year'])

        used_m = _safe_int(base.attrs.get('used_month'))
        if used_m is None:
            used_m = _safe_int(st.session_state.get('month'), 1)

        used_y = year_int  # 손익/BS는 선택연도를 기준연도로 사용

        prev_y = used_y
        prev_m = used_m - 1
        if prev_m <= 0:
            prev_y -= 1
            prev_m += 12

        # 연도 포맷
        yy_used  = f"{used_y % 100:02d}"       # 선택연도 2자리 (예: 26)
        yy_prevY = f"{(used_y - 1) % 100:02d}" # 전년도 2자리 (예: 25)

        # base에서 사용한 컬럼 라벨과 맞추기
        prev_year_col  = f"'{yy_prevY}년말"   # 전년도 12월 잔액 컬럼
        prev_month_col = f"'{yy_used}"       # 전월 잔액 컬럼 (라벨은 그대로)

        top_label = f"'{yy_used} {used_m}월"                  # 예: '26 1월
        prev_text = f"'{prev_y % 100:02d} {prev_m}월"         # 예: '25 12월 (1월 선택 시)


        # 회사별 컬럼(회사명들)만 추출
        company_labels = [
            c for c in cols
            if c not in [SPACER, '구분', prev_year_col, prev_month_col, '당월', '전월비 증감']
        ]

        # ─ 가짜 헤더 구성 ─
        hdr1 = [''] * len(cols)

        hdr2 = [''] * len(cols)
        hdr2[gu_i] = '구분'
        hdr2[c_idx[prev_year_col]]  = prev_year_col          # 예: '24년말, '25년말 ...
        hdr2[c_idx[prev_month_col]] = prev_text              # 예: '25 3월
        hdr2[month_i]               = top_label              # 예: '25 4월
        hdr2[diff_i]                = '전월비 증감'

        hdr3 = [''] * len(cols)
        for k in company_labels:
            hdr3[c_idx[k]] = k

        hdr_df   = pd.DataFrame([hdr1, hdr2, hdr3], columns=cols)
        disp_vis = pd.concat([hdr_df, disp], ignore_index=True)

        last_company_i = max((c_idx[k] for k in company_labels), default=month_i)


        styles = [
            {'selector': 'thead', 'props': [('display','none')]},

            # 헤더 1·2·3행
            {'selector': 'tbody tr:nth-child(1) td', 'props': [('text-align','center'), ('padding','8px 8px'),  ('line-height','1.1'), ('font-weight','600')]},
            {'selector': 'tbody tr:nth-child(2) td', 'props': [('text-align','center'), ('padding','10px 8px'), ('line-height','1.4'), ('font-weight','600')]},
            {'selector': 'tbody tr:nth-child(2) td:nth-child(2)', 'props': [('text-align','center')]},
            {'selector': 'tbody tr:nth-child(3) td', 'props': [('text-align','center'), ('padding','14px 10px'), ('line-height','1.7'), ('font-weight','600')]},

            # 1열 얇게
            {'selector': 'tbody td:nth-child(1)', 'props': [('width','8px'), ('border-right','0')]},


            # 본문
            {'selector': 'tbody tr:nth-child(n+4) td', 'props': [('line-height','1.45'), ('padding','8px 10px'), ('text-align','right')]},
            {'selector': 'tbody tr:nth-child(n+4) td:nth-child(2)', 'props': [('text-align','left')]},
        ]

        spacer_rules1 = [
                {
                    'selector': f'tbody tr:nth-child(1)',
                    'props': [('border-top','3px solid gray !important')]
                
                }


            ]

        styles += spacer_rules1

        spacer_rules1 = [
                    {
                        'selector': f'tbody tr:nth-child({r}) td:nth-child(2)',
                        'props': [('text-align','left')]
                    
                    }
                    for r in range(4,19)
                ]
        
        styles += spacer_rules1
        

        spacer_rules2 = [
                    {
                        'selector': f'tbody tr:nth-child({r}) td:nth-child(2)',
                        'props': [('border-left','3px solid gray ')],
                    
                    }
                    for r in (4,5,6,7,8,10,11,12,14,15,16)
                ]
        
        
        styles  += spacer_rules2

        spacer_rules2 = [
                    {
                        'selector': f'tbody tr:nth-child({r}) td:nth-child(2)',
                        'props': [('border-left','2px solid white ')],
                    
                    }
                    for r in (9,13,17,18)
                ]
        
        
        styles  += spacer_rules2

        spacer_rules3 = [
                    {
                        'selector': f'tbody tr:nth-child({r}) td:nth-child(2)',
                        'props': [('border-top','3px solid gray ')],
                    
                    }
                    for r in (9,10,13,14,17,18)
                ]
        
        styles  += spacer_rules3

        spacer_rules4 = [
                    {
                        'selector': f'tbody tr:nth-child({r}) td:nth-child(1)',
                        'props': [('border-bottom','2px solid white ')],
                    
                    }
                    for r in range(4,18)
                ]
        
        styles  += spacer_rules4

        spacer_rules5 = [
                    {
                        'selector': f'tbody tr:nth-child({r}) td:nth-child(1)',
                        'props': [('border-bottom','3px solid gray ')],
                    
                    }
                    for r in (3,9,13,17)
                ]
        
        styles  += spacer_rules5

        spacer_rules5 = [
                    {
                        'selector': f'tbody tr:nth-child(3) td:nth-child(2)',
                        'props': [('border-bottom','3px solid gray ')],
                    
                    }

                ]
        
        styles  += spacer_rules5        

        spacer_rules5 = [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child(3)',
                'props': [('border-left','3px solid gray ')]
               
            }

            for r in range(4,19)
        ]
        

        styles += spacer_rules5

        ####feature 구분####

        #행 구분

        spacer_rules5 = [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child({j})',
                'props': [('border-top','2px solid white ')]
               
            }
            # for r in (4,5,8,14,15)
            for r in (2,3)
            for j in (1,2,3,4)
        ]


        styles += spacer_rules5

        spacer_rules5 = [
            {
                'selector': f'tbody tr:nth-child(2) td:nth-child({j})',
                'props': [('border-top','3px solid gray ')]
               
            }

            for j in (5,10)
        ]

        styles += spacer_rules5

        spacer_rules5 = [
            {
                'selector': f'tbody tr:nth-child(2) td:nth-child({j})',
                'props': [('border-top','2px solid white ')]
               
            }

            for j in (6,7,8,9)
        ]

        styles += spacer_rules5

        spacer_rules5 = [
            {
                'selector': f'tbody tr:nth-child(1) td:nth-child({j})',
                'props': [('border-top','2px solid white ')]
               
            }

            for j in (7,8,9,10)
        ]
        

        styles += spacer_rules5

        spacer_rules5 = [
            {
                'selector': f'tbody tr:nth-child(3) td:nth-child({j})',
                'props': [('border-top','3px solid gray ')]
               
            }

            for j in range (6,10)
        ]

        styles += spacer_rules5

        spacer_rules5 = [
            {
                'selector': f'tbody tr:nth-child(4) td:nth-child({j})',
                'props': [('border-top','3px solid gray ')]
               
            }
            for j in range(3,11)
        ]
        

        styles += spacer_rules5

        spacer_rules5 = [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child({j})',
                'props': [('border-right','3px solid gray ')]
               
            }

            for r in range (1,4)
            for j in range (2,5)
        ]
        styles += spacer_rules5


        spacer_rules5 = [
            {
                'selector': f'tbody tr:nth-child(1) td:nth-child(5)',
                'props': [('border-right','3px solid gray ')]
               
            }

        ]
        styles += spacer_rules5


        spacer_rules5 = [
            {
                'selector': f'tbody tr:nth-child(3) td:nth-child({j})',
                'props': [('border-top','2px solid white ')]
               
            }

            for j in (5,10)
        ]
        styles += spacer_rules5

        spacer_rules5 = [
            {
                'selector': f'tbody tr:nth-child(1) td:nth-child(10)',
                'props': [('border-right','2px solid white ')]
               
            }

        ]
        styles += spacer_rules5


        spacer_rules5 = [
            {
                'selector': f'tbody tr:nth-child(2) td:nth-child(5)',
                'props': [('border-right','3px solid gray ')],
                
            }



        ]
        styles += spacer_rules5

        spacer_rules5 = [
            {
                'selector': f'tbody tr:nth-child(3) td:nth-child(5)',
                'props': [('border-right','3px solid gray ')],
                
            }



        ]
        styles += spacer_rules5

        spacer_rules5 = [
            {
                'selector': f'tbody tr:nth-child(3) td:nth-child(6)',
                'props': [('border-top','3px solid white ')],
                
            }



        ]
        styles += spacer_rules5

        
        spacer_rules5 = [
            {
                'selector': f'tbody tr:nth-child(2) td:nth-child(5)',
                'props': [('border-top','3px solid white ')],
                
            }



        ]
        styles += spacer_rules5

        spacer_rules5 = [
            {
                
                'selector': f'tbody tr:nth-child(2) td:nth-child(10)',
                'props': [('border-left','3px solid gray ')]
               
            }



        ]
        styles += spacer_rules5




        spacer_rules5 = [
            {
                'selector': f'tbody tr:nth-child(2) td:nth-child({j})',
                'props': [('border-under','2px solid white !important')],
                
            }

            for j in range(5,6)



        ]
        styles += spacer_rules5

        spacer_rules10 = [
            {
                
                'selector': f'tbody tr:nth-child({r}) td:nth-child(1)',
                'props': [('border-right','2px solid white ')],

               
            }
            for r in range (1,4)


        ]
        styles += spacer_rules10


        display_styled_df(
            disp_vis,
            styles=styles,
            already_flat=True
        )
        display_memo('f_13', year, month)

    except Exception as e:
        st.error(f"재무상태표 생성 중 오류: {e}")
##

    ##### 안정성 별도 #####
    st.divider()

    st.markdown("<h4>9) 안정성 (별도)</h4>", unsafe_allow_html=True)

    st.divider()

    col_left, col_mid, col_right = st.columns([1, 0.05, 1])

    with col_left:

        st.markdown("<h4>10) 회전일 (별도)</h4>", unsafe_allow_html=True)


        try:
            file_name = st.secrets["sheets"]["f_4"]
            raw = pd.read_csv(file_name, dtype=str)

            # 최신 modules 반영


            # 본사 전용 표 생성 
            snap = modules.create_turnover_special_steel(
                year=int(st.session_state['year']),
                month=int(st.session_state['month']),
                data=raw
            )

            # ─ 표시용 포맷: 소수1자리, NaN은 공란 ─
            def fmt1(x):
                try:
                    v = float(x)
                    return f"{v:.2f}" if pd.notnull(v) else ""
                except Exception:
                    return x

            # 인덱스 이름 부여 후 1열로 올리기
            disp = snap.copy()
            disp.index.name = '구분'
            disp = disp.reset_index()
            disp = disp.applymap(fmt1)

            cols = disp.columns.tolist()

            if '전월대비' in cols:
                nth_delta = cols.index('전월대비') + 1
            else:
                nth_delta = len(cols)  # 안전장치


            try:
                ccc_row_idx = disp.index[disp['구분'] == '현금전환주기'][0] + 1
            except Exception:
                ccc_row_idx = None

            styles = [

                {'selector': 'thead th', 'props': [('text-align','center'),
                                                ('padding','10px 8px'),
                                                ('font-weight','700'),
                                                ('border-top','3px solid gray !important')]},

                {'selector': 'tbody td', 'props': [('text-align','right'), ('padding','8px 10px')]},

                {'selector': 'tbody td:first-child', 'props': [('text-align','center')]},

            ]
            spacer_rules1 = [
                {
                    'selector': f'tbody tr:nth-child(1)',
                    'props': [('border-top','3px solid gray !important')]
                
                }


            ]

            styles += spacer_rules1

            spacer_rules1 = [
                {
                    'selector': f'tbody td:nth-child(1)',
                    'props': [('border-right','3px solid gray !important')]
                
                }


            ]

            styles += spacer_rules1


            display_styled_df(disp, styles=styles, already_flat=True)

            display_memo('f_15', year, month)

        except Exception as e:
            st.error(f"회전일 표 생성 중 오류: {e}")





    with col_mid:
        st.markdown("<div class='v-divider'></div>", unsafe_allow_html=True)


    with col_right:

        st.markdown("<h4>11) 수익성 (별도)</h4>", unsafe_allow_html=True)


        try:
            file_name = st.secrets["sheets"]["f_16"]
            raw = pd.read_csv(file_name, dtype=str)

            # 본사 전용 표 생성 
            snap = modules.create_profitability_special_steel(
                year=int(st.session_state['year']),
                month=int(st.session_state['month']),
                data=raw
            )


            # ─ 표시용 포맷: 소수1자리, NaN은 공란 ─
            def fmt1(x):
                try:
                    v = float(x)
                    return f"{v:.2f}" if pd.notnull(v) else ""
                except Exception:
                    return x

            # 인덱스 이름 부여 후 1열로 올리기
            disp = snap.copy()
            disp.index.name = '구분'
            disp = disp.reset_index()
            disp = disp.applymap(fmt1)

            cols = disp.columns.tolist()

            if '전월대비' in cols:
                nth_delta = cols.index('전월대비') + 1
            else:
                nth_delta = len(cols)  # 안전장치


            # try:
            #     ccc_row_idx = disp.index[disp['구분'] == '현금전환주기'][0] + 1
            # except Exception:
            #     ccc_row_idx = None

            styles = [

                {'selector': 'thead th', 'props': [('text-align','center'),
                                                ('padding','10px 8px'),
                                                ('font-weight','700'),
                                                ('border-top','3px solid gray !important')]},

                {'selector': 'tbody td', 'props': [('text-align','right'), ('padding','8px 10px')]},

                {'selector': 'tbody td:first-child', 'props': [('text-align','center')]},

            ]

            spacer_rules1 = [
                {
                    'selector': f'tbody tr:nth-child(1)',
                    'props': [('border-top','3px solid gray !important')]
                
                }



            ]

            styles += spacer_rules1

            spacer_rules1 = [
                {
                    'selector': f'tbody td:nth-child(1)',
                    'props': [('border-right','3px solid gray !important')]
                
                }


            ]

            styles += spacer_rules1


            display_styled_df(disp, styles=styles, already_flat=True)

            display_memo('f_16', year, month)

        except Exception as e:
            st.error(f"수익 표 생성 중 오류: {e}")
            
    # ─ 가로 스크롤 래퍼 닫기 ─
    st.markdown(
        """
        </div>
        </div>
        """,
        unsafe_allow_html=True
    )


# 연간사업계획
# =========================
with t3:
    st.markdown("<h4>1) 판매계획 및 실적</h4>", unsafe_allow_html=True)

    try:
        file_name = st.secrets["sheets"]["f_17"]
        raw = pd.read_csv(file_name, dtype=str)

        import importlib
        importlib.invalidate_caches()
        importlib.reload(modules)

        base = modules.create_sales_plan_vs_actual(
            year=int(st.session_state['year']),
            month=int(st.session_state['month']),
            data=raw
        )

        # 숫자 포맷
        def fmt_signed(x: float, decimals=0):
            try:
                if x is None:
                    return ""
                v = float(x)
                if pd.isna(v):
                    return ""
                neg = v < 0
                v_abs = abs(v)
                s = f"{v_abs:,.{decimals}f}" if decimals > 0 else f"{int(v_abs):,}"
                return f"<span style='color:#d32f2f'>-{s}</span>" if neg else s
            except Exception:
                return ""

        def fmt_pct(x):
            return fmt_signed(x, 0)  # 

        def to_numeric(s):
            return pd.to_numeric(s, errors="coerce")

        # ─ 2행 헤더(가짜) 구성
        disp = base.copy()
        disp.index.name = "구분"
        disp = disp.reset_index()

        SP = "__sp__"
        disp.insert(0, SP, "")

        cols = list(disp.columns)
        c = {k: i for i, k in enumerate(cols)}

        label_candidates = [col for col in cols if isinstance(col, str) and col != SP]
        label_col = '구분' if '구분' in cols else (label_candidates[0] if label_candidates else cols[1])

        valid_groups = {"사업 계획(연간)", "사업 계획(누적)", "실적(누적)", "실적-계획", "달성률(%)"}

        gu_i    = c_idx['구분']
        hdr1 = [''] * len(cols); hdr1[gu_i] = '구분'


        for col in cols:
            if not (isinstance(col, tuple) and len(col) >= 2):
                continue
            grp, metric = col[0], str(col[1]).strip()

            # 달성률(%)는 '판매량' 위에만 표시
            if grp == "달성률(%)" and metric == "판매량":
                hdr1[c[col]] = grp
            # 그 외 그룹은 '단가' 위에만 표시
            elif grp in valid_groups - {"달성률(%)"} and metric == "단가":
                hdr1[c[col]] = grp
            # 나머지 칸(판매량/매출액 위)은 공란 유지

        hdr2 = [""] * len(cols)
        hdr2[c[label_col]] = label_col
        for col in cols:
            if isinstance(col, tuple) and len(col) >= 2:
                hdr2[c[col]] = col[1]


        header_df = pd.DataFrame([hdr1, hdr2], columns=cols)
        disp_vis  = pd.concat([header_df, disp], ignore_index=True)

        # ─ 본문 데이터(3행~)
        body = disp_vis.iloc[2:].copy()

        

        # 1) 단위 연산

        def round_then_strip(v, round_place, strip_factor):
            if pd.isna(v):
                return np.nan
            r = np.round(float(v), round_place)   
            return int(r // strip_factor)         

        disp_values = body.copy()

        for col in disp_values.columns:
            if not (isinstance(col, tuple) and len(col) >= 2):
                continue
            metric = str(col[1]).strip()
            if metric == "단가":
                    s = to_numeric(disp_values[col])

                    disp_values[col] = s.apply(
                        lambda v: (
                            np.nan if pd.isna(v) else
                            int(float(v)) if abs(float(v)) < 100_000 else   #10만 미만은 그대로 출력
                            round_then_strip(v, -2, 1000)                   
                        )
                    )

            elif metric == "매출액":
                s = to_numeric(disp_values[col])
                # 만의자리 반올림 
                disp_values[col] = s.apply(lambda v: round_then_strip(v, -3, 1000))

            elif metric == "판매량":
                s = to_numeric(disp_values[col])
                #  백만 이상일 때만 10만자리 반올림 → 10만 단위 표기
                disp_values[col] = s.apply(
                    lambda v: (round_then_strip(v, -3, 1000)
                            if (not pd.isna(v) and abs(float(v)) >= 1_000_000)
                            else (np.nan if pd.isna(v) else int(float(v))))
                )
        
        # 2) 실적 - 계획

        if (("사업 계획(누적)", "판매량") in disp_values.columns) and (("실적(누적)", "판매량") in disp_values.columns):
            p = to_numeric(disp_values[("사업 계획(누적)", "판매량")])
            a = to_numeric(disp_values[("실적(누적)", "판매량")])
            if ("실적-계획", "판매량") in disp_values.columns:
                disp_values[("실적-계획", "판매량")] = (a - p).round(0).astype("Int64")
            if ("달성률(%)", "판매량") in disp_values.columns:
                with np.errstate(divide='ignore', invalid='ignore'):
                    disp_values[("달성률(%)", "판매량")] = np.where((~pd.isna(p)) & (p != 0), (a / p) * 100.0, np.nan)
        
        if (("사업 계획(누적)", "매출액") in disp_values.columns) and (("실적(누적)", "매출액") in disp_values.columns):
            p = to_numeric(disp_values[("사업 계획(누적)", "매출액")])
            a = to_numeric(disp_values[("실적(누적)", "매출액")])
            if ("실적-계획", "매출액") in disp_values.columns:
                disp_values[("실적-계획", "매출액")] = (a - p).round(0).astype("Int64")
            if ("달성률(%)", "매출액") in disp_values.columns:
                with np.errstate(divide='ignore', invalid='ignore'):
                    disp_values[("달성률(%)", "매출액")] = np.where((~pd.isna(p)) & (p != 0), (a / p) * 100.0, np.nan)
        


        # ===== ④ 포맷(음수 빨간색): 판매량/단가/매출액=정수, 달성률=소수1자리 =====
        body = disp_values.copy()
        for col in body.columns:
            if not (isinstance(col, tuple) and len(col) >= 2):
                continue
            metric = str(col[1]).strip()
            if metric in ("판매량", "단가", "매출액"):
                body[col] = body[col].apply(lambda x: fmt_signed(x, 0))

        for metric in ["판매량", "매출액"]:
            col = ("달성률(%)", metric)
            if col in body.columns:
                body[col] = body[col].apply(fmt_pct)

        # 헤더+본문 결합
        disp_vis = pd.concat([disp_vis.iloc[:2], body], ignore_index=True)


        # ─ 스타일
        styles = [
            {'selector':'thead','props':[('display','none')]},
            {'selector':'tbody tr:nth-child(1) td','props':[('text-align','center'),('font-weight','600')]},
            {'selector':'tbody tr:nth-child(2) td','props':[('text-align','center'),('font-weight','600')]},
            {'selector':'tbody td:nth-child(1)','props':[('width','6px'),('border-right','0')]},
            {'selector':'tbody tr:nth-child(n+3) td','props':[('text-align','right')]},
            {'selector':'tbody tr:nth-child(n+3) td:nth-child(2)','props':[('text-align','left')]},  # 구분

            {'selector':'tbody td:nth-child(2)','props':[('min-width','400px'),('width','400px'),('white-space','nowrap')]},
        ]

        spacer_rules1 = [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child(2)',
                'props': [('text-align','right')]
               
            }
            for r in (3,4,5,6)
        ]

        styles += spacer_rules1

        spacer_rules2 = [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child(2)',
                'props': [('text-align','center')]
               
            }
            for r in (7,8,12,13,19,20)
        ]

        styles += spacer_rules2

        spacer_rules3 = [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child(2)',
                'props': [('border-bottom','2px solid white')]
               
            }
            for r in (1,3,4,5,6,7,8,9,12,13,14,16,18,19)
        ]

        styles += spacer_rules3

        spacer_rules4 = [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child(1)',
                'props': [('border-bottom','2px solid white')]
               
            }
            for r in (1,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19)
        ]



        styles += spacer_rules4

        spacer_rules5 = [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child(2)',
                'props': [('border-left','3px solid gray')]
               
            }
            for r in (3,4,5,6,7,8,9,10,12,13,14,15)
        ]

        styles += spacer_rules5

        spacer_rules6 = [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child(2)',
                'props': [('border-bottom','3px solid gray')]
               
            }
            for r in (2,10,11,15,17)
        ]

        styles += spacer_rules6

        spacer_rules7 = [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child(1)',
                'props': [('border-bottom','3px solid gray')]
               
            }
            for r in (2,11,17)
        ]

        styles += spacer_rules7

        spacer_rules8 = [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child(2)',
                'props': [('border-left','2px solid white')]
               
            }
            for r in (1,2,11,16,17,18,19,20)
        ]

        styles += spacer_rules8

        spacer_rules9 = [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child(2)',
                'props': [('border-right','3px solid gray')]
               
            }
            for r in range (3,21)
        ]

        styles += spacer_rules9


        spacer_rules9 = [
            {
                'selector': f'tbody tr:nth-child(1) td:nth-child({r})',
                'props': [('border-right','2px solid white')]
               
            }
            for r in (3,4,6,7,9,10,12,13,15)
        ]

        styles += spacer_rules9

        spacer_rules9 = [
            {
                'selector': f'tbody tr:nth-child(2) td:nth-child({r})',
                'props': [('border-bottom','3px solid gray')]
               
            }
            for r in range (3,17)
        ]

        styles += spacer_rules9

        spacer_rules9 = [
            {
                'selector': f'tbody tr:nth-child(1) td:nth-child({r})',
                'props': [('border-top','3px solid gray')]
               
            }
            for r in range (1,17)
        ]

        styles += spacer_rules9

        # HTML 그대로 렌더(escape 안 함)해야 빨간색 표시가 보입니다.
        display_styled_df(disp_vis, styles=styles, already_flat=True)
        display_memo('f_17', year, month)

    except Exception as e:
        st.error(f"판매계획 및 실적 표 생성 중 오류: {e}")






st.markdown("""
<style>.footer { bottom: 0; left: 0; right: 0; padding: 8px; text-align: center; font-size: 13px; color: #666666;}</style>
<div class="footer">ⓒ 2025 SeAH Special Steel Corp. All rights reserved.</div>
""", unsafe_allow_html=True)