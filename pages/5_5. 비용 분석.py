import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from auth import require_login
import warnings
import modules

warnings.filterwarnings('ignore')
st.set_page_config(layout="wide", initial_sidebar_state="expanded")
require_login()

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
    if already_flat:
        df_for_style = df.copy()
    else:
        df_for_style = df.reset_index()

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


def display_memo(memo_file_key, year, month, css_class="memo-body"):
    """메모 파일 키와 년/월을 받아 해당 메모를 화면에 표시합니다.
       css_class 인자를 통해 모든 탭의 간격과 스타일 수치를 완벽하게 통일합니다."""
    file_name = st.secrets['memos'][memo_file_key]
    try:
        df_memo = pd.read_csv(file_name)
        df_filtered = df_memo[(df_memo['년도'] == year) & (df_memo['월'] == month)]

        if df_filtered.empty:
            return

        memo_text = df_filtered.iloc[0]['메모']
        if not isinstance(memo_text, str) or not memo_text.strip():
            return

        str_list = memo_text.split('\n')
        html_items = [create_indented_html(s) for s in str_list]
        body_content = "".join(html_items)

        html_code = f"""
        <style>
            .{css_class} {{
                font-family: 'Noto Sans KR', sans-serif;
                word-spacing: 5px;
                margin-bottom: 12px;
            }}
            .{css_class} .indent-0 {{ padding-left: 0px !important; padding-top: 10px; text-indent: -30px !important; font-size: 17px; font-weight: 400; }}
            .{css_class} .indent-1 {{ padding-left: 20px !important; padding-top: 5px; text-indent: -10px !important; font-size: 17px; }}
            .{css_class} .indent-2 {{ padding-left: 40px !important; text-indent: 0px !important; font-size: 17px; }}
            .{css_class} .indent-3 {{ padding-left: 60px !important; text-indent: 0px !important; font-size: 12px; }}
            .{css_class} p {{ margin: 0.1rem 0; }}
        </style>
        <div class="{css_class}">{body_content}</div>
        """
        st.markdown(html_code, unsafe_allow_html=True)
    except (FileNotFoundError, KeyError):
        pass


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

# 모든 표의 우측 정렬 끝선을 일치시키는 공통 CSS 강제 주입용 변수
t4_table_align_css = """<style>table { width: 100% !important; }</style>"""

t1, t2, t3 = st.tabs(['전체 생산실적', '부적합 발생내역_포항공장', '부적합 발생내역_충주 1,2공장'])
st.divider()

# 전체 생산실적 (탭 1) - 계층구조 표현 추가
with t1:
    col_l1, col_r1 = st.columns([6, 4], gap="large")

    with col_l1:
        st.markdown("<h4>1) 전체 생산실적</h4>", unsafe_allow_html=True)
        st.markdown("<div style='text-align:right; font-size:13px; color:#666; margin-bottom:5px;'>[단위: 톤]</div>",
                    unsafe_allow_html=True)

        try:
            raw40 = load_f40(st.secrets['sheets']['f_40'])
            df_board = modules.create_board_summary_table(
                year, month, raw40, base_year=year, prev_year_for_avg=year - 1, prev2_year_for_avg=year - 2
            )

            drop_cols = [
                c for c in df_board.columns
                if c not in ["'24년 월평균", "'25년 월평균", "'26년 월평균", "전월대비", "%"]
                   and c.split('.')[-1].isdigit()
                   and int(c.split('.')[-1]) > int(month)
            ]
            df_board = df_board.drop(columns=drop_cols, errors='ignore')

            df_show = df_board.reset_index()
            df_show.columns = ['구분1', '구분2'] + list(df_board.columns)

            # 🟢 [수정] raw40에서 Lv Class와 Parent Class 정보 가져오기
            level_parent_map = {}  # {구분2: (Lv Class, Parent Class)}
            for _, row in raw40.iterrows():
                g2 = str(row['구분2']).strip()
                lv = row.get('Lv class', row.get('Lv Class', 0))
                parent = row.get('Parent Class', '')

                # 구분2가 있으면 저장 (중복 시 첫 번째 값 유지)
                if g2 and g2 not in level_parent_map:
                    try:
                        level_parent_map[g2] = (int(lv), parent)
                    except (TypeError, ValueError):
                        level_parent_map[g2] = (0, parent)


            def _make_label(row):
                g1 = str(row['구분1']).strip()
                g2 = str(row['구분2']).strip()
                return g2 if g1 and g2 else (g1 if g1 else g2)


            df_show['구분'] = df_show.apply(_make_label, axis=1)


            # 🟢 [수정] Lv Class 기반으로 들여쓰기 결정
            def _format_label(label):
                clean_label = str(label).strip()

                # level_parent_map에서 정보 가져오기
                if clean_label in level_parent_map:
                    lv_class, parent = level_parent_map[clean_label]

                    # Lv Class 0이면 무조건 들여쓰기 X
                    if lv_class == 0:
                        padding = 0
                    # Lv Class 1이면 부모 확인
                    elif lv_class == 1:
                        if pd.notna(parent) and str(parent).strip():
                            padding = 16  # 부모가 있으면 들여쓰기
                        else:
                            padding = 0  # 부모가 없으면 들여쓰기 X
                    else:
                        padding = 0
                else:
                    # map에 없으면 들여쓰기 X
                    padding = 0

                return f'<span style="padding-left:{padding}px">{clean_label}</span>'


            df_show['구분'] = df_show['구분'].apply(_format_label)
            df_show = df_show.drop(columns=['구분1', '구분2'])
            cols_order = ['구분'] + [c for c in df_show.columns if c != '구분']
            df_show = df_show[cols_order]

            # 🟢 컬럼명 정규화: 작은따옴표 추가
            new_cols = []
            for col in df_show.columns:
                if col == '구분' or col == '전월대비' or col == '%':
                    new_cols.append(col)
                elif '년' in col and ('월평균' in col or '목표' in col or '월' in col):
                    # '24년 월평균, '25년 목표, '26.2 등 모두 작은따옴표 추가
                    if not col.startswith("'"):
                        # 26.2 형식 처리 → '26년 2월
                        if '.' in col and col[0].isdigit():
                            parts = col.split('.')
                            new_cols.append(f"'{parts[0]}년 {parts[1]}월")
                        else:
                            new_cols.append(f"'{col}")
                    else:
                        new_cols.append(col)
                else:
                    new_cols.append(col)
            df_show.columns = new_cols

            def _fmt_num(x):
                try:
                    v = float(x)
                    return "" if pd.isna(v) else f"{int(round(v)):,}"
                except Exception:
                    return x


            def _fmt_diff(x):
                try:
                    v = float(x)
                    if pd.isna(v): return ""
                    xi = int(round(v))
                    return f'<span style="color:red;">-{abs(xi):,}</span>' if xi < 0 else f"{xi:,}"
                except Exception:
                    return x


            def _fmt_pct(x):
                try:
                    v = float(x)
                    if pd.isna(v): return ""
                    return f'<span style="color:red;">-{abs(v):.1f}%</span>' if v < 0 else f"{v:.1f}%"
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

            styles_prod = [
                {'selector': 'table', 'props': [('border-collapse', 'collapse'), ('width', '100%')]},
                {'selector': 'th, td',
                 'props': [('border', '1px solid #aaa'), ('padding', '8px 16px'), ('font-weight', 'normal'),
                           ('color', 'black'), ('font-size', '15px'), ('background-color', 'white')]},
                {'selector': 'thead th',
                 'props': [('text-align', 'center'), ('font-weight', '700'), ('background-color', 'white'),
                           ('border', '1px solid #aaa')]},
                {'selector': 'tbody td', 'props': [('text-align', 'right'), ('background-color', 'white')]},
                {'selector': 'tbody td:nth-child(1)', 'props': [('text-align', 'left'), ('background-color', 'white')]},
            ]

            styled = (df_show.style.set_table_styles(styles_prod).hide(axis='index'))
            html_table = styled.to_html(escape=False)
            st.markdown(
                f"<div style='width: 100%; max-width: 100%; overflow-x: auto; display: block;'>{t4_table_align_css}{html_table}</div>",
                unsafe_allow_html=True)

            foot = "<div style='text-align:left; font-size:13px; color:#666; margin-top:5px;'>※ 집계기준 : 원재 투입량 + 비가공 + 제품 재가공</div>"
            st.markdown(foot, unsafe_allow_html=True)
        except Exception as e:
            st.error(f"사업부/공장 요약 표를 표시하는 중 오류가 발생했습니다: {e}")

    with col_r1:
        st.markdown("<h4 style='color:transparent'>1) 전체 생산실적 헤더맞춤</h4>", unsafe_allow_html=True)
        st.markdown("<div style='color:transparent; font-size:15px; margin-bottom:5px;'>[단위]</div>",
                    unsafe_allow_html=True)
        display_memo('f_40', year, month, css_class="t4-tight-memo")

# 부적합 발생내역 - 포항 (탭 2)
# =========================================================================
with t2:
    col_l2, col_r2 = st.columns([6, 4], gap="large")

    with col_l2:
        st.markdown("<h4>1) 부적합 발생내역 (포항)</h4>", unsafe_allow_html=True)
        st.markdown("<div style='text-align:right; font-size:13px; color:#666; margin-bottom:5px;'>[단위: 톤, %]</div>",
                    unsafe_allow_html=True)
        try:
            df_src = load_defect(st.secrets['sheets']['f_41_42'])
            df_pohang = modules.create_defect_summary_pohang(year, month, df_src, plant_name="포항")

            df_flat = df_pohang.reset_index()


            def make_label(row):
                상 = str(row['상']).strip()
                중 = str(row['중']).strip()
                구분 = str(row['구분']).strip()
                return 상 if 상 and 상 != 'nan' else (중 if 중 and 중 not in ('nan', ' ') else 구분)


            df_flat['구분명'] = df_flat.apply(make_label, axis=1)
            df_flat = df_flat.drop(columns=['상', '중', '구분'])
            df_flat = df_flat.rename(columns={'구분명': '구분'})

            # 🟢 문법 오류 요소 완벽 박멸 및 순수 한글 '구분' 선언
            cols_order = ['구분'] + [c for c in df_flat.columns if c != '구분']
            df_flat = df_flat[cols_order]

            # 🟢 컬럼명 정규화: 작은따옴표 추가
            new_cols = []
            for col in df_flat.columns:
                if col == '구분':
                    new_cols.append(col)
                elif '년' in col and ('월평균' in col or '목표' in col or '월' in col):
                    # '25년 월평균, '26년 목표, '26.2 → '26년 2월 등
                    if not col.startswith("'"):
                        # 26.2 형식 처리 → '26년 2월
                        if '.' in col and col[0].isdigit():
                            parts = col.split('.')
                            new_cols.append(f"'{parts[0]}년 {parts[1]}월")
                        else:
                            new_cols.append(f"'{col}")
                    else:
                        new_cols.append(col)
                else:
                    new_cols.append(col)
            df_flat.columns = new_cols

            styles_def = [
                {'selector': 'table', 'props': [('border-collapse', 'collapse'), ('width', '100%')]},
                # 1. 기본 스타일: 모든 th와 td를 일단 오른쪽 정렬(right)로 잡아서 숫자 데이터들을 우측 정렬시킵니다.
                {'selector': 'th, td',
                 'props': [('background-color', '#ffffff !important'), ('color', '#000000'), ('font-weight', '400'),
                           ('font-size', '15px'), ('border', '1px solid #aaa'), ('text-align', 'right'),
                           ('padding', '8px 16px')]},
                # 2. 헤더 스타일 수정: 상단 컬럼명(thead tr th)에만 'center !important'를 명시하여 가운데 정렬로 덮어씌웠습니다.
                {'selector': 'thead tr th',
                 'props': [('font-weight', '700'), ('background-color', '#ffffff !important'),
                           ('border', '1px solid #aaa'), ('text-align', 'center !important')]},  # ← 💡 이 부분 추가
                # 3. 첫 번째 열 스타일: '구분' 내용이 들어가는 첫 열(tbody td:nth-child(1))은 기존대로 왼쪽 정렬(left)을 유지합니다.
                {'selector': 'tbody td:nth-child(1)', 'props': [('text-align', 'left')]},
            ]

            # 🟢 소수점 .00000 제거 포맷 장착
            styled_def = (
                df_flat.style
                .format(lambda x: f"{x:,.0f}" if isinstance(x, (int, float, np.integer, np.floating)) and pd.notnull(
                    x) else x)
                .set_table_styles(styles_def)
                .hide(axis='index')
            )
            html_table_def = styled_def.to_html(escape=False)



            # 🟢 [수정] 볼드체 처리: to_html() 이후에 HTML 문자열에서 직접 처리
            bold_items = {'CHQ', 'CD', '포항'}
            for item in bold_items:
                html_table_def = html_table_def.replace(f'>{item}</td>', f'><strong>{item}</strong></td>')

            st.markdown(
                f"<div style='width: 100%; max-width: 100%; overflow-x: auto; display: block;'>{t4_table_align_css}{html_table_def}</div>",
                unsafe_allow_html=True)
        except Exception as e:
            st.error(f"포항 부적합 표 생성 중 오류가 발생했습니다: {e}")

    with col_r2:
        st.markdown("<h4 style='color:transparent'>2) 부적합 발생내역 헤더맞춤</h4>", unsafe_allow_html=True)
        st.markdown("<div style='color:transparent; font-size:15px; margin-bottom:5px;'>[단위]</div>",
                    unsafe_allow_html=True)
        display_memo('f_41', year, month, css_class="t4-tight-memo")

# 부적합 발생내역 - 충주 1,2공장 (탭 3)
# =========================================================================
with t3:
    col_l3, col_r3 = st.columns([6, 4], gap="large")

    with col_l3:
        st.markdown("<h4>1) 부적합 발생내역 (충주 1,2공장)</h4>", unsafe_allow_html=True)
        st.markdown("<div style='text-align:right; font-size:13px; color:#666; margin-bottom:5px;'>[단위: 톤, %]</div>",
                    unsafe_allow_html=True)
        try:
            df_src = load_defect(st.secrets['sheets']['f_41_42'])
            df_cjj = modules.create_defect_summary_chungju(year, month, df_src, plant1_name="충주", plant2_name="충주2")

            df_flat_cjj = df_cjj.reset_index()


            def make_label_cjj(row):
                for i in range(3):
                    v = str(row.iloc[i]).strip()
                    if v and v not in ('', 'nan', ' '): return v
                return ''


            df_flat_cjj['구분명'] = df_flat_cjj.apply(make_label_cjj, axis=1)
            df_flat_cjj = df_flat_cjj.drop(columns=df_flat_cjj.columns[0:3])
            df_flat_cjj = df_flat_cjj.rename(columns={'구분명': '구분'})
            cols_order = ['구분'] + [c for c in df_flat_cjj.columns if c != '구분']
            df_flat_cjj = df_flat_cjj[cols_order]

            # 🟢 컬럼명 정규화: 작은따옴표 추가
            new_cols = []
            for col in df_flat_cjj.columns:
                if col == '구분':
                    new_cols.append(col)
                elif '년' in col and ('월평균' in col or '목표' in col or '월' in col):
                    # '25년 월평균, '26년 목표, '26.2 → '26년 2월 등
                    if not col.startswith("'"):
                        # 26.2 형식 처리 → '26년 2월
                        if '.' in col and col[0].isdigit():
                            parts = col.split('.')
                            new_cols.append(f"'{parts[0]}년 {parts[1]}월")
                        else:
                            new_cols.append(f"'{col}")
                    else:
                        new_cols.append(col)
                else:
                    new_cols.append(col)
            df_flat_cjj.columns = new_cols

            # 💡 [수정] 헤더는 가운데 정렬, 숫자는 오른쪽 정렬, 첫 열은 왼쪽 정렬 설정
            styles_cjj = [
                {'selector': 'table', 'props': [('border-collapse', 'collapse'), ('width', '100%')]},
                # 기본 셀 스타일 (숫자 데이터용 오른쪽 정렬)
                {'selector': 'th, td',
                 'props': [('background-color', '#ffffff !important'), ('color', '#000000'), ('font-weight', '400'),
                           ('font-size', '15px'), ('border', '1px solid #aaa'), ('text-align', 'right'),
                           ('padding', '8px 16px')]},
                # 컬럼명 헤더 스타일 (가운데 정렬 반영)
                {'selector': 'thead tr th',
                 'props': [('font-weight', '700'), ('background-color', '#ffffff !important'),
                           ('border', '1px solid #aaa'), ('text-align', 'center !important')]},
                # ← 💡 center !important 추가
                # 첫 번째 열 '구분' 내용 스타일 (왼쪽 정렬 유지)
                {'selector': 'tbody td:nth-child(1)', 'props': [('text-align', 'left')]},
            ]

            # 🟢 소수점 .00000 제거 포맷 장착
            styled_cjj = (
                df_flat_cjj.style
                .format(lambda x: f"{x:,.0f}" if isinstance(x, (int, float, np.integer, np.floating)) and pd.notnull(
                    x) else x)
                .set_table_styles(styles_cjj)
                .hide(axis='index')
            )
            html_table_cjj = styled_cjj.to_html(escape=False)

            bold_items_cjj = {'충주1공장(CHQ)', '충주2공장', '충주'}
            for item in bold_items_cjj:
                html_table_cjj = html_table_cjj.replace(f'>{item}</td>', f'><strong>{item}</strong></td>')

            st.markdown(
                f"<div style='width: 100%; max-width: 100%; overflow-x: auto; display: block;'>{t4_table_align_css}{html_table_cjj}</div>",
                unsafe_allow_html=True)
        except Exception as e:
            st.error(f"충주 1,2공장 부적합 표 생성 중 오류가 발생했습니다: {e}")

    with col_r3:
        st.markdown("<h4 style='color:transparent'>3) 부적합 발생내역 헤더맞춤</h4>", unsafe_allow_html=True)
        st.markdown("<div style='color:transparent; font-size:15px; margin-bottom:5px;'>[단위]</div>",
                    unsafe_allow_html=True)
        display_memo('f_42', year, month, css_class="t4-tight-memo")

# =========================
# Footer
# =========================
st.markdown("""
<style>.footer { bottom: 0; left: 0; right: 0; padding: 8px; text-align: center; font-size: 13px; color: #666666;}</style>
<div class="footer">ⓒ 2025 SeAH Special Steel Corp. All rights reserved.</div>
""", unsafe_allow_html=True)