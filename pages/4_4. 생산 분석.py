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


def display_styled_df_keep_index(df, styles=None, highlight_cols=None, fmt_int=True, align="left"):
    styled = df.style

    if fmt_int:
        styled = styled.format(
            lambda x: f"{x:,.0f}"
            if isinstance(x, (int, float, np.integer, np.floating)) and pd.notnull(x)
            else x
        )

    if highlight_cols:
        hi = set(map(str, highlight_cols))

        def _hi(col):
            return ['background-color: #f0f0f0'] * len(col) if str(col.name) in hi else [''] * len(col)

        styled = styled.apply(_hi, axis=0)

    base_css = [
        {'selector': 'table', 'props': [('border-collapse', 'separate'), ('border-spacing', '0')]},
        {'selector': 'th, td', 'props': [('border', '1px solid #cfcfcf'), ('padding', '6px 8px')]},
        {'selector': 'thead th', 'props': [('border-bottom', '2px solid #888'), ('text-align', 'center')]},
        {'selector': 'th.row_heading', 'props': [('background-color', '#fff')]}
    ]
    if styles:
        base_css.extend(styles)
    styled = styled.set_table_styles(base_css)

    styled = styled.set_properties(**{'text-align': 'right', 'font-family': 'Noto Sans KR'})

    html = styled.to_html()
    if align == "center":
        wrapper = f"<div style='display:flex; justify-content:center;'>{html}</div>"
    elif align == "right":
        wrapper = f"<div style='display:flex; justify-content:flex-end;'>{html}</div>"
    else:
        wrapper = f"<div style='display:flex; justify-content:flex-start;'>{html}</div>"

    st.markdown(wrapper, unsafe_allow_html=True)


def display_styled_df(df, styles=None, highlight_cols=None, align="left", already_flat=False):
    """
    - already_flat=True: df가 이미 flat한 형태 (reset_index 생략)
    - 행 멀티인덱스는 reset_index()로 컬럼 승격 → 왼쪽 숫자 인덱스 제거
    - Styler.hide(axis="index")로 인덱스 완전 숨김
    """
    # 1) flat 여부에 따라 reset_index 결정
    if already_flat:
        df_for_style = df.copy()
    else:
        df_for_style = df.reset_index()

    # 2) 중복 컬럼명 자동 고유화
    new_cols = []
    seen = {}
    for c in df_for_style.columns:
        c_str = str(c)
        if c_str in seen:
            seen[c_str] += 1
            new_cols.append(f"{c_str}.{seen[c_str]}")
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
    else:
        wrapper = f"<div style='display:flex; justify-content:flex-start;'>{table_html}</div>"

    st.markdown(wrapper, unsafe_allow_html=True)


def create_indented_html(s):
    content = s.lstrip(' ')
    num_spaces = len(s) - len(content)
    indent_level = num_spaces // 2
    return f'<p class="indent-{indent_level}">{content}</p>'


def display_memo(memo_file_key, year, month, ):
    file_name = st.secrets['memos'][memo_file_key]
    try:
        df_memo = pd.read_csv(file_name)
        df_filtered = df_memo[(df_memo['년도'] == year) & (df_memo['월'] == month)]

        if df_filtered.empty:
            st.warning(f"{year}년 {month}월 메모를 찾을 수 없습니다.")
            return

        memo_text = df_filtered.iloc[0]['메모']
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

st.markdown(f"## {year}년 {month}월 생산 분석")
t1, t2, t3 = st.tabs(['전체 생산실적', '부적합 발생내역_포항공장', '부적합 발생내역_충주 1,2공장'])
st.divider()

# =========================
# =========================
# 전체 생산실적
# =========================
with t1:
    st.markdown("<h4>1) 전체 생산실적</h4>", unsafe_allow_html=True)

    unit = "<div style='text-align:left; font-size:14px; color:#666;'>[단위: 톤]</div>"
    st.markdown(unit, unsafe_allow_html=True)

    try:
        raw40 = load_f40(st.secrets['sheets']['f_40'])

        df_board = modules.create_board_summary_table(
            year, month, raw40,
            base_year=year,
            prev_year_for_avg=year - 1,
            prev2_year_for_avg=year - 2
        )

        # ── 선택월 이후 컬럼 삭제 (26.4, 26.5 등) ──
        year_prefix = f"'{str(year)[-2:]}."
        # ── 선택월 이후 컬럼 삭제 ──
        drop_cols = [
            c for c in df_board.columns
            if c not in ["'24년 월평균", "'25년 월평균", "'26년 월평균", "전월대비", "%"]
               and c.split('.')[-1].isdigit()
               and int(c.split('.')[-1]) > int(month)
        ]
        df_board = df_board.drop(columns=drop_cols, errors='ignore')

        # ── 멀티인덱스 → 1열 구분으로 flat ──
        df_show = df_board.reset_index()
        df_show.columns = ['구분1', '구분2'] + list(df_board.columns)

        def _make_label(row):
            g1 = str(row['구분1']).strip()
            g2 = str(row['구분2']).strip()
            if g1 and g2:
                return g2
            elif g1:
                return g1
            else:
                return g2

        df_show['구분'] = df_show.apply(_make_label, axis=1)
        df_show = df_show.drop(columns=['구분1', '구분2'])
        cols_order = ['구분'] + [c for c in df_show.columns if c != '구분']
        df_show = df_show[cols_order]

        # ── 포맷 함수 ──
        def _fmt_num(x):
            try:
                v = float(x)
                if pd.isna(v): return ""
                return f"{int(round(v)):,}"
            except Exception:
                return x

        def _fmt_diff(x):
            try:
                v = float(x)
                if pd.isna(v): return ""
                xi = int(round(v))
                if xi < 0:
                    return f'<span style="color:red;">-{abs(xi):,}</span>'
                return f"{xi:,}"
            except Exception:
                return x

        def _fmt_pct(x):
            try:
                v = float(x)
                if pd.isna(v): return ""
                if v < 0:
                    return f'<span style="color:red;">-{abs(v):.1f}%</span>'
                return f"{v:.1f}%"
            except Exception:
                return x

        for c in df_show.columns:
            if c == '구분':
                continue
            elif c == '전월대비':
                df_show[c] = df_show[c].apply(_fmt_diff)
            elif c == '%':
                df_show[c] = df_show[c].apply(_fmt_pct)
            else:
                df_show[c] = df_show[c].apply(_fmt_num)

        # ── 스타일 ──
        styles_prod = [
            {'selector': 'table',
             'props': [('border-collapse', 'collapse'), ('width', '100%')]},
            {'selector': 'th, td',
             'props': [('border', '1px solid black'),
                       ('padding', '5px 8px'),
                       ('font-weight', 'normal'),
                       ('color', 'black'),
                       ('font-size', '13px'),
                       ('background-color', 'white')]},
            {'selector': 'thead th',
             'props': [('text-align', 'center'),
                       ('font-weight', 'normal'),
                       ('background-color', 'white'),
                       ('border', '1px solid black')]},
            {'selector': 'tbody td',
             'props': [('text-align', 'right'),
                       ('background-color', 'white')]},
            {'selector': 'tbody td:nth-child(1)',
             'props': [('text-align', 'left'),
                       ('background-color', 'white')]},
        ]

        display_styled_df(
            df_show,
            styles=styles_prod,
            highlight_cols=None,
            already_flat=True
        )

        foot = "<div style='text-align:left; font-size:13px; color:#666;'>※ 집계기준 : 원재 투입량 + 비가공 + 제품 재가공</div>"
        st.markdown(foot, unsafe_allow_html=True)

        display_memo('f_40', year, month)

    except Exception as e:
        st.error(f"사업부/공장 요약 표를 표시하는 중 오류가 발생했습니다: {e}")
# =========================
# 부적합 발생내역 - 포항
# =========================
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

        # ── 컬럼명 시안에 맞게 변경 (선택월 이하만 rename, 초과는 drop) ──
        col_rename = {}
        for c in df_pohang.columns:
            cs = str(c)
            if '월평균' in cs and str(year - 1)[-2:] in cs:
                col_rename[c] = f"{str(year-1)[-2:]}년 월평균"
            elif '목표' in cs:
                col_rename[c] = f"{str(year)[-2:]}년 목표"
            elif cs.isdigit() and int(cs) <= month:   # 선택월 이하만 rename
                col_rename[c] = f"'{str(year)[-2:]}.{int(cs)}"
            elif cs == '합계':
                col_rename[c] = '합계'
            elif '월평균' in cs and str(year)[-2:] in cs:
                col_rename[c] = '월평균'
        if col_rename:
            df_pohang = df_pohang.rename(columns=col_rename)

        # rename 안 된 숫자 컬럼(= 선택월 초과) 삭제
        drop_cols = [c for c in df_pohang.columns if str(c).isdigit()]
        df_pohang = df_pohang.drop(columns=drop_cols)

        # ── 가짜 헤더 행을 본문 첫 줄에 삽입 ──
        df_inline = with_inline_header_row(
            df_pohang,
            index_names=('', '', '구분'),
            index_values=('', '', '구분')
        )

        # ── 스타일 ──
        thick_rows_data_zero_based = [2, 5, 8]
        styles_def = []

        # thead 숨김 + 첫 행을 진짜 헤더처럼
        styles_def.append({'selector': 'thead', 'props': [('display', 'none')]})
        styles_def.append({
            'selector': 'tbody tr:nth-child(1) th, tbody tr:nth-child(1) td',
            'props': [('font-weight', '700'),
                      ('background-color', '#ffffff !important')]
        })

        # 표 내부 전체 흰색
        styles_def.append({
            'selector': 'th, td',
            'props': [('background-color', '#ffffff !important')]
        })
        styles_def.append({
            'selector': 'tbody tr td, tbody tr th',
            'props': [('background-color', '#ffffff !important')]
        })

        # 빈 인덱스(th.blank) 흰색
        styles_def.append({'selector': 'th.blank', 'props': [('background-color', '#fff !important')]})
        styles_def.append({'selector': 'th.row_heading.blank', 'props': [('background-color', '#fff !important')]})

        # 경계선
        styles_def.append({
            'selector': (
                'th.row_heading.level1.row1, '
                'th.blank.level0, '
                'th.row_heading.level2.row1, '
                'th.row_heading.level2.row2, '
                'th.row_heading.level2.row3'
            ),
            'props': [('border-bottom', '2px solid white !important')]
        })
        styles_def.append({
            'selector': (
                'th.row_heading.level1.row1, '
                'th.blank.level0, '
                'th.row_heading.level2.row1, '
                'th.row_heading.level2.row2, '
                'th.row_heading.level2.row3'
            ),
            'props': [('border-bottom', '2px solid white !important')]
        })
        styles_def.append({
            'selector': (
                'th.row_heading.level1.row0, '
                'th.row_heading.level1.row1, '
                'th.row_heading.level1.row2, '
                'th.row_heading.level1.row3, '
                'th.row_heading.level1.row4, '
                'th.row_heading.level1.row5, '
                'th.row_heading.level1.row6, '
                'th.row_heading.level1.row7, '
            ),
            'props': [("border-left", "3px solid grey")]
        })
        styles_def.append({
            "selector": "th.row_heading.level0.row1",
            "props": [("border-right", '2px solid white !important')]
        })
        styles_def.append({
            'selector': (
                'th.row_heading.level0.row1, '
                'th.row_heading.level1.row3, '
                'th.row_heading.level1.row6, '
                'th.row_heading.level1.row9'
            ),
            'props': [('border-right', '2px solid white !important')]
        })
        styles_def.append({
            "selector": "th.row_heading.level0",
            "props": [("border-left", "3px solid grey")]
        })
        styles_def.append({
            'selector': 'tbody tr:nth-child(1)',
            'props': [('border-top', '3px solid gray !important')]
        })

        # 굵은 가로 경계선 (그룹 하단)
        styles_def.extend([
            {'selector': f'tbody tr:nth-child({r + 2})',
             'props': [('border-bottom', '3px solid #666 !important')]}
            for r in thick_rows_data_zero_based
        ])

        # 강조 컬럼
        hl_cols = [f"{str(year - 1)[-2:]}년 월평균", f"{str(year)[-2:]}년 목표", '합계', '월평균']

        display_styled_df_keep_index(
            df_inline,
            styles=styles_def,
            highlight_cols=hl_cols,
            fmt_int=True
        )
        display_memo('f_41', year, month)

    except Exception as e:
        st.error(f"포항 부적합 표 생성 중 오류가 발생했습니다: {e}")

# =========================
# 부적합 발생내역 - 충주 1,2공장
# =========================
with t3:
    st.markdown("<h4>3) 부적합 발생내역 (충주 1,2공장)</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 톤, %]</div>", unsafe_allow_html=True)
    try:
        df_src = load_defect(st.secrets['sheets']['f_41_42'])

        all_months = tuple(range(1, month + 1))
        df_cjj = modules.create_defect_summary_chungju(
            year, month, df_src, months_window=all_months,
            plant1_name="충주", plant2_name="충주2"
        )

        if isinstance(df_cjj.index, pd.MultiIndex) and not df_cjj.index.is_unique:
            new_tuples, seen = [], {}
            for tup in df_cjj.index.tolist():
                if tup in seen:
                    a, b, c = tup
                    b = (b or '') + '\u2009' * seen[tup]
                    new_tuples.append((a, b, c))
                    seen[tup] += 1
                else:
                    new_tuples.append(tup)
                    seen[tup] = 1
            df_cjj.index = pd.MultiIndex.from_tuples(new_tuples, names=df_cjj.index.names)

        if isinstance(df_cjj.index, pd.MultiIndex):
            df_cjj.index = df_cjj.index.set_names(['', '', '구분'])
        else:
            df_cjj.index.name = '구분'

        df_inline = with_inline_header_row(
            df_cjj,
            index_names=df_cjj.index.names if isinstance(df_cjj.index, pd.MultiIndex) else ('', '구분'),
            index_values=tuple([''] * (len(df_cjj.index.names) - 1) + ['구분']) if isinstance(df_cjj.index,
                                                                                            pd.MultiIndex) else ('구분',)
        )

        thick_rows_data_zero_based = [2, 5, 8]
        styles_def = []

        styles_def.append({'selector': 'thead', 'props': [('display', 'none')]})
        styles_def.append({
            'selector': 'tbody tr:nth-child(1) th, tbody tr:nth-child(1) td',
            'props': [('font-weight', '700'), ('background', '#ffffff')]
        })
        styles_def.append({
            'selector': (
                'th.row_heading.level1.row1, '
                'th.blank.level0, '
                'th.row_heading.level2.row1, '
                'th.row_heading.level2.row2, '
                'th.row_heading.level2.row3'
            ),
            'props': [('border-bottom', '2px solid white !important')]
        })
        styles_def.append({
            'selector': (
                'th.row_heading.level1.row1, '
                'th.blank.level0, '
                'th.row_heading.level2.row1, '
                'th.row_heading.level2.row2, '
                'th.row_heading.level2.row3'
            ),
            'props': [('border-left', '2px solid white !important')]
        })
        styles_def.append({
            'selector': (
                'th.row_heading.level1.row3, '
                'th.blank.level0, '
                'th.row_heading.level2.row4, '
                'th.row_heading.level2.row5, '
                'th.row_heading.level2.row6'
            ),
            'props': [('border-bottom', '2px solid white !important')]
        })
        styles_def.append({
            'selector': (
                'th.blank.level0, '
                'th.row_heading.level2.row4, '
                'th.row_heading.level2.row5, '
                'th.row_heading.level2.row6'
            ),
            'props': [('border-left', '2px solid white !important')]
        })
        styles_def.append({
            'selector': (
                'th.row_heading.level1.row6, '
                'th.blank.level0, '
                'th.row_heading.level2.row7, '
                'th.row_heading.level2.row8, '
                'th.row_heading.level2.row9'
            ),
            'props': [('border-bottom', '2px solid white !important')]
        })
        styles_def.append({
            'selector': (
                'th.row_heading.level0.row0, '
                'th.blank.level0, '
                'th.row_heading.level1.row7, '
                'th.row_heading.level1.row8, '
            ),
            'props': [('border-bottom', '2px solid white !important')]
        })
        styles_def.append({
            'selector': (
                'th.row_heading.level0.row0, '
                'th.blank.level0, '
                'th.row_heading.level1.row0, '
                'th.row_heading.level1.row4, '
            ),
            'props': [('border-bottom', '2px solid white !important')]
        })
        styles_def.append({
            'selector': (
                'th.row_heading.level2.row6, '
                'th.row_heading.level2.row7, '
                'th.row_heading.level2.row8, '
            ),
            'props': [('border-left', '2px solid white !important')]
        })
        styles_def.append({
            'selector': (
                'th.row_heading.level1.row7, '
                'th.row_heading.level1.row8, '
                'th.row_heading.level1.row9, '
            ),
            'props': [('border-left', '2px solid white !important')]
        })
        styles_def.append({
            'selector': (
                'th.row_heading.level1.row0, '
                'th.row_heading.level1.row1, '
                'th.row_heading.level1.row2, '
                'th.row_heading.level1.row3, '
                'th.row_heading.level1.row4, '
                'th.row_heading.level1.row5, '
                'th.row_heading.level1.row6, '
                'th.row_heading.level1.row7, '
            ),
            'props': [("border-left", "3px solid grey")]
        })
        styles_def.append({
            "selector": "th.row_heading.level0.row1",
            "props": [("border-right", '2px solid white !important')]
        })
        styles_def.append({
            'selector': (
                'th.row_heading.level0.row1, '
                'th.row_heading.level1.row3, '
                'th.row_heading.level1.row6, '
                'th.row_heading.level1.row9'
            ),
            'props': [('border-right', '2px solid white !important')]
        })
        styles_def.append({
            "selector": "th.row_heading.level0",
            "props": [("border-left", "3px solid grey")]
        })
        styles_def.append({
            'selector': 'tbody tr:nth-child(1)',
            'props': [('border-top', '3px solid gray !important')]
        })

        styles_def.append({'selector': 'th.blank', 'props': [('background-color', '#fff !important')]})
        styles_def.append({'selector': 'th.row_heading.blank', 'props': [('background-color', '#fff !important')]})

        styles_def.extend([
            {'selector': f'tbody tr:nth-child({r + 2})',
             'props': [('border-bottom', '3px solid #666 !important')]}
            for r in thick_rows_data_zero_based
        ])

        hl_cols = [f"{str(year - 1)[-2:]}년 월평균", f"{str(year)[-2:]}년 목표", '합계', '월평균']

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
        st.write(f"year={year}, month={month}")

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