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

import re, io, pandas as pd
from urllib.request import urlopen, Request


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


def display_styled_df(df, styles=None, highlight_cols=None, fmt_int=True, align="left",
                      already_flat=False, applymap_rules=None):
    df_for_style = df.copy()

    if not already_flat:
        df_for_style = df_for_style.reset_index()

    df_for_style.columns = df_for_style.columns.astype(str)

    seen = {}
    new_cols = []
    for c in df_for_style.columns:
        c_str = str(c)
        seen[c_str] = seen.get(c_str, 0) + 1
        new_cols.append(c_str if seen[c_str] == 1 else f"{c_str}_{seen[c_str]-1}")
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
# UI 본문
# =========================
year = int(st.session_state['year'])
month = int(st.session_state['month'])

st.markdown(f"## {year}년 {month}월 기타")

t1, = st.tabs(['1. 인원현황'])

with t1:
    # ── 6:4 레이아웃 적용 ──
    col_left, col_right = st.columns([6, 4], gap="large")

    with col_left:
        # 1) 제목 및 단위 출력 (단위는 60% 상자의 맨 우측 정렬)
        st.markdown("<h4>1) 인원현황</h4>", unsafe_allow_html=True)
        st.markdown(
            "<div style='text-align:right; font-size:13px; color:#666; margin-bottom:5px;'>[단위: 명]</div>",
            unsafe_allow_html=True,
        )

        try:
            file_name = st.secrets["sheets"]["f_60"]
            df_src = pd.read_csv(file_name, dtype=str)

            sel_y = int(st.session_state["year"])
            sel_m = int(st.session_state["month"])

            disp_raw, meta = modules.build_table_60(df_src, sel_y, sel_m)

            hdr1 = meta["hdr1"]

            num_cols = [c for c in disp_raw.columns if c not in ("구분1", "구분2")]

            # ── 구분 컬럼 생성 ──
            rows = []
            for _, row in disp_raw.iterrows():
                g1 = str(row["구_분1"] if "구_분1" in row else row.get("구분1", "")).strip()
                g2 = str(row["구_분2"] if "구_분2" in row else row.get("구분2", "")).strip()
                label = g1 if g2 == "" else g2

                # [수정 반영] 화면의 '사무직' 명칭을 원본 DB 기준인 '사무기술직'으로 변환해 매칭 준비
                db_target = "사무기술직" if label == "사무직" else label

                # 원본 DB(df_src) 영역 수색하여 해당 행 추적
                matched = df_src[
                    (df_src["구분1"].str.strip() == db_target) |
                    (df_src["구분2"].str.strip() == db_target) |
                    (df_src["구분3"].str.strip() == db_target)
                ]

                lv = 0
                db_gubun2 = ""
                db_gubun3 = ""

                if not matched.empty:
                    idx_row = matched.iloc[0]
                    try:
                        lv = int(float(idx_row["Lv class"]))
                    except:
                        lv = 0
                    db_gubun2 = str(idx_row.get("구분2", "")).strip()
                    db_gubun3 = str(idx_row.get("구분3", "")).strip()

                # [요청하신 복합 조건 IF문 구현]
                padding = 0
                if lv == 0:
                    # 레벨클래스 == 0; 다른 값들 읽지 않고 들여쓰기 없이 원래 그대로 가만히 두기
                    padding = 0
                elif lv == 1:
                    # 레벨클래스 == 1; 구분3값을 해당 값(사무기술직 OR 기능직)은 한칸 띄우기
                    if db_gubun3 in ["사무기술직", "기능직"]:
                        padding = 16
                elif lv == 2:
                    # 레벨클래스 == 2; 구분2값을 읽고 해당 값(자사 OR 외주)는 두칸 띄우기
                    if db_gubun2 in ["자사", "외주"]:
                        padding = 32

                # 패딩 값이 결정되면 태그 감싸기
                if padding > 0:
                    label = f'<span style="padding-left:{padding}px">{label}</span>'

                r = {"구분": label}
                for c in num_cols:
                    r[c] = row[c]
                rows.append(r)

            disp = pd.DataFrame(rows)

            # ── 헤더 구성 ──
            hdr1_adj = ["구분"] + hdr1[2:]
            cols = disp.columns.tolist()
            hdr_df = pd.DataFrame([hdr1_adj], columns=cols)
            disp_vis = pd.concat([hdr_df, disp], ignore_index=True)


            # ── 포맷 ──
            def fmt_num(v):
                if pd.isna(v) or str(v).strip() == "":
                    return ""
                try:
                    iv = int(round(float(v)))
                except:
                    return str(v)
                return f"{iv:,}"


            def fmt_diff(v):
                if pd.isna(v) or str(v).strip() == "":
                    return ""
                try:
                    iv = int(round(float(v)))
                except:
                    return str(v)
                if iv < 0:
                    return f'<span style="color:red;">-{abs(iv):,}</span>'
                if iv > 0:
                    return f"{iv:,}"
                return "0"


            body = disp_vis.copy()
            data_rows = body.index[1:]
            diff_cols = ["mom_diff", "plan_diff"]

            for c in num_cols:
                body.loc[data_rows, c] = body.loc[data_rows, c].apply(
                    fmt_diff if c in diff_cols else fmt_num
                )

            # ── 스타일 정의 ──
            styles = [
                {"selector": "thead", "props": [("display", "none")]},
                {"selector": "td, th",
                 "props": [("border", "1px solid #aaa"), ("padding", "8px 16px"), ("font-size", "15px")]},
                {
                    "selector": "tbody tr:nth-child(1) td",
                    "props": [("text-align", "center"), ("font-weight", "700"),
                              ("border-bottom", "1px solid #aaa")]
                },
                {
                    "selector": "tbody tr:nth-child(n+2) td:nth-child(1)",
                    "props": [("text-align", "left"), ("white-space", "nowrap")]
                },
                {
                    "selector": "tbody tr:nth-child(n+2) td:nth-child(n+2)",
                    "props": [("text-align", "right")]
                },
            ]

            # ── [핵심 변경] 표 스타일 생성 후 100% 스타일 입히기 ──
            styled_df = (
                body.style
                .set_table_styles(styles)
                .hide(axis="index")
            )

            # [수정 반영] HTML 들여쓰기 span 태그가 브라우저에서 올바르게 표현되도록 escape=False 옵션 추가
            st.markdown(
                f"<div style='width: 100%; overflow-x: auto;'><style>table {{ width: 100% !important; border-collapse: collapse; }}</style>{styled_df.to_html(escape=False)}</div>",
                unsafe_allow_html=True
            )

        except Exception as e:
            st.error(f"인원현황 표 생성 오류: {e}")

    with col_right:
        # 오른쪽 40%는 깨끗하게 비워둡니다.
        pass

    st.divider()


# Footer
st.markdown("""
<style>.footer { bottom: 0; left: 0; right: 0; padding: 8px; text-align: center; font-size: 13px; color: #666666;}</style>
<div class="footer">ⓒ 2025 SeAH Special Steel Corp. All rights reserved.</div>
""", unsafe_allow_html=True)