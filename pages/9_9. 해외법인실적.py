import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from auth import require_login
import warnings
import modules
import io
import re
from itertools import groupby

warnings.filterwarnings('ignore')
st.set_page_config(layout="wide", initial_sidebar_state="expanded")
require_login()

# =========================
# 공통 테이블 렌더 (인덱스 숨김 + 중복 컬럼 안전)
# =========================

import re, io, pandas as pd
from urllib.request import urlopen, Request


def rowspan_like_for_index(blocks, level=2, header_rows=1):
    """
    멀티인덱스(행) 열에서, 연속된 행들을 '한 칸처럼' 보이게 하는 CSS 스타일을 만들어줍니다.
    """
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


def create_indented_html(s):
    """문자열의 앞 공백을 기반으로 들여쓰기된 HTML <p> 태그를 생성합니다."""
    content = s.lstrip(' ')
    num_spaces = len(s) - len(content)
    indent_level = num_spaces // 2
    return f'<p class="indent-{indent_level}">{content}</p>'


# 🟢 [동기화] 성공한 코드 규격과 완전히 일치하는 표준 display_memo 함수 정의
def display_memo(memo_file_key, year, month, memo_column='메모', css_class="memo-body"):
    """메모 파일 키와 년/월을 받아 해당 메모를 화면에 표시합니다.
       memo_column: 사용할 메모 컬럼명 (기본값: '메모', 남통은 '메모1', 태국은 '메모2')
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
        memo_text = df_filtered.iloc[0][memo_column]

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


def with_inline_header_row(df: pd.DataFrame,
                           index_names=('', '', '구분'),
                           index_values=('', '', '구분')) -> pd.DataFrame:
    """
    멀티인덱스(행) 위에 '같은 행 높이'로 컬럼명을 보여주기 위해
    본문 첫 행에 '헤더용 가짜 행'을 삽입한다.
    """
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
        new_cols.append(c_str if seen[c_str] == 1 else f"{c_str}.{seen[c_str] - 1}")
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

st.markdown(f"## {year}년 {month}월 해외법인실적")

st.markdown("""
<style>
table, td, th {
    font-size: 15px !important;
    font-family: 'Noto Sans KR', sans-serif !important;
}
</style>
""", unsafe_allow_html=True)

t1, t2, t3, t4, t5, t6, t7, t8 = st.tabs(
    ['손익요약', '현금흐름표', '재무상태표', '판매구성', '전월대비 손익차이', '재고자산 현황', '채권현황', '인원현황'])

with t1:
    col_l, col_r = st.columns([6, 4], gap="large")

    with col_l:
        st.markdown("<h4> 1) 손익요약</h4>", unsafe_allow_html=True)
        st.markdown(
            "<div style='text-align:right; font-size:13px; color:#666;'>"
            "[단위: 톤, 백만원, %]</div>",
            unsafe_allow_html=True
        )

        try:
            file_name = st.secrets["sheets"]["f_61"]
            raw = pd.read_csv(file_name, dtype=str)

            year = int(st.session_state["year"])
            month = int(st.session_state["month"])

            body = modules.create_abroad_profit_month_block_table(
                df_raw=raw,
                year=year,
                month=month
            )


            # ====== 포맷 함수 ======
            def fmt_amt(x):
                if pd.isna(x):
                    return ""
                try:
                    v = float(x)
                except Exception:
                    return str(x)
                v_rounded = int(round(v))
                if v_rounded < 0:
                    return f"-{abs(v_rounded):,}"
                return f"{v_rounded:,}"


            def fmt_pct(x):
                if pd.isna(x):
                    return ""
                try:
                    v = float(x)
                except Exception:
                    return str(x)
                if v < 0:
                    return f"-{abs(v):.1f}"
                return f"{v:.1f}"


            disp = body.copy()
            assert set(["대분류", "구분"]).issubset(disp.columns)

            num_cols = [c for c in disp.columns if c not in ["대분류", "구분"]]
            pct_mask = disp["대분류"].astype(str).str.contains("%")

            for c in num_cols:
                disp[c] = pd.to_numeric(disp[c], errors="coerce")
                disp.loc[~pct_mask, c] = disp.loc[~pct_mask, c].apply(fmt_amt)
                disp.loc[pct_mask, c] = disp.loc[pct_mask, c].apply(fmt_pct)

            disp["구분"] = disp["대분류"] + " " + disp["구분"]
            disp = disp.drop(columns=["대분류"])

            cols = disp.columns.tolist()
            c_idx = {c: i for i, c in enumerate(cols)}

            pm = month - 1 if month > 1 else 12
            yy = str(year)[-2:]

            col_prev = f"{pm}월실적"
            col_m_pln = f"{month}월계획"
            col_m_act = f"{month}월실적"
            col_m_gap = f"{month}월계획비"
            col_m_mom = f"{month}월전월비"
            col_acc_p = f"'{yy}년누적계획"
            col_acc_a = f"'{yy}년누적실적"
            col_acc_g = f"'{yy}년누적계획비"

            hdr = [""] * len(cols)
            hdr[c_idx["구분"]] = "구분"

            if col_prev in c_idx:
                hdr[c_idx[col_prev]] = f"{pm}월 실적"
            for c, lab in [
                (col_m_pln, f"{month}월 계획"),
                (col_m_act, f"{month}월 실적"),
                (col_m_gap, f"{month}월 계획비"),
                (col_m_mom, f"{month}월 전월비"),
            ]:
                if c in c_idx:
                    hdr[c_idx[c]] = lab

            acc_label = f"'{yy}년 누적"
            for c, lab in [
                (col_acc_p, f"{acc_label} 계획"),
                (col_acc_a, f"{acc_label} 실적"),
                (col_acc_g, f"{acc_label} 계획비"),
            ]:
                if c in c_idx:
                    hdr[c_idx[c]] = lab

            hdr_df = pd.DataFrame([hdr], columns=cols)
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
                 'props': [('text-align', 'left'), ('white-space', 'nowrap'), ('font-weight', '400'),
                           ('min-width', '120px')]},
                {'selector': 'tbody tr:nth-child(1) td',
                 'props': [('text-align', 'center'), ('font-weight', '700'), ('border-top', '1px solid #aaa'),
                           ('white-space', 'pre')]},
                {'selector': 'tbody tr:last-child td', 'props': [('border-bottom', '1px solid #aaa')]},
            ]


            def style_negative(val):
                s = str(val).strip()
                if s.startswith("-") and s != "-":
                    return "color: red; font-weight: 700;"
                return ""


            styled = (
                disp_vis.style
                .set_table_styles(styles)
                .map(style_negative)
                .hide(axis='index')
            )
            html_table = styled.to_html(escape=False)

            custom_css = """
            <style>
            table {
                width: 100%;
                border-collapse: collapse;
                font-family: 'Noto Sans KR', sans-serif;
                font-size: 17px;
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

            st.markdown(
                f"<div style='width: 100%; max-width: 100%; overflow-x: auto; display: block;'>{custom_css}{html_table}</div>",
                unsafe_allow_html=True
            )
            st.caption("(환율 : 월별 평균 환율)")

        except Exception as e:
            st.error(f"손익요약 생성 중 오류: {e}")

    with col_r:
        st.markdown("<h4 style='color:transparent'> 1) 손익요약</h4>", unsafe_allow_html=True)
        st.markdown("<div style='color:transparent; font-size:15px;'>[단위: 톤, 백만원, %]</div>", unsafe_allow_html=True)
        display_memo('f_61', year, month)

    st.divider()

with t2:
    col_l, col_r = st.columns([6, 4], gap="large")

    with col_l:
        st.markdown("<h4> 1) 현금흐름표_ 중국</h4>", unsafe_allow_html=True)
        st.markdown("<div style='text-align:right; font-size:13px; color:#666;'>[단위: 백만원]</div>",
                    unsafe_allow_html=True)

        try:
            file_name = st.secrets["sheets"]["f_62_63_64"]
            raw = pd.read_csv(file_name, dtype=str)


            def _to_num(s: pd.Series) -> pd.Series:
                s = (
                    s.fillna("")
                    .astype(str)
                    .str.replace(",", "", regex=False)
                    .str.strip()
                )
                v = pd.to_numeric(s, errors="coerce")
                return v.fillna(0.0)


            def _clean_cf_namtong(df_raw: pd.DataFrame) -> pd.DataFrame:
                df = df_raw.copy()
                need = {"구분1", "구분2", "연도", "월", "실적"}
                miss = need - set(df.columns)
                if miss:
                    raise ValueError(f"필수 컬럼 누락: {miss}")

                for c in ["구분1", "구분2", "구분3", "구분4"]:
                    if c in df.columns:
                        df[c] = (
                            df[c]
                            .astype(str)
                            .str.strip()
                            .str.replace(r"\s+", " ", regex=True)
                        )

                df["연도"] = pd.to_numeric(df["연도"], errors="coerce").astype("Int64")
                df["월"] = pd.to_numeric(df["월"], errors="coerce").astype("Int64")
                df["실적"] = _to_num(df["실적"])
                df = df[df["구분1"] == "남통"].copy()
                df["__ord__"] = range(len(df))
                return df


            df0 = _clean_cf_namtong(raw)
            year = int(st.session_state["year"])
            month = int(st.session_state["month"])

            item_order = [
                "영업활동현금흐름", "당기순이익", "조정", "감가상각비", "기타", "자산부채증감",
                "매출채권 감소(증가)", "기타채권 감소(증가)", "재고자산 감소(증가)", "기타자산 감소(증가)",
                "매입채무 증가(감소)", "기타채무 증가(감소)", "퇴직급여부채증가(감소)", "법인세납부", "이자의 수취", "이자의 지급",
                "투자활동현금흐름", "유형자산취득", "무형자산취득", "기타 투자활동", "재무활동현금흐름", "차입금의 증가(감소)",
                "현금성자산의 증감", "기초의 현금", "현금성자산의 환율변동", "기말의 현금",
            ]

            name_counts = {}
            order_with_n = []
            for name in item_order:
                name_counts[name] = name_counts.get(name, 0) + 1
                order_with_n.append((name, name_counts[name]))

            index_labels = [nm for nm, _ in order_with_n]

            col_prev2_label = f"'{str(year - 2)[-2:]}년"
            col_prev1_label = f"'{str(year - 1)[-2:]}년"
            col_prev_label = f"'{str(year)[-2:]}년 {month - 1 if month > 1 else 12}월 누적"
            col_curr_label = f"'{str(year)[-2:]}년 {month}월"
            col_currsum_label = f"'{str(year)[-2:]}년 {month}월 누적"

            sel_year = df0[(df0["구분2"].isin(item_order))]

            if sel_year.empty:
                base = pd.DataFrame(
                    {
                        col_prev2_label: [np.nan] * len(index_labels),
                        col_prev1_label: [np.nan] * len(index_labels),
                        col_prev_label: [np.nan] * len(index_labels),
                        col_curr_label: [np.nan] * len(index_labels),
                        col_currsum_label: [np.nan] * len(index_labels),
                    },
                    index=pd.Index(index_labels, name="구분"),
                )
            else:
                # ====================================================
                # 정확한 수식
                # ====================================================

                def _sum_item_year(name: str, y: int) -> float:
                    """연도 y의 1월~12월 전체 합산 ('24년, '25년용)"""
                    sub = df0[(df0["연도"] == y) & (df0["구분2"] == name)]
                    return float(sub["실적"].sum())


                def _block_year(y: int):
                    """연도 y의 모든 항목 1월~12월 합산"""
                    return [_sum_item_year(nm, y) for nm in index_labels]


                def _sum_item_month(name: str, y: int, m: int) -> float:
                    """연도 y, 월 m의 데이터 (그 월만)"""
                    sub = df0[(df0["연도"] == y) & (df0["월"] == m) & (df0["구분2"] == name)]
                    return float(sub["실적"].sum())


                def _block_month(y: int, m: int):
                    """연도 y, 월 m의 모든 항목 데이터 (그 월만)"""
                    return [_sum_item_month(nm, y, m) for nm in index_labels]


                def _sum_item_cum(name: str, y: int, m: int) -> float:
                    """연도 y의 1월~m월 누적"""
                    sub = df0[(df0["연도"] == y) & (df0["월"] <= m) & (df0["구분2"] == name)]
                    return float(sub["실적"].sum())


                def _block_cum(y: int, m: int):
                    """연도 y의 1월~m월 누적 (모든 항목)"""
                    return [_sum_item_cum(nm, y, m) for nm in index_labels]


                vals_prev2 = _block_year(year - 2)  # '24년: 2024년 1월~12월 합산
                vals_prev1 = _block_year(year - 1)  # '25년: 2025년 1월~12월 합산
                vals_prev = _block_cum(year, month - 1)  # 전월까지 누적 (1월~(month-1)월)
                vals_curr = _block_month(year, month)  # 당월 (month월만)
                vals_ytd = _block_cum(year, month)  # 당월누적 (1월~month월)

                base = pd.DataFrame(
                    {
                        col_prev2_label: vals_prev2,
                        col_prev1_label: vals_prev1,
                        col_prev_label: vals_prev,
                        col_curr_label: vals_curr,
                        col_currsum_label: vals_ytd,
                    },
                    index=pd.Index(index_labels, name="구분"),
                    dtype=float,
                )


                def _row(label: str) -> pd.Series:
                    return base.loc[label].astype(float) if label in base.index else pd.Series(0.0,
                                                                                               index=base.columns,
                                                                                               dtype=float)


                base.loc["조정"] = _row("감가상각비") + _row("기타")
                base.loc["자산부채증감"] = (_row("매출채권 감소(증가)") + _row("기타채권 감소(증가)") + _row("기타자산 감소(증가)") + _row(
                    "재고자산 감소(증가)") + _row("매입채무 증가(감소)") + _row("기타채무 증가(감소)") + _row("퇴직급여부채증가(감소)"))
                base.loc["영업활동현금흐름"] = (
                        _row("당기순이익") + _row("조정") + _row("자산부채증감") + _row("법인세납부") + _row("이자의 수취") + _row(
                    "이자의 지급"))
                base.loc["투자활동현금흐름"] = (_row("유형자산취득") + _row("무형자산취득") + _row("기타 투자활동"))
                base.loc["재무활동현금흐름"] = _row("차입금의 증가(감소)")
                base.loc["현금성자산의 증감"] = (_row("영업활동현금흐름") + _row("투자활동현금흐름") + _row("재무활동현금흐름"))


            def fmt_cell(x):
                if pd.isna(x) or x == "":
                    return ""
                try:
                    v = float(x)
                except Exception:
                    return str(x)
                return f"-{abs(int(round(v))):,}" if v < 0 else f"{int(round(v)):,}"


            disp = base.copy()
            for c in disp.columns:
                disp[c] = disp[c].apply(fmt_cell)
            disp = disp.reset_index()

            cols = disp.columns.tolist()
            c_idx = {c: i for i, c in enumerate(cols)}

            hdr = [''] * len(cols)
            hdr[c_idx['구분']] = '구분'
            hdr[c_idx[col_prev2_label]] = col_prev2_label
            hdr[c_idx[col_prev1_label]] = col_prev1_label
            hdr[c_idx[col_prev_label]] = col_prev_label
            hdr[c_idx[col_curr_label]] = col_curr_label
            hdr[c_idx[col_currsum_label]] = col_currsum_label

            hdr_df = pd.DataFrame([hdr], columns=cols)
            disp_vis = pd.concat([hdr_df, disp], ignore_index=True)


            def apply_cf_indent(name):
                clean = str(name).strip()
                lv0 = ["영업활동현금흐름", "투자활동현금흐름", "재무활동현금흐름", "현금성자산의 증감", "기초의 현금", "현금성자산의 환율변동", "기말의 현금"]
                lv1 = ["당기순이익", "조정", "자산부채증감", "법인세납부", "이자의 수취", "이자의 지급", "유형자산취득", "유형자산처분", "무형자산취득",
                       "기타 투자활동", "차입금의 증가(감소)"]
                lv2 = ["감가상각비", "대손상각비", "법인세비용", "기타", "매출채권 감소(증가)", "기타채권 감소(증가)", "재고자산 감소(증가)", "기타자산 감소(증가)",
                       "매입채무 증가(감소)", "기타채무 증가(감소)", "기타부채 증가(감소)", "퇴직급여부채증가(감소)"]
                lv = 2 if clean in lv2 else (1 if clean in lv1 else 0)
                return f'<span style="padding-left:{lv * 16}px">{name}</span>' if lv > 0 else clean


            for idx in disp_vis.index[1:]:
                disp_vis.loc[idx, "구분"] = apply_cf_indent(str(disp_vis.loc[idx, "구분"]).strip())

            # 💡 [중국법인 스타일 수정] 컬럼명 행인 첫 번째 tr td에 'text-align': 'center !important' 추가
            styles = [
                {'selector': 'thead', 'props': [('display', 'none')]},
                {'selector': 'tbody td',
                 'props': [('border', '1px solid #aaa'), ('padding', '8px 16px'), ('font-size', '15px')]},
                {'selector': 'tbody tr:nth-child(1) td',
                 'props': [('text-align', 'center !important'), ('padding', '8px 16px'), ('font-weight', '700'),
                           ('white-space', 'nowrap'), ('border-top', '1px solid #aaa'),
                           ('border-bottom', '1px solid #aaa')]},
                {'selector': 'tbody tr td:nth-child(1)',
                 'props': [('text-align', 'left'), ('white-space', 'nowrap'), ('padding-left', '8px'),
                           ('min-width', '200px')]},
                {'selector': 'tbody tr td:nth-child(n+2)',
                 'props': [('text-align', 'right'), ('padding', '8px 16px'), ('white-space', 'nowrap')]},
            ]


            def red_if_negative(val):
                s = str(val).strip()
                return "color: red;" if s.startswith("-") and s != "-" else ""


            styled = (
                disp_vis.style
                .set_table_styles(styles)
                .map(red_if_negative)
                .hide(axis='index')
            )
            html_table = styled.to_html(escape=False)

            st.markdown(
                f"<div style='width: 100%; max-width: 100%; overflow-x: auto; display: block;'>{html_table}</div>",
                unsafe_allow_html=True
            )

        except Exception as e:
            st.error(f"중국법인 현금흐름표 생성 중 오류: {e}")

    with col_r:
        st.markdown("<h4 style='color:transparent'> 1) 현금흐름 중국법인</h4>", unsafe_allow_html=True)
        st.markdown("<div style='color:transparent; font-size:13px;'>[단위: 백만원]</div>", unsafe_allow_html=True)
        display_memo('f_62', year, month)

    st.divider()

    # (위쪽 중국법인 및 구분선 생략...)

    # (위쪽 중국법인 및 구분선 생략...)

    col_l2, col_r2 = st.columns([6, 4], gap="large")

    with col_l2:
        st.markdown("<h4> 2) 현금흐름표_태국</h4>", unsafe_allow_html=True)
        st.markdown("<div style='text-align:right; font-size:13px; color:#666;'>[단위: 백만원]</div>",
                    unsafe_allow_html=True)

        try:
            file_name = st.secrets["sheets"]["f_62_63_64"]
            raw = pd.read_csv(file_name, dtype=str)


            def _to_num(s: pd.Series) -> pd.Series:
                s = (
                    s.fillna("")
                    .astype(str)
                    .str.replace(",", "", regex=False)
                    .str.strip()
                )
                v = pd.to_numeric(s, errors="coerce")
                return v.fillna(0.0)


            def _clean_cf_thailand(df_raw: pd.DataFrame) -> pd.DataFrame:
                df = df_raw.copy()
                need = {"구분1", "구분2", "연도", "월", "실적"}
                miss = need - set(df.columns)
                if miss:
                    raise ValueError(f"필수 컬럼 누락: {miss}")

                for c in ["구분1", "구분2", "구분3", "구분4"]:
                    if c in df.columns:
                        df[c] = (
                            df[c]
                            .astype(str)
                            .str.strip()
                            .str.replace(r"\s+", " ", regex=True)
                        )

                df["연도"] = pd.to_numeric(df["연도"], errors="coerce").astype("Int64")
                df["월"] = pd.to_numeric(df["월"], errors="coerce").astype("Int64")
                df["실적"] = _to_num(df["실적"])
                df = df[df["구분1"] == "태국"].copy()
                df["__ord__"] = range(len(df))
                return df


            df0 = _clean_cf_thailand(raw)
            year = int(st.session_state["year"])
            month = int(st.session_state["month"])

            item_order = [
                "영업활동현금흐름", "당기순이익", "조정", "감가상각비", "대손상각비", "법인세비용", "기타", "자산부채증감",
                "매출채권 감소(증가)", "기타채권 감소(증가)", "재고자산 감소(증가)", "기타자산 감소(증가)",
                "매입채무 증가(감소)", "기타채무 증가(감소)", "기타부채 증가(감소)", "퇴직급여부채증가(감소)",
                "법인세납부", "이자의 수취", "이자의 지급", "투자활동현금흐름", "유형자산취득", "유형자산처분",
                "무형자산취득", "기타 투자활동", "재무활동현금흐름", "차입금의 증가(감소)", "현금성자산의 증감",
                "기초의 현금", "현금성자산의 환율변동", "기말의 현금",
            ]

            name_counts = {}
            order_with_n = []
            for name in item_order:
                name_counts[name] = name_counts.get(name, 0) + 1
                order_with_n.append((name, name_counts[name]))

            index_labels = [nm for nm, _ in order_with_n]

            col_prev2_label = f"'{str(year - 2)[-2:]}년"
            col_prev1_label = f"'{str(year - 1)[-2:]}년"
            col_prev_label = f"'{str(year)[-2:]}년 {month - 1 if month > 1 else 12}월 누적"
            col_curr_label = f"'{str(year)[-2:]}년 {month}월"
            col_currsum_label = f"'{str(year)[-2:]}년 {month}월 누적"

            sel_year = df0[(df0["구분2"].isin(item_order))]

            if sel_year.empty:
                base = pd.DataFrame(
                    {
                        col_prev2_label: [np.nan] * len(index_labels),
                        col_prev1_label: [np.nan] * len(index_labels),
                        col_prev_label: [np.nan] * len(index_labels),
                        col_curr_label: [np.nan] * len(index_labels),
                        col_currsum_label: [np.nan] * len(index_labels),
                    },
                    index=pd.Index(index_labels, name="구분"),
                )
            else:
                # ====================================================
                # 정확한 수식
                # ====================================================

                def _sum_item_year(name: str, y: int) -> float:
                    """연도 y의 1월~12월 전체 합산 ('24년, '25년용)"""
                    sub = df0[(df0["연도"] == y) & (df0["구분2"] == name)]
                    return float(sub["실적"].sum())


                def _block_year(y: int):
                    """연도 y의 모든 항목 1월~12월 합산"""
                    return [_sum_item_year(nm, y) for nm in index_labels]


                def _sum_item_month(name: str, y: int, m: int) -> float:
                    """연도 y, 월 m의 데이터 (그 월만)"""
                    sub = df0[(df0["연도"] == y) & (df0["월"] == m) & (df0["구분2"] == name)]
                    return float(sub["실적"].sum())


                def _block_month(y: int, m: int):
                    """연도 y, 월 m의 모든 항목 데이터 (그 월만)"""
                    return [_sum_item_month(nm, y, m) for nm in index_labels]


                def _sum_item_cum(name: str, y: int, m: int) -> float:
                    # 💡 [오류 수정 위치] 기존 df0["연度"] 오타를 df0["연도"]로 정상 복구했습니다.
                    """연도 y의 1월~m월 누적"""
                    sub = df0[(df0["연도"] == y) & (df0["월"] <= m) & (df0["구분2"] == name)]
                    return float(sub["실적"].sum())


                def _block_cum(y: int, m: int):
                    """연도 y의 1월~m월 누적 (모든 항목)"""
                    return [_sum_item_cum(nm, y, m) for nm in index_labels]


                vals_prev2 = _block_year(year - 2)  # '24년: 2024년 1월~12월 합산
                vals_prev1 = _block_year(year - 1)  # '25년: 2025년 1월~12월 합산
                vals_prev = _block_cum(year, month - 1)  # 전월까지 누적 (1월~(month-1)월)
                vals_curr = _block_month(year, month)  # 당월 (month월만)
                vals_ytd = _block_cum(year, month)  # 당월누적 (1월~month월)

                base = pd.DataFrame(
                    {
                        col_prev2_label: vals_prev2,
                        col_prev1_label: vals_prev1,
                        col_prev_label: vals_prev,
                        col_curr_label: vals_curr,
                        col_currsum_label: vals_ytd,
                    },
                    index=pd.Index(index_labels, name="구분"),
                    dtype=float,
                )


                def _row(label: str) -> pd.Series:
                    return base.loc[label].astype(float) if label in base.index else pd.Series(0.0,
                                                                                               index=base.columns,
                                                                                               dtype=float)


                base.loc["조정"] = (_row("감가상각비") + _row("대손상각비") + _row("법인세비용") + _row("기타"))
                base.loc["자산부채증감"] = (_row("매출채권 감소(증가)") + _row("기타채권 감소(증가)") + _row("재고자산 감소(증가)") + _row(
                    "기타자산 감소(증가)") + _row("매입채무 증가(감소)") + _row("기타채무 증가(감소)") + _row("기타부채 증가(감소)") + _row(
                    "퇴직급여부채증가(감소)"))
                base.loc["영업활동현금흐름"] = (
                        _row("당기순이익") + _row("조정") + _row("자산부채증감") + _row("법인세납부") + _row("이자의 수취") + _row(
                    "이자의 지급"))
                base.loc["투자활동현금흐름"] = (_row("유형자산취득") + _row("유형자산처분") + _row("무형자산취득") + _row("기타 투자활동"))
                base.loc["재무활동현금흐름"] = _row("차입금의 증가(감소)")
                base.loc["현금성자산의 증감"] = (_row("영업활동현금흐름") + _row("투자활동현금흐름") + _row("재무활동현금흐름"))


            def fmt_cell(x):
                if pd.isna(x) or x == "":
                    return ""
                try:
                    v = float(x)
                except Exception:
                    return str(x)
                return f"-{abs(int(round(v))):,}" if v < 0 else f"{int(round(v)):,}"


            disp = base.copy()
            for c in disp.columns:
                disp[c] = disp[c].apply(fmt_cell)
            disp = disp.reset_index()

            cols = disp.columns.tolist()
            c_idx = {c: i for i, c in enumerate(cols)}

            hdr = [''] * len(cols)
            hdr[c_idx['구분']] = '구분'
            hdr[c_idx[col_prev2_label]] = col_prev2_label
            hdr[c_idx[col_prev1_label]] = col_prev1_label
            hdr[c_idx[col_prev_label]] = col_prev_label
            hdr[c_idx[col_curr_label]] = col_curr_label
            hdr[c_idx[col_currsum_label]] = col_currsum_label

            hdr_df = pd.DataFrame([hdr], columns=cols)
            disp_vis = pd.concat([hdr_df, disp], ignore_index=True)


            def apply_cf_indent(name):
                clean = str(name).strip()
                lv0 = ["영업활동현금흐름", "투자활동현금흐름", "재무활동현금흐름", "현금성자산의 증감", "기초의 현금", "현금성자산의 환율변동", "기말의 현금"]
                lv1 = ["당기순이익", "조정", "자산부채증감", "법인세납부", "이자의 수취", "이자의 지급", "유형자산취득", "유형자산처분", "무형자산취득",
                       "기타 투자활동", "차입금의 증가(감소)"]
                lv2 = ["감가상각비", "대손상각비", "법인세비용", "기타", "매출채권 감소(증가)", "기타채권 감소(증가)", "재고자산 감소(증가)", "기타자산 감소(증가)",
                       "매입채무 증가(감소)", "기타채무 증가(감소)", "기타부채 증가(감소)", "퇴직급여부채증가(감소)"]
                lv = 2 if clean in lv2 else (1 if clean in lv1 else 0)
                return f'<span style="padding-left:{lv * 16}px">{name}</span>' if lv > 0 else clean


            for idx in disp_vis.index[1:]:
                disp_vis.loc[idx, "구분"] = apply_cf_indent(str(disp_vis.loc[idx, "구분"]).strip())

            styles = [
                {'selector': 'thead', 'props': [('display', 'none')]},
                {'selector': 'tbody td',
                 'props': [('border', '1px solid #aaa'), ('padding', '8px 16px'), ('font-size', '15px')]},
                {'selector': 'tbody tr:nth-child(1) td',
                 'props': [('text-align', 'center !important'), ('padding', '8px 16px'), ('font-weight', '700'),
                           ('white-space', 'nowrap'), ('border-top', '1px solid #aaa'),
                           ('border-bottom', '1px solid #aaa')]},
                {'selector': 'tbody tr td:nth-child(1)',
                 'props': [('text-align', 'left'), ('white-space', 'nowrap'), ('padding-left', '8px'),
                           ('min-width', '200px')]},
                {'selector': 'tbody tr td:nth-child(n+2)',
                 'props': [('text-align', 'right'), ('padding', '8px 16px'), ('white-space', 'nowrap')]},
            ]


            def red_if_negative(val):
                s = str(val).strip()
                return "color: red;" if s.startswith("-") and s != "-" else ""


            styled = (
                disp_vis.style
                .set_table_styles(styles)
                .map(red_if_negative)
                .hide(axis='index')
            )
            html_table = styled.to_html(escape=False)

            st.markdown(
                f"<div style='width: 100%; max-width: 100%; overflow-x: auto; display: block;'>{html_table}</div>",
                unsafe_allow_html=True
            )

        except Exception as e:
            st.error(f"태국법인 현금흐름표 생성 중 오류: {e}")

    with col_r2:
        st.markdown("<h4 style='color:transparent'> 2) 현금흐름 태국법인</h4>", unsafe_allow_html=True)
        st.markdown("<div style='color:transparent; font-size:13px;'>[단위: 백만원]</div>", unsafe_allow_html=True)
        display_memo('f_64', year, month)

    st.divider()

##재무상태표
with t3:
    col_l, col_r = st.columns([7, 3], gap="large")

    with col_l:
        st.markdown("<h4> 1) 재무상태표_중국</h4>", unsafe_allow_html=True)
        st.markdown("<div style='text-align:right; font-size:13px; color:#666;'>[단위: 백만원]</div>", unsafe_allow_html=True)

        try:
            file_name = st.secrets["sheets"]["f_65_66_67"]
            raw = pd.read_csv(file_name, dtype=str)

            import importlib

            importlib.invalidate_caches()
            importlib.reload(modules)

            item_order = [
                '현금및현금성자산', '매출채권', '재고자산', '유형자산', '기타자산', '자산총계',
                '매입채무', '차입금', '기타부채', '부채총계',
                '자본금', '기타(외화환산 포함)', '자본총계', '부채 및 자본 총계'
            ]

            base_namtong = modules.create_bs_from_company(
                year=int(st.session_state['year']),
                month=int(st.session_state['month']),
                data=raw,
                item_order=item_order,
                company_name='남통',
            )

            calc = base_namtong.copy()

            sum_map = {
                '자산총계': ['현금및현금성자산', '매출채권', '재고자산', '유형자산', '기타자산'],
                '부채총계': ['매입채무', '차입금', '기타부채'],
                '자본총계': ['자본금', '기타(외화환산 포함)'],
                '부채 및 자본 총계': ['부채총계', '자본총계'],
            }

            for target, sources in sum_map.items():
                missing = [s for s in sources if s not in calc.index]
                if missing:
                    raise ValueError(f"합계 계산에 필요한 항목 누락: {missing}")
                calc.loc[target] = calc.loc[sources].sum()

            # ====================================================
            # 전월비 컬럼 추가
            # ====================================================
            year_int = int(st.session_state['year'])
            yy_curr = f"{year_int % 100:02d}"
            col_prev = f"'{yy_curr} 전월"
            col_curr = "당월"
            col_diff = "전월비"

            if col_prev in calc.columns and col_curr in calc.columns:
                calc[col_diff] = calc[col_curr] - calc[col_prev]

            calc.attrs = base_namtong.attrs


            def fmt_cell(x):
                if pd.isna(x):
                    return ""
                try:
                    v = float(x)
                except Exception:
                    return str(x)
                if v < 0:
                    return f"-{abs(int(round(v))):,}"
                return f"{int(round(v)):,}"


            disp = calc.copy()
            for c in disp.columns:
                disp[c] = disp[c].apply(fmt_cell)

            disp = disp.reset_index()
            cols = disp.columns.tolist()
            c_idx = {c: i for i, c in enumerate(cols)}


            def _safe_int(x, default=None):
                try:
                    return int(x)
                except Exception:
                    return default


            used_m = _safe_int(base_namtong.attrs.get('used_month'))
            prev_m = _safe_int(base_namtong.attrs.get('prev_month'))

            if used_m is None:
                used_m = _safe_int(st.session_state.get('month'), 12)
            if prev_m is None:
                prev_m = used_m - 1 if used_m and used_m > 1 else 12

            year_int = int(st.session_state['year'])
            yy_curr = f"{year_int % 100:02d}"
            yy_m1 = f"{(year_int - 1) % 100:02d}"
            yy_m2 = f"{(year_int - 2) % 100:02d}"
            yy_m3 = f"{(year_int - 3) % 100:02d}"

            col_yend_m3 = f"'{yy_m3}년말"
            col_yend_m2 = f"'{yy_m2}년말"
            col_yend_m1 = f"'{yy_m1}년말"
            col_prev = f"'{yy_curr} 전월"
            col_curr = "당월"
            col_diff = "전월비"

            hdr = [''] * len(cols)
            hdr[c_idx['구분']] = '구분'

            if col_yend_m3 in c_idx:
                hdr[c_idx[col_yend_m3]] = col_yend_m3
            if col_yend_m2 in c_idx:
                hdr[c_idx[col_yend_m2]] = col_yend_m2
            if col_yend_m1 in c_idx:
                hdr[c_idx[col_yend_m1]] = col_yend_m1
            if col_prev in c_idx:
                hdr[c_idx[col_prev]] = col_prev
            if col_curr in c_idx:
                hdr[c_idx[col_curr]] = col_curr
            if col_diff in c_idx:
                hdr[c_idx[col_diff]] = col_diff

            hdr_df = pd.DataFrame([hdr], columns=cols)
            disp_vis = pd.concat([hdr_df, disp], ignore_index=True)


            def apply_bs_indent(name):
                clean = str(name).strip()
                lv0 = ['자산총계', '부채총계', '자본총계', '부채 및 자본 총계']
                if clean in lv0:
                    return clean
                return f'<span style="padding-left:16px">{name}</span>'


            for idx in disp_vis.index[1:]:
                val = str(disp_vis.loc[idx, "구분"]).strip()
                disp_vis.loc[idx, "구분"] = apply_bs_indent(val)

            # 💡 [중국법인 스타일 수정] 첫 행(컬럼명 헤더) 정렬 속성에 !important 추가
            styles = [
                {'selector': 'thead', 'props': [('display', 'none')]},
                {'selector': 'tbody td',
                 'props': [('border', '1px solid #aaa'), ('padding', '8px 16px'), ('font-size', '15px')]},
                {'selector': 'tbody tr:nth-child(1) td',
                 'props': [('text-align', 'center !important'), ('padding', '8px 16px'), ('font-weight', '700'),
                           ('white-space', 'nowrap'), ('border-top', '1px solid #aaa'),
                           ('border-bottom', '1px solid #aaa')]},
                {'selector': 'tbody tr td:nth-child(1)',
                 'props': [('text-align', 'left'), ('white-space', 'nowrap'), ('padding-left', '8px'),
                           ('min-width', '150px')]},
                {'selector': 'tbody tr td:nth-child(n+2)',
                 'props': [('text-align', 'right'), ('padding', '8px 16px'), ('white-space', 'nowrap')]},
            ]


            def red_if_negative(val):
                s = str(val).strip()
                return "color: red;" if s.startswith("-") and s != "-" else ""


            styled = (
                disp_vis.style
                .set_table_styles(styles)
                .map(red_if_negative)
                .hide(axis='index')
            )
            html_table = styled.to_html(escape=False)

            st.markdown(
                f"<div style='width: 100%; max-width: 100%; overflow-x: auto; display: block;'>{html_table}</div>",
                unsafe_allow_html=True
            )

        except Exception as e:
            st.error(f"중국법인 재무상태표 생성 중 오류: {e}")

    with col_r:
        st.markdown("<h4 style='color:transparent'> 1) 재무상태표 중국법인</h4>", unsafe_allow_html=True)
        st.markdown("<div style='color:transparent; font-size:13px;'>[단위: 백만원]</div>", unsafe_allow_html=True)
        display_memo('f_65', year, month)

    st.divider()

    col_l2, col_r2 = st.columns([7, 3], gap="large")

    with col_l2:
        st.markdown("<h4> 2) 재무상태표_태국</h4>", unsafe_allow_html=True)
        st.markdown("<div style='text-align:right; font-size:13px; color:#666;'>[단위: 백만원]</div>", unsafe_allow_html=True)

        try:
            file_name = st.secrets["sheets"]["f_65_66_67"]
            raw = pd.read_csv(file_name, dtype=str)

            item_order = [
                '현금및현금성자산', '매출채권', '재고자산', '유형자산', '기타자산', '자산총계',
                '매입채무', '차입금', '기타부채', '부채총계',
                '자본금', '기타(외화환산 포함)', '자본총계', '부채 및 자본 총계'
            ]

            base_thailand = modules.create_bs_from_company(
                year=int(st.session_state['year']),
                month=int(st.session_state['month']),
                data=raw,
                item_order=item_order,
                company_name='태국',
            )

            calc = base_thailand.copy()

            sum_map = {
                '자산총계': ['현금및현금성자산', '매출채권', '재고자산', '유형자산', '기타자산'],
                '부채총계': ['매입채무', '차입금', '기타부채'],
                '자본총계': ['자본금', '기타(외화환산 포함)'],
                '부채 및 자본 총계': ['부채총계', '자본총계'],
            }

            for target, sources in sum_map.items():
                missing = [s for s in sources if s not in calc.index]
                if missing:
                    raise ValueError(f"합계 계산에 필요한 항목 누락: {missing}")
                calc.loc[target] = calc.loc[sources].sum()

            # ====================================================
            # 전월비 컬럼 추가
            # ====================================================
            year_int = int(st.session_state['year'])
            yy_curr = f"{year_int % 100:02d}"
            col_prev = f"'{yy_curr} 전월"
            col_curr = "당월"
            col_diff = "전월비"

            if col_prev in calc.columns and col_curr in calc.columns:
                calc[col_diff] = calc[col_curr] - calc[col_prev]

            calc.attrs = base_thailand.attrs


            def fmt_cell(x):
                if pd.isna(x):
                    return ""
                try:
                    v = float(x)
                except Exception:
                    return str(x)
                if v < 0:
                    return f"-{abs(int(round(v))):,}"
                return f"{int(round(v)):,}"


            disp = calc.copy()
            for c in disp.columns:
                disp[c] = disp[c].apply(fmt_cell)

            disp = disp.reset_index()
            cols = disp.columns.tolist()
            c_idx = {c: i for i, c in enumerate(cols)}


            def _safe_int(x, default=None):
                try:
                    return int(x)
                except Exception:
                    return default


            used_m = _safe_int(base_thailand.attrs.get('used_month'))
            prev_m = _safe_int(base_thailand.attrs.get('prev_month'))

            if used_m is None:
                used_m = _safe_int(st.session_state.get('month'), 12)
            if prev_m is None:
                prev_m = used_m - 1 if used_m and used_m > 1 else 12

            year_int = int(st.session_state['year'])
            yy_curr = f"{year_int % 100:02d}"
            yy_m1 = f"{(year_int - 1) % 100:02d}"
            yy_m2 = f"{(year_int - 2) % 100:02d}"
            yy_m3 = f"{(year_int - 3) % 100:02d}"

            col_yend_m3 = f"'{yy_m3}년말"
            col_yend_m2 = f"'{yy_m2}년말"
            col_yend_m1 = f"'{yy_m1}년말"
            col_prev = f"'{yy_curr} 전월"
            col_curr = "당월"
            col_diff = "전월비"

            hdr = [''] * len(cols)
            hdr[c_idx['구분']] = '구분'

            if col_yend_m3 in c_idx:
                hdr[c_idx[col_yend_m3]] = col_yend_m3
            if col_yend_m2 in c_idx:
                hdr[c_idx[col_yend_m2]] = col_yend_m2
            if col_yend_m1 in c_idx:
                hdr[c_idx[col_yend_m1]] = col_yend_m1
            if col_prev in c_idx:
                hdr[c_idx[col_prev]] = col_prev
            if col_curr in c_idx:
                hdr[c_idx[col_curr]] = col_curr
            if col_diff in c_idx:
                hdr[c_idx[col_diff]] = col_diff

            hdr_df = pd.DataFrame([hdr], columns=cols)
            disp_vis = pd.concat([hdr_df, disp], ignore_index=True)


            def apply_bs_indent(name):
                clean = str(name).strip()
                lv0 = ['자산총계', '부채총계', '자본총계', '부채 및 자본 총계']
                if clean in lv0:
                    return clean
                return f'<span style="padding-left:16px">{name}</span>'


            for idx in disp_vis.index[1:]:
                val = str(disp_vis.loc[idx, "구분"]).strip()
                disp_vis.loc[idx, "구분"] = apply_bs_indent(val)

            # 💡 [태국법인 스타일 수정] 첫 행(컬럼명 헤더) 정렬 속성에 !important 추가
            styles = [
                {'selector': 'thead', 'props': [('display', 'none')]},
                {'selector': 'tbody td',
                 'props': [('border', '1px solid #aaa'), ('padding', '8px 16px'), ('font-size', '15px')]},
                {'selector': 'tbody tr:nth-child(1) td',
                 'props': [('text-align', 'center !important'), ('padding', '8px 16px'), ('font-weight', '700'),
                           ('white-space', 'nowrap'), ('border-top', '1px solid #aaa'),
                           ('border-bottom', '1px solid #aaa')]},
                {'selector': 'tbody tr td:nth-child(1)',
                 'props': [('text-align', 'left'), ('white-space', 'nowrap'), ('padding-left', '8px'),
                           ('min-width', '150px')]},
                {'selector': 'tbody tr td:nth-child(n+2)',
                 'props': [('text-align', 'right'), ('padding', '8px 16px'), ('white-space', 'nowrap')]},
            ]


            def red_if_negative(val):
                s = str(val).strip()
                return "color: red;" if s.startswith("-") and s != "-" else ""


            styled = (
                disp_vis.style
                .set_table_styles(styles)
                .map(red_if_negative)
                .hide(axis='index')
            )
            html_table = styled.to_html(escape=False)

            st.markdown(
                f"<div style='width: 100%; max-width: 100%; overflow-x: auto; display: block;'>{html_table}</div>",
                unsafe_allow_html=True
            )

        except Exception as e:
            st.error(f"태국법인 재무상태표 생성 중 오류: {e}")

    with col_r2:
        st.markdown("<h4 style='color:transparent'> 2) 재무상태표 태국법인</h4>", unsafe_allow_html=True)
        st.markdown("<div style='color:transparent; font-size:13px;'>[단위: 백만원]</div>", unsafe_allow_html=True)
        display_memo('f_67', year, month)

    st.divider()

with t4:
    col_l, col_r = st.columns([6, 4], gap="large")

    with col_l:
        st.markdown("<h4> 1) 등급별 판매현황</h4>", unsafe_allow_html=True)
        st.markdown("<div style='text-align:right; font-size:13px; color:#666;'>[단위: 톤]</div>", unsafe_allow_html=True)

        try:
            file_name = st.secrets["sheets"]["f_68"]
            df_src = pd.read_csv(file_name, dtype=str)

            disp = modules.build_grade_sales_table_68(df_src, year, month)
            body = disp.copy()

            prev_year_labels = [f"{str(y)[-2:]}년" for y in range(year - 3, year)]

            month_pairs = []
            for k in (2, 1, 0):
                y = year
                m = month - k
                while m <= 0:
                    y -= 1
                    m += 12
                month_pairs.append((y, m))

            month_defs = []
            for y, m in month_pairs:
                col = f"{str(y)[-2:]}년{m}월"
                if col in body.columns:
                    month_defs.append((col, y, m))

            candidate_cols = prev_year_labels + [col for (col, _, _) in month_defs]
            NUM_COLS = [c for c in candidate_cols if c in body.columns]

            yy = str(year)[-2:]
            diff_cols = [c for c in body.columns if "전월비" in c and "%" not in c]
            pct_cols = [c for c in body.columns if c.endswith("전월비%")]

            hdr = {col: "" for col in body.columns}

            if "구분2" in hdr:
                hdr["구분2"] = "구분"

            for y_col in prev_year_labels:
                if y_col in hdr:
                    hdr[y_col] = f"'{y_col}"

            for col, y, m in month_defs:
                yy_col = str(y)[-2:]
                hdr[col] = f"'{yy_col}년{m}월"

            for c in diff_cols:
                if c in hdr:
                    hdr[c] = f"'{yy}.{month}월 전월대비 증감"
            for c in pct_cols:
                if c in hdr:
                    hdr[c] = f"'{yy}.{month}월 전월대비 증감률 %"

            hdr_df = pd.DataFrame([hdr])
            body = pd.concat([hdr_df, body], ignore_index=True)


            def fmt_num(x):
                try:
                    v = float(str(x).replace(",", ""))
                    if pd.isna(v):
                        return x
                    return f"{int(round(v)):,}"
                except Exception:
                    return x


            def fmt_pct(x):
                try:
                    v = float(str(x).replace(",", "").replace("%", ""))
                    if pd.isna(v):
                        return x
                    return f"{v:.1f}%"
                except Exception:
                    return x


            for col in NUM_COLS + diff_cols:
                body.iloc[1:, body.columns.get_loc(col)] = (
                    body.iloc[1:, body.columns.get_loc(col)].apply(fmt_num)
                )

            pct_row_mask = body["구분2"].isin(["POSCO %", "%"])
            for col in NUM_COLS + diff_cols:
                body.loc[pct_row_mask, col] = body.loc[pct_row_mask, col].apply(fmt_pct)

            for col in pct_cols:
                body.iloc[1:, body.columns.get_loc(col)] = (
                    body.iloc[1:, body.columns.get_loc(col)].apply(fmt_pct)
                )


            # 💡 [등급별 판매현황 계층표현 들여쓰기 추가]
            def apply_grade_indent(name):
                clean = str(name).strip()
                lv1 = ["정품", "B급"]
                lv2 = ["POSCO", "세아특수강", "로컬", "기타", "POSCO %", "%"]

                if clean in lv1:
                    return f'<span style="padding-left:16px">{name}</span>'
                elif clean in lv2:
                    return f'<span style="padding-left:32px">{name}</span>'
                return clean


            for idx in body.index[1:]:
                val = str(body.loc[idx, "구분2"]).strip()
                body.loc[idx, "구분2"] = apply_grade_indent(val)

            # 💡 [1번 표 수정] 헤더행 역할을 하는 첫 번째 tr td에 center !important 적용
            styles = [
                {"selector": "thead", "props": [("display", "none")]},
                {"selector": "tbody td",
                 "props": [("border", "1px solid #aaa"), ("padding", "8px 16px"), ("font-size", "15px")]},
                {"selector": "tbody tr:nth-child(1) td",
                 "props": [("text-align", "center !important"), ("padding", "8px 16px"), ("font-weight", "700"),
                           ("white-space", "nowrap"), ("border-top", "1px solid #aaa"),
                           ("border-bottom", "1px solid #aaa")]},
                {"selector": "tbody tr td:nth-child(1)",
                 "props": [("text-align", "left"), ("white-space", "nowrap"), ("padding-left", "8px"),
                           ("min-width", "120px")]},
                {"selector": "tbody tr td:nth-child(n+2)",
                 "props": [("text-align", "right"), ("padding", "8px 16px"), ("white-space", "nowrap")]},
                {"selector": "tbody tr:nth-child(9) td, tbody tr:nth-child(17) td", "props": [("font-weight", "700")]},
            ]


            def red_if_negative(val):
                s = str(val).strip()
                return "color: red;" if s.startswith("-") and s != "-" else ""


            styled = (
                body.style
                .set_table_styles(styles)
                .map(red_if_negative)
                .hide(axis='index')
            )
            html_table = styled.to_html(escape=False)

            st.markdown(
                f"<div style='width: 100%; max-width: 100%; overflow-x: auto; display: block;'>{html_table}</div>",
                unsafe_allow_html=True
            )

        except Exception as e:
            st.error(f"등급별 판매현황 표 생성 오류: {e}")

    with col_r:
        st.markdown("<h4 style='color:transparent'> 1) 등급별 판매현황</h4>", unsafe_allow_html=True)
        st.markdown("<div style='color:transparent; font-size:13px;'>[단위: 톤]</div>", unsafe_allow_html=True)
        display_memo('f_68', year, month)

    st.divider()

    col_l2, col_r2 = st.columns([6, 4], gap="large")

    with col_l2:
        st.markdown("<h4> 2) CHQ 열처리 제품 판매현황</h4>", unsafe_allow_html=True)
        st.markdown("<div style='text-align:right; font-size:13px; color:#666;'>[단위: 톤]</div>", unsafe_allow_html=True)

        try:
            file_name = st.secrets["sheets"]["f_69_70_71"]
            df_src = pd.read_csv(file_name, dtype=str)

            disp = modules.build_chq_f69(df_src, year, month)
            body = disp.copy()

            prev_year_labels = [f"{str(y)[-2:]}년" for y in range(year - 3, year)]

            month_pairs = []
            for k in (2, 1, 0):
                y = year
                m = month - k
                while m <= 0:
                    y -= 1
                    m += 12
                month_pairs.append((y, m))

            month_defs = []
            for y, m in month_pairs:
                col = f"{str(y)[-2:]}년{m}월"
                if col in body.columns:
                    month_defs.append((col, y, m))

            candidate_cols = prev_year_labels + [col for (col, _, _) in month_defs]
            NUM_COLS = [c for c in candidate_cols if c in body.columns]

            yy = str(year)[-2:]
            diff_cols = [c for c in body.columns if "전월비" in c and "%" not in c]
            pct_cols = [c for c in body.columns if c.endswith("전월비%")]

            hdr = {col: "" for col in body.columns}

            if "구분2" in hdr:
                hdr["구분2"] = "구분"

            for y_col in prev_year_labels:
                if y_col in hdr:
                    hdr[y_col] = f"'{y_col}"

            for col, y, m in month_defs:
                yy_col = str(y)[-2:]
                hdr[col] = f"'{yy_col}년{m}월"

            for c in diff_cols:
                if c in hdr:
                    hdr[c] = f"'{yy}.{month}월 전월대비 증감"
            for c in pct_cols:
                if c in hdr:
                    hdr[c] = f"'{yy}.{month}월 전월대비 증감률 %"

            hdr_df = pd.DataFrame([hdr])
            body = pd.concat([hdr_df, body], ignore_index=True)

            def fmt_num(x):
                try:
                    v = float(str(x).replace(",", ""))
                    if pd.isna(v):
                        return x
                    return f"{int(round(v)):,}"
                except Exception:
                    return x

            def fmt_pct(x):
                try:
                    v = float(str(x).replace(",", "").replace("%", ""))
                    if pd.isna(v):
                        return x
                    return f"{v:.1f}%"
                except Exception:
                    return x

            for col in NUM_COLS + diff_cols:
                body.iloc[1:, body.columns.get_loc(col)] = (
                    body.iloc[1:, body.columns.get_loc(col)].apply(fmt_num)
                )

            pct_row_mask = body["구분2"] == "%"
            for col in NUM_COLS + diff_cols:
                body.loc[pct_row_mask, col] = body.loc[pct_row_mask, col].apply(fmt_pct)

            for col in pct_cols:
                body.iloc[1:, body.columns.get_loc(col)] = (
                    body.iloc[1:, body.columns.get_loc(col)].apply(fmt_pct)
                )

            # 💡 [2번 표 수정] 헤더행 역할을 하는 첫 번째 tr td에 center !important 적용
            styles = [
                {"selector": "thead", "props": [("display", "none")]},
                {"selector": "tbody td", "props": [("border", "1px solid #aaa"), ("padding", "8px 16px"), ("font-size", "15px")]},
                {"selector": "tbody tr:nth-child(1) td", "props": [("text-align", "center !important"), ("padding", "8px 16px"), ("font-weight", "700"), ("white-space", "nowrap"), ("border-top", "1px solid #aaa"), ("border-bottom", "1px solid #aaa")]},
                {"selector": "tbody tr td:nth-child(1)", "props": [("text-align", "left"), ("white-space", "nowrap"), ("padding-left", "8px"), ("min-width", "120px")]},
                {"selector": "tbody tr td:nth-child(n+2)", "props": [("text-align", "right"), ("padding", "8px 16px"), ("white-space", "nowrap")]},
                {"selector": "tbody tr:nth-child(5) td, tbody tr:nth-child(9) td", "props": [("font-weight", "700")]},
            ]

            def red_if_negative(val):
                s = str(val).strip()
                return "color: red;" if s.startswith("-") and s != "-" else ""

            styled = (
                body.style
                .set_table_styles(styles)
                .map(red_if_negative)
                .hide(axis='index')
            )
            html_table = styled.to_html(escape=False)

            st.markdown(
                f"<div style='width: 100%; max-width: 100%; overflow-x: auto; display: block;'>{html_table}</div>",
                unsafe_allow_html=True
            )

        except Exception as e:
            st.error(f"CHQ 열처리 제품 판매현황 표 생성 오류: {e}")

    with col_r2:
        st.markdown("<h4 style='color:transparent'> 2) CHQ 열처리 제품 판매현황</h4>", unsafe_allow_html=True)
        st.markdown("<div style='color:transparent; font-size:13px;'>[단위: 톤]</div>", unsafe_allow_html=True)
        display_memo('f_69', year, month)

    st.divider()

    col_l3, col_r3 = st.columns([6, 4], gap="large")

    with col_l3:
        st.markdown("<h4> 3) 비가공품 판매현황</h4>", unsafe_allow_html=True)
        st.markdown("<div style='text-align:right; font-size:13px; color:#666;'>[단위: 톤]</div>", unsafe_allow_html=True)

        try:
            file_name = st.secrets["sheets"]["f_69_70_71"]
            df_src = pd.read_csv(file_name, dtype=str)

            disp = modules.build_f70(df_src, year, month)
            body = disp.copy()

            prev_year_labels = [f"{str(y)[-2:]}년" for y in range(year - 3, year)]

            month_pairs = []
            for k in (2, 1, 0):
                y = year
                m = month - k
                while m <= 0:
                    y -= 1
                    m += 12
                month_pairs.append((y, m))

            month_defs = []
            for y, m in month_pairs:
                col = f"{str(y)[-2:]}년{m}월"
                if col in body.columns:
                    month_defs.append((col, y, m))

            candidate_cols = prev_year_labels + [col for (col, _, _) in month_defs]
            NUM_COLS = [c for c in candidate_cols if c in body.columns]

            yy = str(year)[-2:]
            diff_cols = [c for c in body.columns if "전월비" in c and "%" not in c]
            pct_cols = [c for c in body.columns if c.endswith("전월비%")]

            hdr = {col: "" for col in body.columns}

            if "구분2" in hdr:
                hdr["구분2"] = "구분"

            for y_col in prev_year_labels:
                if y_col in hdr:
                    hdr[y_col] = f"'{y_col}"

            for col, y, m in month_defs:
                yy_col = str(y)[-2:]
                hdr[col] = f"'{yy_col}년{m}월"

            for c in diff_cols:
                if c in hdr:
                    hdr[c] = f"'{yy}.{month}월 전월대비 증감"
            for c in pct_cols:
                if c in hdr:
                    hdr[c] = f"'{yy}.{month}월 전월대비 증감률 %"

            hdr_df = pd.DataFrame([hdr])
            body = pd.concat([hdr_df, body], ignore_index=True)

            def fmt_num(x):
                try:
                    v = float(str(x).replace(",", ""))
                    if pd.isna(v):
                        return x
                    return f"{int(round(v)):,}"
                except Exception:
                    return x

            def fmt_pct(x):
                try:
                    v = float(str(x).replace(",", "").replace("%", ""))
                    if pd.isna(v):
                        return x
                    return f"{v:.1f}%"
                except Exception:
                    return x

            for col in NUM_COLS + diff_cols:
                body.iloc[1:, body.columns.get_loc(col)] = (
                    body.iloc[1:, body.columns.get_loc(col)].apply(fmt_num)
                )

            pct_row_mask = body["구분2"] == "%"
            for col in NUM_COLS + diff_cols:
                body.loc[pct_row_mask, col] = body.loc[pct_row_mask, col].apply(fmt_pct)

            for col in pct_cols:
                body.iloc[1:, body.columns.get_loc(col)] = (
                    body.iloc[1:, body.columns.get_loc(col)].apply(fmt_pct)
                )

            # 💡 [3번 표 수정] 헤더행 역할을 하는 첫 번째 tr td에 center !important 적용
            styles = [
                {"selector": "thead", "props": [("display", "none")]},
                {"selector": "tbody td", "props": [("border", "1px solid #aaa"), ("padding", "8px 16px"), ("font-size", "15px")]},
                {"selector": "tbody tr:nth-child(1) td", "props": [("text-align", "center !important"), ("padding", "8px 16px"), ("font-weight", "700"), ("white-space", "nowrap"), ("border-top", "1px solid #aaa"), ("border-bottom", "1px solid #aaa")]},
                {"selector": "tbody tr td:nth-child(1)", "props": [("text-align", "left"), ("white-space", "nowrap"), ("padding-left", "8px"), ("min-width", "120px")]},
                {"selector": "tbody tr td:nth-child(n+2)", "props": [("text-align", "right"), ("padding", "8px 16px"), ("white-space", "nowrap")]},
                {"selector": "tbody tr:nth-child(5) td, tbody tr:nth-child(9) td", "props": [("font-weight", "700")]},
            ]

            def red_if_negative(val):
                s = str(val).strip()
                return "color: red;" if s.startswith("-") and s != "-" else ""

            styled = (
                body.style
                .set_table_styles(styles)
                .map(red_if_negative)
                .hide(axis='index')
            )
            html_table = styled.to_html(escape=False)

            st.markdown(
                f"<div style='width: 100%; max-width: 100%; overflow-x: auto; display: block;'>{html_table}</div>",
                unsafe_allow_html=True
            )

        except Exception as e:
            st.error(f"비가공품 판매현황 표 생성 오류: {e}")

    with col_r3:
        st.markdown("<h4 style='color:transparent'> 3) 비가공품 판매현황</h4>", unsafe_allow_html=True)
        st.markdown("<div style='color:transparent; font-size:13px;'>[단위: 톤]</div>", unsafe_allow_html=True)
        display_memo('f_70', year, month)

    st.divider()

    col_l4, col_r4 = st.columns([6, 4], gap="large")

    with col_l4:
        st.markdown("<h4> 4) 제품/임가공 판매현황</h4>", unsafe_allow_html=True)
        st.markdown("<div style='text-align:right; font-size:13px; color:#666;'>[단위: 톤]</div>", unsafe_allow_html=True)

        try:
            file_name = st.secrets["sheets"]["f_69_70_71"]
            df_src = pd.read_csv(file_name, dtype=str)

            disp = modules.build_f71(df_src, year, month)
            body = disp.copy()

            prev_year_labels = [f"{str(y)[-2:]}년" for y in range(year - 3, year)]

            month_pairs = []
            for k in (2, 1, 0):
                y = year
                m = month - k
                while m <= 0:
                    y -= 1
                    m += 12
                month_pairs.append((y, m))

            month_defs = []
            for y, m in month_pairs:
                col = f"{str(y)[-2:]}년{m}월"
                if col in body.columns:
                    month_defs.append((col, y, m))

            candidate_cols = prev_year_labels + [col for (col, _, _) in month_defs]
            NUM_COLS = [c for c in candidate_cols if c in body.columns]

            yy = str(year)[-2:]
            diff_cols = [c for c in body.columns if "전월비" in c and "%" not in c]
            pct_cols = [c for c in body.columns if c.endswith("전월비%")]

            hdr = {col: "" for col in body.columns}

            if "구분2" in hdr:
                hdr["구분2"] = "구분"

            for y_col in prev_year_labels:
                if y_col in hdr:
                    hdr[y_col] = f"'{y_col}"

            for col, y, m in month_defs:
                yy_col = str(y)[-2:]
                hdr[col] = f"'{yy_col}년{m}월"

            for c in diff_cols:
                if c in hdr:
                    hdr[c] = f"'{yy}.{month}월 전월대비 증감"
            for c in pct_cols:
                if c in hdr:
                    hdr[c] = f"'{yy}.{month}월 전월대비 증감률 %"

            hdr_df = pd.DataFrame([hdr])
            body = pd.concat([hdr_df, body], ignore_index=True)

            def fmt_num(x):
                try:
                    v = float(str(x).replace(",", ""))
                    if pd.isna(v):
                        return x
                    return f"{int(round(v)):,}"
                except Exception:
                    return x

            def fmt_pct(x):
                try:
                    v = float(str(x).replace(",", "").replace("%", ""))
                    if pd.isna(v):
                        return x
                    return f"{v:.1f}%"
                except Exception:
                    return x

            for col in NUM_COLS + diff_cols:
                body.iloc[1:, body.columns.get_loc(col)] = (
                    body.iloc[1:, body.columns.get_loc(col)].apply(fmt_num)
                )

            pct_row_mask = body["구분2"] == "%"
            for col in NUM_COLS + diff_cols:
                body.loc[pct_row_mask, col] = body.loc[pct_row_mask, col].apply(fmt_pct)

            for col in pct_cols:
                body.iloc[1:, body.columns.get_loc(col)] = (
                    body.iloc[1:, body.columns.get_loc(col)].apply(fmt_pct)
                )

            # 💡 [4번 표 수정] 헤더행 역할을 하는 첫 번째 tr td에 center !important 적용
            styles = [
                {"selector": "thead", "props": [("display", "none")]},
                {"selector": "tbody td", "props": [("border", "1px solid #aaa"), ("padding", "8px 16px"), ("font-size", "15px")]},
                {"selector": "tbody tr:nth-child(1) td", "props": [("text-align", "center !important"), ("padding", "8px 16px"), ("font-weight", "700"), ("white-space", "nowrap"), ("border-top", "1px solid #aaa"), ("border-bottom", "1px solid #aaa")]},
                {"selector": "tbody tr td:nth-child(1)", "props": [("text-align", "left"), ("white-space", "nowrap"), ("padding-left", "8px"), ("min-width", "120px")]},
                {"selector": "tbody tr td:nth-child(n+2)", "props": [("text-align", "right"), ("padding", "8px 16px"), ("white-space", "nowrap")]},
                {"selector": "tbody tr:nth-child(5) td, tbody tr:nth-child(9) td", "props": [("font-weight", "700")]},
            ]

            def red_if_negative(val):
                s = str(val).strip()
                return "color: red;" if s.startswith("-") and s != "-" else ""

            styled = (
                body.style
                .set_table_styles(styles)
                .map(red_if_negative)
                .hide(axis='index')
            )
            html_table = styled.to_html(escape=False)

            st.markdown(
                f"<div style='width: 100%; max-width: 100%; overflow-x: auto; display: block;'>{html_table}</div>",
                unsafe_allow_html=True
            )

        except Exception as e:
            st.error(f"제품/임가공 판매현황 표 생성 오류: {e}")

    with col_r4:
        st.markdown("<h4 style='color:transparent'> 4) 제품/임가공 판매현황</h4>", unsafe_allow_html=True)
        st.markdown("<div style='color:transparent; font-size:13px;'>[단위: 톤]</div>", unsafe_allow_html=True)
        display_memo('f_71', year, month)

    st.divider()

# Tab 5: 전월대비 손익차이
with t5:
    st.markdown("<h4>1) 전월대비 손익차이</h4>", unsafe_allow_html=True)

    year = int(st.session_state['year'])
    month = int(st.session_state['month'])

    try:
        file_name = st.secrets["sheets"]["f_72"]
        df_src = pd.read_csv(file_name, dtype=str)

        # 스타일 설정
        styles = [
            {"selector": "thead th", "props": [
                ("border", "1px solid #aaa"),
                ("padding", "8px 16px"),
                ("font-size", "15px"),
                ("font-family", "'Noto Sans KR'"),
                ("font-weight", "700"),
                ("text-align", "center"),
                ("background", "#fff"),
            ]},
            {"selector": "tbody td", "props": [
                ("border", "1px solid #aaa"),
                ("padding", "8px 16px"),
                ("font-size", "15px"),
                ("font-family", "'Noto Sans KR'"),
                ("font-weight", "400"),
            ]},
            {"selector": "tbody tr td:first-child", "props": [
                ("text-align", "left"),
                ("white-space", "nowrap"),
                ("padding-left", "8px"),
                ("min-width", "120px"),
            ]},
            {"selector": "tbody tr td:nth-child(n+2)", "props": [
                ("text-align", "right"),
                ("padding", "8px 16px"),
                ("white-space", "nowrap"),
            ]},
        ]


        def red_if_negative(val):
            s = str(val).strip()
            return "color: red;" if s.startswith("-") and s != "-" else ""


        def fmt_num(x):
            try:
                v = int(float(x))
                return f"{v:,}"
            except Exception:
                return x


        # 모든 가능한 구분2 값 (고정 행 목록)
        all_category2 = ['매출이익', '영업이익차이', '원가', '판매', '판매비와관리비']
        # 항상 보여줄 컬럼 순서
        col_order = ['영업', '제조', '구매', '기타']

        # ===== 남통 표 =====
        col_l1, col_r1 = st.columns([6, 4], gap="large")

        with col_l1:
            st.markdown("<h5>남통</h5>", unsafe_allow_html=True)
            st.markdown("<div style='text-align:right; font-size:13px; color:#666;'>[단위: 백만원]</div>",
                        unsafe_allow_html=True)

            try:
                # 남통 데이터 필터링: 구분1='남통' + 연도/월 필터링
                nam_data = df_src[(df_src['구분1'] == '남통') &
                                  (df_src['연도'] == str(year)) &
                                  (df_src['월'] == str(month))].copy()
                nam_data['실적'] = pd.to_numeric(nam_data['실적'], errors='coerce').fillna(0).astype(int)

                # 구분2(행) x 구분3(열) 피벗
                body = nam_data.pivot_table(
                    index='구분2',
                    columns='구분3',
                    values='실적',
                    aggfunc='first'
                ).fillna(0).astype(int)

                # 컬럼 순서 강제 - 데이터가 없어도 컬럼 유지
                body = body.reindex(columns=col_order, fill_value=0)

                # 소계 컬럼 추가 (각 행의 합계)
                body.insert(0, '소계', body.sum(axis=1).astype(int))

                # 인덱스를 '구분' 컬럼으로 리셋
                body = body.reset_index()
                body.rename(columns={'구분2': '구분'}, inplace=True)

                # 모든 고정 행이 있는지 확인하고, 없는 행 추가
                existing_rows = set(body['구분'].tolist())
                missing_rows = [row for row in all_category2 if row not in existing_rows]

                for missing_row in missing_rows:
                    new_row = {'구분': missing_row}
                    for col in body.columns:
                        if col != '구분':
                            new_row[col] = 0
                    body = pd.concat([body, pd.DataFrame([new_row])], ignore_index=True)

                # 원래 순서대로 정렬
                body['구분'] = pd.Categorical(body['구분'], categories=all_category2, ordered=True)
                body = body.sort_values('구분').reset_index(drop=True)

                # 숫자 변환
                for col in body.columns:
                    if col != '구분':
                        body[col] = body[col].apply(fmt_num)

                # 스타일 적용
                styled = (
                    body.style
                    .set_table_styles(styles)
                    .map(red_if_negative)
                    .hide(axis='index')
                )
                html_table = styled.to_html(escape=False)

                st.markdown(
                    f"<div style='width: 100%; max-width: 100%; overflow-x: auto; display: block;'>{html_table}</div>",
                    unsafe_allow_html=True
                )

            except Exception as e:
                st.error(f"남통 표 생성 오류: {e}")

        with col_r1:
            st.markdown("<h5 style='color:transparent'>남통</h5>", unsafe_allow_html=True)
            st.markdown("<div style='color:transparent; font-size:13px;'>[단위: 백만원]</div>", unsafe_allow_html=True)
            display_memo('f_72', year, month, memo_column='메모1')

        st.divider()

        # ===== 태국 표 =====
        col_l2, col_r2 = st.columns([6, 4], gap="large")

        with col_l2:
            st.markdown("<h5>태국</h5>", unsafe_allow_html=True)
            st.markdown("<div style='text-align:right; font-size:13px; color:#666;'>[단위: 백만원]</div>",
                        unsafe_allow_html=True)

            try:
                # 태국 데이터 필터링: 구분1='태국' + 연도/월 필터링
                tag_data = df_src[(df_src['구분1'] == '태국') &
                                  (df_src['연도'] == str(year)) &
                                  (df_src['월'] == str(month))].copy()
                tag_data['실적'] = pd.to_numeric(tag_data['실적'], errors='coerce').fillna(0).astype(int)

                # 구분2(행) x 구분3(열) 피벗
                body = tag_data.pivot_table(
                    index='구분2',
                    columns='구분3',
                    values='실적',
                    aggfunc='first'
                ).fillna(0).astype(int)

                # 컬럼 순서 강제 - 데이터가 없어도 컬럼 유지
                body = body.reindex(columns=col_order, fill_value=0)

                # 소계 컬럼 추가 (각 행의 합계)
                body.insert(0, '소계', body.sum(axis=1).astype(int))

                # 인덱스를 '구분' 컬럼으로 리셋
                body = body.reset_index()
                body.rename(columns={'구분2': '구분'}, inplace=True)

                # 모든 고정 행이 있는지 확인하고, 없는 행 추가
                existing_rows = set(body['구분'].tolist())
                missing_rows = [row for row in all_category2 if row not in existing_rows]

                for missing_row in missing_rows:
                    new_row = {'구분': missing_row}
                    for col in body.columns:
                        if col != '구분':
                            new_row[col] = 0
                    body = pd.concat([body, pd.DataFrame([new_row])], ignore_index=True)

                # 원래 순서대로 정렬
                body['구분'] = pd.Categorical(body['구분'], categories=all_category2, ordered=True)
                body = body.sort_values('구분').reset_index(drop=True)

                # 숫자 변환
                for col in body.columns:
                    if col != '구분':
                        body[col] = body[col].apply(fmt_num)

                # 스타일 적용
                styled = (
                    body.style
                    .set_table_styles(styles)
                    .map(red_if_negative)
                    .hide(axis='index')
                )
                html_table = styled.to_html(escape=False)

                st.markdown(
                    f"<div style='width: 100%; max-width: 100%; overflow-x: auto; display: block;'>{html_table}</div>",
                    unsafe_allow_html=True
                )

            except Exception as e:
                st.error(f"태국 표 생성 오류: {e}")

        with col_r2:
            st.markdown("<h5 style='color:transparent'>태국</h5>", unsafe_allow_html=True)
            st.markdown("<div style='color:transparent; font-size:13px;'>[단위: 백만원]</div>", unsafe_allow_html=True)
            display_memo('f_72', year, month, memo_column='메모2')

    except Exception as e:
        st.error(f"전월대비 손익차이 표 생성 오류: {e}")

    st.divider()

with t6:
    # ========== 1) 재고자산 현황 남통법인 ==========
    col_l1, col_r1 = st.columns([6, 4], gap="large")

    with col_l1:
        st.markdown("<h4> 1) 재고자산 현황_중국</h4>", unsafe_allow_html=True)
        st.markdown("<div style='text-align:right; font-size:13px; color:#666;'>[단위: 톤, 백만원, %]</div>", unsafe_allow_html=True)

        try:
            file_name = st.secrets["sheets"]["f_75_76_77"]
            raw = pd.read_csv(file_name, dtype=str)

            inv = modules.create_inv_table_from_company(
                year=int(st.session_state['year']),
                month=int(st.session_state['month']),
                data=raw,
                company_name='남통',
            )

            disp = inv.copy().reset_index()

            def relabel(row):
                b = str(row['구분2']).strip() if pd.notna(row['구분2']) else ''
                s = str(row['구분3']).strip() if pd.notna(row['구분3']) else ''
                if s == '소계':
                    return b if b else '소계'
                if s and s != 'nan':
                    return s
                if b and b != 'nan':
                    return b
                return ''

            disp['구분'] = disp.apply(relabel, axis=1)
            disp = disp[disp['구분'].str.strip() != ''].copy()
            disp = disp.drop(columns=['구분2', '구분3'])
            cols_order = ['구분'] + [c for c in disp.columns if c != '구분']
            disp = disp[cols_order]

            def fmt_amt(x):
                if pd.isna(x):
                    return "0"
                try:
                    v = float(x)
                except Exception:
                    return x
                if v == 0:
                    return "0"
                v_rounded = int(round(v))
                return f"({abs(v_rounded):,})" if v_rounded < 0 else f"{v_rounded:,}"

            def fmt_rate(x):
                if pd.isna(x):
                    return "0%"
                try:
                    v = float(x)
                except Exception:
                    return x
                if v == 0:
                    return ""
                return f"{int(round(v))}%"

            for c in disp.columns:
                if c == '구분':
                    continue
                if c == '증감률':
                    disp[c] = disp[c].apply(fmt_rate)
                else:
                    disp[c] = disp[c].apply(fmt_amt)

            used_m = int(inv.attrs.get('used_month'))
            prev_m = int(inv.attrs.get('prev_month'))
            prev2_m = int(inv.attrs.get('prev2_month'))
            year_int = int(inv.attrs.get('base_year'))
            company = inv.attrs.get('company', '남통')

            yy_m1 = f"{(year_int - 1) % 100:02d}"
            yy_m2 = f"{(year_int - 2) % 100:02d}"
            yy_m3 = f"{(year_int - 3) % 100:02d}"
            yy_m4 = f"{(year_int - 4) % 100:02d}"

            col_yend_m4 = f"'{yy_m4}년말"
            col_yend_m3 = f"'{yy_m3}년말"
            col_yend_m2 = f"'{yy_m2}년말"
            col_yend_m1 = f"'{yy_m1}년말"

            col_m3 = f"{prev2_m}월"
            col_m2 = f"{prev_m}월"
            col_m1 = f"{used_m}월"

            m1_year = year_int
            m2_year = year_int if prev_m <= used_m else year_int - 1
            m3_year = m2_year if prev2_m <= prev_m else m2_year - 1

            cols = disp.columns.tolist()
            c_idx = {c: i for i, c in enumerate(cols)}

            hdr = [''] * len(cols)
            hdr[c_idx['구분']] = f"[{company}]"

            for col_key in [col_yend_m4, col_yend_m3, col_yend_m2, col_yend_m1]:
                if col_key in c_idx:
                    hdr[c_idx[col_key]] = col_key

            hdr[c_idx[col_m3]] = f"'{m3_year % 100:02d}년{prev2_m}월"
            hdr[c_idx[col_m2]] = f"'{m2_year % 100:02d}년{prev_m}월"
            hdr[c_idx[col_m1]] = f"'{m1_year % 100:02d}년{used_m}월 중량"
            hdr[c_idx['증량']] = f"'{m1_year % 100:02d}년{used_m}월 증감"
            hdr[c_idx['증감률']] = f"'{m1_year % 100:02d}년{used_m}월 증감률"

            hdr_df = pd.DataFrame([hdr], columns=cols)
            disp_vis = pd.concat([hdr_df, disp], ignore_index=True)

            styles = [
                {'selector': 'thead', 'props': [('display', 'none')]},
                {'selector': 'tbody td', 'props': [('border', '1px solid #aaa'), ('padding', '8px 16px'), ('font-size', '15px')]},
                {'selector': 'tbody tr:nth-child(1) td', 'props': [('text-align', 'center'), ('padding', '8px 16px'), ('font-weight', '700'), ('white-space', 'nowrap'), ('border-top', '1px solid #aaa'), ('border-bottom', '1px solid #aaa')]},
                {'selector': 'tbody tr:nth-child(n+2) td:nth-child(1)', 'props': [('text-align', 'left'), ('white-space', 'nowrap'), ('padding-left', '8px'), ('min-width', '120px')]},
                {'selector': 'tbody tr:nth-child(n+2) td:nth-child(n+2)', 'props': [('text-align', 'right'), ('padding', '8px 16px'), ('white-space', 'nowrap')]},
                {'selector': 'tbody tr:nth-child(5) td, tbody tr:nth-child(9) td, tbody tr:nth-child(13) td, tbody tr:nth-child(14) td', 'props': [('font-weight', '700')]},
            ]

            def red_if_negative(val):
                s = str(val).strip()
                if s.startswith("(") and s.endswith(")"):
                    return "color: red;"
                return ""

            styled = (
                disp_vis.style
                .set_table_styles(styles)
                .map(red_if_negative)
                .hide(axis='index')
            )
            html_table = styled.to_html(escape=False)

            st.markdown(
                f"<div style='width: 100%; max-width: 100%; overflow-x: auto; display: block;'>{html_table}</div>",
                unsafe_allow_html=True
            )

        except Exception as e:
            st.error(f"재고자산 현황 남통법인 표 생성 중 오류: {e}")

    with col_r1:
        st.markdown("<h4 style='color:transparent'> 1) 재고자산 현황 남통법인</h4>", unsafe_allow_html=True)
        st.markdown("<div style='color:transparent; font-size:13px;'>[단위: 톤, 백만원, %]</div>", unsafe_allow_html=True)
        display_memo('f_75', year, month)

    st.divider()

    # ========== 2) 재고자산 현황 태국법인 ==========
    col_l2, col_r2 = st.columns([6, 4], gap="large")

    with col_l2:
        st.markdown("<h4> 2) 재고자산 현황_태국</h4>", unsafe_allow_html=True)
        st.markdown("<div style='text-align:right; font-size:13px; color:#666;'>[단위: 톤, 백만원, %]</div>", unsafe_allow_html=True)

        try:
            file_name = st.secrets["sheets"]["f_75_76_77"]
            raw = pd.read_csv(file_name, dtype=str)

            inv = modules.create_inv_table_from_company(
                year=int(st.session_state['year']),
                month=int(st.session_state['month']),
                data=raw,
                company_name='태국',
            )

            disp = inv.copy().reset_index()

            def relabel(row):
                b = str(row['구분2']).strip() if pd.notna(row['구분2']) else ''
                s = str(row['구분3']).strip() if pd.notna(row['구분3']) else ''
                if s == '소계':
                    return b if b else '소계'
                if s and s != 'nan':
                    return s
                if b and b != 'nan':
                    return b
                return ''

            disp['구분'] = disp.apply(relabel, axis=1)
            disp = disp[disp['구분'].str.strip() != ''].copy()
            disp = disp.drop(columns=['구분2', '구분3'])
            cols_order = ['구분'] + [c for c in disp.columns if c != '구분']
            disp = disp[cols_order]

            def fmt_amt(x):
                if pd.isna(x):
                    return "0"
                try:
                    v = float(x)
                except Exception:
                    return x
                if v == 0:
                    return "0"
                v_rounded = int(round(v))
                return f"({abs(v_rounded):,})" if v_rounded < 0 else f"{v_rounded:,}"

            def fmt_rate(x):
                if pd.isna(x):
                    return "0%"
                try:
                    v = float(x)
                except Exception:
                    return x
                if v == 0:
                    return ""
                return f"{int(round(v))}%"

            for c in disp.columns:
                if c == '구분':
                    continue
                if c == '증감률':
                    disp[c] = disp[c].apply(fmt_rate)
                else:
                    disp[c] = disp[c].apply(fmt_amt)

            used_m = int(inv.attrs.get('used_month'))
            prev_m = int(inv.attrs.get('prev_month'))
            prev2_m = int(inv.attrs.get('prev2_month'))
            year_int = int(inv.attrs.get('base_year'))
            company = inv.attrs.get('company', '태국')

            yy_m1 = f"{(year_int - 1) % 100:02d}"
            yy_m2 = f"{(year_int - 2) % 100:02d}"
            yy_m3 = f"{(year_int - 3) % 100:02d}"
            yy_m4 = f"{(year_int - 4) % 100:02d}"

            col_yend_m4 = f"'{yy_m4}년말"
            col_yend_m3 = f"'{yy_m3}년말"
            col_yend_m2 = f"'{yy_m2}년말"
            col_yend_m1 = f"'{yy_m1}년말"

            col_m3 = f"{prev2_m}월"
            col_m2 = f"{prev_m}월"
            col_m1 = f"{used_m}월"

            m1_year = year_int
            m2_year = year_int if prev_m <= used_m else year_int - 1
            m3_year = m2_year if prev2_m <= prev_m else m2_year - 1

            cols = disp.columns.tolist()
            c_idx = {c: i for i, c in enumerate(cols)}

            hdr = [''] * len(cols)
            hdr[c_idx['구분']] = f"[{company}]"

            for col_key in [col_yend_m4, col_yend_m3, col_yend_m2, col_yend_m1]:
                if col_key in c_idx:
                    hdr[c_idx[col_key]] = col_key

            hdr[c_idx[col_m3]] = f"'{m3_year % 100:02d}년{prev2_m}월"
            hdr[c_idx[col_m2]] = f"'{m2_year % 100:02d}년{prev_m}월"
            hdr[c_idx[col_m1]] = f"'{m1_year % 100:02d}년{used_m}월 중량"
            hdr[c_idx['증량']] = f"'{m1_year % 100:02d}년{used_m}월 증감"
            hdr[c_idx['증감률']] = f"'{m1_year % 100:02d}년{used_m}월 증감률"

            hdr_df = pd.DataFrame([hdr], columns=cols)
            disp_vis = pd.concat([hdr_df, disp], ignore_index=True)

            styles = [
                {'selector': 'thead', 'props': [('display', 'none')]},
                {'selector': 'tbody td', 'props': [('border', '1px solid #aaa'), ('padding', '8px 16px'), ('font-size', '15px')]},
                {'selector': 'tbody tr:nth-child(1) td', 'props': [('text-align', 'center'), ('padding', '8px 16px'), ('font-weight', '700'), ('white-space', 'nowrap'), ('border-top', '1px solid #aaa'), ('border-bottom', '1px solid #aaa')]},
                {'selector': 'tbody tr:nth-child(n+2) td:nth-child(1)', 'props': [('text-align', 'left'), ('white-space', 'nowrap'), ('padding-left', '8px'), ('min-width', '120px')]},
                {'selector': 'tbody tr:nth-child(n+2) td:nth-child(n+2)', 'props': [('text-align', 'right'), ('padding', '8px 16px'), ('white-space', 'nowrap')]},
                {'selector': 'tbody tr:nth-child(5) td, tbody tr:nth-child(9) td, tbody tr:nth-child(13) td, tbody tr:nth-child(14) td', 'props': [('font-weight', '700')]},
            ]

            def red_if_negative(val):
                s = str(val).strip()
                if s.startswith("(") and s.endswith(")"):
                    return "color: red;"
                return ""

            styled = (
                disp_vis.style
                .set_table_styles(styles)
                .map(red_if_negative)
                .hide(axis='index')
            )
            html_table = styled.to_html(escape=False)

            st.markdown(
                f"<div style='width: 100%; max-width: 100%; overflow-x: auto; display: block;'>{html_table}</div>",
                unsafe_allow_html=True
            )

        except Exception as e:
            st.error(f"재고자산 현황 태국법인 표 생성 중 오류: {e}")

    with col_r2:
        st.markdown("<h4 style='color:transparent'> 2) 재고자산 현황 태국법인</h4>", unsafe_allow_html=True)
        st.markdown("<div style='color:transparent; font-size:13px;'>[단위: 톤, 백만원, %]</div>", unsafe_allow_html=True)
        display_memo('f_76', year, month)

    st.divider()


    # ========== 3) 부적합 및 장기재고 현황 남통법인 ==========
    col_l3, col_r3 = st.columns([6, 4], gap="large")

    with col_l3:
        st.markdown("<h4> 3) 부적합 및 장기재고 현황_중국</h4>", unsafe_allow_html=True)
        st.markdown("<div style='text-align:right; font-size:13px; color:#666;'>[단위: 톤, 백만원, %]</div>", unsafe_allow_html=True)

        try:
            file_name = st.secrets["sheets"]["f_78_79_80"]
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

            inv = modules.create_defect_longinv_table_from_company(
                year=int(st.session_state['year']),
                month=int(st.session_state['month']),
                data=raw,
                company_name='남통',
            )

            disp = inv.copy().reset_index()

            def relabel(row):
                b = str(row['구분2']).strip() if pd.notna(row['구분2']) else ''
                s = str(row['구분3']).strip() if pd.notna(row['구분3']) else ''
                if b and b != 'nan' and (not s or s == 'nan'):
                    return b
                if s and s != 'nan':
                    return s
                return ''

            disp['구분'] = disp.apply(relabel, axis=1)
            disp = disp[disp['구분'].str.strip() != ''].copy()
            disp = disp.drop(columns=['구분2', '구분3'])
            cols_order = ['구분'] + [c for c in disp.columns if c != '구분']
            disp = disp[cols_order]

            def fmt_amt(x):
                if pd.isna(x):
                    return "-"
                try:
                    v = float(x)
                except Exception:
                    return x
                if v == 0:
                    return "-"
                v_rounded = int(round(v))
                return f"({abs(v_rounded):,})" if v_rounded < 0 else f"{v_rounded:,}"

            def fmt_rate(x):
                if pd.isna(x):
                    return "-"
                if isinstance(x, str):
                    if x.strip() in ("", "0", "0.0", "-"):
                        return "-"
                    try:
                        x = float(x)
                    except Exception:
                        return x
                try:
                    v = float(x)
                except Exception:
                    return x
                if v == 0:
                    return "-"
                return f"{v:.1f}%"

            for c in disp.columns:
                if c == '구분':
                    continue
                if c == '증감률':
                    disp[c] = disp[c].apply(fmt_rate)
                else:
                    disp[c] = disp[c].apply(fmt_amt)

            year_int = int(inv.attrs.get('base_year'))
            used_m = int(inv.attrs.get('used_month'))
            prev_m = int(inv.attrs.get('prev_month'))
            prev2_m = int(inv.attrs.get('prev2_month'))
            used_y = int(inv.attrs.get('used_year'))
            company = inv.attrs.get('company', '남통')

            yy_m1 = f"{(year_int - 1) % 100:02d}"
            yy_m2 = f"{(year_int - 2) % 100:02d}"

            col_yend_m2 = f"'{yy_m2}년말"
            col_yend_m1 = f"'{yy_m1}년말"

            col_prev2 = f"{prev2_m}월"
            col_prev = f"{prev_m}월"

            m1_year = used_y
            m2_year = used_y if prev_m <= used_m else used_y - 1
            m3_year = m2_year if prev2_m <= prev_m else m2_year - 1

            cols = disp.columns.tolist()
            c_idx = {c: i for i, c in enumerate(cols)}

            hdr = [''] * len(cols)
            hdr[c_idx['구분']] = f"[{company}]"

            for col_key in [col_yend_m4, col_yend_m3, col_yend_m2, col_yend_m1]:
                if col_key in c_idx:
                    hdr[c_idx[col_key]] = col_key

            hdr[c_idx[col_prev2]] = f"'{m3_year % 100:02d}년{prev2_m}월"
            hdr[c_idx[col_prev]] = f"'{m2_year % 100:02d}년{prev_m}월"

            yy_used = f"{m1_year % 100:02d}"
            hdr[c_idx['발생']] = f"'{yy_used}년{used_m}월 발생"
            hdr[c_idx['소진']] = f"'{yy_used}년{used_m}월 소진"
            hdr[c_idx['기말']] = f"'{yy_used}년{used_m}월 기말"
            hdr[c_idx['증감률']] = f"'{yy_used}년{used_m}월 증감률"

            hdr_df = pd.DataFrame([hdr], columns=cols)
            disp_vis = pd.concat([hdr_df, disp], ignore_index=True)

            styles = [
                {'selector': 'thead', 'props': [('display', 'none')]},
                {'selector': 'tbody td', 'props': [('border', '1px solid #aaa'), ('padding', '8px 16px'), ('font-size', '15px')]},
                {'selector': 'tbody tr:nth-child(1) td', 'props': [('text-align', 'center'), ('padding', '8px 16px'), ('font-weight', '700'), ('white-space', 'nowrap'), ('border-top', '1px solid #aaa'), ('border-bottom', '1px solid #aaa')]},
                {'selector': 'tbody tr:nth-child(n+2) td:nth-child(1)', 'props': [('text-align', 'left'), ('white-space', 'nowrap'), ('padding-left', '8px'), ('min-width', '120px')]},
                {'selector': 'tbody tr:nth-child(n+2) td:nth-child(n+2)', 'props': [('text-align', 'right'), ('padding', '8px 16px'), ('white-space', 'nowrap')]},
                {'selector': 'tbody tr:nth-child(4) td, tbody tr:nth-child(7) td', 'props': [('font-weight', '700')]},
            ]

            def red_if_negative(val):
                s = str(val).strip()
                if s.startswith("(") and s.endswith(")"):
                    return "color: red;"
                return ""

            styled = (
                disp_vis.style
                .set_table_styles(styles)
                .map(red_if_negative)
                .hide(axis='index')
            )
            html_table = styled.to_html(escape=False)

            st.markdown(
                f"<div style='width: 100%; max-width: 100%; overflow-x: auto; display: block;'>{html_table}</div>",
                unsafe_allow_html=True
            )

        except Exception as e:
            st.error(f"부적합 및 장기재고 현황 남통법인 표 생성 중 오류: {e}")

    with col_r3:
        st.markdown("<h4 style='color:transparent'> 3) 부적합 및 장기재고 현황 남통법인</h4>", unsafe_allow_html=True)
        st.markdown("<div style='color:transparent; font-size:13px;'>[단위: 톤, 백만원, %]</div>", unsafe_allow_html=True)
        display_memo('f_78', year, month)

    st.divider()

    # ========== 4) 부적합 및 장기재고 현황 태국법인 ==========
    col_l4, col_r4 = st.columns([6, 4], gap="large")

    with col_l4:
        st.markdown("<h4> 4) 부적합 및 장기재고 현황_태국</h4>", unsafe_allow_html=True)
        st.markdown("<div style='text-align:right; font-size:13px; color:#666;'>[단위: 톤, 백만원, %]</div>", unsafe_allow_html=True)

        try:
            file_name = st.secrets["sheets"]["f_78_79_80"]
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

            inv = modules.create_defect_longinv_table_from_company(
                year=int(st.session_state['year']),
                month=int(st.session_state['month']),
                data=raw,
                company_name='태국',
            )

            disp = inv.copy().reset_index()

            def relabel(row):
                b = str(row['구분2']).strip() if pd.notna(row['구분2']) else ''
                s = str(row['구분3']).strip() if pd.notna(row['구분3']) else ''
                if b and b != 'nan' and (not s or s == 'nan'):
                    return b
                if s and s != 'nan':
                    return s
                return ''

            disp['구분'] = disp.apply(relabel, axis=1)
            disp = disp[disp['구분'].str.strip() != ''].copy()
            disp = disp.drop(columns=['구분2', '구분3'])
            cols_order = ['구분'] + [c for c in disp.columns if c != '구분']
            disp = disp[cols_order]

            def fmt_amt(x):
                if pd.isna(x):
                    return "-"
                try:
                    v = float(x)
                except Exception:
                    return x
                if v == 0:
                    return "-"
                v_rounded = int(round(v))
                return f"({abs(v_rounded):,})" if v_rounded < 0 else f"{v_rounded:,}"

            def fmt_rate(x):
                if pd.isna(x):
                    return "-"
                if isinstance(x, str):
                    if x.strip() in ("", "0", "0.0", "-"):
                        return "-"
                    try:
                        x = float(x)
                    except Exception:
                        return x
                try:
                    v = float(x)
                except Exception:
                    return x
                if v == 0:
                    return "-"
                return f"{v:.1f}%"

            for c in disp.columns:
                if c == '구분':
                    continue
                if c == '증감률':
                    disp[c] = disp[c].apply(fmt_rate)
                else:
                    disp[c] = disp[c].apply(fmt_amt)

            year_int = int(inv.attrs.get('base_year'))
            used_m = int(inv.attrs.get('used_month'))
            prev_m = int(inv.attrs.get('prev_month'))
            prev2_m = int(inv.attrs.get('prev2_month'))
            used_y = int(inv.attrs.get('used_year'))
            company = inv.attrs.get('company', '태국')

            yy_m1 = f"{(year_int - 1) % 100:02d}"
            yy_m2 = f"{(year_int - 2) % 100:02d}"

            col_yend_m2 = f"'{yy_m2}년말"
            col_yend_m1 = f"'{yy_m1}년말"

            col_prev2 = f"{prev2_m}월"
            col_prev = f"{prev_m}월"

            m1_year = used_y
            m2_year = used_y if prev_m <= used_m else used_y - 1
            m3_year = m2_year if prev2_m <= prev_m else m2_year - 1

            cols = disp.columns.tolist()
            c_idx = {c: i for i, c in enumerate(cols)}

            hdr = [''] * len(cols)
            hdr[c_idx['구분']] = f"[{company}]"

            for col_key in [col_yend_m4, col_yend_m3, col_yend_m2, col_yend_m1]:
                if col_key in c_idx:
                    hdr[c_idx[col_key]] = col_key

            hdr[c_idx[col_prev2]] = f"'{m3_year % 100:02d}년{prev2_m}월"
            hdr[c_idx[col_prev]] = f"'{m2_year % 100:02d}년{prev_m}월"

            yy_used = f"{m1_year % 100:02d}"
            hdr[c_idx['발생']] = f"'{yy_used}년{used_m}월 발생"
            hdr[c_idx['소진']] = f"'{yy_used}년{used_m}월 소진"
            hdr[c_idx['기말']] = f"'{yy_used}년{used_m}월 기말"
            hdr[c_idx['증감률']] = f"'{yy_used}년{used_m}월 증감률"

            hdr_df = pd.DataFrame([hdr], columns=cols)
            disp_vis = pd.concat([hdr_df, disp], ignore_index=True)

            styles = [
                {'selector': 'thead', 'props': [('display', 'none')]},
                {'selector': 'tbody td', 'props': [('border', '1px solid #aaa'), ('padding', '8px 16px'), ('font-size', '15px')]},
                {'selector': 'tbody tr:nth-child(1) td', 'props': [('text-align', 'center'), ('padding', '8px 16px'), ('font-weight', '700'), ('white-space', 'nowrap'), ('border-top', '1px solid #aaa'), ('border-bottom', '1px solid #aaa')]},
                {'selector': 'tbody tr:nth-child(n+2) td:nth-child(1)', 'props': [('text-align', 'left'), ('white-space', 'nowrap'), ('padding-left', '8px'), ('min-width', '120px')]},
                {'selector': 'tbody tr:nth-child(n+2) td:nth-child(n+2)', 'props': [('text-align', 'right'), ('padding', '8px 16px'), ('white-space', 'nowrap')]},
                {'selector': 'tbody tr:nth-child(4) td, tbody tr:nth-child(7) td', 'props': [('font-weight', '700')]},
            ]

            def red_if_negative(val):
                s = str(val).strip()
                if s.startswith("(") and s.endswith(")"):
                    return "color: red;"
                return ""

            styled = (
                disp_vis.style
                .set_table_styles(styles)
                .map(red_if_negative)
                .hide(axis='index')
            )
            html_table = styled.to_html(escape=False)

            st.markdown(
                f"<div style='width: 100%; max-width: 100%; overflow-x: auto; display: block;'>{html_table}</div>",
                unsafe_allow_html=True
            )

        except Exception as e:
            st.error(f"부적합 및 장기재고 현황 태국법인 표 생성 중 오류: {e}")

    with col_r4:
        st.markdown("<h4 style='color:transparent'> 4) 부적합 및 장기재고 현황 태국법인</h4>", unsafe_allow_html=True)
        st.markdown("<div style='color:transparent; font-size:13px;'>[단위: 톤, 백만원, %]</div>", unsafe_allow_html=True)
        display_memo('f_79', year, month)

    st.divider()


    # ========== 5) 연령별 재고 현황 남통법인 ==========
    col_l5, col_r5 = st.columns([6, 4], gap="large")

    with col_l5:
        st.markdown("<h4> 5) 연령별 재고 현황_중국</h4>", unsafe_allow_html=True)
        st.markdown("<div style='text-align:right; font-size:13px; color:#666;'>[단위: 톤, 백만원]</div>", unsafe_allow_html=True)

        try:
            file_name = st.secrets["sheets"]["f_81_82_83"]
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

            inv = modules.create_age_table_from_company(
                year=int(st.session_state['year']),
                month=int(st.session_state['month']),
                data=raw,
                company_name='남통',
            )

            disp = inv.copy().reset_index()

            def relabel(row):
                b = str(row['구분2']).strip() if pd.notna(row['구분2']) else ''
                s = str(row['구분3']).strip() if pd.notna(row['구분3']) else ''
                if b and b != 'nan' and (not s or s == 'nan'):
                    return b
                if s and s != 'nan':
                    return s
                return ''

            disp['구분'] = disp.apply(relabel, axis=1)
            disp = disp[disp['구분'].str.strip() != ''].copy()
            disp = disp.drop(columns=['구분2', '구분3'])
            cols_order = ['구분'] + [c for c in disp.columns if c != '구분']
            disp = disp[cols_order]

            def fmt_amt(x):
                if pd.isna(x):
                    return "0"
                try:
                    v = float(x)
                except Exception:
                    return x
                if v == 0:
                    return "0"
                v_rounded = int(round(v))
                return f"({abs(v_rounded):,})" if v_rounded < 0 else f"{v_rounded:,}"

            for c in disp.columns:
                if c != '구분':
                    disp[c] = disp[c].apply(fmt_amt)

            year_int = int(inv.attrs.get('base_year'))
            used_m = int(inv.attrs.get('used_month'))
            prev_m = int(inv.attrs.get('prev_month'))
            prev2_m = int(inv.attrs.get('prev2_month'))
            used_y = int(inv.attrs.get('used_year'))
            company = inv.attrs.get('company', '남통')

            yy_m1 = f"{(year_int - 1) % 100:02d}"
            yy_m2 = f"{(year_int - 2) % 100:02d}"
            yy_m3 = f"{(year_int - 3) % 100:02d}"
            yy_m4 = f"{(year_int - 4) % 100:02d}"

            col_yend_m4 = f"'{yy_m4}년말"
            col_yend_m3 = f"'{yy_m3}년말"
            col_yend_m2 = f"'{yy_m2}년말"
            col_yend_m1 = f"'{yy_m1}년말"

            col_prev2 = f"{prev2_m}월"
            col_prev = f"{prev_m}월"
            col_used = f"{used_m}월"

            m1_year = used_y
            m2_year = used_y if prev_m <= used_m else used_y - 1
            m3_year = m2_year if prev2_m <= prev_m else m2_year - 1

            cols = disp.columns.tolist()
            c_idx = {c: i for i, c in enumerate(cols)}

            hdr = [''] * len(cols)
            hdr[c_idx['구분']] = f"[{company}]"

            for col_key in [col_yend_m4, col_yend_m3, col_yend_m2, col_yend_m1]:
                if col_key in c_idx:
                    hdr[c_idx[col_key]] = col_key

            hdr[c_idx[col_prev2]] = f"'{m3_year % 100:02d}년{prev2_m}월"
            hdr[c_idx[col_prev]] = f"'{m2_year % 100:02d}년{prev_m}월"

            yy_used = f"{m1_year % 100:02d}"
            hdr[c_idx[col_used]] = f"'{yy_used}년{used_m}월 중량"
            hdr[c_idx['금액']] = f"'{yy_used}년{used_m}월 금액"
            hdr[c_idx['증감률']] = f"'{yy_used}년{used_m}월 증감률"

            hdr_df = pd.DataFrame([hdr], columns=cols)
            disp_vis = pd.concat([hdr_df, disp], ignore_index=True)

            styles = [
                {'selector': 'thead', 'props': [('display', 'none')]},
                {'selector': 'tbody td', 'props': [('border', '1px solid #aaa'), ('padding', '8px 16px'), ('font-size', '15px')]},
                {'selector': 'tbody tr:nth-child(1) td', 'props': [('text-align', 'center'), ('padding', '8px 16px'), ('font-weight', '700'), ('white-space', 'nowrap'), ('border-top', '1px solid #aaa'), ('border-bottom', '1px solid #aaa')]},
                {'selector': 'tbody tr:nth-child(n+2) td:nth-child(1)', 'props': [('text-align', 'left'), ('white-space', 'nowrap'), ('padding-left', '8px'), ('min-width', '120px')]},
                {'selector': 'tbody tr:nth-child(n+2) td:nth-child(n+2)', 'props': [('text-align', 'right'), ('padding', '8px 16px'), ('white-space', 'nowrap')]},
                {'selector': 'tbody tr:nth-child(6) td, tbody tr:nth-child(11) td, tbody tr:nth-child(16) td, tbody tr:nth-child(19) td', 'props': [('font-weight', '700')]},
            ]

            def red_if_negative(val):
                s = str(val).strip()
                if s.startswith("(") and s.endswith(")"):
                    return "color: red;"
                return ""

            styled = (
                disp_vis.style
                .set_table_styles(styles)
                .map(red_if_negative)
                .hide(axis='index')
            )
            html_table = styled.to_html(escape=False)

            st.markdown(
                f"<div style='width: 100%; max-width: 100%; overflow-x: auto; display: block;'>{html_table}</div>",
                unsafe_allow_html=True
            )

        except Exception as e:
            st.error(f"연령별 재고 현황 남통법인 표 생성 중 오류: {e}")

    with col_r5:
        st.markdown("<h4 style='color:transparent'> 5) 연령별 재고 현황 남통법인</h4>", unsafe_allow_html=True)
        st.markdown("<div style='color:transparent; font-size:13px;'>[단위: 톤, 백만원]</div>", unsafe_allow_html=True)
        display_memo('f_81', year, month)

    st.divider()

    # ========== 6) 연령별 재고 현황 태국법인 ==========
    col_l6, col_r6 = st.columns([6, 4], gap="large")

    with col_l6:
        st.markdown("<h4> 6) 연령별 재고 현황_태국</h4>", unsafe_allow_html=True)
        st.markdown("<div style='text-align:right; font-size:13px; color:#666;'>[단위: 톤, 백만원]</div>", unsafe_allow_html=True)

        try:
            file_name = st.secrets["sheets"]["f_81_82_83"]
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

            inv = modules.create_age_table_from_company(
                year=int(st.session_state['year']),
                month=int(st.session_state['month']),
                data=raw,
                company_name='태국',
            )

            disp = inv.copy().reset_index()

            def relabel(row):
                b = str(row['구분2']).strip() if pd.notna(row['구분2']) else ''
                s = str(row['구분3']).strip() if pd.notna(row['구분3']) else ''
                if b and b != 'nan' and (not s or s == 'nan'):
                    return b
                if s and s != 'nan':
                    return s
                return ''

            disp['구분'] = disp.apply(relabel, axis=1)
            disp = disp[disp['구분'].str.strip() != ''].copy()
            disp = disp.drop(columns=['구분2', '구분3'])
            cols_order = ['구분'] + [c for c in disp.columns if c != '구분']
            disp = disp[cols_order]

            def fmt_amt(x):
                if pd.isna(x):
                    return "0"
                try:
                    v = float(x)
                except Exception:
                    return x
                if v == 0:
                    return "0"
                v_rounded = int(round(v))
                return f"({abs(v_rounded):,})" if v_rounded < 0 else f"{v_rounded:,}"

            for c in disp.columns:
                if c != '구분':
                    disp[c] = disp[c].apply(fmt_amt)

            year_int = int(inv.attrs.get('base_year'))
            used_m = int(inv.attrs.get('used_month'))
            prev_m = int(inv.attrs.get('prev_month'))
            prev2_m = int(inv.attrs.get('prev2_month'))
            used_y = int(inv.attrs.get('used_year'))
            company = inv.attrs.get('company', '태국')

            yy_m1 = f"{(year_int - 1) % 100:02d}"
            yy_m2 = f"{(year_int - 2) % 100:02d}"
            yy_m3 = f"{(year_int - 3) % 100:02d}"
            yy_m4 = f"{(year_int - 4) % 100:02d}"

            col_yend_m4 = f"'{yy_m4}년말"
            col_yend_m3 = f"'{yy_m3}년말"
            col_yend_m2 = f"'{yy_m2}년말"
            col_yend_m1 = f"'{yy_m1}년말"

            col_prev2 = f"{prev2_m}월"
            col_prev = f"{prev_m}월"
            col_used = f"{used_m}월"

            m1_year = used_y
            m2_year = used_y if prev_m <= used_m else used_y - 1
            m3_year = m2_year if prev2_m <= prev_m else m2_year - 1

            cols = disp.columns.tolist()
            c_idx = {c: i for i, c in enumerate(cols)}

            hdr = [''] * len(cols)
            hdr[c_idx['구분']] = f"[{company}]"

            for col_key in [col_yend_m4, col_yend_m3, col_yend_m2, col_yend_m1]:
                if col_key in c_idx:
                    hdr[c_idx[col_key]] = col_key

            hdr[c_idx[col_prev2]] = f"'{m3_year % 100:02d}년{prev2_m}월"
            hdr[c_idx[col_prev]] = f"'{m2_year % 100:02d}년{prev_m}월"

            yy_used = f"{m1_year % 100:02d}"
            hdr[c_idx[col_used]] = f"'{yy_used}년{used_m}월 중량"
            hdr[c_idx['금액']] = f"'{yy_used}년{used_m}월 금액"
            hdr[c_idx['증감률']] = f"'{yy_used}년{used_m}월 증감률"

            hdr_df = pd.DataFrame([hdr], columns=cols)
            disp_vis = pd.concat([hdr_df, disp], ignore_index=True)

            styles = [
                {'selector': 'thead', 'props': [('display', 'none')]},
                {'selector': 'tbody td', 'props': [('border', '1px solid #aaa'), ('padding', '8px 16px'), ('font-size', '15px')]},
                {'selector': 'tbody tr:nth-child(1) td', 'props': [('text-align', 'center'), ('padding', '8px 16px'), ('font-weight', '700'), ('white-space', 'nowrap'), ('border-top', '1px solid #aaa'), ('border-bottom', '1px solid #aaa')]},
                {'selector': 'tbody tr:nth-child(n+2) td:nth-child(1)', 'props': [('text-align', 'left'), ('white-space', 'nowrap'), ('padding-left', '8px'), ('min-width', '120px')]},
                {'selector': 'tbody tr:nth-child(n+2) td:nth-child(n+2)', 'props': [('text-align', 'right'), ('padding', '8px 16px'), ('white-space', 'nowrap')]},
                {'selector': 'tbody tr:nth-child(6) td, tbody tr:nth-child(11) td, tbody tr:nth-child(16) td, tbody tr:nth-child(19) td', 'props': [('font-weight', '700')]},
            ]

            def red_if_negative(val):
                s = str(val).strip()
                if s.startswith("(") and s.endswith(")"):
                    return "color: red;"
                return ""

            styled = (
                disp_vis.style
                .set_table_styles(styles)
                .map(red_if_negative)
                .hide(axis='index')
            )
            html_table = styled.to_html(escape=False)

            st.markdown(
                f"<div style='width: 100%; max-width: 100%; overflow-x: auto; display: block;'>{html_table}</div>",
                unsafe_allow_html=True
            )

        except Exception as e:
            st.error(f"연령별 재고 현황 태국법인 표 생성 중 오류: {e}")

    with col_r6:
        st.markdown("<h4 style='color:transparent'> 6) 연령별 재고 현황 태국법인</h4>", unsafe_allow_html=True)
        st.markdown("<div style='color:transparent; font-size:13px;'>[단위: 톤, 백만원]</div>", unsafe_allow_html=True)
        display_memo('f_82', year, month)

    st.divider()

with t7:
    # ========== 1) 채권 현황 남통법인 ==========
    col_l, col_r = st.columns([6, 4], gap="large")

    with col_l:
        st.markdown("<h4> 1) 채권 현황_중국</h4>", unsafe_allow_html=True)
        st.markdown("<div style='text-align:right; font-size:13px; color:#666;'>[단위: 백만원, %]</div>", unsafe_allow_html=True)

        try:
            file_name = st.secrets["sheets"]["f_84_85_86"]
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

            importlib.invalidate_caches()
            importlib.reload(modules)

            ar = modules.create_ar_status_table_from_company(
                year=int(st.session_state['year']),
                month=int(st.session_state['month']),
                data=raw,
                company_name='남통',
            )

            disp = ar.copy().reset_index()

            def fmt_amt(x):
                if pd.isna(x):
                    return "0"
                try:
                    v = float(x)
                except Exception:
                    return x
                if v == 0:
                    return "0"
                v_rounded = int(round(v))
                return f"({abs(v_rounded):,})" if v_rounded < 0 else f"{v_rounded:,}"

            def fmt_rate(x):
                if pd.isna(x):
                    return "-"
                try:
                    v = float(x)
                except Exception:
                    return x
                if v == 0:
                    return "-"
                return f"{v:.1f}"

            ratio_mask = disp['구분'] == '초과채권 비율(%)'

            for c in disp.columns:
                if c == '구분':
                    continue
                disp.loc[ratio_mask, c] = disp.loc[ratio_mask, c].apply(fmt_rate)
                disp.loc[~ratio_mask, c] = disp.loc[~ratio_mask, c].apply(fmt_amt)

            cols = disp.columns.tolist()
            c_idx = {c: i for i, c in enumerate(cols)}

            name_i = c_idx['구분']
            year_int = int(ar.attrs.get('base_year'))
            used_y = int(ar.attrs.get('used_year'))
            used_m = int(ar.attrs.get('used_month'))
            prev_m = int(ar.attrs.get('prev_month'))

            yy_m1 = f"{(year_int - 1) % 100:02d}"
            yy_m2 = f"{(year_int - 2) % 100:02d}"
            yy_m3 = f"{(year_int - 3) % 100:02d}"
            yy_m4 = f"{(year_int - 4) % 100:02d}"

            col_yend_m4 = f"'{yy_m4}년말"
            col_yend_m3 = f"'{yy_m3}년말"
            col_yend_m2 = f"'{yy_m2}년말"
            col_yend_m1 = f"'{yy_m1}년말"
            col_prev = f"{prev_m}월"
            col_used = f"{used_m}월"

            y4_i = c_idx[col_yend_m4]
            y3_i = c_idx[col_yend_m3]
            y2_i = c_idx[col_yend_m2]
            y1_i = c_idx[col_yend_m1]
            prev_i = c_idx[col_prev]
            used_i = c_idx[col_used]

            m_used_year = used_y
            m_prev_year = used_y
            if prev_m > used_m:
                m_prev_year = used_y - 1

            hdr = [''] * len(cols)
            hdr[name_i] = "[남통]"
            hdr[y4_i] = col_yend_m4
            hdr[y3_i] = col_yend_m3
            hdr[y2_i] = col_yend_m2
            hdr[y1_i] = col_yend_m1
            hdr[prev_i] = f"'{m_prev_year % 100:02d}년 {prev_m}월"
            hdr[used_i] = f"'{m_used_year % 100:02d}년 {used_m}월"

            hdr_df = pd.DataFrame([hdr], columns=cols)
            disp_vis = pd.concat([hdr_df, disp], ignore_index=True)

            def apply_ar_indent(name):
                clean = str(name).strip()
                lv0 = ['매출액 ( 세금포함 )', '매출액(세금포함)', '정상채권', '기준초과채권',
                       '매출채권 계', '초과채권 비율(%)', '초과채권 이자손실', '매출채권기일', '정상채권기일', '차이']
                lv1 = ['3개월 이하', '3개월 초과', '6개월 초과', '회수불능']

                if clean in lv0:
                    lv = 0
                elif clean in lv1:
                    lv = 1
                else:
                    lv = 0

                if lv > 0:
                    return f'<span style="padding-left:{lv * 16}px">{name}</span>'
                return clean

            for idx in disp_vis.index[1:]:
                val = str(disp_vis.loc[idx, "구분"]).strip()
                disp_vis.loc[idx, "구분"] = apply_ar_indent(val)

            def red_if_negative(val):
                s = str(val).strip()
                if s.startswith("(") and s.endswith(")"):
                    return "color: red;"
                return ""

            styles = [
                {'selector': 'thead', 'props': [('display', 'none')]},
                {'selector': 'tbody td', 'props': [('border', '1px solid #aaa'), ('padding', '8px 16px'), ('font-size', '15px')]},
                {'selector': 'tbody tr:nth-child(1) td', 'props': [('text-align', 'center'), ('padding', '8px 16px'), ('font-weight', '700'), ('font-size', '15px'), ('border-top', '1px solid #aaa'), ('border-bottom', '1px solid #aaa'), ('border-left', '1px solid #aaa'), ('border-right', '1px solid #aaa')]},
                {'selector': 'tbody tr:nth-child(n+2) td', 'props': [('line-height', '1.4'), ('padding', '8px 16px'), ('font-size', '15px'), ('text-align', 'right'), ('border-top', '1px solid #aaa'), ('border-bottom', '1px solid #aaa'), ('border-left', '1px solid #aaa'), ('border-right', '1px solid #aaa')]},
                {'selector': 'tbody tr:nth-child(n+2) td:nth-child(1)', 'props': [('text-align', 'left')]},
            ]

            styled = (
                disp_vis.style
                .set_table_styles(styles)
                .map(red_if_negative)
                .hide(axis='index')
            )
            html_table = styled.to_html(escape=False)

            st.markdown(
                f"<div style='width: 100%; max-width: 100%; overflow-x: auto; display: block;'>{html_table}</div>",
                unsafe_allow_html=True
            )

        except Exception as e:
            st.error(f"채권 현황 남통법인 표 생성 중 오류: {e}")

    with col_r:
        st.markdown("<h4 style='color:transparent'> 1) 채권 현황 남통법인</h4>", unsafe_allow_html=True)
        st.markdown("<div style='color:transparent; font-size:13px;'>[단위: 백만원, %]</div>", unsafe_allow_html=True)
        display_memo('f_84', year, month)

    st.divider()

    # ========== 2) 채권 현황 태국법인 ==========
    col_l2, col_r2 = st.columns([6, 4], gap="large")

    with col_l2:
        st.markdown("<h4> 2) 채권 현황_태국</h4>", unsafe_allow_html=True)
        st.markdown("<div style='text-align:right; font-size:13px; color:#666;'>[단위: 백만원, %]</div>", unsafe_allow_html=True)

        try:
            file_name = st.secrets["sheets"]["f_84_85_86"]
            raw = pd.read_csv(file_name, dtype=str)

            for c in raw.columns:
                raw[c] = raw[c].apply(clean_accounting_str)

            importlib.invalidate_caches()
            importlib.reload(modules)

            ar = modules.create_ar_status_table_from_company(
                year=int(st.session_state['year']),
                month=int(st.session_state['month']),
                data=raw,
                company_name='태국',
            )

            disp = ar.copy().reset_index()

            def fmt_amt(x):
                if pd.isna(x):
                    return "0"
                try:
                    v = float(x)
                except Exception:
                    return x
                if v == 0:
                    return "0"
                v_rounded = int(round(v))
                return f"({abs(v_rounded):,})" if v_rounded < 0 else f"{v_rounded:,}"

            def fmt_rate(x):
                if pd.isna(x):
                    return "-"
                try:
                    v = float(x)
                except Exception:
                    return x
                if v == 0:
                    return "-"
                return f"{v:.1f}"

            ratio_mask = disp['구분'] == '초과채권 비율(%)'

            for c in disp.columns:
                if c == '구분':
                    continue
                disp.loc[ratio_mask, c] = disp.loc[ratio_mask, c].apply(fmt_rate)
                disp.loc[~ratio_mask, c] = disp.loc[~ratio_mask, c].apply(fmt_amt)

            cols = disp.columns.tolist()
            c_idx = {c: i for i, c in enumerate(cols)}

            name_i = c_idx['구분']
            year_int = int(ar.attrs.get('base_year'))
            used_y = int(ar.attrs.get('used_year'))
            used_m = int(ar.attrs.get('used_month'))
            prev_m = int(ar.attrs.get('prev_month'))

            yy_m1 = f"{(year_int - 1) % 100:02d}"
            yy_m2 = f"{(year_int - 2) % 100:02d}"
            yy_m3 = f"{(year_int - 3) % 100:02d}"
            yy_m4 = f"{(year_int - 4) % 100:02d}"

            col_yend_m4 = f"'{yy_m4}년말"
            col_yend_m3 = f"'{yy_m3}년말"
            col_yend_m2 = f"'{yy_m2}년말"
            col_yend_m1 = f"'{yy_m1}년말"
            col_prev = f"{prev_m}월"
            col_used = f"{used_m}월"

            y4_i = c_idx[col_yend_m4]
            y3_i = c_idx[col_yend_m3]
            y2_i = c_idx[col_yend_m2]
            y1_i = c_idx[col_yend_m1]
            prev_i = c_idx[col_prev]
            used_i = c_idx[col_used]

            m_used_year = used_y
            m_prev_year = used_y
            if prev_m > used_m:
                m_prev_year = used_y - 1

            hdr = [''] * len(cols)
            hdr[name_i] = "[태국]"
            hdr[y4_i] = col_yend_m4
            hdr[y3_i] = col_yend_m3
            hdr[y2_i] = col_yend_m2
            hdr[y1_i] = col_yend_m1
            hdr[prev_i] = f"'{m_prev_year % 100:02d}년 {prev_m}월"
            hdr[used_i] = f"'{m_used_year % 100:02d}년 {used_m}월"

            hdr_df = pd.DataFrame([hdr], columns=cols)
            disp_vis = pd.concat([hdr_df, disp], ignore_index=True)

            for idx in disp_vis.index[1:]:
                val = str(disp_vis.loc[idx, "구분"]).strip()
                disp_vis.loc[idx, "구분"] = apply_ar_indent(val)

            def red_if_negative(val):
                s = str(val).strip()
                if s.startswith("(") and s.endswith(")"):
                    return "color: red;"
                return ""

            styles = [
                {'selector': 'thead', 'props': [('display', 'none')]},
                {'selector': 'tbody td', 'props': [('border', '1px solid #aaa'), ('padding', '8px 16px'), ('font-size', '15px')]},
                {'selector': 'tbody tr:nth-child(1) td', 'props': [('text-align', 'center'), ('padding', '8px 16px'), ('font-weight', '700'), ('font-size', '15px'), ('border-top', '1px solid #aaa'), ('border-bottom', '1px solid #aaa'), ('border-left', '1px solid #aaa'), ('border-right', '1px solid #aaa')]},
                {'selector': 'tbody tr:nth-child(n+2) td', 'props': [('line-height', '1.4'), ('padding', '8px 16px'), ('font-size', '15px'), ('text-align', 'right'), ('border-top', '1px solid #aaa'), ('border-bottom', '1px solid #aaa'), ('border-left', '1px solid #aaa'), ('border-right', '1px solid #aaa')]},
                {'selector': 'tbody tr:nth-child(n+2) td:nth-child(1)', 'props': [('text-align', 'left')]},
            ]

            styled = (
                disp_vis.style
                .set_table_styles(styles)
                .map(red_if_negative)
                .hide(axis='index')
            )
            html_table = styled.to_html(escape=False)

            st.markdown(
                f"<div style='width: 100%; max-width: 100%; overflow-x: auto; display: block;'>{html_table}</div>",
                unsafe_allow_html=True
            )

        except Exception as e:
            st.error(f"채권 현황 태국법인 표 생성 중 오류: {e}")

    with col_r2:
        st.markdown("<h4 style='color:transparent'> 2) 채권 현황 태국법인</h4>", unsafe_allow_html=True)
        st.markdown("<div style='color:transparent; font-size:13px;'>[단위: 백만원, %]</div>", unsafe_allow_html=True)
        display_memo('f_86', year, month)

    st.divider()

with t8:
    # ========== 1) 인원현황표 ==========
    col_l1, col_r1 = st.columns([6, 4], gap="large")

    with col_l1:
        st.markdown("<h4> 1) 인원현황표</h4>", unsafe_allow_html=True)
        st.markdown("<div style='text-align:right; font-size:13px; color:#666;'>[단위: 명]</div>", unsafe_allow_html=True)

        try:
            file_name = st.secrets["sheets"]["f_87_88"]
            raw = pd.read_csv(file_name, dtype=str)

            year = int(st.session_state["year"])
            month = int(st.session_state["month"])

            ar = modules.create_87(
                year=year,
                month=month,
                data=raw,
            )

            disp = ar.copy()

            current_plant = ""
            plant_labels = []
            for _, row in disp.iterrows():
                g1 = str(row["구분1"]).strip()
                g2 = str(row["구분2"]).strip()
                if g2 == "합계":
                    current_plant = g1
                plant_labels.append(current_plant)

            disp["_plant"] = plant_labels
            disp = disp[~disp["_plant"].isin(["천진", "중국"])].copy()
            disp = disp.drop(columns=["_plant"])

            def merge_label(row):
                g2 = str(row["구분2"]).strip()
                if g2 == "합계":
                    return str(row["구분1"]).strip()
                return g2

            is_total = disp["구분2"] == "합계"
            disp["구분"] = disp.apply(merge_label, axis=1)
            disp = disp.drop(columns=["구분1", "구분2"])
            cols_reorder = ["구분"] + [c for c in disp.columns if c != "구분"]
            disp = disp[cols_reorder]

            def fmt_amt(x):
                if pd.isna(x):
                    return "0"
                try:
                    v = float(x)
                except Exception:
                    return x
                if v == 0:
                    return "0"
                v_rounded = int(round(v))
                return f"({abs(v_rounded):,})" if v_rounded < 0 else f"{v_rounded:,}"

            def fmt_rate(x):
                if pd.isna(x):
                    return "0%"
                try:
                    v = float(x)
                except Exception:
                    return x
                return f"{v:.0f}%"

            for c in disp.columns:
                if c == "구분":
                    continue
                if c == "%":
                    disp[c] = disp[c].apply(fmt_rate)
                else:
                    disp[c] = disp[c].apply(fmt_amt)

            cols = disp.columns.tolist()
            c_idx = {c: i for i, c in enumerate(cols)}

            name_i = c_idx["구분"]

            yy_m1 = f"{(year - 1) % 100:02d}"
            yy_m2 = f"{(year - 2) % 100:02d}"
            yy_m3 = f"{(year - 3) % 100:02d}"
            yy_m4 = f"{(year - 4) % 100:02d}"

            col_yend_m4 = f"'{yy_m4}년말"
            col_yend_m3 = f"'{yy_m3}년말"
            col_yend_m2 = f"'{yy_m2}년말"
            col_yend_m1 = f"'{yy_m1}년말"

            prev_y = year
            prev_m = month - 1
            if prev_m <= 0:
                prev_y -= 1
                prev_m += 12

            col_prev = f"{prev_m}월"
            col_used = f"{month}월"

            y4_i = c_idx[col_yend_m4]
            y3_i = c_idx[col_yend_m3]
            y2_i = c_idx[col_yend_m2]
            y1_i = c_idx[col_yend_m1]
            prev_i = c_idx[col_prev]
            used_i = c_idx[col_used]

            hdr = [""] * len(cols)
            hdr[name_i] = "구분"
            hdr[y4_i] = col_yend_m4
            hdr[y3_i] = col_yend_m3
            hdr[y2_i] = col_yend_m2
            hdr[y1_i] = col_yend_m1
            hdr[prev_i] = f"'{prev_y % 100:02d}년 {prev_m}월"
            hdr[used_i] = f"'{year % 100:02d}년 {month}월"

            year_end_cols = {col_yend_m4, col_yend_m3, col_yend_m2, col_yend_m1}
            for c, i in c_idx.items():
                if (
                        hdr[i] == ""
                        and c != "구분"
                        and c not in year_end_cols
                        and c not in (col_prev, col_used)
                ):
                    hdr[i] = c

            hdr_df = pd.DataFrame([hdr], columns=cols)
            disp_vis = pd.concat([hdr_df, disp], ignore_index=True)

            bold_rows = [i + 2 for i, val in enumerate(is_total) if val]

            def red_if_negative(val):
                s = str(val).strip()
                if s.startswith("(") and s.endswith(")"):
                    return "color: red;"
                return ""

            styles = [
                {'selector': 'thead', 'props': [('display', 'none')]},
                {'selector': 'tbody td', 'props': [('border', '1px solid #aaa'), ('padding', '8px 16px'), ('font-size', '15px')]},
                {'selector': 'tbody tr:nth-child(1) td', 'props': [('text-align', 'center'), ('padding', '8px 16px'), ('font-weight', '700'), ('font-size', '15px'), ('border-top', '1px solid #aaa'), ('border-bottom', '1px solid #aaa'), ('border-left', '1px solid #aaa'), ('border-right', '1px solid #aaa')]},
                {'selector': 'tbody tr:nth-child(n+2) td', 'props': [('line-height', '1.4'), ('padding', '8px 16px'), ('font-size', '15px'), ('text-align', 'right'), ('border-top', '1px solid #aaa'), ('border-bottom', '1px solid #aaa'), ('border-left', '1px solid #aaa'), ('border-right', '1px solid #aaa')]},
                {'selector': 'tbody tr:nth-child(n+2) td:nth-child(1)', 'props': [('text-align', 'left')]},
            ]

            styles += [
                {'selector': f'tbody tr:nth-child({r}) td', 'props': [('font-weight', '700')]}
                for r in bold_rows
            ]

            styled = (
                disp_vis.style
                .set_table_styles(styles)
                .map(red_if_negative)
                .hide(axis='index')
            )
            html_table = styled.to_html(escape=False)

            st.markdown(
                f"<div style='width: 100%; max-width: 100%; overflow-x: auto; display: block;'>{html_table}</div>",
                unsafe_allow_html=True
            )

        except Exception as e:
            st.error(f"인원현황 표 생성 중 오류: {e}")

    with col_r1:
        st.markdown("<h4 style='color:transparent'> 1) 인원현황표</h4>", unsafe_allow_html=True)
        st.markdown("<div style='color:transparent; font-size:13px;'>[단위: 명]</div>", unsafe_allow_html=True)
        display_memo("f_87", year, month)

    st.divider()

    # ========== 2) 인당 월평균 생산량 ==========
    col_l2, col_r2 = st.columns([6, 4], gap="large")

    with col_l2:
        st.markdown("<h4> 2) 인당 월평균 생산량</h4>", unsafe_allow_html=True)
        st.markdown("<div style='text-align:right; font-size:13px; color:#666;'>[단위: 명, 톤]</div>", unsafe_allow_html=True)

        try:
            file_name = st.secrets["sheets"]["f_87_88"]
            raw = pd.read_csv(file_name, dtype=str)

            year = int(st.session_state["year"])
            month = int(st.session_state["month"])

            ar = modules.create_89(
                year=year,
                month=month,
                data=raw,
            )

            disp = ar.copy()

            def fmt_int(x):
                if pd.isna(x):
                    return "0"
                try:
                    v = float(x)
                except Exception:
                    return x
                if v == 0:
                    return "0"
                v_r = int(round(v))
                return f"{v_r:,}"

            for c in disp.columns:
                if c in ("구분1", "구분2"):
                    continue
                disp[c] = disp[c].apply(fmt_int)

            current_plant = ""
            plant_labels = []
            for _, row in disp.iterrows():
                g1 = str(row["구분1"]).strip()
                g2 = str(row["구분2"]).strip()
                if g2 == "(인당)":
                    current_plant = g1
                plant_labels.append(current_plant)

            def merge_label(row):
                g1 = str(row["구분1"]).strip()
                g2 = str(row["구분2"]).strip()
                if g2 == "(인당)":
                    return f"{g1} {g2}"
                return g2

            is_total = disp["구분2"] == "(인당)"
            disp["구분"] = disp.apply(merge_label, axis=1)
            disp = disp.drop(columns=["구분1", "구분2"])
            cols_reorder = ["구분"] + [c for c in disp.columns if c != "구분"]
            disp = disp[cols_reorder]

            cols = disp.columns.tolist()
            c_idx = {c: i for i, c in enumerate(cols)}

            name_i = c_idx["구분"]

            yy4 = f"{(year - 4) % 100:02d}"
            yy3 = f"{(year - 3) % 100:02d}"
            yy2 = f"{(year - 2) % 100:02d}"
            yy1 = f"{(year - 1) % 100:02d}"
            yy0 = f"{year % 100:02d}"

            col_y4 = f"'{yy4}년 월평균"
            col_y3 = f"'{yy3}년 월평균"
            col_y2 = f"'{yy2}년 월평균"
            col_y1 = f"'{yy1}년 월평균"
            col_y0_avg = f"'{yy0}년 월평균"

            prev_y = year
            prev_m = month - 1
            if prev_m <= 0:
                prev_y -= 1
                prev_m += 12

            col_prev = f"{prev_m}월"
            col_cur = f"{month}월"

            y4_i = c_idx[col_y4]
            y3_i = c_idx[col_y3]
            y2_i = c_idx[col_y2]
            y1_i = c_idx[col_y1]
            prev_i = c_idx[col_prev]
            cur_i = c_idx[col_cur]
            y0_avg_i = c_idx[col_y0_avg]

            hdr = [""] * len(cols)
            hdr[name_i] = "구분"
            hdr[y4_i] = col_y4
            hdr[y3_i] = col_y3
            hdr[y2_i] = col_y2
            hdr[y1_i] = col_y1
            hdr[prev_i] = f"'{prev_y % 100:02d}년 {prev_m}월"
            hdr[cur_i] = f"'{yy0}년 {month}월"
            hdr[y0_avg_i] = col_y0_avg

            hdr_df = pd.DataFrame([hdr], columns=cols)
            disp_vis = pd.concat([hdr_df, disp], ignore_index=True)

            bold_rows = [i + 2 for i, val in enumerate(is_total) if val]

            def red_if_negative(val):
                s = str(val).strip()
                if s.startswith("(") and s.endswith(")"):
                    return "color: red;"
                return ""

            styles = [
                {'selector': 'thead', 'props': [('display', 'none')]},
                {'selector': 'tbody td', 'props': [('border', '1px solid #aaa'), ('padding', '8px 16px'), ('font-size', '15px')]},
                {'selector': 'tbody tr:nth-child(1) td', 'props': [('text-align', 'center'), ('padding', '8px 16px'), ('font-weight', '700'), ('font-size', '15px'), ('border-top', '1px solid #aaa'), ('border-bottom', '1px solid #aaa'), ('border-left', '1px solid #aaa'), ('border-right', '1px solid #aaa')]},
                {'selector': 'tbody tr:nth-child(n+2) td', 'props': [('line-height', '1.4'), ('padding', '8px 16px'), ('font-size', '15px'), ('text-align', 'right'), ('border-top', '1px solid #aaa'), ('border-bottom', '1px solid #aaa'), ('border-left', '1px solid #aaa'), ('border-right', '1px solid #aaa')]},
                {'selector': 'tbody tr:nth-child(n+2) td:nth-child(1)', 'props': [('text-align', 'left')]},
            ]

            styles += [
                {'selector': f'tbody tr:nth-child({r}) td', 'props': [('font-weight', '700')]}
                for r in bold_rows
            ]

            styled = (
                disp_vis.style
                .set_table_styles(styles)
                .map(red_if_negative)
                .hide(axis='index')
            )
            html_table = styled.to_html(escape=False)

            st.markdown(
                f"<div style='width: 100%; max-width: 100%; overflow-x: auto; display: block;'>{html_table}</div>",
                unsafe_allow_html=True
            )

        except Exception as e:
            st.error(f"인당 월평균 생산량 표 생성 중 오류: {e}")

    with col_r2:
        st.markdown("<h4 style='color:transparent'> 2) 인당 월평균 생산량</h4>", unsafe_allow_html=True)
        st.markdown("<div style='color:transparent; font-size:13px;'>[단위: 명, 톤]</div>", unsafe_allow_html=True)
        display_memo("f_89", year, month)

    st.divider()

# Footer
st.markdown("""
<style>.footer { bottom: 0; left: 0; right: 0; padding: 8px; text-align: center; font-size: 13px; color: #666666;}</style>
<div class="footer">ⓒ 2025 SeAH Special Steel Corp. All rights reserved.</div>
""", unsafe_allow_html=True)