import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from auth import require_login
import warnings
import plotly.graph_objects as go
import modules

warnings.filterwarnings('ignore')
st.set_page_config(layout="wide", initial_sidebar_state="expanded")
require_login()

# 🟢 [오류 수정] modules.update_performance_form 내부의 작은따옴표 포함 int 변환 버그("20'26") 우회 보정 로직
def fixed_update_performance_form(year, month):
    all_dfs = {}
    file_name = st.secrets['sheets']['f_89']
    data = pd.read_csv(file_name)

    data['실적'] = data['실적'].astype(str).str.replace(r'\(', '-', regex=True).str.replace(r'\)', '', regex=True)
    data['실적'] = pd.to_numeric(data['실적'].str.replace(",", ""), errors='coerce')
    data.loc[data['구분2'] != '판매량', '실적'] /= 1_000_000
    data.loc[data['구분2'] == '판매량', '실적'] /= 1_000

    for category in data['구분1'].unique():
        df = modules.create_performance_form(year, month)

        for col in df.columns:
            # 💡 작은따옴표(')를 완전히 제거하여 "20'26" 에러를 원천 차단합니다.
            yy = int("20" + col.split(" ")[0].replace("년", "").replace("'", ""))
            mm = int(col.split(" ")[1].replace("월", ""))

            temp = data[
                (data['연도'] == yy) &
                (data['월'] == mm) &
                (data['구분1'] == category)
                ]

            if temp.empty:
                df.loc[:, col] = 0
            else:
                df.loc[:, col] = round(temp['실적'], 0).astype('Int64').to_list()

        # 영업이익률 계산
        sales = df.loc['매출액', :].replace(0, np.nan)
        df.loc['영업이익률', :] = (df.loc['영업이익', :] / sales) * 100
        df.loc['영업이익률', :] = (
                pd.to_numeric(df.loc['영업이익률', :], errors='coerce')
                .round(1)
                .astype(str)
                + "%"
        )

        all_dfs[category] = df

    return all_dfs

# 에러가 발생하는 모듈 함수를 안전한 수정본 함수로 강제 대체합니다.
modules.update_performance_form = fixed_update_performance_form


# --- Helper Functions (도우미 함수) ---
@st.cache_data(ttl=1800)
def load_data(url):
    """CSV 데이터를 로드하고 기본 전처리를 수행합니다."""
    data = pd.read_csv(url, thousands=',')
    data['실적'] = round(data['실적']).astype(float)
    data['월'] = data['월'].astype(str).apply(lambda x: x if '월' in x else x + '월')
    data = data.fillna('')
    return data


def display_summary_chart(df, key, yaxis1_range, yaxis2_range):
    """실적 요약(막대+꺾은선) 차트를 생성하고 화면에 표시합니다."""
    plot_rows = ['매출액', '판매량', '영업이익']
    df_plot = df.loc[plot_rows].copy()

    # 최근 13개월만 선택
    df_plot = df_plot.iloc[:, -13:]

    # 숫자형 변환
    sales = pd.to_numeric(df_plot.loc['매출액'], errors='coerce')
    profit = pd.to_numeric(df_plot.loc['영업이익'], errors='coerce')

    # 매출이 0이면 영업이익률 0, 아니면 계산
    margin = np.where(sales == 0, 0, (profit / sales) * 100)

    df_plot.loc['영업이익률'] = margin
    df_plot = df_plot.T

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df_plot.index, y=df_plot['매출액'], name='매출액', marker_color='#3b4951',
        width=0.4, text=df_plot['매출액'], texttemplate='%{text:,.0f}',
        textposition='inside', insidetextanchor='middle', insidetextfont=dict(color='white'),
        textangle=0
    ))
    fig.add_trace(go.Bar(
        x=df_plot.index, y=df_plot['판매량'], name='판매량', marker_color='#e54e2b',
        width=0.4, text=df_plot['판매량'], texttemplate='%{text:,.0f}',
        textposition='inside', insidetextanchor='middle', insidetextfont=dict(color='white'),
        textangle=0
    ))

    # 텍스트와 hovertemplate를 위한 데이터 준비
    custom_text = [
        f"{profit:,.0f}<br>({margin:.1f}%)"
        for profit, margin in zip(df_plot['영업이익'], df_plot['영업이익률'])
    ]

    fig.add_trace(go.Scatter(
        x=df_plot.index, y=df_plot['영업이익'], name='영업이익', mode='lines+markers+text',
        text=custom_text, customdata=df_plot['영업이익률'],
        hovertemplate='<b>%{x}</b><br>영업이익: %{y:,.0f}<br>영업이익률: %{customdata:.1f}%<extra></extra>',
        marker=dict(size=8, color='grey'), line=dict(width=3, color='grey'),
        yaxis='y2', textposition="middle right", textfont=dict(size=15, color='black')
    ))

    fig.update_layout(
        height=500, font=dict(size=15), bargap=0.2, barmode='group', plot_bgcolor='white',
        yaxis=dict(showticklabels=False, showgrid=False, zeroline=False, range=yaxis1_range),
        yaxis2=dict(showticklabels=False, overlaying='y', side='right', showgrid=False, zeroline=False,
                    range=yaxis2_range),
        xaxis=dict(showline=True, linewidth=1, linecolor='lightgrey', tickfont=dict(size=18), tickangle=0),
        legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5, font=dict(size=18)),
        margin=dict(t=80, b=20, l=20, r=20)
    )
    _, chart_col, _ = st.columns([0.2, 0.6, 0.2])
    with chart_col:
        st.plotly_chart(fig, use_container_width=True, key=key)


def display_line_chart(df, traces, key, offset_map=None):
    if offset_map is None:
        offset_map = {"합금강": 10}

    df_plot = df.T
    fig = go.Figure()
    layout_options = {}

    # y축 범위는 offset이 반영된 값으로 계산
    all_vals = []
    for trace in traces:
        series = df_plot[trace['name']]
        offset = offset_map.get(trace['name'][1], 0)
        all_vals.append(series + offset)
    all_concat = pd.concat(all_vals)
    y_min, y_max = all_concat.min(), all_concat.max()
    pad = (y_max - y_min) * 0.1
    default_y_range = [y_min - pad, y_max + pad]

    for i, trace in enumerate(traces, 1):
        axis_name = 'y' if i == 1 else f'y{i}'
        series = df_plot[trace['name']]
        offset = offset_map.get(trace['name'][1], 0)

        fig.add_trace(go.Scatter(
            x=df_plot.index,
            y=series + offset,
            name=trace['name'][1],
            mode='lines+markers+text',
            marker=dict(size=8, color=trace['color']),
            line=dict(width=3, color=trace['color']),
            yaxis=axis_name,
            text=series,
            textposition=trace.get('textposition', 'top center'),
            textfont=dict(size=15, color='black'),
            texttemplate='%{text:,.1f}',
            hovertemplate=f"<b>%{{x}}</b><br><b>{trace['name'][1]}</b>: %{{text:,.1f}}<extra></extra>",
            customdata=series,
            hoverlabel=dict(namelength=-1, bgcolor='white', bordercolor=trace['color'], font=dict(size=14))
        ))

        trace_range = trace.get('range', None)
        if trace_range is None:
            trace_range = default_y_range

        axis_config = dict(
            showticklabels=False,
            showgrid=False,
            zeroline=False,
            range=trace_range,
        )
        if i > 1:
            axis_config.update(overlaying='y', side='right')
        axis_suffix = '' if i == 1 else i
        layout_options[f'yaxis{axis_suffix}'] = axis_config

    fig.update_layout(
        height=500, font=dict(size=15), plot_bgcolor='white',
        xaxis=dict(showline=True, linewidth=1, linecolor='lightgrey',
                   tickfont=dict(size=18)),
        legend=dict(orientation="h", yanchor="bottom", y=-0.3,
                    xanchor="center", x=0.5, font=dict(size=18)),
        hovermode='x unified',
        margin=dict(t=80, b=20, l=20, r=20),
        **layout_options
    )

    _, chart_col, _ = st.columns([0.2, 0.6, 0.2])
    with chart_col:
        st.plotly_chart(fig, use_container_width=True, key=key)


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


# --- Main Streamlit App ---
modules.create_sidebar()
this_year = st.session_state['year']
current_month = st.session_state['month']

st.markdown(f"## {this_year}년 {current_month}월 별첨")

t1, t2, t3, t4, t5 = st.tabs(['실적요약', '가격차이', '환율 추이', '손익계산서', '유형별 손익분석 (수정정상원가 기반)'])
all_dfs = modules.update_performance_form(this_year, current_month)

# 전체 실적요약
with t1:
    st.markdown("<h4>1) 전체 실적요약 (해외법인 포함)</h4>", unsafe_allow_html=True)
    df_list = list(all_dfs.values())
    total_df = df_list[0].copy()

    for df in df_list[1:]:
        total_df += df

    plot_rows = ['매출액', '판매량', '영업이익']
    plot_columns = total_df.columns
    df_plot = total_df.loc[plot_rows, plot_columns].copy()

    # 숫자형 변환
    sales = pd.to_numeric(df_plot.loc['매출액', :], errors='coerce')
    profit = pd.to_numeric(df_plot.loc['영업이익', :], errors='coerce')

    # 매출액이 0이면 영업이익률 0으로 처리
    margin = np.where(sales == 0, 0, (profit / sales) * 100)

    df_plot.loc['영업이익률', :] = margin

    # % 표시용 문자열 변환
    df_plot.loc['영업이익률', :] = (
            pd.to_numeric(df_plot.loc['영업이익률', :], errors='coerce')
            .round(1)
            .astype(str)
            + "%"
    )

    df_plot = df_plot.T

    display_summary_chart(total_df, key="total_summary", yaxis1_range=[0, 150000], yaxis2_range=[-10000, 8000])
    st.divider()

    # 本사 실적요약
    st.markdown("<h4>2) 본사 실적요약</h4>", unsafe_allow_html=True)
    display_summary_chart(all_dfs['본사'], key="hq_summary", yaxis1_range=[0, 150000], yaxis2_range=[-10000, 8000])
    st.divider()

    # 중국법인 실적요약
    st.markdown("<h4>3) 중국법인 실적요약</h4>", unsafe_allow_html=True)
    display_summary_chart(all_dfs['중국'], key="cn_summary", yaxis1_range=[0, 40000], yaxis2_range=[-1000, 1500])
    st.divider()

    # 태국법인 실적요약
    st.markdown("<h4>4) 태국법인 실적요약</h4>", unsafe_allow_html=True)
    display_summary_chart(all_dfs['태국'], key="th_summary", yaxis1_range=[0, 10000], yaxis2_range=[-300, 600])
    st.divider()

# 환율 추이 (실제로는 가격차이 탭)
with t2:
    st.markdown("<h4>1) 포스코 대 JFE 가격 차이</h4>", unsafe_allow_html=True)
    df_raw = modules.create_df(this_year, current_month, load_data(st.secrets['sheets']['f_93']), mean="False",
                               prev_year=1, prev_month=6)
    df_plot = df_raw.loc[('가격차이', ['탄소강', '합금강']), df_raw.columns]

    traces = [
        {'name': ('가격차이', '탄소강'), 'color': '#3b4951', 'range': [-20, 450], 'textposition': 'top center'},
        {'name': ('가격차이', '합금강'), 'color': '#e54e2b', 'range': [-20, 450], 'textposition': 'bottom center'}
    ]

    display_line_chart(df_plot, traces, key="price_diff_chart", offset_map={"합금강": 65})
    st.divider()

with t3:
    st.markdown("<h4>1) 환율 추이 (USD, CNH, THB)</h4>", unsafe_allow_html=True)
    df = modules.create_df(this_year, current_month, load_data(st.secrets['sheets']['f_94']), mean="False", prev_year=1)

    df_plot = df.loc[('환율추이', ['USD', 'CNH', 'THB']), df.columns].replace(0, float('nan'))

    traces = [
        {'name': ('환율추이', 'USD'), 'color': '#3b4951', 'range': [1250, 1550], 'textposition': 'top center'},
        {'name': ('환율추이', 'CNH'), 'color': '#e54e2b', 'range': [150, 250], 'textposition': 'bottom center'},
        {'name': ('환율추이', 'THB'), 'color': '#0070c0', 'range': [30, 60], 'textposition': 'top center'}
    ]

    display_line_chart(df_plot, traces, key="exchange_rate_chart")
    st.divider()

with t4:
        st.markdown(
            """
            <div style='display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 5px;'>
                <h4 style='margin: 0;'>1) 손익계산서 수정정상원가</h4>
            </div>
            <div style='width:100%; display: flex; justify-content: flex-end; margin-bottom: 10px;'>
                <div style='font-size: 13px; color: #666;'>[단위: 백만원, 톤]</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        try:
            year = int(st.session_state["year"])
            month = int(st.session_state["month"])

            file_name = st.secrets["sheets"]["f_95"]
            df_src = pd.read_csv(file_name, dtype=str)

            if '값' in df_src.columns:
                df_src = df_src.rename(columns={'값': '실적'})

            # DB형태 데이터를 피벗팅하여 가져온다고 가정
            body = modules.build_f95(df_src, year, month)

            all_cols = list(body.columns)
            label_cols = ["구분1", "구분2", "구분3"]
            value_cols = [c for c in all_cols if c not in label_cols]

            selected_value_cols = []
            col_display_names = []

            yy_str = str(year)[-2:]

            for m in range(1, month + 1):
                col = f"{m}월"
                if col in value_cols:
                    selected_value_cols.append(col)
                    col_display_names.append(f"'{yy_str}.{m}월")

                if m % 3 == 0:
                    q = m // 3
                    col = f"{q}분기"
                    if col in value_cols:
                        selected_value_cols.append(col)
                        col_display_names.append(f"'{yy_str}.{col}")

            if month >= 4:
                col = "누계"
                if col in value_cols:
                    selected_value_cols.append(col)
                    col_display_names.append(col)

            def fmt_pct(v):
                if v == "" or pd.isna(v):
                    return ""
                try:
                    v = float(v)
                except Exception:
                    return str(v)
                if v < 0:
                    return f'<span style="color:#d62728;">-{abs(v):,.1f}%</span>'
                return f"{v:,.1f}%"

            def fmt_num(v):
                if v == "" or pd.isna(v):
                    return ""
                try:
                    v = float(v)
                    # ❗ 주의: 만약 build_f95에서 '원'단위를 '백만원' 단위로 변환하지 않았다면 아래 주석을 해제하세요.
                    # v = v / 1000000 
                except Exception:
                    return str(v)
                if v == 0:
                    return "0"
                if v < 0:
                    return f'<span style="color:#d62728;">-{abs(int(round(v))):,}</span>'
                return f"{int(round(v)):,}"

            def fmt_t(v):
                if v == "" or pd.isna(v):
                    return ""
                try:
                    v = float(v)
                except Exception:
                    return str(v)
                return f"{v:,.0f}t"

            # 🟢 [수정됨] 오타 수정 및 UI 계층(들여쓰기) 구분 적용
            def merge_label(row):
                g3 = str(row.get("구분3", "")).strip()
                g2 = str(row.get("구분2", "")).strip()
                g1 = str(row.get("구분1", "")).strip()
                
                if g3 and g3 != "nan":
                    # 구분3이 있으면 가장 하위이므로 들여쓰기 2번
                    return f"&nbsp;&nbsp;&nbsp;&nbsp;{g3}"
                elif g2 and g2 != "nan":
                    # 구분2만 있으면 들여쓰기 1번
                    return f"&nbsp;&nbsp;{g2}"
                elif g1 and g1 != "nan":
                    # 구분1만 있으면 최상위 항목 (예: 매출액, 변동비)
                    return g1
                return ""

            body["구분"] = body.apply(merge_label, axis=1)
            disp = body[["구분"] + selected_value_cols].copy()

            th_style = "border:1px solid #aaa; background:white; padding:8px 16px; text-align:center; font-weight:700; font-size:15px; white-space:nowrap;"
            td_style = "border:1px solid #aaa; padding:8px 16px; text-align:right; font-weight:400; font-size:15px;"
            td_left_style = "border:1px solid #aaa; padding:8px 16px; text-align:left; font-weight:400; font-size:15px; white-space:nowrap;"

            bold_rows = {"매출액", "변동비", "한계이익", "고정비", "영업이익", "경상이익", "경상이익_재경마감"}
            pct_labels = {"DM%", "(이익율)"}
            qty_labels = {"수량"}

            for idx in disp.index:
                # 텍스트 비교를 위해 &nbsp; 등 html 엔티티 제거
                raw_label = str(disp.at[idx, "구분"]).replace("&nbsp;", "").strip()
                is_pct = raw_label in pct_labels
                is_qty = raw_label in qty_labels

                for col in selected_value_cols:
                    v = disp.at[idx, col]
                    if is_pct:
                        disp.at[idx, col] = fmt_pct(v)
                    elif is_qty:
                        disp.at[idx, col] = fmt_t(v)
                    else:
                        disp.at[idx, col] = fmt_num(v)

            header_names = ["구분"] + col_display_names
            th_cells = "".join(f'<th style="{th_style}">{c}</th>' for c in header_names)

            tr_html = ""
            col_names = list(disp.columns)
            for idx, row in disp.iterrows():
                tds = ""
                # 원본 라벨(들여쓰기 제거)을 기준으로 bold 처리 여부 결정
                raw_label = str(row[col_names[0]]).replace("&nbsp;", "").strip()
                is_bold = raw_label in bold_rows
                
                for ci, c in enumerate(col_names):
                    val = row[c]
                    val = "" if str(val) == "nan" else str(val)
                    
                    # 좌측 헤더열과 데이터열 스타일 분기 및 Bold 적용
                    base_style = td_left_style if ci == 0 else td_style
                    final_style = base_style + " font-weight:700;" if is_bold else base_style
                    
                    tds += f'<td style="{final_style}">{val}</td>'
                tr_html += f'<tr>{tds}</tr>\n'

            html_table = f"""
<div style="overflow-x:auto; width:100%;">
<table style="border-collapse:collapse; width:100%; font-family:'Noto Sans KR', sans-serif; font-size:15px;">
  <thead>
    <tr>
      {th_cells}
    </tr>
  </thead>
  <tbody>
    {tr_html}
  </tbody>
</table>
</div>
"""
        except Exception as e:
            st.error(f"손익계산서 수정정상원가 표 생성 오류: {e}")

        st.divider()

# ===== 유형별 손익분석 (탭 5) =====
with t5:
    st.markdown("<h4>1) 산업군별 영업이익 </h4>", unsafe_allow_html=True)
    st.markdown("<h6>- B급 제외</h6>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:right; font-size:13px; color:#666;'>[단위: 톤, 백만원]</div>",
                unsafe_allow_html=True)

    try:
        year = int(st.session_state['year'])
        month = int(st.session_state['month'])

        file_name = st.secrets["sheets"]["f_96"]
        df_src = pd.read_csv(file_name, dtype=str)

        disp = modules.build_f96(df_src, year, month)
        body = disp.copy()

        # ── 컬럼명 매핑 ──
        col_label_map = {}
        if "구분" in body.columns:
            col_label_map["구분"] = "구분"
        if "구분1" in body.columns:
            col_label_map["구분1"] = "구분"
        if "구분2" in body.columns:
            col_label_map["구분2"] = "구분2"

        products_all = ["총계", "CHQ", "CD", "STS", "BTB", "PB"]
        for prod in products_all:
            if f"{prod}_판매중량" in body.columns:
                col_label_map[f"{prod}_판매중량"] = f"{prod}_판매중량"
            if f"{prod}_단가" in body.columns:
                col_label_map[f"{prod}_단가"] = f"{prod}_영업이익_단가"
            if f"{prod}_영업이익" in body.columns:
                col_label_map[f"{prod}_영업이익"] = f"{prod}_영업이익_금액"
            if f"{prod}_%" in body.columns:
                col_label_map[f"{prod}_%"] = f"{prod}_영업이익_%"

        body = body.rename(columns=col_label_map)


        # ── 포맷 함수 ──
        def fmt_num(v):
            try:
                v = float(str(v).replace(",", "").replace("%", ""))
            except Exception:
                return ""
            if v < 0:
                return f'<span style="color:#d62728;">-{abs(v):,.0f}</span>'
            return f"{v:,.0f}"


        def fmt_pct(v):
            s = str(v)
            if s.strip() == "":
                return ""
            try:
                v = float(s.replace(",", "").replace("%", ""))
            except Exception:
                return s
            if v < 0:
                return f'<span style="color:#d62728;">-{abs(v):,.1f}%</span>'
            return f"{v:,.1f}%"


        # ── 포맷 적용 ──
        num_cols = [c for c in body.columns if
                    ("판매중량" in c) or ("단가" in c) or ("금액" in c)]
        pct_cols = [c for c in body.columns if "_%" in c]

        for c in num_cols:
            body[c] = body[c].map(fmt_num)
        for c in pct_cols:
            body[c] = body[c].map(fmt_pct)

        # ── 스타일 상수 ──
        th_style = "border:1px solid #aaa; background:white; padding:8px 16px; text-align:center; font-weight:700; font-size:15px; white-space:nowrap;"
        td_style = "border:1px solid #aaa; padding:8px 16px; text-align:right; font-weight:400; font-size:15px;"
        td_left_style = "border:1px solid #aaa; padding:8px 16px; text-align:left; font-weight:400; font-size:15px; white-space:nowrap;"

        # ── 헤더 행 ──
        col_names = list(body.columns)
        th_cells = "".join(f'<th style="{th_style}">{c}</th>' for c in col_names)

        # ── 데이터 행 ──
        tr_html = ""
        for idx, row in body.iterrows():
            tds = ""
            for ci, c in enumerate(col_names):
                val = row[c]
                val = "" if str(val) == "nan" else str(val)
                style = td_left_style if ci == 0 else td_style

                # 💡 [1번 표 툴팁 주입]
                if ci == 0:
                    tds += f'<td style="{style}">{val}</td>'
                else:
                    row_label = str(row[col_names[0]]).strip()
                    tds += f'<td style="{style}" title="{row_label}, {c}">{val}</td>'
            tr_html += f'<tr>{tds}</tr>\n'

        html_table = f"""
<div style="overflow-x:auto;">
<table style="border-collapse:collapse; width:100%; font-family:'Noto Sans KR', sans-serif; font-size:15px;">
  <thead>
    <tr>
      {th_cells}
    </tr>
  </thead>
  <tbody>
    {tr_html}
  </tbody>
</table>
</div>
"""
        st.markdown(html_table, unsafe_allow_html=True)

    except Exception as e:
        pass

    st.divider()

    st.markdown("<h4>2) 실수요/유통 영업이익 </h4>", unsafe_allow_html=True)
    st.markdown("<h4>- B급 제외</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:right; font-size:13px; color:#666;'>[단위: 톤, 백만원]</div>",
                unsafe_allow_html=True)

    try:
        year = int(st.session_state['year'])
        month = int(st.session_state['month'])

        file_name = st.secrets["sheets"]["f_97"]
        df_src = pd.read_csv(file_name, dtype=str)

        # 선택연월 당월 데이터 사용
        disp = modules.build_f97(df_src, year, month)
        body = disp.copy()

        # =========================
        # 2) 가짜 헤더 hdr1, hdr2, hdr3 구성
        # =========================
        hdr1 = {col: "" for col in body.columns}
        hdr2 = {col: "" for col in body.columns}
        hdr3 = {col: "" for col in body.columns}

        if "구분2" in hdr1:
            hdr1["구분2"] = "구분"

        products = ["총계", "CHQ", "CD", "STS", "BTB", "PB"]
        metrics = ["판매중량", "단가", "영업이익", "%"]

        for prod in products:
            for m in metrics:
                col = f"{prod}_{m}"
                if col not in body.columns:
                    continue

                hdr1[col] = prod
                if m == "판매중량":
                    hdr2[col] = "판매"
                else:
                    hdr2[col] = "영업이익"

                if m == "판매중량":
                    hdr3[col] = "중량"
                elif m == "단가":
                    hdr3[col] = "단가"
                elif m == "영업이익":
                    hdr3[col] = "금액"
                elif m == "%":
                    hdr3[col] = "%"

        if "비중" in hdr1:
            hdr1["비중"] = ""
            hdr2["비중"] = "비중"
            hdr3["비중"] = ""

        hdr_df = pd.DataFrame([hdr1, hdr2, hdr3])
        body = pd.concat([hdr_df, body], ignore_index=True)


        def fmt_diff(v):
            try:
                v = float(str(v).replace(",", "").replace("%", ""))
            except Exception:
                return ""
            if v < 0:
                return f'<span style="color:#d62728;">({abs(v):,.0f})</span>'
            return f"{v:,.0f}"


        def fmt_pct(v):
            s = str(v)
            if s.strip() == "":
                return ""
            try:
                s = s.replace(",", "").replace("%", "")
                v = float(s)
            except Exception:
                return v
            return f"{v:,.1f}%"


        def fmt_pct_ver2(v):
            s = str(v)
            if s.strip() == "":
                return ""
            try:
                s = s.replace(",", "").replace("%", "")
                v = float(s)
            except Exception:
                return v
            return f"{v:,.0f}%"


        data_rows = body.index >= 3

        diff_cols = [
            c for c in body.columns
            if (
                    ("단가" in c)
                    or ("판매금액" in c)
                    or ("영업이익" in c and not c.endswith("_%"))
            )
        ]

        body.loc[data_rows, diff_cols] = (
            body.loc[data_rows, diff_cols].map(fmt_diff)
        )

        pct_cols = [
            c for c in body.columns
            if c.endswith("_%")
        ]

        body.loc[data_rows, pct_cols] = (
            body.loc[data_rows, pct_cols].map(fmt_pct)
        )

        ratio_cols = [c for c in body.columns if c == "비중"]

        body.loc[data_rows, ratio_cols] = (
            body.loc[data_rows, ratio_cols].map(fmt_pct_ver2)
        )

        # 💡 구분 정리 전 원본 헤더값 기반으로 백그라운드 툴팁 명칭을 추출하기 위해 빈 배열 정리 전 루프 설계
        tr_html = ""
        col_names = list(body.columns)

        # 병합 셀 정리를 위해 원본 값을 보존한 임시 헤더 객체 참조
        orig_hdr1, orig_hdr2, orig_hdr3 = hdr1.copy(), hdr2.copy(), hdr3.copy()

        for i in [4, 5, 6, 8, 9, 10, 12, 13, 14, 16, 17, 18, 20, 21, 22, 24, 25, 26]:
            body.iloc[0, i] = ""
        for i in [4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26]:
            body.iloc[1, i] = ""

        for r_idx, row in body.iterrows():
            tds = ""
            for c_idx, c in enumerate(col_names):
                val = row[c]
                val = "" if str(val) == "nan" else str(val)

                cell_styles = ["border:1px solid #aaa;", "padding:8px 16px;", "font-size:15px;",
                               "font-family:'Noto Sans KR', sans-serif;"]
                if r_idx < 3:
                    cell_styles.append("font-weight:700; text-align:center; background-color:white;")
                    if r_idx == 0:
                        cell_styles.append("border-top:3px solid gray !important;")
                else:
                    if c_idx in (0, 1):
                        cell_styles.append("text-align:left;")
                    else:
                        cell_styles.append("text-align:right;")
                    if c_idx == 1:
                        cell_styles.append("white-space:nowrap;")

                if r_idx in (2, 5, 8, 11):
                    cell_styles.append("border-bottom:3px solid gray !important;")
                if (c_idx + 1) in (2, 3, 7, 11, 15, 19, 23):
                    cell_styles.append("border-right:3px solid gray !important;")
                if r_idx == 0 and (c_idx + 1) in (1, 4, 5, 6, 8, 9, 10, 12, 13, 14, 16, 17, 18, 20, 21, 22, 24, 25, 26):
                    cell_styles.append("border-right:2px solid white !important;")
                if r_idx == 1 and (c_idx + 1) in (1, 5, 6, 9, 10, 13, 14, 17, 18, 21, 22, 25, 26):
                    cell_styles.append("border-right:2px solid white !important;")
                if r_idx in (2, 12) and c_idx == 0:
                    cell_styles.append("border-right:2px solid white !important;")
                if r_idx == 12 and c_idx == 1:
                    cell_styles.append("border-right:2px solid white !important;")

                style_str = " ".join(cell_styles)

                # 💡 [2번 표 툴팁 주입]
                if r_idx >= 3 and c_idx >= 2:
                    lbl1 = str(row.iloc[0]).strip() if str(row.iloc[0]).strip() not in ["", "nan"] else ""
                    lbl2 = str(row.iloc[1]).strip() if str(row.iloc[1]).strip() not in ["", "nan"] else ""
                    row_label = f"{lbl1} {lbl2}".strip()

                    h1 = str(orig_hdr1[c]).strip()
                    h2 = str(orig_hdr2[c]).strip()
                    h3 = str(orig_hdr3[c]).strip()
                    col_label = f"{h1} {h2} {h3}".strip().replace("  ", " ")
                    tds += f'<td style="{style_str}" title="{row_label}, {col_label}">{val}</td>'
                else:
                    tds += f'<td style="{style_str}">{val}</td>'
            tr_html += f'<tr>{tds}</tr>\n'

        html_table = f"""
<div style="overflow-x:auto;">
<table style="border-collapse:collapse; width:100%; font-family:'Noto Sans KR', sans-serif; font-size:15px;">
  <tbody>
    {tr_html}
  </tbody>
</table>
</div>
"""
        st.markdown(html_table, unsafe_allow_html=True)

    except Exception as e:
        pass

    st.divider()

    st.markdown("<h4>3) 메이커별 영업이익 </h4>", unsafe_allow_html=True)
    st.markdown("<h4>- B급 및 매입매출 제외</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:right; font-size:13px; color:#666;'>[단위: 톤, 백만원]</div>",
                unsafe_allow_html=True)

    try:
        year = int(st.session_state['year'])
        month = int(st.session_state['month'])

        file_name = st.secrets["sheets"]["f_98"]
        df_src = pd.read_csv(file_name, dtype=str)

        disp = modules.build_f98(df_src, year, month)
        body = disp.copy()

        hdr1 = {col: "" for col in body.columns}
        hdr2 = {col: "" for col in body.columns}
        hdr3 = {col: "" for col in body.columns}

        if "구분2" in hdr1:
            hdr1["구분2"] = "구분"

        products = ["총계", "CHQ", "CD", "STS", "BTB", "PB"]
        metrics = ["판매중량", "단가", "영업이익", "%"]

        for prod in products:
            for m in metrics:
                col = f"{prod}_{m}"
                if col not in body.columns:
                    continue

                hdr1[col] = prod
                if m == "판매중량":
                    hdr2[col] = "판매"
                else:
                    hdr2[col] = "영업이익"

                if m == "판매중량":
                    hdr3[col] = "중량"
                elif m == "단가":
                    hdr3[col] = "단가"
                elif m == "영업이익":
                    hdr3[col] = "금액"
                elif m == "%":
                    hdr3[col] = "%"

        if "비중" in hdr1:
            hdr1["비중"] = ""
            hdr2["비중"] = "비중"
            hdr3["비중"] = ""

        hdr_df = pd.DataFrame([hdr1, hdr2, hdr3])
        body = pd.concat([hdr_df, body], ignore_index=True)

        data_rows = body.index >= 3

        # 1) 단가/금액/영업이익(금액) 컬럼
        diff_cols = [
            c for c in body.columns
            if (
                    ("단가" in c)
                    or ("판매금액" in c)
                    or ("영업이익" in c and not c.endswith("_%"))
            )
        ]

        body.loc[data_rows, diff_cols] = (
            body.loc[data_rows, diff_cols].map(fmt_diff)
        )

        # 2-1) 영업이익 % (소수 1자리 + %)
        pct_cols = [
            c for c in body.columns
            if c.endswith("_%")
        ]

        body.loc[data_rows, pct_cols] = (
            body.loc[data_rows, pct_cols].map(fmt_pct)
        )

        # 2-2) 비중만 따로
        ratio_cols = [c for c in body.columns if c == "비중"]

        body.loc[data_rows, ratio_cols] = (
            body.loc[data_rows, ratio_cols].map(fmt_pct_ver2)
        )

        orig_hdr1_f98, orig_hdr2_f98, orig_hdr3_f98 = hdr1.copy(), hdr2.copy(), hdr3.copy()

        for i in [4, 5, 6, 8, 9, 10, 12, 13, 14, 16, 17, 18, 20, 21, 22, 24, 25, 26]:
            body.iloc[0, i] = ""
        for i in [4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26]:
            body.iloc[1, i] = ""

        # 💡 [3번 표 툴팁 주입]
        tr_html = ""
        col_names = list(body.columns)
        for r_idx, row in body.iterrows():
            tds = ""
            for c_idx, c in enumerate(col_names):
                val = row[c]
                val = "" if str(val) == "nan" else str(val)

                cell_styles = ["border:1px solid #aaa;", "padding:8px 16px;", "font-size:15px;",
                               "font-family:'Noto Sans KR', sans-serif;"]
                if r_idx < 3:
                    cell_styles.append("font-weight:700; text-align:center; background-color:white;")
                else:
                    if c_idx in (0, 1):
                        cell_styles.append("text-align:left;")
                    else:
                        cell_styles.append("text-align:right;")

                if r_idx in (2, 17, 24):
                    cell_styles.append("border-bottom:3px solid #aaa !important;")

                style_str = " ".join(cell_styles)

                if r_idx >= 3 and c_idx >= 2:
                    lbl1 = str(row.iloc[0]).strip() if str(row.iloc[0]).strip() not in ["", "nan"] else ""
                    lbl2 = str(row.iloc[1]).strip() if str(row.iloc[1]).strip() not in ["", "nan"] else ""
                    row_label = f"{lbl1} {lbl2}".strip()

                    h1 = str(orig_hdr1_f98[c]).strip()
                    h2 = str(orig_hdr2_f98[c]).strip()
                    h3 = str(orig_hdr3[c]).strip()
                    col_label = f"{h1} {h2} {h3}".strip().replace("  ", " ")
                    tds += f'<td style="{style_str}" title="{row_label}, {col_label}">{val}</td>'
                else:
                    tds += f'<td style="{style_str}">{val}</td>'
            tr_html += f'<tr>{tds}</tr>\n'

        html_table = f"""
<div style="overflow-x:auto;">
<table style="border-collapse:collapse; width:100%; font-family:'Noto Sans KR', sans-serif; font-size:15px;">
  <tbody>
    {tr_html}
  </tbody>
</table>
</div>
"""
        st.markdown(html_table, unsafe_allow_html=True)

    except Exception as e:
        pass

    st.divider()

    st.markdown("<h4>4) 부서/메이커별 영업이익 </h4>", unsafe_allow_html=True)
    st.markdown("<h6>- B급 및 매입매출 제외</h6>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:right; font-size:13px; color:#666;'>[단위: 톤, 백만원]</div>",
                unsafe_allow_html=True)

    try:
        year = int(st.session_state['year'])
        month = int(st.session_state['month'])

        file_name = st.secrets["sheets"]["f_99"]
        df_src = pd.read_csv(file_name, dtype=str)

        disp = modules.build_f99(df_src, year, month)
        body = disp.copy()

        # ── 컬럼명 한글 표시명 매핑 ──
        col_label_map = {
            "구분1": "구분", "비중": "비중",
            "총계_판매중량": "총계_판매중량", "총계_단가": "총계_영업이익_단가", "총계_영업이익": "총계_영업이익_금액", "총계_%": "총계_영업이익_%",
            "선재영업팀_판매중량": "선재영업팀_판매중량", "선재영업팀_단가": "선재영업팀_영업이익_단가", "선재영업팀_영업이익": "선재영업팀_영업이익_금액",
            "선재영업팀_%": "선재영업팀_영업이익_%",
            "봉강영업팀_판매중량": "봉강영업팀_판매중량", "봉강영업팀_단가": "봉강영업팀_영업이익_단가", "봉강영업팀_영업이익": "봉강영업팀_영업이익_금액",
            "봉강영업팀_%": "봉강영업팀_영업이익_%",
            "부산영업소_판매중량": "부산영업소_판매중량", "부산영업소_단가": "부산영업소_영업이익_단가", "부산영업소_영업이익": "부산영업소_영업이익_금액",
            "부산영업소_%": "부산영업소_영업이익_%",
            "대구영업소_판매중량": "대구영업소_판매중량", "대구영업소_단가": "대구영업소_영업이익_단가", "대구영업소_영업이익": "대구영업소_영업이익_금액",
            "대구영업소_%": "대구영업소_영업이익_%",
            "글로벌영업팀_판매중량": "글로벌영업팀_판매중량", "글로벌영업팀_단가": "글로벌영업팀_영업이익_단가", "글로벌영업팀_영업이익": "글로벌영업팀_영업이익_금액",
            "글로벌영업팀_%": "글로벌영업팀_영업이익_%",
        }
        body = body.rename(columns=col_label_map)

        num_cols = [c for c in body.columns if ("판매중량" in c) or ("단가" in c) or ("금액" in c)]
        pct_cols = [c for c in body.columns if c.endswith("_%") or c == "비중"]

        for c in num_cols:
            body[c] = body[c].map(fmt_num)
        for c in pct_cols:
            body[c] = body[c].map(fmt_pct)

        th_style = "border:1px solid #aaa; background:white; padding:8px 16px; text-align:center; font-weight:700; font-size:15px; white-space:nowrap;"
        td_style = "border:1px solid #aaa; padding:8px 16px; text-align:right; font-weight:400; font-size:15px;"
        td_left_style = "border:1px solid #aaa; padding:8px 16px; text-align:left; font-weight:400; font-size:15px; white-space:nowrap;"

        col_names = list(body.columns)
        th_cells = "".join(f'<th style="{th_style}">{c}</th>' for c in col_names)

        # 💡 [4번 표 툴팁 주입]
        tr_html = ""
        for idx, row in body.iterrows():
            tds = ""
            for ci, c in enumerate(col_names):
                val = row[c]
                val = "" if str(val) == "nan" else str(val)
                style = td_left_style if ci == 0 else td_style

                if ci == 0:
                    tds += f'<td style="{style}">{val}</td>'
                else:
                    row_label = str(row[col_names[0]]).strip()
                    tds += f'<td style="{style}" title="{row_label}, {c}">{val}</td>'
            tr_html += f'<tr>{tds}</tr>\n'

        html_table = f"""
<div style="overflow-x:auto;">
<table style="border-collapse:collapse; width:100%; font-family:'Noto Sans KR', sans-serif; font-size:15px;">
  <thead>
    <tr>
      {th_cells}
    </tr>
  </thead>
  <tbody>
    {tr_html}
  </tbody>
</table>
</div>
"""
        st.markdown(html_table, unsafe_allow_html=True)

    except Exception as e:
        pass

    st.divider()

    st.markdown("<h4>5) 부서/사업장/메이커별 영업이익 </h4>", unsafe_allow_html=True)
    st.markdown("<h6>- B급 및 매입매출 제외</h6>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:right; font-size:13px; color:#666;'>[단위: 톤, 백만원]</div>",
                unsafe_allow_html=True)

    try:
        year = int(st.session_state['year'])
        month = int(st.session_state['month'])

        file_name = st.secrets["sheets"]["f_100"]
        df_src = pd.read_csv(file_name, dtype=str)

        disp = modules.build_f100(df_src, year, month)
        body = disp.copy()

        body["구분"] = body.apply(
            lambda r: str(r["구분1"]) if str(r["구분1"]).strip() not in ["", "nan"]
            else str(r["구분2"]) if str(r["구분2"]).strip() not in ["", "nan"]
            else "",
            axis=1
        )
        body = body.drop(columns=["구분1", "구분2"])
        cols = ["구분"] + [c for c in body.columns if c != "구분"]
        body = body[cols]

        col_label_map = {
            "비중": "비중", "총계_판매중량": "총계_판매중량", "총계_단가": "총계_영업이익_단가", "총계_영업이익": "총계_영업이익_금액", "총계_%": "총계_영업이익_%",
            "선재영업팀_판매중량": "선재영업팀_판매중량", "선재영업팀_단가": "선재영업팀_영업이익_단가", "선재영업팀_영업이익": "선재영업팀_영업이익_금액",
            "선재영업팀_%": "선재영업팀_영업이익_%",
            "봉강영업팀_판매중량": "봉강영업팀_판매중량", "봉강영업팀_단가": "봉강영업팀_영업이익_단가", "봉강영업팀_영업이익": "봉강영업팀_영업이익_금액",
            "봉강영업팀_%": "봉강영업팀_영업이익_%",
            "부산영업소_판매중량": "부산영업소_판매중량", "부산영업소_단가": "부산영업소_영업이익_단가", "부산영업소_영업이익": "부산영업소_영업이익_금액",
            "부산영업소_%": "부산영업소_영업이익_%",
            "대구영업소_판매중량": "대구영업소_판매중량", "대구영업소_단가": "대구영업소_영업이익_단가", "대구영업소_영업이익": "대구영업소_영업이익_금액",
            "대구영업소_%": "대구영업소_영업이익_%",
            "글로벌영업팀_판매중량": "글로벌영업팀_판매중량", "글로벌영업팀_단가": "글로벌영업팀_영업이익_단가", "글로벌영업팀_영업이익": "글로벌영업팀_영업이익_금액",
            "글로벌영업팀_%": "글로벌영업팀_영업이익_%",
        }
        body = body.rename(columns=col_label_map)

        num_cols = [c for c in body.columns if ("판매중량" in c) or ("단가" in c) or ("금액" in c)]
        pct_cols = [c for c in body.columns if c.endswith("_%") or c == "비중"]

        for c in num_cols:
            body[c] = body[c].map(fmt_num)
        for c in pct_cols:
            body[c] = body[c].map(fmt_pct)

        th_style = "border:1px solid #aaa; background:white; padding:8px 16px; text-align:center; font-weight:700; font-size:15px; white-space:nowrap;"
        td_style = "border:1px solid #aaa; padding:8px 16px; text-align:right; font-weight:400; font-size:15px;"
        td_left_style = "border:1px solid #aaa; padding:8px 16px; text-align:left; font-weight:400; font-size:15px; white-space:nowrap;"

        col_names = list(body.columns)
        th_cells = "".join(f'<th style="{th_style}">{c}</th>' for c in col_names)

        # 💡 [5번 표 툴팁 주입]
        tr_html = ""
        for idx, row in body.iterrows():
            tds = ""
            for ci, c in enumerate(col_names):
                val = row[c]
                val = "" if str(val) == "nan" else str(val)
                style = td_left_style if ci == 0 else td_style

                if ci == 0:
                    tds += f'<td style="{style}">{val}</td>'
                else:
                    row_label = str(row[col_names[0]]).strip()
                    tds += f'<td style="{style}" title="{row_label}, {c}">{val}</td>'
            tr_html += f'<tr>{tds}</tr>\n'

        html_table = f"""
<div style="overflow-x:auto;">
<table style="border-collapse:collapse; width:100%; font-family:'Noto Sans KR', sans-serif; font-size:15px;">
  <thead>
    <tr>
      {th_cells}
    </tr>
  </thead>
  <tbody>
    {tr_html}
  </tbody>
</table>
</div>
"""
        st.markdown(html_table, unsafe_allow_html=True)

    except Exception as e:
        pass

    st.divider()

    st.markdown("<h4>6) 부서별/인당 영업이익 </h4>", unsafe_allow_html=True)
    st.markdown("<h6>- B급 제외</h6>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:right; font-size:13px; color:#666;'>[단위: 톤, 백만원]</div>",
                unsafe_allow_html=True)

    try:
        year = int(st.session_state["year"])
        month = int(st.session_state["month"])

        file_name = st.secrets["sheets"]["f_101"]
        df_src = pd.read_csv(file_name, dtype=str)

        disp = modules.build_f101(df_src, year, month)
        body = disp.copy()

        if month == 1:
            prev_year, prev_month = year - 1, 12
        else:
            prev_year, prev_month = year, month - 1

        body["구분"] = body.apply(
            lambda r: str(r["구분1"]) if str(r["구분1"]).strip() not in ["", "nan"]
            else str(r["구분2"]) if str(r["구분2"]).strip() not in ["", "nan"]
            else "",
            axis=1
        )
        body = body.drop(columns=["구분1", "구분2"])
        cols = ["구분"] + [c for c in body.columns if c != "구분"]
        body = body[cols]

        col_label_map = {}
        for col in body.columns:
            if col == "구분":
                continue
            for prefix, period in [
                ("누적_", f"{year}년 누적평균"),
                ("전월_", f"{prev_year}년 {prev_month}월"),
                ("당월_", f"{year}년 {month}월"),
            ]:
                if col.startswith(prefix):
                    metric = col[len(prefix):]
                    metric_label = {
                        "판매중량": "판매중량", "판매단가": "영업이익_단가", "영업이익": "영업이익_금액", "영업이익율": "영업이익_%",
                        "인원": "인원_명", "인당중량": "인당평균_중량", "인당영업이익": "인당평균_영업이익",
                    }.get(metric, metric)
                    col_label_map[col] = f"{period}_{metric_label}"
                    break

        body = body.rename(columns=col_label_map)

        num_cols = [c for c in body.columns if any(k in c for k in ["판매중량", "단가", "금액", "명", "인당평균"]) and "%" not in c]
        pct_cols = [c for c in body.columns if c.endswith("_%")]

        for c in num_cols:
            body[c] = body[c].map(fmt_num)
        for c in pct_cols:
            body[c] = body[c].map(fmt_pct)

        th_style = "border:1px solid #aaa; background:white; padding:8px 16px; text-align:center; font-weight:700; font-size:15px; white-space:nowrap;"
        td_style = "border:1px solid #aaa; padding:8px 16px; text-align:right; font-weight:400; font-size:15px;"
        td_left_style = "border:1px solid #aaa; padding:8px 16px; text-align:left; font-weight:400; font-size:15px; white-space:nowrap;"

        col_names = list(body.columns)
        th_cells = "".join(f'<th style="{th_style}">{c}</th>' for c in col_names)

        # 💡 [6번 표 툴팁 주입]
        tr_html = ""
        for idx, row in body.iterrows():
            tds = ""
            for ci, c in enumerate(col_names):
                val = row[c]
                val = "" if str(val) == "nan" else str(val)
                style = td_left_style if ci == 0 else td_style

                if ci == 0:
                    tds += f'<td style="{style}">{val}</td>'
                else:
                    row_label = str(row[col_names[0]]).strip()
                    tds += f'<td style="{style}" title="{row_label}, {c}">{val}</td>'
            tr_html += f'<tr>{tds}</tr>\n'

        html_table = f"""
<div style="overflow-x:auto;">
<table style="border-collapse:collapse; width:100%; font-family:'Noto Sans KR', sans-serif; font-size:15px;">
  <thead>
    <tr>
      {th_cells}
    </tr>
  </thead>
  <tbody>
    {tr_html}
  </tbody>
</table>
</div>
"""
        st.markdown(html_table, unsafe_allow_html=True)

    except Exception as e:
        pass

    st.divider()

# Footer
st.markdown("""
<style>.footer { bottom: 0; left: 0; right: 0; padding: 8px; text-align: center; font-size: 13px; color: #666666;}</style>
<div class="footer">ⓒ 2025 SeAH Special Steel Corp. All rights reserved.</div>
""", unsafe_allow_html=True)
