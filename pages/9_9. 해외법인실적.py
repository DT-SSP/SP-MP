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

        # ====== 데이터 가공 (modules) ======
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
            return f"({abs(v_rounded):,})" if v_rounded < 0 else f"{v_rounded:,}"

        def fmt_pct(x):
            if pd.isna(x):
                return ""
            try:
                v = float(x)
            except Exception:
                return str(x)
            return f"{v:.1f}"

        disp = body.copy()
        assert set(["대분류", "구분"]).issubset(disp.columns), "'대분류', '구분' 컬럼이 필요합니다."

        # 수치 컬럼
        num_cols = [c for c in disp.columns if c not in ["대분류", "구분"]]

        # 퍼센트 행: 대분류에 '(%)' 포함
        pct_mask = disp["대분류"].astype(str).str.contains("%")

        # 숫자형 변환 + 포맷
        for c in num_cols:
            disp[c] = pd.to_numeric(disp[c], errors="coerce")
            disp.loc[~pct_mask, c] = disp.loc[~pct_mask, c].apply(fmt_amt)
            disp.loc[ pct_mask, c] = disp.loc[ pct_mask, c].apply(fmt_pct)


        SPACER = "__spacer__"
        disp.insert(0, SPACER, "")

        current_grp = None
        for i in disp.index:
            g = disp.loc[i, "대분류"]
            if g != current_grp:
                disp.at[i, SPACER] = g
                current_grp = g

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

        hdr1 = [""] * len(cols)
        hdr2 = [""] * len(cols)

        # 왼쪽 구분 라벨
        hdr1[c_idx[SPACER]] = "구분"
        hdr1[c_idx["구분"]] = ""

        # 전월
        if col_prev in c_idx:
            hdr1[c_idx[col_prev]] = f"{pm}월"
            hdr2[c_idx[col_prev]] = "실적"

        # 당월
        for c, lab in [
            (col_m_pln, "계획"),
            (col_m_act, "실적"),
            (col_m_gap, "계획비"),
            (col_m_mom, "전월비"),
        ]:
            if c in c_idx:
                hdr1[c_idx[c]] = f"{month}월"
                hdr2[c_idx[c]] = lab

        # 누적
        acc_label = f"'{yy}년 누적"
        for c, lab in [
            (col_acc_p, "계획"),
            (col_acc_a, "실적"),
            (col_acc_g, "계획비"),
        ]:
            if c in c_idx:
                hdr1[c_idx[c]] = acc_label
                hdr2[c_idx[c]] = lab

        hdr_df = pd.DataFrame([hdr1, hdr2], columns=cols)
        disp_vis = pd.concat([hdr_df, disp], ignore_index=True)

        styles = [
            # thead 숨김
            {'selector': 'thead', 'props': [('display', 'none')]},

            # 헤더 1행
            {
                'selector': 'tbody tr:nth-child(1) td',
                'props': [
                    ('text-align', 'center'),
                    ('padding', '6px 8px'),
                    ('font-weight', '600'),
                    ('border-top','3px solid gray !important')
                ]
            },
            # 헤더 2행
            {
                'selector': 'tbody tr:nth-child(2) td',
                'props': [
                    ('text-align', 'center'),
                    ('padding', '6px 8px'),
                    ('font-weight', '600'),
                    ('border-bottom', '3px solid gray')
                ]
            },
            # 스페이서 열
            {
                'selector': 'tbody td:nth-child(2)',
                'props': [
                    ('min-width', '80px'),
                    ('white-space', 'nowrap'),
                    # ('font-weight', '600'),
                    ('border-right', '3px solid gray')
                ]
            },
            # '구분' 열 (2열) 좌측 정렬
            {
                'selector': 'tbody tr td:nth-child(2)',
                'props': [
                    ('text-align', 'left'),
                    ('white-space', 'nowrap')
                ]
            }
        ]


        spacer_rules1 = [
            {
                'selector': f'tbody tr:nth-child({r})',
                'props': [('border-bottom','3px solid gray !important')]
               
            }
            for r in (6,12,16)

        ]

        styles += spacer_rules1

        spacer_rules2 = [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child(1)',
                'props': [('border-bottom','2px solid white !important')]
               
            }
            for r in (1,3,4,5,7,8,9,10,11,13,14,15,17,18,19)
        ]

        styles += spacer_rules2


        display_styled_df(
            disp_vis,
            styles=styles,
            already_flat=True
        )

        display_memo('f_61', year, month)

    except Exception as e:
        st.error(f"손익요약 생성 중 오류: {e}")
    
    st.divider()



with t2:

    st.markdown("<h4> 1) 현금흐름 남통법인</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 톤, 백만원, %]</div>", unsafe_allow_html=True)

    try:
        file_name = st.secrets["sheets"]["f_62_63_64"]
        raw = pd.read_csv(file_name, dtype=str)

        # 1) 유틸
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
            # 월은 '전월누적', '당월', '당월누적' 같은 문자열이 있으므로 숫자로 바꾸지 않는다
            df["월"] = df["월"].fillna("").astype(str).str.strip()
            df["실적"] = _to_num(df["실적"])

            # 남통만 사용
            df = df[df["구분1"] == "남통"].copy()

            # 원본 순서 보존 (중복 라벨의 N번째 구분용)
            df["__ord__"] = range(len(df))
            return df

        df0 = _clean_cf_namtong(raw)
        year = int(st.session_state["year"])
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

        # 같은 라벨의 N번째 등장만 집계하도록 번호 부여
        name_counts = {}
        order_with_n = []
        for name in item_order:
            name_counts[name] = name_counts.get(name, 0) + 1
            order_with_n.append((name, name_counts[name]))  # ('기타',1), ('기타',2)...

        index_labels = [nm for nm, _ in order_with_n]

        # 3) 컬럼 라벨
        col_prev2_label = f"{str(year - 2)[-2:]}년"   # '23년
        col_prev1_label = f"{str(year - 1)[-2:]}년"   # '24년
        col_currsum_label = "당월누적"                # 선택년도 당월누적

        # 4) 선택연도에 데이터 있는지 체크 (월은 구분자라서 신경 안 씀)
        sel_year = df0[
            (df0["연도"] == year)
            & (df0["구분2"].isin(item_order))
        ]

        used_m = month  # 헤더에 표시할 선택월 텍스트용

        if sel_year.empty:
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
            # -------------------------------
            # 5) 집계 함수들
            # -------------------------------

            # (1) 전전년도/전년도: 해당 연도 전체 합계
            #     2023, 2024는 구분2별 1건씩이라는 가정 ⇒ nth 사용
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

            # 선택연도
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

            # -------------------------------
            # 6) 컬럼별 값 계산
            # -------------------------------
            vals_prev2 = _block_year(year - 2)   # 예: 2023
            vals_prev1 = _block_year(year - 1)   # 예: 2024

            # 선택년도
            vals_prev = _block_kind(year, "전월누적")
            vals_curr = _block_kind(year, "당월")
            vals_ytd  = _block_kind(year, "당월누적")

            base = pd.DataFrame(
                {
                    col_prev2_label:   vals_prev2,
                    col_prev1_label:   vals_prev1,
                    "전월누적":         vals_prev,
                    "당월":             vals_curr,
                    col_currsum_label: vals_ytd,
                },
                index=pd.Index(index_labels, name="구분"),
                dtype=float
            )

            # -------------------------------
            # 6-1) 파생 항목 강제 재계산
            # -------------------------------
            def _row(label: str) -> pd.Series:
                """해당 라벨이 없으면 0으로 채운 Series 반환(안전장치)"""
                if label in base.index:
                    return base.loc[label]
                else:
                    return pd.Series(0.0, index=base.columns, dtype=float)

            # 조정 = 감가상각비 + 기타
            base.loc["조정"] = _row("감가상각비") + _row("기타")

            # 자산부채증감 =
            #   매출채권 감소(증가) + 기타채권 감소(증가) + 기타자산 감소(증가)
            #   + 재고자산 감소(증가) + 매입채무 증가(감소)
            #   + 기타채무 증가(감소) + 퇴직급여부채증가(감소)
            base.loc["자산부채증감"] = (
                _row("매출채권 감소(증가)")
                + _row("기타채권 감소(증가)")
                + _row("기타자산 감소(증가)")
                + _row("재고자산 감소(증가)")
                + _row("매입채무 증가(감소)")
                + _row("기타채무 증가(감소)")
                + _row("퇴직급여부채증가(감소)")
            )

            # 영업활동현금흐름 =
            #   당기순이익 + 조정 + 자산부채증감
            #   + 법인세납부 + 이자의 수취 + 이자의 지급
            base.loc["영업활동현금흐름"] = (
                _row("당기순이익")
                + base.loc["조정"]
                + base.loc["자산부채증감"]
                + _row("법인세납부")
                + _row("이자의 수취")
                + _row("이자의 지급")
            )

            # 투자활동현금흐름 = 유형자산취득 + 무형자산취득 + 기타 투자활동
            base.loc["투자활동현금흐름"] = (
                _row("유형자산취득")
                + _row("무형자산취득")
                + _row("기타 투자활동")
            )

            # 재무활동현금흐름 = 차입금의 증가(감소)
            base.loc["재무활동현금흐름"] = _row("차입금의 증가(감소)")

            # 현금성자산의 증감 =
            #   영업활동현금흐름 + 투자활동현금흐름 + 재무활동현금흐름
            base.loc["현금성자산의 증감"] = (
                base.loc["영업활동현금흐름"]
                + base.loc["투자활동현금흐름"]
                + base.loc["재무활동현금흐름"]
            )

        
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

        
        disp = disp.reset_index()
        SPACER = "__spacer__"
        disp.insert(0, SPACER, "")

        cols = disp.columns.tolist()
        c_idx = {c: i for i, c in enumerate(cols)}
        yy = str(year)[-2:]
        top_label = f"'{yy} {used_m}월"   

        hdr1 = [''] * len(cols)
        hdr2 = [''] * len(cols)

        # 1행 헤더
        hdr1[c_idx['구분']]             = '구분'
        hdr1[c_idx[col_prev2_label]]   = col_prev2_label
        hdr1[c_idx[col_prev1_label]]   = col_prev1_label
        hdr1[c_idx[col_currsum_label]] = col_currsum_label   # 당월누적

        # 2행 헤더 (선택년도 부분)
        hdr2[c_idx['전월누적']]         = '전월누적'
        hdr2[c_idx['당월']]             = '당월'

        hdr_df = pd.DataFrame([hdr1, hdr2], columns=cols)
        disp_vis = pd.concat([hdr_df, disp], ignore_index=True)




       
        styles = [
            {'selector': 'thead', 'props': [('display','none')]},
            {
                "selector": "tbody tr td:nth-child(1)",
                "props": [
                    ("border-right", "2px solid white !important"),
                ],
            },
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
                'props': [('border-bottom','3px solid gray !important')]
               
            }
            for r in (3,4,7,15,16,17,18,19,22,23,24,25,26,27)
        ]

        styles += spacer_rules1

        spacer_rules2 = [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child(2)',
                'props': [('border-left','3px solid gray !important')]
               
            }
            for r in (4,5,6,7,8,9,10,11,12,13,14,15,20,21,22,24)
        ]

        styles += spacer_rules2

        spacer_rules1 = [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child(1)',
                'props': [('border-bottom','3px solid gray !important')]
               
            }
            for r in (15,16,17,18,22,24,25,26,27)
        ]

        styles += spacer_rules1

        spacer_rules1 = [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child(2)',
                'props': [('text-align','right')]
               
            }
            for r in (6,7,9,10,11,12,13,14,15)
        ]

        styles += spacer_rules1


        display_styled_df(disp_vis, styles=styles, already_flat=True)
        display_memo('f_62', year, month)

    except Exception as e:
        st.error(f"남통 현금흐름표 생성 중 오류: {e}")

    st.divider()

    st.markdown("<h4> 2) 현금흐름 천진법인</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 톤, 백만원, %]</div>", unsafe_allow_html=True)

    try:
        file_name = st.secrets["sheets"]["f_62_63_64"]
        raw = pd.read_csv(file_name, dtype=str)

        # 1) 유틸
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
            # 월은 '전월누적', '당월', '당월누적' 같은 문자열이 있으므로 숫자로 바꾸지 않는다
            df["월"] = df["월"].fillna("").astype(str).str.strip()
            df["실적"] = _to_num(df["실적"])

            # 천진만 사용
            df = df[df["구분1"] == "천진"].copy()

            # 원본 순서 보존 (중복 라벨의 N번째 구분용)
            df["__ord__"] = range(len(df))
            return df

        df0 = _clean_cf_namtong(raw)
        year = int(st.session_state["year"])
        month = int(st.session_state["month"])

        # 행순서 고정
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

        # 같은 라벨의 N번째 등장만 집계하도록 번호 부여
        name_counts = {}
        order_with_n = []
        for name in item_order:
            name_counts[name] = name_counts.get(name, 0) + 1
            order_with_n.append((name, name_counts[name]))  # ('기타',1), ('기타',2)...

        index_labels = [nm for nm, _ in order_with_n]

        # 3) 컬럼 라벨
        col_prev2_label = f"{str(year - 2)[-2:]}년"   # '23년
        col_prev1_label = f"{str(year - 1)[-2:]}년"   # '24년
        col_currsum_label = "당월누적"                # 선택년도 당월누적

        # 4) 선택연도에 데이터 있는지 체크 (월은 구분자라서 신경 안 씀)
        sel_year = df0[
            (df0["연도"] == year)
            & (df0["구분2"].isin(item_order))
        ]

        used_m = month  # 헤더에 표시할 선택월 텍스트용

        if sel_year.empty:
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

            # (2) 선택연도
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


            vals_prev2 = _block_year(year - 2)   # 예: 2023
            vals_prev1 = _block_year(year - 1)   # 예: 2024

            # 선택년도
            vals_prev = _block_kind(year, "전월누적")
            vals_curr = _block_kind(year, "당월")
            vals_ytd  = _block_kind(year, "당월누적")

            base = pd.DataFrame(
                {
                    col_prev2_label:   vals_prev2,
                    col_prev1_label:   vals_prev1,
                    "전월누적":         vals_prev,
                    "당월":             vals_curr,
                    col_currsum_label: vals_ytd,
                },
                index=pd.Index(index_labels, name="구분"),
                dtype=float
            )

            # -------------------------------
            # 6-1) 파생 항목 강제 재계산
            # -------------------------------
            def _row(label: str) -> pd.Series:
                """해당 라벨이 없으면 0으로 채운 Series 반환(안전장치)"""
                if label in base.index:
                    return base.loc[label]
                else:
                    return pd.Series(0.0, index=base.columns, dtype=float)

            # 조정 = 감가상각비 + 기타
            base.loc["조정"] = _row("감가상각비") + _row("기타")

            # 자산부채증감 =
            #   매출채권 감소(증가) + 기타채권 감소(증가) + 기타자산 감소(증가)
            #   + 재고자산 감소(증가) + 매입채무 증가(감소)
            #   + 기타채무 증가(감소) + 퇴직급여부채증가(감소)
            base.loc["자산부채증감"] = (
                _row("매출채권 감소(증가)")
                + _row("기타채권 감소(증가)")
                + _row("기타자산 감소(증가)")
                + _row("재고자산 감소(증가)")
                + _row("매입채무 증가(감소)")
                + _row("기타채무 증가(감소)")
                + _row("퇴직급여부채증가(감소)")
            )

            # 영업활동현금흐름 =
            #   당기순이익 + 조정 + 자산부채증감
            #   + 법인세납부 + 이자의 수취 + 이자의 지급
            base.loc["영업활동현금흐름"] = (
                _row("당기순이익")
                + base.loc["조정"]
                + base.loc["자산부채증감"]
                + _row("법인세납부")
                + _row("이자의 수취")
                + _row("이자의 지급")
            )

            # 투자활동현금흐름 = 유형자산취득 + 무형자산취득 + 기타 투자활동
            base.loc["투자활동현금흐름"] = (
                _row("유형자산취득")
                + _row("무형자산취득")
                + _row("기타 투자활동")
            )

            # 재무활동현금흐름 = 차입금의 증가(감소)
            base.loc["재무활동현금흐름"] = _row("차입금의 증가(감소)")

            # 현금성자산의 증감 =
            #   영업활동현금흐름 + 투자활동현금흐름 + 재무활동현금흐름
            base.loc["현금성자산의 증감"] = (
                base.loc["영업활동현금흐름"]
                + base.loc["투자활동현금흐름"]
                + base.loc["재무활동현금흐름"]
            )

        # 7) 표시 포맷(괄호표기)
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

        # 8) 스페이서 + 2단 헤더
        disp = disp.reset_index()
        SPACER = "__spacer__"
        disp.insert(0, SPACER, "")

        cols = disp.columns.tolist()
        c_idx = {c: i for i, c in enumerate(cols)}
        yy = str(year)[-2:]
        top_label = f"'{yy} {used_m}월"   

        hdr1 = [''] * len(cols)
        hdr2 = [''] * len(cols)

        # 1행 헤더
        hdr1[c_idx['구분']]             = '구분'
        hdr1[c_idx[col_prev2_label]]   = col_prev2_label
        hdr1[c_idx[col_prev1_label]]   = col_prev1_label
        hdr1[c_idx[col_currsum_label]] = col_currsum_label   # 당월누적

        # 2행 헤더 (선택년도 부분)
        hdr2[c_idx['전월누적']]         = '전월누적'
        hdr2[c_idx['당월']]             = '당월'

        hdr_df = pd.DataFrame([hdr1, hdr2], columns=cols)
        disp_vis = pd.concat([hdr_df, disp], ignore_index=True)





        styles = [
            {'selector': 'thead', 'props': [('display','none')]},
            {
                "selector": "tbody tr td:nth-child(1)",
                "props": [
                    ("border-right", "2px solid white !important"),
                ],
            },
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
                'props': [('border-bottom','3px solid gray !important')]
               
            }
            for r in (3,4,7,15,16,17,18,19,22,23,24,25,26,27)
        ]

        styles += spacer_rules1

        spacer_rules2 = [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child(2)',
                'props': [('border-left','3px solid gray !important')]
               
            }
            for r in (4,5,6,7,8,9,10,11,12,13,14,15,20,21,22,24)
        ]

        styles += spacer_rules2

        spacer_rules1 = [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child(1)',
                'props': [('border-bottom','3px solid gray !important')]
               
            }
            for r in (15,16,17,18,22,24,25,26,27)
        ]

        styles += spacer_rules1

        spacer_rules1 = [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child(2)',
                'props': [('text-align','right')]
               
            }
            for r in (6,7,9,10,11,12,13,14,15)
        ]

        styles += spacer_rules1

        
        display_styled_df(disp_vis, styles=styles, already_flat=True)
        display_memo('f_63', year, month)

    except Exception as e:
        st.error(f"천진 현금흐름표 생성 중 오류: {e}")

    st.divider()

    st.markdown("<h4> 3) 현금흐름 태국법인</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 톤, 백만원, %]</div>", unsafe_allow_html=True)

    try:
        file_name = st.secrets["sheets"]["f_62_63_64"]
        raw = pd.read_csv(file_name, dtype=str)

        # 1) 유틸
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
            # 월은 '전월누적', '당월', '당월누적' 같은 문자열이 있으므로 숫자로 바꾸지 않는다
            df["월"] = df["월"].fillna("").astype(str).str.strip()
            df["실적"] = _to_num(df["실적"])

            # 태국만 사용
            df = df[df["구분1"] == "태국"].copy()

            # 원본 순서 보존 (중복 라벨의 N번째 구분용)
            df["__ord__"] = range(len(df))
            return df

        df0 = _clean_cf_namtong(raw)
        year = int(st.session_state["year"])
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

        # 같은 라벨의 N번째 등장만 집계하도록 번호 부여
        name_counts = {}
        order_with_n = []
        for name in item_order:
            name_counts[name] = name_counts.get(name, 0) + 1
            order_with_n.append((name, name_counts[name]))  # ('기타',1), ('기타',2)...

        index_labels = [nm for nm, _ in order_with_n]

        # 3) 컬럼 라벨
        col_prev2_label = f"{str(year - 2)[-2:]}년"   # '23년
        col_prev1_label = f"{str(year - 1)[-2:]}년"   # '24년
        col_currsum_label = "당월누적"                # 선택년도 당월누적

        # 4) 선택연도에 데이터 있는지 체크 (월은 구분자라서 신경 안 씀)
        sel_year = df0[
            (df0["연도"] == year)
            & (df0["구분2"].isin(item_order))
        ]

        used_m = month 

        if sel_year.empty:
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


            # (1) 전전년도/전년도: 해당 연도 전체 합계

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

            # -------------------------------
            # 6) 컬럼별 값 계산
            # -------------------------------
            vals_prev2 = _block_year(year - 2)   
            vals_prev1 = _block_year(year - 1)   

            # 선택년도
            vals_prev = _block_kind(year, "전월누적")
            vals_curr = _block_kind(year, "당월")
            vals_ytd  = _block_kind(year, "당월누적")

            base = pd.DataFrame(
                {
                    col_prev2_label:   vals_prev2,
                    col_prev1_label:   vals_prev1,
                    "전월누적":         vals_prev,
                    "당월":             vals_curr,
                    col_currsum_label: vals_ytd,
                },
                index=pd.Index(index_labels, name="구분"),
                dtype=float
            )

            # -------------------------------
            # 6-1) 파생 항목 강제 재계산
            # -------------------------------
            def _row(label: str) -> pd.Series:
                """해당 라벨이 없으면 0으로 채운 Series 반환(안전장치)"""
                if label in base.index:
                    return base.loc[label]
                else:
                    return pd.Series(0.0, index=base.columns, dtype=float)

            # 조정 = 감가상각비 + 기타
            base.loc["조정"] = _row("감가상각비") + _row("기타")

            # 자산부채증감 =
            #   매출채권 감소(증가) + 기타채권 감소(증가) + 기타자산 감소(증가)
            #   + 재고자산 감소(증가) + 매입채무 증가(감소)
            #   + 기타채무 증가(감소) + 퇴직급여부채증가(감소)
            base.loc["자산부채증감"] = (
                _row("매출채권 감소(증가)")
                + _row("기타채권 감소(증가)")
                + _row("기타자산 감소(증가)")
                + _row("재고자산 감소(증가)")
                + _row("매입채무 증가(감소)")
                + _row("기타채무 증가(감소)")
                + _row("퇴직급여부채증가(감소)")
            )

            # 영업활동현금흐름 =
            #   당기순이익 + 조정 + 자산부채증감
            #   + 법인세납부 + 이자의 수취 + 이자의 지급
            base.loc["영업활동현금흐름"] = (
                _row("당기순이익")
                + base.loc["조정"]
                + base.loc["자산부채증감"]
                + _row("법인세납부")
                + _row("이자의 수취")
                + _row("이자의 지급")
            )

            # 투자활동현금흐름 = 유형자산취득 + 무형자산취득 + 기타 투자활동
            base.loc["투자활동현금흐름"] = (
                _row("유형자산취득")
                + _row("무형자산취득")
                + _row("기타 투자활동")
            )

            # 재무활동현금흐름 = 차입금의 증가(감소)
            base.loc["재무활동현금흐름"] = _row("차입금의 증가(감소)")

            # 현금성자산의 증감 =
            #   영업활동현금흐름 + 투자활동현금흐름 + 재무활동현금흐름
            base.loc["현금성자산의 증감"] = (
                base.loc["영업활동현금흐름"]
                + base.loc["투자활동현금흐름"]
                + base.loc["재무활동현금흐름"]
            )

        # 7) 표시 포맷(괄호표기)
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

        # 8) 스페이서 + 2단 헤더
        disp = disp.reset_index()
        SPACER = "__spacer__"
        disp.insert(0, SPACER, "")

        cols = disp.columns.tolist()
        c_idx = {c: i for i, c in enumerate(cols)}
        yy = str(year)[-2:]
        top_label = f"'{yy} {used_m}월"   

        hdr1 = [''] * len(cols)
        hdr2 = [''] * len(cols)

        # 1행 헤더
        hdr1[c_idx['구분']]             = '구분'
        hdr1[c_idx[col_prev2_label]]   = col_prev2_label
        hdr1[c_idx[col_prev1_label]]   = col_prev1_label
        hdr1[c_idx[col_currsum_label]] = col_currsum_label   # 당월누적

        # 2행 헤더 (선택년도 부분)
        hdr2[c_idx['전월누적']]         = '전월누적'
        hdr2[c_idx['당월']]             = '당월'

        hdr_df = pd.DataFrame([hdr1, hdr2], columns=cols)
        disp_vis = pd.concat([hdr_df, disp], ignore_index=True)




        styles = [
            {'selector': 'thead', 'props': [('display','none')]},
            {
                "selector": "tbody tr td:nth-child(1)",
                "props": [
                    ("border-right", "2px solid white !important"),
                ],
            },
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
                'props': [('border-bottom','3px solid gray !important')]
               
            }
            for r in (3,4,7,15,16,17,18,19,22,23,24,25,26,27)
        ]

        styles += spacer_rules1

        spacer_rules2 = [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child(2)',
                'props': [('border-left','3px solid gray !important')]
               
            }
            for r in (4,5,6,7,8,9,10,11,12,13,14,15,20,21,22,24)
        ]

        styles += spacer_rules2

        spacer_rules1 = [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child(1)',
                'props': [('border-bottom','3px solid gray !important')]
               
            }
            for r in (15,16,17,18,22,24,25,26,27)
        ]

        styles += spacer_rules1

        spacer_rules1 = [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child(2)',
                'props': [('text-align','right')]
               
            }
            for r in (6,7,9,10,11,12,13,14,15)
        ]

        styles += spacer_rules1


        display_styled_df(disp_vis, styles=styles, already_flat=True)
        display_memo('f_64', year, month)

    except Exception as e:
        st.error(f"태국 현금흐름표 생성 중 오류: {e}")

    st.divider()



with t3:
    st.markdown("<h4> 1) 재무상태표 남통법인</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 백만원]</div>", unsafe_allow_html=True)
    # 데이터 로드
    try:
        file_name = st.secrets["sheets"]["f_65_66_67"]
        raw = pd.read_csv(file_name, dtype=str)

        # 모듈 갱신(수정 반영)
        import importlib
        importlib.invalidate_caches(); importlib.reload(modules)

        item_order = [
            '현금및현금성자산','매출채권','재고자산','유형자산','기타자산','자산총계',
            '매입채무','차입금','기타부채','부채총계',
            '자본금','이익잉여금','자본총계','부채 및 자본 총계'
        ]

        base_namtong = modules.create_bs_from_company(
            year         = int(st.session_state['year']),
            month        = int(st.session_state['month']),
            data         = raw,
            item_order   = item_order,
            company_name = '남통',
        )

        # ─────────────────────────
        # 1) 합계 행 재계산
        # ─────────────────────────
        calc = base_namtong.copy()

        sum_map = {
            # 자산총계 = 현금및현금성자산 + 매출채권 + 재고자산 + 유형자산 + 기타자산
            '자산총계': ['현금및현금성자산','매출채권','재고자산','유형자산','기타자산'],

            # 부채총계 = 매입채무 + 차입금 + 기타부채
            '부채총계': ['매입채무','차입금','기타부채'],

            # 자본총계 = 자본금 + 이익잉여금
            '자본총계': ['자본금','이익잉여금'],

            # 부채 및 자본 총계 = 부채총계 + 자본총계
            '부채 및 자본 총계': ['부채총계','자본총계'],
        }

        for target, sources in sum_map.items():
            missing = [s for s in sources if s not in calc.index]
            if missing:
                raise ValueError(f"합계 계산에 필요한 항목 누락: {missing}")
            calc.loc[target] = calc.loc[sources].sum()

        # attrs 그대로 유지
        calc.attrs = base_namtong.attrs


        def fmt_cell(x):
            if pd.isna(x):
                return ""
            try:
                v = float(x)
            except Exception:
                return x

            if v == 0:
                return ""
            return f"({abs(int(round(v))):,})" if v < 0 else f"{int(round(v)):,}"

        disp = calc.copy()
        for c in disp.columns:
            disp[c] = disp[c].apply(fmt_cell)

        disp = disp.reset_index()
        SPACER = "__spacer__"
        disp.insert(0, SPACER, "")


        cols = disp.columns.tolist()
        c_idx = {c: i for i, c in enumerate(cols)}

        gu_i   = c_idx['구분']
        diff_i = c_idx['전월비']
        month_i = c_idx['당월']

        # ===========================
        # 4) 연도·월 정보 가져오기
        # ===========================
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
        yy_curr  = f"{year_int % 100:02d}"
        yy_m1    = f"{(year_int - 1) % 100:02d}"
        yy_m2    = f"{(year_int - 2) % 100:02d}"
        yy_m3    = f"{(year_int - 3) % 100:02d}"


        col_yend_m3 = f"'{yy_m3}년말"
        col_yend_m2 = f"'{yy_m2}년말"
        col_yend_m1 = f"'{yy_m1}년말"
        col_prev    = f"'{yy_curr} 전월"

        # 인덱스 확인
        y3_i   = c_idx[col_yend_m3]
        y2_i   = c_idx[col_yend_m2]
        y1_i   = c_idx[col_yend_m1]
        prev_i = c_idx[col_prev]


        # ===========================
        # 5) 3단 헤더 구성
        # ===========================
        hdr1 = [''] * len(cols)
        hdr2 = [''] * len(cols)
 

        hdr2[gu_i] = '남통'
        hdr2[y3_i] = f"'{yy_m3}년말"   # 선택 전전전년 말
        hdr2[y2_i] = f"'{yy_m2}년말"   # 선택 전전년 말
        hdr2[y1_i] = f"'{yy_m1}년말"   # 전년말


        prev_year_int = year_int
        if used_m is not None and prev_m is not None and prev_m > used_m:
            prev_year_int = year_int - 1

        yy_curr_hdr = f"{year_int % 100:02d}"        # 당월 연도 (예: 2025 -> '25')
        yy_prev_hdr = f"{prev_year_int % 100:02d}"   # 전월 연도 (예: 2024 -> '24')

        hdr1[prev_i]  = f"'{yy_prev_hdr}년"   # 전월용 연도
        hdr1[month_i] = f"'{yy_curr_hdr}년"   # 당월용 연도

        hdr2[prev_i]  = f"{prev_m}월"   # 예: 3월
        hdr2[month_i] = f"{used_m}월"   # 예: 4월

        # 전월비 컬럼 라벨
        hdr2[diff_i] = '전월비'

        hdr_df   = pd.DataFrame([hdr1, hdr2], columns=cols)
        disp_vis = pd.concat([hdr_df, disp], ignore_index=True)






        styles = [
            {'selector': 'thead', 'props': [('display','none')]},
            
            {
                "selector": "tbody tr td:nth-child(1)",
                "props": [
                    ("border-right", "2px solid white !important"),
                ],
            },

            # 헤더 1·2·3행
            {'selector': 'tbody tr:nth-child(1) td', 'props': [('text-align','center'), ('padding','8px 8px'),  ('line-height','1.1'), ('font-weight','600'),('border-top','3px solid gray !important')]},
            {'selector': 'tbody tr:nth-child(2) td', 'props': [('text-align','center'), ('padding','10px 8px'), ('line-height','1.4'), ('font-weight','600')]},
            {'selector': 'tbody tr:nth-child(2) td:nth-child(2)', 'props': [('text-align','center')]},


            # 1열 얇게
            {'selector': 'tbody td:nth-child(1)', 'props': [('width','8px'), ('border-right','0')]},


            # 본문
            {'selector': 'tbody tr:nth-child(n+4) td', 'props': [('line-height','1.45'), ('padding','8px 10px'), ('text-align','right')]},
            {'selector': 'tbody tr:nth-child(n+4) td:nth-child(2)', 'props': [('text-align','left')]},
        ]

        spacer_rules2 = [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child(2)',
                'props': [('border-left','3px solid gray !important')]
               
            }
            for r in (3,4,5,6,7,9,10,11,13,14)
        ]

        styles += spacer_rules2

        
        spacer_rules1 = [
            {
                'selector': f'tbody tr:nth-child(2)',
                'props': [('border-bottom','3px solid gray !important')]
               
            }

        ]

        styles += spacer_rules1

        spacer_rules1 = [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child(2)',
                'props': [('border-bottom','3px solid gray !important')]
               
            }
            for r in (7,8,11,12,14,15,16)
        ]

        styles += spacer_rules1

        spacer_rules1 = [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child(1)',
                'props': [('border-bottom','3px solid gray !important')]
               
            }
            for r in (8,12,15,16)
        ]

        styles += spacer_rules1

        spacer_rules3 = [
            {
                'selector': f'td:nth-child(2)',
                'props': [('border-right','3px solid gray !important')]
               
            }

        ]

        styles += spacer_rules3


        display_styled_df(
            disp_vis,
            styles=styles,
            already_flat=True
        )
        display_memo('f_65', year, month)
        


    except Exception as e:
        st.error(f"남통 재무상태표 생성 중 오류: {e}")

    st.divider()


    st.markdown("<h4> 2) 재무상태표 천진법인</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 백만원]</div>", unsafe_allow_html=True)

    try:
        file_name = st.secrets["sheets"]["f_65_66_67"]
        raw = pd.read_csv(file_name, dtype=str)

        # 모듈 갱신(수정 반영)
        import importlib
        importlib.invalidate_caches(); importlib.reload(modules)

        item_order = [
            '현금및현금성자산','매출채권','재고자산','유형자산','기타자산','자산총계',
            '매입채무','차입금','기타부채','부채총계',
            '자본금','이익잉여금','자본총계','부채 및 자본 총계'
        ]

        base_namtong = modules.create_bs_from_company(
            year         = int(st.session_state['year']),
            month        = int(st.session_state['month']),
            data         = raw,
            item_order   = item_order,
            company_name = '천진',
        )

        # ─────────────────────────
        # 1) 합계 행 재계산
        # ─────────────────────────
        calc = base_namtong.copy()

        sum_map = {
            # 자산총계 = 현금및현금성자산 + 매출채권 + 재고자산 + 유형자산 + 기타자산
            '자산총계': ['현금및현금성자산','매출채권','재고자산','유형자산','기타자산'],

            # 부채총계 = 매입채무 + 차입금 + 기타부채
            '부채총계': ['매입채무','차입금','기타부채'],

            # 자본총계 = 자본금 + 이익잉여금
            '자본총계': ['자본금','이익잉여금'],

            # 부채 및 자본 총계 = 부채총계 + 자본총계
            '부채 및 자본 총계': ['부채총계','자본총계'],
        }

        for target, sources in sum_map.items():
            missing = [s for s in sources if s not in calc.index]
            if missing:
                raise ValueError(f"합계 계산에 필요한 항목 누락: {missing}")
            calc.loc[target] = calc.loc[sources].sum()

        # attrs 그대로 유지
        calc.attrs = base_namtong.attrs


        def fmt_cell(x):
            if pd.isna(x):
                return ""
            try:
                v = float(x)
            except Exception:
                return x

            if v == 0:
                return ""
            return f"({abs(int(round(v))):,})" if v < 0 else f"{int(round(v)):,}"

        disp = calc.copy()
        for c in disp.columns:
            disp[c] = disp[c].apply(fmt_cell)

        disp = disp.reset_index()
        SPACER = "__spacer__"
        disp.insert(0, SPACER, "")



        cols = disp.columns.tolist()
        c_idx = {c: i for i, c in enumerate(cols)}

        gu_i   = c_idx['구분']
        diff_i = c_idx['전월비']
        month_i = c_idx['당월']

        # ===========================
        # 4) 연도·월 정보 가져오기
        # ===========================
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
        yy_curr  = f"{year_int % 100:02d}"
        yy_m1    = f"{(year_int - 1) % 100:02d}"
        yy_m2    = f"{(year_int - 2) % 100:02d}"
        yy_m3    = f"{(year_int - 3) % 100:02d}"

        # create_bs_from_company에서 만들어진 컬럼명과 매칭
        col_yend_m3 = f"'{yy_m3}년말"
        col_yend_m2 = f"'{yy_m2}년말"
        col_yend_m1 = f"'{yy_m1}년말"
        col_prev    = f"'{yy_curr} 전월"

        # 인덱스 확인
        y3_i   = c_idx[col_yend_m3]
        y2_i   = c_idx[col_yend_m2]
        y1_i   = c_idx[col_yend_m1]
        prev_i = c_idx[col_prev]

        # ===========================
        # 5) 3단 헤더 구성
        # ===========================
        hdr1 = [''] * len(cols)
        hdr2 = [''] * len(cols)


        hdr2[gu_i] = '천진'
        hdr2[y3_i] = f"'{yy_m3}년말"   # 선택 전전전년 말
        hdr2[y2_i] = f"'{yy_m2}년말"   # 선택 전전년 말
        hdr2[y1_i] = f"'{yy_m1}년말"   # 전년말


        prev_year_int = year_int
        if used_m is not None and prev_m is not None and prev_m > used_m:
            prev_year_int = year_int - 1

        yy_curr_hdr = f"{year_int % 100:02d}"        # 당월 연도 (예: 2025 -> '25')
        yy_prev_hdr = f"{prev_year_int % 100:02d}"   # 전월 연도 (예: 2024 -> '24')

        hdr1[prev_i]  = f"'{yy_prev_hdr}년"   # 전월용 연도
        hdr1[month_i] = f"'{yy_curr_hdr}년"   # 당월용 연도

        hdr2[prev_i]  = f"{prev_m}월"   # 예: 3월
        hdr2[month_i] = f"{used_m}월"   # 예: 4월

        # 전월비 컬럼 라벨
        hdr2[diff_i] = '전월비'

        hdr_df   = pd.DataFrame([hdr1, hdr2], columns=cols)
        disp_vis = pd.concat([hdr_df, disp], ignore_index=True)






        styles = [
            {'selector': 'thead', 'props': [('display','none')]},
            
            {
                "selector": "tbody tr td:nth-child(1)",
                "props": [
                    ("border-right", "2px solid white !important"),
                ],
            },

            # 헤더 1·2·3행
            {'selector': 'tbody tr:nth-child(1) td', 'props': [('text-align','center'), ('padding','8px 8px'),  ('line-height','1.1'), ('font-weight','600'),('border-top','3px solid gray !important')]},
            {'selector': 'tbody tr:nth-child(2) td', 'props': [('text-align','center'), ('padding','10px 8px'), ('line-height','1.4'), ('font-weight','600')]},
            {'selector': 'tbody tr:nth-child(2) td:nth-child(2)', 'props': [('text-align','center')]},


            # 1열 얇게
            {'selector': 'tbody td:nth-child(1)', 'props': [('width','8px'), ('border-right','0')]},


            # 본문
            {'selector': 'tbody tr:nth-child(n+4) td', 'props': [('line-height','1.45'), ('padding','8px 10px'), ('text-align','right')]},
            {'selector': 'tbody tr:nth-child(n+4) td:nth-child(2)', 'props': [('text-align','left')]},
        ]

        spacer_rules2 = [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child(2)',
                'props': [('border-left','3px solid gray !important')]
               
            }
            for r in (3,4,5,6,7,9,10,11,13,14)
        ]

        styles += spacer_rules2

        
        spacer_rules1 = [
            {
                'selector': f'tbody tr:nth-child(2)',
                'props': [('border-bottom','3px solid gray !important')]
               
            }

        ]

        styles += spacer_rules1

        spacer_rules1 = [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child(2)',
                'props': [('border-bottom','3px solid gray !important')]
               
            }
            for r in (7,8,11,12,14,15,16)
        ]

        styles += spacer_rules1

        spacer_rules1 = [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child(1)',
                'props': [('border-bottom','3px solid gray !important')]
               
            }
            for r in (8,12,15,16)
        ]

        styles += spacer_rules1

        spacer_rules3 = [
            {
                'selector': f'td:nth-child(2)',
                'props': [('border-right','3px solid gray !important')]
               
            }

        ]

        styles += spacer_rules3


        display_styled_df(
            disp_vis,
            styles=styles,
            already_flat=True
        )

        display_memo('f_66', year, month)
        



    except Exception as e:
        st.error(f"천진 재무상태표 생성 중 오류: {e}")

    st.divider()

    st.markdown("<h4> 3) 재무상태표 태국법인</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 백만원]</div>", unsafe_allow_html=True)

    try:
        file_name = st.secrets["sheets"]["f_65_66_67"]
        raw = pd.read_csv(file_name, dtype=str)



        item_order = [
            '현금및현금성자산','매출채권','재고자산','유형자산','기타자산','자산총계',
            '매입채무','차입금','기타부채','부채총계',
            '자본금','이익잉여금','자본총계','부채 및 자본 총계'
        ]

        base_namtong = modules.create_bs_from_company(
            year         = int(st.session_state['year']),
            month        = int(st.session_state['month']),
            data         = raw,
            item_order   = item_order,
            company_name = '태국',
        )

        # ─────────────────────────
        # 1) 합계 행 재계산
        # ─────────────────────────
        calc = base_namtong.copy()

        sum_map = {
            # 자산총계 = 현금및현금성자산 + 매출채권 + 재고자산 + 유형자산 + 기타자산
            '자산총계': ['현금및현금성자산','매출채권','재고자산','유형자산','기타자산'],

            # 부채총계 = 매입채무 + 차입금 + 기타부채
            '부채총계': ['매입채무','차입금','기타부채'],

            # 자본총계 = 자본금 + 이익잉여금
            '자본총계': ['자본금','이익잉여금'],

            # 부채 및 자본 총계 = 부채총계 + 자본총계
            '부채 및 자본 총계': ['부채총계','자본총계'],
        }

        for target, sources in sum_map.items():
            missing = [s for s in sources if s not in calc.index]
            if missing:
                raise ValueError(f"합계 계산에 필요한 항목 누락: {missing}")
            calc.loc[target] = calc.loc[sources].sum()

        # attrs 그대로 유지
        calc.attrs = base_namtong.attrs


        def fmt_cell(x):
            if pd.isna(x):
                return ""
            try:
                v = float(x)
            except Exception:
                return x

            if v == 0:
                return ""
            return f"({abs(int(round(v))):,})" if v < 0 else f"{int(round(v)):,}"

        disp = calc.copy()
        for c in disp.columns:
            disp[c] = disp[c].apply(fmt_cell)

        disp = disp.reset_index()
        SPACER = "__spacer__"
        disp.insert(0, SPACER, "")




        cols = disp.columns.tolist()
        c_idx = {c: i for i, c in enumerate(cols)}

        gu_i   = c_idx['구분']
        diff_i = c_idx['전월비']
        month_i = c_idx['당월']

        # ===========================
        # 4) 연도·월 정보 가져오기
        # ===========================
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
        yy_curr  = f"{year_int % 100:02d}"
        yy_m1    = f"{(year_int - 1) % 100:02d}"
        yy_m2    = f"{(year_int - 2) % 100:02d}"
        yy_m3    = f"{(year_int - 3) % 100:02d}"

        # create_bs_from_company에서 만들어진 컬럼명과 매칭
        col_yend_m3 = f"'{yy_m3}년말"
        col_yend_m2 = f"'{yy_m2}년말"
        col_yend_m1 = f"'{yy_m1}년말"
        col_prev    = f"'{yy_curr} 전월"

        # 인덱스 확인
        y3_i   = c_idx[col_yend_m3]
        y2_i   = c_idx[col_yend_m2]
        y1_i   = c_idx[col_yend_m1]
        prev_i = c_idx[col_prev]

        # ===========================
        # 5) 3단 헤더 구성
        # ===========================
        hdr1 = [''] * len(cols)
        hdr2 = [''] * len(cols)


        hdr2[gu_i] = '남통'
        hdr2[y3_i] = f"'{yy_m3}년말"   # 선택 전전전년 말
        hdr2[y2_i] = f"'{yy_m2}년말"   # 선택 전전년 말
        hdr2[y1_i] = f"'{yy_m1}년말"   # 전년말


        prev_year_int = year_int
        if used_m is not None and prev_m is not None and prev_m > used_m:
            prev_year_int = year_int - 1

        yy_curr_hdr = f"{year_int % 100:02d}"        # 당월 연도 (예: 2025 -> '25')
        yy_prev_hdr = f"{prev_year_int % 100:02d}"   # 전월 연도 (예: 2024 -> '24')

        hdr1[prev_i]  = f"'{yy_prev_hdr}년"   # 전월용 연도
        hdr1[month_i] = f"'{yy_curr_hdr}년"   # 당월용 연도

        hdr2[prev_i]  = f"{prev_m}월"   # 예: 3월
        hdr2[month_i] = f"{used_m}월"   # 예: 4월

        # 전월비 컬럼 라벨
        hdr2[diff_i] = '전월비'

        hdr_df   = pd.DataFrame([hdr1, hdr2], columns=cols)
        disp_vis = pd.concat([hdr_df, disp], ignore_index=True)






        styles = [
            {'selector': 'thead', 'props': [('display','none')]},
            
            {
                "selector": "tbody tr td:nth-child(1)",
                "props": [
                    ("border-right", "2px solid white !important"),
                ],
            },

            # 헤더 1·2·3행
            {'selector': 'tbody tr:nth-child(1) td', 'props': [('text-align','center'), ('padding','8px 8px'),  ('line-height','1.1'), ('font-weight','600'),('border-top','3px solid gray !important')]},
            {'selector': 'tbody tr:nth-child(2) td', 'props': [('text-align','center'), ('padding','10px 8px'), ('line-height','1.4'), ('font-weight','600')]},
            {'selector': 'tbody tr:nth-child(2) td:nth-child(2)', 'props': [('text-align','center')]},


            # 1열 얇게
            {'selector': 'tbody td:nth-child(1)', 'props': [('width','8px'), ('border-right','0')]},


            # 본문
            {'selector': 'tbody tr:nth-child(n+4) td', 'props': [('line-height','1.45'), ('padding','8px 10px'), ('text-align','right')]},
            {'selector': 'tbody tr:nth-child(n+4) td:nth-child(2)', 'props': [('text-align','left')]},
        ]

        spacer_rules2 = [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child(2)',
                'props': [('border-left','3px solid gray !important')]
               
            }
            for r in (3,4,5,6,7,9,10,11,13,14)
        ]

        styles += spacer_rules2

        
        spacer_rules1 = [
            {
                'selector': f'tbody tr:nth-child(2)',
                'props': [('border-bottom','3px solid gray !important')]
               
            }

        ]

        styles += spacer_rules1


        spacer_rules1 = [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child(2)',
                'props': [('border-bottom','3px solid gray !important')]
               
            }
            for r in (7,8,11,12,14,15,16)
        ]

        styles += spacer_rules1

        spacer_rules1 = [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child(1)',
                'props': [('border-bottom','3px solid gray !important')]
               
            }
            for r in (8,12,15,16)
        ]

        styles += spacer_rules1

        spacer_rules3 = [
            {
                'selector': f'td:nth-child(2)',
                'props': [('border-right','3px solid gray !important')]
               
            }

        ]

        styles += spacer_rules3




        display_styled_df(
            disp_vis,
            styles=styles,
            already_flat=True
        )

        display_memo('f_67', year, month)
        



    except Exception as e:
        st.error(f"남통 재무상태표 생성 중 오류: {e}")

    st.divider()

with t4:

    st.markdown("<h4> 1) 등급별 판매현황</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 톤]</div>", unsafe_allow_html=True)

    try:
        file_name = st.secrets["sheets"]["f_68"]
        df_src = pd.read_csv(file_name, dtype=str)

        # 선택한 year, month 기준으로 테이블 생성
        disp = modules.build_grade_sales_table_68(df_src, year, month)
        body = disp.copy()

        # =========================
        # 1) 연도/월 컬럼 정보 수집
        # =========================

        # 직전 3개 연도 컬럼 이름 (예: "23년", "24년", "25년")
        prev_year_labels = [f"{str(y)[-2:]}년" for y in range(year - 3, year)]

        # 최근 3개월 (전전월, 전월, 선택월) - 연도 포함
        # 예: 2026-02 선택 → (2025,12), (2026,1), (2026,2)
        month_pairs = []
        for k in (2, 1, 0):  # 전전월, 전월, 선택월
            y = year
            m = month - k
            while m <= 0:
                y -= 1
                m += 12
            month_pairs.append((y, m))

        # disp/body 에 실제로 존재하는 월 컬럼명 구성
        # 예: "25년12월", "26년1월", "26년2월"
        month_defs = []
        for y, m in month_pairs:
            col = f"{str(y)[-2:]}년{m}월"
            if col in body.columns:
                month_defs.append((col, y, m))

        # 숫자 포맷 대상 컬럼 후보 (연도 + 최근 3개월)
        candidate_cols = prev_year_labels + [col for (col, _, _) in month_defs]
        NUM_COLS = [c for c in candidate_cols if c in body.columns]

        # 전월비 계열
        diff_cols = [c for c in body.columns if "전월비" in c and "%" not in c]
        pct_cols  = [c for c in body.columns if c.endswith("전월비%")]

        # =========================
        # 2) 가짜 헤더 hdr1, hdr2 구성
        # =========================
        hdr1 = {col: "" for col in body.columns}
        hdr2 = {col: "" for col in body.columns}

        # (1) 구분 컬럼 텍스트
        if "구분2" in hdr1:
            hdr1["구분2"] = "구분"

        # (2) 직전 3개 연도: 1행에만 표시 (예: '23년, '24년, '25년)
        for y_col in prev_year_labels:
            if y_col in hdr1:
                hdr1[y_col] = f"'{y_col}"

        # (3) 최근 3개월: 연도가 바뀔 때만 1행에 'yy년, 2행에 "m월"
        last_year = None
        for col, y, m in month_defs:
            yy_col = str(y)[-2:]
            if y != last_year:
                hdr1[col] = f"'{yy_col}년"
                last_year = y
            else:
                hdr1[col] = ""
            hdr2[col] = f"{m}월"

        # (4) 전월비 / 전월비% 컬럼 헤더
        #     1행: "'yy.mm월" (선택연도 기준), 2행: "전월比" / "%"
        yy = str(year)[-2:]  # '2025' -> '25'
        ym_group = []
        ym_group += [c for c in diff_cols if c in body.columns]
        ym_group += [c for c in pct_cols  if c in body.columns]

        first = True
        for c in ym_group:
            if first:
                hdr1[c] = f"'{yy}.{month}월"   # 예: '26.2월
                first = False
            else:
                hdr1[c] = ""

            if c in diff_cols:
                hdr2[c] = "전월比"
            else:
                hdr2[c] = "%"

        # body 맨 위에 hdr1, hdr2 추가
        hdr_df = pd.DataFrame([hdr1, hdr2])
        body = pd.concat([hdr_df, body], ignore_index=True)




        styles = [
            {"selector": "thead", "props": [("display", "none")]},

            # hdr1(첫 행) 중앙 정렬 + 볼드
            {"selector": "tbody tr:nth-child(1) td",
             "props": [("font-weight","700"), ("text-align","center"),('border-top','3px solid gray !important')]},

             # hdr2(두번째 행) 중앙 정렬 + 볼드
            {"selector": "tbody tr:nth-child(2) td",
             "props": [("font-weight","700"), ("text-align","center")]},

            # 구분1/구분2 왼쪽정렬 (hdr1 제외)
            {"selector": "tbody tr:nth-child(n+2) td:nth-child(1), tbody tr:nth-child(n+2) td:nth-child(2)",
             "props": [("text-align", "left")]},

            # 숫자는 오른쪽 정렬 (hdr1 제외)
            {"selector": "tbody tr:nth-child(n+2) td:nth-child(n+3)",
             "props": [("text-align", "right")]},

            # 공장명 bold (데이터부)
            {"selector": "tbody tr:nth-child(n+2) td:nth-child(1)",
             "props": [("font-weight","700")]},

            {"selector": "tbody tr td:nth-child(2)",
             "props": [("white-space","nowrap")]},
        ]

        #행
        spacer_rules1 = [
            {
                'selector': f'tr:nth-child({r})',
                'props': [('border-bottom','3px solid gray !important')]
               
            }
            for r in (2,11,20,30,38)
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

        spacer_rules1 = [
            {
                'selector': f'tr:nth-child({r}) td:nth-child(1)',
                'props': [('border-bottom','2px solid white !important')]
               
            }
            for r in (1,3,4,5,6,7,8,9,10,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,29,28,30,31,32,33,34,35,36,37)
        ]

        styles += spacer_rules1

        # 구분 정리
        spacer_rules1 = [
            {
                'selector': f'tr:nth-child({r}) td:nth-child(1)',
                'props': [('border-right','3px solid gray !important')]
               
            }
            for r in (3,4,5,6,7,8,9,10,12,13,14,15,16,17,18,19,21,22,23,24,25,26,27,28,29,31,32,33,34,35,36,37)
        ]

        styles += spacer_rules1

        spacer_rules1 = [
            {
                'selector': f'tr:nth-child({r}) td:nth-child(2)',
                'props': [('border-bottom','3px solid gray !important')]
               
            }
            for r in (10,19,29,37)
        ]

        styles += spacer_rules1

        

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

        # 1) 모듈에서 표 생성 (연산)
        disp = modules.build_chq_f69(df_src, year, month)
        body = disp.copy()

        yy = str(year)[-2:]   # 예: 2025 -> "25"

        # -----------------------------
        # 2) 연도 / 월 / 전월비 컬럼 정보
        # -----------------------------

        # (1) 직전 3개 연도 라벨 (모듈과 동일 규칙)
        #   예: "'22년", "'23년", "'24년 누계"
        prev_year_labels_all = []
        for y in range(year - 3, year):
            if y == year - 1:
                label = f"'{str(y)[-2:]}년 누계"
            else:
                label = f"'{str(y)[-2:]}년"
            prev_year_labels_all.append(label)

        # 실제 body에 존재하는 연도 컬럼만 사용
        prev_year_labels = [c for c in prev_year_labels_all if c in body.columns]

        # (2) 최근 3개월 (전전월, 전월, 선택월) – 연도 경계 포함
        #     예: 2026-02 선택 → (2025,12), (2026,1), (2026,2)
        month_pairs = []
        for k in (2, 1, 0):   # 전전월, 전월, 선택월
            y0 = year
            m0 = month - k
            while m0 <= 0:
                y0 -= 1
                m0 += 12
            month_pairs.append((y0, m0))

        # body에 실제로 존재하는 월 컬럼명만 사용
        #   예: "25년12월", "26년1월", "26년2월"
        month_cols = []   # (col_name, y, m)
        for y0, m0 in month_pairs:
            col = f"{str(y0)[-2:]}년{m0}월"
            if col in body.columns:
                month_cols.append((col, y0, m0))

        # (3) 숫자 포맷 대상 컬럼 (연도 + 최근 3개월)
        candidate_cols = prev_year_labels + [col for (col, _, _) in month_cols]
        NUM_COLS = [c for c in candidate_cols if c in body.columns]

        # (4) 전월비 계열 컬럼
        diff_cols = [c for c in body.columns if "전월비" in c and "%" not in c]
        pct_cols  = [c for c in body.columns if c.endswith("전월비%")]

        # -----------------------------
        # 3) 가짜 헤더 hdr1, hdr2 구성
        # -----------------------------
        hdr1 = {col: "" for col in body.columns}
        hdr2 = {col: "" for col in body.columns}

        # (1) 구분 컬럼 텍스트
        if "구분2" in hdr1:
            hdr1["구분2"] = "구분"

        # (2) 직전 3개 연도 1행 라벨
        for y_col in prev_year_labels:
            # '25년 누계 → '25년 으로 표시
            hdr1[y_col] = y_col.replace(" 누계", "")

        # (3) 최근 3개월: 연도가 바뀔 때만 1행에 'yy년, 2행에 "m월"
        #     예: 25년12월, 26년1월, 26년2월
        last_year = None
        for col, y0, m0 in month_cols:
            yy_col = str(y0)[-2:]
            if y0 != last_year:
                hdr1[col] = f"'{yy_col}년"
                last_year = y0
            else:
                hdr1[col] = ""
            hdr2[col] = f"{m0}월"

        # (4) 전월비 / 전월비% 컬럼 헤더
        #     1행: "'yy.mm월" (선택연도 기준 라벨), 2행: "전월比" / "%"
        ym_group = []
        ym_group += [c for c in diff_cols if c in body.columns]
        ym_group += [c for c in pct_cols  if c in body.columns]

        first = True
        for c in ym_group:
            if first:
                hdr1[c] = f"'{yy}.{month}월"   # 예: '25.8월
                first = False
            else:
                hdr1[c] = ""

            if c in diff_cols:
                hdr2[c] = "전월比"
            else:
                hdr2[c] = "%"

        # body 맨 위에 hdr1, hdr2 추가
        hdr_df = pd.DataFrame([hdr1, hdr2])
        body = pd.concat([hdr_df, body], ignore_index=True)

        # =========================
        #  포맷팅 함수
        # =========================
        def fmt_num(v):
            try:
                v = float(v)
            except Exception:
                return ""
            return f"{v:,.0f}"

        def fmt_diff(v):
            try:
                v = float(v)
            except Exception:
                return ""
            if v < 0:
                return f'<span style="color:#d62728;">({abs(v):,.0f})</span>'
            return f"{v:,.0f}"

        def fmt_pct(v):
            try:
                v = float(v)
            except Exception:
                return ""
            return f"{v:.1f}%"

        # 0,1행 = 가짜 헤더
        data_rows = body.index >= 2

        # % 행(열처리 비율)
        has_gubun2 = "구분2" in body.columns
        pct_rows_disp = (disp["구분2"] == "%") if "구분2" in disp.columns else pd.Series(False, index=disp.index)
        pct_rows_body = ((body["구분2"] == "%") & data_rows) if has_gubun2 else (body.index == -1)

        # (1) 일반 숫자행: 콤마
        for c in NUM_COLS:
            body.loc[data_rows & ~pct_rows_body, c] = (
                body.loc[data_rows & ~pct_rows_body, c].apply(fmt_num)
            )

        # (2) % 행: disp 원본 숫자 → 퍼센트 포맷
        for c in NUM_COLS:
            if c in disp.columns and pct_rows_body.any():
                raw_vals = disp.loc[pct_rows_disp, c].values
                body.loc[pct_rows_body, c] = [fmt_pct(v) for v in raw_vals]

        # (3) 전월비 (톤)
        for c in diff_cols:
            # 일반 행
            body.loc[data_rows & ~pct_rows_body, c] = (
                body.loc[data_rows & ~pct_rows_body, c].apply(fmt_diff)
            )
            # % 행은 pp 표기
            if pct_rows_body.any():
                def fmt_pp(v):
                    try:
                        v = float(v)
                    except Exception:
                        return ""
                    return f"{v:.1f}pp"
                body.loc[pct_rows_body, c] = body.loc[pct_rows_body, c].apply(fmt_pp)

        # (4) 전월비 % 컬럼
        for c in pct_cols:
            body.loc[data_rows, c] = body.loc[data_rows, c].apply(fmt_pct)

        # =========================
        #  스타일
        # =========================
        styles = [
            {"selector": "thead", "props": [("display", "none")]},
            {
                "selector": "tbody tr:nth-child(1) td",
                "props": [("font-weight","700"), ("text-align","center"),('border-top','3px solid gray !important')],
            },
            {
                "selector": "tbody tr:nth-child(2) td",
                "props": [("font-weight","700"), ("text-align","center")],
            },
            {
                "selector": "tbody tr:nth-child(n+2) td:nth-child(1), tbody tr:nth-child(n+2) td:nth-child(2)",
                "props": [("text-align", "left")],
            },
            {
                "selector": "tbody tr:nth-child(n+2) td:nth-child(n+3)",
                "props": [("text-align", "right")],
            },
            {
                "selector": "tbody tr:nth-child(n+2) td:nth-child(1)",
                "props": [("font-weight","700")],
            },
            {
                "selector": "tbody tr td:nth-child(2)",
                "props": [("white-space","nowrap")],
            },
        ]

        #행
        spacer_rules1 = [
            {
                'selector': f'tr:nth-child({r})',
                'props': [('border-bottom','3px solid gray !important')]
               
            }
            for r in (2,6,10,14)
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
            for r in (1,3,4,5,7,8,9,11,12,13,15,16,17)
        ]

        styles += spacer_rules2

        # 구분 정리
        spacer_rules1 = [
            {
                'selector': f'tr:nth-child({r}) td:nth-child(1)',
                'props': [('border-right','3px solid gray !important')]
               
            }
            for r in (3,4,5,7,8,9,11,12,13,15,16,17)
        ]

        styles += spacer_rules1

        spacer_rules1 = [
            {
                'selector': f'tr:nth-child({r}) td:nth-child(2)',
                'props': [('border-bottom','3px solid gray !important')]
               
            }
            for r in (5,9,13,17)
        ]

        styles += spacer_rules1







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

        # 1) 모듈에서 표 생성
        disp = modules.build_f70(df_src, year, month)
        body = disp.copy()

        yy = str(year)[-2:]   # 예: 2025 -> "25"

        # -----------------------------
        # 2) 연도 / 월 / 전월비 컬럼 정보
        # -----------------------------

        # (1) 직전 3개 연도 라벨 (모듈과 맞춰야 함)
        #   예: "'22년", "'23년", "'24년 누계"
        prev_year_labels_all = []
        for y in range(year - 3, year):
            if y == year - 1:
                label = f"'{str(y)[-2:]}년 누계"
            else:
                label = f"'{str(y)[-2:]}년"
            prev_year_labels_all.append(label)

        # 실제 body에 존재하는 연도 컬럼만 사용
        prev_year_labels = [c for c in prev_year_labels_all if c in body.columns]

        # (2) 최근 3개월 (전전월, 전월, 선택월) – 연도 경계 포함
        #     예: 2026-02 선택 → (2025,12), (2026,1), (2026,2)
        month_pairs = []
        for k in (2, 1, 0):   # 전전월, 전월, 선택월
            y0 = year
            m0 = month - k
            while m0 <= 0:
                y0 -= 1
                m0 += 12
            month_pairs.append((y0, m0))

        # body에 실제로 존재하는 월 컬럼명만 사용
        #   예: "25년12월", "26년1월", "26년2월"
        month_cols = []   # (col_name, y, m)
        for y0, m0 in month_pairs:
            col = f"{str(y0)[-2:]}년{m0}월"
            if col in body.columns:
                month_cols.append((col, y0, m0))

        # (3) 숫자 포맷 대상 컬럼 (연도 + 최근 3개월)
        candidate_cols = prev_year_labels + [col for (col, _, _) in month_cols]
        NUM_COLS = [c for c in candidate_cols if c in body.columns]

        # (4) 전월비 계열 컬럼
        diff_cols = [c for c in body.columns if "전월비" in c and "%" not in c]
        pct_cols  = [c for c in body.columns if c.endswith("전월비%")]

        # -----------------------------
        # 3) 가짜 헤더 hdr1, hdr2 구성
        # -----------------------------
        hdr1 = {col: "" for col in body.columns}
        hdr2 = {col: "" for col in body.columns}

        # (1) 구분 컬럼 텍스트
        if "구분2" in hdr1:
            hdr1["구분2"] = "구분"

        # (2) 직전 3개 연도 1행 라벨
        for y_col in prev_year_labels:
            # '25년 누계 → '25년 으로 표시
            hdr1[y_col] = y_col.replace(" 누계", "")

        # (3) 최근 3개월: 연도가 바뀔 때만 1행에 'yy년, 2행에 "m월"
        last_year = None
        for col, y0, m0 in month_cols:
            yy_col = str(y0)[-2:]
            if y0 != last_year:
                hdr1[col] = f"'{yy_col}년"
                last_year = y0
            else:
                hdr1[col] = ""
            hdr2[col] = f"{m0}월"

        # (4) 전월비 / 전월비% 컬럼 헤더
        #     1행: "'yy.mm월" (선택연도 기준 라벨), 2행: "전월比" / "%"
        ym_group = []
        ym_group += [c for c in diff_cols if c in body.columns]
        ym_group += [c for c in pct_cols  if c in body.columns]

        first = True
        for c in ym_group:
            if first:
                hdr1[c] = f"'{yy}.{month}월"   # 예: '25.8월
                first = False
            else:
                hdr1[c] = ""

            if c in diff_cols:
                hdr2[c] = "전월比"
            else:
                hdr2[c] = "%"

        # body 맨 위에 hdr1, hdr2 추가
        hdr_df = pd.DataFrame([hdr1, hdr2])
        body = pd.concat([hdr_df, body], ignore_index=True)

        # =========================
        #  포맷팅 함수
        # =========================
        def fmt_num(v):
            try:
                v = float(v)
            except Exception:
                return ""
            return f"{v:,.0f}"

        def fmt_diff(v):
            try:
                v = float(v)
            except Exception:
                return ""
            if v < 0:
                return f'<span style="color:#d62728;">({abs(v):,.0f})</span>'
            return f"{v:,.0f}"

        def fmt_pct(v):
            try:
                v = float(v)
            except Exception:
                return ""
            return f"{v:.1f}%"

        # 0,1행 = 가짜 헤더
        data_rows = body.index >= 2

        # % 행 (있다면 처리, 없으면 전부 False)
        has_gubun2 = "구분2" in body.columns
        pct_rows_disp = (disp["구분2"] == "%") if "구분2" in disp.columns else pd.Series(False, index=disp.index)
        pct_rows_body = ((body["구분2"] == "%") & data_rows) if has_gubun2 else (body.index == -1)

        # (1) 일반 숫자행: 콤마
        for c in NUM_COLS:
            body.loc[data_rows & ~pct_rows_body, c] = (
                body.loc[data_rows & ~pct_rows_body, c].apply(fmt_num)
            )

        # (2) % 행: disp 원본 숫자 → 퍼센트 포맷
        for c in NUM_COLS:
            if c in disp.columns and pct_rows_body.any():
                raw_vals = disp.loc[pct_rows_disp, c].values
                body.loc[pct_rows_body, c] = [fmt_pct(v) for v in raw_vals]

        # (3) 전월비 (톤)
        for c in diff_cols:
            # 일반 행
            body.loc[data_rows & ~pct_rows_body, c] = (
                body.loc[data_rows & ~pct_rows_body, c].apply(fmt_diff)
            )
            # % 행은 pp 표기
            if pct_rows_body.any():
                def fmt_pp(v):
                    try:
                        v = float(v)
                    except Exception:
                        return ""
                    return f"{v:.1f}pp"
                body.loc[pct_rows_body, c] = body.loc[pct_rows_body, c].apply(fmt_pp)

        # (4) 전월비 % 컬럼
        for c in pct_cols:
            body.loc[data_rows, c] = body.loc[data_rows, c].apply(fmt_pct)

        # =========================
        #  스타일
        # =========================
        styles = [
            {"selector": "thead", "props": [("display", "none")]},
            {
                "selector": "tbody tr:nth-child(1) td",
                "props": [("font-weight","700"), ("text-align","center"),('border-top','3px solid gray !important')],
            },
            {
                "selector": "tbody tr:nth-child(2) td",
                "props": [("font-weight","700"), ("text-align","center")],
            },
            {
                "selector": "tbody tr:nth-child(n+2) td:nth-child(1), tbody tr:nth-child(n+2) td:nth-child(2)",
                "props": [("text-align", "left")],
            },
            {
                "selector": "tbody tr:nth-child(n+2) td:nth-child(n+3)",
                "props": [("text-align", "right")],
            },
            {
                "selector": "tbody tr:nth-child(n+2) td:nth-child(1)",
                "props": [("font-weight","700")],
            },
            {
                "selector": "tbody tr td:nth-child(2)",
                "props": [("white-space","nowrap")],
            },
        ]

        #행
        spacer_rules1 = [
            {
                'selector': f'tr:nth-child({r})',
                'props': [('border-bottom','3px solid gray !important')]
               
            }
            for r in (2,6,10,14)
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
            for r in (1,3,4,5,7,8,9,11,12,13,15,16,17,18)
        ]

        styles += spacer_rules2

                # 구분 정리
        spacer_rules1 = [
            {
                'selector': f'tr:nth-child({r}) td:nth-child(1)',
                'props': [('border-right','3px solid gray !important')]
               
            }
            for r in (3,4,5,7,8,9,11,12,13,15,16,17,18)
        ]

        styles += spacer_rules1

        spacer_rules1 = [
            {
                'selector': f'tr:nth-child({r}) td:nth-child(2)',
                'props': [('border-bottom','3px solid gray !important')]
               
            }
            for r in (5,9,13,18)
        ]

        styles += spacer_rules1






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

        # 1) 모듈에서 표 생성
        disp = modules.build_f71(df_src, year, month)
        body = disp.copy()

        yy = str(year)[-2:]   # 예: 2025 -> "25"

        # -----------------------------
        # 2) 연도 / 월 / 전월비 컬럼 정보
        # -----------------------------

        # (1) 직전 3개 연도 라벨 (모듈과 맞춰야 함)
        #   예: "'22년", "'23년", "'24년 누계"
        prev_year_labels_all = []
        for y in range(year - 3, year):
            if y == year - 1:
                label = f"'{str(y)[-2:]}년 누계"
            else:
                label = f"'{str(y)[-2:]}년"
            prev_year_labels_all.append(label)

        # 실제 body에 존재하는 연도 컬럼만 사용
        prev_year_labels = [c for c in prev_year_labels_all if c in body.columns]

        # (2) 최근 3개월 (전전월, 전월, 선택월) – 연도 경계 포함
        #     예: 2026-02 선택 → (2025,12), (2026,1), (2026,2)
        month_pairs = []
        for k in (2, 1, 0):   # 전전월, 전월, 선택월
            y0 = year
            m0 = month - k
            while m0 <= 0:
                y0 -= 1
                m0 += 12
            month_pairs.append((y0, m0))

        # body에 실제로 존재하는 월 컬럼명만 사용
        #   예: "25년12월", "26년1월", "26년2월"
        month_cols = []   # (col_name, y, m)
        for y0, m0 in month_pairs:
            col = f"{str(y0)[-2:]}년{m0}월"
            if col in body.columns:
                month_cols.append((col, y0, m0))

        # (3) 숫자 포맷 대상 컬럼 (연도 + 최근 3개월)
        candidate_cols = prev_year_labels + [col for (col, _, _) in month_cols]
        NUM_COLS = [c for c in candidate_cols if c in body.columns]

        # (4) 전월비 계열 컬럼
        diff_cols = [c for c in body.columns if "전월비" in c and "%" not in c]
        pct_cols  = [c for c in body.columns if c.endswith("전월비%")]

        # -----------------------------
        # 3) 가짜 헤더 hdr1, hdr2 구성
        # -----------------------------
        hdr1 = {col: "" for col in body.columns}
        hdr2 = {col: "" for col in body.columns}

        # (1) 구분 컬럼 텍스트
        if "구분2" in hdr1:
            hdr1["구분2"] = "구분"

        # (2) 직전 3개 연도 1행 라벨
        for y_col in prev_year_labels:
            # '25년 누계 → '25년 으로 표시
            hdr1[y_col] = y_col.replace(" 누계", "")

        # (3) 최근 3개월: 연도가 바뀔 때만 1행에 'yy년, 2행에 "m월"
        last_year = None
        for col, y0, m0 in month_cols:
            yy_col = str(y0)[-2:]
            if y0 != last_year:
                hdr1[col] = f"'{yy_col}년"
                last_year = y0
            else:
                hdr1[col] = ""
            hdr2[col] = f"{m0}월"

        # (4) 전월비 / 전월비% 컬럼 헤더
        #     1행: "'yy.mm월" (선택연도 기준 라벨), 2행: "전월比" / "%"
        ym_group = []
        ym_group += [c for c in diff_cols if c in body.columns]
        ym_group += [c for c in pct_cols  if c in body.columns]

        first = True
        for c in ym_group:
            if first:
                hdr1[c] = f"'{yy}.{month}월"   # 예: '25.8월
                first = False
            else:
                hdr1[c] = ""

            if c in diff_cols:
                hdr2[c] = "전월比"
            else:
                hdr2[c] = "%"

        # body 맨 위에 hdr1, hdr2 추가
        hdr_df = pd.DataFrame([hdr1, hdr2])
        body = pd.concat([hdr_df, body], ignore_index=True)

        # =========================
        #  포맷팅 함수
        # =========================
        def fmt_num(v):
            try:
                v = float(v)
            except Exception:
                return ""
            return f"{v:,.0f}"

        def fmt_diff(v):
            try:
                v = float(v)
            except Exception:
                return ""
            if v < 0:
                return f'<span style="color:#d62728;">({abs(v):,.0f})</span>'
            return f"{v:,.0f}"

        def fmt_pct(v):
            try:
                v = float(v)
            except Exception:
                return ""
            return f"{v:.1f}%"

        # 0,1행 = 가짜 헤더
        data_rows = body.index >= 2

        # % 행(비율행) – 없을 수도 있으니 방어
        has_gubun2 = "구분2" in body.columns
        pct_rows_disp = (disp["구분2"] == "%") if "구분2" in disp.columns else pd.Series(False, index=disp.index)
        pct_rows_body = ((body["구분2"] == "%") & data_rows) if has_gubun2 else (body.index == -1)

        # (1) 일반 숫자행: 콤마
        for c in NUM_COLS:
            body.loc[data_rows & ~pct_rows_body, c] = (
                body.loc[data_rows & ~pct_rows_body, c].apply(fmt_num)
            )

        # (2) % 행: disp 원본 숫자 → 퍼센트 포맷
        for c in NUM_COLS:
            if c in disp.columns and pct_rows_body.any():
                raw_vals = disp.loc[pct_rows_disp, c].values
                body.loc[pct_rows_body, c] = [fmt_pct(v) for v in raw_vals]

        # (3) 전월비 (톤)
        for c in diff_cols:
            # 일반 행
            body.loc[data_rows & ~pct_rows_body, c] = (
                body.loc[data_rows & ~pct_rows_body, c].apply(fmt_diff)
            )
            # % 행은 pp 표기
            if pct_rows_body.any():
                def fmt_pp(v):
                    try:
                        v = float(v)
                    except Exception:
                        return ""
                    return f"{v:.1f}pp"
                body.loc[pct_rows_body, c] = body.loc[pct_rows_body, c].apply(fmt_pp)

        # (4) 전월비 % 컬럼
        for c in pct_cols:
            body.loc[data_rows, c] = body.loc[data_rows, c].apply(fmt_pct)

        # =========================
        #  스타일
        # =========================
        styles = [
            {"selector": "thead", "props": [("display", "none")]},
            {
                "selector": "tbody tr:nth-child(1) td",
                "props": [("font-weight","700"), ("text-align","center"),('border-top','3px solid gray !important')],
            },
            {
                "selector": "tbody tr:nth-child(2) td",
                "props": [("font-weight","700"), ("text-align","center")],
            },
            {
                "selector": "tbody tr:nth-child(n+2) td:nth-child(1), tbody tr:nth-child(n+2) td:nth-child(2)",
                "props": [("text-align", "left")],
            },
            {
                "selector": "tbody tr:nth-child(n+2) td:nth-child(n+3)",
                "props": [("text-align", "right")],
            },
            {
                "selector": "tbody tr:nth-child(n+2) td:nth-child(1)",
                "props": [("font-weight","700")],
            },
            {
                "selector": "tbody tr td:nth-child(2)",
                "props": [("white-space","nowrap")],
            },
        ]

        #행
        spacer_rules1 = [
            {
                'selector': f'tr:nth-child({r})',
                'props': [('border-bottom','3px solid gray !important')]
               
            }
            for r in (2,6,10,14)
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
            for r in (1,3,4,5,7,8,9,11,12,13,15,16,17)
        ]

        styles += spacer_rules2

                # 구분 정리
        spacer_rules1 = [
            {
                'selector': f'tr:nth-child({r}) td:nth-child(1)',
                'props': [('border-right','3px solid gray !important')]
               
            }
            for r in (3,4,5,7,8,9,11,12,13,15,16,17)
        ]

        styles += spacer_rules1

        spacer_rules1 = [
            {
                'selector': f'tr:nth-child({r}) td:nth-child(2)',
                'props': [('border-bottom','3px solid gray !important')]
               
            }
            for r in (5,9,13,17)
        ]

        styles += spacer_rules1





        display_styled_df(body, styles=styles, already_flat=True)
        display_memo('f_71', year, month)

    except Exception as e:
        st.error(f"제품/임가공 판매현황 표 생성 오류: {e}")

    st.divider()



with t6:

    st.markdown("<h4> 1) 재고자산 현황 남통법인</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 톤, 백만원, %]</div>", unsafe_allow_html=True)



    try:
        file_name = st.secrets["sheets"]["f_75_76_77"]  
        raw = pd.read_csv(file_name, dtype=str)

        importlib.invalidate_caches()
        importlib.reload(modules)


        inv = modules.create_inv_table_from_company(
            year=int(st.session_state['year']),    
            month=int(st.session_state['month']),  
            data=raw,
            company_name='남통',
        )

        # 2) 표시용 복사 & 인덱스 풀기
        disp = inv.copy().reset_index()  
        SPACER = "__spacer__"
        disp.insert(0, SPACER, "")

        # 3) 숫자 포맷 함수
        def fmt_amt(x):
            """금액: 0은 공란, 음수는 괄호, 천단위 콤마"""
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
            """증감률: 0 / NaN 은 공란, 정수 %"""
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
            if c in (SPACER, '구분2', '구분3'):
                continue
            if c == '증감률':
                disp[c] = disp[c].apply(fmt_rate)
            else:
                disp[c] = disp[c].apply(fmt_amt)

        # 5) 헤더 3단 구성
        cols = disp.columns.tolist()
        c_idx = {c: i for i, c in enumerate(cols)}

        spacer_i = c_idx[SPACER]
        big_i    = c_idx['구분2']
        mid_i    = c_idx['구분3']
        diff_i   = c_idx['증량']
        rate_i   = c_idx['증감률']


        used_m   = int(inv.attrs.get('used_month'))
        prev_m   = int(inv.attrs.get('prev_month'))
        prev2_m  = int(inv.attrs.get('prev2_month'))
        year_int = int(inv.attrs.get('base_year'))
        company  = inv.attrs.get('company', '남통')

        yy_curr  = f"{year_int % 100:02d}"
        yy_m1    = f"{(year_int - 1) % 100:02d}"
        yy_m2    = f"{(year_int - 2) % 100:02d}"
        yy_m3    = f"{(year_int - 3) % 100:02d}"
        yy_m4    = f"{(year_int - 4) % 100:02d}"


        col_yend_m4 = f"'{yy_m4}년말"
        col_yend_m3 = f"'{yy_m3}년말"
        col_yend_m2 = f"'{yy_m2}년말"
        col_yend_m1 = f"'{yy_m1}년말"


        col_m3 = f"{prev2_m}월"
        col_m2 = f"{prev_m}월"
        col_m1 = f"{used_m}월"

        y4_i = c_idx[col_yend_m4]
        y3_i = c_idx[col_yend_m3]
        y2_i = c_idx[col_yend_m2]
        y1_i = c_idx[col_yend_m1]
        m3_i = c_idx[col_m3]
        m2_i = c_idx[col_m2]
        m1_i = c_idx[col_m1]


        hdr1 = [''] * len(cols)
        hdr2 = [''] * len(cols)
        hdr3 = [''] * len(cols)


        hdr2[big_i] = f"[{company}]"     
        
        hdr2[y4_i] = col_yend_m4         
        hdr2[y3_i] = col_yend_m3
        hdr2[y2_i] = col_yend_m2
        hdr2[y1_i] = col_yend_m1


        used_year = year_int

        m1_year = used_year

       
        m2_year = used_year
        if prev_m > used_m:
            m2_year = used_year - 1

      
        m3_year = m2_year
        if prev2_m > prev_m:
            m3_year = m2_year - 1

        hdr1 = [''] * len(cols)  

        year_runs = [
            (m3_i, m3_year),
            (m2_i, m2_year),
            (m1_i, m1_year),
        ]

        last_year = None
        for col_i, y in year_runs:
            if y != last_year:
                hdr1[col_i] = f"'{y % 100:02d}년"   
                last_year = y
       
       
        hdr2[m3_i] = f"{prev2_m}월"      
        hdr2[m2_i] = f"{prev_m}월"       
        hdr2[m1_i] = f"{used_m}월"       


        hdr3[m1_i]   = "중량"
        hdr3[diff_i] = "증감"
        hdr3[rate_i] = "증감률"


        # 나머지 셀들은 공백("") 유지

        hdr_df   = pd.DataFrame([hdr1, hdr2, hdr3], columns=cols)
        disp_vis = pd.concat([hdr_df, disp], ignore_index=True)



        styles = [
            {'selector': 'thead', 'props': [('display', 'none')]},
            
            {
                "selector": "tbody tr td:nth-child(1)",
                "props": [
                    ("border-right", "2px solid white !important"),
                ],
            },

            # 헤더 1·2·3행
            {
                'selector': 'tbody tr:nth-child(1) td',
                'props': [('text-align', 'center'),
                        ('padding', '4px 6px'),
                        ('font-weight', '600'),
                        ('border-top','3px solid gray !important')],
            },
            {
                'selector': 'tbody tr:nth-child(2) td',
                'props': [('text-align', 'center'),
                        ('padding', '8px 6px'),
                        ('font-weight', '600')]
            },
            {
                'selector': 'tbody tr:nth-child(3) td',
                'props': [('text-align', 'center'),
                        ('padding', '10px 6px'),
                        ('font-weight', '600')]
            },

            # 1열(spacer)은 얇게
            {
                'selector': 'tbody td:nth-child(1)',
                'props': [('width', '8px'), ('border-right', '0')]
            },

            # 본문: 4행 이후
            {
                'selector': 'tbody tr:nth-child(n+4) td',
                'props': [('line-height', '1.4'),
                        ('padding', '6px 8px'),
                        ('text-align', 'right')]
            },
            {
                # 구분2, 구분3 열은 왼쪽 정렬
                'selector': 'tbody tr:nth-child(n+4) td:nth-child(2), tbody tr:nth-child(n+4) td:nth-child(3)',
                'props': [('text-align', 'left')]
            },
        ]

                #행
        spacer_rules1 = [
            {
                'selector': f'tr:nth-child({r})',
                'props': [('border-bottom','3px solid gray !important')]
               
            }
            for r in (3,7,11,15)
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
            for r in (3,4,5,6,8,9,10,11,12,13,14,15,16)
            for i in (1,2)

        ]

        styles += spacer_rules2

                # 구분 정리
        spacer_rules1 = [
            {
                'selector': f'tr:nth-child({r}) td:nth-child(2)',
                'props': [('border-right','3px solid gray !important')]
               
            }
            for r in (4,5,6,8,9,10,12,13,14)
        ]

        styles += spacer_rules1

        spacer_rules1 = [
            {
                'selector': f'tr:nth-child({r}) td:nth-child(3)',
                'props': [('border-bottom','3px solid gray !important')]
               
            }
            for r in (6,10,14,18)
        ]

        styles += spacer_rules1

        for i in [6,10,14]:
            disp_vis.iloc[i, 2] = ""

        display_styled_df(
            disp_vis,
            styles=styles,
            already_flat=True,
        )
        display_memo('f_75', year, month)


    except Exception as e:
        st.error(f"재고자산 현황 남통법인 표 생성 중 오류: {e}")

    st.divider()

    st.markdown("<h4> 2) 재고자산 현황 천진법인</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 톤, 백만원, %]</div>", unsafe_allow_html=True)


    try:
        # 0) 데이터 로딩
        file_name = st.secrets["sheets"]["f_75_76_77"]  
        raw = pd.read_csv(file_name, dtype=str)




        inv = modules.create_inv_table_from_company(
            year=int(st.session_state['year']),   
            month=int(st.session_state['month']), 
            data=raw,
            company_name='천진',
        )

        # 2) 표시용 복사 & 인덱스 풀기
        disp = inv.copy().reset_index()  
        SPACER = "__spacer__"
        disp.insert(0, SPACER, "")

        # 3) 숫자 포맷 함수
        def fmt_amt(x):
            """금액: 0은 공란, 음수는 괄호, 천단위 콤마"""
            if pd.isna(x):
                return ""
            try:
                v = float(x)
            except Exception:
                return x
            if v == 0:
                return "0"
            v_rounded = int(round(v))
            return f"({abs(v_rounded):,})" if v_rounded < 0 else f"{v_rounded:,}"

        def fmt_rate(x):
            """증감률: 0 / NaN 은 공란, 정수 %"""
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
            if c in (SPACER, '구분2', '구분3'):
                continue
            if c == '증감률':
                disp[c] = disp[c].apply(fmt_rate)
            else:
                disp[c] = disp[c].apply(fmt_amt)

        # 5) 헤더 3단 구성
        cols = disp.columns.tolist()
        c_idx = {c: i for i, c in enumerate(cols)}

        spacer_i = c_idx[SPACER]
        big_i    = c_idx['구분2']
        mid_i    = c_idx['구분3']
        diff_i   = c_idx['증량']
        rate_i   = c_idx['증감률']


        used_m   = int(inv.attrs.get('used_month'))
        prev_m   = int(inv.attrs.get('prev_month'))
        prev2_m  = int(inv.attrs.get('prev2_month'))
        year_int = int(inv.attrs.get('base_year'))
        company  = inv.attrs.get('company', '남통')

        yy_curr  = f"{year_int % 100:02d}"
        yy_m1    = f"{(year_int - 1) % 100:02d}"
        yy_m2    = f"{(year_int - 2) % 100:02d}"
        yy_m3    = f"{(year_int - 3) % 100:02d}"
        yy_m4    = f"{(year_int - 4) % 100:02d}"


        col_yend_m4 = f"'{yy_m4}년말"
        col_yend_m3 = f"'{yy_m3}년말"
        col_yend_m2 = f"'{yy_m2}년말"
        col_yend_m1 = f"'{yy_m1}년말"


        col_m3 = f"{prev2_m}월"
        col_m2 = f"{prev_m}월"
        col_m1 = f"{used_m}월"

        y4_i = c_idx[col_yend_m4]
        y3_i = c_idx[col_yend_m3]
        y2_i = c_idx[col_yend_m2]
        y1_i = c_idx[col_yend_m1]
        m3_i = c_idx[col_m3]
        m2_i = c_idx[col_m2]
        m1_i = c_idx[col_m1]


        hdr1 = [''] * len(cols)
        hdr2 = [''] * len(cols)
        hdr3 = [''] * len(cols)


        hdr2[big_i] = f"[{company}]"     
        
        hdr2[y4_i] = col_yend_m4         
        hdr2[y3_i] = col_yend_m3
        hdr2[y2_i] = col_yend_m2
        hdr2[y1_i] = col_yend_m1


        used_year = year_int

        m1_year = used_year

       
        m2_year = used_year
        if prev_m > used_m:
            m2_year = used_year - 1

      
        m3_year = m2_year
        if prev2_m > prev_m:
            m3_year = m2_year - 1

        hdr1 = [''] * len(cols)  

        year_runs = [
            (m3_i, m3_year),
            (m2_i, m2_year),
            (m1_i, m1_year),
        ]

        last_year = None
        for col_i, y in year_runs:
            if y != last_year:
                hdr1[col_i] = f"'{y % 100:02d}년"   
                last_year = y
       
       
        hdr2[m3_i] = f"{prev2_m}월"      
        hdr2[m2_i] = f"{prev_m}월"       
        hdr2[m1_i] = f"{used_m}월"       


        hdr3[m1_i]   = "중량"
        hdr3[diff_i] = "증감"
        hdr3[rate_i] = "증감률"


        # 나머지 셀들은 공백("") 유지

        hdr_df   = pd.DataFrame([hdr1, hdr2, hdr3], columns=cols)
        disp_vis = pd.concat([hdr_df, disp], ignore_index=True)



        styles = [
            {'selector': 'thead', 'props': [('display', 'none')]},
            
            {
                "selector": "tbody tr td:nth-child(1)",
                "props": [
                    ("border-right", "2px solid white !important"),
                ],
            },

            # 헤더 1·2·3행
            {
                'selector': 'tbody tr:nth-child(1) td',
                'props': [('text-align', 'center'),
                        ('padding', '4px 6px'),
                        ('font-weight', '600'),
                        ('border-top','3px solid gray !important')]
            },
            {
                'selector': 'tbody tr:nth-child(2) td',
                'props': [('text-align', 'center'),
                        ('padding', '8px 6px'),
                        ('font-weight', '600')]
            },
            {
                'selector': 'tbody tr:nth-child(3) td',
                'props': [('text-align', 'center'),
                        ('padding', '10px 6px'),
                        ('font-weight', '600')]
            },

            # 1열(spacer)은 얇게
            {
                'selector': 'tbody td:nth-child(1)',
                'props': [('width', '8px'), ('border-right', '0')]
            },

            # 본문: 4행 이후
            {
                'selector': 'tbody tr:nth-child(n+4) td',
                'props': [('line-height', '1.4'),
                        ('padding', '6px 8px'),
                        ('text-align', 'right')]
            },
            {
                # 구분2, 구분3 열은 왼쪽 정렬
                'selector': 'tbody tr:nth-child(n+4) td:nth-child(2), tbody tr:nth-child(n+4) td:nth-child(3)',
                'props': [('text-align', 'left')]
            },
        ]

                #행
        spacer_rules1 = [
            {
                'selector': f'tr:nth-child({r})',
                'props': [('border-bottom','3px solid gray !important')]
               
            }
            for r in (3,7,11,15)
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
            for r in (3,4,5,6,8,9,10,11,12,13,14,15,16)
            for i in (1,2)

        ]

        styles += spacer_rules2

                # 구분 정리
        spacer_rules1 = [
            {
                'selector': f'tr:nth-child({r}) td:nth-child(2)',
                'props': [('border-right','3px solid gray !important')]
               
            }
            for r in (4,5,6,8,9,10,12,13,14)
        ]

        styles += spacer_rules1

        spacer_rules1 = [
            {
                'selector': f'tr:nth-child({r}) td:nth-child(3)',
                'props': [('border-bottom','3px solid gray !important')]
               
            }
            for r in (6,10,14,18)
        ]

        styles += spacer_rules1

        for i in [6,10,14]:
            disp_vis.iloc[i, 2] = ""

        display_styled_df(
            disp_vis,
            styles=styles,
            already_flat=True,
        )
        display_memo('f_76', year, month)


    except Exception as e:
        st.error(f"재고자산 현황 천진법인 표 생성 중 오류: {e}")

    st.divider()


    st.markdown("<h4> 3) 재고자산 현황 태국법인</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 톤, 백만원, %]</div>", unsafe_allow_html=True)


    try:
        # 0) 데이터 로딩
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
        SPACER = "__spacer__"
        disp.insert(0, SPACER, "")

        # 3) 숫자 포맷 함수
        def fmt_amt(x):
            """금액: 0은 공란, 음수는 괄호, 천단위 콤마"""
            if pd.isna(x):
                return ""
            try:
                v = float(x)
            except Exception:
                return x
            if v == 0:
                return "0"
            v_rounded = int(round(v))
            return f"({abs(v_rounded):,})" if v_rounded < 0 else f"{v_rounded:,}"

        def fmt_rate(x):
            """증감률: 0 / NaN 은 공란, 정수 %"""
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
            if c in (SPACER, '구분2', '구분3'):
                continue
            if c == '증감률':
                disp[c] = disp[c].apply(fmt_rate)
            else:
                disp[c] = disp[c].apply(fmt_amt)

        # 5) 헤더 3단 구성
        cols = disp.columns.tolist()
        c_idx = {c: i for i, c in enumerate(cols)}

        spacer_i = c_idx[SPACER]
        big_i    = c_idx['구분2']
        mid_i    = c_idx['구분3']
        diff_i   = c_idx['증량']
        rate_i   = c_idx['증감률']


        used_m   = int(inv.attrs.get('used_month'))
        prev_m   = int(inv.attrs.get('prev_month'))
        prev2_m  = int(inv.attrs.get('prev2_month'))
        year_int = int(inv.attrs.get('base_year'))
        company  = inv.attrs.get('company', '태국')

        yy_curr  = f"{year_int % 100:02d}"
        yy_m1    = f"{(year_int - 1) % 100:02d}"
        yy_m2    = f"{(year_int - 2) % 100:02d}"
        yy_m3    = f"{(year_int - 3) % 100:02d}"
        yy_m4    = f"{(year_int - 4) % 100:02d}"


        col_yend_m4 = f"'{yy_m4}년말"
        col_yend_m3 = f"'{yy_m3}년말"
        col_yend_m2 = f"'{yy_m2}년말"
        col_yend_m1 = f"'{yy_m1}년말"


        col_m3 = f"{prev2_m}월"
        col_m2 = f"{prev_m}월"
        col_m1 = f"{used_m}월"

        y4_i = c_idx[col_yend_m4]
        y3_i = c_idx[col_yend_m3]
        y2_i = c_idx[col_yend_m2]
        y1_i = c_idx[col_yend_m1]
        m3_i = c_idx[col_m3]
        m2_i = c_idx[col_m2]
        m1_i = c_idx[col_m1]


        hdr1 = [''] * len(cols)
        hdr2 = [''] * len(cols)
        hdr3 = [''] * len(cols)


        hdr2[big_i] = f"[{company}]"     
        
        hdr2[y4_i] = col_yend_m4         
        hdr2[y3_i] = col_yend_m3
        hdr2[y2_i] = col_yend_m2
        hdr2[y1_i] = col_yend_m1


        used_year = year_int

        m1_year = used_year

       
        m2_year = used_year
        if prev_m > used_m:
            m2_year = used_year - 1

      
        m3_year = m2_year
        if prev2_m > prev_m:
            m3_year = m2_year - 1

        hdr1 = [''] * len(cols)  

        year_runs = [
            (m3_i, m3_year),
            (m2_i, m2_year),
            (m1_i, m1_year),
        ]

        last_year = None
        for col_i, y in year_runs:
            if y != last_year:
                hdr1[col_i] = f"'{y % 100:02d}년"   
                last_year = y
       
       
        hdr2[m3_i] = f"{prev2_m}월"      
        hdr2[m2_i] = f"{prev_m}월"       
        hdr2[m1_i] = f"{used_m}월"       


        hdr3[m1_i]   = "중량"
        hdr3[diff_i] = "증감"
        hdr3[rate_i] = "증감률"


        # 나머지 셀들은 공백("") 유지

        hdr_df   = pd.DataFrame([hdr1, hdr2, hdr3], columns=cols)
        disp_vis = pd.concat([hdr_df, disp], ignore_index=True)


        styles = [
            {'selector': 'thead', 'props': [('display', 'none')]},
            
            {
                "selector": "tbody tr td:nth-child(1)",
                "props": [
                    ("border-right", "2px solid white !important"),
                ],
            },

            # 헤더 1·2·3행
            {
                'selector': 'tbody tr:nth-child(1) td',
                'props': [('text-align', 'center'),
                        ('padding', '4px 6px'),
                        ('font-weight', '600'),
                        ('border-top','3px solid gray !important')]
            },
            {
                'selector': 'tbody tr:nth-child(2) td',
                'props': [('text-align', 'center'),
                        ('padding', '8px 6px'),
                        ('font-weight', '600')]
            },
            {
                'selector': 'tbody tr:nth-child(3) td',
                'props': [('text-align', 'center'),
                        ('padding', '10px 6px'),
                        ('font-weight', '600')]
            },

            # 1열(spacer)은 얇게
            {
                'selector': 'tbody td:nth-child(1)',
                'props': [('width', '8px'), ('border-right', '0')]
            },

            # 본문: 4행 이후
            {
                'selector': 'tbody tr:nth-child(n+4) td',
                'props': [('line-height', '1.4'),
                        ('padding', '6px 8px'),
                        ('text-align', 'right')]
            },
            {
                # 구분2, 구분3 열은 왼쪽 정렬
                'selector': 'tbody tr:nth-child(n+4) td:nth-child(2), tbody tr:nth-child(n+4) td:nth-child(3)',
                'props': [('text-align', 'left')]
            },
        ]

                #행
        spacer_rules1 = [
            {
                'selector': f'tr:nth-child({r})',
                'props': [('border-bottom','3px solid gray !important')]
               
            }
            for r in (3,7,11,15)
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
            for r in (3,4,5,6,8,9,10,11,12,13,14,15,16)
            for i in (1,2)

        ]

        styles += spacer_rules2

                # 구분 정리
        spacer_rules1 = [
            {
                'selector': f'tr:nth-child({r}) td:nth-child(2)',
                'props': [('border-right','3px solid gray !important')]
               
            }
            for r in (4,5,6,8,9,10,12,13,14)
        ]

        styles += spacer_rules1

        spacer_rules1 = [
            {
                'selector': f'tr:nth-child({r}) td:nth-child(3)',
                'props': [('border-bottom','3px solid gray !important')]
               
            }
            for r in (6,10,14,18)
        ]

        styles += spacer_rules1

        for i in [6,10,14]:
            disp_vis.iloc[i, 2] = ""


        display_styled_df(
            disp_vis,
            styles=styles,
            already_flat=True,
        )
        display_memo('f_77', year, month)


    except Exception as e:
        st.error(f"재고자산 현황 태국법인 표 생성 중 오류: {e}")

    st.divider()



    st.markdown("<h4> 4) 부적합 및 장기재고 현황 남통법인</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 톤, 백만원, %]</div>", unsafe_allow_html=True)


    try:
        # 0) 데이터 로딩
        file_name = st.secrets["sheets"]["f_78_79_80"]  
        raw = pd.read_csv(file_name, dtype=str)


        inv = modules.create_defect_longinv_table_from_company(
            year=int(st.session_state['year']),    
            month=int(st.session_state['month']),  
            data=raw,
            company_name='남통',                  
        )


        disp = inv.copy().reset_index()
        SPACER = "__spacer__"
        disp.insert(0, SPACER, "")


        def fmt_amt(x):
            """금액/수량: 0은 0, 음수는 괄호, 천단위 콤마"""
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
            """증감률: NaN / 0 / '0' 은 '-', 소수 1자리 %"""
            # NaN
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
            if c in (SPACER, '구분2', '구분3'):
                continue
            if c == '증감률':
                disp[c] = disp[c].apply(fmt_rate)
            else:
                disp[c] = disp[c].apply(fmt_amt)


                # 5) 헤더 3단 구성
        cols = disp.columns.tolist()
        c_idx = {c: i for i, c in enumerate(cols)}

        spacer_i = c_idx[SPACER]
        big_i    = c_idx['구분2']
        mid_i    = c_idx['구분3']

        # 컬럼 인덱스 및 메타
        year_int = int(inv.attrs.get('base_year'))     # 연말 컬럼 기준 연도
        used_m   = int(inv.attrs.get('used_month'))    # 선택월
        prev_m   = int(inv.attrs.get('prev_month'))    # 전월
        prev2_m  = int(inv.attrs.get('prev2_month'))   # 전전월
        used_y   = int(inv.attrs.get('used_year'))     # 선택월이 속한 실제 연도
        company  = inv.attrs.get('company', '남통')

        # 연말 컬럼 이름
        yy_m1 = f"{(year_int - 1) % 100:02d}"
        yy_m2 = f"{(year_int - 2) % 100:02d}"
        yy_m3 = f"{(year_int - 3) % 100:02d}"
        yy_m4 = f"{(year_int - 4) % 100:02d}"

        col_yend_m4 = f"'{yy_m4}년말"
        col_yend_m3 = f"'{yy_m3}년말"
        col_yend_m2 = f"'{yy_m2}년말"
        col_yend_m1 = f"'{yy_m1}년말"

        # 월 컬럼 이름
        col_prev2 = f"{prev2_m}월"
        col_prev  = f"{prev_m}월"

        # 인덱스
        y4_i = c_idx[col_yend_m4]
        y3_i = c_idx[col_yend_m3]
        y2_i = c_idx[col_yend_m2]
        y1_i = c_idx[col_yend_m1]

        prev2_i = c_idx[col_prev2]
        prev_i  = c_idx[col_prev]

        gen_i   = c_idx['발생']
        used_i  = c_idx['소진']
        end_i   = c_idx['기말']
        rate_i  = c_idx['증감률']

        hdr1 = [''] * len(cols)
        hdr2 = [''] * len(cols)
        hdr3 = [''] * len(cols)

        # 회사명
        hdr2[big_i] = f"[{company}]"

        # 연말 헤더 ('xx년말)
        hdr2[y4_i] = col_yend_m4
        hdr2[y3_i] = col_yend_m3
        hdr2[y2_i] = col_yend_m2
        hdr2[y1_i] = col_yend_m1

        # ─────────────────────────────
        # ① prev2 / prev / 선택월 그룹의 "연도" 계산
        #    (선택월 연도 = used_y 기준, 월이 되돌아가면 연도 -1)
        # ─────────────────────────────
        used_year = used_y          # 선택월이 속한 실제 연도

        m_used = used_m             # 선택월
        m_prev = prev_m             # 전월
        m_prev2 = prev2_m           # 전전월

        # 선택월 연도
        m1_year = used_year

        # 전월 연도
        m2_year = used_year
        if m_prev > m_used:         # 1월 선택, 전월이 12월인 경우 등
            m2_year = used_year - 1

        # 전전월 연도
        m3_year = m2_year
        if m_prev2 > m_prev:        # 또 한 번 연도 경계 넘어가는 경우
            m3_year = m2_year - 1

        # ─────────────────────────────
        # ② 1행 헤더: 연도가 바뀌는 첫 컬럼에만 'yy년 표시
        #    prev2 → prev → (선택월 그룹의 첫 컬럼: 발생)
        # ─────────────────────────────
        year_runs = [
            (prev2_i, m3_year),
            (prev_i,  m2_year),
            (gen_i,   m1_year),     # 선택월 그룹은 '발생' 위에만 연도 표시
        ]

        last_year = None
        for col_i, y in year_runs:
            if y != last_year:
                hdr1[col_i] = f"'{y % 100:02d}년"
                last_year = y

        # ─────────────────────────────
        # ③ 2행 헤더: 월 / 선택월 그룹 라벨
        # ─────────────────────────────
        # 전전월 / 전월
        hdr2[prev2_i] = f"{prev2_m}월"
        hdr2[prev_i]  = f"{prev_m}월"

        # 선택월 그룹(발생·소진·기말·증감률)
        used_month_label = f"{used_m}월"
        for idx in (gen_i, used_i, end_i, rate_i):
            hdr2[idx] = used_month_label

        # ─────────────────────────────
        # ④ 3행 헤더: 항목명
        # ─────────────────────────────
        hdr3[gen_i]  = "발생"
        hdr3[used_i] = "소진"
        hdr3[end_i]  = "기말"
        hdr3[rate_i] = "증감률"

        # 최종 헤더 DF + 본문 결합
        hdr_df   = pd.DataFrame([hdr1, hdr2, hdr3], columns=cols)
        disp_vis = pd.concat([hdr_df, disp], ignore_index=True)


        styles = [
            {'selector': 'thead', 'props': [('display', 'none')]},

            {
                "selector": "tbody tr td:nth-child(1)",
                "props": [
                    ("border-right", "2px solid white !important"),
                ],
            },

            # 헤더 1·2·3 행
            {
                'selector': 'tbody tr:nth-child(1) td',
                'props': [
                    ('text-align', 'center'),
                    ('padding', '4px 6px'),
                    ('font-weight', '600'),
                    ('border-top','3px solid gray !important'),
                ],
            },
            {
                'selector': 'tbody tr:nth-child(2) td',
                'props': [
                    ('text-align', 'center'),
                    ('padding', '8px 6px'),
                    ('font-weight', '600'),
                ],
            },
            {
                'selector': 'tbody tr:nth-child(3) td',
                'props': [
                    ('text-align', 'center'),
                    ('padding', '10px 6px'),
                    ('font-weight', '600'),
                ],
            },






            # spacer 열
            {
                'selector': 'tbody td:nth-child(1)',
                'props': [('width', '8px'), ('border-right', '0')],
            },

            # 본문(4행 이후)
            {
                'selector': 'tbody tr:nth-child(n+4) td',
                'props': [
                    ('line-height', '1.4'),
                    ('padding', '6px 8px'),
                    ('text-align', 'right'),
                ],
            },
            {
                # 구분2, 구분3 열은 왼쪽 정렬
                'selector': 'tbody tr:nth-child(n+4) td:nth-child(2), tbody tr:nth-child(n+4) td:nth-child(3)',
                'props': [('text-align', 'left')],
            },
        ]

                #행
        spacer_rules1 = [
            {
                'selector': f'tr:nth-child({r})',
                'props': [('border-bottom','3px solid gray !important')]
               
            }
            for r in (3,11)
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
            for r in (3,4,5,6,7,8,9,10,12,13,14,15)
            for i in (1,2)

        ]

        styles += spacer_rules2

                # 구분 정리
        spacer_rules1 = [
            {
                'selector': f'tr:nth-child({r}) td:nth-child(2)',
                'props': [('border-right','3px solid gray !important')]
               
            }
            for r in (4,5,6,7,8,9,10,12,13,14)
        ]

        styles += spacer_rules1

        spacer_rules1 = [
            {
                'selector': f'tr:nth-child({r}) td:nth-child(3)',
                'props': [('border-bottom','3px solid gray !important')]
               
            }
            for r in (4,10,14)
        ]

        styles += spacer_rules1

        spacer_rules4 =[
                    {
                'selector': 'tbody td:nth-child(3)',
                'props': [
                    ('min-width', '180px'),
                    ('width', '180px'),
                    ('max-width', '180px'),

                ]
            }
        ]

        styles += spacer_rules4

        spacer_rules4 = [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child(3)',
                'props': [('text-align', 'center')]
            }
            for r in (5, 6, 7, 8, 9)
        ]

        styles += spacer_rules4


                    

        for i in [10,14]:
            disp_vis.iloc[i, 2] = ""

        display_styled_df(
            disp_vis,
            styles=styles,
            already_flat=True,
        )

        display_memo('f_78', year, month)

    except Exception as e:
        st.error(f"부적합 및 장기재고 현황 남통법인 표 생성 중 오류: {e}")


    st.divider()



    st.markdown("<h4> 5) 부적합 및 장기재고 현황 천진법인</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 톤, 백만원, %]</div>", unsafe_allow_html=True)


    try:

        file_name = st.secrets["sheets"]["f_78_79_80"]  
        raw = pd.read_csv(file_name, dtype=str)

        inv = modules.create_defect_longinv_table_from_company(
            year=int(st.session_state['year']),    
            month=int(st.session_state['month']),  
            data=raw,
            company_name='천진',                  
        )

        disp = inv.copy().reset_index()
        SPACER = "__spacer__"
        disp.insert(0, SPACER, "")


        def fmt_amt(x):
            """금액/수량: 0은 0, 음수는 괄호, 천단위 콤마"""
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
            """증감률: NaN / 0 / '0' 은 '-', 소수 1자리 %"""
            # NaN
            if pd.isna(x):
                return "-"

            # 문자열로 이미 넘어온 경우 대응
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
            if c in (SPACER, '구분2', '구분3'):
                continue
            if c == '증감률':
                disp[c] = disp[c].apply(fmt_rate)
            else:
                disp[c] = disp[c].apply(fmt_amt)


        cols = disp.columns.tolist()
        c_idx = {c: i for i, c in enumerate(cols)}

        spacer_i = c_idx[SPACER]
        big_i    = c_idx['구분2']
        mid_i    = c_idx['구분3']

        # 컬럼 인덱스 및 메타
        year_int = int(inv.attrs.get('base_year'))     # 연말 컬럼 기준 연도
        used_m   = int(inv.attrs.get('used_month'))    # 선택월
        prev_m   = int(inv.attrs.get('prev_month'))    # 전월
        prev2_m  = int(inv.attrs.get('prev2_month'))   # 전전월
        used_y   = int(inv.attrs.get('used_year'))     # 선택월이 속한 실제 연도
        company  = inv.attrs.get('company', '남통')

        # 연말 컬럼 이름
        yy_m1 = f"{(year_int - 1) % 100:02d}"
        yy_m2 = f"{(year_int - 2) % 100:02d}"
        yy_m3 = f"{(year_int - 3) % 100:02d}"
        yy_m4 = f"{(year_int - 4) % 100:02d}"

        col_yend_m4 = f"'{yy_m4}년말"
        col_yend_m3 = f"'{yy_m3}년말"
        col_yend_m2 = f"'{yy_m2}년말"
        col_yend_m1 = f"'{yy_m1}년말"

        # 월 컬럼 이름
        col_prev2 = f"{prev2_m}월"
        col_prev  = f"{prev_m}월"

        # 인덱스
        y4_i = c_idx[col_yend_m4]
        y3_i = c_idx[col_yend_m3]
        y2_i = c_idx[col_yend_m2]
        y1_i = c_idx[col_yend_m1]

        prev2_i = c_idx[col_prev2]
        prev_i  = c_idx[col_prev]

        gen_i   = c_idx['발생']
        used_i  = c_idx['소진']
        end_i   = c_idx['기말']
        rate_i  = c_idx['증감률']

        hdr1 = [''] * len(cols)
        hdr2 = [''] * len(cols)
        hdr3 = [''] * len(cols)

        # 회사명
        hdr2[big_i] = f"[{company}]"

        # 연말 헤더 ('xx년말)
        hdr2[y4_i] = col_yend_m4
        hdr2[y3_i] = col_yend_m3
        hdr2[y2_i] = col_yend_m2
        hdr2[y1_i] = col_yend_m1

        # ─────────────────────────────
        # ① prev2 / prev / 선택월 그룹의 "연도" 계산
        #    (선택월 연도 = used_y 기준, 월이 되돌아가면 연도 -1)
        # ─────────────────────────────
        used_year = used_y          # 선택월이 속한 실제 연도

        m_used = used_m             # 선택월
        m_prev = prev_m             # 전월
        m_prev2 = prev2_m           # 전전월

        # 선택월 연도
        m1_year = used_year

        # 전월 연도
        m2_year = used_year
        if m_prev > m_used:         # 1월 선택, 전월이 12월인 경우 등
            m2_year = used_year - 1

        # 전전월 연도
        m3_year = m2_year
        if m_prev2 > m_prev:        # 또 한 번 연도 경계 넘어가는 경우
            m3_year = m2_year - 1

        # ─────────────────────────────
        # ② 1행 헤더: 연도가 바뀌는 첫 컬럼에만 'yy년 표시
        #    prev2 → prev → (선택월 그룹의 첫 컬럼: 발생)
        # ─────────────────────────────
        year_runs = [
            (prev2_i, m3_year),
            (prev_i,  m2_year),
            (gen_i,   m1_year),     # 선택월 그룹은 '발생' 위에만 연도 표시
        ]

        last_year = None
        for col_i, y in year_runs:
            if y != last_year:
                hdr1[col_i] = f"'{y % 100:02d}년"
                last_year = y

        # ─────────────────────────────
        # ③ 2행 헤더: 월 / 선택월 그룹 라벨
        # ─────────────────────────────
        # 전전월 / 전월
        hdr2[prev2_i] = f"{prev2_m}월"
        hdr2[prev_i]  = f"{prev_m}월"

        # 선택월 그룹(발생·소진·기말·증감률)
        used_month_label = f"{used_m}월"
        for idx in (gen_i, used_i, end_i, rate_i):
            hdr2[idx] = used_month_label

        # ─────────────────────────────
        # ④ 3행 헤더: 항목명
        # ─────────────────────────────
        hdr3[gen_i]  = "발생"
        hdr3[used_i] = "소진"
        hdr3[end_i]  = "기말"
        hdr3[rate_i] = "증감률"

        # 최종 헤더 DF + 본문 결합
        hdr_df   = pd.DataFrame([hdr1, hdr2, hdr3], columns=cols)
        disp_vis = pd.concat([hdr_df, disp], ignore_index=True)


        # 6) 스타일
        styles = [
            {'selector': 'thead', 'props': [('display', 'none')]},

            {
                "selector": "tbody tr td:nth-child(1)",
                "props": [
                    ("border-right", "2px solid white !important"),
                ],
            },

            # 헤더 1·2·3 행
            {
                'selector': 'tbody tr:nth-child(1) td',
                'props': [
                    ('text-align', 'center'),
                    ('padding', '4px 6px'),
                    ('font-weight', '600'),
                    ('border-top','3px solid gray !important'),
                ],
            },
            {
                'selector': 'tbody tr:nth-child(2) td',
                'props': [
                    ('text-align', 'center'),
                    ('padding', '8px 6px'),
                    ('font-weight', '600'),
                ],
            },
            {
                'selector': 'tbody tr:nth-child(3) td',
                'props': [
                    ('text-align', 'center'),
                    ('padding', '10px 6px'),
                    ('font-weight', '600'),
                ],
            },

            # spacer 열
            {
                'selector': 'tbody td:nth-child(1)',
                'props': [('width', '8px'), ('border-right', '0')],
            },

            # 본문(4행 이후)
            {
                'selector': 'tbody tr:nth-child(n+4) td',
                'props': [
                    ('line-height', '1.4'),
                    ('padding', '6px 8px'),
                    ('text-align', 'right'),
                ],
            },
            {
                # 구분2, 구분3 열은 왼쪽 정렬
                'selector': 'tbody tr:nth-child(n+4) td:nth-child(2), tbody tr:nth-child(n+4) td:nth-child(3)',
                'props': [('text-align', 'left')],
            },
        ]

                #행
        spacer_rules1 = [
            {
                'selector': f'tr:nth-child({r})',
                'props': [('border-bottom','3px solid gray !important')]
               
            }
            for r in (3,11)
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
            for r in (3,4,5,6,7,8,9,10,12,13,14,15)
            for i in (1,2)

        ]

        styles += spacer_rules2

                # 구분 정리
        spacer_rules1 = [
            {
                'selector': f'tr:nth-child({r}) td:nth-child(2)',
                'props': [('border-right','3px solid gray !important')]
               
            }
            for r in (4,5,6,7,8,9,10,12,13,14)
        ]

        styles += spacer_rules1

        spacer_rules1 = [
            {
                'selector': f'tr:nth-child({r}) td:nth-child(3)',
                'props': [('border-bottom','3px solid gray !important')]
               
            }
            for r in (4,10,14)
        ]

        styles += spacer_rules1

        spacer_rules4 =[
                    {
                'selector': 'tbody td:nth-child(3)',
                'props': [
                    ('min-width', '180px'),
                    ('width', '180px'),
                    ('max-width', '180px'),

                ]
            }
        ]

        styles += spacer_rules4

        spacer_rules4 = [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child(3)',
                'props': [('text-align', 'center')]
            }
            for r in (5, 6, 7, 8, 9)
        ]

        styles += spacer_rules4


                    

        for i in [10,14]:
            disp_vis.iloc[i, 2] = ""

        display_styled_df(
            disp_vis,
            styles=styles,
            already_flat=True,
        )

        display_memo('f_79', year, month)

    except Exception as e:
        st.error(f"부적합 및 장기재고 현황 천진법인 표 생성 중 오류: {e}")

    st.divider()



    st.markdown("<h4> 6) 부적합 및 장기재고 현황 태국법인</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 톤, 백만원, %]</div>", unsafe_allow_html=True)


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
        SPACER = "__spacer__"
        disp.insert(0, SPACER, "")

        # 3) 숫자 포맷 함수
        def fmt_amt(x):
            """금액/수량: 0은 0, 음수는 괄호, 천단위 콤마"""
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
            """증감률: NaN / 0 / '0' 은 '-', 소수 1자리 %"""
            # NaN
            if pd.isna(x):
                return "-"

            # 문자열로 이미 넘어온 경우 대응
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
            if c in (SPACER, '구분2', '구분3'):
                continue
            if c == '증감률':
                disp[c] = disp[c].apply(fmt_rate)
            else:
                disp[c] = disp[c].apply(fmt_amt)


        # 5) 헤더 3단 구성
        cols = disp.columns.tolist()
        c_idx = {c: i for i, c in enumerate(cols)}

        spacer_i = c_idx[SPACER]
        big_i    = c_idx['구분2']
        mid_i    = c_idx['구분3']

        # 컬럼 인덱스 및 메타
        year_int = int(inv.attrs.get('base_year'))     # 연말 컬럼 기준 연도
        used_m   = int(inv.attrs.get('used_month'))    # 선택월
        prev_m   = int(inv.attrs.get('prev_month'))    # 전월
        prev2_m  = int(inv.attrs.get('prev2_month'))   # 전전월
        used_y   = int(inv.attrs.get('used_year'))     # 선택월이 속한 실제 연도
        company  = inv.attrs.get('company', '태국')

        # 연말 컬럼 이름
        yy_m1 = f"{(year_int - 1) % 100:02d}"
        yy_m2 = f"{(year_int - 2) % 100:02d}"
        yy_m3 = f"{(year_int - 3) % 100:02d}"
        yy_m4 = f"{(year_int - 4) % 100:02d}"

        col_yend_m4 = f"'{yy_m4}년말"
        col_yend_m3 = f"'{yy_m3}년말"
        col_yend_m2 = f"'{yy_m2}년말"
        col_yend_m1 = f"'{yy_m1}년말"

        # 월 컬럼 이름
        col_prev2 = f"{prev2_m}월"
        col_prev  = f"{prev_m}월"

        # 인덱스
        y4_i = c_idx[col_yend_m4]
        y3_i = c_idx[col_yend_m3]
        y2_i = c_idx[col_yend_m2]
        y1_i = c_idx[col_yend_m1]

        prev2_i = c_idx[col_prev2]
        prev_i  = c_idx[col_prev]

        gen_i   = c_idx['발생']
        used_i  = c_idx['소진']
        end_i   = c_idx['기말']
        rate_i  = c_idx['증감률']

        hdr1 = [''] * len(cols)
        hdr2 = [''] * len(cols)
        hdr3 = [''] * len(cols)

        # 회사명
        hdr2[big_i] = f"[{company}]"

        # 연말 헤더 ('xx년말)
        hdr2[y4_i] = col_yend_m4
        hdr2[y3_i] = col_yend_m3
        hdr2[y2_i] = col_yend_m2
        hdr2[y1_i] = col_yend_m1

        # ─────────────────────────────
        # ① prev2 / prev / 선택월 그룹의 "연도" 계산
        #    (선택월 연도 = used_y 기준, 월이 되돌아가면 연도 -1)
        # ─────────────────────────────
        used_year = used_y          # 선택월이 속한 실제 연도

        m_used = used_m             # 선택월
        m_prev = prev_m             # 전월
        m_prev2 = prev2_m           # 전전월

        # 선택월 연도
        m1_year = used_year

        # 전월 연도
        m2_year = used_year
        if m_prev > m_used:         # 1월 선택, 전월이 12월인 경우 등
            m2_year = used_year - 1

        # 전전월 연도
        m3_year = m2_year
        if m_prev2 > m_prev:        # 또 한 번 연도 경계 넘어가는 경우
            m3_year = m2_year - 1

        # ─────────────────────────────
        # ② 1행 헤더: 연도가 바뀌는 첫 컬럼에만 'yy년 표시
        #    prev2 → prev → (선택월 그룹의 첫 컬럼: 발생)
        # ─────────────────────────────
        year_runs = [
            (prev2_i, m3_year),
            (prev_i,  m2_year),
            (gen_i,   m1_year),     # 선택월 그룹은 '발생' 위에만 연도 표시
        ]

        last_year = None
        for col_i, y in year_runs:
            if y != last_year:
                hdr1[col_i] = f"'{y % 100:02d}년"
                last_year = y

        # ─────────────────────────────
        # ③ 2행 헤더: 월 / 선택월 그룹 라벨
        # ─────────────────────────────
        # 전전월 / 전월
        hdr2[prev2_i] = f"{prev2_m}월"
        hdr2[prev_i]  = f"{prev_m}월"

        # 선택월 그룹(발생·소진·기말·증감률)
        used_month_label = f"{used_m}월"
        for idx in (gen_i, used_i, end_i, rate_i):
            hdr2[idx] = used_month_label

        # ─────────────────────────────
        # ④ 3행 헤더: 항목명
        # ─────────────────────────────
        hdr3[gen_i]  = "발생"
        hdr3[used_i] = "소진"
        hdr3[end_i]  = "기말"
        hdr3[rate_i] = "증감률"

        # 최종 헤더 DF + 본문 결합
        hdr_df   = pd.DataFrame([hdr1, hdr2, hdr3], columns=cols)
        disp_vis = pd.concat([hdr_df, disp], ignore_index=True)


        # 6) 스타일
        styles = [
            {'selector': 'thead', 'props': [('display', 'none')]},

            {
                "selector": "tbody tr td:nth-child(1)",
                "props": [
                    ("border-right", "2px solid white !important"),
                ],
            },

            # 헤더 1·2·3 행
            {
                'selector': 'tbody tr:nth-child(1) td',
                'props': [
                    ('text-align', 'center'),
                    ('padding', '4px 6px'),
                    ('font-weight', '600'),
                    ('border-top','3px solid gray !important'),
                ],
            },
            {
                'selector': 'tbody tr:nth-child(2) td',
                'props': [
                    ('text-align', 'center'),
                    ('padding', '8px 6px'),
                    ('font-weight', '600'),
                ],
            },
            {
                'selector': 'tbody tr:nth-child(3) td',
                'props': [
                    ('text-align', 'center'),
                    ('padding', '10px 6px'),
                    ('font-weight', '600'),
                ],
            },

            # spacer 열
            {
                'selector': 'tbody td:nth-child(1)',
                'props': [('width', '8px'), ('border-right', '0')],
            },

            # 본문(4행 이후)
            {
                'selector': 'tbody tr:nth-child(n+4) td',
                'props': [
                    ('line-height', '1.4'),
                    ('padding', '6px 8px'),
                    ('text-align', 'right'),
                ],
            },
            {
                # 구분2, 구분3 열은 왼쪽 정렬
                'selector': 'tbody tr:nth-child(n+4) td:nth-child(2), tbody tr:nth-child(n+4) td:nth-child(3)',
                'props': [('text-align', 'left')],
            },
        ]

                #행
        spacer_rules1 = [
            {
                'selector': f'tr:nth-child({r})',
                'props': [('border-bottom','3px solid gray !important')]
               
            }
            for r in (3,11)
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
            for r in (3,4,5,6,7,8,9,10,12,13,14,15)
            for i in (1,2)

        ]

        styles += spacer_rules2

                # 구분 정리
        spacer_rules1 = [
            {
                'selector': f'tr:nth-child({r}) td:nth-child(2)',
                'props': [('border-right','3px solid gray !important')]
               
            }
            for r in (4,5,6,7,8,9,10,12,13,14)
        ]

        styles += spacer_rules1

        spacer_rules1 = [
            {
                'selector': f'tr:nth-child({r}) td:nth-child(3)',
                'props': [('border-bottom','3px solid gray !important')]
               
            }
            for r in (4,10,14)
        ]

        styles += spacer_rules1

        spacer_rules4 =[
                    {
                'selector': 'tbody td:nth-child(3)',
                'props': [
                    ('min-width', '180px'),
                    ('width', '180px'),
                    ('max-width', '180px'),

                ]
            }
        ]

        styles += spacer_rules4

        spacer_rules4 = [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child(3)',
                'props': [('text-align', 'center')]
            }
            for r in (5, 6, 7, 8, 9)
        ]

        styles += spacer_rules4


                    

        for i in [10,14]:
            disp_vis.iloc[i, 2] = ""

        display_styled_df(
            disp_vis,
            styles=styles,
            already_flat=True,
        )

        display_memo('f_80', year, month)

    except Exception as e:
        st.error(f"부적합 및 장기재고 현황 태국법인 표 생성 중 오류: {e}")

    st.divider()


    st.markdown("<h4> 7) 연령별 재고 현황 남통법인</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 톤, 백만원, %]</div>", unsafe_allow_html=True)


    try:

        file_name = st.secrets["sheets"]["f_81_82_83"]  
        raw = pd.read_csv(file_name, dtype=str)

        inv = modules.create_age_table_from_company(
            year=int(st.session_state['year']),
            month=int(st.session_state['month']),
            data=raw,
            company_name='남통',
        )

        disp = inv.copy().reset_index()  
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
            """증감률: NaN / 0 은 '-' (정수 %)"""
            if pd.isna(x):
                return "-"
            try:
                v = float(x)
            except Exception:
                return x
            if v == 0:
                return "-"
            return f"{int(round(v))}%"

        # 4) 컬럼별 포맷
        for c in disp.columns:
            if c in (SPACER, '구분2', '구분3'):
                continue
            if c == '증감률':
                disp[c] = disp[c].apply(fmt_rate)
            else:
                disp[c] = disp[c].apply(fmt_amt)

        # 5) 헤더 3단 구성 (부적합/장기재고 현황과 동일 스타일)
        cols = disp.columns.tolist()
        c_idx = {c: i for i, c in enumerate(cols)}

        spacer_i = c_idx[SPACER]
        big_i    = c_idx['구분2']
        mid_i    = c_idx['구분3']

        used_m   = int(inv.attrs.get('used_month'))
        prev_m   = int(inv.attrs.get('prev_month'))
        prev2_m  = int(inv.attrs.get('prev2_month'))
        year_int = int(inv.attrs.get('base_year'))
        used_y   = int(inv.attrs.get('used_year'))
        company  = inv.attrs.get('company', '남통')

        # 연말 컬럼용 연도 (고정)
        yy_m1 = f"{(year_int - 1) % 100:02d}"
        yy_m2 = f"{(year_int - 2) % 100:02d}"
        yy_m3 = f"{(year_int - 3) % 100:02d}"
        yy_m4 = f"{(year_int - 4) % 100:02d}"

        col_yend_m4 = f"'{yy_m4}년말"
        col_yend_m3 = f"'{yy_m3}년말"
        col_yend_m2 = f"'{yy_m2}년말"
        col_yend_m1 = f"'{yy_m1}년말"

        # 월/금액/증감률 컬럼
        col_prev2 = f"{prev2_m}월"
        col_prev  = f"{prev_m}월"
        col_used  = f"{used_m}월"

        y4_i    = c_idx[col_yend_m4]
        y3_i    = c_idx[col_yend_m3]
        y2_i    = c_idx[col_yend_m2]
        y1_i    = c_idx[col_yend_m1]
        prev2_i = c_idx[col_prev2]
        prev_i  = c_idx[col_prev]
        used_i  = c_idx[col_used]
        money_i = c_idx['금액']
        rate_i  = c_idx['증감률']

        hdr1 = [''] * len(cols)
        hdr2 = [''] * len(cols)
        hdr3 = [''] * len(cols)

        # 회사명
        hdr2[big_i] = f"[{company}]"

        # 연말 헤더
        hdr2[y4_i] = col_yend_m4
        hdr2[y3_i] = col_yend_m3
        hdr2[y2_i] = col_yend_m2
        hdr2[y1_i] = col_yend_m1

        # ─────────────────────
        # ① prev2 / prev / 선택월 구간의 실제 연도 계산
        #    (used_y, used_m 기준으로 연도 넘김 처리)
        # ─────────────────────
        used_year = used_y
        m_used = used_m
        m_prev = prev_m
        m_prev2 = prev2_m

        # 선택월 연도
        m1_year = used_year

        # 전월 연도
        m2_year = used_year
        if m_prev > m_used:      # 예: used=1, prev=12 → 전년도
            m2_year = used_year - 1

        # 전전월 연도
        m3_year = m2_year
        if m_prev2 > m_prev:     # 예: prev2=12, prev=1 같은 경우 또 연도 -1
            m3_year = m2_year - 1

        # ─────────────────────
        # ② 1행 헤더: 연도가 바뀌는 첫 컬럼에만 'yy년 표시
        #    prev2 → prev → (선택월 그룹의 첫 컬럼: used_i)
        #    금액/증감률은 선택월 그룹에 붙어서 같이 병합되게 공백 유지
        # ─────────────────────
        year_runs = [
            (prev2_i, m3_year),
            (prev_i,  m2_year),
            (used_i,  m1_year),  # 선택월 그룹 시작
        ]

        last_year = None
        for col_i, y in year_runs:
            if y != last_year:
                hdr1[col_i] = f"'{y % 100:02d}년"
                last_year = y
        # money_i, rate_i 는 같은 그룹이라 hdr1은 빈칸으로 두기

        # ─────────────────────
        # ③ 2행 헤더: 월 / 금액 / 증감률
        # ─────────────────────
        hdr2[prev2_i] = f"{prev2_m}월"
        hdr2[prev_i]  = f"{prev_m}월"
        hdr2[used_i]  = f"{used_m}월"
        hdr2[money_i] = "금액"
        hdr2[rate_i]  = "증감률"

        # ─────────────────────
        # ④ 3행 헤더: 단위
        # ─────────────────────
        hdr3[prev2_i] = "중량"
        hdr3[prev_i]  = "중량"
        hdr3[used_i]  = "중량"
        hdr3[money_i] = "금액"
        # 증감률은 단위 없음 (공백)

        hdr_df   = pd.DataFrame([hdr1, hdr2, hdr3], columns=cols)
        disp_vis = pd.concat([hdr_df, disp], ignore_index=True)


        styles = [
            {'selector': 'thead', 'props': [('display', 'none')]},
            {
                "selector": "tbody tr td:nth-child(1)",
                "props": [
                    ("border-right", "2px solid white !important"),
                ],
            },

            # 헤더 1·2·3행
            {
                'selector': 'tbody tr:nth-child(1) td',
                'props': [('text-align', 'center'),
                        ('padding', '4px 6px'),
                        ('font-weight', '600'),
                        ('border-top','3px solid gray !important')],
                        
            },
            {
                'selector': 'tbody tr:nth-child(2) td',
                'props': [('text-align', 'center'),
                        ('padding', '8px 6px'),
                        ('font-weight', '600')],
            },
            {
                'selector': 'tbody tr:nth-child(3) td',
                'props': [('text-align', 'center'),
                        ('padding', '10px 6px'),
                        ('font-weight', '600')],
            },

            # spacer 열
            {
                'selector': 'tbody td:nth-child(1)',
                'props': [('width', '8px'), ('border-right', '0')],
            },

            # 본문: 4행 이후
            {
                'selector': 'tbody tr:nth-child(n+4) td',
                'props': [('line-height', '1.4'),
                        ('padding', '6px 8px'),
                        ('text-align', 'right')],
            },
            {
                # 구분2, 구분3 열은 왼쪽 정렬
                'selector': 'tbody tr:nth-child(n+4) td:nth-child(2), tbody tr:nth-child(n+4) td:nth-child(3)',
                'props': [('text-align', 'left')],
            },
        ]

        #행
        spacer_rules1 = [
            {
                'selector': f'tr:nth-child(3)',
                'props': [('border-bottom','3px solid gray ')]
               
            }

        ]

        styles += spacer_rules1

        spacer_rules1 = [
            {
                'selector': f'tr:nth-child({r}) td:nth-child({i})',
                'props': [('border-bottom','3px solid gray ')]
               
            }
            for r in (8,13,18)
            for i in range(2,13)
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
            for r in (4,5,6,7,9,10,11,12,14,15,16,17,19,20)
            for i in (1,2)

        ]

        styles += spacer_rules2

        spacer_rules2 = [
            {
                'selector': f'tr:nth-child({r}) td:nth-child(1)',
                'props': [('border-bottom','2px solid white !important')]
               
            }
            for r in (8,13,18)


        ]

        styles += spacer_rules2

        spacer_rules2 = [
            {
                'selector': f'tr:nth-child({r}) td:nth-child(3)',
                'props': [('border-bottom','3px solid gray !important')]
               
            }
            for r in (7,12,17)


        ]

        styles += spacer_rules2

        spacer_rules2 = [
            {
                'selector': f'tr:nth-child(20) td:nth-child({r})',
                'props': [('border-bottom','3px solid gray !important')]
               
            }
            for r in (2,3)


        ]

        styles += spacer_rules2

                # 구분 정리
        spacer_rules1 = [
            {
                'selector': f'tr:nth-child({r}) td:nth-child(2)',
                'props': [('border-right','3px solid gray !important')]
               
            }
            for r in (4,5,6,7,9,10,11,12,14,15,16,17)
        ]

        styles += spacer_rules1

        spacer_rules1 = [
            {
                'selector': f'tr:nth-child({r}) td:nth-child(1)',
                'props': [('border-right','3px solid gray !important')]
               
            }
            for r in range(4,21)
        ]

        styles += spacer_rules1



        for i in [7,12,17,20]:
            disp_vis.iloc[i, 2] = ""

        display_styled_df(
            disp_vis,
            styles=styles,
            already_flat=True,
        )

        display_memo('f_81', year, month)

    except Exception as e:
        st.error(f"연령별 재고 현황 남통법인 표 생성 중 오류: {e}")


    st.divider()


    st.markdown("<h4> 8) 연령별 재고 현황 천진법인</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 톤, 백만원, %]</div>", unsafe_allow_html=True)


    try:

        file_name = st.secrets["sheets"]["f_81_82_83"]  
        raw = pd.read_csv(file_name, dtype=str)

        inv = modules.create_age_table_from_company(
            year=int(st.session_state['year']),
            month=int(st.session_state['month']),
            data=raw,
            company_name='천진',
        )

        # 2) 표시용 복사 & 인덱스 풀기
        disp = inv.copy().reset_index()  
        SPACER = "__spacer__"
        disp.insert(0, SPACER, "")

        # 3) 포맷 함수
        def fmt_amt(x):
            """수량/금액: 0은 0, 음수는 괄호, 천단위 콤마"""
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
            """증감률: NaN / 0 은 '-' (정수 %)"""
            if pd.isna(x):
                return "-"
            try:
                v = float(x)
            except Exception:
                return x
            if v == 0:
                return "-"
            return f"{int(round(v))}%"

        # 4) 컬럼별 포맷
        for c in disp.columns:
            if c in (SPACER, '구분2', '구분3'):
                continue
            if c == '증감률':
                disp[c] = disp[c].apply(fmt_rate)
            else:
                disp[c] = disp[c].apply(fmt_amt)

        # 5) 헤더 3단 구성 (부적합/장기재고 현황과 동일 스타일)
        cols = disp.columns.tolist()
        c_idx = {c: i for i, c in enumerate(cols)}

        spacer_i = c_idx[SPACER]
        big_i    = c_idx['구분2']
        mid_i    = c_idx['구분3']

        used_m   = int(inv.attrs.get('used_month'))
        prev_m   = int(inv.attrs.get('prev_month'))
        prev2_m  = int(inv.attrs.get('prev2_month'))
        year_int = int(inv.attrs.get('base_year'))
        used_y   = int(inv.attrs.get('used_year'))
        company  = inv.attrs.get('company', '남통')

        # 연말 컬럼용 연도 (고정)
        yy_m1 = f"{(year_int - 1) % 100:02d}"
        yy_m2 = f"{(year_int - 2) % 100:02d}"
        yy_m3 = f"{(year_int - 3) % 100:02d}"
        yy_m4 = f"{(year_int - 4) % 100:02d}"

        col_yend_m4 = f"'{yy_m4}년말"
        col_yend_m3 = f"'{yy_m3}년말"
        col_yend_m2 = f"'{yy_m2}년말"
        col_yend_m1 = f"'{yy_m1}년말"

        # 월/금액/증감률 컬럼
        col_prev2 = f"{prev2_m}월"
        col_prev  = f"{prev_m}월"
        col_used  = f"{used_m}월"

        y4_i    = c_idx[col_yend_m4]
        y3_i    = c_idx[col_yend_m3]
        y2_i    = c_idx[col_yend_m2]
        y1_i    = c_idx[col_yend_m1]
        prev2_i = c_idx[col_prev2]
        prev_i  = c_idx[col_prev]
        used_i  = c_idx[col_used]
        money_i = c_idx['금액']
        rate_i  = c_idx['증감률']

        hdr1 = [''] * len(cols)
        hdr2 = [''] * len(cols)
        hdr3 = [''] * len(cols)

        # 회사명
        hdr2[big_i] = f"[{company}]"

        # 연말 헤더
        hdr2[y4_i] = col_yend_m4
        hdr2[y3_i] = col_yend_m3
        hdr2[y2_i] = col_yend_m2
        hdr2[y1_i] = col_yend_m1

        # ─────────────────────
        # ① prev2 / prev / 선택월 구간의 실제 연도 계산
        #    (used_y, used_m 기준으로 연도 넘김 처리)
        # ─────────────────────
        used_year = used_y
        m_used = used_m
        m_prev = prev_m
        m_prev2 = prev2_m

        # 선택월 연도
        m1_year = used_year

        # 전월 연도
        m2_year = used_year
        if m_prev > m_used:      # 예: used=1, prev=12 → 전년도
            m2_year = used_year - 1

        # 전전월 연도
        m3_year = m2_year
        if m_prev2 > m_prev:     # 예: prev2=12, prev=1 같은 경우 또 연도 -1
            m3_year = m2_year - 1

        # ─────────────────────
        # ② 1행 헤더: 연도가 바뀌는 첫 컬럼에만 'yy년 표시
        #    prev2 → prev → (선택월 그룹의 첫 컬럼: used_i)
        #    금액/증감률은 선택월 그룹에 붙어서 같이 병합되게 공백 유지
        # ─────────────────────
        year_runs = [
            (prev2_i, m3_year),
            (prev_i,  m2_year),
            (used_i,  m1_year),  # 선택월 그룹 시작
        ]

        last_year = None
        for col_i, y in year_runs:
            if y != last_year:
                hdr1[col_i] = f"'{y % 100:02d}년"
                last_year = y
        # money_i, rate_i 는 같은 그룹이라 hdr1은 빈칸으로 두기

        # ─────────────────────
        # ③ 2행 헤더: 월 / 금액 / 증감률
        # ─────────────────────
        hdr2[prev2_i] = f"{prev2_m}월"
        hdr2[prev_i]  = f"{prev_m}월"
        hdr2[used_i]  = f"{used_m}월"
        hdr2[money_i] = "금액"
        hdr2[rate_i]  = "증감률"

        # ─────────────────────
        # ④ 3행 헤더: 단위
        # ─────────────────────
        hdr3[prev2_i] = "중량"
        hdr3[prev_i]  = "중량"
        hdr3[used_i]  = "중량"
        hdr3[money_i] = "금액"
        # 증감률은 단위 없음 (공백)

        hdr_df   = pd.DataFrame([hdr1, hdr2, hdr3], columns=cols)
        disp_vis = pd.concat([hdr_df, disp], ignore_index=True)


        styles = [
            {'selector': 'thead', 'props': [('display', 'none')]},
            
            {
                "selector": "tbody tr td:nth-child(1)",
                "props": [
                    ("border-right", "2px solid white !important"),
                ],
            },

            # 헤더 1·2·3행
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
                        ('font-weight', '600'),
                        ],
            },
            {
                'selector': 'tbody tr:nth-child(3) td',
                'props': [('text-align', 'center'),
                        ('padding', '10px 6px'),
                        ('font-weight', '600')],
            },

            # spacer 열
            {
                'selector': 'tbody td:nth-child(1)',
                'props': [('width', '8px'), ('border-right', '0')],
            },

            # 본문: 4행 이후
            {
                'selector': 'tbody tr:nth-child(n+4) td',
                'props': [('line-height', '1.4'),
                        ('padding', '6px 8px'),
                        ('text-align', 'right')],
            },
            {
                # 구분2, 구분3 열은 왼쪽 정렬
                'selector': 'tbody tr:nth-child(n+4) td:nth-child(2), tbody tr:nth-child(n+4) td:nth-child(3)',
                'props': [('text-align', 'left')],
            },
        ]

        #행
        spacer_rules1 = [
            {
                'selector': f'tr:nth-child(3)',
                'props': [('border-bottom','3px solid gray ')]
               
            }

        ]

        styles += spacer_rules1

        spacer_rules1 = [
            {
                'selector': f'tr:nth-child({r}) td:nth-child({i})',
                'props': [('border-bottom','3px solid gray ')]
               
            }
            for r in (8,13,18)
            for i in range(2,13)
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
            for r in (4,5,6,7,9,10,11,12,14,15,16,17,19,20)
            for i in (1,2)

        ]

        styles += spacer_rules2

        spacer_rules2 = [
            {
                'selector': f'tr:nth-child({r}) td:nth-child(1)',
                'props': [('border-bottom','2px solid white !important')]
               
            }
            for r in (8,13,18)


        ]

        styles += spacer_rules2

        spacer_rules2 = [
            {
                'selector': f'tr:nth-child({r}) td:nth-child(3)',
                'props': [('border-bottom','3px solid gray !important')]
               
            }
            for r in (7,12,17)


        ]

        styles += spacer_rules2

        spacer_rules2 = [
            {
                'selector': f'tr:nth-child(20) td:nth-child({r})',
                'props': [('border-bottom','3px solid gray !important')]
               
            }
            for r in (2,3)


        ]

        styles += spacer_rules2

                # 구분 정리
        spacer_rules1 = [
            {
                'selector': f'tr:nth-child({r}) td:nth-child(2)',
                'props': [('border-right','3px solid gray !important')]
               
            }
            for r in (4,5,6,7,9,10,11,12,14,15,16,17)
        ]

        styles += spacer_rules1

        spacer_rules1 = [
            {
                'selector': f'tr:nth-child({r}) td:nth-child(1)',
                'props': [('border-right','3px solid gray !important')]
               
            }
            for r in range(4,21)
        ]

        styles += spacer_rules1



        for i in [7,12,17,20]:
            disp_vis.iloc[i, 2] = ""

        display_styled_df(
            disp_vis,
            styles=styles,
            already_flat=True,
        )

        display_memo('f_82', year, month)

    except Exception as e:
        st.error(f"연령별 재고 현황 천진법인 표 생성 중 오류: {e}")

    st.divider()


    st.markdown("<h4> 9) 연령별 재고 현황 태국법인</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 톤, 백만원, %]</div>", unsafe_allow_html=True)


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
        SPACER = "__spacer__"
        disp.insert(0, SPACER, "")

        # 3) 포맷 함수
        def fmt_amt(x):
            """수량/금액: 0은 0, 음수는 괄호, 천단위 콤마"""
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
            """증감률: NaN / 0 은 '-' (정수 %)"""
            if pd.isna(x):
                return "-"
            try:
                v = float(x)
            except Exception:
                return x
            if v == 0:
                return "-"
            return f"{int(round(v))}%"

        # 4) 컬럼별 포맷
        for c in disp.columns:
            if c in (SPACER, '구분2', '구분3'):
                continue
            if c == '증감률':
                disp[c] = disp[c].apply(fmt_rate)
            else:
                disp[c] = disp[c].apply(fmt_amt)

        # 5) 헤더 3단 구성 (부적합/장기재고 현황과 동일 스타일)
        cols = disp.columns.tolist()
        c_idx = {c: i for i, c in enumerate(cols)}

        spacer_i = c_idx[SPACER]
        big_i    = c_idx['구분2']
        mid_i    = c_idx['구분3']

        used_m   = int(inv.attrs.get('used_month'))
        prev_m   = int(inv.attrs.get('prev_month'))
        prev2_m  = int(inv.attrs.get('prev2_month'))
        year_int = int(inv.attrs.get('base_year'))
        used_y   = int(inv.attrs.get('used_year'))
        company  = inv.attrs.get('company', '남통')

        # 연말 컬럼용 연도 (고정)
        yy_m1 = f"{(year_int - 1) % 100:02d}"
        yy_m2 = f"{(year_int - 2) % 100:02d}"
        yy_m3 = f"{(year_int - 3) % 100:02d}"
        yy_m4 = f"{(year_int - 4) % 100:02d}"

        col_yend_m4 = f"'{yy_m4}년말"
        col_yend_m3 = f"'{yy_m3}년말"
        col_yend_m2 = f"'{yy_m2}년말"
        col_yend_m1 = f"'{yy_m1}년말"

        # 월/금액/증감률 컬럼
        col_prev2 = f"{prev2_m}월"
        col_prev  = f"{prev_m}월"
        col_used  = f"{used_m}월"

        y4_i    = c_idx[col_yend_m4]
        y3_i    = c_idx[col_yend_m3]
        y2_i    = c_idx[col_yend_m2]
        y1_i    = c_idx[col_yend_m1]
        prev2_i = c_idx[col_prev2]
        prev_i  = c_idx[col_prev]
        used_i  = c_idx[col_used]
        money_i = c_idx['금액']
        rate_i  = c_idx['증감률']

        hdr1 = [''] * len(cols)
        hdr2 = [''] * len(cols)
        hdr3 = [''] * len(cols)

        # 회사명
        hdr2[big_i] = f"[{company}]"

        # 연말 헤더
        hdr2[y4_i] = col_yend_m4
        hdr2[y3_i] = col_yend_m3
        hdr2[y2_i] = col_yend_m2
        hdr2[y1_i] = col_yend_m1

        # ─────────────────────
        # ① prev2 / prev / 선택월 구간의 실제 연도 계산
        #    (used_y, used_m 기준으로 연도 넘김 처리)
        # ─────────────────────
        used_year = used_y
        m_used = used_m
        m_prev = prev_m
        m_prev2 = prev2_m

        # 선택월 연도
        m1_year = used_year

        # 전월 연도
        m2_year = used_year
        if m_prev > m_used:      # 예: used=1, prev=12 → 전년도
            m2_year = used_year - 1

        # 전전월 연도
        m3_year = m2_year
        if m_prev2 > m_prev:     # 예: prev2=12, prev=1 같은 경우 또 연도 -1
            m3_year = m2_year - 1

        # ─────────────────────
        # ② 1행 헤더: 연도가 바뀌는 첫 컬럼에만 'yy년 표시
        #    prev2 → prev → (선택월 그룹의 첫 컬럼: used_i)
        #    금액/증감률은 선택월 그룹에 붙어서 같이 병합되게 공백 유지
        # ─────────────────────
        year_runs = [
            (prev2_i, m3_year),
            (prev_i,  m2_year),
            (used_i,  m1_year),  # 선택월 그룹 시작
        ]

        last_year = None
        for col_i, y in year_runs:
            if y != last_year:
                hdr1[col_i] = f"'{y % 100:02d}년"
                last_year = y
        # money_i, rate_i 는 같은 그룹이라 hdr1은 빈칸으로 두기

        # ─────────────────────
        # ③ 2행 헤더: 월 / 금액 / 증감률
        # ─────────────────────
        hdr2[prev2_i] = f"{prev2_m}월"
        hdr2[prev_i]  = f"{prev_m}월"
        hdr2[used_i]  = f"{used_m}월"
        hdr2[money_i] = "금액"
        hdr2[rate_i]  = "증감률"

        # ─────────────────────
        # ④ 3행 헤더: 단위
        # ─────────────────────
        hdr3[prev2_i] = "중량"
        hdr3[prev_i]  = "중량"
        hdr3[used_i]  = "중량"
        hdr3[money_i] = "금액"
        # 증감률은 단위 없음 (공백)

        hdr_df   = pd.DataFrame([hdr1, hdr2, hdr3], columns=cols)
        disp_vis = pd.concat([hdr_df, disp], ignore_index=True)


        styles = [
            {'selector': 'thead', 'props': [('display', 'none')]},

            {
                "selector": "tbody tr td:nth-child(1)",
                "props": [
                    ("border-right", "2px solid white !important"),
                ],
            },

            # 헤더 1·2·3행
            {
                'selector': 'tbody tr:nth-child(1) td',
                'props': [('text-align', 'center'),
                        ('padding', '4px 6px'),
                        ('font-weight', '600'),
                        ('border-top','3px solid gray !important')],
            },
            {
                'selector': 'tbody tr:nth-child(2) td',
                'props': [('text-align', 'center'),
                        ('padding', '8px 6px'),
                        ('font-weight', '600')],
            },
            {
                'selector': 'tbody tr:nth-child(3) td',
                'props': [('text-align', 'center'),
                        ('padding', '10px 6px'),
                        ('font-weight', '600')],
            },

            # spacer 열
            {
                'selector': 'tbody td:nth-child(1)',
                'props': [('width', '8px'), ('border-right', '0')],
            },

            # 본문: 4행 이후
            {
                'selector': 'tbody tr:nth-child(n+4) td',
                'props': [('line-height', '1.4'),
                        ('padding', '6px 8px'),
                        ('text-align', 'right')],
            },
            {
                # 구분2, 구분3 열은 왼쪽 정렬
                'selector': 'tbody tr:nth-child(n+4) td:nth-child(2), tbody tr:nth-child(n+4) td:nth-child(3)',
                'props': [('text-align', 'left')],
            },
        ]

        #행
        spacer_rules1 = [
            {
                'selector': f'tr:nth-child(3)',
                'props': [('border-bottom','3px solid gray ')]
               
            }

        ]

        styles += spacer_rules1

        spacer_rules1 = [
            {
                'selector': f'tr:nth-child({r}) td:nth-child({i})',
                'props': [('border-bottom','3px solid gray ')]
               
            }
            for r in (8,13,18)
            for i in range(2,13)
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
            for r in (4,5,6,7,9,10,11,12,14,15,16,17,19,20)
            for i in (1,2)

        ]

        styles += spacer_rules2

        spacer_rules2 = [
            {
                'selector': f'tr:nth-child({r}) td:nth-child(1)',
                'props': [('border-bottom','2px solid white !important')]
               
            }
            for r in (8,13,18)


        ]

        styles += spacer_rules2

        spacer_rules2 = [
            {
                'selector': f'tr:nth-child({r}) td:nth-child(3)',
                'props': [('border-bottom','3px solid gray !important')]
               
            }
            for r in (7,12,17)


        ]

        styles += spacer_rules2

        spacer_rules2 = [
            {
                'selector': f'tr:nth-child(20) td:nth-child({r})',
                'props': [('border-bottom','3px solid gray !important')]
               
            }
            for r in (2,3)


        ]

        styles += spacer_rules2

                # 구분 정리
        spacer_rules1 = [
            {
                'selector': f'tr:nth-child({r}) td:nth-child(2)',
                'props': [('border-right','3px solid gray !important')]
               
            }
            for r in (4,5,6,7,9,10,11,12,14,15,16,17)
        ]

        styles += spacer_rules1

        spacer_rules1 = [
            {
                'selector': f'tr:nth-child({r}) td:nth-child(1)',
                'props': [('border-right','3px solid gray !important')]
               
            }
            for r in range(4,21)
        ]

        styles += spacer_rules1



        for i in [7,12,17,20]:
            disp_vis.iloc[i, 2] = ""

        display_styled_df(
            disp_vis,
            styles=styles,
            already_flat=True,
        )

        display_memo('f_83', year, month)

    except Exception as e:
        st.error(f"연령별 재고 현황 태국법인 표 생성 중 오류: {e}")
    
    st.divider()

with t7:

    st.markdown("<h4> 1) 채권 현황 남통법인</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 톤, 백만원, %]</div>", unsafe_allow_html=True)


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


        cols = disp.columns.tolist()
        c_idx = {c: i for i, c in enumerate(cols)}

        name_i   = c_idx['구분']

        year_int = int(ar.attrs.get('base_year'))
        used_y   = int(ar.attrs.get('used_year'))
        used_m   = int(ar.attrs.get('used_month'))
        prev_m   = int(ar.attrs.get('prev_month'))
        company  = ar.attrs.get('company', '남통')

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
        hdr2[used_i] = f"{used_m}월"


        # 2단 헤더만 붙이기
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

            {
                'selector': 'tbody td:nth-child(1)',
                'props': [('width', '8px'), ('border-right', '0')],
            },

            {
                'selector': 'tbody tr:nth-child(n+3) td',
                'props': [('line-height', '1.4'),
                        ('padding', '6px 8px'),
                        ('text-align', 'right')],
            },
            {

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


        display_memo('f_84', year, month)

    except Exception as e:
        st.error(f"채권 현황 남통법인 표 생성 중 오류: {e}")
    
    st.divider()


    st.markdown("<h4> 2) 채권 현황 천진법인</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 톤, 백만원, %]</div>", unsafe_allow_html=True)


    try:
        file_name = st.secrets["sheets"]["f_84_85_86"]  

        raw = pd.read_csv(file_name, dtype=str)

        ar = modules.create_ar_status_table_from_company(
            year=int(st.session_state['year']),
            month=int(st.session_state['month']),
            data=raw,
            company_name='천진',
        )

        disp = ar.copy().reset_index()  # '구분'
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

        name_i   = c_idx['구분']

        year_int = int(ar.attrs.get('base_year'))
        used_y   = int(ar.attrs.get('used_year'))
        used_m   = int(ar.attrs.get('used_month'))
        prev_m   = int(ar.attrs.get('prev_month'))
        company  = ar.attrs.get('company', '천진')

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

        m_used_year = used_year

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
        hdr2[used_i] = f"{used_m}월"

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


        display_memo('f_85', year, month)

    except Exception as e:
        st.error(f"채권 현황 천진법인 표 생성 중 오류: {e}")
    
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