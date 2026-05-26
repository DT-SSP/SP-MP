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
    to_nth = lambda r: r + header_rows + 1  
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

st.markdown(f"## {year}년 {month}월 해외법인실적")

t1, t2, t3, t4, t5, t6, t7, t8 = st.tabs(['1. 손익요약', '2. 현금흐름', '3. 재무상태표', '4. 판매구성', '5. 전월대비 손익차이', '6. 재고자산 현황', '7. 채권현황', '8. 인원현황'])

with t1:
    st.markdown("<h4> 1) 손익요약</h4>", unsafe_allow_html=True)
    st.markdown(
        "<div style='text-align:left; font-size:13px; color:#666;'>"
        "[단위: 톤, 백만원, %]</div>",
        unsafe_allow_html=True
    )

    try:
        file_name = st.secrets["sheets"]["f_61"]
        raw = pd.read_csv(file_name, dtype=str)

        year  = int(st.session_state["year"])
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
            disp.loc[ pct_mask, c] = disp.loc[ pct_mask, c].apply(fmt_pct)

        # ====== 대분류 + 구분 합쳐서 하나의 열로 ======
        disp["구분"] = disp["대분류"] + " " + disp["구분"]
        disp = disp.drop(columns=["대분류"])

        cols = disp.columns.tolist()
        c_idx = {c: i for i, c in enumerate(cols)}

        pm = month - 1 if month > 1 else 12
        yy = str(year)[-2:]

        col_prev  = f"{pm}월실적"
        col_m_pln = f"{month}월계획"
        col_m_act = f"{month}월실적"
        col_m_gap = f"{month}월계획비"
        col_m_mom = f"{month}월전월비"
        col_acc_p = f"'{yy}년누적계획"
        col_acc_a = f"'{yy}년누적실적"
        col_acc_g = f"'{yy}년누적계획비"

        # ====== 헤더 1줄 ======
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

        # ====== 행 구성 (헤더1 + 데이터10) ======
        # row1: 헤더
        # row2~3: 매출액 중국, 매출액 태국
        # row4~7: 판매량 중국, 판매량 태국, 판매량 (제품), 판매량 (연강)
        # row8~9: 영업이익 중국, 영업이익 태국
        # row10~11: 영업이익률(%) 중국, 영업이익률(%) 태국

        styles = [
            {'selector': 'thead', 'props': [('display', 'none')]},

            # 전체 셀 기본 테두리 - 얇은 검정선
            {
                'selector': 'tbody td',
                'props': [('border', '1px solid black')]
            },

            # 헤더 1행
            {
                'selector': 'tbody tr:nth-child(1) td',
                'props': [
                    ('text-align', 'center'),
                    ('padding', '6px 8px'),
                    ('font-weight', '600'),
                    ('white-space', 'nowrap'),
                    ('border-top', '1px solid black'),
                    ('border-bottom', '1px solid black'),
                ]
            },

            # 구분 열 (1열) 좌측 정렬
            {
                'selector': 'tbody tr td:nth-child(1)',
                'props': [
                    ('text-align', 'left'),
                    ('white-space', 'nowrap'),
                    ('padding-left', '8px'),
                    ('min-width', '120px'),
                ]
            },

            # 수치 열 우측 정렬
            {
                'selector': 'tbody tr td:nth-child(n+2)',
                'props': [
                    ('text-align', 'right'),
                    ('padding', '4px 8px'),
                    ('white-space', 'nowrap'),
                ]
            },
        ]

        # ====== 음수 빨간색 처리 ======
        def red_if_negative(val):
            s = str(val).strip()
            if s.startswith("-") and s != "-":
                return "color: red;"
            return ""

        data_rows = disp_vis.index[1:]
        num_col_labels = [c for c in disp_vis.columns if c != "구분"]

        applymap_rules = [
            (red_if_negative, (data_rows, num_col_labels))
        ]

        display_styled_df(
            disp_vis,
            styles=styles,
            already_flat=True,
            applymap_rules=applymap_rules,
        )

        display_memo('f_61', year, month)

    except Exception as e:
        st.error(f"손익요약 생성 중 오류: {e}")

    st.divider()

#현금흐름표(중국,태국)
with t2:

    st.markdown("<h4> 1) 현금흐름 중국법인</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 백만원]</div>", unsafe_allow_html=True)

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
            df["월"] = df["월"].fillna("").astype(str).str.strip()
            df["실적"] = _to_num(df["실적"])

            # 남통만 사용 (천진 완전 제외)
            df = df[df["구분1"] == "남통"].copy()

            df["__ord__"] = range(len(df))
            return df


        df0 = _clean_cf_namtong(raw)
        year = int(st.session_state["year"])
        month = int(st.session_state["month"])

        item_order = [
            "영업활동현금흐름",
            "당기순이익",
            "조정",
            "감가상각비",
            "기타",
            "자산부채증감",
            "매출채권 감소(증가)",
            "기타채권 감소(증가)",
            "재고자산 감소(증가)",
            "기타자산 감소(증가)",
            "매입채무 증가(감소)",
            "기타채무 증가(감소)",
            "퇴직급여부채증가(감소)",
            "법인세납부",
            "이자의 수취",
            "이자의 지급",
            "투자활동현금흐름",
            "유형자산취득",
            "무형자산취득",
            "기타 투자활동",
            "재무활동현금흐름",
            "차입금의 증가(감소)",
            "현금성자산의 증감",
            "기초의 현금",
            "현금성자산의 환율변동",
            "기말의 현금",
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
        col_memo_label = "당월 현금흐름 주요변동내역(단위: RMB)"

        sel_year = df0[
            (df0["연도"] == year)
            & (df0["구분2"].isin(item_order))
            ]

        if sel_year.empty:
            base = pd.DataFrame(
                {
                    col_prev2_label: [np.nan] * len(index_labels),
                    col_prev1_label: [np.nan] * len(index_labels),
                    col_prev_label: [np.nan] * len(index_labels),
                    col_curr_label: [np.nan] * len(index_labels),
                    col_currsum_label: [np.nan] * len(index_labels),
                    col_memo_label: [""] * len(index_labels),
                },
                index=pd.Index(index_labels, name="구분"),
            )
        else:
            def _sum_item_year(name: str, nth: int, y: int) -> float:
                sub = df0[
                    (df0["연도"] == y)
                    & (df0["구분2"] == name)
                    ].sort_values("__ord__", kind="stable")
                if len(sub) >= nth:
                    return float(sub.iloc[nth - 1]["실적"])
                return 0.0


            def _block_year(y: int):
                return [_sum_item_year(nm, nth, y) for (nm, nth) in order_with_n]


            def _sum_item_kind(name: str, nth: int, y: int, kind: str) -> float:
                sub = df0[
                    (df0["연도"] == y)
                    & (df0["월"] == kind)
                    & (df0["구분2"] == name)
                    ].sort_values("__ord__", kind="stable")
                if len(sub) >= nth:
                    return float(sub.iloc[nth - 1]["실적"])
                return 0.0


            def _block_kind(y: int, kind: str):
                return [_sum_item_kind(nm, nth, y, kind) for (nm, nth) in order_with_n]


            vals_prev2 = _block_year(year - 2)
            vals_prev1 = _block_year(year - 1)
            vals_prev = _block_kind(year, "전월누적")
            vals_curr = _block_kind(year, "당월")
            vals_ytd = _block_kind(year, "당월누적")

            # 수치 컬럼만으로 base 구성 (메모 컬럼 나중에 추가)
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
                if label in base.index:
                    return base.loc[label].astype(float)
                else:
                    return pd.Series(0.0, index=base.columns, dtype=float)


            base.loc["조정"] = _row("감가상각비") + _row("기타")
            base.loc["자산부채증감"] = (
                    _row("매출채권 감소(증가)")
                    + _row("기타채권 감소(증가)")
                    + _row("기타자산 감소(증가)")
                    + _row("재고자산 감소(증가)")
                    + _row("매입채무 증가(감소)")
                    + _row("기타채무 증가(감소)")
                    + _row("퇴직급여부채증가(감소)")
            )
            base.loc["영업활동현금흐름"] = (
                    _row("당기순이익")
                    + _row("조정")
                    + _row("자산부채증감")
                    + _row("법인세납부")
                    + _row("이자의 수취")
                    + _row("이자의 지급")
            )
            base.loc["투자활동현금흐름"] = (
                    _row("유형자산취득")
                    + _row("무형자산취득")
                    + _row("기타 투자활동")
            )
            base.loc["재무활동현금흐름"] = _row("차입금의 증가(감소)")
            base.loc["현금성자산의 증감"] = (
                    _row("영업활동현금흐름")
                    + _row("투자활동현금흐름")
                    + _row("재무활동현금흐름")
            )
            # 계산 완료 후 메모 컬럼 추가
            base[col_memo_label] = ""


        # ====== 포맷 함수 ======
        def fmt_cell(x):
            if pd.isna(x) or x == "":
                return ""
            try:
                v = float(x)
            except Exception:
                return str(x)
            if v < 0:
                return f"-{abs(int(round(v))):,}"
            return f"{int(round(v)):,}"


        disp = base.copy()
        num_cols = [c for c in disp.columns if c != col_memo_label]
        for c in num_cols:
            disp[c] = disp[c].apply(fmt_cell)

        disp = disp.reset_index()

        cols = disp.columns.tolist()
        c_idx = {c: i for i, c in enumerate(cols)}

        # ====== 헤더 1줄 ======
        hdr = [''] * len(cols)
        hdr[c_idx['구분']] = '구분'
        hdr[c_idx[col_prev2_label]] = col_prev2_label
        hdr[c_idx[col_prev1_label]] = col_prev1_label
        hdr[c_idx[col_prev_label]] = col_prev_label
        hdr[c_idx[col_curr_label]] = col_curr_label
        hdr[c_idx[col_currsum_label]] = col_currsum_label
        hdr[c_idx[col_memo_label]] = col_memo_label

        hdr_df = pd.DataFrame([hdr], columns=cols)
        disp_vis = pd.concat([hdr_df, disp], ignore_index=True)

        # ====== 스타일 ======
        styles = [
            {'selector': 'thead', 'props': [('display', 'none')]},

            # 전체 셀 얇은 검정선
            {
                'selector': 'tbody td',
                'props': [('border', '1px solid black')]
            },

            # 헤더 1행
            {
                'selector': 'tbody tr:nth-child(1) td',
                'props': [
                    ('text-align', 'center'),
                    ('padding', '6px 8px'),
                    ('font-weight', '600'),
                    ('white-space', 'nowrap'),
                    ('border-top', '1px solid black'),
                    ('border-bottom', '1px solid black'),
                ]
            },

            # 구분 열 좌측 정렬
            {
                'selector': 'tbody tr td:nth-child(1)',
                'props': [
                    ('text-align', 'left'),
                    ('white-space', 'nowrap'),
                    ('padding-left', '8px'),
                    ('min-width', '200px'),
                ]
            },

            # 수치 열 우측 정렬
            {
                'selector': 'tbody tr td:nth-child(n+2)',
                'props': [
                    ('text-align', 'right'),
                    ('padding', '4px 8px'),
                    ('white-space', 'nowrap'),
                ]
            },

            # 메모 열 좌측 정렬
            {
                'selector': f'tbody tr td:nth-child({c_idx[col_memo_label] + 1})',
                'props': [
                    ('text-align', 'left'),
                    ('min-width', '180px'),
                ]
            },
        ]


        # ====== 음수 빨간색 처리 ======
        def red_if_negative(val):
            s = str(val).strip()
            if s.startswith("-") and s != "-":
                return "color: red;"
            return ""


        data_rows = disp_vis.index[1:]
        num_col_labels = [c for c in disp_vis.columns if c not in ["구분", col_memo_label]]

        applymap_rules = [
            (red_if_negative, (data_rows, num_col_labels))
        ]

        display_styled_df(
            disp_vis,
            styles=styles,
            already_flat=True,
            applymap_rules=applymap_rules,
        )

        display_memo('f_62', year, month)

    except Exception as e:
        st.error(f"남통 현금흐름표 생성 중 오류: {e}")

    st.divider()

    with t2:

        st.divider()

        st.markdown("<h4> 2) 현금흐름 태국법인</h4>", unsafe_allow_html=True)
        st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 백만원]</div>", unsafe_allow_html=True)

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
                df["월"] = df["월"].fillna("").astype(str).str.strip()
                df["실적"] = _to_num(df["실적"])

                # 태국만 사용
                df = df[df["구분1"] == "태국"].copy()

                df["__ord__"] = range(len(df))
                return df


            df0 = _clean_cf_thailand(raw)
            year = int(st.session_state["year"])
            month = int(st.session_state["month"])

            item_order = [
                "영업활동현금흐름",
                "당기순이익",
                "조정",
                "감가상각비",
                "대손상각비",
                "법인세비용",
                "기타",
                "자산부채증감",
                "매출채권 감소(증가)",
                "기타채권 감소(증가)",
                "재고자산 감소(증가)",
                "기타자산 감소(증가)",
                "매입채무 증가(감소)",
                "기타채무 증가(감소)",
                "기타부채 증가(감소)",
                "퇴직급여부채증가(감소)",
                "법인세납부",
                "이자의 수취",
                "이자의 지급",
                "투자활동현금흐름",
                "유형자산취득",
                "유형자산처분",
                "무형자산취득",
                "기타 투자활동",
                "재무활동현금흐름",
                "차입금의 증가(감소)",
                "현금성자산의 증감",
                "기초의 현금",
                "현금성자산의 환율변동",
                "기말의 현금",
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
            col_memo_label = "당월 현금흐름 주요변동내역(단위: THB)"

            sel_year = df0[
                (df0["연도"] == year)
                & (df0["구분2"].isin(item_order))
                ]

            if sel_year.empty:
                base = pd.DataFrame(
                    {
                        col_prev2_label: [np.nan] * len(index_labels),
                        col_prev1_label: [np.nan] * len(index_labels),
                        col_prev_label: [np.nan] * len(index_labels),
                        col_curr_label: [np.nan] * len(index_labels),
                        col_currsum_label: [np.nan] * len(index_labels),
                        col_memo_label: [""] * len(index_labels),
                    },
                    index=pd.Index(index_labels, name="구분"),
                )
            else:
                def _sum_item_year(name: str, nth: int, y: int) -> float:
                    sub = df0[
                        (df0["연도"] == y)
                        & (df0["구분2"] == name)
                        ].sort_values("__ord__", kind="stable")
                    if len(sub) >= nth:
                        return float(sub.iloc[nth - 1]["실적"])
                    return 0.0


                def _block_year(y: int):
                    return [_sum_item_year(nm, nth, y) for (nm, nth) in order_with_n]


                def _sum_item_kind(name: str, nth: int, y: int, kind: str) -> float:
                    sub = df0[
                        (df0["연도"] == y)
                        & (df0["월"] == kind)
                        & (df0["구분2"] == name)
                        ].sort_values("__ord__", kind="stable")
                    if len(sub) >= nth:
                        return float(sub.iloc[nth - 1]["실적"])
                    return 0.0


                def _block_kind(y: int, kind: str):
                    return [_sum_item_kind(nm, nth, y, kind) for (nm, nth) in order_with_n]


                vals_prev2 = _block_year(year - 2)
                vals_prev1 = _block_year(year - 1)
                vals_prev = _block_kind(year, "전월누적")
                vals_curr = _block_kind(year, "당월")
                vals_ytd = _block_kind(year, "당월누적")

                # 수치 컬럼만으로 base 구성 (메모 컬럼 나중에 추가)
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
                    if label in base.index:
                        return base.loc[label].astype(float)
                    else:
                        return pd.Series(0.0, index=base.columns, dtype=float)


                base.loc["조정"] = (
                        _row("감가상각비")
                        + _row("대손상각비")
                        + _row("법인세비용")
                        + _row("기타")
                )
                base.loc["자산부채증감"] = (
                        _row("매출채권 감소(증가)")
                        + _row("기타채권 감소(증가)")
                        + _row("재고자산 감소(증가)")
                        + _row("기타자산 감소(증가)")
                        + _row("매입채무 증가(감소)")
                        + _row("기타채무 증가(감소)")
                        + _row("기타부채 증가(감소)")
                        + _row("퇴직급여부채증가(감소)")
                )
                base.loc["영업활동현금흐름"] = (
                        _row("당기순이익")
                        + _row("조정")
                        + _row("자산부채증감")
                        + _row("법인세납부")
                        + _row("이자의 수취")
                        + _row("이자의 지급")
                )
                base.loc["투자활동현금흐름"] = (
                        _row("유형자산취득")
                        + _row("유형자산처분")
                        + _row("무형자산취득")
                        + _row("기타 투자활동")
                )
                base.loc["재무활동현금흐름"] = _row("차입금의 증가(감소)")
                base.loc["현금성자산의 증감"] = (
                        _row("영업활동현금흐름")
                        + _row("투자활동현금흐름")
                        + _row("재무활동현금흐름")
                )
                # 계산 완료 후 메모 컬럼 추가
                base[col_memo_label] = ""


            # ====== 포맷 함수 ======
            def fmt_cell(x):
                if pd.isna(x) or x == "":
                    return ""
                try:
                    v = float(x)
                except Exception:
                    return str(x)
                if v < 0:
                    return f"-{abs(int(round(v))):,}"
                return f"{int(round(v)):,}"


            disp = base.copy()
            num_cols = [c for c in disp.columns if c != col_memo_label]
            for c in num_cols:
                disp[c] = disp[c].apply(fmt_cell)

            disp = disp.reset_index()

            cols = disp.columns.tolist()
            c_idx = {c: i for i, c in enumerate(cols)}

            # ====== 헤더 1줄 ======
            hdr = [''] * len(cols)
            hdr[c_idx['구분']] = '구분'
            hdr[c_idx[col_prev2_label]] = col_prev2_label
            hdr[c_idx[col_prev1_label]] = col_prev1_label
            hdr[c_idx[col_prev_label]] = col_prev_label
            hdr[c_idx[col_curr_label]] = col_curr_label
            hdr[c_idx[col_currsum_label]] = col_currsum_label
            hdr[c_idx[col_memo_label]] = col_memo_label

            hdr_df = pd.DataFrame([hdr], columns=cols)
            disp_vis = pd.concat([hdr_df, disp], ignore_index=True)

            # ====== 스타일 ======
            styles = [
                {'selector': 'thead', 'props': [('display', 'none')]},
                {
                    'selector': 'tbody td',
                    'props': [('border', '1px solid black')]
                },
                {
                    'selector': 'tbody tr:nth-child(1) td',
                    'props': [
                        ('text-align', 'center'),
                        ('padding', '6px 8px'),
                        ('font-weight', '600'),
                        ('white-space', 'nowrap'),
                        ('border-top', '1px solid black'),
                        ('border-bottom', '1px solid black'),
                    ]
                },
                {
                    'selector': 'tbody tr td:nth-child(1)',
                    'props': [
                        ('text-align', 'left'),
                        ('white-space', 'nowrap'),
                        ('padding-left', '8px'),
                        ('min-width', '200px'),
                    ]
                },
                {
                    'selector': 'tbody tr td:nth-child(n+2)',
                    'props': [
                        ('text-align', 'right'),
                        ('padding', '4px 8px'),
                        ('white-space', 'nowrap'),
                    ]
                },
                {
                    'selector': f'tbody tr td:nth-child({c_idx[col_memo_label] + 1})',
                    'props': [
                        ('text-align', 'left'),
                        ('min-width', '180px'),
                    ]
                },
            ]


            # ====== 음수 빨간색 처리 ======
            def red_if_negative(val):
                s = str(val).strip()
                if s.startswith("-") and s != "-":
                    return "color: red;"
                return ""


            data_rows = disp_vis.index[1:]
            num_col_labels = [c for c in disp_vis.columns if c not in ["구분", col_memo_label]]

            applymap_rules = [
                (red_if_negative, (data_rows, num_col_labels))
            ]

            display_styled_df(
                disp_vis,
                styles=styles,
                already_flat=True,
                applymap_rules=applymap_rules,
            )

            display_memo('f_64', year, month)

        except Exception as e:
            st.error(f"태국 현금흐름표 생성 중 오류: {e}")

    st.divider()

with t3:
    st.markdown("<h4> 1) 재무상태표 중국법인</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 백만원]</div>", unsafe_allow_html=True)

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
        yy_m1   = f"{(year_int - 1) % 100:02d}"
        yy_m2   = f"{(year_int - 2) % 100:02d}"
        yy_m3   = f"{(year_int - 3) % 100:02d}"

        col_yend_m3 = f"'{yy_m3}년말"
        col_yend_m2 = f"'{yy_m2}년말"
        col_yend_m1 = f"'{yy_m1}년말"
        col_prev    = f"'{yy_curr} 전월"
        col_curr    = "당월"
        col_diff    = "전월비"

        hdr = [''] * len(cols)
        hdr[c_idx['구분']] = '[중국]'

        if col_yend_m3 in c_idx:
            hdr[c_idx[col_yend_m3]] = f"'{yy_m3}년말"
        if col_yend_m2 in c_idx:
            hdr[c_idx[col_yend_m2]] = f"'{yy_m2}년말"
        if col_yend_m1 in c_idx:
            hdr[c_idx[col_yend_m1]] = f"'{yy_m1}년말"

        prev_year_int = year_int
        if used_m is not None and prev_m is not None and prev_m > used_m:
            prev_year_int = year_int - 1
        yy_prev_hdr = f"{prev_year_int % 100:02d}"

        if col_prev in c_idx:
            hdr[c_idx[col_prev]] = f"'{yy_prev_hdr}년 {prev_m}월"
        if col_curr in c_idx:
            hdr[c_idx[col_curr]] = f"'{yy_curr}년 {used_m}월"
        if col_diff in c_idx:
            hdr[c_idx[col_diff]] = "전월비"

        hdr_df   = pd.DataFrame([hdr], columns=cols)
        disp_vis = pd.concat([hdr_df, disp], ignore_index=True)

        styles = [
            {'selector': 'thead', 'props': [('display', 'none')]},
            {
                'selector': 'tbody td',
                'props': [('border', '1px solid black')]
            },
            {
                'selector': 'tbody tr:nth-child(1) td',
                'props': [
                    ('text-align', 'center'),
                    ('padding', '6px 8px'),
                    ('font-weight', '600'),
                    ('white-space', 'nowrap'),
                    ('border-top', '1px solid black'),
                    ('border-bottom', '1px solid black'),
                ]
            },
            {
                'selector': 'tbody tr td:nth-child(1)',
                'props': [
                    ('text-align', 'left'),
                    ('white-space', 'nowrap'),
                    ('padding-left', '8px'),
                    ('min-width', '180px'),
                ]
            },
            {
                'selector': 'tbody tr td:nth-child(n+2)',
                'props': [
                    ('text-align', 'right'),
                    ('padding', '4px 8px'),
                    ('white-space', 'nowrap'),
                ]
            },
        ]

        def red_if_negative(val):
            s = str(val).strip()
            if s.startswith("-") and s != "-":
                return "color: red;"
            return ""

        data_rows = disp_vis.index[1:]
        num_col_labels = [c for c in disp_vis.columns if c != "구분"]

        applymap_rules = [
            (red_if_negative, (data_rows, num_col_labels))
        ]

        display_styled_df(
            disp_vis,
            styles=styles,
            already_flat=True,
            applymap_rules=applymap_rules,
        )

        display_memo('f_65', year, month)

    except Exception as e:
        st.error(f"남통 재무상태표 생성 중 오류: {e}")

    st.divider()

    st.markdown("<h4> 2) 재무상태표 태국법인</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 백만원]</div>", unsafe_allow_html=True)

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
        yy_m1   = f"{(year_int - 1) % 100:02d}"
        yy_m2   = f"{(year_int - 2) % 100:02d}"
        yy_m3   = f"{(year_int - 3) % 100:02d}"

        col_yend_m3 = f"'{yy_m3}년말"
        col_yend_m2 = f"'{yy_m2}년말"
        col_yend_m1 = f"'{yy_m1}년말"
        col_prev    = f"'{yy_curr} 전월"
        col_curr    = "당월"
        col_diff    = "전월비"

        hdr = [''] * len(cols)
        hdr[c_idx['구분']] = '[태국]'

        if col_yend_m3 in c_idx:
            hdr[c_idx[col_yend_m3]] = f"'{yy_m3}년말"
        if col_yend_m2 in c_idx:
            hdr[c_idx[col_yend_m2]] = f"'{yy_m2}년말"
        if col_yend_m1 in c_idx:
            hdr[c_idx[col_yend_m1]] = f"'{yy_m1}년말"

        prev_year_int = year_int
        if used_m is not None and prev_m is not None and prev_m > used_m:
            prev_year_int = year_int - 1
        yy_prev_hdr = f"{prev_year_int % 100:02d}"

        if col_prev in c_idx:
            hdr[c_idx[col_prev]] = f"'{yy_prev_hdr}년 {prev_m}월"
        if col_curr in c_idx:
            hdr[c_idx[col_curr]] = f"'{yy_curr}년 {used_m}월"
        if col_diff in c_idx:
            hdr[c_idx[col_diff]] = "전월비"

        hdr_df   = pd.DataFrame([hdr], columns=cols)
        disp_vis = pd.concat([hdr_df, disp], ignore_index=True)

        styles = [
            {'selector': 'thead', 'props': [('display', 'none')]},
            {
                'selector': 'tbody td',
                'props': [('border', '1px solid black')]
            },
            {
                'selector': 'tbody tr:nth-child(1) td',
                'props': [
                    ('text-align', 'center'),
                    ('padding', '6px 8px'),
                    ('font-weight', '600'),
                    ('white-space', 'nowrap'),
                    ('border-top', '1px solid black'),
                    ('border-bottom', '1px solid black'),
                ]
            },
            {
                'selector': 'tbody tr td:nth-child(1)',
                'props': [
                    ('text-align', 'left'),
                    ('white-space', 'nowrap'),
                    ('padding-left', '8px'),
                    ('min-width', '180px'),
                ]
            },
            {
                'selector': 'tbody tr td:nth-child(n+2)',
                'props': [
                    ('text-align', 'right'),
                    ('padding', '4px 8px'),
                    ('white-space', 'nowrap'),
                ]
            },
        ]

        def red_if_negative(val):
            s = str(val).strip()
            if s.startswith("-") and s != "-":
                return "color: red;"
            return ""

        data_rows = disp_vis.index[1:]
        num_col_labels = [c for c in disp_vis.columns if c != "구분"]

        applymap_rules = [
            (red_if_negative, (data_rows, num_col_labels))
        ]

        display_styled_df(
            disp_vis,
            styles=styles,
            already_flat=True,
            applymap_rules=applymap_rules,
        )

        display_memo('f_67', year, month)

    except Exception as e:
        st.error(f"태국 재무상태표 생성 중 오류: {e}")

#판매구성
with t4:

    st.markdown("<h4> 1) 등급별 판매현황</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 톤]</div>", unsafe_allow_html=True)

    try:
        file_name = st.secrets["sheets"]["f_68"]
        df_src = pd.read_csv(file_name, dtype=str)

        disp = modules.build_grade_sales_table_68(df_src, year, month)
        body = disp.copy()

        # =========================
        # 1) 연도/월 컬럼 정보 수집
        # =========================
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

        # =========================
        # 2) 가짜 헤더 hdr 1줄 구성
        # =========================
        hdr = {col: "" for col in body.columns}

        if "구분2" in hdr:
            hdr["구분2"] = "구분"

        for y_col in prev_year_labels:
            if y_col in hdr:
                hdr[y_col] = f"'{y_col}"

        for col, y, m in month_defs:
            yy_col = str(y)[-2:]
            hdr[col] = f"'{yy_col}년{m}월"

        # ★ 마지막 두 컬럼: 선택연도.월 포함
        for c in diff_cols:
            if c in hdr:
                hdr[c] = f"'{yy}.{month}월 전월比"
        for c in pct_cols:
            if c in hdr:
                hdr[c] = f"'{yy}.{month}월 전월比 %"

        hdr_df = pd.DataFrame([hdr])
        body = pd.concat([hdr_df, body], ignore_index=True)


        # =========================
        # 3) 숫자 포맷
        # =========================
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

        # =========================
        # 4) 스타일
        # =========================
        styles = [
            {"selector": "thead",
             "props": [("display", "none")]},

            {"selector": "tbody td",
             "props": [("border", "1px solid black")]},

            {"selector": "tbody tr:nth-child(1) td",
             "props": [("text-align", "center"),
                       ("font-weight", "700"),
                       ("white-space", "nowrap"),
                       ("border-top", "1px solid black"),
                       ("border-bottom", "1px solid black")]},

            {"selector": "tbody tr td:nth-child(1)",
             "props": [("text-align", "left"),
                       ("white-space", "nowrap"),
                       ("padding-left", "8px"),
                       ("min-width", "120px")]},

            {"selector": "tbody tr td:nth-child(n+2)",
             "props": [("text-align", "right"),
                       ("padding", "4px 8px"),
                       ("white-space", "nowrap")]},

            {"selector": "tbody tr:nth-child(9) td, tbody tr:nth-child(17) td",
             "props": [("font-weight", "700")]},
        ]

        display_styled_df(body, styles=styles, already_flat=True)
        display_memo('f_68', year, month)

    except Exception as e:
        st.error(f"등급별 판매현황 표 생성 오류: {e}")

    st.divider()

    st.markdown("<h4> 2) CHQ 열처리 제품 판매현황</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 톤]</div>", unsafe_allow_html=True)

    try:
        file_name = st.secrets["sheets"]["f_69_70_71"]
        df_src = pd.read_csv(file_name, dtype=str)

        disp = modules.build_chq_f69(df_src, year, month)
        body = disp.copy()

        # =========================
        # 1) 연도/월 컬럼 정보 수집
        # =========================
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

        # =========================
        # 2) 가짜 헤더 hdr 1줄 구성
        # =========================
        hdr = {col: "" for col in body.columns}

        if "구분2" in hdr:
            hdr["구분2"] = "구분"

        for y_col in prev_year_labels:
            if y_col in hdr:
                hdr[y_col] = f"'{y_col}"

        for col, y, m in month_defs:
            yy_col = str(y)[-2:]
            hdr[col] = f"'{yy_col}년{m}월"

        # ★ 마지막 두 컬럼: 선택연도.월 포함
        for c in diff_cols:
            if c in hdr:
                hdr[c] = f"'{yy}.{month}월 전월比"
        for c in pct_cols:
            if c in hdr:
                hdr[c] = f"'{yy}.{month}월 전월比 %"

        hdr_df = pd.DataFrame([hdr])
        body = pd.concat([hdr_df, body], ignore_index=True)


        # =========================
        # 3) 숫자 포맷
        # =========================
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

        # =========================
        # 4) 스타일
        # =========================
        styles = [
            {"selector": "thead",
             "props": [("display", "none")]},

            {"selector": "tbody td",
             "props": [("border", "1px solid black")]},

            {"selector": "tbody tr:nth-child(1) td",
             "props": [("text-align", "center"),
                       ("font-weight", "700"),
                       ("white-space", "nowrap"),
                       ("border-top", "1px solid black"),
                       ("border-bottom", "1px solid black")]},

            {"selector": "tbody tr td:nth-child(1)",
             "props": [("text-align", "left"),
                       ("white-space", "nowrap"),
                       ("padding-left", "8px"),
                       ("min-width", "120px")]},

            {"selector": "tbody tr td:nth-child(n+2)",
             "props": [("text-align", "right"),
                       ("padding", "4px 8px"),
                       ("white-space", "nowrap")]},

            {"selector": "tbody tr:nth-child(5) td, tbody tr:nth-child(9) td",
             "props": [("font-weight", "700")]},
        ]

        display_styled_df(body, styles=styles, already_flat=True)
        display_memo('f_69', year, month)

    except Exception as e:
        st.error(f"CHQ 열처리 제품 판매현황 표 생성 오류: {e}")

    st.divider()

    st.markdown("<h4> 3) 비가공품 판매현황</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 톤]</div>", unsafe_allow_html=True)

    try:
        file_name = st.secrets["sheets"]["f_69_70_71"]
        df_src = pd.read_csv(file_name, dtype=str)

        disp = modules.build_f70(df_src, year, month)
        body = disp.copy()

        # =========================
        # 1) 연도/월 컬럼 정보 수집
        # =========================
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

        # =========================
        # 2) 가짜 헤더 hdr 1줄 구성
        # =========================
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
                hdr[c] = f"'{yy}.{month}월 전월比"
        for c in pct_cols:
            if c in hdr:
                hdr[c] = f"'{yy}.{month}월 전월比 %"

        hdr_df = pd.DataFrame([hdr])
        body = pd.concat([hdr_df, body], ignore_index=True)


        # =========================
        # 3) 숫자 포맷
        # =========================
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

        # =========================
        # 4) 스타일
        # =========================
        # 행 구조:
        #   행 1    : hdr
        #   행 2~4  : 남통 (가공, 비가공, %)
        #   행 5    : 남통 합계
        #   행 6~8  : 태국 (가공, 비가공, %)
        #   행 9    : 태국 합계

        styles = [
            {"selector": "thead",
             "props": [("display", "none")]},

            {"selector": "tbody td",
             "props": [("border", "1px solid black")]},

            {"selector": "tbody tr:nth-child(1) td",
             "props": [("text-align", "center"),
                       ("font-weight", "700"),
                       ("white-space", "nowrap"),
                       ("border-top", "1px solid black"),
                       ("border-bottom", "1px solid black")]},

            {"selector": "tbody tr td:nth-child(1)",
             "props": [("text-align", "left"),
                       ("white-space", "nowrap"),
                       ("padding-left", "8px"),
                       ("min-width", "120px")]},

            {"selector": "tbody tr td:nth-child(n+2)",
             "props": [("text-align", "right"),
                       ("padding", "4px 8px"),
                       ("white-space", "nowrap")]},

            # 합계행(남통/태국) 볼드
            {"selector": "tbody tr:nth-child(5) td, tbody tr:nth-child(9) td",
             "props": [("font-weight", "700")]},
        ]

        display_styled_df(body, styles=styles, already_flat=True)
        display_memo('f_70', year, month)

    except Exception as e:
        st.error(f"비가공품 판매현황 표 생성 오류: {e}")

    st.divider()

    st.markdown("<h4> 4) 제품/임가공 판매현황</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 톤]</div>", unsafe_allow_html=True)

    try:
        file_name = st.secrets["sheets"]["f_69_70_71"]
        df_src = pd.read_csv(file_name, dtype=str)

        disp = modules.build_f71(df_src, year, month)
        body = disp.copy()

        # =========================
        # 1) 연도/월 컬럼 정보 수집
        # =========================
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

        # =========================
        # 2) 가짜 헤더 hdr 1줄 구성
        # =========================
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
                hdr[c] = f"'{yy}.{month}월 전월比"
        for c in pct_cols:
            if c in hdr:
                hdr[c] = f"'{yy}.{month}월 전월比 %"

        hdr_df = pd.DataFrame([hdr])
        body = pd.concat([hdr_df, body], ignore_index=True)


        # =========================
        # 3) 숫자 포맷
        # =========================
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

        # =========================
        # 4) 스타일
        # =========================
        # 행 구조:
        #   행 1    : hdr
        #   행 2~4  : 남통 (제품, 임가공, %)
        #   행 5    : 남통 합계
        #   행 6~8  : 태국 (제품, 임가공, %)
        #   행 9    : 태국 합계

        styles = [
            {"selector": "thead",
             "props": [("display", "none")]},

            {"selector": "tbody td",
             "props": [("border", "1px solid black")]},

            {"selector": "tbody tr:nth-child(1) td",
             "props": [("text-align", "center"),
                       ("font-weight", "700"),
                       ("white-space", "nowrap"),
                       ("border-top", "1px solid black"),
                       ("border-bottom", "1px solid black")]},

            {"selector": "tbody tr td:nth-child(1)",
             "props": [("text-align", "left"),
                       ("white-space", "nowrap"),
                       ("padding-left", "8px"),
                       ("min-width", "120px")]},

            {"selector": "tbody tr td:nth-child(n+2)",
             "props": [("text-align", "right"),
                       ("padding", "4px 8px"),
                       ("white-space", "nowrap")]},

            # 합계행(남통/태국) 볼드
            {"selector": "tbody tr:nth-child(5) td, tbody tr:nth-child(9) td",
             "props": [("font-weight", "700")]},
        ]

        display_styled_df(body, styles=styles, already_flat=True)
        display_memo('f_71', year, month)

    except Exception as e:
        st.error(f"제품/임가공 판매현황 표 생성 오류: {e}")

    st.divider()

with t6:

    st.markdown("<h4> 1) 재고자산 현황 남통법인</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 톤, 백만원, %]</div>",
                unsafe_allow_html=True)

    try:
        file_name = st.secrets["sheets"]["f_75_76_77"]
        raw = pd.read_csv(file_name, dtype=str)

        inv = modules.create_inv_table_from_company(
            year=int(st.session_state['year']),
            month=int(st.session_state['month']),
            data=raw,
            company_name='남통',
        )

        # 2) 표시용 복사 & 인덱스 풀기
        disp = inv.copy().reset_index()


        # ★ 소계행의 구분2 값을 label로 가져온 뒤,
        #   소계행을 구분2 이름으로 대체 (구분3을 구분2 값으로 교체)
        def relabel(row):
            b = str(row['구분2']).strip() if pd.notna(row['구분2']) else ''
            s = str(row['구분3']).strip() if pd.notna(row['구분3']) else ''
            # 소계행: 구분3이 '소계' → 구분2 카테고리명으로 표시
            if s == '소계':
                return b if b else '소계'
            # 세부항목: 구분3 표시
            if s and s != 'nan':
                return s
            # 총재고
            if b and b != 'nan':
                return b
            return ''


        disp['구분'] = disp.apply(relabel, axis=1)
        disp = disp[disp['구분'].str.strip() != ''].copy()

        # 구분2, 구분3 열 제거 후 구분 열을 앞으로
        disp = disp.drop(columns=['구분2', '구분3'])
        cols_order = ['구분'] + [c for c in disp.columns if c != '구분']
        disp = disp[cols_order]


        # 3) 숫자 포맷 함수
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


        # 4) 컬럼별 포맷 적용
        for c in disp.columns:
            if c == '구분':
                continue
            if c == '증감률':
                disp[c] = disp[c].apply(fmt_rate)
            else:
                disp[c] = disp[c].apply(fmt_amt)

        # 5) attrs에서 연월 정보 추출
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

        # =========================
        # 6) 헤더 1줄 구성
        # =========================
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

        # =========================
        # 7) 스타일
        # =========================
        # 행 구조 (hdr 1줄 포함):
        #   행 1      : hdr
        #   행 2~4    : 원재료 세부 (POSCO, LOCAL, 기타)
        #   행 5      : 원재료 합계
        #   행 6~8    : 재공 세부 (POSCO, LOCAL, 기타)
        #   행 9      : 재공 합계
        #   행 10~12  : 제품 세부 (POSCO, LOCAL, 기타)
        #   행 13     : 제품 합계
        #   행 14     : 총재고

        styles = [
            {'selector': 'thead', 'props': [('display', 'none')]},

            {'selector': 'tbody td',
             'props': [('border', '1px solid black')]},

            # hdr 행 (1행)
            {'selector': 'tbody tr:nth-child(1) td',
             'props': [('text-align', 'center'),
                       ('font-weight', '700'),
                       ('white-space', 'nowrap'),
                       ('border-top', '1px solid black'),
                       ('border-bottom', '1px solid black')]},

            # 구분 열 (1열) 왼쪽 정렬
            {'selector': 'tbody tr:nth-child(n+2) td:nth-child(1)',
             'props': [('text-align', 'left'),
                       ('white-space', 'nowrap'),
                       ('padding-left', '8px'),
                       ('min-width', '120px')]},

            # 숫자 열 오른쪽 정렬
            {'selector': 'tbody tr:nth-child(n+2) td:nth-child(n+2)',
             'props': [('text-align', 'right'),
                       ('padding', '4px 8px'),
                       ('white-space', 'nowrap')]},

            # 합계행 볼드 (원재료/재공/제품/총재고)
            {
                'selector': 'tbody tr:nth-child(5) td, tbody tr:nth-child(9) td, tbody tr:nth-child(13) td, tbody tr:nth-child(14) td',
                'props': [('font-weight', '700')]},
        ]

        display_styled_df(
            disp_vis,
            styles=styles,
            already_flat=True,
        )
        display_memo('f_75', year, month)

    except Exception as e:
        st.error(f"재고자산 현황 남통법인 표 생성 중 오류: {e}")

    st.divider()

    st.markdown("<h4> 2) 재고자산 현황 태국법인</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 톤, 백만원, %]</div>",
                unsafe_allow_html=True)

    try:
        file_name = st.secrets["sheets"]["f_75_76_77"]
        raw = pd.read_csv(file_name, dtype=str)

        inv = modules.create_inv_table_from_company(
            year=int(st.session_state['year']),
            month=int(st.session_state['month']),
            data=raw,
            company_name='태국',
        )

        # 2) 표시용 복사 & 인덱스 풀기
        disp = inv.copy().reset_index()


        # ★ 소계행 → 원재료/재공/제품으로 이름 변경, 1열로 합치기
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


        # 3) 숫자 포맷 함수
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


        # 4) 컬럼별 포맷 적용
        for c in disp.columns:
            if c == '구분':
                continue
            if c == '증감률':
                disp[c] = disp[c].apply(fmt_rate)
            else:
                disp[c] = disp[c].apply(fmt_amt)

        # 5) attrs에서 연월 정보 추출
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

        # =========================
        # 6) 헤더 1줄 구성
        # =========================
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

        # =========================
        # 7) 스타일
        # =========================
        styles = [
            {'selector': 'thead', 'props': [('display', 'none')]},

            {'selector': 'tbody td',
             'props': [('border', '1px solid black')]},

            {'selector': 'tbody tr:nth-child(1) td',
             'props': [('text-align', 'center'),
                       ('font-weight', '700'),
                       ('white-space', 'nowrap'),
                       ('border-top', '1px solid black'),
                       ('border-bottom', '1px solid black')]},

            {'selector': 'tbody tr:nth-child(n+2) td:nth-child(1)',
             'props': [('text-align', 'left'),
                       ('white-space', 'nowrap'),
                       ('padding-left', '8px'),
                       ('min-width', '120px')]},

            {'selector': 'tbody tr:nth-child(n+2) td:nth-child(n+2)',
             'props': [('text-align', 'right'),
                       ('padding', '4px 8px'),
                       ('white-space', 'nowrap')]},

            # 합계행 볼드 (원재료/재공/제품/총재고)
            {
                'selector': 'tbody tr:nth-child(5) td, tbody tr:nth-child(9) td, tbody tr:nth-child(13) td, tbody tr:nth-child(14) td',
                'props': [('font-weight', '700')]},
        ]

        display_styled_df(
            disp_vis,
            styles=styles,
            already_flat=True,
        )
        display_memo('f_76', year, month)

    except Exception as e:
        st.error(f"재고자산 현황 태국법인 표 생성 중 오류: {e}")


    st.divider()

    st.markdown("<h4> 3) 부적합 및 장기재고 현황 남통법인</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 톤, 백만원, %]</div>",
                unsafe_allow_html=True)

    try:
        file_name = st.secrets["sheets"]["f_78_79_80"]
        raw = pd.read_csv(file_name, dtype=str)

        inv = modules.create_defect_longinv_table_from_company(
            year=int(st.session_state['year']),
            month=int(st.session_state['month']),
            data=raw,
            company_name='남통',
        )

        # 2) 표시용 복사 & 인덱스 풀기
        disp = inv.copy().reset_index()


        # ★ 구분2 + 구분3 합쳐서 구분 1열로
        def relabel(row):
            b = str(row['구분2']).strip() if pd.notna(row['구분2']) else ''
            s = str(row['구분3']).strip() if pd.notna(row['구분3']) else ''
            # 소계행: 구분3이 비어있고 구분2만 있는 경우
            if b and b != 'nan' and (not s or s == 'nan'):
                return b
            # 세부항목
            if s and s != 'nan':
                return s
            return ''


        disp['구분'] = disp.apply(relabel, axis=1)
        disp = disp[disp['구분'].str.strip() != ''].copy()

        disp = disp.drop(columns=['구분2', '구분3'])
        cols_order = ['구분'] + [c for c in disp.columns if c != '구분']
        disp = disp[cols_order]


        # 3) 숫자 포맷 함수
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


        # 4) 컬럼별 포맷 적용
        for c in disp.columns:
            if c == '구분':
                continue
            if c == '증감률':
                disp[c] = disp[c].apply(fmt_rate)
            else:
                disp[c] = disp[c].apply(fmt_amt)

        # 5) attrs에서 연월 정보 추출
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

        m1_year = used_y
        m2_year = used_y if prev_m <= used_m else used_y - 1
        m3_year = m2_year if prev2_m <= prev_m else m2_year - 1

        # =========================
        # 6) 헤더 1줄 구성
        # =========================
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

        # =========================
        # 7) 스타일
        # =========================
        # 행 구조 (hdr 1줄 포함):
        #   행 1      : hdr
        #   행 2      : 재공
        #   행 3~7    : B급, C급, D급, D2급, X급
        #   행 8      : 제품
        #   행 9      : 부적합재고 소계
        #   행 10~12  : 원재료, 재공, 제품
        #   행 13     : 장기재고 소계

        styles = [
            {'selector': 'thead', 'props': [('display', 'none')]},

            {'selector': 'tbody td',
             'props': [('border', '1px solid black')]},

            # hdr 행 (1행)
            {'selector': 'tbody tr:nth-child(1) td',
             'props': [('text-align', 'center'),
                       ('font-weight', '700'),
                       ('white-space', 'nowrap'),
                       ('border-top', '1px solid black'),
                       ('border-bottom', '1px solid black')]},

            # 구분 열 (1열) 왼쪽 정렬
            {'selector': 'tbody tr:nth-child(n+2) td:nth-child(1)',
             'props': [('text-align', 'left'),
                       ('white-space', 'nowrap'),
                       ('padding-left', '8px'),
                       ('min-width', '120px')]},

            # 숫자 열 오른쪽 정렬
            {'selector': 'tbody tr:nth-child(n+2) td:nth-child(n+2)',
             'props': [('text-align', 'right'),
                       ('padding', '4px 8px'),
                       ('white-space', 'nowrap')]},

            # 소계행 볼드 (부적합재고 소계 / 장기재고 소계)
            {'selector': 'tbody tr:nth-child(9) td, tbody tr:nth-child(13) td',
             'props': [('font-weight', '700')]},
        ]

        display_styled_df(
            disp_vis,
            styles=styles,
            already_flat=True,
        )
        display_memo('f_78', year, month)

    except Exception as e:
        st.error(f"부적합 및 장기재고 현황 남통법인 표 생성 중 오류: {e}")

    st.divider()

    st.markdown("<h4> 4) 부적합 및 장기재고 현황 태국법인</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 톤, 백만원, %]</div>",
                unsafe_allow_html=True)

    try:
        file_name = st.secrets["sheets"]["f_78_79_80"]
        raw = pd.read_csv(file_name, dtype=str)

        inv = modules.create_defect_longinv_table_from_company(
            year=int(st.session_state['year']),
            month=int(st.session_state['month']),
            data=raw,
            company_name='태국',
        )

        # 2) 표시용 복사 & 인덱스 풀기
        disp = inv.copy().reset_index()


        # ★ 구분2 + 구분3 합쳐서 구분 1열로
        def relabel(row):
            b = str(row['구분2']).strip() if pd.notna(row['구분2']) else ''
            s = str(row['구분3']).strip() if pd.notna(row['구분3']) else ''
            # 소계행: 구분3이 비어있고 구분2만 있는 경우
            if b and b != 'nan' and (not s or s == 'nan'):
                return b
            # 세부항목
            if s and s != 'nan':
                return s
            return ''


        disp['구분'] = disp.apply(relabel, axis=1)
        disp = disp[disp['구분'].str.strip() != ''].copy()

        disp = disp.drop(columns=['구분2', '구분3'])
        cols_order = ['구분'] + [c for c in disp.columns if c != '구분']
        disp = disp[cols_order]


        # 3) 숫자 포맷 함수
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


        # 4) 컬럼별 포맷 적용
        for c in disp.columns:
            if c == '구분':
                continue
            if c == '증감률':
                disp[c] = disp[c].apply(fmt_rate)
            else:
                disp[c] = disp[c].apply(fmt_amt)

        # 5) attrs에서 연월 정보 추출
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

        m1_year = used_y
        m2_year = used_y if prev_m <= used_m else used_y - 1
        m3_year = m2_year if prev2_m <= prev_m else m2_year - 1

        # =========================
        # 6) 헤더 1줄 구성
        # =========================
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

        # =========================
        # 7) 스타일
        # =========================
        # 행 구조 (hdr 1줄 포함):
        #   행 1      : hdr
        #   행 2      : 재공
        #   행 3~7    : B급, C급, D급, D2급, X급
        #   행 8      : 제품
        #   행 9      : 부적합재고 소계
        #   행 10~12  : 원재료, 재공, 제품
        #   행 13     : 장기재고 소계

        styles = [
            {'selector': 'thead', 'props': [('display', 'none')]},

            {'selector': 'tbody td',
             'props': [('border', '1px solid black')]},

            # hdr 행 (1행)
            {'selector': 'tbody tr:nth-child(1) td',
             'props': [('text-align', 'center'),
                       ('font-weight', '700'),
                       ('white-space', 'nowrap'),
                       ('border-top', '1px solid black'),
                       ('border-bottom', '1px solid black')]},

            # 구분 열 (1열) 왼쪽 정렬
            {'selector': 'tbody tr:nth-child(n+2) td:nth-child(1)',
             'props': [('text-align', 'left'),
                       ('white-space', 'nowrap'),
                       ('padding-left', '8px'),
                       ('min-width', '120px')]},

            # 숫자 열 오른쪽 정렬
            {'selector': 'tbody tr:nth-child(n+2) td:nth-child(n+2)',
             'props': [('text-align', 'right'),
                       ('padding', '4px 8px'),
                       ('white-space', 'nowrap')]},

            # 소계행 볼드 (부적합재고 소계 / 장기재고 소계)
            {'selector': 'tbody tr:nth-child(9) td, tbody tr:nth-child(13) td',
             'props': [('font-weight', '700')]},
        ]

        display_styled_df(
            disp_vis,
            styles=styles,
            already_flat=True,
        )
        display_memo('f_79', year, month)

    except Exception as e:
        st.error(f"부적합 및 장기재고 현황 태국법인 표 생성 중 오류: {e}")

    st.divider()

    st.markdown("<h4> 5) 연령별 재고 현황 남통법인</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 톤, 백만원, %]</div>",
                unsafe_allow_html=True)

    try:
        file_name = st.secrets["sheets"]["f_81_82_83"]
        raw = pd.read_csv(file_name, dtype=str)

        inv = modules.create_age_table_from_company(
            year=int(st.session_state['year']),
            month=int(st.session_state['month']),
            data=raw,
            company_name='남통',
        )

        # 2) 표시용 복사 & 인덱스 풀기
        disp = inv.copy().reset_index()


        # ★ 소계행 → 원재료/재공/제품으로 이름 변경, 1열로 합치기
        def relabel(row):
            b = str(row['구분2']).strip() if pd.notna(row['구분2']) else ''
            s = str(row['구분3']).strip() if pd.notna(row['구분3']) else ''
            # 소계행: 구분3이 '소계' → 구분2 카테고리명으로 표시
            if s == '소계':
                return b if b else '소계'
            # 세부항목
            if s and s != 'nan':
                return s
            # 합계행 (구분2만 있고 구분3 없음)
            if b and b != 'nan':
                return b
            return ''


        disp['구분'] = disp.apply(relabel, axis=1)
        disp = disp[disp['구분'].str.strip() != ''].copy()

        disp = disp.drop(columns=['구분2', '구분3'])
        cols_order = ['구분'] + [c for c in disp.columns if c != '구분']
        disp = disp[cols_order]


        # 3) 숫자 포맷 함수
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
            return f"{int(round(v))}%"


        # 4) 컬럼별 포맷 적용
        for c in disp.columns:
            if c == '구분':
                continue
            if c == '증감률':
                disp[c] = disp[c].apply(fmt_rate)
            else:
                disp[c] = disp[c].apply(fmt_amt)

        # 5) attrs에서 연월 정보 추출
        used_m = int(inv.attrs.get('used_month'))
        prev_m = int(inv.attrs.get('prev_month'))
        prev2_m = int(inv.attrs.get('prev2_month'))
        year_int = int(inv.attrs.get('base_year'))
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

        # =========================
        # 6) 헤더 1줄 구성
        # =========================
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

        # =========================
        # 7) 스타일
        # =========================
        # 행 구조:
        #   행 1      : hdr
        #   행 2~5    : 원재료 세부 (3개월이하, 3개월초과, 6개월초과, 1년초과)
        #   행 6      : 원재료
        #   행 7~10   : 재공 세부
        #   행 11     : 재공
        #   행 12~15  : 제품 세부
        #   행 16     : 제품
        #   행 17~18  : 6개월이하, 6개월초과
        #   행 19     : 합계

        styles = [
            {'selector': 'thead', 'props': [('display', 'none')]},

            {'selector': 'tbody td',
             'props': [('border', '1px solid black')]},

            {'selector': 'tbody tr:nth-child(1) td',
             'props': [('text-align', 'center'),
                       ('font-weight', '700'),
                       ('white-space', 'nowrap'),
                       ('border-top', '1px solid black'),
                       ('border-bottom', '1px solid black')]},

            {'selector': 'tbody tr:nth-child(n+2) td:nth-child(1)',
             'props': [('text-align', 'left'),
                       ('white-space', 'nowrap'),
                       ('padding-left', '8px'),
                       ('min-width', '120px')]},

            {'selector': 'tbody tr:nth-child(n+2) td:nth-child(n+2)',
             'props': [('text-align', 'right'),
                       ('padding', '4px 8px'),
                       ('white-space', 'nowrap')]},

            # 합계행 볼드 (원재료/재공/제품/합계)
            {
                'selector': 'tbody tr:nth-child(6) td, tbody tr:nth-child(11) td, tbody tr:nth-child(16) td, tbody tr:nth-child(19) td',
                'props': [('font-weight', '700')]},
        ]

        display_styled_df(
            disp_vis,
            styles=styles,
            already_flat=True,
        )
        display_memo('f_81', year, month)

    except Exception as e:
        st.error(f"연령별 재고 현황 남통법인 표 생성 중 오류: {e}")


    st.divider()

    st.markdown("<h4> 5) 연령별 재고 현황 태국법인</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 톤, 백만원, %]</div>",
                unsafe_allow_html=True)

    try:
        file_name = st.secrets["sheets"]["f_81_82_83"]
        raw = pd.read_csv(file_name, dtype=str)

        inv = modules.create_age_table_from_company(
            year=int(st.session_state['year']),
            month=int(st.session_state['month']),
            data=raw,
            company_name='태국',
        )

        # 2) 표시용 복사 & 인덱스 풀기
        disp = inv.copy().reset_index()


        # ★ 소계행 → 원재료/재공/제품으로 이름 변경, 1열로 합치기
        def relabel(row):
            b = str(row['구분2']).strip() if pd.notna(row['구분2']) else ''
            s = str(row['구분3']).strip() if pd.notna(row['구분3']) else ''
            # 소계행: 구분3이 '소계' → 구분2 카테고리명으로 표시
            if s == '소계':
                return b if b else '소계'
            # 세부항목
            if s and s != 'nan':
                return s
            # 합계행 (구분2만 있고 구분3 없음)
            if b and b != 'nan':
                return b
            return ''


        disp['구분'] = disp.apply(relabel, axis=1)
        disp = disp[disp['구분'].str.strip() != ''].copy()

        disp = disp.drop(columns=['구분2', '구분3'])
        cols_order = ['구분'] + [c for c in disp.columns if c != '구분']
        disp = disp[cols_order]


        # 3) 숫자 포맷 함수
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
            return f"{int(round(v))}%"


        # 4) 컬럼별 포맷 적용
        for c in disp.columns:
            if c == '구분':
                continue
            if c == '증감률':
                disp[c] = disp[c].apply(fmt_rate)
            else:
                disp[c] = disp[c].apply(fmt_amt)

        # 5) attrs에서 연월 정보 추출
        used_m = int(inv.attrs.get('used_month'))
        prev_m = int(inv.attrs.get('prev_month'))
        prev2_m = int(inv.attrs.get('prev2_month'))
        year_int = int(inv.attrs.get('base_year'))
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

        # =========================
        # 6) 헤더 1줄 구성
        # =========================
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

        # =========================
        # 7) 스타일
        # =========================
        # 행 구조:
        #   행 1      : hdr
        #   행 2~5    : 원재료 세부 (3개월이하, 3개월초과, 6개월초과, 1년초과)
        #   행 6      : 원재료
        #   행 7~10   : 재공 세부
        #   행 11     : 재공
        #   행 12~15  : 제품 세부
        #   행 16     : 제품
        #   행 17~18  : 6개월이하, 6개월초과
        #   행 19     : 합계

        styles = [
            {'selector': 'thead', 'props': [('display', 'none')]},

            {'selector': 'tbody td',
             'props': [('border', '1px solid black')]},

            {'selector': 'tbody tr:nth-child(1) td',
             'props': [('text-align', 'center'),
                       ('font-weight', '700'),
                       ('white-space', 'nowrap'),
                       ('border-top', '1px solid black'),
                       ('border-bottom', '1px solid black')]},

            {'selector': 'tbody tr:nth-child(n+2) td:nth-child(1)',
             'props': [('text-align', 'left'),
                       ('white-space', 'nowrap'),
                       ('padding-left', '8px'),
                       ('min-width', '120px')]},

            {'selector': 'tbody tr:nth-child(n+2) td:nth-child(n+2)',
             'props': [('text-align', 'right'),
                       ('padding', '4px 8px'),
                       ('white-space', 'nowrap')]},

            # 합계행 볼드 (원재료/재공/제품/합계)
            {
                'selector': 'tbody tr:nth-child(6) td, tbody tr:nth-child(11) td, tbody tr:nth-child(16) td, tbody tr:nth-child(19) td',
                'props': [('font-weight', '700')]},
        ]

        display_styled_df(
            disp_vis,
            styles=styles,
            already_flat=True,
        )
        display_memo('f_82', year, month)

    except Exception as e:
        st.error(f"연령별 재고 현황 태국법인 표 생성 중 오류: {e}")

    st.divider()
with t7:

    st.markdown("<h4> 1) 채권 현황 남통법인</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 톤, 백만원, %]</div>",
                unsafe_allow_html=True)

    try:
        file_name = st.secrets["sheets"]["f_84_85_86"]

        raw = pd.read_csv(file_name, dtype=str)

        importlib.invalidate_caches()
        importlib.reload(modules)

        # 1) 표 생성
        ar = modules.create_ar_status_table_from_company(
            year=int(st.session_state['year']),
            month=int(st.session_state['month']),
            data=raw,
            company_name='남통',
        )

        # 2) 표시용 복사 & 인덱스 풀기
        disp = ar.copy().reset_index()
        SPACER = "__spacer__"
        disp.insert(0, SPACER, "")


        # 3) 포맷 함수
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
            if c in (SPACER, '구분'):
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

        # ── 헤더 1줄 ──
        hdr = [''] * len(cols)
        hdr[name_i] = "구분"
        hdr[y4_i] = col_yend_m4
        hdr[y3_i] = col_yend_m3
        hdr[y2_i] = col_yend_m2
        hdr[y1_i] = col_yend_m1
        hdr[prev_i] = f"{prev_m}월"
        hdr[used_i] = f"{used_m}월"

        hdr_df = pd.DataFrame([hdr], columns=cols)
        disp_vis = pd.concat([hdr_df, disp], ignore_index=True)

        # disp_vis 행 번호 (1-based, CSS nth-child 기준):
        # tr1 : 헤더
        # tr2 : 매출액(세금포함)
        # tr3 : 정상채권
        # tr4 : 3개월 이하       ┐
        # tr5 : 3개월 초과       │ 왼쪽 세로선 묶음
        # tr6 : 6개월 초과       │
        # tr7 : 회수불능         ┘
        # tr8 : 기준초과채권
        # tr9 : 매출채권 계
        # tr10: 초과채권 비율(%)
        # tr11: 초과채권 이자손실
        # tr12: 매출채권기일
        # tr13: 정상채권기일
        # tr14: 차이

        styles = [
            {'selector': 'thead', 'props': [('display', 'none')]},

            # spacer 열
            {
                'selector': 'tbody tr td:nth-child(1)',
                'props': [('border-right', '2px solid white !important')],
            },

            # 헤더 1행
            {
                'selector': 'tbody tr:nth-child(1) td',
                'props': [
                    ('text-align', 'center'),
                    ('padding', '8px 8px'),
                    ('font-weight', '600'),
                    ('border-top', '3px solid gray !important'),
                ],
            },

            # 1열 얇게
            {'selector': 'tbody td:nth-child(1)', 'props': [('width', '8px'), ('border-right', '0')]},

            # 본문 (tr2 이후)
            {
                'selector': 'tbody tr:nth-child(n+2) td',
                'props': [('line-height', '1.4'), ('padding', '6px 8px'), ('text-align', 'right')],
            },
            {
                'selector': 'tbody tr:nth-child(n+2) td:nth-child(2)',
                'props': [('text-align', 'left')],
            },
        ]

        # 헤더 하단선 + 본문 구분선 (행)
        styles += [
            {
                'selector': 'tbody tr:nth-child(1)',
                'props': [('border-bottom', '3px solid gray !important')],
            }
        ]

        # 행 구분선 - td:nth-child(2) 기준
        styles += [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child(2)',
                'props': [('border-bottom', '3px solid gray !important')],
            }
            for r in (2, 3, 7, 8, 9, 10, 11, 13, 14)
        ]

        # 행 구분선 - td:nth-child(1) 기준 (spacer열, 묶음 구간 제외)
        styles += [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child(1)',
                'props': [('border-bottom', '3px solid gray !important')],
            }
            for r in (2, 3, 8, 9, 10, 11, 12, 14)
        ]

        # 열 구분선 (구분 열 오른쪽)
        styles += [
            {
                'selector': 'td:nth-child(2)',
                'props': [('border-right', '3px solid gray !important')],
            }
        ]

        # 3개월이하~회수불능(tr4~7) spacer열 왼쪽 세로선
        styles += [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child(1)',
                'props': [('border-right', '3px solid gray !important')],
            }
            for r in (4, 5, 6, 7)
        ]

        display_styled_df(
            disp_vis,
            styles=styles,
            already_flat=True,
        )

        display_memo('f_84', year, month)

    except Exception as e:
        st.error(f"채권 현황 남통법인 표 생성 중 오류: {e}")
    st.divider()


    st.markdown("<h4> 3) 채권 현황 태국법인</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 톤, 백만원, %]</div>", unsafe_allow_html=True)


    try:
        file_name = st.secrets["sheets"]["f_84_85_86"]  

        raw = pd.read_csv(file_name, dtype=str)

        # 1) 표 생성
        ar = modules.create_ar_status_table_from_company(
            year=int(st.session_state['year']),
            month=int(st.session_state['month']),
            data=raw,
            company_name='태국',
        )

        # 2) 표시용 복사 & 인덱스 풀기
        disp = ar.copy().reset_index()  # '구분'
        SPACER = "__spacer__"
        disp.insert(0, SPACER, "")

        # 3) 포맷 함수
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

        # 초과채권 비율(%) 행만 % 포맷
        ratio_mask = disp['구분'] == '초과채권 비율(%)'

        for c in disp.columns:
            if c in (SPACER, '구분'):
                continue
            disp.loc[ratio_mask, c] = disp.loc[ratio_mask, c].apply(fmt_rate)
            disp.loc[~ratio_mask, c] = disp.loc[~ratio_mask, c].apply(fmt_amt)

        # 4) 헤더 2단 구성
        cols = disp.columns.tolist()
        c_idx = {c: i for i, c in enumerate(cols)}

        name_i   = c_idx['구분']

        year_int = int(ar.attrs.get('base_year'))
        used_y   = int(ar.attrs.get('used_year'))
        used_m   = int(ar.attrs.get('used_month'))
        prev_m   = int(ar.attrs.get('prev_month'))
        company  = ar.attrs.get('company', '태국')

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

        y4_i   = c_idx[col_yend_m4]
        y3_i   = c_idx[col_yend_m3]
        y2_i   = c_idx[col_yend_m2]
        y1_i   = c_idx[col_yend_m1]
        prev_i = c_idx[col_prev]
        used_i = c_idx[col_used]

        hdr1 = [''] * len(cols)
        hdr2 = [''] * len(cols)


        used_year = used_y
        m_used = used_m
        m_prev = prev_m

        # 선택월 연도
        m_used_year = used_year

        # 전월 연도 (1월에서 12월로 넘어가는 경우 전년도 처리)
        m_prev_year = used_year
        if m_prev > m_used:   
            m_prev_year = used_year - 1

        year_runs = [
            (prev_i, m_prev_year),
            (used_i, m_used_year),
        ]

        last_year = None
        for col_i, y in year_runs:
            if y != last_year:
                hdr1[col_i] = f"'{y % 100:02d}년"
                last_year = y



        hdr2[name_i] = "구분"
        hdr2[y4_i] = col_yend_m4
        hdr2[y3_i] = col_yend_m3
        hdr2[y2_i] = col_yend_m2
        hdr2[y1_i] = col_yend_m1
        hdr2[prev_i] = f"{prev_m}월"

        hdr_df   = pd.DataFrame([hdr1, hdr2], columns=cols)
        disp_vis = pd.concat([hdr_df, disp], ignore_index=True)


        styles = [
            {'selector': 'thead', 'props': [('display', 'none')]},

            {
                "selector": "tbody tr td:nth-child(1)",
                "props": [
                    ("border-right", "2px solid white !important"),
                ],
            },

            # 헤더 1·2행
            {
                'selector': 'tbody tr:nth-child(1) td',
                'props': [('text-align', 'center'),
                        ('padding', '4px 6px'),
                        ('font-weight', '600'),('border-top','3px solid gray !important')],
            },
            {
                'selector': 'tbody tr:nth-child(2) td',
                'props': [('text-align', 'center'),
                        ('padding', '8px 6px'),
                        ('font-weight', '600')],
            },

            # spacer 열
            {
                'selector': 'tbody td:nth-child(1)',
                'props': [('width', '8px'), ('border-right', '0')],
            },

            # 본문: 3행 이후
            {
                'selector': 'tbody tr:nth-child(n+3) td',
                'props': [('line-height', '1.4'),
                        ('padding', '6px 8px'),
                        ('text-align', 'right')],
            },
            {
                # 구분 열만 왼쪽 정렬
                'selector': 'tbody tr:nth-child(n+3) td:nth-child(2)',
                'props': [('text-align', 'left')],
            },
        ]

        #행
        spacer_rules1 = [
            {
                'selector': f'tr:nth-child(2)',
                'props': [('border-bottom','3px solid gray ')]
               
            }

        ]

        styles += spacer_rules1

        spacer_rules1 = [
            {
                'selector': f'tr:nth-child({r}) td:nth-child(1)',
                'props': [('border-bottom','3px solid gray ')]
               
            }
            for r in (3,4,9,10,11,12,14)
        ]

        styles += spacer_rules1

        spacer_rules1 = [
            {
                'selector': f'tr:nth-child(13) td:nth-child({i})',
                'props': [('border-bottom','2px solid white ')]
               
            }

            for i in (1,2)
        ]

        styles += spacer_rules1

        # #열
        spacer_rules1 = [
            {
                'selector': f'td:nth-child(2)',
                'props': [('border-right','3px solid gray !important')]
               
            }

        ]
        
        styles += spacer_rules1


        spacer_rules2 = [
            {
                'selector': f'tr:nth-child({r}) td:nth-child(2)',
                'props': [('border-bottom','3px solid gray !important')]
               
            }
            for r in (3,4,8,9,10,11,12,14)


        ]

        styles += spacer_rules2



        spacer_rules1 = [
            {
                'selector': f'tr:nth-child({r}) td:nth-child(1)',
                'props': [('border-right','3px solid gray !important')]
               
            }
            for r in range(5,9)
        ]

        styles += spacer_rules1

        display_styled_df(
            disp_vis,
            styles=styles,
            already_flat=True,
        )


        display_memo('f_86', year, month)

    except Exception as e:
        st.error(f"채권 현황 태국법인 표 생성 중 오류: {e}")
    
    st.divider()

with t8:

    st.markdown("<h4> 1) 인원현황표</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 명]</div>", unsafe_allow_html=True)





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



        # 맨 앞 spacer 열
        SPACER = "__spacer__"
        disp.insert(0, SPACER, "")

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
            if c in (SPACER, "구분1", "구분2"):
                continue
            if c == "%":
                disp[c] = disp[c].apply(fmt_rate)
            else:
                disp[c] = disp[c].apply(fmt_amt)


        cols = disp.columns.tolist()
        c_idx = {c: i for i, c in enumerate(cols)}

        g1_i = c_idx["구분1"]
        g2_i = c_idx["구분2"]

        # create_87 이 사용하는 연말 컬럼 이름 재구성
        yy_m1 = f"{(year - 1) % 100:02d}"
        yy_m2 = f"{(year - 2) % 100:02d}"
        yy_m3 = f"{(year - 3) % 100:02d}"
        yy_m4 = f"{(year - 4) % 100:02d}"

        col_yend_m4 = f"'{yy_m4}년말"
        col_yend_m3 = f"'{yy_m3}년말"
        col_yend_m2 = f"'{yy_m2}년말"
        col_yend_m1 = f"'{yy_m1}년말"

        # 전월 / 당월
        prev_y = year
        prev_m = month - 1
        if prev_m <= 0:
            prev_y -= 1
            prev_m += 12

        col_prev = f"{prev_m}월"
        col_used = f"{month}월"

        y4_i   = c_idx[col_yend_m4]
        y3_i   = c_idx[col_yend_m3]
        y2_i   = c_idx[col_yend_m2]
        y1_i   = c_idx[col_yend_m1]
        prev_i = c_idx[col_prev]
        used_i = c_idx[col_used]

        hdr1 = [""] * len(cols)
        hdr2 = [""] * len(cols)

        # 1행: 현재 연도만 월 컬럼 위에 표시
        yy_curr = f"'{year % 100:02d}년"
        hdr1[prev_i] = yy_curr
        hdr1[used_i] = yy_curr


        # 1행: 연말/구분 라벨
        hdr1[g2_i] = "구분"
        hdr1[y4_i] = col_yend_m4
        hdr1[y3_i] = col_yend_m3
        hdr1[y2_i] = col_yend_m2
        hdr1[y1_i] = col_yend_m1

        # 2행: 월, 전월비, % 등
        hdr2[prev_i] = col_prev
        hdr2[used_i] = col_used

 
        year_end_cols = {col_yend_m4, col_yend_m3, col_yend_m2, col_yend_m1}

        for c, i in c_idx.items():
            if (
                hdr2[i] == ""
                and c not in (SPACER, "구분1", "구분2")
                and c not in year_end_cols      # ← 이 줄 추가
            ):
                hdr2[i] = c  # 전월비, % 등


        hdr_df   = pd.DataFrame([hdr1, hdr2], columns=cols)
        disp_vis = pd.concat([hdr_df, disp], ignore_index=True)


        styles = [
            {"selector": "thead", "props": [("display", "none")]},

            {
                "selector": "tbody tr td:nth-child(1)",
                "props": [
                    ("border-right", "2px solid white !important"),
                ],
            },

            # 헤더 1행
            {
                "selector": "tbody tr:nth-child(1) td",
                "props": [
                    ("text-align", "center"),
                    ("padding", "4px 6px"),
                    ("font-weight", "600"),
                    ('border-top','3px solid gray !important'),
                ],
            },
            # 헤더 2행
            {
                "selector": "tbody tr:nth-child(2) td",
                "props": [
                    ("text-align", "center"),
                    ("padding", "8px 6px"),
                    ("font-weight", "600"),
                ],
            },

            # spacer 열
            {
                "selector": "tbody td:nth-child(1)",
                "props": [("width", "8px"), ("border-right", "0")],
            },

            # 본문 전체 기본: 숫자 오른쪽 정렬
            {
                "selector": "tbody tr:nth-child(n+3) td",
                "props": [
                    ("line-height", "1.4"),
                    ("padding", "6px 8px"),
                    ("text-align", "right"),
                ],
            },
            # 구분1 / 구분2 는 왼쪽 정렬
            {
                "selector": "tbody tr:nth-child(n+3) td:nth-child(2)",
                "props": [("text-align", "left")],
            },
            {
                "selector": "tbody tr:nth-child(n+3) td:nth-child(3)",
                "props": [("text-align", "left")],
            },
        ]

        #행
        spacer_rules1 = [
            {
                'selector': f'tr:nth-child({r})',
                'props': [('border-bottom','3px solid gray !important')]
               
            }
            for r in (2,7,12,17)
        ]

        styles += spacer_rules1

        #열
        spacer_rules1 = [
            {
                'selector': f'td:nth-child(3)',
                'props': [('border-right','3px solid gray !important')]
               
            }

        ]

        #열
        styles += spacer_rules1

        spacer_rules2 = [
            {
                'selector': f'tr:nth-child({r}) td:nth-child({i})',
                'props': [('border-bottom','2px solid white !important')]
               
            }
            for r in (1,3,4,5,6,8,9,10,11,12,13,14,15,16,18,19,20,21)
            for i in (1,2)
        ]

        styles += spacer_rules2

                # 구분 정리
        spacer_rules1 = [
            {
                'selector': f'tr:nth-child({r}) td:nth-child(2)',
                'props': [('border-right','3px solid gray !important')]
               
            }
            for r in (3,4,5,6,8,9,10,11,13,14,15,16,18,19,20,21)
        ]

        styles += spacer_rules1

        spacer_rules1 = [
            {
                'selector': f'tr:nth-child({r}) td:nth-child(3)',
                'props': [('border-bottom','3px solid gray !important')]
               
            }
            for r in (6,11,16,21)
        ]

        styles += spacer_rules1

        for i in [6,11,16,21]:
            disp_vis.iloc[i, 2] = ""



        display_styled_df(
            disp_vis,
            styles=styles,
            already_flat=True,
        )

        display_memo("f_87", year, month)

    except Exception as e:
        st.error(f"인원현황 표 생성 중 오류: {e}")

    st.divider()


    st.markdown("<h4> 2) 인당 월평균 생산량</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 명, 톤]</div>", unsafe_allow_html=True)

    try:
        file_name = st.secrets["sheets"]["f_87_88"]  
        raw = pd.read_csv(file_name, dtype=str)

        year = int(st.session_state["year"])
        month = int(st.session_state["month"])

        # 1) 표 생성
        ar = modules.create_89(
            year=year,
            month=month,
            data=raw,
        )

        disp = ar.copy()

        # SPACER = "__spacer__"
        # disp.insert(0, SPACER, "")  # 맨 앞에 spacer 열

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
            if c in ( "구분1", "구분2"):
                continue
            disp[c] = disp[c].apply(fmt_int)

        cols = disp.columns.tolist()
        c_idx = {c: i for i, c in enumerate(cols)}

        g1_i = c_idx["구분1"]
        g2_i = c_idx["구분2"]

        # 모듈에서 사용한 컬럼명 재구성
        yy4 = f"{(year - 4) % 100:02d}"
        yy3 = f"{(year - 3) % 100:02d}"
        yy2 = f"{(year - 2) % 100:02d}"
        yy1 = f"{(year - 1) % 100:02d}"
        yy0 = f"{year % 100:02d}"

        col_y4 = f"'{yy4}년 월평균"
        col_y3 = f"'{yy3}년 월평균"
        col_y2 = f"'{yy2}년 월평균"
        col_y1 = f"'{yy1}년 월평균"

        # 전월
        prev_y = year
        prev_m = month - 1
        if prev_m <= 0:
            prev_y -= 1
            prev_m += 12

        col_prev = f"{prev_m}월"
        col_cur = f"{month}월"
        col_y0_avg = f"'{yy0}년 월평균"

        y4_i = c_idx[col_y4]
        y3_i = c_idx[col_y3]
        y2_i = c_idx[col_y2]
        y1_i = c_idx[col_y1]
        prev_i = c_idx[col_prev]
        cur_i = c_idx[col_cur]
        y0_avg_i = c_idx[col_y0_avg]

        hdr1 = [""] * len(cols)
        hdr2 = [""] * len(cols)

        hdr1[g2_i] = "구분"

        hdr1[y4_i] = col_y4
        hdr1[y3_i] = col_y3
        hdr1[y2_i] = col_y2
        hdr1[y1_i] = col_y1


        yy_curr_label = f"'{yy0}년"
        hdr1[prev_i] = yy_curr_label
        hdr1[cur_i] = yy_curr_label

        hdr2[prev_i] = col_prev
        hdr2[cur_i] = col_cur

        hdr1[y0_avg_i] = col_y0_avg


        hdr_df = pd.DataFrame([hdr1, hdr2], columns=cols)
        disp_vis = pd.concat([hdr_df, disp], ignore_index=True)

        styles = [
            {"selector": "thead", "props": [("display", "none")]},

            # 헤더 1행
            {
                "selector": "tbody tr:nth-child(1) td",
                "props": [
                    ("text-align", "center"),
                    ("padding", "4px 6px"),
                    ("font-weight", "600"),
                    ('border-top','3px solid gray !important'),
                ],
            },
            # 헤더 2행
            {
                "selector": "tbody tr:nth-child(2) td",
                "props": [
                    ("text-align", "center"),
                    ("padding", "6px 6px"),
                    ("font-weight", "600"),
                ],
            },


            # 구분1 / 구분2 왼쪽 정렬
            {
                "selector": "tbody tr:nth-child(n+3) td:nth-child(2)",
                "props": [("text-align", "left")],
            },
            {
                "selector": "tbody tr:nth-child(n+3) td:nth-child(3)",
                "props": [("text-align", "left")],
            },
        ]

        #행
        spacer_rules1 = [
            {
                'selector': f'tr:nth-child({r})',
                'props': [('border-bottom','3px solid gray !important')]
               
            }
            for r in (2,5,8)
        ]

        styles += spacer_rules1

        #열
        spacer_rules1 = [
            {
                'selector': f'td:nth-child(2)',
                'props': [('border-right','3px solid gray !important')]
               
            }

        ]

        #열
        styles += spacer_rules1

        spacer_rules2 = [
            {
                'selector': f'tr:nth-child({r}) td:nth-child(1)',
                'props': [('border-bottom','2px solid white !important')]
               
            }
            for r in (1,3,4,6,7,9,10)
        ]

        styles += spacer_rules2




        display_styled_df(
            disp_vis,
            styles=styles,
            already_flat=True,
        )
        
        display_memo("f_89", year, month)

    except Exception as e:
        st.error(f"인당 월평균 생산량 표 생성 중 오류: {e}")
    
    st.divider()






# Footer
st.markdown("""
<style>.footer { bottom: 0; left: 0; right: 0; padding: 8px; text-align: center; font-size: 13px; color: #666666;}</style>
<div class="footer">ⓒ 2025 SeAH Special Steel Corp. All rights reserved.</div>
""", unsafe_allow_html=True)