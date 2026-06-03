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

import re, io, pandas as pd
from urllib.request import urlopen, Request

def rowspan_like_for_index(blocks, level=2, header_rows=1):
    styles = []
    to_nth = lambda r: r + header_rows + 1
    for start, end in blocks:
        top = to_nth(start)
        mid = [to_nth(r) for r in range(start + 1, end)]
        bot = to_nth(end)
        styles.append({'selector': f'tbody tr:nth-child({top}) th.row_heading.level{level}', 'props': [('border-bottom', '0')]})
        for r in mid:
            styles.append({'selector': f'tbody tr:nth-child({r}) th.row_heading.level{level}', 'props': [('border-top', '0'), ('border-bottom', '0'), ('color', 'transparent'), ('text-shadow', 'none')]})
        styles.append({'selector': f'tbody tr:nth-child({bot}) th.row_heading.level{level}', 'props': [('border-top', '0')]})
    return styles

def with_inline_header_row(df, index_names=('', '', '구분'), index_values=('', '', '구분')):
    if isinstance(df.index, pd.MultiIndex):
        df.index = df.index.set_names(index_names)
    else:
        df.index.name = index_names[-1]
    hdr = pd.DataFrame([list(df.columns)], columns=df.columns)
    if isinstance(df.index, pd.MultiIndex):
        hdr.index = pd.MultiIndex.from_tuples([index_values], names=index_names)
    else:
        hdr.index = pd.Index([index_values[-1]], name=index_names[-1])
    return pd.concat([hdr, df], axis=0)

def display_styled_df(df, styles=None, highlight_cols=None, already_flat=False, applymap_rules=None):
    if already_flat:
        df_for_style = df.copy()
    else:
        df_for_style = df.reset_index()
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
            rows, cols = subset
            styled_df = styled_df.map(func, subset=pd.IndexSlice[rows, cols])
    st.markdown(styled_df.to_html(), unsafe_allow_html=True)

def create_indented_html(s):
    content = s.lstrip(' ')
    num_spaces = len(s) - len(content)
    indent_level = num_spaces // 2
    return f'<p class="indent-{indent_level}">{content}</p>'

def display_memo(memo_file_key, year, month):
    try:
        file_name = st.secrets['memos'][memo_file_key]
        df_memo = pd.read_csv(file_name)
        df_filtered = df_memo[(df_memo['년도'] == year) & (df_memo['월'] == month)]
        if df_filtered.empty:
            return
        memo_text = df_filtered.iloc[0]['메모']
        str_list = memo_text.split('\n')
        html_items = [create_indented_html(s) for s in str_list]
        body_content = "".join(html_items)
        html_code = f"""
        <style>
            .memo-body .indent-0 {{ padding-left: 0px; padding-top: 10px; font-size: 17px; font-weight: bold; }}
            .memo-body .indent-1 {{ padding-left: 20px; padding-top: 5px; font-size: 17px; }}
            .memo-body .indent-2 {{ padding-left: 40px; font-size: 17px; }}
            .memo-body p {{ margin: 0.2rem 0; }}
        </style>
        <div class="memo-body">{body_content}</div>
        """
        st.markdown(html_code, unsafe_allow_html=True)
    except (FileNotFoundError, KeyError):
        pass

def _date_update_callback():
    st.session_state.year = st.session_state.year_selector
    st.session_state.month = st.session_state.month_selector

this_year = datetime.today().year
current_month = datetime.today().month

def create_sidebar():
    with st.sidebar:
        st.title("날짜 선택")
        if 'year' not in st.session_state:
            st.session_state.year = this_year
        if 'month' not in st.session_state:
            st.session_state.month = current_month
        st.selectbox('년(Year)', range(2020, 2031), key='year_selector', index=st.session_state.year - 2020, on_change=_date_update_callback)
        st.selectbox('월(Month)', range(1, 13), key='month_selector', index=st.session_state.month - 1, on_change=_date_update_callback)
        st.info(f"선택된 날짜: {st.session_state.year}년 {st.session_state.month}월")

create_sidebar()

@st.cache_data(ttl=1800)
def load_f40(url):
    df = pd.read_csv(url, dtype=str)
    if '실적' in df.columns:
        s = df['실적'].str.replace(',', '', regex=False)
        df['실적'] = pd.to_numeric(s, errors='coerce').fillna(0.0)
    else:
        df['실적'] = 0.0
    if '월' in df.columns:
        m = (df['월'].astype(str).str.replace('월', '', regex=False).str.replace('.', '', regex=False).str.strip().replace({'': np.nan, 'nan': np.nan, 'None': np.nan, 'NULL': np.nan}))
        df['월'] = pd.to_numeric(m, errors='coerce').astype('Int64')
    else:
        df['월'] = pd.Series([pd.NA] * len(df), dtype='Int64')
    if '연도' in df.columns:
        y = (df['연도'].astype(str).str.extract(r'(\d{4}|\d{2})')[0].replace({'': np.nan, 'nan': np.nan, 'None': np.nan, 'NULL': np.nan}))
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
def load_defect(url):
    df = pd.read_csv(url, dtype=str)
    for c in ['연도', '월', '실적']:
        df[c] = pd.to_numeric(df.get(c), errors='coerce')
    for c in ['구분1', '구분2', '구분3', '구분4']:
        if c in df.columns:
            df[c] = df[c].fillna('').astype(str)
        else:
            df[c] = ''
    return df

year = int(st.session_state['year'])
month = int(st.session_state['month'])

st.markdown(f"## {year}년 {month}월 손익 분석")

t1, t2, t3, t4, t5, t6 = st.tabs(['1. 손익요약', '2. 전월 대비 손익차이', '3. 원재료', '4. 제조 가공비', '5. 판매비와 관리비', '6. 성과급 및 격려금'])

with t1:
    st.markdown("<h4>1) 손익요약 </h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 톤, 백만원]</div>", unsafe_allow_html=True)
    try:
        file_name = st.secrets["sheets"]["f_19"]
        raw = pd.read_csv(file_name, dtype=str)
        body = modules.create_profit_month_block_table(df_raw=raw, year=int(st.session_state['year']),
                                                       month=int(st.session_state['month']))
        yy = str(int(st.session_state['year']))[-2:]
        mm = int(st.session_state['month'])
        pm = mm - 1 if mm > 1 else 12
        py = int(st.session_state['year']) if mm > 1 else int(st.session_state['year']) - 1
        pm_yy = str(py)[-2:]
        y1 = int(yy) - 1
        y2 = int(yy) - 2
        body_cols = [c for c in body.columns if c != "구분"]


        def _find(label):
            return next((c for c in body_cols if label in c), None)


        col_23 = next((c for c in body_cols if c.startswith("'") and "년" in c), None)
        col_24 = next((c for c in body_cols if c != col_23 and c.startswith("'") and "년" in c), None)
        col_pm = next((c for c in body_cols if c.endswith("월") and "계획" not in c), None)
        col_m = next((c for c in body_cols if "월(①)" in c and "계획" not in c), None)
        col_diff = _find("전월대비")
        col_pm_plan = next((c for c in body_cols if c.endswith("월계획")), None)
        col_m_plan = next((c for c in body_cols if c.endswith("월계획(②)")), None)
        col_gap = _find("계획대비")
        col_acc = _find("당월누적")


        def fmt_amt(x):
            if pd.isna(x): return ""
            try:
                v = float(x)
            except:
                return str(x)
            if v < 0:
                return f'<span style="color:#d32f2f;">-{abs(int(round(v))):,}</span>'
            return f"{int(round(v)):,}"


        def fmt_pct(x):
            if pd.isna(x): return ""
            try:
                v = float(x)
            except:
                return str(x)
            if v < 0:
                return f'<span style="color:#d32f2f;">-{abs(v):,.1f}</span>'
            return f"{v:,.1f}"


        disp = body.copy()
        num_cols_list = [c for c in disp.columns if c != "구분"]
        pct_mask = disp["구분"].astype(str).str.endswith("(%)")
        for c in num_cols_list:
            disp[c] = pd.to_numeric(disp[c], errors="coerce")
            disp.loc[~pct_mask, c] = disp.loc[~pct_mask, c].apply(fmt_amt)
            disp.loc[pct_mask, c] = disp.loc[pct_mask, c].apply(fmt_pct)
        rename_map = {}
        if col_23:      rename_map[col_23] = f"'{y2:02d}년"
        if col_24:      rename_map[col_24] = f"'{y1:02d}년"
        if col_pm:      rename_map[col_pm] = f"{pm}월"
        if col_m:       rename_map[col_m] = f"{mm}월①"
        if col_diff:    rename_map[col_diff] = "전월대비"
        if col_pm_plan: rename_map[col_pm_plan] = f"{pm}월계획"
        if col_m_plan:  rename_map[col_m_plan] = f"{mm}월계획②"
        if col_gap:     rename_map[col_gap] = "계획대비"
        if col_acc:     rename_map[col_acc] = "당월누적"
        disp = disp.rename(columns=rename_map)
        empty_row = {c: "" for c in disp.columns}


        def insert_empty_after(df, gubun_value):
            idx_list = df.index[df["구분"].astype(str).str.strip() == gubun_value].tolist()
            if not idx_list:
                return df
            insert_at = idx_list[-1] + 1
            upper = df.iloc[:insert_at]
            lower = df.iloc[insert_at:]
            empty = pd.DataFrame([empty_row])
            return pd.concat([upper, empty, lower], ignore_index=True)


        disp = insert_empty_after(disp, "영업이익(%)")
        disp = insert_empty_after(disp, "수출개별")
        col_list = disp.columns.tolist()
        ci = {c: i + 1 for i, c in enumerate(col_list)}
        bc_24 = rename_map.get(col_24, "")
        bc_m = rename_map.get(col_m, "")
        bc_diff = rename_map.get(col_diff, "")
        bc_mplan = rename_map.get(col_m_plan, "")
        styles = [
            {'selector': 'table', 'props': [('border-collapse', 'collapse'), ('width', '100%'), ('font-size', '15px')]},
            {'selector': 'thead th',
             'props': [('border', '1px solid #aaa'), ('padding', '8px 16px'), ('font-size', '15px'),
                       ('text-align', 'center'), ('font-weight', '700'), ('background-color', 'white'),
                       ('white-space', 'nowrap')]},
            {'selector': 'tbody td',
             'props': [('border', '1px solid #aaa'), ('padding', '8px 16px'), ('font-size', '15px'),
                       ('text-align', 'right')]},
            {'selector': 'tbody td:nth-child(1), thead th:nth-child(1)',
             'props': [('text-align', 'left'), ('white-space', 'nowrap')]},
            {'selector': 'tbody td:first-child', 'props': [('text-align', 'left'), ('white-space', 'pre')]},
        ]
        for bc in [bc_24, bc_m, bc_diff, bc_mplan]:
            if bc and bc in ci:
                n = ci[bc]
                styles.append({'selector': f'tbody td:nth-child({n})', 'props': [('border-right', '1px solid #aaa')]})
                styles.append({'selector': f'thead th:nth-child({n})', 'props': [('border-right', '1px solid #aaa')]})

        # ── 👇 [질문자님 정답 리스트 100% 완전 고대로 반영 및 중복 처리] 👇 ──
        lv0_items = ['매출액', '판매량', '매출원가', '매출이익', '매출이익(%)', '판관비', '영업이익', '영업이익(%)', '판매비', '판매량']
        lv1_items = ['제품등', '부산물', '제품원가', 'C조건 선임', '클레임', '재고평가분', '단가소급 등', '인건비', '관리비', '판매비', '내수운반', '수출개별',
                     '내수', '수출']

        indent_labels = []
        vanmebi_seen = 0

        # 데이터 위에서부터 순차적으로 읽으며 중복된 판매비 처리
        for val in disp['구분']:
            clean = str(val).strip()
            if not clean:
                indent_labels.append(val)
                continue

            if clean == "판매비":
                vanmebi_seen += 1
                # 첫 번째 판매비는 레벨 0, 두 번째 판매비는 레벨 1
                lv = 0 if vanmebi_seen == 1 else 1
            elif clean in lv0_items:
                lv = 0
            elif clean in lv1_items:
                lv = 1
            else:
                lv = 0

            padding = lv * 16
            indent_labels.append(f'<span style="padding-left:{padding}px">{val}</span>')

        disp['구분'] = indent_labels
        # ── 👆 수정 끝 👆 ──

        new_cols, seen = [], {}
        df_render = disp.copy()
        for c in df_render.columns:
            s = str(c);
            seen[s] = seen.get(s, 0) + 1
            new_cols.append(s if seen[s] == 1 else f"{s}.{seen[s] - 1}")
        df_render.columns = new_cols
        styled = (
            df_render.style.format(lambda x: x if isinstance(x, str) else ("" if pd.isna(x) else f"{x:,.0f}")).hide(
                axis="index").set_table_styles(styles))
        st.markdown(f"<div style='overflow-x:auto'>{styled.to_html(escape=False)}</div>", unsafe_allow_html=True)
        try:
            display_memo('f_19', year, month)
        except NameError:
            pass
    except Exception as e:
        st.error(f"손익요약 생성 중 오류: {e}")
    st.divider()

def resolve_period(df, sel_y, sel_m):
    d = df.copy()
    d["연도"] = pd.to_numeric(d["연도"], errors="coerce").astype("Int64")
    d["월"]   = pd.to_numeric(d["월"],   errors="coerce").astype("Int64")
    d = d.dropna(subset=["연도","월"])
    periods = set(zip(d["연도"].astype(int), d["월"].astype(int)))
    if (sel_y, sel_m) in periods:
        return sel_y, sel_m, False
    ly = int(d["연도"].max())
    lm = int(d[d["연도"]==ly]["월"].max())
    return ly, lm, True

with t2:
    st.markdown("<h4>1) 전월대비 손익차이 </h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:right; font-size:13px; color:#666;'>[단위: 톤, 백만원]</div>", unsafe_allow_html=True)
    st.divider()
    st.markdown("<h4>2) 수출 환율 차이 </h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 톤, 백만원]</div>", unsafe_allow_html=True)
    try:
        file_name = st.secrets["sheets"]["f_21"]
        df_src = pd.read_csv(file_name)
        use_y = int(st.session_state["year"])
        use_m = int(st.session_state["month"])
        body, prev_lab, curr_lab, usd_delta, usd_effect = modules.fx_export_table(df_long=df_src, year=use_y, month=use_m)
        disp = body.copy()
        for c in disp.columns:
            if c == "구분": continue
            disp[c] = pd.to_numeric(disp[c], errors="coerce")
        def fmt_rate(x):
            if pd.isna(x): return ""
            return f'<span style="color:#d32f2f;">-{abs(x):,.2f}</span>' if x < 0 else f"{x:,.2f}"
        def fmt_diff(x):
            if pd.isna(x): return ""
            return f'<span style="color:#d32f2f;">-{abs(x):,.1f}</span>' if x < 0 else f"{x:,.1f}"
        def fmt_int(x):
            if pd.isna(x): return ""
            return f'<span style="color:#d32f2f;">-{abs(int(round(x))):,}</span>' if x < 0 else f"{int(round(x)):,}"
        rate_cols = [c for c in disp.columns if c.endswith("환율")]
        diff_cols = ["차이단가"]
        int_cols  = [c for c in disp.columns if c not in (["구분"] + rate_cols + diff_cols)]
        for c in rate_cols: disp[c] = disp[c].apply(fmt_rate)
        for c in diff_cols: disp[c] = disp[c].apply(fmt_diff)
        for c in int_cols:  disp[c] = disp[c].apply(fmt_int)
        block_prev = [f"{prev_lab}_중량", f"{prev_lab}_외화공급가액", f"{prev_lab}_환율", f"{prev_lab}_원화공급가액"]
        block_curr = [f"{curr_lab}_중량", f"{curr_lab}_외화공급가액", f"{curr_lab}_환율", f"{curr_lab}_원화공급가액"]
        tail_cols  = ["차이단가", "영향금액"]
        ordered = ["구분"] + [c for c in block_prev if c in disp.columns] + [c for c in block_curr if c in disp.columns] + tail_cols
        disp = disp[ordered]
        rename_map = {
            f"{prev_lab}_중량": f"{prev_lab} 중량", f"{prev_lab}_외화공급가액": f"{prev_lab} 외화공급가액",
            f"{prev_lab}_환율": f"{prev_lab} 환율", f"{prev_lab}_원화공급가액": f"{prev_lab} 원화공급가액",
            f"{curr_lab}_중량": f"{curr_lab} 중량", f"{curr_lab}_외화공급가액": f"{curr_lab} 외화공급가액",
            f"{curr_lab}_환율": f"{curr_lab} 환율", f"{curr_lab}_원화공급가액": f"{curr_lab} 원화공급가액",
            "차이단가": "환율차이 차이단가", "영향금액": "환율차이 영향금액",
        }
        disp = disp.rename(columns=rename_map)
        total_mask = disp["구분"].astype(str).str.strip() == "총계"
        total_rows = disp.index[total_mask].tolist()
        col_list = disp.columns.tolist()
        ci = {c: i+1 for i, c in enumerate(col_list)}
        prev_last = rename_map.get(f"{prev_lab}_원화공급가액", "")
        curr_last = rename_map.get(f"{curr_lab}_원화공급가액", "")
        styles = [
            {'selector': 'table', 'props': [('border-collapse', 'collapse'), ('width', '100%'), ('font-size', '15px')]},
            {'selector': 'thead th', 'props': [('border', '1px solid #aaa'), ('padding', '8px 16px'), ('font-size', '15px'), ('text-align', 'center'), ('font-weight', '700'), ('background-color', 'white'), ('white-space', 'nowrap')]},
            {'selector': 'tbody td', 'props': [('border', '1px solid #aaa'), ('padding', '8px 16px'), ('font-size', '15px'), ('text-align', 'right')]},
            {'selector': 'tbody td:nth-child(1), thead th:nth-child(1)', 'props': [('text-align', 'left'), ('white-space', 'nowrap')]},
        ]
        for bc in [prev_last, curr_last]:
            if bc and bc in ci:
                n = ci[bc]
                styles.append({'selector': f'tbody td:nth-child({n})', 'props': [('border-right', '1px solid #aaa')]})
                styles.append({'selector': f'thead th:nth-child({n})', 'props': [('border-right', '1px solid #aaa')]})

        for tr in total_rows:
            nth = tr + 1
            styles.append({'selector': f'tbody tr:nth-child({nth}) td', 'props': [('font-weight', '700'), ('color', 'black')]})
        new_cols, seen = [], {}
        df_render = disp.copy()
        for c in df_render.columns:
            s = str(c); seen[s] = seen.get(s, 0) + 1
            new_cols.append(s if seen[s] == 1 else f"{s}.{seen[s]-1}")
        df_render.columns = new_cols
        styled = (df_render.style.format(lambda x: x if isinstance(x, str) else ("" if pd.isna(x) else f"{x:,.0f}")).hide(axis="index").set_table_styles(styles))
        st.markdown(f"<div style='overflow-x:auto'>{styled.to_html()}</div>", unsafe_allow_html=True)
        display_memo('f_21', year, month)
    except Exception as e:
        st.error(f"수출 환율 차이 생성 중 오류: {e}")
    st.divider()

with t3:
    st.markdown("<h4>1) 포스코 對 JFE 입고가격 </h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 천원/톤]</div>",
                unsafe_allow_html=True)
    try:
        file_name = st.secrets["sheets"]["f_23"]
        raw = pd.read_csv(file_name, dtype=str)
        raw["연도"] = pd.to_numeric(raw["연도"], errors="coerce")
        raw["월"] = pd.to_numeric(raw["월"], errors="coerce")
        sel_y = int(st.session_state["year"])
        sel_m = int(st.session_state["month"])
        wide, col_order, hdr1_labels, hdr2_labels = modules.build_posco_jfe_price_wide(raw, sel_y, sel_m,
                                                                                       group_name="포스코 對 JFE 입고가격")
        idx_df = wide.index.to_frame(index=False)


        def make_row_label(row):
            kind = str(row["kind"]).strip()
            party = str(row["party"]).strip()
            item = str(row["item"]).strip()
            if party == "포스코 할인단가(원)": return "포스코 할인단가(원)"
            if party == "환율": return "환율"
            if party == "차이":
                if kind == "탄소강": return "탄소강_차이(ⓐ-ⓑ)"
                if kind == "합금강": return "합금강_차이(ⓒ-ⓓ)"
            item_map = {
                ("탄소강", "SWRCH45FS"): "탄소강_포스코_SWRCH45FS(ⓐ)",
                ("탄소강", "변동폭(천원/톤)"): "탄소강_포스코_SWRCH45FS_변동폭(천원/톤)",
                ("탄소강", "SWRCH45K-M"): "탄소강_JFE_SWRCH45K-M(ⓑ)",
                ("탄소강", "(USD)"): "탄소강_JFE_SWRCH45K-M(USD)",
                ("탄소강", "변동폭(USD/톤)"): "탄소강_JFE_SWRCH45K-M_변동폭(USD/톤)",
                ("합금강", "SCM435H Y73"): "합금강_포스코_SCM435H Y73(ⓒ)",
                ("합금강", "변동폭(천원/톤)"): "합금강_포스코_SCM435H Y73_변동폭(천원/톤)",
                ("합금강", "SCM435H"): "합금강_JFE_SCM435H(ⓓ)",
                ("합금강", "(USD)"): "합금강_JFE_SCM435H_USD",
                ("합금강", "변동폭(USD/톤)"): "합금강_JFE_SCM435H_변동폭(USD/톤)",
            }
            return item_map.get((kind, item), "")


        last_kind = ""
        new_kinds = []
        for _, row in idx_df.iterrows():
            k = str(row["kind"]).strip()
            if k and k != "nan": last_kind = k
            new_kinds.append(last_kind)
        idx_df = idx_df.copy()
        idx_df["kind"] = new_kinds
        row_labels = idx_df.apply(make_row_label, axis=1).tolist()
        vis = wide.copy()
        for c in vis.columns:
            vis[c] = [("" if (isinstance(x, float) and pd.isna(x)) else str(x)) for x in vis[c]]
        disp = vis.copy()
        disp.index = row_labels
        disp = disp.reset_index()
        disp.rename(columns={"index": "구분"}, inplace=True)
        dyn_pat = re.compile(r"^(?P<m>\d{1,2})월\((?P<y>\d{4})\)$")
        rename_map = {}
        for c in disp.columns:
            if c == "구분": continue
            if c.endswith("년 월평균"):
                y_str = c[:4];
                yy = y_str[-2:];
                y_int = int(y_str)
                rename_map[c] = f"'{yy}년 12월" if y_int == sel_y - 1 else f"'{yy}년 월평균"
            else:
                mt = dyn_pat.match(c)
                if mt:
                    y_val = int(mt.group("y"));
                    m_val = int(mt.group("m"));
                    yy = str(y_val)[-2:]
                    rename_map[c] = f"'{yy}년 {m_val}월"
        disp = disp.rename(columns=rename_map)


        # ── 👇 Lv class 들여쓰기 적용 (하드코딩 수정) 👇 ──
        def get_indent_f23(name):
            clean = str(name).strip()

            # 레벨 0 (들여쓰기 없음): 최상위 항목 및 주요 차이 항목
            lv0_items = [
                "포스코 할인단가(원)",
                "환율",
                "탄소강_차이(ⓐ-ⓑ)",
                "합금강_차이(ⓒ-ⓓ)",
                "탄소강_포스코_SWRCH45FS(ⓐ)",
                "탄소강_JFE_SWRCH45K-M(ⓑ)",
                "합금강_포스코_SCM435H Y73(ⓒ)",
                "합금강_JFE_SCM435H(ⓓ)"
            ]

            if clean in lv0_items:
                lv = 0
            else:
                # 레벨 1 (16px 들여쓰기): 그 외 세부 변동폭 및 USD 항목들
                lv = 1

            return f'<span style="padding-left:{lv * 16}px">{name}</span>'


        disp['구분'] = disp['구분'].apply(get_indent_f23)
        # ── 👆 들여쓰기 적용 끝 👆 ──

        # CSS 스타일 (다른 표와 동일하게 셀 여백 8px 16px 일괄 적용)
        styles = [
            {'selector': 'table',
             'props': [('border-collapse', 'collapse'), ('width', '100%'), ('font-size', '15px')]},
            {'selector': 'thead th',
             'props': [('border', '1px solid #aaa'), ('padding', '8px 16px'), ('font-size', '15px'),
                       ('text-align', 'center'), ('font-weight', '700'), ('background-color', 'white'),
                       ('white-space', 'nowrap')]},
            {'selector': 'tbody td',
             'props': [('border', '1px solid #aaa'), ('padding', '8px 16px'), ('font-size', '15px'),
                       ('text-align', 'right')]},
            {'selector': 'tbody td:nth-child(1), thead th:nth-child(1)',
             'props': [('text-align', 'left'), ('white-space', 'nowrap')]},
            {'selector': 'tbody td:first-child', 'props': [('text-align', 'left'), ('white-space', 'nowrap')]},
        ]

        new_cols, seen = [], {}
        df_render = disp.copy()
        for c in df_render.columns:
            s = str(c);
            seen[s] = seen.get(s, 0) + 1
            new_cols.append(s if seen[s] == 1 else f"{s}.{seen[s] - 1}")
        df_render.columns = new_cols

        styled = (
            df_render.style.format(lambda x: x if isinstance(x, str) else ("" if pd.isna(x) else str(x))).hide(
                axis="index").set_table_styles(styles))

        st.markdown(f"<div style='overflow-x:auto'>{styled.to_html(escape=False)}</div>", unsafe_allow_html=True)
        display_memo('f_23', year, month)
    except Exception as e:
        st.error(f"포스코 對 JFE 입고가격 생성 오류: {e}")

    st.divider()

    st.markdown("<h4>2) 포스코/JFE 투입비중 </h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 백만원, 톤]</div>", unsafe_allow_html=True)
    try:
        file_name = st.secrets["sheets"]["f_24"]
        df_src = pd.read_csv(file_name, dtype=str)

        # 컬럼 공백 제거 및 숫자형 변환
        df_src.columns = df_src.columns.str.strip()
        df_src["연도"] = pd.to_numeric(df_src["연도"], errors="coerce")
        df_src["월"] = pd.to_numeric(df_src["월"], errors="coerce")

        sel_y = int(st.session_state["year"])
        sel_m = int(st.session_state["month"])
        ret = modules.build_posco_jfe_wide(df_src, sel_y, sel_m)
        wide = ret[0] if isinstance(ret, tuple) else ret


        def _fmt(idx, v):
            if pd.isna(v): return ""
            metric = idx[2] if isinstance(idx, tuple) and len(idx) > 2 else ""
            if metric == "비중":
                return f"({abs(v):.1f}%)" if v < 0 else f"{v:.1f}%"
            iv = int(round(v))
            return f"({abs(iv):,})" if v < 0 else f"{iv:,}"


        vis = wide.copy()
        for c in vis.columns:
            vis[c] = [_fmt(i, x) for i, x in zip(vis.index, vis[c])]

        disp = vis.reset_index()
        disp.rename(columns={"kind": "kind", "sub": "sub", "metric": "metric"}, inplace=True)


        def make_row_label2(row):
            kind = str(row.get("kind", "")).strip()
            sub = str(row.get("sub", "")).strip()
            metric = str(row.get("metric", "")).strip()
            if sub == "JFE 사용비중": return "JFE 사용비중"
            if sub == "전월(전년)대비 손익영향 금액": return "전월(전년)대비 손익영향 금액"
            parts = []
            if kind and kind != "nan": parts.append(kind)
            if sub and sub != "nan": parts.append(sub)
            if metric and metric != "nan" and metric != sub: parts.append(metric)
            return "_".join(parts)


        last_kind = ""
        new_kinds = []
        for _, row in disp.iterrows():
            k = str(row.get("kind", "")).strip()
            if k and k != "nan": last_kind = k
            new_kinds.append(last_kind)

        disp["kind"] = new_kinds
        disp["구분"] = disp.apply(make_row_label2, axis=1)


        # ── 👇 [수정] 100% 완전 일치 방식 + 볼드체 제거 반영 👇 ──
        def apply_exact_indent(name):
            clean_name = str(name).strip()

            # 레벨 0 (들여쓰기 없음)
            lv0_items = [
                "탄소강_평균단가",
                "합금강_평균단가",
                "JFE 사용비중",
                "전월(전년)대비 손익영향 금액",
                "탄소강_탄소강_평균단가",
                "합금강_합금강_평균단가"
            ]

            # 레벨 1 (들여쓰기 적용)
            # ※ 표에 조합되어 나오는 이름을 고려해 혹시 모를 중복단어(예:탄소강_탄소강) 패턴도 모두 포함시켰습니다.
            lv1_items = [
                "탄소강_포스코_중량", "탄소강_포스코_비중",
                "탄소강_JFE_중량", "탄소강_JFE_비중",
                "합금강_포스코_중량", "합금강_포스코_비중",
                "합금강_JFE_중량", "합금강_JFE_비중",
                "탄소강_탄소강_포스코_중량", "탄소강_탄소강_포스코_비중",
                "탄소강_탄소강_JFE_중량", "탄소강_탄소강_JFE_비중",
                "합금강_합금강_포스코_중량", "합금강_합금강_포스코_비중",
                "합금강_합금강_JFE_중량", "합금강_합금강_JFE_비중"
            ]

            if clean_name in lv0_items:
                lv = 0
            elif clean_name in lv1_items:
                lv = 1
            else:
                lv = 0

                # 레벨 1이면 16px 들여쓰기, 아니면 기본 출력 (볼드체 제거됨)
            if lv > 0:
                return f'<span style="padding-left:16px;">{name}</span>'
            else:
                return f'<span>{name}</span>'


        disp["구분"] = disp["구분"].apply(apply_exact_indent)
        # ────────────────────────────────────────────────────────

        disp = disp.drop(columns=["kind", "sub", "metric"])
        cols_order = ["구분"] + [c for c in disp.columns if c != "구분"]
        disp = disp[cols_order]

        dyn_pat = re.compile(r"^(?P<m>\d{1,2})월\((?P<y>\d{4})\)$")
        rename_map = {}
        for c in disp.columns:
            if c == "구분": continue
            if c.endswith("년 월평균"):
                y_str = c[:4];
                yy = y_str[-2:];
                y_int = int(y_str)
                rename_map[c] = f"'{yy}년 12월" if y_int == sel_y - 1 else f"'{yy}년 월평균"
            else:
                mt = dyn_pat.match(c)
                if mt:
                    y_val = int(mt.group("y"));
                    m_val = int(mt.group("m"));
                    yy = str(y_val)[-2:]
                    rename_map[c] = f"'{yy}년 {m_val}월"
        disp = disp.rename(columns=rename_map)


        def fmt_val(x):
            if not isinstance(x, str): return ""
            x = x.strip()
            if x.startswith("(") and x.endswith(")"):
                inner = x[1:-1].replace("%", "")
                return f'<span style="color:#d32f2f;">-{inner}</span>'
            return x


        for c in disp.columns:
            if c == "구분": continue
            disp[c] = disp[c].apply(fmt_val)

        styles = [
            {'selector': 'table', 'props': [('border-collapse', 'collapse'), ('width', '100%'), ('font-size', '15px')]},
            {'selector': 'thead th',
             'props': [('border', '1px solid #aaa'), ('padding', '8px 16px'), ('font-size', '15px'),
                       ('text-align', 'center'), ('font-weight', '700'), ('background-color', 'white'),
                       ('white-space', 'nowrap')]},
            {'selector': 'tbody td',
             'props': [('border', '1px solid #aaa'), ('padding', '8px 16px'), ('font-size', '15px'),
                       ('text-align', 'right')]},
            {'selector': 'tbody td:nth-child(1), thead th:nth-child(1)',
             'props': [('text-align', 'left'), ('white-space', 'nowrap')]},
        ]

        new_cols, seen = [], {}
        df_render = disp.copy()
        for c in df_render.columns:
            s = str(c);
            seen[s] = seen.get(s, 0) + 1
            new_cols.append(s if seen[s] == 1 else f"{s}.{seen[s] - 1}")
        df_render.columns = new_cols

        styled = (df_render.style.format(lambda x: x if isinstance(x, str) else ("" if pd.isna(x) else str(x))).hide(
            axis="index").set_table_styles(styles))

        st.markdown(f"<div style='overflow-x:auto'>{styled.to_html(escape=False)}</div>", unsafe_allow_html=True)
        st.markdown(
            "<div style='text-align:left; font-size:17px; color:black; font-weight: bold;'>※ 전월대비 손익영향 금액 = 당월 포스코比 JFE 단가차이 x (당월 JFE 중량 - 전월 JFE 비중 적용시 당월 JFE 중량) </div>",
            unsafe_allow_html=True)

        display_memo('f_24', sel_y, sel_m)
    except Exception as e:
        st.error(f"포스코/JFE 투입비중 생성 오류: {e}")

    st.divider()

    st.markdown("<h4>3) 메이커별 입고추이 </h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 톤, 톤/천원]</div>", unsafe_allow_html=True)

    try:
        file_name = st.secrets["sheets"]["f_25"]
        df_src = pd.read_csv(file_name, dtype=str)
        df_src["연도"] = pd.to_numeric(df_src["연도"], errors="coerce")
        df_src["월"] = pd.to_numeric(df_src["월"], errors="coerce")

        sel_y = int(st.session_state["year"])
        sel_m = int(st.session_state["month"])

        wide, cols_mi = modules.build_maker_receipt_wide(df_src, sel_y, sel_m, base_year=sel_y - 1)

        # === 구분_항목 flatten → 1열 구분 ===
        disp = wide.reset_index()

        # 인덱스 컬럼명 확인 후 처리
        idx_cols = disp.columns[:2].tolist()  # 첫 두 컬럼이 구분, 항목
        col_maker = idx_cols[0]
        col_item = idx_cols[1]

        # kind 빈값 채우기
        last_maker = ""
        new_makers = []
        for _, row in disp.iterrows():
            k = str(row[col_maker]).strip()
            if k and k not in ("", "nan"): last_maker = k
            new_makers.append(last_maker)
        disp[col_maker] = new_makers


        def make_maker_label(row):
            maker = str(row[col_maker]).strip()
            item = str(row[col_item]).strip()
            return f"{maker}_{item}"


        disp["구분_new"] = disp.apply(make_maker_label, axis=1)
        disp = disp.drop(columns=[col_maker, col_item])
        disp.insert(0, "구분", disp.pop("구분_new"))



        # === 컬럼명 flatten (멀티인덱스 → 1행) ===
        def make_col_label(col):
            top, bot = str(col[0]).strip(), str(col[1]).strip()
            # 매입비중은 상단 라벨에 포함
            if bot == "매입비중":
                return f"{top} 매입비중"
            # 월평균
            if bot == "월평균":
                return f"{top} 월평균"
            # 중량 (직전 2개월)
            if bot == "중량":
                return f"{top}"
            return f"{top}_{bot}"


        new_cols = [make_col_label(c) for c in cols_mi]
        disp.columns = ["구분"] + new_cols


        # === 포맷 (숫자 ÷1000 반올림 + 증감 색상/화살표) ===
        def fmt_cell_flat(col_name, val, is_jungam=False):
            if val == "" or (isinstance(val, float) and pd.isna(val)):
                return ""
            val_str = str(val).strip()
            if "<span" in val_str:
                return val_str
            try:
                v = float(val_str.replace(",", "").replace("%", ""))
            except:
                return val_str

            if "매입비중" in col_name:
                return f"{v:.1f}%"

            # 천 단위 나누기
            iv = int(round(v / 1000))

            if is_jungam:
                if iv > 0:
                    return f'<span style="color:#1565C0;">▲ {iv:,}</span>'
                elif iv < 0:
                    return f'<span style="color:#C62828;">▼ {abs(iv):,}</span>'
                else:
                    return "0"

            return f"{iv:,}"


        for c in disp.columns:
            if c == "구분": continue
            is_jungam = disp["구분"].str.contains("증감", na=False)
            disp[c] = [
                fmt_cell_flat(c, val, jungam)
                for val, jungam in zip(disp[c], is_jungam)
            ]


        # === 스타일 ===
        col_list = disp.columns.tolist()
        ci = {c: i + 1 for i, c in enumerate(col_list)}

        styles = [
            {'selector': 'table', 'props': [('border-collapse', 'collapse'), ('width', '100%'), ('font-size', '15px')]},
            {'selector': 'thead th',
             'props': [('border', '1px solid #aaa'), ('padding', '8px 16px'), ('font-size', '15px'),
                       ('text-align', 'center'), ('font-weight', '700'), ('background-color', 'white'),
                       ('white-space', 'nowrap')]},
            {'selector': 'tbody td',
             'props': [('border', '1px solid #aaa'), ('padding', '8px 16px'), ('font-size', '15px'),
                       ('text-align', 'right')]},
            {'selector': 'tbody td:nth-child(1), thead th:nth-child(1)',
             'props': [('text-align', 'left'), ('white-space', 'nowrap')]},
        ]

        # === 렌더링 ===
        new_cols2, seen = [], {}
        df_render = disp.copy()
        for c in df_render.columns:
            s = str(c);
            seen[s] = seen.get(s, 0) + 1
            new_cols2.append(s if seen[s] == 1 else f"{s}.{seen[s] - 1}")
        df_render.columns = new_cols2

        styled = (
            df_render.style
            .format(lambda x: x if isinstance(x, str) else ("" if pd.isna(x) else str(x)))
            .hide(axis="index")
            .set_table_styles(styles)
        )

        st.markdown(f"<div style='overflow-x:auto'>{styled.to_html()}</div>", unsafe_allow_html=True)
        display_memo('f_25', year, month)

    except Exception as e:
        st.error(f"메이커별 입고추이 표 생성 오류: {e}")

    st.divider()

with t4:
    st.markdown("<h4>1) 제조 가공비 </h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 톤, 백만원]</div>",
                unsafe_allow_html=True)
    try:
        file_name = st.secrets["sheets"]["f_26"]
        raw = pd.read_csv(file_name, dtype=str)
        raw["연도"] = pd.to_numeric(raw["연도"], errors="coerce")
        raw["월"] = pd.to_numeric(raw["월"], errors="coerce")
        sel_y = int(st.session_state["year"])
        sel_m = int(st.session_state["month"])
        disp_raw, meta = modules.build_mfg_cost_table(raw, sel_y, sel_m)
        prev_y, prev_m, cur_y, cur_m = meta["prev_y"], meta["prev_m"], meta["sel_y"], meta["sel_m"]

        flat_cols = ["구분"]
        for top in ["전월", "당월", "전월대비"]:
            for sub in ["포항", "충주", "충주2", "계"]:
                flat_cols.append(f"{top}|{sub}")

        disp = disp_raw.copy()
        disp.columns = flat_cols

        # 👇 [수정] 문제의 원흉이었던 __spacer__ 강제 삽입 코드 제거 👇
        # SPACER = "__spacer__"
        # disp.insert(0, SPACER, "")

        cols = disp.columns.tolist()

        prev_short = f"'{str(prev_y)[-2:]}.{prev_m}"
        cur_short = f"'{str(cur_y)[-2:]}.{cur_m}"

        # 👇 [수정] spacer가 빠졌으므로 헤더 앞의 빈칸("")도 제거 👇
        hdr2 = ["구분"] \
               + ["포항/본사①", "충주②", "충주2③", f"{prev_short}월(①+②+③)"] \
               + ["포항/본사④", "충주⑤", "충주2⑥", f"{cur_short}월(④+⑤+⑥)"] \
               + ["포항/본사⑦", "충주⑧", "충주2⑨", "전월대비(⑦+⑧+⑨)"]

        hdr_df = pd.DataFrame([hdr2], columns=cols)
        disp_vis = pd.concat([hdr_df, disp], ignore_index=True)


        def fmt_num(구분_val, v):
            if v is None or v == "" or (isinstance(v, float) and pd.isna(v)):
                return ""
            try:
                fv = float(str(v).replace(",", "").strip())
            except:
                return str(v)
            if 구분_val == "투입중량 원단위(천원)":
                fv1 = fv / 1000
                if fv1 < 0:
                    return f'<span style="color:red;">-{abs(fv1):.1f}</span>'
                return f"{fv1:.1f}"
            elif 구분_val == "원재투입중량":
                iv = int(round(fv / 1000))
                if iv < 0:
                    return f'<span style="color:red;">-{abs(iv):,}</span>'
                return f"{iv:,}"
            else:
                iv = int(round(fv / 1000000))
                if iv < 0:
                    return f'<span style="color:red;">-{abs(iv):,}</span>'
                return f"{iv:,}"


        def fmt_cell(구분_val, key, v):
            if "|" not in key:
                return v
            if v is None or v == "" or (isinstance(v, float) and pd.isna(v)):
                return ""
            try:
                fv = float(str(v).replace(",", "").strip())
            except:
                return str(v)
            top, _ = key.split("|", 1)
            if top == "전월대비":
                if 구분_val == "투입중량 원단위(천원)":
                    fv1 = fv / 1000
                    if fv1 > 0: return f'<span style="color:#000000;">{fv1:.1f}</span>'
                    if fv1 < 0: return f'<span style="color:red;">-{abs(fv1):.1f}</span>'
                    return "0"
                elif 구분_val == "원재투입중량":
                    iv = int(round(fv / 1000))
                    if iv > 0: return f'<span style="color:#000000;">{iv:,}</span>'
                    if iv < 0: return f'<span style="color:red;">-{abs(iv):,}</span>'
                    return "0"
                else:
                    iv = int(round(fv / 1000000))
                    if iv > 0: return f'<span style="color:#000000;">{iv:,}</span>'
                    if iv < 0: return f'<span style="color:red;">-{abs(iv):,}</span>'
                    return "0"
            else:
                return fmt_num(구분_val, fv)


        body = disp_vis.copy()
        data_rows = body.index[1:]

        # 👇 [수정] spacer가 없어졌으므로 데이터 컬럼 시작 인덱스를 2에서 1로 조정 👇
        for c in body.columns[1:]:
            for idx in data_rows:
                구분_val = str(body.loc[idx, "구분"]).strip()
                body.loc[idx, c] = fmt_cell(구분_val, c, body.loc[idx, c])

        # ── Lv class 들여쓰기 적용 ──
        if 'Lv class' in raw.columns:
            level_map = {}
            for _, row in raw[['구분2', 'Lv class']].dropna(subset=['구분2']).iterrows():
                name = str(row['구분2']).strip()
                try:
                    level_map[name] = int(float(row['Lv class']))
                except (TypeError, ValueError):
                    level_map[name] = 0


            def get_indent_f26(name):
                clean = str(name).strip()
                lv = level_map.get(clean, 0)
                return f'<span style="padding-left:{lv * 16}px">{name}</span>'


            for idx in data_rows:
                val = str(body.loc[idx, "구분"]).strip()
                body.loc[idx, "구분"] = get_indent_f26(val)

        # 👇 [수정] 표를 정상화하는 CSS 업데이트 (끊김 현상 및 띄어쓰기 복구) 👇
        styles = [
            {'selector': 'thead', 'props': [('display', 'none')]},
            {'selector': 'table',
             'props': [('border-collapse', 'collapse'), ('width', '100%'), ('font-size', '15px')]},
            {'selector': 'tbody td',
             'props': [('border', '1px solid #aaa'), ('padding', '8px 16px'), ('text-align', 'right'),
                       ('font-weight', 'normal')]},
            # 구분 컬럼(첫 번째) 좌측 정렬
            {'selector': 'tbody td:nth-child(1)',
             'props': [('text-align', 'left'), ('white-space', 'nowrap')]},
            # 헤더 역할을 하는 첫 번째 행 디자인 (가운데 정렬, 굵게, 위 테두리 추가)
            {'selector': 'tbody tr:nth-child(1) td',
             'props': [('text-align', 'center'), ('font-weight', '700'), ('background-color', 'white'),
                       ('white-space', 'nowrap'), ('border-top', '1px solid #aaa')]},
        ]

        new_cols2, seen = [], {}
        df_render = body.copy()
        for c in df_render.columns:
            s = str(c)
            seen[s] = seen.get(s, 0) + 1
            new_cols2.append(s if seen[s] == 1 else f"{s}.{seen[s] - 1}")
        df_render.columns = new_cols2

        styled = (
            df_render.style
            .format(lambda x: x if isinstance(x, str) else ("" if pd.isna(x) else str(x)))
            .hide(axis="index")
            .set_table_styles(styles)
        )
        st.markdown(f"<div style='overflow-x:auto'>{styled.to_html(escape=False)}</div>", unsafe_allow_html=True)
        display_memo('f_26', sel_y, sel_m)
    except Exception as e:
        st.error(f"제조가공비 표 생성 오류: {e}")

    st.divider()
with t5:
    st.markdown("<h4>1) 판매비와 관리비 </h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 톤, 백만원]</div>",
                unsafe_allow_html=True)
    try:
        file_name = st.secrets["sheets"]["f_27"]
        raw = pd.read_csv(file_name, dtype=str)
        raw["연도"] = pd.to_numeric(raw["연도"], errors="coerce")
        sel_y = int(st.session_state["year"])
        sel_m = int(st.session_state["month"])
        disp_raw, meta = modules.build_sgna_table(raw, sel_y, sel_m)
        avg_years = meta.get("avg_years", [])
        m2, m1, m0 = meta["months"]
        m2_col = f"{int(m2)}월"
        m1_col = f"{int(m1)}월"
        m0_col = f"{int(m0)}월"
        avg_cols = [f"'{y}년 월평균" for y in avg_years]
        desired = ["구분"] + avg_cols + [m2_col, m1_col, m0_col, "전월대비"]
        desired = [c for c in desired if c in disp_raw.columns]
        disp = disp_raw[desired].copy()


        def _month_shift(y, m, delta):
            t = y * 12 + (m - 1) + delta
            ny = t // 12;
            nm = t % 12 + 1
            return int(ny), int(nm)


        prev2_y, prev2_m = _month_shift(sel_y, sel_m, -2)
        prev_y, prev_m = _month_shift(sel_y, sel_m, -1)
        cur_y, cur_m = sel_y, sel_m


        def fmt_num(v, is_avg=False):
            if pd.isna(v): return ""
            try:
                fv = float(v)
                iv = int(round(fv if is_avg else fv / 1_000_000))
            except:
                return v
            if iv < 0: return f'<span style="color:red">-{abs(iv):,}</span>'
            return f"{iv:,}"


        def fmt_diff(v):
            if pd.isna(v): return ""
            try:
                iv = int(round(float(v) / 1_000_000))
            except:
                return v
            if iv < 0: return f'<span style="color:red">-{abs(iv):,}</span>'
            if iv > 0: return f"{iv:,}"
            return "0"


        for c in disp.columns:
            if c == "전월대비":
                disp[c] = disp[c].apply(fmt_diff)
            elif c in avg_cols:
                disp[c] = disp[c].apply(lambda v: fmt_num(v, is_avg=True))
            elif c != "구분":
                disp[c] = disp[c].apply(lambda v: fmt_num(v, is_avg=False))
        col_rename = {}
        for y in avg_years:
            col_rename[f"'{y}년 월평균"] = f"'{str(y)[-2:]}년 월평균"
        col_rename[m2_col] = f"{str(prev2_y)[-2:]}.{prev2_m}월"
        col_rename[m1_col] = f"{str(prev_y)[-2:]}.{prev_m}월"
        col_rename[m0_col] = f"{str(cur_y)[-2:]}.{cur_m}월"
        disp = disp.rename(columns=col_rename)
        # ── Lv class 들여쓰기 적용 ──
        if 'Lv class' in raw.columns:
            level_map = {}
            for _, row in raw[['구분1', 'Lv class']].dropna(subset=['구분1']).iterrows():
                name = str(row['구분1']).strip()
                try:
                    level_map[name] = int(float(row['Lv class']))
                except (TypeError, ValueError):
                    level_map[name] = 0


            def get_indent_f27(name):
                clean = str(name).strip()
                lv = level_map.get(clean, 0)
                return f'<span style="padding-left:{lv * 16}px">{name}</span>'


            disp['구분'] = disp['구분'].apply(get_indent_f27)
        styles = [
            {'selector': 'thead th',
             'props': [('text-align', 'center'), ('font-weight', '700'), ('border', '1px solid #aaa'),
                       ('background-color', 'white'), ('padding', '8px 16px'), ('font-size', '15px')]},
            {'selector': 'tbody td',
             'props': [('border', '1px solid #aaa'), ('padding', '8px 16px'), ('text-align', 'right'), ('font-size', '15px')]},
            {'selector': 'tbody td:first-child', 'props': [('text-align', 'left'), ('white-space', 'pre')]},
        ]
        styled = (
            disp.style
            .set_table_styles(styles)
            .hide(axis='index')
        )
        st.markdown(f"<div style='overflow-x:auto'>{styled.to_html(escape=False)}</div>", unsafe_allow_html=True)
        display_memo('f_27', sel_y, sel_m)
    except Exception as e:
        st.error(f"판매비와 관리비 표 생성 오류: {e}")
    st.divider()

with t6:
    st.markdown("<h4>1) 성과급 및 격려금 </h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 백만원]</div>", unsafe_allow_html=True)
    try:
        file_name = st.secrets["sheets"]["f_28"]
        df_src = pd.read_csv(file_name, dtype=str)
        sel_y = int(st.session_state["year"])
        sel_m = int(st.session_state["month"])
        disp, meta = modules.build_bonus_table_28(df_src, sel_y, sel_m)

        def fmt_num(v):
            if pd.isna(v) or v is None: return ""
            try:
                iv = int(round(float(v) / 1_000))
            except:
                return ""
            if iv == 0: return "0"
            if iv < 0: return f'<span style="color:red">-{abs(iv):,}</span>'
            return f"{iv:,}"

        for c in disp.columns:
            if c != "구분":
                disp[c] = disp[c].apply(fmt_num)

        styles = [
            {'selector': 'thead th', 'props': [
                ('text-align', 'center'),
                ('font-weight', '700'),
                ('border', '1px solid #aaa'),
                ('background-color', 'white'),
                ('padding', '8px 16px'),
                ('font-size', '15px')
            ]},
            {'selector': 'tbody td', 'props': [
                ('border', '1px solid #aaa'),
                ('padding', '8px 16px'),
                ('text-align', 'right'),
                ('font-size', '15px')
            ]},
            {'selector': 'tbody td:first-child', 'props': [
                ('text-align', 'left'),
                ('white-space', 'nowrap')
            ]},
        ]

        styled = (
            disp.style
            .set_table_styles(styles)
            .hide(axis='index')
        )

        st.markdown(
            f"<div style='overflow-x:auto'>{styled.to_html(escape=False)}</div>",
            unsafe_allow_html=True
        )
        display_memo('f_28', sel_y, sel_m)

    except Exception as e:
        st.error(f"성과급 및 격려금 표 생성 오류: {e}")
    st.divider()


st.markdown("""
<style>.footer { bottom: 0; left: 0; right: 0; padding: 8px; text-align: center; font-size: 13px; color: #666666;}</style>
<div class="footer">ⓒ 2025 SeAH Special Steel Corp. All rights reserved.</div>
""", unsafe_allow_html=True)
