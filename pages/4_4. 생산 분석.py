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

def display_styled_df_keep_index(df, styles=None, highlight_cols=None, fmt_int=True,align="left"):
    """
    인덱스를 reset_index()하지 않고 그대로 렌더링합니다.
    - Pandas Styler가 인덱스 셀에 th.row_heading.level* 클래스를 붙여줍니다.
    - highlight_cols: 배경 강조할 컬럼 라벨 리스트(문자열). 예) ['24년 월평균','25년 목표','합계','월평균']
    - fmt_int=True: 숫자형을 천단위 콤마로 표시
    - styles: set_table_styles에 그대로 전달할 추가 CSS [{selector:'...', props:[('k','v'), ...]}]
    """
    styled = df.style

    # 숫자 포맷
    if fmt_int:
        styled = styled.format(
            lambda x: f"{x:,.0f}"
            if isinstance(x, (int, float, np.integer, np.floating)) and pd.notnull(x)
            else x
        )

    # 강조 컬럼 (배경)
    if highlight_cols:
        hi = set(map(str, highlight_cols))
        def _hi(col):
            return ['background-color: #f0f0f0'] * len(col) if str(col.name) in hi else [''] * len(col)
        styled = styled.apply(_hi, axis=0)

    # 기본 스타일
    base_css = [
        {'selector': 'table', 'props': [('border-collapse', 'separate'), ('border-spacing', '0')]},
        {'selector': 'th, td', 'props': [('border', '1px solid #cfcfcf'), ('padding', '6px 8px')]},
        {'selector': 'thead th', 'props': [('border-bottom', '2px solid #888'), ('text-align', 'center')]},
        {'selector': 'th.row_heading', 'props': [('background-color', '#fff')]}
    ]
    if styles:
        base_css.extend(styles)
    styled = styled.set_table_styles(base_css)

    # 공통 글꼴/정렬
    styled = styled.set_properties(**{'text-align': 'right', 'font-family': 'Noto Sans KR'})

    # 렌더링
    html = styled.to_html()  # 인덱스는 그대로(th.row_heading.level*)
    if align == "center":
        wrapper = f"<div style='display:flex; justify-content:center;'>{html}</div>"
    elif align == "right":
        wrapper = f"<div style='display:flex; justify-content:flex-end;'>{html}</div>"
    else:  # left
        wrapper = f"<div style='display:flex; justify-content:flex-start;'>{html}</div>"

    st.markdown(wrapper, unsafe_allow_html=True)

def display_styled_df(df, styles=None, highlight_cols=None,align="left"):
    """
    - 행 멀티인덱스는 reset_index()로 컬럼 승격 → 왼쪽 숫자 인덱스 제거
    - reset_index()로 생길 수 있는 '중복 컬럼명' 자동 고유화
    - Styler.hide(axis="index")로 인덱스 헤더까지 숨김
    """
    # 1) 멀티인덱스(행) → 컬럼 승격
    df_for_style = df.reset_index()

    # 2) 중복 컬럼명 자동 고유화 (예: '', '', '구분'...)
    new_cols = []
    seen = {}
    for c in df_for_style.columns:
        c_str = str(c)
        if c_str in seen:
            seen[c_str] += 1
            new_cols.append(f"{c_str}.{seen[c_str]}")  # ex) ''.1, ''.2
        else:
            seen[c_str] = 0
            new_cols.append(c_str)
    df_for_style.columns = new_cols

    # 3) 강조 컬럼 스타일
    hi_set = set(map(str, (highlight_cols or [])))
    def highlight_columns(col):
        return ['background-color: #f0f0f0'] * len(col) if str(col.name) in hi_set else [''] * len(col)

    # 4) 스타일 지정 + 인덱스 완전 숨김
    styled_df = (
        df_for_style.style
        .format(lambda x: f"{x:,.0f}" if isinstance(x, (int, float, np.integer, np.floating)) and pd.notnull(x) else x)
        .set_properties(**{'text-align': 'right', 'font-family': 'Noto Sans KR'})
        .apply(highlight_columns, axis=0)
        .hide(axis="index")
    )
    if styles:
        styled_df = styled_df.set_table_styles(styles)

    # 5) 렌더
    table_html = styled_df.to_html()
    if align == "center":
        wrapper = f"<div style='display:flex; justify-content:center;'>{table_html}</div>"
    elif align == "right":
        wrapper = f"<div style='display:flex; justify-content:flex-end;'>{table_html}</div>"
    else:  # left
        wrapper = f"<div style='display:flex; justify-content:flex-start;'>{table_html}</div>"

    st.markdown(wrapper, unsafe_allow_html=True)

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

st.markdown(f"## {year}년 {month}월 생산 분석")
t1, t2, t3 = st.tabs(['전체 생산실적', '부적합 발생내역_포항공장', '부적합 발생내역_충주 1,2공장'])
st.divider()

# =========================
# 전체 생산실적
# =========================
with t1:
    st.markdown("<h4>1) 전체 생산실적</h4>", unsafe_allow_html=True)

    # 표 우측 상단 단위
    unit = "<div style='text-align:left; font-size:14px; color:#666;'>[단위: 톤]</div>"
    st.markdown(unit, unsafe_allow_html=True)

    try:
        raw40 = load_f40(st.secrets['sheets']['f_40'])

        df_board = modules.create_board_summary_table(
            year, month, raw40,
            base_year=year,  # 현재 선택연도 기준
            prev_year_for_avg=year - 1  # 전년 평균
        )

        # 숫자 포맷팅
        df_show = df_board.copy()

        def _fmt_diff(x):
            try:
                xi = int(round(float(x)))
                return f"({abs(xi):,})" if xi < 0 else f"{xi:,}"
            except Exception:
                return x

        def _fmt_pct(x):
            try:
                return f"{float(x):.1f}%"
            except Exception:
                return x

        for c in df_show.columns:
            if c == "전월대비":
                df_show[c] = df_show[c].apply(_fmt_diff)
            elif c == "%":
                df_show[c] = df_show[c].apply(_fmt_pct)
            else:
                df_show[c] = df_show[c].apply(
                    lambda v: f"{int(v):,}" if isinstance(v, (int, float, np.integer, np.floating)) and not pd.isna(v) else v
                )

        # 등급별 보더 스타일 유사 적용
        border_rows = []
        for i, (g, sub) in enumerate(df_board.index, start=1):
            if g in ["CHQ", "CD", "STS", "BTB", "PB", "합계"]:
                border_rows.append(i)

        styles_prod = []

        

        # 1행 2열(첫 번째 데이터 행의 두 번째 셀)
        styles_prod.append({'selector': 'thead th', 'props': [('text-align','center'),
                                                ('padding','10px 8px'),
                                                ('font-weight','700'),
                                                ('border-top','3px solid gray !important')]},)

        styles_prod.append({
            'selector': 'tbody tr:nth-child(1) td:nth-child(2)',

            'props': [('border-left', '3px solid grey !important')]
        })

        styles_prod.append({
            'selector': 'tbody tr:nth-child(1) td:nth-child(2)',

            'props': [('border-bottom', '2px solid white !important')]
        })
        styles_prod.append({
            'selector': 'tbody tr:nth-child(2) td:nth-child(2)',

            'props': [('border-left', '3px solid grey !important')]
        })
        styles_prod.append({
            'selector': 'tbody tr:nth-child(2) td:nth-child(2)',

            'props': [('border-bottom', '2px solid white !important')]
        })
        styles_prod.append({
            'selector': 'tbody tr:nth-child(3) td:nth-child(2)',

            'props': [('border-left', '2px solid white !important')]
        })

        styles_prod.append({
            'selector': 'tbody tr:nth-child(3) td:nth-child(1)',

            'props': [('border-top', '3px solid grey !important')]
        })


        ######cd
        styles_prod.append({
            'selector': 'tbody tr:nth-child(4) td:nth-child(2)',

            'props': [('border-left', '3px solid grey !important')]
        })

        styles_prod.append({
            'selector': 'tbody tr:nth-child(4) td:nth-child(2)',

            'props': [('border-bottom', '2px solid white !important')]
        })
        styles_prod.append({
            'selector': 'tbody tr:nth-child(5) td:nth-child(2)',

            'props': [('border-left', '3px solid grey !important')]
        })
        styles_prod.append({
            'selector': 'tbody tr:nth-child(5) td:nth-child(2)',

            'props': [('border-bottom', '2px solid white !important')]
        })
        styles_prod.append({
            'selector': 'tbody tr:nth-child(6) td:nth-child(2)',

            'props': [('border-left', '2px solid white !important')]
        })

        styles_prod.append({
            'selector': 'tbody tr:nth-child(6) td:nth-child(1)',

            'props': [('border-top', '3px solid grey !important')]
        })


        ###sts
        styles_prod.append({
            'selector': 'tbody tr:nth-child(7) td:nth-child(2)',

            'props': [('border-left', '3px solid grey !important')]
        })

        styles_prod.append({
            'selector': 'tbody tr:nth-child(7) td:nth-child(2)',

            'props': [('border-bottom', '2px solid white !important')]
        })
        styles_prod.append({
            'selector': 'tbody tr:nth-child(8) td:nth-child(2)',

            'props': [('border-left', '3px solid grey !important')]
        })
        styles_prod.append({
            'selector': 'tbody tr:nth-child(8) td:nth-child(2)',

            'props': [('border-bottom', '2px solid white !important')]
        })
        styles_prod.append({
            'selector': 'tbody tr:nth-child(9) td:nth-child(2)',

            'props': [('border-left', '2px solid white !important')]
        })

        styles_prod.append({
            'selector': 'tbody tr:nth-child(9) td:nth-child(1)',

            'props': [('border-top', '3px solid grey !important')]
        })
        styles_prod.append({
            'selector': 'tbody tr:nth-child(10) td:nth-child(2)',

            'props': [('border-left', '2px solid white !important')]
        })

        styles_prod.append({
            'selector': 'tbody tr:nth-child(11) td:nth-child(2)',

            'props': [('border-left', '2px solid white !important')]
        })
        styles_prod.append({
            'selector': 'tbody tr:nth-child(12) td:nth-child(2)',

            'props': [('border-left', '2px solid white !important')]
        })
        styles_prod.append({
            'selector': 'tbody tr:nth-child(13) td:nth-child(2)',

            'props': [('border-left', '2px solid white !important')]
        })
        styles_prod.append({
            'selector': 'tbody tr:nth-child(14) td:nth-child(2)',

            'props': [('border-left', '2px solid white !important')]
        })
        styles_prod.append({
            'selector': 'tbody tr:nth-child(15) td:nth-child(2)',

            'props': [('border-left', '2px solid white !important')]
        })

        styles_prod.append({
            'selector': 'tbody tr:nth-child(1) td:nth-child(1)',

            'props': [('border-bottom', '2px solid white !important')]
        })

        styles_prod.append({
            'selector': 'tbody tr:nth-child(4) td:nth-child(1)',

            'props': [('border-bottom', '2px solid white !important')]
        })

        styles_prod.append({
            'selector': 'tbody tr:nth-child(7) td:nth-child(1)',

            'props': [('border-bottom', '2px solid white !important')]
        })

        styles_prod.append({
            'selector': 'tbody tr:nth-child(7) td:nth-child(1)',

            'props': [('border-bottom', '2px solid white !important')]
        })

        styles_prod.append({
            'selector': 'tbody tr:nth-child(3)',

            'props': [('border-bottom', '3px solid gray !important')]
        })
        
        styles_prod.append({
            'selector': 'tbody tr:nth-child(6)',

            'props': [('border-bottom', '3px solid gray !important')]
        })

        styles_prod.append({
            'selector': 'tbody tr:nth-child(9)',

            'props': [('border-bottom', '3px solid gray !important')]
        })

        styles_prod.append({
            'selector': 'tbody tr:nth-child(10)',

            'props': [('border-bottom', '3px solid gray !important')]
        })
        styles_prod.append({
            'selector': 'tbody tr:nth-child(11)',

            'props': [('border-bottom', '3px solid gray !important')]
        })

        styles_prod.append({
            'selector': 'tbody tr:nth-child(12)',

            'props': [('border-bottom', '3px solid gray !important')]
        })

        styles_prod.append({
            'selector': 'tbody tr:nth-child(13)',

            'props': [('border-bottom', '3px solid gray !important')]
        })

        styles_prod.append({
            'selector': 'tbody tr:nth-child(14)',

            'props': [('border-bottom', '3px solid gray !important')]
        })

        styles_prod.append({
            'selector': 'tbody tr:nth-child(15)',

            'props': [('border-bottom', '3px solid gray !important')]
        })

        styles_prod.append({
            'selector': 'tbody tr:nth-child(1)',

            'props': [('border-top', '3px solid gray !important')]
        })



        styles_prod.append({
            'selector': f'tbody td:nth-child(2)',
            'props': [('border-right','3px solid gray !important')]
        })

        styles_prod.append({
            'selector': 'thead tr:last-child th:nth-child(1)',  # 마지막 헤더 행의 1열(= 구분)
            'props': [('border-right', '2px solid white !important')]
        })

        

        

        highlight_cols = [f"'{str(year - 1)[-2:]}년 월평균", f"'{str(year)[-2:]}년 월평균", "전월대비", "%"]

        display_styled_df(df_show, styles=styles_prod, highlight_cols=highlight_cols)

        # 표 좌측 하단 집계기준
        foot = "<div style='text-align:left; font-size:13px; color:#666;'>※ 집계기준 : 원재 투입량 + 비가공 + 제품 재가공</div>"
        st.markdown(foot, unsafe_allow_html=True)

        display_memo('f_40', year, month)

    except Exception as e:
        st.error(f"사업부/공장 요약 표를 표시하는 중 오류가 발생했습니다: {e}")

# =========================
# 부적합 발생내역 - 포항
# =========================
with t2:
    st.markdown("<h4>2) 부적합 발생내역 (포항)</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 톤, %]</div>", unsafe_allow_html=True)
    try:
        # 원본 로드
        df_src = load_defect(st.secrets['sheets']['f_41_42'])

        # 1월 ~ 선택월 전체를 컬럼으로 고정 (전년 월평균 / 당년 목표 / 1..선택월 / 합계 / 월평균)
        df_pohang = modules.create_defect_summary_pohang(
            year, month, df_src,
            months_window=tuple(range(1, month + 1)),
            plant_name="포항"
        )

        # 인덱스 헤더 표기: 마지막 레벨만 '구분'
        if isinstance(df_pohang.index, pd.MultiIndex) and df_pohang.index.nlevels == 3:
            df_pohang.index = df_pohang.index.set_names(['', '', '구분'])

        # ── 가짜 헤더 행을 본문 첫 줄에 삽입 ──
        df_inline = with_inline_header_row(
            df_pohang,
            index_names=('', '', '구분'),
            index_values=('', '', '구분')
        )

        # ── 스타일 ──
        # 기존 굵은 경계선 대상(데이터 기준 0-based): [2, 5, 8]
        # 가짜 헤더가 tbody 1행을 차지하므로 nth-child는 +1 보정 → (r + 2)
        thick_rows_data_zero_based = [2, 5, 8]
        styles_def = []
        
        # thead 숨김 + 첫 행을 진짜 헤더처럼
        styles_def.append({'selector': 'thead', 'props': [('display', 'none')]})
        styles_def.append({
            'selector': 'tbody tr:nth-child(1) th, tbody tr:nth-child(1) td',
            'props': [('font-weight', '700'),
                      ('background', '#ffffff'),
                      ]
        })
        styles_def.append({
            'selector': (
                'th.row_heading.level1.row1, '  #  CHQ 라벨 행
                'th.blank.level0, '              # 좌측 공백 인덱스 셀
                'th.row_heading.level2.row1, '   # 빈칸
                'th.row_heading.level2.row2, '   # 공정성
                'th.row_heading.level2.row3'     # 소재성
            ),
            'props': [('border-bottom', '2px solid white !important')]
        })

        styles_def.append({
            'selector': (
                'th.row_heading.level1.row1, '  #  CHQ 라벨 행
                'th.blank.level0, '              # 좌측 공백 인덱스 셀
                'th.row_heading.level2.row1, '   # 빈칸
                'th.row_heading.level2.row2, '   # 공정성
                'th.row_heading.level2.row3'     # 소재성
            ),
            'props': [('border-left', '2px solid white !important')]
        })

        styles_def.append({
            'selector': (
                'th.row_heading.level1.row3, '  # CD 라벨 행
                'th.blank.level0, '              # 좌측 공백 인덱스 셀
                'th.row_heading.level2.row4, '   # 빈칸
                'th.row_heading.level2.row5, '   # 공정성
                'th.row_heading.level2.row6'     # 소재성
            ),
            'props': [('border-bottom', '2px solid white !important')]
        })

        styles_def.append({
            'selector': (
                # 'th.row_heading.level1.row3, '  # CD 라벨 행
                'th.blank.level0, '              # 좌측 공백 인덱스 셀
                'th.row_heading.level2.row4, '   # 빈칸
                'th.row_heading.level2.row5, '   # 공정성
                'th.row_heading.level2.row6'     # 소재성
            ),
            'props': [('border-left', '2px solid white !important')]
        })

        styles_def.append({
            'selector': (
                'th.row_heading.level1.row6, '  # CD 라벨 행
                'th.blank.level0, '              # 좌측 공백 인덱스 셀
                'th.row_heading.level2.row7, '   # 빈칸
                'th.row_heading.level2.row8, '   # 공정성
                'th.row_heading.level2.row9'     # 소재성
            ),
            'props': [('border-bottom', '2px solid white !important')]
        })
        styles_def.append({
            'selector': (
                'th.row_heading.level1.row6, '  # CD 라벨 행
                'th.blank.level0, '              # 좌측 공백 인덱스 셀
                'th.row_heading.level2.row7, '   # 빈칸
                'th.row_heading.level2.row8, '   # 공정성
                'th.row_heading.level2.row9'     # 소재성
            ),
            'props': [('border-bottom', '2px solid white !important')]
        })
        styles_def.append({
            'selector': (
                'th.row_heading.level0.row0, '  # CD 라벨 행
                'th.blank.level0, '              # 좌측 공백 인덱스 셀
                'th.row_heading.level1.row7, '   # 빈칸
                'th.row_heading.level1.row8, '   # 공정성
                  # 소재성
            ),
            'props': [('border-bottom', '2px solid white !important')]
        })

        styles_def.append({
            'selector': (
                'th.row_heading.level0.row0, '  # CD 라벨 행
                'th.blank.level0, '              # 좌측 공백 인덱스 셀
                'th.row_heading.level1.row0, '   # 빈칸
                
                'th.row_heading.level1.row4, '
                
            ),
            'props': [('border-bottom', '2px solid white !important')]
        })

        
        ##
        styles_def.append({
            'selector': (
                'th.row_heading.level2.row6, '  # CD 라벨 행
                # 'th.blank.level0, '              # 좌측 공백 인덱스 셀
                 'th.row_heading.level2.row7, '   # 빈칸
                 'th.row_heading.level2.row8, '   # 공정성
                # 'th.row_heading.level2.row9'     # 소재성
            ),
            'props': [('border-left', '2px solid white !important')]
        })
        ##
        styles_def.append({
            'selector': (
                'th.row_heading.level1.row7, '  # CD 라벨 행
                # 'th.blank.level0, '              # 좌측 공백 인덱스 셀
                 'th.row_heading.level1.row8, '   # 빈칸
                 'th.row_heading.level1.row9, '   # 공정성
                # 'th.row_heading.level2.row9'     # 소재성
            ),
            'props': [('border-left', '2px solid white !important')]
        })
        
        styles_def.append({
            'selector': (
                'th.row_heading.level1.row7, '  # CD 라벨 행
                # 'th.blank.level0, '              # 좌측 공백 인덱스 셀
                'th.row_heading.level1.row0, '
                 'th.row_heading.level1.row1, '   # 빈칸
                 'th.row_heading.level1.row2, '   # 공정성
                 'th.row_heading.level1.row3, '
                 'th.row_heading.level1.row4, '
                 'th.row_heading.level1.row5, '
                 'th.row_heading.level1.row6, '
                 'th.row_heading.level1.row7, '
                # 'th.row_heading.level2.row9'     # 소재성
            ),
            'props': [("border-left", "3px solid grey")]
        })



        styles_def.append({
            "selector": "th.row_heading.level0.row1",  # level1의 row1(0-기반) 한 칸만
            "props": [("border-right", '2px solid white !important')]
        })
        styles_def.append({
            'selector': (
                'th.row_heading.level0.row1, '  # CD 라벨 행
                # 'th.blank.level0, '              # 좌측 공백 인덱스 셀
                # 'th.row_heading.level1.row1, '   # 빈칸
                'th.row_heading.level1.row3, '
                'th.row_heading.level1.row6, '   # 공정성
                'th.row_heading.level1.row9'     # 소재성
                
            ),
            'props': [('border-right', '2px solid white !important')]
        })

        styles_def.append({
            "selector": "th.row_heading.level0",          # level0 인덱스 전체
            "props": [("border-left", "3px solid grey")]  # 왼쪽 굵은 선
        })

        styles_def.append({
            'selector': 'tbody tr:nth-child(1)',

            'props': [('border-top', '3px solid gray !important')]
        })




        

        # 빈 인덱스(th.blank) 회색 배경 제거
        styles_def.append({'selector': 'th.blank', 'props': [('background-color', '#fff !important')]})
        styles_def.append({'selector': 'th.row_heading.blank', 'props': [('background-color', '#fff !important')]})

        # 굵은 가로 경계선(데이터 구간, +1 보정)
        styles_def.extend([
            {'selector': f'tbody tr:nth-child({r + 2})',
             'props': [('border-bottom', '3px solid #666 !important')]}
            for r in thick_rows_data_zero_based
        ])
        # 강조 컬럼
        hl_cols = [f"{str(year - 1)[-2:]}년 월평균", f"{str(year)[-2:]}년 목표", '합계', '월평균']

        # 렌더 (정수 포맷, 소수점 없음)
        display_styled_df_keep_index(
            df_inline,
            styles=styles_def,
            highlight_cols=hl_cols,
            fmt_int=True
        )
        display_memo('f_41', year, month)

    except Exception as e:
        st.error(f"충주 1,2공장 부적합 표 생성 중 오류가 발생했습니다: {e}")
                       
    
# =========================
# 부적합 발생내역 - 충주 1,2공장
# =========================
with t3:
    st.markdown("<h4>3) 부적합 발생내역 (충주 1,2공장)</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 톤, %]</div>", unsafe_allow_html=True)
    try:
        df_src = load_defect(st.secrets['sheets']['f_41_42'])

        # 1월~선택월 전체를 컬럼으로
        all_months = tuple(range(1, month + 1))
        df_cjj = modules.create_defect_summary_chungju(
            year, month, df_src, months_window=all_months,
            plant1_name="충주", plant2_name="충주2"
        )

        # ── (핵심) Styler 호환 위해 행 인덱스 유니크화 ──
        if isinstance(df_cjj.index, pd.MultiIndex) and not df_cjj.index.is_unique:
            new_tuples, seen = [], {}
            for tup in df_cjj.index.tolist():
                if tup in seen:
                    a, b, c = tup
                    b = (b or '') + '\u2009' * seen[tup]  # thin space 덧붙여 시각차 없이 고유화
                    new_tuples.append((a, b, c))
                    seen[tup] += 1
                else:
                    new_tuples.append(tup)
                    seen[tup] = 1
            df_cjj.index = pd.MultiIndex.from_tuples(new_tuples, names=df_cjj.index.names)

        # 인덱스 머리글 설정(마지막 레벨만 '구분')
        if isinstance(df_cjj.index, pd.MultiIndex):
            df_cjj.index = df_cjj.index.set_names(['', '', '구분'])
        else:
            df_cjj.index.name = '구분'

        # 본문 첫 줄에 '헤더용 가짜 행' 삽입
        df_inline = with_inline_header_row(
            df_cjj,
            index_names=df_cjj.index.names if isinstance(df_cjj.index, pd.MultiIndex) else ('', '구분'),
            index_values=tuple([''] * (len(df_cjj.index.names) - 1) + ['구분']) if isinstance(df_cjj.index, pd.MultiIndex) else ('구분',)
        )

        # ── 스타일 ──
        styles_def = []

        # thead 숨기고, 첫 행을 헤더처럼(가짜 헤더 행)
        styles_def.append({'selector': 'thead', 'props': [('display', 'none')]})
        styles_def.append({
            'selector': 'tbody tr:nth-child(1) th, tbody tr:nth-child(1) td',
            'props': [('font-weight', '700'),
                      ('background', '#ffffff')]
        })
        styles_def.append({
            'selector': (
                'th.row_heading.level1.row1, '  #  CHQ 라벨 행
                'th.blank.level0, '              # 좌측 공백 인덱스 셀
                'th.row_heading.level2.row1, '   # 빈칸
                'th.row_heading.level2.row2, '   # 공정성
                'th.row_heading.level2.row3'     # 소재성
            ),
            'props': [('border-bottom', '2px solid white !important')]
        })

        styles_def.append({
            'selector': (
                'th.row_heading.level1.row1, '  #  CHQ 라벨 행
                'th.blank.level0, '              # 좌측 공백 인덱스 셀
                'th.row_heading.level2.row1, '   # 빈칸
                'th.row_heading.level2.row2, '   # 공정성
                'th.row_heading.level2.row3'     # 소재성
            ),
            'props': [('border-left', '2px solid white !important')]
        })

        styles_def.append({
            'selector': (
                'th.row_heading.level1.row3, '  # CD 라벨 행
                'th.blank.level0, '              # 좌측 공백 인덱스 셀
                'th.row_heading.level2.row4, '   # 빈칸
                'th.row_heading.level2.row5, '   # 공정성
                'th.row_heading.level2.row6'     # 소재성
            ),
            'props': [('border-bottom', '2px solid white !important')]
        })

        styles_def.append({
            'selector': (
                # 'th.row_heading.level1.row3, '  # CD 라벨 행
                'th.blank.level0, '              # 좌측 공백 인덱스 셀
                'th.row_heading.level2.row4, '   # 빈칸
                'th.row_heading.level2.row5, '   # 공정성
                'th.row_heading.level2.row6'     # 소재성
            ),
            'props': [('border-left', '2px solid white !important')]
        })

        styles_def.append({
            'selector': (
                'th.row_heading.level1.row6, '  # CD 라벨 행
                'th.blank.level0, '              # 좌측 공백 인덱스 셀
                'th.row_heading.level2.row7, '   # 빈칸
                'th.row_heading.level2.row8, '   # 공정성
                'th.row_heading.level2.row9'     # 소재성
            ),
            'props': [('border-bottom', '2px solid white !important')]
        })
        styles_def.append({
            'selector': (
                'th.row_heading.level1.row6, '  # CD 라벨 행
                'th.blank.level0, '              # 좌측 공백 인덱스 셀
                'th.row_heading.level2.row7, '   # 빈칸
                'th.row_heading.level2.row8, '   # 공정성
                'th.row_heading.level2.row9'     # 소재성
            ),
            'props': [('border-bottom', '2px solid white !important')]
        })
        styles_def.append({
            'selector': (
                'th.row_heading.level0.row0, '  # CD 라벨 행
                'th.blank.level0, '              # 좌측 공백 인덱스 셀
                'th.row_heading.level1.row7, '   # 빈칸
                'th.row_heading.level1.row8, '   # 공정성
                  # 소재성
            ),
            'props': [('border-bottom', '2px solid white !important')]
        })

        styles_def.append({
            'selector': (
                'th.row_heading.level0.row0, '  # CD 라벨 행
                'th.blank.level0, '              # 좌측 공백 인덱스 셀
                'th.row_heading.level1.row0, '   # 빈칸
                
                'th.row_heading.level1.row4, '
                
            ),
            'props': [('border-bottom', '2px solid white !important')]
        })

        
        ##
        styles_def.append({
            'selector': (
                'th.row_heading.level2.row6, '  # CD 라벨 행
                # 'th.blank.level0, '              # 좌측 공백 인덱스 셀
                 'th.row_heading.level2.row7, '   # 빈칸
                 'th.row_heading.level2.row8, '   # 공정성
                # 'th.row_heading.level2.row9'     # 소재성
            ),
            'props': [('border-left', '2px solid white !important')]
        })
        ##
        styles_def.append({
            'selector': (
                'th.row_heading.level1.row7, '  # CD 라벨 행
                # 'th.blank.level0, '              # 좌측 공백 인덱스 셀
                 'th.row_heading.level1.row8, '   # 빈칸
                 'th.row_heading.level1.row9, '   # 공정성
                # 'th.row_heading.level2.row9'     # 소재성
            ),
            'props': [('border-left', '2px solid white !important')]
        })
        
        styles_def.append({
            'selector': (
                'th.row_heading.level1.row7, '  # CD 라벨 행
                # 'th.blank.level0, '              # 좌측 공백 인덱스 셀
                'th.row_heading.level1.row0, '
                 'th.row_heading.level1.row1, '   # 빈칸
                 'th.row_heading.level1.row2, '   # 공정성
                 'th.row_heading.level1.row3, '
                 'th.row_heading.level1.row4, '
                 'th.row_heading.level1.row5, '
                 'th.row_heading.level1.row6, '
                 'th.row_heading.level1.row7, '
                # 'th.row_heading.level2.row9'     # 소재성
            ),
            'props': [("border-left", "3px solid grey")]
        })



        styles_def.append({
            "selector": "th.row_heading.level0.row1",  # level1의 row1(0-기반) 한 칸만
            "props": [("border-right", '2px solid white !important')]
        })
        styles_def.append({
            'selector': (
                'th.row_heading.level0.row1, '  # CD 라벨 행
                # 'th.blank.level0, '              # 좌측 공백 인덱스 셀
                # 'th.row_heading.level1.row1, '   # 빈칸
                'th.row_heading.level1.row3, '
                'th.row_heading.level1.row6, '   # 공정성
                'th.row_heading.level1.row9'     # 소재성
                
            ),
            'props': [('border-right', '2px solid white !important')]
        })

        styles_def.append({
            "selector": "th.row_heading.level0",          # level0 인덱스 전체
            "props": [("border-left", "3px solid grey")]  # 왼쪽 굵은 선
        })

        styles_def.append({
            'selector': 'tbody tr:nth-child(1)',

            'props': [('border-top', '3px solid gray !important')]
        })
        

        # 빈 인덱스(th.blank) 회색 배경 제거
        styles_def.append({'selector': 'th.blank', 'props': [('background-color', '#fff !important')]})
        styles_def.append({'selector': 'th.row_heading.blank', 'props': [('background-color', '#fff !important')]})

        # 굵은 가로 경계선(데이터 구간, +1 보정)
        styles_def.extend([
            {'selector': f'tbody tr:nth-child({r + 2})',
             'props': [('border-bottom', '3px solid #666 !important')]}
            for r in thick_rows_data_zero_based
        ])
        # 강조 컬럼
        hl_cols = [f"{str(year - 1)[-2:]}년 월평균", f"{str(year)[-2:]}년 목표", '합계', '월평균']

        # 렌더 (정수 포맷, 소수점 없음)
        display_styled_df_keep_index(
            df_inline,
            styles=styles_def,
            highlight_cols=hl_cols,
            fmt_int=True
        )

        display_memo('f_42', year, month)

    except Exception as e:
        st.error(f"충주 1,2공장 부적합 표 생성 중 오류가 발생했습니다: {e}")



# =========================
# Footer
# =========================
st.markdown("""
<style>.footer { bottom: 0; left: 0; right: 0; padding: 8px; text-align: center; font-size: 13px; color: #666666;}</style>
<div class="footer">ⓒ 2025 SeAH Special Steel Corp. All rights reserved.</div>
""", unsafe_allow_html=True)