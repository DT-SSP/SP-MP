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

    st.markdown(styled_df.to_html(escape=False), unsafe_allow_html=True)


##### 메모 #####
def create_indented_html(s):
    """문자열의 앞 공백을 기반으로 들여쓰기된 HTML <p> 태그를 생성합니다."""
    content = s.lstrip(' ')
    num_spaces = len(s) - len(content)
    indent_level = num_spaces // 2
    return f'<p class="indent-{indent_level}">{content}</p>'


def display_memo(memo_file_key, year, month, ):
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

st.markdown("""
<style>
table, td, th {
    font-size: 17px !important;
    font-family: 'Noto Sans KR', sans-serif !important;
}
</style>
""", unsafe_allow_html=True)
t1, t2, t3 = st.tabs(['주요경영지표', '주요경영지표(본사)', '연간사업계획'])

# =========================



# 주요경영지표


with t1:
    st.divider()
    # ===== 1) 손익 (연결) =====
    st.markdown("<h4>1) 손익 (연결) </h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:15px; color:#666;'>[단위: 톤, 백만원, %]</div>",
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
            # 이미 - 기호로 시작하는 경우
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


        styles = [
            {'selector': 'thead', 'props': [('display', 'none')]},
            {'selector': 'table', 'props': [('border-collapse', 'collapse')]},
            {'selector': 'td', 'props': [('border', '1px solid #000'), ('padding', '6px 10px')]},
            {'selector': 'tbody tr:nth-child(1) td',
             'props': [('text-align', 'center'), ('font-weight', '600'), ('border-top', '2px solid #000'),
                       ('white-space', 'pre-line')]},
            {'selector': 'tbody tr:nth-child(n+2) td', 'props': [('text-align', 'right')]},
            {'selector': f'td:nth-child({nth("구분")})', 'props': [('text-align', 'left')]},
            {'selector': 'tbody tr:last-child td', 'props': [('border-bottom', '2px solid #000')]},
        ]

        display_styled_df(disp_vis, styles=styles, already_flat=True)
        st.caption("각 %는 계산")
        display_memo('f_1', year, month)

    except Exception as e:
        st.error(f"손익 연결 생성 중 오류: {e}")


    # ===== 2) 현금흐름표 (연결) =====
    st.divider()


    st.markdown("<h4>2) 현금흐름표 (연결)</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:15px; color:#666;'>[단위: 백만원]</div>",
                unsafe_allow_html=True)

    try:
        file_name = st.secrets["sheets"]["f_2"]
        raw = pd.read_csv(file_name, dtype=str)

        base = modules.create_cashflow_by_gubun(
            year=int(st.session_state['year']),
            month=int(st.session_state['month']),
            data=raw
        )

        # ── 연도/월 정보 ──
        used_y = int(base.attrs.get("used_year", year))
        used_m = int(base.attrs.get("used_month", month))
        prev_y = used_y
        prev_m = used_m - 1
        if prev_m <= 0:
            prev_y -= 1
            prev_m += 12

        # ── 컬럼명 변경: 남통→중국, 연도컬럼 라벨 변경 ──
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


        # ── 숫자 포맷 ──
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

        disp = disp.reset_index()  # 구분 컬럼 생성

        # ── level/parent_name 컬럼으로 들여쓰기 적용 ──
        if 'level' in raw.columns:
            level_map = {}
            for _, row in raw[['구분3', 'parent_name', 'level']].dropna(subset=['구분3']).iterrows():
                key = (str(row['구분3']).strip(), str(row['parent_name']).strip())
                try:
                    level_map[key] = int(row['level'])
                except (TypeError, ValueError):
                    level_map[key] = 0


            def get_indent(name):
                # parent_name 없이 이름만으로 먼저 찾기
                for (n, p), lv in level_map.items():
                    if n == str(name).strip():
                        return '\u00a0' * lv + str(name)
                return str(name)


            disp['구분'] = disp['구분'].apply(get_indent)

        # ── 볼드 처리할 행 인덱스 ──
        bold_rows = ['영업활동현금흐름', '투자활동현금흐름', '재무활동현금흐름']

        # ── 스타일 ──
        styles = [
            {'selector': 'table', 'props': [('border-collapse', 'collapse'), ('width', '100%'),
                                            ('font-family', "'Noto Sans KR', sans-serif"), ('font-size', '13px')]},
            {'selector': 'thead th',
             'props': [('background-color', 'white'), ('text-align', 'center'), ('border', '1px solid black'),
                       ('padding', '6px 10px'), ('font-weight', '700')]},
            {'selector': 'tbody td',
             'props': [('border', '1px solid black'), ('padding', '5px 10px'), ('text-align', 'right')]},
            {'selector': 'tbody td:first-child', 'props': [('text-align', 'left'), ('font-weight', '400')]},
        ]

        # 볼드 행 스타일
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

        st.markdown(
            f"<div style='overflow-x:auto'>{styled.to_html(escape=False)}</div>",
            unsafe_allow_html=True
        )
        display_memo('f_2', year, month)

    except Exception as e:
        st.error(f"현금흐름표 연결 생성 중 오류: {e}")

    st.divider()

    # ===== 3) 재무상태표 (연결) =====
    st.markdown("<h4>3) 재무상태표</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:15px; color:#666;'>[단위: 백만원]</div>",
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
            {'selector': 'table', 'props': [('border-collapse', 'collapse'), ('font-size', '13px')]},
            {'selector': 'td',
             'props': [('border', '1px solid #000'), ('padding', '5px 10px'), ('background-color', 'white')]},
            {'selector': 'tbody tr:nth-child(1) td',
             'props': [('text-align', 'center'), ('font-weight', '600'),
                       ('border-top', '2px solid #000'), ('border-bottom', '2px solid #000'),
                       ('background-color', 'white')]},
            {'selector': 'tbody tr:nth-child(n+2) td', 'props': [('text-align', 'right')]},
            {'selector': 'tbody tr:nth-child(n+2) td:nth-child(1)',
             'props': [('text-align', 'left'), ('white-space', 'nowrap')]},
            {'selector': 'tbody tr:last-child td', 'props': [('border-bottom', '2px solid #000')]},
        ]
        bold_items = ['자산총계', '부채총계', '자본총계', '부채 및 자본 총계']
        for i, item in enumerate(item_order):
            if item in bold_items:
                row_num = i + 2
                styles.append({'selector': f'tbody tr:nth-child({row_num}) td',
                               'props': [('font-weight', '700'), ('border-top', '2px solid #000')]})

        display_styled_df(disp_vis, styles=styles, already_flat=True)
        display_memo('f_3', year, month)

    except Exception as e:
        st.error(f"재무상태표 생성 중 오류: {e}")

    st.divider()

    st.markdown(
        """
        <style>
        .block-container {
            min-width: 1600px;
            margin-left: 0 !important;
            margin-right: auto !important;
        }
        .main { overflow-x: auto; }
        </style>
        """,
        unsafe_allow_html=True
    )

    col_left, col_mid, col_right = st.columns([1, 0.05, 1])

    with col_left:
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
                ('매임채무', '매입채무 ⓒ'),
                ('현금전환주기', '현금전환주기\n(ⓐ+ⓑ-ⓒ)'),
            ]

            th = "style='border:1px solid #000; padding:5px 10px; text-align:center; font-weight:600; background-color:white;'"
            td_left = "style='border:1px solid #000; padding:5px 10px; text-align:left; white-space:pre-line;'"
            td_center = "style='border:1px solid #000; padding:5px 10px; text-align:center; font-weight:600; vertical-align:middle;'"
            td_num = "style='border:1px solid #000; padding:5px 10px; text-align:right;'"
            td_red = "style='border:1px solid #000; padding:5px 10px; text-align:right; color:red;'"


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
<table style="border-collapse:collapse; font-size:15px; width:100%;">
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
            st.markdown(html, unsafe_allow_html=True)
            display_memo('f_4', year, month)

        except Exception as e:
            st.error(f"회전일 표 생성 중 오류: {e}")

    with col_mid:
        st.markdown("<div class='v-divider'></div>", unsafe_allow_html=True)

    with col_right:
        # ===== 5) ROE =====
        try:
            st.markdown("<h4>5) ROE</h4>", unsafe_allow_html=True)
            st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 백만원]</div>",
                        unsafe_allow_html=True)

            file_name = st.secrets["sheets"]["f_5"]
            raw = pd.read_csv(file_name, dtype=str)

            import importlib

            importlib.invalidate_caches()
            importlib.reload(modules)

            base = modules.create_roe_table(year=year, month=month, data=raw)
            disp = base.reset_index().rename(columns={"index": "구분"})

            styles = [
                {
                    'selector': 'thead th',
                    'props': [
                        ('text-align', 'center'),
                        ('padding', '10px 8px'),
                        ('font-weight', '600'),
                        ('border', '1px solid black'),
                    ]
                },
                {
                    'selector': 'tbody td',
                    'props': [
                        ('padding', '8px 10px'),
                        ('text-align', 'right'),
                        ('border', '1px solid black'),
                    ]
                },
                {
                    'selector': 'tbody td:nth-child(1)',
                    'props': [('text-align', 'left')]
                },
            ]

            display_styled_df(disp, styles=styles, highlight_cols=None, already_flat=True)

            st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>* ROE = 당기순이익/ 자본총계, 연결기준</div>",
                        unsafe_allow_html=True)
            st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>* 유효법인세율 20% 반영</div>",
                        unsafe_allow_html=True)

            display_memo('f_5', year, month)

        except Exception as e:
            st.error(f"ROE 표 생성 중 오류: {e}")

    # ─ 가로 스크롤 래퍼 닫기 ─
    st.markdown("</div></div>", unsafe_allow_html=True)

    with t2:

        st.markdown("<h4>1) 손익(별도)</h4>", unsafe_allow_html=True)
        st.markdown("<div style='text-align:left; font-size:15px; color:#666;'>[단위: 톤, 백만원, %]</div>",
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
                v_thousand = v / 1000.0
                r = int(Decimal(str(v_thousand)).quantize(Decimal("0"), rounding=ROUND_HALF_UP))
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

            th = "style='border:1px solid #000; padding:5px 10px; text-align:center; font-weight:600; background-color:white;'"
            td_left = "style='border:1px solid #000; padding:5px 10px; text-align:left; white-space:nowrap;'"
            td_right = "style='border:1px solid #000; padding:5px 10px; text-align:right;'"


            def make_td(v, row_label):
                s = str(v) if v is not None else ""
                try:
                    fv = float(str(s).replace(',', '').replace('-', '').strip())
                    if str(s).startswith('-') and fv != 0:
                        return f'<td style="border:1px solid #000; padding:5px 10px; text-align:right; color:red;">{s}</td>'
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

            st.markdown(html, unsafe_allow_html=True)
            display_memo('f_1_2', year, month)

        except Exception as e:
            st.error(f"손익 별도 생성 중 오류: {e}")

        st.divider()

        st.markdown("<h4>2) 품목손익 (별도)</h4>", unsafe_allow_html=True)
        st.markdown("<div style='text-align:left; font-size:15px; color:#666;'>[단위: 톤, 백만원, %]</div>",
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

            td_base = "border:1px solid black; padding:5px 8px; text-align:right; font-size:15px;"
            th_base = "border:1px solid black; padding:5px 8px; text-align:center; font-size:15px; font-weight:600;"
            td_center = td_base.replace("text-align:right", "text-align:center")

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
            display_memo('f_7', year, month)

        except Exception as e:
            st.error(f"품목손익 (별도) 생성 중 오류: {e}")

        # 수정원가기준 손익(별도)
        st.divider()

        st.markdown("<h4>3) 수정원가기준 손익 (별도)</h4>", unsafe_allow_html=True)
        st.markdown("<div style='text-align:left; font-size:15px; color:#666;'>[단위: 톤, 백만원, %]</div>",
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


            th = "border:1px solid black; padding:6px 10px; text-align:center; font-size:15px; font-weight:600;"
            td_r = "border:1px solid black; padding:6px 10px; text-align:right; font-size:15px;"
            td_c = "border:1px solid black; padding:6px 10px; text-align:center; font-size:15px;"

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

        st.divider()

        st.markdown("<h4>4) 원재료 입고-기초 단가 차이</h4>", unsafe_allow_html=True)

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
                    return f'<span style="color:red">-{abs(v):,}</span>'
                return f"{v:,}"


            th = "border:1px solid black; padding:6px 10px; text-align:center; font-size:15px; font-weight:600;"
            td_l = "border:1px solid black; padding:6px 10px; text-align:left;   font-size:15px;"
            td_r = "border:1px solid black; padding:6px 10px; text-align:right;  font-size:15px;"
            td_l_bold = "border:1px solid black; padding:6px 10px; text-align:left;   font-size:15px; font-weight:700;"
            td_r_bold = "border:1px solid black; padding:6px 10px; text-align:right;  font-size:15px; font-weight:700;"

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

        st.divider()

        st.markdown("<h4>5) 원재료 입고-기초 단가 차이 거래처 기준</h4>", unsafe_allow_html=True)

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
                    return f'<span style="color:red">-{abs(v):,}</span>'
                return f"{v:,}"


            th = "border:1px solid black; padding:6px 10px; text-align:center; font-size:15px; font-weight:600;"
            td_l = "border:1px solid black; padding:6px 10px; text-align:left;   font-size:15px;"
            td_r = "border:1px solid black; padding:6px 10px; text-align:right;  font-size:15px;"
            td_l_bold = "border:1px solid black; padding:6px 10px; text-align:left;   font-size:15px; font-weight:700;"
            td_r_bold = "border:1px solid black; padding:6px 10px; text-align:right;  font-size:15px; font-weight:700;"

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

            th = "border:1px solid black; padding:10px 20px; text-align:center; font-size:15px; font-weight:400;"
            td = "border:1px solid black; padding:10px 20px; text-align:right;  font-size:15px;"

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

        st.divider()

        st.markdown("<h4>7) 현금흐름표 손익 (별도)</h4>", unsafe_allow_html=True)
        st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 톤, 백만원, %]</div>",
                    unsafe_allow_html=True)

        try:
            file_name = st.secrets["sheets"]["f_12"]
            raw = pd.read_csv(file_name, dtype=str)


            def _to_num(s: pd.Series) -> pd.Series:
                s = s.fillna("").astype(str).str.replace(",", "", regex=False).str.strip()
                return pd.to_numeric(s, errors="coerce").fillna(0.0)


            def _clean_cf_sep(df_raw: pd.DataFrame) -> pd.DataFrame:
                df = df_raw.copy()
                need = {"구분1", "구분2", "연도", "월", "실적"}
                miss = need - set(df.columns)
                if miss:
                    raise ValueError(f"필수 컬럼 누락: {miss}")
                for c in ["구분1", "구분2", "구분3", "구분4"]:
                    if c in df.columns:
                        df[c] = df[c].astype(str).str.strip().str.replace(r"\s+", " ", regex=True)
                df["연도"] = pd.to_numeric(df["연도"], errors="coerce").astype("Int64")
                df["월"] = pd.to_numeric(df["월"], errors="coerce").astype("Int64")
                df["실적"] = _to_num(df["실적"])
                df = df[df["구분1"] == "현금흐름표_별도"].copy()
                df["__ord__"] = range(len(df))
                return df


            df0 = _clean_cf_sep(raw)
            year = int(st.session_state["year"])
            month = int(st.session_state["month"])

            item_order = [
                "영업활동현금흐름", "당기순이익", "조정", "감가상각비", "기타", "자산부채증감",
                "매출채권 감소(증가)", "재고자산 감소(증가)", "기타자산 감소(증가)",
                "매입채무 증가(감소)", "기타채무 증가(감소)", "법인세납부",
                "투자활동현금흐름", "투자활동 현금유출", "투자활동 현금유입",
                "재무활동현금흐름", "차입금의 증가(감소)", "기타", "배당금의 지급",
                "리스부채의 증감", "현금성자산의 증감", "기초현금", "기말현금",
            ]

            name_counts = {}
            order_with_n = []
            for name in item_order:
                name_counts[name] = name_counts.get(name, 0) + 1
                order_with_n.append((name, name_counts[name]))
            index_labels = [nm for nm, _ in order_with_n]

            col_prev2_label = f"'{str(year - 2)[-2:]}년"
            col_prev1_label = f"'{str(year - 1)[-2:]}년"
            col_curr_label = f"'{str(year)[-2:]}년"
            col_currsum_label = f"'{str(year + 1)[-2:]}년 누적"

            used_m = month


            def _sum_item_nth(name, nth, years, months):
                sub = df0[(df0["연도"].isin(years)) & (df0["월"].isin(months))]
                total = 0.0
                for (_, _), g in sub.groupby(["연도", "월"], sort=False):
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
                col_curr_label: vals_curr,
                "전월누적": vals_prev,
                "당월": vals_mon,
                col_currsum_label: vals_ytd,
            }, index=pd.Index(index_labels, name="구분"))

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


            th = "border:1px solid black; padding:6px 10px; text-align:center; font-size:14px; font-weight:600;"
            td_l = "border:1px solid black; padding:5px 10px; text-align:left;   font-size:14px; font-weight:400;"
            td_r = "border:1px solid black; padding:5px 10px; text-align:right;  font-size:14px; font-weight:400;"
            td_l_b = "border:1px solid black; padding:5px 10px; text-align:left;   font-size:14px; font-weight:700;"
            td_r_b = "border:1px solid black; padding:5px 10px; text-align:right;  font-size:14px; font-weight:700;"

            html = f"""
        <table style="border-collapse:collapse; width:100%; font-family:'Noto Sans KR', sans-serif;">
          <thead>
            <tr>
              <th style="{th}">구분</th>
              <th style="{th}">{col_prev2_label}</th>
              <th style="{th}">{col_prev1_label}</th>
              <th style="{th}">{col_curr_label}</th>
              <th style="{th}">전월누적</th>
              <th style="{th}">당월</th>
              <th style="{th}">{col_currsum_label}</th>
            </tr>
          </thead>
          <tbody>
        """
            for label in index_labels:
                is_bold = label in bold_rows
                _l = td_l_b if is_bold else td_l
                _r = td_r_b if is_bold else td_r

                row = base.loc[label]
                html += "    <tr>\n"
                html += f'      <td style="{_l}">{label}</td>\n'
                for col in [col_prev2_label, col_prev1_label, col_curr_label, "전월누적", "당월", col_currsum_label]:
                    val = fmt_num(row[col])
                    html += f'      <td style="{_r}">{val}</td>\n'
                html += "    </tr>\n"

            html += "  </tbody>\n</table>"
            st.markdown(html, unsafe_allow_html=True)
            display_memo('f_12', year, month)

        except Exception as e:
            st.error(f"현금흐름표 (별도) 생성 중 오류: {e}")

        st.divider()

        st.markdown("<h4>8) 재무상태표 (별도)</h4>", unsafe_allow_html=True)
        st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 백만원]</div>", unsafe_allow_html=True)

        try:
            file_name = st.secrets["sheets"]["f_3"]
            raw = pd.read_csv(file_name, dtype=str)

            import importlib

            importlib.invalidate_caches()
            importlib.reload(modules)

            item_order = [
                '현금및현금성자산', '매출채권', '재고자산', '유형자산', '기타', '자산총계',
                '매입채무', '차입금', '기타', '부채총계',
                '자본금', '이익잉여금', '기타', '자본총계', '부채 및 자본 총계'
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

            th = "border:1px solid black; padding:8px 12px; text-align:center; font-size:14px; font-weight:600;"
            td_l = "border:1px solid black; padding:6px 12px; text-align:left;   font-size:14px; font-weight:400;"
            td_r = "border:1px solid black; padding:6px 12px; text-align:right;  font-size:14px; font-weight:400;"
            td_l_b = "border:1px solid black; padding:6px 12px; text-align:left;   font-size:14px; font-weight:700;"
            td_r_b = "border:1px solid black; padding:6px 12px; text-align:right;  font-size:14px; font-weight:700;"

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
                is_bold = label in bold_rows
                _l = td_l_b if is_bold else td_l
                _r = td_r_b if is_bold else td_r

                try:
                    row = base.loc[label]
                    v_yend = fmt_cell(row.get(prev_year_col, ""))
                    v_prev = fmt_cell(row.get(prev_month_col, ""))
                    v_curr = fmt_cell(row.get(curr_month_col, ""))
                    v_diff = fmt_cell(row.get(diff_col, ""))
                except:
                    v_yend, v_prev, v_curr, v_diff = "", "", "", ""

                html += f"""    <tr>
              <td style="{_l}">{label}</td>
              <td style="{_r}">{v_yend}</td>
              <td style="{_r}">{v_prev}</td>
              <td style="{_r}">{v_curr}</td>
              <td style="{_r}">{v_diff}</td>
            </tr>
        """
            html += "  </tbody>\n</table>"
            st.markdown(html, unsafe_allow_html=True)
            display_memo('f_3', year_int, used_m)

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

                th = "border:1px solid black; padding:8px 12px; text-align:center; font-size:14px; font-weight:600;"
                td_c = "border:1px solid black; padding:6px 12px; text-align:center; font-size:14px; vertical-align:middle;"
                td_l = "border:1px solid black; padding:6px 12px; text-align:left;   font-size:14px;"
                td_r = "border:1px solid black; padding:6px 12px; text-align:right;  font-size:14px;"

                rows_info = [
                    ("매출채권 ⓐ", "매출채권"),
                    ("재고자산 ⓑ", "재고자산"),
                    ("매입채무 ⓒ", "매임채무"),
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


                th = "border:1px solid black; padding:8px 12px; text-align:center; font-size:14px; font-weight:600;"
                td_c = "border:1px solid black; padding:6px 12px; text-align:center; font-size:14px; vertical-align:middle;"
                td_l = "border:1px solid black; padding:6px 12px; text-align:left;   font-size:14px;"
                td_r = "border:1px solid black; padding:6px 12px; text-align:right;  font-size:14px;"

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
                display_memo('f_16', year, month)

            except Exception as e:
                st.error(f"수익 표 생성 중 오류: {e}")

        # ─ 가로 스크롤 래퍼 닫기 ─
        st.markdown("</div></div>", unsafe_allow_html=True)


# =========================
# 연간사업계획






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
                return f"<span style='color:#d32f2f'>-{s}%</span>" if neg else f"{s}%"
            except Exception:
                return ""

        def fmt_pct(x):
            return fmt_signed(x, 0)

        def fmt_number(x, decimals=0):
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

        def to_numeric(s):
            return pd.to_numeric(s, errors="coerce")

        # ─ 데이터 준비
        disp = base.copy()
        disp.index.name = "구분"
        disp = disp.reset_index()

        cols = list(disp.columns)
        c = {k: i for i, k in enumerate(cols)}

        label_candidates = [col for col in cols if isinstance(col, str)]
        label_col = '구분' if '구분' in cols else (label_candidates[0] if label_candidates else cols[0])

        # tuple 컬럼만 추출 (문자열 컬럼 완전 제외)
        tuple_cols = [col for col in cols if isinstance(col, tuple) and len(col) >= 2 and col[0] in ["사업 계획(연간)", "사업 계획(누적)", "실적(누적)", "실적-계획", "달성률(%)"]]

        # ─ 본문 데이터 처리
        body = disp.copy()

        # 1) 단위 연산
        def round_then_strip(v, round_place, strip_factor):
            if pd.isna(v):
                return np.nan
            r = np.round(float(v), round_place)
            return int(r // strip_factor)

        disp_values = body.copy()

        for col in tuple_cols:
            metric = str(col[1]).strip()
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
                disp_values[col] = s.apply(lambda v: round_then_strip(v, -3, 1000))
            elif metric == "판매량":
                s = to_numeric(disp_values[col])
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

        # 3) 포맷(음수 빨간색)
        body = disp_values.copy()
        for col in tuple_cols:
            metric = str(col[1]).strip()
            grp = col[0]
            if grp == "달성률(%)":
                # 달성률은 % 붙이기
                body[col] = body[col].apply(lambda x: fmt_pct(x))
            elif metric in ("판매량", "단가", "매출액"):
                body[col] = body[col].apply(lambda x: fmt_number(x, 0))

        # ─ 그룹별 컬럼 수 계산
        groups = ["사업 계획(연간)", "사업 계획(누적)", "실적(누적)", "실적-계획", "달성률(%)"]
        group_cols = {}
        for grp in groups:
            group_cols[grp] = [col for col in tuple_cols if col[0] == grp]

        # ─ HTML 테이블 생성
        th_style     = "border:1px solid black; background:white; padding:5px 8px; text-align:center; font-weight:700;"
        th_sub_style = "border:1px solid black; background:white; padding:5px 8px; text-align:center; font-weight:600; border-bottom:2px solid black;"
        th_left      = "border:1px solid black; background:white; padding:5px 8px; text-align:left; font-weight:700;"

        # 헤더 1행 (그룹명 colspan 병합)
        header_row1 = f"<th style='{th_left}'>구분</th>"
        for grp in groups:
            span = len(group_cols[grp])
            if span > 0:
                header_row1 += f"<th colspan='{span}' style='{th_style}'>{grp}</th>"

        # 헤더 2행 (세부 컬럼명)
        header_row2 = f"<th style='{th_sub_style}'></th>"
        for grp in groups:
            for col in group_cols[grp]:
                header_row2 += f"<th style='{th_sub_style}'>{col[1]}</th>"

        # 본문 행
        thick_rows_labels = ['국내 계', '중국 계', '태국 계']

        body_html = ""
        for _, row in body.iterrows():
            label = str(row.get(label_col, ''))
            is_thick = label.strip() in thick_rows_labels
            border_b = '2px solid black' if is_thick else '1px solid black'
            fw = '700' if is_thick else '400'

            td_style      = f"border:1px solid black; border-bottom:{border_b}; padding:5px 8px; text-align:right; font-weight:{fw};"
            td_left_style = f"border:1px solid black; border-bottom:{border_b}; padding:5px 8px; text-align:left; font-weight:{fw}; white-space:nowrap;"

            body_html += "<tr>"
            body_html += f"<td style='{td_left_style}'>{label}</td>"
            for col in tuple_cols:
                val = row.get(col, '')
                val = '' if pd.isna(val) else str(val)
                body_html += f"<td style='{td_style}'>{val}</td>"
            body_html += "</tr>"

        # 최종 HTML 렌더링
        html = f"""
        <div style='overflow-x:auto'>
        <table style='border-collapse:collapse; width:100%; font-size:13px; font-family:"Noto Sans KR",sans-serif;'>
            <thead>
                <tr>{header_row1}</tr>
                <tr>{header_row2}</tr>
            </thead>
            <tbody>
                {body_html}
            </tbody>
        </table>
        </div>
        """
        st.markdown(html, unsafe_allow_html=True)
        display_memo('f_17', year, month)

    except Exception as e:
        st.error(f"판매계획 및 실적 표 생성 중 오류: {e}")

st.markdown("""
<style>.footer { bottom: 0; left: 0; right: 0; padding: 8px; text-align: center; font-size: 13px; color: #666666;}</style>
<div class="footer">ⓒ 2025 SeAH Special Steel Corp. All rights reserved.</div>
""", unsafe_allow_html=True)
