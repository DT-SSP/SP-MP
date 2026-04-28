import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
import plotly.graph_objects as go
import modules

warnings.filterwarnings('ignore')
st.set_page_config(layout="wide", initial_sidebar_state="expanded")

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
        textposition='inside', insidetextanchor='middle', insidetextfont=dict(color='white')
    ))
    fig.add_trace(go.Bar(
        x=df_plot.index, y=df_plot['판매량'], name='판매량', marker_color='#e54e2b',
        width=0.4, text=df_plot['판매량'], texttemplate='%{text:,.0f}',
        textposition='inside', insidetextanchor='middle', insidetextfont=dict(color='white')
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
        yaxis='y2', textposition="top center", textfont=dict(size=15, color='black')
    ))

    fig.update_layout(
        height=500, font=dict(size=15), bargap=0.2, barmode='group', plot_bgcolor='white',
        yaxis=dict(showticklabels=False, showgrid=False, zeroline=False, range=yaxis1_range),
        yaxis2=dict(showticklabels=False, overlaying='y', side='right', showgrid=False, zeroline=False,
                    range=yaxis2_range),
        xaxis=dict(showline=True, linewidth=1, linecolor='lightgrey', tickfont=dict(size=18)),
        legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5, font=dict(size=18)),
        margin=dict(t=80, b=20, l=20, r=20)
    )
    _, chart_col, _ = st.columns([0.2, 0.6, 0.2])
    with chart_col:
        st.plotly_chart(fig, use_container_width=True, key=key)


def display_line_chart(df, traces, key, offset_map=None):
    if offset_map is None:
        offset_map = {"합금강":10}  # 예: {"합금강": 15}

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
    y_range = [y_min - pad, y_max + pad]

    for i, trace in enumerate(traces, 1):
        axis_name = 'y' if i == 1 else f'y{i}'
        series = df_plot[trace['name']]
        offset = offset_map.get(trace['name'][1], 0) 

        fig.add_trace(go.Scatter(
            x=df_plot.index,
            y=series + offset,        # 화면에서는 offset 적용
            name=trace['name'][1],
            mode='lines+markers+text',
            marker=dict(size=8, color=trace['color']),
            line=dict(width=3, color=trace['color']),
            yaxis=axis_name,
            text=series,              # 텍스트는 실제 값
            textposition=trace.get('textposition', 'top center'),
            textfont=dict(size=15, color='black'),
            texttemplate='%{text:,.1f}',
            hovertemplate=f"{trace['name'][1]}: %{{text}}<extra></extra>"
        ))

        axis_config = dict(
            showticklabels=False,
            showgrid=False,
            zeroline=False,
            range=y_range,
        )
        if i > 1:
            axis_config.update(overlaying='y', side='right')
        layout_options[f'yaxis{'' if i == 1 else i}'] = axis_config

    fig.update_layout(
        height=500, font=dict(size=15), plot_bgcolor='white',
        xaxis=dict(showline=True, linewidth=1, linecolor='lightgrey',
                   tickfont=dict(size=18)),
        legend=dict(orientation="h", yanchor="bottom", y=-0.3,
                    xanchor="center", x=0.5, font=dict(size=18)),
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

# 본사 실적요약

    st.markdown("<h4>2) 본사 실적요약</h4>", unsafe_allow_html=True)
    display_summary_chart(all_dfs['본사'], key="hq_summary", yaxis1_range=[0, 150000], yaxis2_range=[-10000, 8000])
    st.divider()

# 중국법인 실적요약

    st.markdown("<h4>3) 중국법인 실적요약</h4>", unsafe_allow_html=True)
    display_summary_chart(all_dfs['중국'], key="cn_summary", yaxis1_range=[0, 40000], yaxis2_range=[-1000, 1500])
    st.divider()

# 태국법인 실적요약

    st.markdown("<h4>4) 태국법인 실적요약</h4>", unsafe_allow_html=True)
    display_summary_chart(all_dfs['태국'], key="th_summary", yaxis1_range=[0, 10000], yaxis2_range=[-300, 400])
    st.divider()

# 환율 추이
with t2:
    st.markdown("<h4>1) 포스코 대 JFE 가격 차이</h4>", unsafe_allow_html=True)
    df_raw = modules.create_df(this_year, current_month, load_data(st.secrets['sheets']['f_93']), mean="False",
                               prev_year=1, prev_month=6)
    df_plot = df_raw.loc[('가격차이', ['탄소강', '합금강']), df_raw.columns]

    traces = [
        {'name': ('가격차이', '탄소강'), 'color': '#3b4951', 'range': [-100, 400]},
        {'name': ('가격차이', '합금강'), 'color': '#e54e2b', 'range': [-100, 400], 'textposition': 'bottom center'}
    ]
    display_line_chart(df_plot, traces, key="price_diff_chart")
    st.divider()

with t3:
    st.markdown("<h4>1) 산업군별 영업이익</h4>", unsafe_allow_html=True)
    df = modules.create_df(this_year, current_month, load_data(st.secrets['sheets']['f_94']), mean="False", prev_year=1)
    df_plot = df.loc[('환율추이', ['USD', 'CNH', 'THB']), df.columns]

    traces = [
        {'name': ('환율추이', 'USD'), 'color': '#3b4951', 'range': [1300, 1500]},
        {'name': ('환율추이', 'CNH'), 'color': '#e54e2b', 'range': [160, 230], 'textposition': 'bottom center'},
        {'name': ('환율추이', 'THB'), 'color': '#0070c0', 'range': [30, 100]}
    ]
    display_line_chart(df_plot, traces, key="exchange_rate_chart")
    st.divider()


with t4:

    st.markdown("<h4>1) 손익계산서 수정정상원가 </h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 백만원, 톤]</div>", unsafe_allow_html=True)

    try:
        year = int(st.session_state["year"])
        month = int(st.session_state["month"])

        file_name = st.secrets["sheets"]["f_95"]
        df_src = pd.read_csv(file_name, dtype=str)


        body = modules.build_f95(df_src, year, month)


        def fmt_pct(v):
            if v == "" or pd.isna(v):
                return ""
            try:
                v = float(v)
            except Exception:
                return v
            return f"{v:,.1f}%"
        
        def fmt_t(v):
            if v == "" or pd.isna(v):
                return ""
            try:
                v = float(v)
            except Exception:
                return v
            return f"{v:,.0f}t"


        value_cols = [c for c in body.columns if c not in ["구분1", "구분2", "구분3"]]

        for idx in body.index:
            is_pct_row = body.at[idx, "구분3"] in ("DM%", "(이익율)")
            for col in value_cols:
                v = body.at[idx, col]
                if is_pct_row:
                    body.at[idx, col] = fmt_pct(v)
                else:
                    pass

        for idx in body.index:
            is_pct_row = body.at[idx, "구분2"] == "수량"
            for col in value_cols:
                v = body.at[idx, col]
                if is_pct_row:
                    body.at[idx, col] = fmt_t(v)
                else:
                    pass

        # -----------------------
        # 4. 테이블 스타일
        # -----------------------
        styles = [

            {
                "selector": "th.col_heading",
                "props": [("text-align", "center"),('border-top','3px solid gray !important')]
            },

            {
                "selector": "tbody td:nth-child(1), "
                            "tbody td:nth-child(2), "
                            "tbody td:nth-child(3)",
                "props": [("text-align", "left")]
            },

            {
                "selector": "tbody td:nth-child(n+4)",
                "props": [("text-align", "right")]
            },

            {
                "selector": "tbody td:nth-child(2)",
                "props": [("white-space", "nowrap")]
            },
        ]


        
        spacer_rules18 = [
            {
                'selector': f'td:nth-child(3)',
                'props': [('border-right','3px solid gray !important')]
               
            }
            # for r in (1,3,4,5,7,8,9,11,12,13,15,16,17,19,20,21,23,24,25)
        ]

        styles += spacer_rules18
        

        spacer_rules1 = [
            {
                'selector': f'tbody tr:nth-child({r})',
                'props': [('border-top','3px solid gray !important')]
               
            }
            for r in (1,5,15,17,22,23,29,31)

        ]

        styles += spacer_rules1


        spacer_rules17 = [
            {
                'selector': f'tbody tr:nth-child(4))',
                'props': [('border-right','3px solid gray !important')]
               
            }

        ]

        styles += spacer_rules17



        


        
        cols = list(body.columns)


        cols[0] = " "          
        cols[1] = "구분"     
        cols[2] = ""

        body.columns = cols


        display_styled_df(body, styles=styles, already_flat=True)

    except Exception as e:
        st.error(f"손익계산서 수정정상원가 표 생성 오류: {e}")




    st.divider()





with t5:
    st.markdown("<h4>1) 산업군별 영업이익 </h4>", unsafe_allow_html=True)
    st.markdown("<h6>- B급 제외</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 톤, 백만원]</div>", unsafe_allow_html=True)



    try:
        year = int(st.session_state['year'])
        month = int(st.session_state['month'])

        file_name = st.secrets["sheets"]["f_96"]
        df_src = pd.read_csv(file_name, dtype=str)

        # 선택연월 당월 데이터 사용
        disp = modules.build_f96(df_src, year, month)
        body = disp.copy()

        hdr1 = {col: "" for col in body.columns}
        hdr2 = {col: "" for col in body.columns}
        hdr3 = {col: "" for col in body.columns}

        # (1) 구분 컬럼 텍스트
        if "구분2" in hdr1:
            hdr1["구분2"] = "구분"

        products = ["총계", "CHQ", "CD", "STS", "BTB", "PB"]
        metrics  = ["판매중량", "단가", "판매금액", "영업이익", "%"]

        for prod in products:
            for m in metrics:
                col = f"{prod}_{m}"
                if col not in body.columns:
                    continue

                # 1행: 제품명
                hdr1[col] = prod

                # 2행: 판매 vs 영업이익
                if m in ["판매중량", "판매금액"]:
                    hdr2[col] = "판매"
                else:
                    hdr2[col] = "영업이익"

                # 3행: 세부 지표명
                if m == "판매중량":
                    hdr3[col] = "중량"
                elif m == "단가":
                    hdr3[col] = "단가"
                elif m in ["판매금액", "영업이익"]:
                    hdr3[col] = "금액"
                elif m == "%":
                    hdr3[col] = "%"

        # body 맨 위에 hdr1, hdr2, hdr3 추가
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

        # 데이터 행: 4행부터
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
            body.loc[data_rows, diff_cols].applymap(fmt_diff)
        )


        pct_cols = [
            c for c in body.columns
            if c.endswith("_%") 
        ]

        body.loc[data_rows, pct_cols] = (
            body.loc[data_rows, pct_cols].applymap(fmt_pct)
        )

        styles = [
            {"selector": "thead", "props": [("display", "none")]},

            {
                "selector": "tbody tr:nth-child(1) td",
                "props": [("font-weight", "700"), ("text-align", "center"),('border-top','3px solid gray !important')],
            },

            {
                "selector": "tbody tr:nth-child(2) td",
                "props": [("font-weight", "700"), ("text-align", "center")],
            },

            {
                "selector": "tbody tr:nth-child(3) td",
                "props": [("font-weight", "700"), ("text-align", "center")],
            },

            {
                "selector": "tbody tr:nth-child(n+4) td:nth-child(1), "
                            "tbody tr:nth-child(n+4) td:nth-child(2)",
                "props": [("text-align", "left")],
            },

            {
                "selector": "tbody tr:nth-child(n+4) td:nth-child(n+3)",
                "props": [("text-align", "right")],
            },


            {
                "selector": "tbody tr td:nth-child(2)",
                "props": [("white-space", "nowrap")],
            },
        ]

#########################
        spacer_rules18 = [
            {
                'selector': f'tbody tr:nth-child(1) td:nth-child({r})',
                'props': [('border-right','2px solid white !important')]
               
            }
            for r in (1,3,4,5,7,8,9,11,12,13,15,16,17,19,20,21,23,24,25)
        ]

        styles += spacer_rules18

        
        spacer_rules1 = [
            {
                'selector': f'tbody tr:nth-child(3)',
                'props': [('border-bottom','3px solid gray !important')]
               
            }

        ]

        styles += spacer_rules1

        spacer_rules1 = [
            {
                'selector': f'tbody tr:nth-child(11)',
                'props': [('border-bottom','3px solid gray !important')]
               
            }

        ]

        styles += spacer_rules1

        spacer_rules1 = [
            {
                'selector': f'tbody tr:nth-child(19)',
                'props': [('border-bottom','3px solid gray !important')]
               
            }

        ]

        styles += spacer_rules1




        spacer_rules2 = [
            {
                'selector': f'td:nth-child(2)',
                'props': [('border-right','3px solid gray !important')]
               
            }

        ]

        styles += spacer_rules2

        spacer_rules3 = [
            {
                'selector': f'td:nth-child({r})',
                'props': [('border-right','3px solid gray !important')]
               
            }
            for r in (6,10,14,18,22)
        ]

        styles += spacer_rules3

        
        spacer_rules18 = [
            {
                'selector': f'tbody tr:nth-child(2) td:nth-child({r})',
                'props': [('border-right','2px solid white !important')]
               
            }
            for r in (1,4,5,8,9,12,13,16,17,20,21,24,25)
        ]

        styles += spacer_rules18

        spacer_rules18 = [
            {
                'selector': f'tbody tr:nth-child(3) td:nth-child(1)',
                'props': [('border-right','2px solid white !important')]
               
            }

        ]

        styles += spacer_rules18










        #구분 정리
        for i in [3,4,5,7,8,9,11,12,13,15,16,17,19,20,21,23,24,25]:
            body.iloc[0, i] = ""

        for i in [3,5,7,9,11,13,15,17,19,21,23,25]:
            body.iloc[1, i] = ""
        

        display_styled_df(body, styles=styles, already_flat=True)

    except Exception as e:
        st.error(f"산업군별 영업이익 표 생성 오류: {e}")


    st.divider()

    st.markdown("<h4>2) 실수요/유통 영업이익 </h4>", unsafe_allow_html=True)
    st.markdown("<h6>- B급 제외</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 톤, 백만원]</div>", unsafe_allow_html=True)



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

        # (1) 구분 컬럼 텍스트
        if "구분2" in hdr1:
            hdr1["구분2"] = "구분"

        products = ["총계", "CHQ", "CD", "STS", "BTB", "PB"]
        metrics  = ["판매중량", "단가", "영업이익", "%"]   # 여기엔 비중 X

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



        # body 맨 위에 hdr1, hdr2, hdr3 추가
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
                return v  # 숫자 아니면 그대로
            return f"{v:,.0f}%"   

        # 데이터 행: 4행부터
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
            body.loc[data_rows, diff_cols].applymap(fmt_diff)
        )


        # 2-1) 영업이익 % (소수 1자리 + %)
        pct_cols = [
            c for c in body.columns
            if c.endswith("_%")
        ]

        body.loc[data_rows, pct_cols] = (
            body.loc[data_rows, pct_cols].applymap(fmt_pct)
        )

        # 2-2) 비중만 따로
        ratio_cols = [c for c in body.columns if c == "비중"]

        body.loc[data_rows, ratio_cols] = (
            body.loc[data_rows, ratio_cols].applymap(fmt_pct_ver2)
        )



        styles = [
            {"selector": "thead", "props": [("display", "none")]},

            {
                "selector": "tbody tr:nth-child(1) td",
                "props": [("font-weight", "700"), ("text-align", "center"),('border-top','3px solid gray !important')],
            },

            {
                "selector": "tbody tr:nth-child(2) td",
                "props": [("font-weight", "700"), ("text-align", "center")],
            },

            {
                "selector": "tbody tr:nth-child(3) td",
                "props": [("font-weight", "700"), ("text-align", "center")],
            },

            {
                "selector": "tbody tr:nth-child(n+4) td:nth-child(1), "
                            "tbody tr:nth-child(n+4) td:nth-child(2)",
                "props": [("text-align", "left")],
            },

            {
                "selector": "tbody tr:nth-child(n+4) td:nth-child(n+3)",
                "props": [("text-align", "right")],
            },


            {
                "selector": "tbody tr td:nth-child(2)",
                "props": [("white-space", "nowrap")],
            },
        ]

        spacer_rules18 = [
            {
                'selector': f'tbody tr:nth-child(1) td:nth-child({r})',
                'props': [('border-right','2px solid white !important')]
               
            }
            # for r in (1,3,4,5,7,8,9,11,12,13,15,16,17,19,20,21,23,24,25)
            for r in (1,4,5,6,8,9,10,12,13,14,16,17,18,20,21,22,24,25,26)
        ]

        styles += spacer_rules18

        
        spacer_rules1 = [
            {
                'selector': f'tbody tr:nth-child(3)',
                'props': [('border-bottom','3px solid gray !important')]
               
            }

        ]

        styles += spacer_rules1

        spacer_rules1 = [
            {
                'selector': f'tbody tr:nth-child(6)',
                'props': [('border-bottom','3px solid gray !important')]
               
            }

        ]

        styles += spacer_rules1

        spacer_rules1 = [
            {
                'selector': f'tbody tr:nth-child(9)',
                'props': [('border-bottom','3px solid gray !important')]
               
            }

        ]

        styles += spacer_rules1

        spacer_rules1 = [
            {
                'selector': f'tbody tr:nth-child(12)',
                'props': [('border-bottom','3px solid gray !important')]
               
            }

        ]

        styles += spacer_rules1




        # spacer_rules2 = [
        #     {
        #         'selector': f'td:nth-child(2)',
        #         'props': [('border-right','3px solid gray !important')]
               
        #     }

        # ]

        # styles += spacer_rules2

        spacer_rules3 = [
            {
                'selector': f'td:nth-child({r})',
                'props': [('border-right','3px solid gray !important')]
               
            }
            # for r in (6,10,14,18,22)
            for r in (2,3,7,11,15,19,23)
        ]

        styles += spacer_rules3

        
        spacer_rules18 = [
            {
                'selector': f'tbody tr:nth-child(2) td:nth-child({r})',
                'props': [('border-right','2px solid white !important')]
               
            }
            # for r in (4,5,8,9,12,13,16,17,20,21,24,25)
            for r in (1,5,6,9,10,13,14,17,18,21,22,25,26)
        ]

        styles += spacer_rules18

        
        spacer_rules18 = [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child(1)',
                'props': [('border-right','2px solid white !important')]
               
            }
            for r in (3,13)

        ]

        styles += spacer_rules18

        spacer_rules18 = [
            {
                'selector': f'tbody tr:nth-child(13) td:nth-child(2)',
                'props': [('border-right','2px solid white !important')]
               
            }

        ]

        styles += spacer_rules18





        #구분 정리
        # for i in [3,4,5,7,8,9,11,12,13,15,16,17,19,20,21,23,24,25]:
        for i in [4,5,6,8,9,10,12,13,14,16,17,18,20,21,22,24,25,26]:
            body.iloc[0, i] = ""

        # for i in [3,5,7,9,11,13,15,17,19,21,23,25]:
        for i in [4,6,8,10,12,14,16,18,20,22,24,26]:
            body.iloc[1, i] = ""
        



        display_styled_df(body, styles=styles, already_flat=True)

    except Exception as e:
        st.error(f"유통/실수요 영업이익 표 생성 오류: {e}")


    st.divider()


    st.markdown("<h4>3) 메이커별 영업이익 </h4>", unsafe_allow_html=True)
    st.markdown("<h6>- B급 및 매입매출 제외</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 톤, 백만원]</div>", unsafe_allow_html=True)



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
        metrics  = ["판매중량", "단가", "영업이익", "%"]  

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
                return v  # 숫자 아니면 그대로
            return f"{v:,.0f}%"   

        # 데이터 행: 4행부터
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
            body.loc[data_rows, diff_cols].applymap(fmt_diff)
        )


        # 2-1) 영업이익 % (소수 1자리 + %)
        pct_cols = [
            c for c in body.columns
            if c.endswith("_%")
        ]

        body.loc[data_rows, pct_cols] = (
            body.loc[data_rows, pct_cols].applymap(fmt_pct)
        )

        # 2-2) 비중만 따로
        ratio_cols = [c for c in body.columns if c == "비중"]

        body.loc[data_rows, ratio_cols] = (
            body.loc[data_rows, ratio_cols].applymap(fmt_pct_ver2)
        )



        styles = [
            {"selector": "thead", "props": [("display", "none")]},

            {
                "selector": "tbody tr:nth-child(1) td",
                "props": [("font-weight", "700"), ("text-align", "center"),('border-top','3px solid gray !important')],
            },

            {
                "selector": "tbody tr:nth-child(2) td",
                "props": [("font-weight", "700"), ("text-align", "center")],
            },

            {
                "selector": "tbody tr:nth-child(3) td",
                "props": [("font-weight", "700"), ("text-align", "center")],
            },

            {
                "selector": "tbody tr:nth-child(n+4) td:nth-child(1), "
                            "tbody tr:nth-child(n+4) td:nth-child(2)",
                "props": [("text-align", "left")],
            },

            {
                "selector": "tbody tr:nth-child(n+4) td:nth-child(n+3)",
                "props": [("text-align", "right")],
            },



            {
                "selector": "tbody tr td:nth-child(2)",
                "props": [("white-space", "nowrap")],
            },
        ]

        spacer_rules18 = [
            {
                'selector': f'tbody tr:nth-child(1) td:nth-child({r})',
                'props': [('border-right','2px solid white !important')]
               
            }
            # for r in (1,3,4,5,7,8,9,11,12,13,15,16,17,19,20,21,23,24,25)
            for r in (1,4,5,6,8,9,10,12,13,14,16,17,18,20,21,22,24,25,26)
        ]

        styles += spacer_rules18

        
        spacer_rules1 = [
            {
                'selector': f'tbody tr:nth-child(3)',
                'props': [('border-bottom','3px solid gray !important')]
               
            }

        ]

        styles += spacer_rules1

        spacer_rules1 = [
            {
                'selector': f'tbody tr:nth-child(18)',
                'props': [('border-bottom','3px solid gray !important')]
               
            }

        ]

        styles += spacer_rules1

        spacer_rules1 = [
            {
                'selector': f'tbody tr:nth-child(25)',
                'props': [('border-bottom','3px solid gray !important')]
               
            }

        ]

        styles += spacer_rules1

        spacer_rules1 = [
            {
                'selector': f'tbody tr:nth-child(41)',
                'props': [('border-bottom','3px solid gray !important')]
               
            }

        ]

        styles += spacer_rules1




        # spacer_rules2 = [
        #     {
        #         'selector': f'td:nth-child(2)',
        #         'props': [('border-right','3px solid gray !important')]
               
        #     }

        # ]

        # styles += spacer_rules2

        spacer_rules3 = [
            {
                'selector': f'td:nth-child({r})',
                'props': [('border-right','3px solid gray !important')]
               
            }
            # for r in (6,10,14,18,22)
            for r in (2,3,7,11,15,19,23)
        ]

        styles += spacer_rules3

        
        spacer_rules18 = [
            {
                'selector': f'tbody tr:nth-child(2) td:nth-child({r})',
                'props': [('border-right','2px solid white !important')]
               
            }
            # for r in (4,5,8,9,12,13,16,17,20,21,24,25)
            for r in (1,5,6,9,10,13,14,17,18,21,22,25,26)
        ]

        styles += spacer_rules18

        spacer_rules18 = [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child(1)',
                'props': [('border-right','2px solid white !important')]
               
            }
            for r in (3,42)

        ]

        styles += spacer_rules18

        spacer_rules18 = [
            {
                'selector': f'tbody tr:nth-child(42) td:nth-child(2)',
                'props': [('border-right','2px solid white !important')]
               
            }


        ]

        styles += spacer_rules18
        










        #구분 정리
        # for i in [3,4,5,7,8,9,11,12,13,15,16,17,19,20,21,23,24,25]:
        for i in [4,5,6,8,9,10,12,13,14,16,17,18,20,21,22,24,25,26]:
            body.iloc[0, i] = ""

        # for i in [3,5,7,9,11,13,15,17,19,21,23,25]:
        for i in [4,6,8,10,12,14,16,18,20,22,24,26]:
            body.iloc[1, i] = ""

        

        display_styled_df(body, styles=styles, already_flat=True)

    except Exception as e:
        st.error(f"메이커별 영업이익 표 생성 오류: {e}")

    st.divider()
    
    st.markdown("<h4>4) 부서/메이커별 영업이익 </h4>", unsafe_allow_html=True)
    st.markdown("<h6>- B급 및 매입매출 제외</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 톤, 백만원]</div>", unsafe_allow_html=True)



    try:
        year = int(st.session_state['year'])
        month = int(st.session_state['month'])

        file_name = st.secrets["sheets"]["f_99"]
        df_src = pd.read_csv(file_name, dtype=str)

        disp = modules.build_f99(df_src, year, month)
        body = disp.copy()

        # =========================
        # 2) 가짜 헤더 hdr1, hdr2, hdr3 구성
        # =========================
        hdr1 = {col: "" for col in body.columns}
        hdr2 = {col: "" for col in body.columns}
        hdr3 = {col: "" for col in body.columns}


        if "구분1" in hdr1:
            hdr1["구분1"] = "구분"

        products = ["총계","선재영업팀","봉강영업팀","부산영업소","대구영업소","글로벌영업팀"]
        metrics  = ["판매중량", "단가", "영업이익", "%"]  

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
                return v  # 숫자 아니면 그대로
            return f"{v:,.1f}%"   

        # 데이터 행: 4행부터
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
            body.loc[data_rows, diff_cols].applymap(fmt_diff)
        )


        # 2-1) 영업이익 % (소수 1자리 + %)
        pct_cols = [
            c for c in body.columns
            if c.endswith("_%")
        ]

        body.loc[data_rows, pct_cols] = (
            body.loc[data_rows, pct_cols].applymap(fmt_pct)
        )

        # 2-2) 비중만 따로
        ratio_cols = [c for c in body.columns if c == "비중"]

        body.loc[data_rows, ratio_cols] = (
            body.loc[data_rows, ratio_cols].applymap(fmt_pct_ver2)
        )



        styles = [
            {"selector": "thead", "props": [("display", "none")]},

            {
                "selector": "tbody tr:nth-child(1) td",
                "props": [("font-weight", "700"), ("text-align", "center"),('border-top','3px solid gray !important')],
            },

            {
                "selector": "tbody tr:nth-child(2) td",
                "props": [("font-weight", "700"), ("text-align", "center")],
            },

            {
                "selector": "tbody tr:nth-child(3) td",
                "props": [("font-weight", "700"), ("text-align", "center")],
            },

            {
                "selector": "tbody tr:nth-child(n+4) td:nth-child(1), "
                            "tbody tr:nth-child(n+4) td:nth-child(2)",
                "props": [("text-align", "left")],
            },

            {
                "selector": "tbody tr:nth-child(n+4) td:nth-child(n+3)",
                "props": [("text-align", "right")],
            },



            {
                "selector": "tbody tr td:nth-child(2)",
                "props": [("white-space", "nowrap")],
            },
        ]

        spacer_rules18 = [
            {
                'selector': f'tbody tr:nth-child(1) td:nth-child({r})',
                'props': [('border-right','2px solid white !important')]
               
            }
            # for r in (1,3,4,5,7,8,9,11,12,13,15,16,17,19,20,21,23,24,25)
            for r in (3,4,5,7,8,9,11,12,13,15,16,17,19,20,21,23,24,25)
        ]

        styles += spacer_rules18

        
        spacer_rules1 = [
            {
                'selector': f'tbody tr:nth-child(3)',
                'props': [('border-bottom','3px solid gray !important')]
               
            }

        ]

        styles += spacer_rules1

        spacer_rules1 = [
            {
                'selector': f'tbody tr:nth-child(9)',
                'props': [('border-bottom','3px solid gray !important')]
               
            }

        ]

        styles += spacer_rules1






        # # spacer_rules2 = [
        # #     {
        # #         'selector': f'td:nth-child(2)',
        # #         'props': [('border-right','3px solid gray !important')]
               
        # #     }

        # # ]

        # # styles += spacer_rules2

        spacer_rules3 = [
            {
                'selector': f'td:nth-child({r})',
                'props': [('border-right','3px solid gray !important')]
               
            }
            # for r in (6,10,14,18,22)
            for r in (1,2,6,10,14,18,22)
        ]

        styles += spacer_rules3

        
        spacer_rules18 = [
            {
                'selector': f'tbody tr:nth-child(2) td:nth-child({r})',
                'props': [('border-right','2px solid white !important')]
               
            }
            for r in (4,5,8,9,12,13,16,17,20,21,24,25)
            # for r in (1,5,6,9,10,13,14,17,18,21,22,25,26)
        ]

        styles += spacer_rules18

        spacer_rules18 = [
            {
                'selector': f'tbody tr:nth-child(10) td:nth-child(1)',
                'props': [('border-right','2px solid white !important')]
               
            }


        ]

        styles += spacer_rules18

        


        











        #구분 정리
        for i in [3,4,5,7,8,9,11,12,13,15,16,17,19,20,21,23,24,25]:
            body.iloc[0, i] = ""


        for i in [3,5,7,9,11,13,15,17,19,21,23,25]:
            body.iloc[1, i] = ""



        display_styled_df(body, styles=styles, already_flat=True)

    except Exception as e:
        st.error(f"메이커별 영업이익 표 생성 오류: {e}")

    st.divider()


    st.markdown("<h4>5) 부서/사업장/메이커별 영업이익 </h4>", unsafe_allow_html=True)
    st.markdown("<h6>- B급 및 매입매출 제외</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 톤, 백만원]</div>", unsafe_allow_html=True)



    try:
        year = int(st.session_state['year'])
        month = int(st.session_state['month'])

        file_name = st.secrets["sheets"]["f_100"]
        df_src = pd.read_csv(file_name, dtype=str)

        disp = modules.build_f100(df_src, year, month)
        body = disp.copy()

        hdr1 = {col: "" for col in body.columns}
        hdr2 = {col: "" for col in body.columns}
        hdr3 = {col: "" for col in body.columns}

        # (1) 구분 컬럼 텍스트
        if "구분2" in hdr1:
            hdr1["구분2"] = "구분"

        products = ["총계","선재영업팀","봉강영업팀","부산영업소","대구영업소","글로벌영업팀"]
        metrics  = ["판매중량", "단가", "영업이익", "%"]  

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
                return v  # 숫자 아니면 그대로
            return f"{v:,.0f}%"   

        # 데이터 행: 4행부터
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
            body.loc[data_rows, diff_cols].applymap(fmt_diff)
        )


        # 2-1) 영업이익 % (소수 1자리 + %)
        pct_cols = [
            c for c in body.columns
            if c.endswith("_%")
        ]

        body.loc[data_rows, pct_cols] = (
            body.loc[data_rows, pct_cols].applymap(fmt_pct)
        )

        # 2-2) 비중만 따로
        ratio_cols = [c for c in body.columns if c == "비중"]

        body.loc[data_rows, ratio_cols] = (
            body.loc[data_rows, ratio_cols].applymap(fmt_pct_ver2)
        )



        styles = [
            {"selector": "thead", "props": [("display", "none")]},

            {
                "selector": "tbody tr:nth-child(1) td",
                "props": [("font-weight", "700"), ("text-align", "center"),('border-top','3px solid gray !important')],
            },

            {
                "selector": "tbody tr:nth-child(2) td",
                "props": [("font-weight", "700"), ("text-align", "center")],
            },

            {
                "selector": "tbody tr:nth-child(3) td",
                "props": [("font-weight", "700"), ("text-align", "center")],
            },

            {
                "selector": "tbody tr:nth-child(n+4) td:nth-child(1), "
                            "tbody tr:nth-child(n+4) td:nth-child(2)",
                "props": [("text-align", "left")],
            },

            {
                "selector": "tbody tr:nth-child(n+4) td:nth-child(n+3)",
                "props": [("text-align", "right")],
            },



            {
                "selector": "tbody tr td:nth-child(2)",
                "props": [("white-space", "nowrap")],
            },
        ]

        spacer_rules18 = [
            {
                'selector': f'tbody tr:nth-child(1) td:nth-child({r})',
                'props': [('border-right','2px solid white !important')]
               
            }
            # for r in (1,3,4,5,7,8,9,11,12,13,15,16,17,19,20,21,23,24,25)
            for r in (1,4,5,6,8,9,10,12,13,14,16,17,18,20,21,22,24,25,26)
        ]

        styles += spacer_rules18

        
        spacer_rules1 = [
            {
                'selector': f'tbody tr:nth-child(3)',
                'props': [('border-bottom','3px solid gray !important')]
               
            }

        ]

        styles += spacer_rules1

        spacer_rules1 = [
            {
                'selector': f'tbody tr:nth-child(10)',
                'props': [('border-bottom','3px solid gray !important')]
               
            }

        ]

        styles += spacer_rules1

        spacer_rules1 = [
            {
                'selector': f'tbody tr:nth-child(17)',
                'props': [('border-bottom','3px solid gray !important')]
               
            }

        ]

        styles += spacer_rules1

        spacer_rules1 = [
            {
                'selector': f'tbody tr:nth-child(24)',
                'props': [('border-bottom','3px solid gray !important')]
               
            }

        ]

        styles += spacer_rules1




        # spacer_rules2 = [
        #     {
        #         'selector': f'td:nth-child(2)',
        #         'props': [('border-right','3px solid gray !important')]
               
        #     }

        # ]

        # styles += spacer_rules2

        spacer_rules3 = [
            {
                'selector': f'td:nth-child({r})',
                'props': [('border-right','3px solid gray !important')]
               
            }
            # for r in (6,10,14,18,22)
            for r in (2,3,7,11,15,19,23)
        ]

        styles += spacer_rules3

        
        spacer_rules18 = [
            {
                'selector': f'tbody tr:nth-child(2) td:nth-child({r})',
                'props': [('border-right','2px solid white !important')]
               
            }
            # for r in (4,5,8,9,12,13,16,17,20,21,24,25)
            for r in (1,5,6,9,10,13,14,17,18,21,22,25,26)
        ]

        styles += spacer_rules18


        spacer_rules18 = [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child(1)',
                'props': [('border-right','2px solid white !important')]
               
            }
            for r in (3,25)

        ]

        styles += spacer_rules18


        spacer_rules18 = [
            {
                'selector': f'tbody tr:nth-child(25) td:nth-child(2)',
                'props': [('border-right','2px solid white !important')]
               
            }


        ]

        styles += spacer_rules18









        #구분 정리
        for i in [4,5,6,8,9,10,12,13,14,16,17,18,20,21,22,24,25,26]:
            body.iloc[0, i] = ""


        for i in [4,6,8,10,12,14,16,18,20,22,24,26]:
            body.iloc[1, i] = ""


        display_styled_df(body, styles=styles, already_flat=True)

    except Exception as e:
        st.error(f"부서/사업장/메이커별 영업이익 표 생성 오류: {e}")

    st.divider()

    




    st.markdown("<h4>6) 부서별/인당 영업이익 </h4>", unsafe_allow_html=True)
    st.markdown("<h6>- B급 제외</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:13px; color:#666;'>[단위: 톤, 백만원]</div>", unsafe_allow_html=True)

    try:
        year = int(st.session_state["year"])
        month = int(st.session_state["month"])

        file_name = st.secrets["sheets"]["f_101"]
        df_src = pd.read_csv(file_name, dtype=str)


        disp = modules.build_f101(df_src, year, month)
        body = disp.copy()

        # 전월(헤더 표시용) 계산
        if month == 1:
            prev_year, prev_month = year - 1, 12
        else:
            prev_year, prev_month = year, month - 1

        # =========================
        # 2) 가짜 헤더 hdr1, hdr2, hdr3 구성
        # =========================
        hdr1 = {col: "" for col in body.columns}
        hdr2 = {col: "" for col in body.columns}
        hdr3 = {col: "" for col in body.columns}

        # (1) 구분 컬럼 텍스트
        if "구분1" in hdr1:
            hdr1["구분1"] = ""
        if "구분2" in hdr1:
            hdr1["구분2"] = "구분"

        # 기간별 prefix → 1행 헤더 텍스트
        h1_label = {
            "누적_": f"{year}년 누적평균",     # ← 여기: 누적실적 → 누적평균
            "전월_": f"{prev_year}년 {prev_month}월",
            "당월_": f"{year}년 {month}월",
        }

        # metric 이름에 따라 2,3단 헤더 정리
        def fill_header_for_col(col: str):
            for prefix in ["누적_", "전월_", "당월_"]:
                if col.startswith(prefix):
                    metric = col[len(prefix):]

                    # 1행 (기간)
                    hdr1[col] = h1_label.get(prefix, "")

                    # 2·3행: metric 별로 직접 매핑
                    if metric == "판매중량":
                        hdr2[col] = "판매"
                        hdr3[col] = "중량"

                    elif metric == "판매단가":
                        hdr2[col] = "영업이익"   # ← 영업이익 단가
                        hdr3[col] = "단가"

                    elif metric == "영업이익":
                        hdr2[col] = "영업이익"
                        hdr3[col] = "금액"

                    elif metric == "영업이익율":
                        hdr2[col] = "영업이익"
                        hdr3[col] = "%"

                    elif metric == "인원":
                        hdr2[col] = "인원"
                        hdr3[col] = "명"

                    elif metric == "인당중량":
                        hdr2[col] = "인당평균"
                        hdr3[col] = "중량"

                    elif metric == "인당영업이익":
                        hdr2[col] = "인당평균"
                        hdr3[col] = "영업이익"

                    else:
                        hdr2[col] = ""
                        hdr3[col] = ""

                    break

        for c in body.columns:
            fill_header_for_col(c)

        # 헤더 3줄 위에 붙이기
        hdr_df = pd.DataFrame([hdr1, hdr2, hdr3])
        body = pd.concat([hdr_df, body], ignore_index=True)

        # =========================
        # 3) 포맷팅 함수
        # =========================
        def fmt_diff(v):
            # 숫자(단가, 금액, 인원, 인당지표) → 음수는 ( ) + red
            s = str(v)
            if s.strip() == "":
                return ""
            s = s.replace(",", "").replace("%", "")
            try:
                val = float(s)
            except Exception:
                return v
            if val < 0:
                return f'<span style="color:#d62728;">({abs(val):,.0f})</span>'
            return f"{val:,.0f}"

        def fmt_pct(v):
            # 영업이익율 (소수 1자리 + %)
            s = str(v)
            if s.strip() == "":
                return ""
            try:
                s = s.replace(",", "").replace("%", "")
                val = float(s)
            except Exception:
                return v
            return f"{val:,.1f}%"

        # 데이터 행: 4행부터
        data_rows = body.index >= 3

        # 1) 금액/단가/인원/인당 지표 컬럼 포맷
        diff_cols = [
            c
            for c in body.columns
            if (
                any(key in c for key in ["판매중량", "판매단가", "영업이익", "인원", "인당중량", "인당영업이익"])
                and "영업이익율" not in c   # 퍼센트는 제외
            )
        ]

        body.loc[data_rows, diff_cols] = (
            body.loc[data_rows, diff_cols].applymap(fmt_diff)
        )

        # 2) 영업이익율(%) 컬럼
        pct_cols = [c for c in body.columns if "영업이익율" in c]

        body.loc[data_rows, pct_cols] = (
            body.loc[data_rows, pct_cols].applymap(fmt_pct)
        )

        # =========================
        # 4) 스타일 지정
        # =========================
        styles = [
            # 판다스 기본 thead 숨기고 우리가 만든 3줄 사용
            {"selector": "thead", "props": [("display", "none")]},

            # 가짜 헤더 1,2,3 행
            {
                "selector": "tbody tr:nth-child(1) td",
                "props": [("font-weight", "700"), ("text-align", "center"),('border-top','3px solid gray !important')],
            },
            {
                "selector": "tbody tr:nth-child(2) td",
                "props": [("font-weight", "700"), ("text-align", "center")],
            },
            {
                "selector": "tbody tr:nth-child(3) td",
                "props": [("font-weight", "700"), ("text-align", "center")],
            },

            # 본문: 구분1/구분2는 좌측 정렬
            {
                "selector": "tbody tr:nth-child(n+4) td:nth-child(1), "
                            "tbody tr:nth-child(n+4) td:nth-child(2)",
                "props": [("text-align", "left")],
            },
            # 나머지 숫자 컬럼은 우측 정렬
            {
                "selector": "tbody tr:nth-child(n+4) td:nth-child(n+3)",
                "props": [("text-align", "right")],
            },
            # 구분2 줄바꿈 방지
            {
                "selector": "tbody tr td:nth-child(2)",
                "props": [("white-space", "nowrap")],
            },
        ]

        spacer_rules18 = [
            {
                'selector': f'tbody tr:nth-child(1) td:nth-child({r})',
                'props': [('border-right','2px solid white !important')]
               
            }
            # for r in (1,3,4,5,7,8,9,11,12,13,15,16,17,19,20,21,23,24,25)
            for r in (1,3,4,5,6,7,8,10,11,12,13,14,15,17,18,19,20,21,22)
        ]

        styles += spacer_rules18

        
        spacer_rules1 = [
            {
                'selector': f'tbody tr:nth-child({r})',
                'props': [('border-bottom','3px solid gray !important')]
               
            }
            for r in (3,9,15,21)

        ]

        styles += spacer_rules1

        




        # # spacer_rules2 = [
        # #     {
        # #         'selector': f'td:nth-child(2)',
        # #         'props': [('border-right','3px solid gray !important')]
               
        # #     }

        # # ]

        # # styles += spacer_rules2

        spacer_rules3 = [
            {
                'selector': f'td:nth-child({r})',
                'props': [('border-right','3px solid gray !important')]
               
            }
            # for r in (6,10,14,18,22)
            for r in (2,9,16)
        ]

        styles += spacer_rules3

        
        spacer_rules18 = [
            {
                'selector': f'tbody tr:nth-child(2) td:nth-child({r})',
                'props': [('border-right','2px solid white !important')]
               
            }
            # for r in (4,5,8,9,12,13,16,17,20,21,24,25)
            for r in (1,4,5,8,11,12,15,18,19,22)
        ]

        styles += spacer_rules18


        spacer_rules18 = [
            {
                'selector': f'tbody tr:nth-child({r}) td:nth-child(1)',
                'props': [('border-right','2px solid white !important')]
               
            }
            for r in (3,22)

        ]

        styles += spacer_rules18









        #구분 정리
        for i in [3,4,5,6,7,8,10,11,12,13,14,15,17,18,19,20,21,22]:
            body.iloc[0, i] = ""


        for i in [3,5,8,10,12,15,17,19,22]:
            body.iloc[1, i] = ""

        display_styled_df(body, styles=styles, already_flat=True)

    except Exception as e:
        st.error(f"부서별/인당 영업이익 표 생성 오류: {e}")

    st.divider()






# Footer
st.markdown("""
<style>.footer { bottom: 0; left: 0; right: 0; padding: 8px; text-align: center; font-size: 13px; color: #666666;}</style>
<div class="footer">ⓒ 2025 SeAH Special Steel Corp. All rights reserved.</div>
""", unsafe_allow_html=True)
