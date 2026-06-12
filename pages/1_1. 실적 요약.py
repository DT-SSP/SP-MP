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


custom_css = """
<style>
table {
    width: 100%;
    border-collapse: collapse;
    font-family: 'Noto Sans KR', sans-serif;
    font-size: 13px;
}
th, td {
    padding: 8px 16px;
    text-align: right;
    border: 1px solid #aaa;
    vertical-align: middle;
}
thead {
    background-color: #f2f2f2;
    font-weight: bold;
}
</style>
"""


def display_styled_df(df, styles=None, highlight_cols=None, already_flat=False):
    if already_flat:
        df_for_style = df.copy()
    else:
        df_for_style = df.reset_index()

    # (중복 컬럼명 고유화)
    new_cols, seen = [], {}
    for c in df_for_style.columns:
        c_str = str(c)
        seen[c_str] = seen.get(c_str, 0) + 1
        new_cols.append(c_str if seen[c_str] == 1 else f"{c_str}.{seen[c_str] - 1}")
    df_for_style.columns = new_cols

    hi_set = set(map(str, (highlight_cols or [])))

    def highlight_columns(col):
        return ['background-color: #f0f0f0'] * len(col) if str(col.name) in hi_set else [''] * len(col)

    def fmt_value(x):
        # 1) 숫자 타입
        if isinstance(x, (int, float, np.integer, np.floating)) and pd.notnull(x):
            if x < 0:
                return f'<span style="color:red">-{abs(x):,.0f}</span>'
            return f"{x:,.0f}"
        # 2) 문자열 타입 - 괄호(음수) 형태 변환
        if isinstance(x, str):
            s = x.strip()
            if s.startswith('(') and s.endswith(')'):
                inner = s[1:-1].strip()
                return f'<span style="color:red">-{inner}</span>'
        return x

    styled_df = (
        df_for_style.style
        .format(fmt_value)
        .set_properties(**{'text-align': 'right', 'font-family': 'Noto Sans KR'})
        .apply(highlight_columns, axis=0)
        .hide(axis="index")
    )
    if styles:
        styled_df = styled_df.set_table_styles(styles)

    html_table = styled_df.to_html(escape=False)
    # [수정] 5번 ROE 테이블 등 display_styled_df를 사용하는 표에도 동일하게 스크롤 래퍼 적용
    st.markdown(f"<div style='width: 100%; max-width: 100%; overflow-x: auto; display: block;'>{html_table}</div>", unsafe_allow_html=True)


##### 메모 #####
def create_indented_html(s):
    """문자열의 앞 공백을 기반으로 들여쓰기된 HTML <p> 태그를 생성합니다."""
    content = s.lstrip(' ')
    num_spaces = len(s) - len(content)
    indent_level = num_spaces // 2
    return f'<p class="indent-{indent_level}">{content}</p>'


def display_memo(memo_file_key, year, month, css_class="memo-body"):
    """메모 파일 키와 년/월을 받아 해당 메모를 화면에 표시합니다.
       css_class 인자를 통해 탭별로 독립된 스타일 울타리를 제공합니다."""
    file_name = st.secrets['memos'][memo_file_key]
    try:
        df_memo = pd.read_csv(file_name)

        # 년도/월 기준으로 필터
        df_filtered = df_memo[(df_memo['년도'] == year) & (df_memo['월'] == month)]

        if df_filtered.empty:
            st.warning(f"{year}년 {month}월 메모를 찾을 수 없습니다.")
            return

        # 여러 행이 있을 경우, 일단 첫 번째 행 사용
        memo_text = df_filtered.iloc[0]['메모']

        if not isinstance(memo_text, str) or not memo_text.strip():
            return

        str_list = memo_text.split('\n')
        html_items = [create_indented_html(s) for s in str_list]
        body_content = "".join(html_items)

        # 🟢 [핵심] css_class 매개변수를 동적으로 주입하여 브라우저 오염을 방지합니다.
        html_code = f"""
        <style>
            .{css_class} {{
                font-family: 'Noto Sans KR', sans-serif;
                word-spacing: 5px;
                margin-bottom: 12px;
            }}
            .{css_class} .indent-0 {{ padding-left: 0px; padding-top: 10px; text-indent: -30px; font-size: 17px; font-weight: 400; }}
            .{css_class} .indent-1 {{ padding-left: 20px; padding-top: 5px; text-indent: -10px; font-size: 17px; }}
            .{css_class} .indent-2 {{ padding-left: 40px; font-size: 17px; }}
            .{css_class} .indent-3 {{ padding-left: 60px; font-size: 12px; }}
            .{css_class} p {{ margin: 0.1rem 0; }}
        </style>
        <div class="{css_class}">{body_content}</div>
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

st.markdown("""
<style>
table, td, th {
    font-size: 15px !important;
    font-family: 'Noto Sans KR', sans-serif !important;
}
</style>
""", unsafe_allow_html=True)
t1, t2, t3 = st.tabs(['주요경영지표', '주요경영지표(본사)', '연간사업계획'])

# =========================


with t1:
    # ===== 1) 손익 (연결) =====
    col_l, col_r = st.columns([6, 4], gap="large")

    with col_l:
        st.markdown("<h4>1) 손익 (연결) </h4>", unsafe_allow_html=True)
        st.markdown("<div style='text-align:right; font-size:13px; color:#666;'>[단위: 톤, 백만원, %]</div>",
                    unsafe_allow_html=True)

        try:
            file_name = st.secrets["sheets"]["f_1"]
            df_src = pd.read_csv(file_name)

            base = modules.create_connected_profit(
                year=int(st.session_state['year']),
                month=int(st.session_state['month']),
                data=df_src
            )

            disp = base.copy()
            disp.insert(0, '구분', disp.index.map(lambda x: '%' if str(x).startswith('%') else x))
            disp = disp.reset_index(drop=True)


            def remove_paren(x):
                if not isinstance(x, str):
                    return x
                s = x.strip()
                if s.startswith('(') and s.endswith(')'):
                    return f'<span style="color:red">-{s[1:-1]}</span>'
                if s.startswith('-') and len(s) > 1:
                    return f'<span style="color:red">{s}</span>'
                return x


            for col in disp.columns:
                if col != '구분':
                    disp[col] = disp[col].apply(remove_paren)

            cols = disp.columns.tolist()
            c_idx = {c: i for i, c in enumerate(cols)}

            sel_y = int(st.session_state['year'])
            sel_m = int(st.session_state['month'])


            def shift_ym(y, m, delta):
                base_v = y * 12 + (m - 1) + delta
                return base_v // 12, base_v % 12 + 1


            prev2_y, prev2_m = shift_ym(sel_y, sel_m, -2)
            prev1_y, prev1_m = shift_ym(sel_y, sel_m, -1)

            prev2_label = f"'{str(prev2_y)[-2:]}년 {prev2_m}월"
            prev1_label = f"'{str(prev1_y)[-2:]}년 {prev1_m}월"
            curr_month_label = f"'{str(sel_y)[-2:]}.{sel_m}월"

            hdr1 = [''] * len(cols)
            hdr1[c_idx['구분']] = '구분'
            hdr1[c_idx['전전월 실적']] = prev2_label
            hdr1[c_idx['전월 실적']] = prev1_label
            hdr1[c_idx['당월 계획']] = '계획'
            hdr1[c_idx['당월 실적']] = f"{curr_month_label}\n①+②+③"
            hdr1[c_idx['본사']] = '본사\n①'
            hdr1[c_idx['중국']] = '중국\n②'
            hdr1[c_idx['태국']] = '태국\n③'
            hdr1[c_idx['전월 실적 대비']] = '전월대비'
            hdr1[c_idx['계획 대비']] = '계획대비'

            hdr_df = pd.DataFrame([hdr1], columns=cols)
            disp_vis = pd.concat([hdr_df, disp], ignore_index=True)


            def nth(col_name):
                return c_idx[col_name] + 1

            # [원상복구] padding 8px 16px 원복 및 줄바꿈 방지(nowrap)로 표를 일직선으로 맞춥니다.
            styles = [
                {'selector': 'thead', 'props': [('display', 'none')]},
                {'selector': 'table',
                 'props': [('border-collapse', 'collapse'), ('font-family', "'Noto Sans KR', sans-serif"),
                           ('font-size', '15px')]},
                {'selector': 'tbody td',
                 'props': [('border', '1px solid #aaa'), ('padding', '8px 16px'), ('text-align', 'right'),
                           ('font-weight', '400')]},
                {'selector': 'tbody td:first-child',
                 'props': [('text-align', 'left'), ('white-space', 'nowrap'), ('font-weight', '400')]},
                {'selector': 'tbody tr:nth-child(1) td',
                 'props': [('text-align', 'center'), ('font-weight', '700'), ('border-top', '1px solid #aaa'),
                           ('white-space', 'pre')]},
                {'selector': 'tbody tr:last-child td', 'props': [('border-bottom', '1px solid #aaa')]},
            ]

            custom_css = """<style>table { width: 100%; }</style>"""
            styled = (
                disp_vis.style
                .set_table_styles(styles)
                .hide(axis='index')
            )
            html_table = styled.to_html(escape=False)

            st.markdown(
                f"<div style='width: 100%; max-width: 100%; overflow-x: auto; display: block;'>{custom_css}{html_table}</div>",
                unsafe_allow_html=True)
            st.caption("각 %는 계산")

        except Exception as e:
            st.error(f"손익 연결 생성 중 오류: {e}")

    with col_r:
        st.markdown("<h4 style='color:transparent'>1) 손익 (연결)</h4>", unsafe_allow_html=True)
        st.markdown("<div style='color:transparent; font-size:15px;'>[단위: 톤, 백만원, %]</div>", unsafe_allow_html=True)
        display_memo('f_1', year, month)

    # ===== 2) 현금흐름표 (연결) =====
    st.divider()
    # [수정] 아래쪽 표들도 모두 비율과 간격 적용
    col_l, col_r = st.columns([6, 4], gap="large")
    with col_l:
        st.markdown("<h4>2) 현금흐름표 (연결)</h4>", unsafe_allow_html=True)
        st.markdown("<div style='text-align:right; font-size:13px; color:#666;'>[단위: 백만원]</div>",
                    unsafe_allow_html=True)

        try:
            file_name = st.secrets["sheets"]["f_2"]
            raw = pd.read_csv(file_name, dtype=str)

            base = modules.create_cashflow_by_gubun(
                year=int(st.session_state['year']),
                month=int(st.session_state['month']),
                data=raw
            )

            used_y = int(base.attrs.get("used_year", year))
            used_m = int(base.attrs.get("used_month", month))
            prev_y = used_y
            prev_m = used_m - 1
            if prev_m <= 0:
                prev_y -= 1
                prev_m += 12

            base = base.rename(columns={"남통": "중국"})

            year_cols = sorted(
                [c for c in base.columns if isinstance(c, str) and c.startswith("'")],
                key=lambda s: int(s[1:])
            )
            col_rename = {}
            if len(year_cols) >= 1:
                col_rename[year_cols[0]] = f"'{str(used_y - 1)[-2:]}년"
            if len(year_cols) >= 2:
                col_rename[year_cols[1]] = f"'{str(prev_y)[-2:]} {prev_m}월"
            base = base.rename(columns=col_rename)

            def fmt_cell(x):
                if pd.isna(x):
                    return ""
                try:
                    v = float(x)
                except Exception:
                    return x
                if v == 0:
                    return "0"
                return f'<span style="color:red">-{abs(int(round(v))):,}</span>' if v < 0 else f"{int(round(v)):,}"

            disp = base.copy().fillna(0)
            for c in disp.columns:
                disp[c] = disp[c].apply(fmt_cell)

            disp = disp.reset_index()

            if 'Lv class' in raw.columns:
                level_map = {}
                for _, row in raw[['구분3', 'Lv class']].dropna(subset=['구분3']).iterrows():
                    name = str(row['구분3']).strip()
                    try:
                        level_map[name] = int(row['Lv class'])
                    except (TypeError, ValueError):
                        level_map[name] = 0

                def get_indent(name):
                    clean = str(name).strip()
                    lv = level_map.get(clean, 0)
                    padding = lv * 16
                    return f'<span style="padding-left:{padding}px">{name}</span>'

                disp['구분'] = disp['구분'].apply(get_indent)

            bold_rows = ['영업활동현금흐름', '투자활동현금흐름', '재무활동현금흐름']
            bold_idx = [i for i, v in enumerate(disp['구분']) if
                        any(str(v).replace('\u00a0', '').strip() == b for b in bold_rows)]

            styles = [
                {'selector': 'table',
                 'props': [('border-collapse', 'collapse'), ('font-family', "'Noto Sans KR', sans-serif"),
                           ('font-size', '15px')]},
                {'selector': 'thead th',
                 'props': [('border', '1px solid #aaa'), ('padding', '8px 16px'), ('text-align', 'center'),
                           ('font-weight', '700'), ('background-color', '#fff'), ('white-space', 'nowrap')]},
                {'selector': 'tbody td',
                 'props': [('border', '1px solid #aaa'), ('padding', '8px 16px'), ('text-align', 'right'),
                           ('font-weight', '400')]},
                {'selector': 'tbody td:first-child',
                 'props': [('text-align', 'left'), ('white-space', 'pre'), ('font-weight', '400')]},
            ]

            for i in bold_idx:
                styles.append({
                    'selector': f'tbody tr:nth-child({i + 1})',
                    'props': [('font-weight', '700')]
                })

            styled = (
                disp.style
                .set_table_styles(styles)
                .hide(axis='index')
            )

            custom_css = """<style>table { width: 100%; }</style>"""
            # [수정] 아래쪽 표들도 모두 래퍼 적용
            st.markdown(
                f"<div style='width: 100%; max-width: 100%; overflow-x: auto; display: block;'>{custom_css}{styled.to_html(escape=False)}</div>",
                unsafe_allow_html=True
            )

        except Exception as e:
            st.error(f"현금흐름표 연결 생성 중 오류: {e}")

    with col_r:
        st.markdown("<h4 style='color:transparent'>2) 현금흐름표 (연결)</h4>", unsafe_allow_html=True)
        st.markdown("<div style='color:transparent; font-size:15px;'>[단위: 백만원]</div>", unsafe_allow_html=True)
        display_memo('f_2', year, month)

    # ===== 3) 재무상태표 (연결) =====
    st.divider()
    # [수정] 아래쪽 표들도 모두 비율과 간격 적용
    col_l, col_r = st.columns([6, 4], gap="large")
    with col_l:
        st.markdown("<h4>3) 재무상태표</h4>", unsafe_allow_html=True)
        st.markdown("<div style='text-align:right; font-size:13px; color:#666;'>[단위: 백만원]</div>",
                    unsafe_allow_html=True)

        try:
            file_name = st.secrets["sheets"]["f_3"]
            raw = pd.read_csv(file_name, dtype=str)

            item_order = [
                '현금및현금성자산', '매출채권', '재고자산', '유형자산', '기타', '자산총계',
                '매입채무', '차입금', '기타', '부채총계',
                '자본금', '이익잉여금', '기타', '자본총계', '부채 및 자본 총계'
            ]

            base = modules.create_bs_by_items(
                year=int(st.session_state['year']),
                month=int(st.session_state['month']),
                data=raw,
                item_order=item_order
            )


            def fmt_cell(x):
                if pd.isna(x): return ""
                try:
                    v = float(x)
                except:
                    return x
                return f'<span style="color:red">-{abs(int(round(v))):,}</span>' if v < 0 else f"{int(round(v)):,}"


            disp = base.copy().fillna(0)
            for c in disp.columns:
                disp[c] = disp[c].apply(fmt_cell)
            disp = disp.reset_index()

            # --- 👇 계층 표현(들여쓰기) 수정 부분 시작 👇 ---
            bold_items = ['자산총계', '부채총계', '자본총계', '부채 및 자본 총계']


            def get_indent_f3(name):
                clean_name = str(name).strip()
                lv = 0 if clean_name in bold_items else 1
                return f'<span style="padding-left:{lv * 16}px">{name}</span>'


            disp['구분'] = disp['구분'].apply(get_indent_f3)
            # --- 👆 계층 표현(들여쓰기) 수정 부분 끝 👆 ---
            # ⚠️ 이 바로 밑에 있던 구형 get_indent_f3 함수와 apply 구문이 삭제된 상태여야 합니다!

            drop_cols = [c for c in disp.columns if '천진' in str(c)]
            disp = disp.drop(columns=drop_cols, errors='ignore')
            disp = disp.rename(columns={'남통': '중국'})



            cols = disp.columns.tolist()
            c_idx = {c: i for i, c in enumerate(cols)}
            gu_i = c_idx['구분']
            month_i = c_idx['당월']
            diff_i = c_idx['전월비 증감']
            year_cols = [c for c in cols if isinstance(c, str) and c.startswith("'")]
            year_cols_sorted = sorted(year_cols, key=len) if year_cols else []
            prev_year_col = year_cols_sorted[0] if year_cols_sorted else None
            prev_month_col = year_cols_sorted[1] if len(year_cols_sorted) > 1 else prev_year_col

            cur_y = int(st.session_state['year'])
            cur_m = int(st.session_state['month'])
            month_pairs = []
            for k in (1, 0):
                y0, m0 = cur_y, cur_m - k
                while m0 <= 0:
                    y0 -= 1
                    m0 += 12
                month_pairs.append((y0, m0))
            (prev_y, prev_m), (used_y, used_m) = month_pairs

            curr_col_label = f"'{str(used_y)[-2:]}.{used_m}월"
            prev_text = f"'{str(prev_y)[-2:]} {prev_m}월"
            company_labels = [c for c in cols if c not in ['구분', '당월', '전월비 증감'] and c not in year_cols]

            hdr1 = [''] * len(cols)
            hdr1[gu_i] = '구분'
            if prev_year_col:
                hdr1[c_idx[prev_year_col]] = f"{prev_year_col}년말"
            if prev_month_col:
                hdr1[c_idx[prev_month_col]] = prev_text
            hdr1[month_i] = curr_col_label
            for k in company_labels:
                hdr1[c_idx[k]] = k
            hdr1[diff_i] = '전월대비'

            hdr_df = pd.DataFrame([hdr1], columns=cols)
            disp_vis = pd.concat([hdr_df, disp], ignore_index=True)

            styles = [
                {'selector': 'thead', 'props': [('display', 'none')]},
                {'selector': 'table',
                 'props': [('border-collapse', 'collapse'), ('font-family', "'Noto Sans KR', sans-serif"),
                           ('font-size', '15px')]},
                {'selector': 'tbody td',
                 'props': [('border', '1px solid #aaa'), ('padding', '8px 16px'), ('text-align', 'right'),
                           ('font-weight', '400')]},
                {'selector': 'tbody td:first-child',
                 'props': [('text-align', 'left'), ('white-space', 'pre'), ('font-weight', '400')]},
                {'selector': 'tbody tr:nth-child(1) td',
                 'props': [('text-align', 'center'), ('font-weight', '700'), ('border-top', '1px solid #aaa'),
                           ('border-bottom', '1px solid #aaa')]},
                {'selector': 'tbody tr:last-child td', 'props': [('border-bottom', '1px solid #aaa')]},
            ]
            bold_items = ['자산총계', '부채총계', '자본총계', '부채 및 자본 총계']
            for i, item in enumerate(item_order):
                if item in bold_items:
                    row_num = i + 2
                    styles.append({'selector': f'tbody tr:nth-child({row_num}) td',
                                   'props': [('font-weight', '700')]})

            custom_css = """<style>table { width: 100%; }</style>"""
            styled = (
                disp_vis.style
                .set_table_styles(styles)
                .hide(axis='index')
            )
            html_table = styled.to_html(escape=False)
            # [수정] 래퍼 적용
            st.markdown(
                f"<div style='width: 100%; max-width: 100%; overflow-x: auto; display: block;'>{custom_css}{html_table}</div>",
                unsafe_allow_html=True)

        except Exception as e:
            st.error(f"재무상태표 생성 중 오류: {e}")

    with col_r:
        st.markdown("<h4 style='color:transparent'>3) 재무상태표</h4>", unsafe_allow_html=True)
        st.markdown("<div style='color:transparent; font-size:15px;'>[단위: 백만원]</div>", unsafe_allow_html=True)
        display_memo('f_3', year, month)

    st.divider()
    # [수정] 아래쪽 표들도 모두 비율과 간격 적용
    col_l, col_r = st.columns([6, 4], gap="large")
    with col_l:
        # ===== 4) 회전일 (연결) =====
        st.markdown("<h4>4) 회전일 (연결)</h4>", unsafe_allow_html=True)

        try:
            file_name = st.secrets["sheets"]["f_4"]
            raw = pd.read_csv(file_name, dtype=str)

            import importlib
            importlib.invalidate_caches()
            importlib.reload(modules)

            snap = modules.create_turnover(
                year=year,
                month=month,
                data=raw
            )

            used_y = int(snap.attrs.get("used_year", year))
            used_m = int(snap.attrs.get("used_month", month))
            prev_y = int(snap.attrs.get("prev_year", year))
            prev_m = int(snap.attrs.get("prev_month", month))

            curr_label = f"'{used_y % 100:02d}.{used_m}월"

            def get_val(item, group, company):
                try:
                    v = snap.loc[item, (group, company)]
                    return v
                except:
                    try:
                        for col in snap.columns:
                            if col[0] == group and col[1] == company:
                                return snap.loc[item, col]
                    except:
                        pass
                    return None

            def fmt(v):
                try:
                    f = float(v)
                    if pd.isna(f): return ""
                    return f"{f:.1f}"
                except:
                    return ""


            items = [
                ('매출채권', '매출채권 ⓐ'),
                ('재고자산', '재고자산 ⓑ'),
                ('매입채무', '매입채무 ⓒ'),  # ← 이 줄을
                ('현금전환주기', '현금전환주기\n(ⓐ+ⓑ-ⓒ)'),
            ]

            th = "style='border:1px solid #aaa; padding:5px 10px; text-align:center; font-weight:700; background-color:white;'"
            td_left = "style='border:1px solid #aaa; padding:5px 10px; text-align:left; white-space:pre-line;'"
            td_center = "style='border:1px solid #aaa; padding:5px 10px; text-align:center; font-weight:600; vertical-align:middle;'"
            td_num = "style='border:1px solid #aaa; padding:5px 10px; text-align:right;'"
            td_red = "style='border:1px solid #aaa; padding:5px 10px; text-align:right; color:red;'"

            def make_td(v):
                s = fmt(v)
                try:
                    if s != "" and float(s) < 0:
                        return f'<td {td_red}>{s}</td>'
                except:
                    pass
                return f'<td {td_num}>{s}</td>'

            rows_html = ""
            for i, (item_key, item_label) in enumerate(items):
                rows_html += "<tr>"
                if i == 0:
                    rows_html += f'<td {td_center} rowspan="4">회전일</td>'
                rows_html += f'<td {td_left}>{item_label}</td>'
                for comp in ['계', '특수강', '중국', '태국']:
                    v = get_val(item_key, '당월', comp)
                    rows_html += make_td(v)
                for comp in ['계', '특수강', '중국', '태국']:
                    v = get_val(item_key, '전월비', comp)
                    rows_html += make_td(v)
                rows_html += "</tr>"

            html = f"""
<table style="border-collapse:collapse; font-size:15px;">
  <thead>
    <tr>
      <th {th} rowspan="2" colspan="2">구분</th>
      <th {th} colspan="4">{curr_label}</th>
      <th {th} colspan="4">전월比</th>
    </tr>
    <tr>
      <th {th}>계</th>
      <th {th}>본사</th>
      <th {th}>중국</th>
      <th {th}>태국</th>
      <th {th}>계</th>
      <th {th}>본사</th>
      <th {th}>중국</th>
      <th {th}>태국</th>
    </tr>
  </thead>
  <tbody>
    {rows_html}
  </tbody>
</table>
"""
            # [수정] 래퍼 적용
            st.markdown(f"<div style='width: 100%; max-width: 100%; overflow-x: auto; display: block;'>{html}</div>", unsafe_allow_html=True)

        except Exception as e:
            st.error(f"회전일 표 생성 중 오류: {e}")

    with col_r:
        st.markdown("<h4 style='color:transparent'>4) 회전일 (연결)</h4>", unsafe_allow_html=True)
        display_memo('f_4', year, month)

    st.markdown("<br>", unsafe_allow_html=True)

    # [수정] 아래쪽 표들도 모두 비율과 간격 적용
    col_l, col_r = st.columns([6, 4], gap="large")
    with col_l:
        # ===== 5) ROE =====
        try:
            st.markdown("<h4>5) ROE</h4>", unsafe_allow_html=True)
            st.markdown("<div style='text-align:right; font-size:13px; color:#666;'>[단위: 백만원]</div>",
                        unsafe_allow_html=True)

            file_name = st.secrets["sheets"]["f_5"]
            raw = pd.read_csv(file_name, dtype=str)

            import importlib
            importlib.invalidate_caches()
            importlib.reload(modules)

            base = modules.create_roe_table(year=year, month=month, data=raw)
            disp = base.reset_index().rename(columns={"index": "구분"})

            styles = [
                {'selector': 'table',
                 'props': [('border-collapse', 'collapse'), ('font-family', "'Noto Sans KR', sans-serif"),
                           ('font-size', '15px')]},
                {'selector': 'thead th',
                 'props': [('border', '1px solid #aaa'), ('padding', '8px 16px'), ('text-align', 'center'),
                           ('font-weight', '700'), ('background-color', '#fff'), ('white-space', 'nowrap')]},
                {'selector': 'tbody td',
                 'props': [('border', '1px solid #aaa'), ('padding', '8px 16px'), ('text-align', 'right'),
                           ('font-weight', '400')]},
                {'selector': 'tbody td:first-child',
                 'props': [('text-align', 'left'), ('white-space', 'pre'), ('font-weight', '400')]},
            ]

            display_styled_df(disp, styles=styles, highlight_cols=None, already_flat=True)

            st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>* ROE = 당기순이익/ 자본총계, 연결기준</div>",
                        unsafe_allow_html=True)
            st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>* 유효법인세율 20% 반영</div>",
                        unsafe_allow_html=True)

        except Exception as e:
            st.error(f"ROE 표 생성 중 오류: {e}")

    with col_r:
        st.markdown("<h4 style='color:transparent'>5) ROE</h4>", unsafe_allow_html=True)
        st.markdown("<div style='color:transparent; font-size:15px;'>[단위: 백만원]</div>", unsafe_allow_html=True)
        display_memo('f_5', year, month)

with t2:

    st.markdown("<h4>1) 손익(별도)</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:right; font-size:13px; color:#666;'>[단위: 톤, 백만원, %]</div>",
                unsafe_allow_html=True)

    try:
        file_name = st.secrets["sheets"]["f_1"]
        raw = pd.read_csv(file_name, dtype=str)

        base = modules.create_pl_separate_hq(
            year=int(st.session_state['year']),
            month=int(st.session_state['month']),
            data=raw
        )

        disp = base.reset_index().rename(columns={"index": "구분"})
        cols = disp.columns.tolist()
        c = {k: i for i, k in enumerate(cols)}

        sel_y = int(st.session_state['year'])
        sel_m = int(st.session_state['month'])


        def shift_ym(y, m, delta):
            base_v = y * 12 + (m - 1) + delta
            return base_v // 12, base_v % 12 + 1


        prev_y, prev_m = shift_ym(sel_y, sel_m, -1)
        prev_label = f"'{str(prev_y)[-2:]}.{prev_m}월"
        curr_label = f"'{str(sel_y)[-2:]}.{sel_m}월"

        from decimal import Decimal, ROUND_HALF_UP
        import math

        amt_rows = ["매출액", "영업이익", "순금융비용", "경상이익"]
        qty_rows = ["판매량"]
        pct_rows = ["%(영업)", "%(경상)"]


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


        def fmt_amount(x):
            v = _to_float(x)
            if math.isnan(v):
                return ""
            r = int(Decimal(str(v)).quantize(Decimal("0"), rounding=ROUND_HALF_UP))
            s = f"{abs(r):,}"
            return f"-{s}" if r < 0 else s


        def fmt_qty(x):
            v = _to_float(x)
            if math.isnan(v):
                return ""
            r = int(Decimal(str(v)).quantize(Decimal("0"), rounding=ROUND_HALF_UP))
            s = f"{abs(r):,}"
            return f"-{s}" if r < 0 else s


        def fmt_pct(x):
            v = _to_float(x)
            if math.isnan(v):
                return ""
            r = float(Decimal(str(v)).quantize(Decimal("0.0"), rounding=ROUND_HALF_UP))
            s = f"{abs(r):.1f}"
            return f"-{s}" if r < 0 else s


        num_cols = [c_name for c_name in cols if c_name != '구분']
        body = disp.copy()

        mask_amt = body["구분"].isin(amt_rows)
        mask_qty = body["구분"].isin(qty_rows)
        mask_pct = body["구분"].isin(pct_rows)

        body.loc[mask_amt, num_cols] = body.loc[mask_amt, num_cols].map(fmt_amount)
        body.loc[mask_qty, num_cols] = body.loc[mask_qty, num_cols].map(fmt_qty)
        body.loc[mask_pct, num_cols] = body.loc[mask_pct, num_cols].map(fmt_pct)

        th = "style='border:1px solid #aaa; padding:5px 10px; text-align:center; font-weight:700; background-color:white;'"
        td_left = "style='border:1px solid #aaa; padding:5px 10px; text-align:left; white-space:nowrap;'"
        td_right = "style='border:1px solid #aaa; padding:5px 10px; text-align:right;'"


        def make_td(v, row_label):
            s = str(v) if v is not None else ""
            try:
                fv = float(str(s).replace(',', '').replace('-', '').strip())
                if str(s).startswith('-') and fv != 0:
                    return f'<td style="border:1px solid #aaa; padding:5px 10px; text-align:right; color:red;">{s}</td>'
            except:
                pass
            return f'<td {td_right}>{s}</td>'


        rows_html = ""
        for _, row in body.iterrows():
            rows_html += "<tr>"
            rows_html += f'<td {td_left}>{row["구분"]}</td>'
            for col_name in num_cols:
                rows_html += make_td(row[col_name], row["구분"])
            rows_html += "</tr>"

        html = f"""
        <table style="border-collapse:collapse; font-size:15px; width:100%;">
          <thead>
            <tr>
              <th {th} rowspan="2">구분</th>
              <th {th}>{prev_label}</th>
              <th {th} colspan="4">{curr_label}</th>
              <th {th} colspan="3">누적</th>
            </tr>
            <tr>
              <th {th}>전월</th>
              <th {th}>계획</th>
              <th {th}>실적</th>
              <th {th}>계획대비</th>
              <th {th}>전월대비</th>
              <th {th}>계획</th>
              <th {th}>실적</th>
              <th {th}>계획대비</th>
            </tr>
          </thead>
          <tbody>
            {rows_html}
          </tbody>
        </table>
        """

        # 1. 마크다운 표 출력
        st.markdown(html, unsafe_allow_html=True)

        # 2. 🟢 [수정] 표와 메모 간격 최소화 + 문장 간의 간격 추가 제어
        t2_exclusive_css = """
        <style>
            .t2-special-memo {
                margin-top: -22px !important;    /* 🟢 표와 메모 사이 간격을 더 위로 바짝 붙임 */
            }
            .t2-special-memo .indent-0 { 
                padding-left: 20px !important;   
                padding-top: 0px !important;     /* 🟢 기본 적용되어 있던 위쪽 패딩을 제거 */
                text-indent: 0px !important;     
            }
            .t2-special-memo .indent-1 { 
                padding-left: 40px !important; 
                text-indent: 0px !important; 
            }
            .t2-special-memo .indent-2 { 
                padding-left: 60px !important; 
            }
            /* 🟢 [추가] 문장과 문장 사이(각 행)의 위아래 간격을 좁게 강제 조정 */
            .t2-special-memo p {
                margin: 0.1rem 0 !important;      /* 🟢 기본 0.2rem에서 0.1rem으로 축소 */
                line-height: 1.3 !important;      /* 🟢 줄 간격도 조금 더 콤팩트하게 설정 */
            }
        </style>
        """
        st.markdown(t2_exclusive_css, unsafe_allow_html=True)

        # 3. 새 이름표(t2-special-memo) 격리 호출
        display_memo('f_1_2', year, month, css_class="t2-special-memo")

    except Exception as e:
        st.error(f"손익 별도 생성 중 오류: {e}")

    st.divider()

    st.markdown("<h4>2) 품목손익 (별도)</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:right; font-size:13px; color:#666;'>[단위: 톤, 백만원, %]</div>",
                unsafe_allow_html=True)

    try:
        file_name = st.secrets["sheets"]["f_7"]
        raw = pd.read_csv(file_name, dtype=str)

        year = int(st.session_state["year"])
        month = int(st.session_state["month"])

        base = modules.create_item_pl_from_flat(
            data=raw, year=year, month=month,
            main_items=("CHQ", "CD", "STS", "BTB", "PB"),
            filter_tag="품목손익"
        )

        amt_rows = ["매출액", "영업이익", "경상이익"]
        qty_rows = ["판매량"]
        pct_rows = ["%(영업)", "%(경상)"]


        def fmt_amount(x):
            try:
                v = float(x)
                s = f"{abs(int(round(v))):,}"
                return f'<span style="color:red">-{s}</span>' if v < 0 else s
            except:
                return ""


        def fmt_qty(x):
            try:
                v = float(x)
                s = f"{abs(int(round(v))):,}"
                return f'<span style="color:red">-{s}</span>' if v < 0 else s
            except:
                return ""


        def fmt_pct(x):
            try:
                v = float(x)
                s = f"{abs(v):.1f}"
                return f'<span style="color:red">-{s}</span>' if v < 0 else s
            except:
                return ""


        item_cols = ["CHQ", "CD", "STS", "BTB", "PB", "상품 등"]
        all_cols = ["합계"] + item_cols

        # 🔴 [정렬 교정] 데이터 셀은 우측 정렬(right)이 표준입니다.
        td_base = "border:1px solid #aaa; padding:5px 8px; text-align:right; font-size:15px;"
        th_base = "border:1px solid #aaa; padding:5px 8px; text-align:center; font-size:15px; font-weight:700;"
        td_center = "border:1px solid #aaa; padding:5px 8px; text-align:left; font-size:15px;"

        html = f"""
        <table style="border-collapse:collapse; width:100%; font-family:'Noto Sans KR', sans-serif;">
          <thead>
            <tr>
              <th rowspan="2" style="{th_base}">구분</th>
              <th rowspan="2" style="{th_base}">합계</th>
              <th colspan="6" style="{th_base}">품목</th>
            </tr>
            <tr>
              <th style="{th_base}">CHQ</th>
              <th style="{th_base}">CD</th>
              <th style="{th_base}">STS</th>
              <th style="{th_base}">BTB</th>
              <th style="{th_base}">PB</th>
              <th style="{th_base}">상품 등</th>
            </tr>
          </thead>
          <tbody>
        """
        for row_label in ["매출액", "판매량", "영업이익", "%(영업)", "경상이익", "%(경상)"]:
            if row_label in amt_rows:
                fmt = fmt_amount
            elif row_label in qty_rows:
                fmt = fmt_qty
            else:
                fmt = fmt_pct

            html += f'    <tr>\n'
            html += f'      <td style="{td_center}">{row_label}</td>\n'
            for col in all_cols:
                val = base.loc[row_label, col] if row_label in base.index and col in base.columns else ""
                html += f'      <td style="{td_base}">{fmt(val)}</td>\n'
            html += f'    </tr>\n'

        html += "  </tbody>\n</table>"
        st.markdown(html, unsafe_allow_html=True)

        # 🟢 [품목손익 전용 격리 스타일]
        t2_item_css = """
            <style>
                .t2-item-memo { margin-top: -22px !important; }
                .t2-item-memo .indent-0 { padding-left: 20px !important; padding-top: 0px !important; text-indent: 0px !important; }
                .t2-item-memo .indent-1 { padding-left: 40px !important; text-indent: 0px !important; }
                .t2-item-memo p { margin: 0.1rem 0 !important; line-height: 1.3 !important; }
            </style>
            """
        st.markdown(t2_item_css, unsafe_allow_html=True)
        display_memo('f_7', year, month, css_class="t2-item-memo")

    except Exception as e:
        st.error(f"품목손익 (별도) 생성 중 오류: {e}")

    # 수정원가기준 손익(별도)
    st.divider()

    st.markdown("<h4>3) 수정원가기준 손익 (별도)</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:right; font-size:13px; color:#666;'>[단위: 톤, 백만원, %]</div>",
                unsafe_allow_html=True)

    try:
        file_name = st.secrets["sheets"]["f_8"]
        raw = pd.read_csv(file_name, dtype=str)

        year = int(st.session_state["year"])
        month = int(st.session_state["month"])

        base = modules.create_item_change_cost_from_flat(
            data=raw, year=year, month=month,
            col_order=("계", "CHQ", "CD", "STS", "BTB", "PB", "내수", "수출")
        )

        amt_rows = ["매출액", "X등급 및 재고평가", "영업이익", "한계이익"]
        qty_rows = ["판매량"]
        pct_rows = ["%(영업)", "%(한계)"]


        def fmt_val(x, row_label):
            try:
                v = float(x)
            except:
                return ""
            if row_label in pct_rows:
                s = f"{abs(v):.1f}%"
            else:
                s = f"{abs(int(round(v))):,}"
            if v < 0:
                return f'<span style="color:red;">-{s}</span>'
            return s


        def fmt_cell(val, row_label, col):
            if pd.isna(val) or str(val).strip() == "":
                return ""
            return fmt_val(val, row_label)


        th = "border:1px solid #aaa; padding:6px 10px; text-align:center; font-size:15px; font-weight:700;"
        # 🔴 [정렬 교정] 데이터 셀 우측 정렬(right)로 변경
        td_r = "border:1px solid #aaa; padding:6px 10px; text-align:right; font-size:15px;"
        td_c = "border:1px solid #aaa; padding:6px 10px; text-align:left; font-size:15px;"

        row_order = ["매출액", "판매량", "X등급 및 재고평가", "영업이익", "%(영업)", "한계이익", "%(한계)"]
        item_cols = ["CHQ", "CD", "STS", "BTB", "PB"]
        all_cols = ["계"] + item_cols + ["내수", "수출"]

        html = f"""
        <table style="border-collapse:collapse; width:100%; font-family:'Noto Sans KR', sans-serif;">
          <thead>
            <tr>
              <th rowspan="2" style="{th}">구분</th>
              <th rowspan="2" style="{th}">계</th>
              <th colspan="5" style="{th}">품목</th>
              <th rowspan="2" style="{th}">내수</th>
              <th rowspan="2" style="{th}">수출</th>
            </tr>
            <tr>
              <th style="{th}">CHQ</th>
              <th style="{th}">CD</th>
              <th style="{th}">STS</th>
              <th style="{th}">BTB</th>
              <th style="{th}">PB</th>
            </tr>
          </thead>
          <tbody>
        """
        for row_label in row_order:
            html += "    <tr>\n"
            html += f'      <td style="{td_c}">{row_label}</td>\n'
            for col in all_cols:
                try:
                    val = base.loc[row_label, col] if row_label in base.index and col in base.columns else ""
                except:
                    val = ""
                html += f'      <td style="{td_r}">{fmt_cell(val, row_label, col)}</td>\n'
            html += "    </tr>\n"

        html += "  </tbody>\n</table>"
        st.markdown(html, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"수정원가기준 (별도) 생성 중 오류: {e}")

    # 원재료 입고-기초 단가 차이
    st.divider()

    st.markdown("<h4>4) 원재료 입고-기초 단가 차이</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:right; font-size:13px; color:#666;'>[단위: 톤, 백만원, %]</div>",
                unsafe_allow_html=True)

    try:
        file_name = st.secrets["sheets"]["f_9"]
        raw = pd.read_csv(file_name, dtype=str)

        year = int(st.session_state["year"])
        month = int(st.session_state["month"])

        ar = modules.create_9(year=year, month=month, data=raw)
        disp = ar.copy()

        for col in ["중량", "금액", "단가"]:
            disp[col] = pd.to_numeric(
                disp[col].astype(str).str.replace(",", ""), errors="coerce"
            ).fillna(0)


        def round_then_drop(v, divisor):
            return int(round(v / divisor, 1))


        disp["중량"] = disp["중량"].apply(lambda v: round_then_drop(v, 1_000))
        disp["금액"] = disp["금액"].apply(lambda v: round_then_drop(v, 1_000_000))
        disp["단가"] = disp["단가"].apply(lambda v: int(round(v)))


        def fmt_num(v):
            if v < 0:
                return f'<span style="color:red">-{abs(v):}</span>'
            return f"{v:,}"


        th = "border:1px solid #aaa; padding:6px 10px; text-align:center; font-size:15px; font-weight:700;"
        td_l = "border:1px solid #aaa; padding:6px 10px; text-align:left;   font-size:15px;"
        # 🔴 [정렬 교정] 데이터 셀 우측 정렬(right)로 변경
        td_r = "border:1px solid #aaa; padding:6px 10px; text-align:right;  font-size:15px;"
        td_l_bold = "border:1px solid #aaa; padding:6px 10px; text-align:left;   font-size:15px; font-weight:700;"
        td_r_bold = "border:1px solid #aaa; padding:6px 10px; text-align:right;  font-size:15px; font-weight:700;"

        maker_order = ["포스코", "JFE STEEL(S)", "세아창원특수강", "현대제철", "세아베스틸", "합계"]

        html = f"""
        <table style="border-collapse:collapse; width:100%; font-family:'Noto Sans KR', sans-serif;">
          <thead>
            <tr>
              <th style="{th}">메이커</th>
              <th style="{th}">중량</th>
              <th style="{th}">금액</th>
              <th style="{th}">단가</th>
              <th style="{th}">비고</th>
            </tr>
          </thead>
          <tbody>
        """
        disp_indexed = disp.set_index("메이커")

        for maker in maker_order:
            is_total = (maker == "합계")
            _l = td_l_bold if is_total else td_l
            _r = td_r_bold if is_total else td_r

            if maker in disp_indexed.index:
                row = disp_indexed.loc[maker]
                중량 = fmt_num(row["중량"])
                금액 = fmt_num(row["금액"])
                단가 = fmt_num(row["단가"])
            else:
                중량, 금액, 단가 = "", "", ""

            html += f"""    <tr>
              <td style="{_l}">{maker}</td>
              <td style="{_r}">{중량}</td>
              <td style="{_r}">{금액}</td>
              <td style="{_r}">{단가}</td>
              <td style="{_r}"></td>
            </tr>
        """
        html += "  </tbody>\n</table>"
        st.markdown(html, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"원재료 입고-기초 단가 차이 표 생성 중 오류: {e}")

    # 원재료 입고-기초 단가 차이 거래처 기준
    st.divider()

    st.markdown("<h4>5) 원재료 입고-기초 단가 차이 거래처 기준</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:right; font-size:13px; color:#666;'>[단위:톤,백만원]</div>",
                unsafe_allow_html=True)

    try:
        file_name = st.secrets["sheets"]["f_10"]
        raw = pd.read_csv(file_name, dtype=str)

        year = int(st.session_state["year"])
        month = int(st.session_state["month"])

        ar = modules.create_10(year=year, month=month, data=raw)
        disp = ar.copy()

        for col in ["금액", "단가"]:
            disp[col] = pd.to_numeric(
                disp[col].astype(str).str.replace(",", ""), errors="coerce"
            ).fillna(0)


        def round_then_drop(v, divisor):
            return int(round(v / divisor, 1))


        disp["금액"] = disp["금액"].apply(lambda v: round_then_drop(v, 1_000_000))
        disp["단가"] = disp["단가"].apply(lambda v: int(round(v)))


        def fmt_num(v):
            if v < 0:
                return f'<span style="color:red">-{abs(v):}</span>'
            return f"{v:,}"


        th = "border:1px solid #aaa; padding:6px 10px; text-align:center; font-size:15px; font-weight:700;"
        td_l = "border:1px solid #aaa; padding:6px 10px; text-align:left;   font-size:15px;"
        # 🔴 [정렬 교정] 데이터 셀 우측 정렬(right)로 변경
        td_r = "border:1px solid #aaa; padding:6px 10px; text-align:right;  font-size:15px;"
        td_l_bold = "border:1px solid #aaa; padding:6px 10px; text-align:left;   font-size:15px; font-weight:700;"
        td_r_bold = "border:1px solid #aaa; padding:6px 10px; text-align:right;  font-size:15px; font-weight:700;"

        maker_order = ["포스코_일반", "포스코_산업", "JFE STEEL(S)", "세아창원특수강", "현대제철", "세아베스틸", "합계"]

        html = f"""
        <table style="border-collapse:collapse; width:100%; font-family:'Noto Sans KR', sans-serif;">
          <thead>
            <tr>
              <th style="{th}">메이커</th>
              <th style="{th}">금액</th>
              <th style="{th}">단가</th>
              <th style="{th}">비고</th>
            </tr>
          </thead>
          <tbody>
        """
        disp_indexed = disp.set_index("메이커")

        for maker in maker_order:
            is_total = (maker == "합계")
            _l = td_l_bold if is_total else td_l
            _r = td_r_bold if is_total else td_r

            if maker in disp_indexed.index:
                row = disp_indexed.loc[maker]
                금액 = fmt_num(row["금액"])
                단가 = fmt_num(row["단가"])
            else:
                금액, 단가 = "", ""

            html += f"""    <tr>
              <td style="{_l}">{maker}</td>
              <td style="{_r}">{금액}</td>
              <td style="{_r}">{단가}</td>
              <td style="{_r}"></td>
            </tr>
        """
        html += "  </tbody>\n</table>"
        st.markdown(html, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"원재료 입고-기초 단가 차이 거래처 기준 표 생성 중 오류: {e}")
        st.markdown("<div style='text-align:right; font-size:13px; color:#666;'>[단위:백만원]</div>",
                    unsafe_allow_html=True)

    # 제품수불표
    st.divider()

    st.markdown("<h4>6) 제품수불표</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:right; font-size:13px; color:#666;'>[단위: 백만원]</div>", unsafe_allow_html=True)

    try:
        file_name = st.secrets["sheets"]["f_11"]
        df_src = pd.read_csv(file_name, dtype=str)

        pf_base = modules.create_product_flow_base(
            year=int(st.session_state['year']),
            month=int(st.session_state['month']),
            data=df_src,
            amount_div=1_000_000
        )

        mm = int(st.session_state['month'])


        def _fmt(x, nd=1):
            try:
                v = float(x)
            except:
                return ""
            if v < 0:
                return f'<span style="color:red">-{abs(v):,.{nd}f}</span>'
            return f"{v:,.{nd}f}"


        입고_단가 = _fmt(pf_base["입고-기초_단가"].iloc[0])
        입고_금액 = _fmt(pf_base["입고-기초_금액"].iloc[0])
        매출_단가 = _fmt(pf_base["매출원가-기초_단가"].iloc[0])
        매출_금액 = _fmt(pf_base["매출원가-기초_금액"].iloc[0])

        th = "border:1px solid #aaa; padding:10px 20px; text-align:center; font-size:15px; font-weight:700;"
        # 🔴 [정렬 교정] 제품수불표 수치 셀도 우측 정렬로 수정
        td = "border:1px solid #aaa; padding:10px 20px; text-align:right;  font-size:15px;"

        html = f"""
        <table style="border-collapse:collapse; font-family:'Noto Sans KR', sans-serif;">
          <thead>
            <tr><th colspan="4" style="{th}">{mm}월</th></tr>
            <tr>
              <th colspan="2" style="{th}">입고-기초</th>
              <th colspan="2" style="{th}">매출원가-기초</th>
            </tr>
            <tr>
              <th style="{th}">단가</th>
              <th style="{th}">금액</th>
              <th style="{th}">단가</th>
              <th style="{th}">금액</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td style="{td}">{입고_단가}</td>
              <td style="{td}">{입고_금액}</td>
              <td style="{td}">{매출_단가}</td>
              <td style="{td}">{매출_금액}</td>
            </tr>
          </tbody>
        </table>
        """
        st.markdown(html, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"제품 수불표 생성 중 오류: {e}")

    # 현금흐름표손익(별도)

    st.divider()

    st.markdown("<h4>7) 현금흐름표 손익 (별도)</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 톤, 백만원, %]</div>",
                unsafe_allow_html=True)

    try:
        file_name = st.secrets["sheets"]["f_12"]
        raw = pd.read_csv(file_name, dtype=str)


        def clean_accounting_str(val):
            if pd.isna(val):
                return val
            s = str(val).strip()
            if s.startswith('(') and s.endswith(')'):
                inner = s[1:-1].replace(',', '').replace('.', '')
                if inner.isdigit():
                    s = '-' + s[1:-1]
            temp_for_check = s.replace(',', '').replace('.', '').replace('-', '')
            if temp_for_check.isdigit():
                s = s.replace(',', '')
            return s


        for c in raw.columns:
            raw[c] = raw[c].apply(clean_accounting_str)


        def _to_num(s: pd.Series) -> pd.Series:
            s = s.fillna("").astype(str).str.replace(",", "", regex=False).str.strip()
            return pd.to_numeric(s, errors="coerce").fillna(0.0)


        def _clean_cf_sep(df_raw: pd.DataFrame) -> pd.DataFrame:
            df = df_raw.copy()
            need = {"구분1", "구분2", "연도", "월", "실적"}
            miss = need - set(df.columns)
            if miss:
                raise ValueError(f"필수 컬럼 누락: {miss}")

            # 문자열 정제 대상 컬럼에 Parent Class 추가
            target_cols = ["구분1", "구분2", "구분3", "구분4", "Parent Class"]
            for c in target_cols:
                if c in df.columns:
                    df[c] = df[c].astype(str).str.strip().str.replace(r"\s+", " ", regex=True)

            # 🟢 [한자 오타 수정 완료] df["연度"] -> df["연도"]로 수정했습니다.
            df["연도"] = pd.to_numeric(df["연도"], errors="coerce").astype("Int64")
            df["월"] = pd.to_numeric(df["월"], errors="coerce").astype("Int64")
            df["실적"] = _to_num(df["실적"])
            df = df[df["구분1"] == "현금흐름표_별도"].copy()
            df["__ord__"] = range(len(df))
            return df


        df0 = _clean_cf_sep(raw)
        year = int(st.session_state["year"])
        month = int(st.session_state["month"])

        # item_order 규칙은 그대로 유지하되, 매칭 로직을 수정합니다.
        item_order = [
            "영업활동현금흐름", "당기순이익", "조정", "감가상각비",
            "조정1",  # 내부적으로 1번째 기타를 식별하기 위함
            "자산부채증감",
            "매출채권 감소(증가)", "재고자산 감소(증가)", "기타자산 감소(증가)",
            "매입채무 증가(감소)", "기타채무 증가(감소)", "법인세납부",
            "투자활동현금흐름", "투자활동 현금유출", "투자활동 현금유입",
            "재무활동현금흐름", "차입금의 증가(감소)",
            "조정2",  # 내부적으로 2번째 기타를 식별하기 위함
            "배당금의 지급", "리스부채의 증감",
            "현금성자산의 증감", "기초현금", "기말현금",
        ]

        name_counts = {}
        order_with_n = []
        for name in item_order:
            name_counts[name] = name_counts.get(name, 0) + 1
            order_with_n.append((name, name_counts[name]))

        index_labels = []
        for nm, _ in order_with_n:
            if nm in ["조정1", "조정2"]:
                index_labels.append("기타")
            else:
                index_labels.append(nm)

        col_prev2_label = f"'{str(year - 2)[-2:]}년"
        col_prev1_label = f"'{str(year - 1)[-2:]}년"
        col_currsum_label = f"'{str(year)[-2:]}년누적"

        data_filter_names = [nm if nm not in ["조정1", "조정2"] else "기타" for nm in item_order]
        sel_month = df0[
            (df0["연도"] == year)
            & (df0["월"] == month)
            & (df0["구분2"].isin(data_filter_names))
            ]

        used_m = month

        if sel_month.empty:
            base = pd.DataFrame(
                {
                    col_prev2_label: [np.nan] * len(index_labels),
                    col_prev1_label: [np.nan] * len(index_labels),
                    "전월누적": [np.nan] * len(index_labels),
                    "당월": [np.nan] * len(index_labels),
                    col_currsum_label: [np.nan] * len(index_labels),
                },
                index=pd.Index(index_labels, name="구분"),
                dtype=float
            )

        else:
            def _sum_item_nth(name: str, nth: int, years, months):
                sub = df0[(df0["연도"].isin(years)) & (df0["월"].isin(months))]
                total = 0.0
                for (_, _), g in sub.groupby(["연도", "월"], sort=False):
                    if name in ["조정1", "조정2"]:
                        if "Parent Class" in g.columns:
                            gg = g[(g["구분2"] == "기타") & (g["Parent Class"] == name)].sort_values("__ord__",
                                                                                                 kind="stable")
                        else:
                            gg = pd.DataFrame()
                    else:
                        gg = g[g["구분2"] == name].sort_values("__ord__", kind="stable")

                    if len(gg) >= nth:
                        total += float(gg.iloc[nth - 1]["실적"])
                return total


            def _block(years, months):
                return [_sum_item_nth(nm, nth, years, months) for (nm, nth) in order_with_n]


            vals_y2 = _block([year - 2], range(1, 13))
            vals_y1 = _block([year - 1], range(1, 13))
            vals_curr = _block([year], range(1, 13))
            prev_ms = range(1, used_m) if used_m > 1 else []
            vals_prev = _block([year], prev_ms) if prev_ms else [0.0] * len(order_with_n)
            vals_ytd = _block([year], range(1, used_m + 1))
            vals_mon = (np.array(vals_ytd) - np.array(vals_prev)).tolist()

            base = pd.DataFrame({
                col_prev2_label: vals_y2,
                col_prev1_label: vals_y1,
                col_currsum_label: vals_curr,
                "전월누적": vals_prev,
                "당월": vals_mon,
            })

        bold_rows = {"영업활동현금흐름", "투자활동현금흐름", "재무활동현금흐름",
                     "현금성자산의 증감", "기초현금", "기말현금"}


        def fmt_num(v):
            try:
                iv = int(round(float(v)))
            except:
                return ""
            if iv < 0:
                return f'<span style="color:red">-{abs(iv):,}</span>'
            return f"{iv:,}"


        th = "border:1px solid #aaa; padding:8px 16px; text-align:center; font-size:15px; font-weight:700; white-space:nowrap;"
        td_l = "border:1px solid #aaa; padding:8px 16px; text-align:left;   font-size:15px; font-weight:400; white-space:nowrap; min-width:200px;"
        td_r = "border:1px solid #aaa; padding:8px 16px; text-align:right;  font-size:15px; font-weight:400; white-space:nowrap;"
        td_l_b = "border:1px solid #aaa; padding:8px 16px; text-align:left;   font-size:15px; font-weight:700; white-space:nowrap; min-width:200px;"
        td_r_b = "border:1px solid #aaa; padding:8px 16px; text-align:right;  font-size:15px; font-weight:700; white-space:nowrap;"

        html = f"""
                <div style="overflow-x:auto;">
                <table style="border-collapse:collapse; width:100%; font-family:'Noto Sans KR', sans-serif;">
                  <thead>
                    <tr>
                      <th style="{th}">구분</th>
                      <th style="{th}">{col_prev2_label}</th>
                      <th style="{th}">{col_prev1_label}</th>
                      <th style="{th}">전월누적</th>
                      <th style="{th}">당월</th>
                      <th style="{th}">{col_currsum_label}</th>
                    </tr>
                  </thead>
                  <tbody>
                """

        lv0 = ["영업활동현금흐름", "투자활동현금흐름", "재무활동현금흐름", "현금성자산의 증감", "기초현금", "기말현금"]
        lv1 = ["당기순이익", "조정", "자산부채증감", "법인세납부",
               "투자활동 현금유출", "투자활동 현금유입",
               "차입금의 증가(감소)", "배당금의 지급", "리스부채의 증감"]
        lv2 = ["감가상각비", "매출채권 감소(증가)", "재고자산 감소(증가)", "기타자산 감소(증가)",
               "매입채무 증가(감소)", "기타채무 증가(감소)"]

        gita_count = 0

        for i, (nm, _) in enumerate(order_with_n):
            label = "기타" if nm in ["조정1", "조정2"] else nm
            is_bold = label in bold_rows
            _l = td_l_b if is_bold else td_l
            _r = td_r_b if is_bold else td_r

            clean_label = str(label).strip()

            if clean_label in lv0:
                lv = 0
            elif clean_label in lv1:
                lv = 1
            elif clean_label in lv2:
                lv = 2
            elif clean_label == "기타":
                gita_count += 1
                if gita_count == 1:
                    lv = 2
                else:
                    lv = 1
            else:
                lv = 0

            _lv_pad = lv * 16

            row = base.iloc[i] if not sel_month.empty else base.iloc[0]

            html += "    <tr>\n"
            html += f'      <td style="{_l}"><span style="padding-left:{_lv_pad}px">{label}</span></td>\n'
            for col in [col_prev2_label, col_prev1_label, "전월누적", "당월", col_currsum_label]:
                val = fmt_num(row[col]) if not sel_month.empty else ""
                html += f'      <td style="{_r}">{val}</td>\n'
            html += "    </tr>\n"

        html += "  </tbody>\n</table>\n</div>"
        st.markdown(html, unsafe_allow_html=True)

        t2_cf_css = """
                <style>
                    .t2-cf-memo { margin-top: -22px !important; }
                    .t2-cf-memo .indent-0 { padding-left: 20px !important; padding-top: 0px !important; text-indent: 0px !important; }
                    .t2-cf-memo .indent-1 { padding-left: 40px !important; text-indent: 0px !important; }
                    .t2-cf-memo p { margin: 0.1rem 0 !important; line-height: 1.3 !important; }
                </style>
                """
        st.markdown(t2_cf_css, unsafe_allow_html=True)
        display_memo('f_12', year, month, css_class="t2-cf-memo")

    except Exception as e:
        st.error(f"현금흐름표 (별도) 생성 중 오류: {e}")

    # 재무상태표 (별도)
    st.divider()

    st.markdown("<h4>8) 재무상태표 (별도)</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:right; font-size:13px; color:#666;'>[단위: 백만원]</div>", unsafe_allow_html=True)

    try:
        file_name = st.secrets["sheets"]["f_3"]
        raw = pd.read_csv(file_name, dtype=str)

        # 🟢 [기타 분리 트릭 추가]
        # 모듈에 들어가기 전, '구분2'가 '기타'인 항목들을 'Parent Class'를 기준으로 고유한 이름으로 바꿔줍니다.
        if "Parent Class" in raw.columns and "구분2" in raw.columns:
            raw["Parent Class"] = raw["Parent Class"].astype(str).str.strip()
            raw["구분2"] = raw["구분2"].astype(str).str.strip()

            mask_gita_asset = (raw["구분2"] == "기타") & (raw["Parent Class"] == "자산총계")
            mask_gita_debt = (raw["구분2"] == "기타") & (raw["Parent Class"] == "부채총계")
            mask_gita_equity = (raw["구분2"] == "기타") & (raw["Parent Class"] == "자본총계")

            raw.loc[mask_gita_asset, "구분2"] = "기타_자산"
            raw.loc[mask_gita_debt, "구분2"] = "기타_부채"
            raw.loc[mask_gita_equity, "구분2"] = "기타_자본"
        # -------------------------------------------------------------

        import importlib

        importlib.invalidate_caches()
        importlib.reload(modules)

        # 🟢 [item_order 수정] 내부 계산용으로 분리한 고유 이름으로 리스트를 구성합니다.
        item_order = [
            '현금및현금성자산', '매출채권', '재고자산', '유형자산', '기타_자산', '자산총계',
            '매입채무', '차입금', '기타_부채', '부채총계',
            '자본금', '이익잉여금', '기타_자본', '자본총계', '부채 및 자본 총계'
        ]

        base = modules.create_bs_from_teuksugang(
            year=int(st.session_state['year']),
            month=int(st.session_state['month']),
            data=raw,
            item_order=item_order
        )


        def _safe_int(x, default=None):
            try:
                return int(x)
            except:
                return default


        year_int = int(st.session_state['year'])
        used_m = _safe_int(base.attrs.get('used_month')) or _safe_int(st.session_state.get('month'), 1)
        prev_m = used_m - 1 if used_m > 1 else 12
        prev_y = year_int if used_m > 1 else year_int - 1

        yy_used = f"{year_int % 100:02d}"
        yy_prevY = f"{(year_int - 1) % 100:02d}"

        prev_year_col = f"'{yy_prevY}년말"
        prev_month_col = f"'{yy_used}"
        curr_month_col = "당월"
        diff_col = "전월비 증감"

        h_yend = f"'{yy_prevY}년말"
        h_prev = f"'{yy_used} {prev_m}월"
        h_curr = f"'{yy_used} {used_m}월"
        h_diff = "전월대비"


        def fmt_cell(x):
            if pd.isna(x):
                return ""
            try:
                v = float(str(x).replace(",", "").replace("(", "-").replace(")", ""))
            except Exception:
                return str(x)
            if v == 0:
                return "0"
            return f'<span style="color:red">-{abs(int(round(v))):,}</span>' if v < 0 else f"{int(round(v)):,}"


        bold_rows = {"자산총계", "부채총계", "자본총계", "부채 및 자본 총계"}

        th = "border:1px solid #aaa; padding:8px 16px; text-align:center; font-size:15px; font-weight:700;"
        td_l = "border:1px solid #aaa; padding:8px 16px; text-align:left;   font-size:15px; font-weight:400;"
        td_r = "border:1px solid #aaa; padding:8px 16px; text-align:right;  font-size:15px; font-weight:400;"
        td_l_b = "border:1px solid #aaa; padding:8px 16px; text-align:left;   font-size:15px; font-weight:700;"
        td_r_b = "border:1px solid #aaa; padding:8px 16px; text-align:right;  font-size:15px; font-weight:700;"

        html = f"""
        <table style="border-collapse:collapse; width:100%; font-family:'Noto Sans KR', sans-serif;">
          <thead>
            <tr>
              <th style="{th}">구 분</th>
              <th style="{th}">{h_yend}</th>
              <th style="{th}">{h_prev}</th>
              <th style="{th}">{h_curr}</th>
              <th style="{th}">{h_diff}</th>
            </tr>
          </thead>
          <tbody>
        """
        for label in item_order:
            # 🟢 [출력 라벨 복구] 화면에 보여줄 때는 '기타_자산' 등을 다시 '기타'로 바꿔서 출력합니다.
            display_label = "기타" if str(label).startswith("기타_") else label
            clean_label = str(display_label).strip()

            is_bold = clean_label in bold_rows
            _l = td_l_b if is_bold else td_l
            _r = td_r_b if is_bold else td_r

            lv = 0 if is_bold else 1

            try:
                # base 데이터프레임의 인덱스는 item_order와 동일하므로 label(ex. 기타_자산)로 찾습니다.
                row = base.loc[label]
                v_yend = fmt_cell(row.get(prev_year_col, ""))
                v_prev = fmt_cell(row.get(prev_month_col, ""))
                v_curr = fmt_cell(row.get(curr_month_col, ""))
                v_diff = fmt_cell(row.get(diff_col, ""))
            except:
                v_yend, v_prev, v_curr, v_diff = "", "", "", ""

            html += f"""    <tr>
              <td style="{_l}"><span style="padding-left:{lv * 16}px">{display_label}</span></td>
              <td style="{_r}">{v_yend}</td>
              <td style="{_r}">{v_prev}</td>
              <td style="{_r}">{v_curr}</td>
              <td style="{_r}">{v_diff}</td>
            </tr>
        """
        html += "  </tbody>\n</table>"
        st.markdown(html, unsafe_allow_html=True)

        # 🟢 [재무상태표 전용 격리 스타일]
        t2_bs_css = """
            <style>
                .t2-bs-memo { margin-top: -22px !important; }
                .t2-bs-memo .indent-0 { padding-left: 20px !important; padding-top: 0px !important; text-indent: 0px !important; }
                .t2-bs-memo .indent-1 { padding-left: 40px !important; text-indent: 0px !important; }
                .t2-bs-memo p { margin: 0.1rem 0 !important; line-height: 1.3 !important; }
            </style>
            """
        st.markdown(t2_bs_css, unsafe_allow_html=True)
        display_memo('f_3', year_int, used_m, css_class="t2-bs-memo")

    except Exception as e:
        st.error(f"재무상태표 (별도) 생성 중 오류: {e}")

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

            snap = modules.create_turnover_special_steel(
                year=int(st.session_state['year']),
                month=int(st.session_state['month']),
                data=raw
            )


            def fmt1(x):
                try:
                    v = float(x)
                    return f"{v:.1f}" if pd.notnull(v) else ""
                except:
                    return x


            cols_base = snap.columns.tolist()
            col_yend = next((c for c in cols_base if '년말' in str(c)), cols_base[0] if cols_base else "")
            col_prev = next((c for c in cols_base if '전월' in str(c) and '대비' not in str(c)),
                            cols_base[1] if len(cols_base) > 1 else "")
            col_curr = next((c for c in cols_base if '당월' in str(c)),
                            cols_base[2] if len(cols_base) > 2 else "")
            col_diff = next((c for c in cols_base if '전월대비' in str(c) or '대비' in str(c)),
                            cols_base[3] if len(cols_base) > 3 else "")

            th = "border:1px solid #aaa; padding:8px 12px; text-align:center; font-size:15px; font-weight:700;"
            td_c = "border:1px solid #aaa; padding:6px 12px; text-align:center; font-size:15px; vertical-align:middle;"
            td_l = "border:1px solid #aaa; padding:6px 12px; text-align:left;   font-size:15px;"
            # 🔴 [정렬 교정] 수치 셀 우측 정렬(right)로 변경
            td_r = "border:1px solid #aaa; padding:6px 12px; text-align:right;  font-size:15px;"

            rows_info = [
                ("매출채권 ⓐ", "매출채권"),
                ("재고자산 ⓑ", "재고자산"),
                ("매입채무 ⓒ", "매입채무"),
                ("현금전환주기<br>(ⓐ+ⓑ-ⓒ)", "현금전환주기"),
            ]

            html = f"""
    <table style="border-collapse:collapse; width:100%; font-family:'Noto Sans KR', sans-serif;">
    <thead>
    <tr>
      <th colspan="2" style="{th}">구분</th>
      <th style="{th}">{col_yend}</th>
      <th style="{th}">{col_prev}</th>
      <th style="{th}">{col_curr}</th>
      <th style="{th}">{col_diff}</th>
    </tr>
    </thead>
    <tbody>
    """
            for i, (label, idx) in enumerate(rows_info):
                try:
                    row = snap.loc[idx]
                    v_end = fmt1(row.get(col_yend, ""))
                    v_pre = fmt1(row.get(col_prev, ""))
                    v_cur = fmt1(row.get(col_curr, ""))
                    v_dif = fmt1(row.get(col_diff, ""))
                except:
                    v_end, v_pre, v_cur, v_dif = "", "", "", ""

                if i == 0:
                    html += f"""    <tr>
      <td rowspan="4" style="{td_c}">회전일<br>(일)</td>
      <td style="{td_l}">{label}</td>
      <td style="{td_r}">{v_end}</td>
      <td style="{td_r}">{v_pre}</td>
      <td style="{td_r}">{v_cur}</td>
      <td style="{td_r}">{v_dif}</td>
    </tr>
    """
                else:
                    html += f"""    <tr>
      <td style="{td_l}">{label}</td>
      <td style="{td_r}">{v_end}</td>
      <td style="{td_r}">{v_pre}</td>
      <td style="{td_r}">{v_cur}</td>
      <td style="{td_r}">{v_dif}</td>
    </tr>
    """
            html += "  </tbody>\n</table>"
            st.markdown(html, unsafe_allow_html=True)

            # 🟢 [회전일 전용 격리 스타일]
            t2_turn_css = """
                <style>
                    .t2-turn-memo { margin-top: -22px !important; }
                    .t2-turn-memo .indent-0 { padding-left: 20px !important; padding-top: 0px !important; text-indent: 0px !important; }
                    .t2-turn-memo .indent-1 { padding-left: 40px !important; text-indent: 0px !important; }
                    .t2-turn-memo p { margin: 0.1rem 0 !important; line-height: 1.3 !important; }
                </style>
                """
            st.markdown(t2_turn_css, unsafe_allow_html=True)
            display_memo('f_15', year, month, css_class="t2-turn-memo")

        except Exception as e:
            st.error(f"회전일 표 생성 중 오류: {e}")

    with col_mid:
        st.markdown("<div class='v-divider'></div>", unsafe_allow_html=True)

    with col_right:

        st.markdown("<h4>11) 수익성 (별도)</h4>", unsafe_allow_html=True)

        try:
            file_name = st.secrets["sheets"]["f_16"]
            raw = pd.read_csv(file_name, dtype=str)

            snap = modules.create_profitability_special_steel(
                year=int(st.session_state['year']),
                month=int(st.session_state['month']),
                data=raw
            )


            def fmt1(x):
                try:
                    v = float(x)
                    return f"{v:.2f}%" if pd.notnull(v) else ""
                except:
                    return x


            cols_base = snap.columns.tolist()
            col_yend = next((c for c in cols_base if '년말' in str(c)), cols_base[0] if cols_base else "")
            col_prev = next((c for c in cols_base if '전월' in str(c) and '대비' not in str(c)),
                            cols_base[1] if len(cols_base) > 1 else "")
            col_curr = next((c for c in cols_base if '당월' in str(c) or (
                    '.' in str(c) and '월' in str(c) and '년말' not in str(c) and c != col_prev)),
                            cols_base[2] if len(cols_base) > 2 else "")
            col_diff = next((c for c in cols_base if '전월대비' in str(c) or '대비' in str(c)),
                            cols_base[3] if len(cols_base) > 3 else "")


            def fmt_diff(x):
                try:
                    v = float(x)
                    return f"{v:.1f}p" if pd.notnull(v) else ""
                except:
                    return x


            th = "border:1px solid #aaa; padding:8px 12px; text-align:center; font-size:15px; font-weight:700;"
            td_c = "border:1px solid #aaa; padding:6px 12px; text-align:center; font-size:15px; vertical-align:middle;"
            td_l = "border:1px solid #aaa; padding:6px 12px; text-align:left;   font-size:15px;"
            # 🔴 [정렬 교정] 수치 셀 우측 정렬(right)로 변경
            td_r = "border:1px solid #aaa; padding:6px 12px; text-align:right;  font-size:15px;"

            rows_info = [
                ("ROA", "ROA"),
                ("ROE", "ROE"),
            ]

            html = f"""
    <table style="border-collapse:collapse; width:100%; font-family:'Noto Sans KR', sans-serif;">
    <thead>
    <tr>
      <th colspan="2" style="{th}">구분</th>
      <th style="{th}">{col_yend}</th>
      <th style="{th}">{col_prev}</th>
      <th style="{th}">{col_curr}</th>
      <th style="{th}">전월대비</th>
    </tr>
    </thead>
    <tbody>
    """
            for i, (label, idx) in enumerate(rows_info):
                try:
                    row = snap.loc[idx]
                    v_end = fmt1(row.get(col_yend, ""))
                    v_pre = fmt1(row.get(col_prev, ""))
                    v_cur = fmt1(row.get(col_curr, ""))
                    v_dif = fmt_diff(row.get(col_diff, ""))
                except:
                    v_end, v_pre, v_cur, v_dif = "", "", "", ""

                if i == 0:
                    html += f"""    <tr>
      <td rowspan="2" style="{td_c}">수익성</td>
      <td style="{td_l}">{label}</td>
      <td style="{td_r}">{v_end}</td>
      <td style="{td_r}">{v_pre}</td>
      <td style="{td_r}">{v_cur}</td>
      <td style="{td_r}">{v_dif}</td>
    </tr>
    """
                else:
                    html += f"""    <tr>
      <td style="{td_l}">{label}</td>
      <td style="{td_r}">{v_end}</td>
      <td style="{td_r}">{v_pre}</td>
      <td style="{td_r}">{v_cur}</td>
      <td style="{td_r}">{v_dif}</td>
    </tr>
    """
            html += "  </tbody>\n</table>"
            st.markdown(html, unsafe_allow_html=True)

            # 🟢 [수익성 전용 격리 스타일]
            t2_prof_css = """
                <style>
                    .t2-prof-memo { margin-top: -22px !important; }
                    .t2-prof-memo .indent-0 { padding-left: 20px !important; padding-top: 0px !important; text-indent: 0px !important; }
                    .t2-prof-memo .indent-1 { padding-left: 40px !important; text-indent: 0px !important; }
                    .t2-prof-memo p { margin: 0.1rem 0 !important; line-height: 1.3 !important; }
                </style>
                """
            st.markdown(t2_prof_css, unsafe_allow_html=True)
            display_memo('f_16', year, month, css_class="t2-prof-memo")

        except Exception as e:
            st.error(f"수익 표 생성 중 오류: {e}")

    st.markdown("</div></div>", unsafe_allow_html=True)

    # ─ 가로 스크롤 래퍼 닫기 ─
    st.markdown("</div></div>", unsafe_allow_html=True)


# =========================
# 연간사업계획


with t3:
    st.markdown("<h4>1) 판매계획 및 실적</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:right; font-size:13px; color:#666;'>[단위: 톤,천개,억원]</div>",
                unsafe_allow_html=True)

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


        def fmt_signed(x: float, decimals=0):
            try:
                if x is None or pd.isna(x) or x == "":
                    return ""
                v = float(x)
                neg = v < 0
                v_abs = abs(v)
                s = f"{v_abs:,.{decimals}f}" if decimals > 0 else f"{int(v_abs):,}"
                return f"<span style='color:red;'>-{s}%</span>" if neg else f"{s}%"
            except Exception:
                return str(x)


        def fmt_pct(x):
            return fmt_signed(x, 0)


        def fmt_number(x, decimals=0):
            try:
                if x is None or pd.isna(x) or x == "":
                    return ""
                v = float(x)
                neg = v < 0
                v_abs = abs(v)
                s = f"{v_abs:,.{decimals}f}" if decimals > 0 else f"{int(v_abs):,}"
                return f"<span style='color:red;'>-{s}</span>" if neg else s
            except Exception:
                return str(x)


        def to_numeric(s):
            return pd.to_numeric(s, errors="coerce")


        disp = base.copy()
        disp.index.name = "구분"
        disp = disp.reset_index()

        tuple_cols = [
            ("사업 계획(연간)", "판매량"), ("사업 계획(연간)", "단가"), ("사업 계획(연간)", "매출액"),
            ("사업 계획(누적)", "판매량"), ("사업 계획(누적)", "단가"), ("사업 계획(누적)", "매출액"),
            ("실적(누적)", "판매량"), ("실적(누적)", "단가"), ("실적(누적)", "매출액"),
            ("실적-계획", "판매량"), ("실적-계획", "단가"), ("실적-계획", "매출액"),
            ("달성률(%)", "판매량"), ("달성률(%)", "매출액")
        ]

        disp_values = disp.copy()


        def round_then_strip(v, round_place, strip_factor):
            if pd.isna(v):
                return np.nan
            r = np.round(float(v), round_place)
            return int(r // strip_factor)


        for col in disp_values.columns:
            if col == '구분':
                continue

            grp = str(col[0]).strip() if isinstance(col, tuple) else ''
            metric = str(col[1]).strip() if isinstance(col, tuple) else ''

            # 달성률(%)은 무조건 나누기 패스!
            if grp == "달성률(%)":
                continue

            if metric == "단가":
                s = to_numeric(disp_values[col])
                disp_values[col] = s.apply(
                    lambda v: (
                        np.nan if pd.isna(v) else
                        int(float(v)) if abs(float(v)) < 100_000 else
                        round_then_strip(v, -2, 1000)
                    )
                )
            elif metric == "매출액":
                s = to_numeric(disp_values[col])
                # 🟢 [수정됨] 판매량과 똑같이 1,000,000 이상일 때만 1000으로 나누도록 변경
                disp_values[col] = s.apply(
                    lambda v: (round_then_strip(v, -3, 1000)
                               if (not pd.isna(v) and abs(float(v)) >= 1_000_000)
                               else (np.nan if pd.isna(v) else int(float(v))))
                )
            elif metric == "판매량":
                s = to_numeric(disp_values[col])
                disp_values[col] = s.apply(
                    lambda v: (round_then_strip(v, -3, 1000)
                               if (not pd.isna(v) and abs(float(v)) >= 1_000_000)
                               else (np.nan if pd.isna(v) else int(float(v))))
                )

        body = disp_values.copy()
        for col in body.columns:
            if col == '구분':
                continue
            grp = col[0] if isinstance(col, tuple) else ''
            metric = str(col[1]).strip() if isinstance(col, tuple) else ''
            if grp == "달성률(%)":
                body[col] = body[col].apply(lambda x: fmt_pct(x))
            elif metric in ("판매량", "단가", "매출액"):
                body[col] = body[col].apply(lambda x: fmt_number(x, 0))

        flat_headers = [
            "구분",
            "사업 계획_판매량 (연간)", "사업 계획_단가 (연간)", "사업 계획_매출액 (연간)",
            "사업 계획_판매량 (누적)", "사업 계획_단가 (누적)", "사업 계획_매출액 (누적)",
            "실적_판매량 (누적)", "실적_단가 (누적)", "실적_매출액 (누적)",
            "판매량 (실적 - 계획)", "단가 (실적 - 계획)", "매출액 (실적 - 계획)",
            "달성률(%)_판매량", "달성률(%)_매출액"
        ]

        th_style = "border:1px solid #aaa; background:white; padding:8px 16px; text-align:center; font-weight:700; white-space:nowrap; font-size:15px;"

        header_html = "<tr>"
        for h_name in flat_headers:
            header_html += f"<th style='{th_style}'>{h_name}</th>"
        header_html += "</tr>"

        lv0_items = ['국내 계', '중국 계', '태국 계', 'Total']
        lv1_items = ['국내_선재사업부문', '국내_AT사업부문', '중국_포스세아 남통', '중국_기차배건', '선재 계', 'AT 계']
        lv2_items = ['내수_계', '수출_글로벌영업팀']
        lv3_items = ['내수_선재영업팀', '내수_봉강영업팀', '내수_부산영업소', '내수_대구영업소']

        bold_items = ['내수_계', '국내 계', '중국 계', '태국 계', 'Total', '선재 계', 'AT 계']

        body_html = ""
        for _, row in body.iterrows():
            raw_label = row.get('구분', '')
            if isinstance(raw_label, pd.Series):
                raw_label = raw_label.iloc[0]
            label = str(raw_label).strip()

            if label in lv0_items:
                lv = 0
            elif label in lv1_items:
                lv = 1
            elif label in lv2_items:
                lv = 2
            elif label in lv3_items:
                lv = 3
            else:
                lv = 0

            is_bold = label in bold_items
            fw = '700' if is_bold else '400'

            # 🔴 [정렬 교정] 수치 셀들의 정렬을 표준 우측 정렬(right)로 변경했습니다.
            td_style = f"border:1px solid #aaa; padding:8px 16px; text-align:right; font-weight:{fw}; font-size:15px;"
            td_left_style = f"border:1px solid #aaa; padding:8px 16px; text-align:left; font-weight:{fw}; white-space:nowrap; font-size:15px;"

            body_html += "<tr>"
            body_html += f"<td style='{td_left_style}'><span style='padding-left:{lv * 16}px'>{label}</span></td>"

            for c_col in base.columns:
                val = row.get(c_col, '')
                if isinstance(val, pd.Series):
                    val = val.iloc[0]
                val = '' if pd.isna(val) else str(val)
                body_html += f"<td style='{td_style}'>{val}</td>"
            body_html += "</tr>"

        html = f"""
                <div style='overflow-x:auto'>
                <table style='border-collapse:collapse; width:100%; font-size:15px; font-family:"Noto Sans KR",sans-serif;'>
                    <thead>
                        {header_html}
                    </thead>
                    <tbody>
                        {body_html}
                    </tbody>
                </table>
                </div>
                """
        # 1. 표 출력
        st.markdown(html, unsafe_allow_html=True)

        # 2. 🟢 이 표 바로 밑에 복사될 t3 탭 전용 격리 스타일 가이드
        t3_exclusive_css = """
        <style>
            .t3-special-memo {
                margin-top: -22px !important;    /* 표와 메모 사이 간격을 위로 바짝 붙임 */
            }
            .t3-special-memo .indent-0 { 
                padding-left: 20px !important;   /* '구분' 열 시작선 라인에 수직 정렬 일치 */
                padding-top: 0px !important;     
                text-indent: 0px !important;     /* 마이너스 내어쓰기 초기화 */
            }
            .t3-special-memo .indent-1 { 
                padding-left: 40px !important; 
                text-indent: 0px !important; 
            }
            .t3-special-memo .indent-2 { 
                padding-left: 60px !important; 
            }
            /* 문장 간 격자 간격을 0.1rem으로 축소하고 행간 조절 */
            .t3-special-memo p {
                margin: 0.1rem 0 !important;      
                line-height: 1.3 !important;      
            }
        </style>
        """
        st.markdown(t3_exclusive_css, unsafe_allow_html=True)

        # 3. 🟢 격리 이름표(t3-special-memo)를 전달하여 메모를 안전하게 생성합니다.
        display_memo('f_17', year, month, css_class="t3-special-memo")

    except Exception as e:
        st.error(f"판매계획 및 실적 표 생성 중 오류: {e}")

st.markdown("""
<style>.footer { bottom: 0; left: 0; right: 0; padding: 8px; text-align: center; font-size: 13px; color: #666666;}</style>
<div class="footer">ⓒ 2025 SeAH Special Steel Corp. All rights reserved.</div>
""", unsafe_allow_html=True)