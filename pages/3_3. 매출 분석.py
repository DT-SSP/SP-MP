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

def create_stacked_bar_chart(df, categories, colors, trace_options=None, yaxis_range=None):
    """스택 바 차트를 생성하고 Plotly Figure 객체를 반환합니다."""
    fig = go.Figure()
    df_T = df.T

    total_series = pd.Series(0.0, index=df_T.index)
    for category in categories:
        total_series += df_T[category]

    for category, color in zip(categories, colors):
        legend_name = category[1] if isinstance(category, tuple) else category
        fig.add_trace(go.Bar(
            x=df_T.index,
            y=df_T[category],
            name=legend_name,
            marker_color=color,
            text=df_T[category],
            texttemplate='%{text:,.0f}',
            textposition='inside',
            insidetextanchor='middle',
            insidetextfont=dict(color='white')
        ))

    for idx, val in total_series.items():
        fig.add_annotation(
            x=idx,
            y=val,
            text=f"<b>{val:,.0f}</b>",
            showarrow=False,
            yshift=10,
            font=dict(color='black', size=15)
        )

    if trace_options:
        trace_name = trace_options['name'][1] if isinstance(trace_options['name'], tuple) else trace_options['name']
        fig.add_trace(go.Scatter(
            x=df_T.index, y=df_T[trace_options['name']], name=trace_name,
            mode='lines+markers+text', marker=dict(size=8, color=trace_options['color']),
            line=dict(width=3, color=trace_options['color']), yaxis='y2',
            text=df_T[trace_options['name']], textposition="top center",
            textfont=dict(size=18, color='black'), texttemplate='%{text:,.0f}',
            hovertemplate=f"{trace_name}: %{{y}}<extra></extra>"
        ))

    # y축 옵션을 설정하는 부분을 수정합니다.
    yaxis_options = dict(showticklabels=False, showgrid=False, zeroline=False)
    if yaxis_range:
        yaxis_options['range'] = yaxis_range

    fig.update_layout(
        font=dict(size=15), bargap=0.5, barmode='stack', plot_bgcolor='white',
        yaxis=yaxis_options,  # 수정된 y축 옵션을 적용합니다.
        xaxis=dict(showline=True, linewidth=1, linecolor='lightgrey', tickfont=dict(size=18)),
        legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5, font=dict(size=18)),
        margin=dict(t=80, b=20, l=20, r=20)
    )

    if trace_options:
        fig.update_layout(height=600, yaxis2=dict(overlaying='y', side='right', showticklabels=False, showgrid=False,
                                                  zeroline=False, range=trace_options.get('range')))

    return fig


def display_styled_df(df, styles=None, highlight_cols=None, align="left"):
    """DataFrame에 스타일을 적용하여 화면에 표시합니다. align: 'left' | 'center' | 'right'"""
    def highlight_columns(col):
        if col.name in (highlight_cols or []):
            return ['background-color: #f0f0f0'] * len(col)
        return [''] * len(col)

    styled_df = (
        df.style
        .format(lambda x: f"{x:,.0f}" if isinstance(x, (int, float)) and pd.notnull(x) else x)
        .set_properties(**{'text-align': 'right', 'font-family': 'Noto Sans KR'})
        .apply(highlight_columns, axis=0)
    )
    if styles:
        styled_df = styled_df.set_table_styles(styles)

    table_html = styled_df.to_html(index=True)

    if align == "center":
        wrapper = f"<div style='display:flex; justify-content:center;'>{table_html}</div>"
    elif align == "right":
        wrapper = f"<div style='display:flex; justify-content:flex-end;'>{table_html}</div>"
    else:  # left
        wrapper = f"<div style='display:flex; justify-content:flex-start;'>{table_html}</div>"

    st.markdown(wrapper, unsafe_allow_html=True)

    # st.markdown(wrapper, unsafe_allow_html=True)
    # st.markdown(styled_df.to_html(), unsafe_allow_html=True)


# --- Main Streamlit App ---
modules.create_sidebar()
this_year = st.session_state['year']
current_month = st.session_state['month']

st.markdown(f"## {this_year}년 {current_month}월 매출 분석")

t1, t2 = st.tabs(['계획대비 매출실적', '판매구성'])

# 1. 계획대비 매출실적
with t1:
    st.markdown("<h4>1. 계획대비 매출실적</h4>", unsafe_allow_html=True)
    df_agg = modules.update_report_form(this_year, current_month)

    # 스타일 정의
    border_rows = [1, 4, 7, 10, 13, 14, 17]
    styles = [{'selector': f'tr:nth-child({row_idx + 2})', 'props': [('border-bottom', '2px solid grey')]} for row_idx
              in border_rows]
    spacer_rules1 = [
            {
                'selector': f'tbody tr:nth-child(1)',
                'props': [('border-top','3px solid gray !important')]
               
            }

        ]

    styles += spacer_rules1
    styles.append({'selector': 'thead tr:last-child th', 'props': [('border-bottom', '2px solid grey')]},
    )


    columns_to_color = [('당월', '계획'), ('당월', '실적'), ('당월', '계획대비'), ('당월', '전월대비')]

    # 함수 호출
    display_styled_df(df_agg, styles=styles, highlight_cols=columns_to_color,align='left')
    display_memo('f_30', this_year, current_month)
    


# 2. 판매 구성
with t2:
    st.markdown("<h4>2. 판매구성</h4>", unsafe_allow_html=True)

    # (1) 등급별 판매현황
    st.markdown("<h5>(1) 등급별 판매현황(월평균)</h5>", unsafe_allow_html=True)
    df_item = modules.update_item_form(
        modules.create_df(this_year, current_month, load_data(st.secrets['sheets']['f_31'])))

    border_rows = [3, 4, 6, 7]
    styles_2 = []

    styles_2.append({
        'selector': 'th.row_heading.level1.row3, th.blank.level0, th.row_heading.level1.row4, th.row_heading.level1.row5, th.row_heading.level1.row6',
        'props': [('border-left', '2px solid white !important')]
    })

    styles_2.append({
        'selector': 'th.row_heading.level1.row4, th.row_heading.level1.row0, th.row_heading.level1.row1',
        'props': [('border-bottom', '2px solid white !important')]
    })

    styles_2.append({
        'selector': 'thead tr:last-child th',
        'props': [('border-bottom', '3px solid grey')]
    })

    styles_2.append({
        'selector': 'th.row_heading.level1.row0, th.row_heading.level1.row1, th.row_heading.level1.row2',
        'props': [('border-left', '3px solid grey')]
    })

    styles_2.extend([
        {
            'selector': f'tr:nth-child({row_idx})',
            'props': [('border-bottom', '3px solid grey !important')]
        }
        for row_idx in border_rows
    ])

    display_styled_df(df_item, styles = styles_2)
    display_memo('f_31',this_year, current_month)
    st.divider()

    # (2) CHQ 제품 판매현황
    st.markdown("<h5>(2) CHQ 제품 판매현황</h5>", unsafe_allow_html=True)
    st.markdown("<h6>[월별 CHQ 판매 추이 (산업/중국材 포함, B급 제외)]</h6>", unsafe_allow_html=True)
    df_chq_1 = modules.create_df(this_year, current_month, load_data(st.secrets['sheets']['f_32']))
    df_plot_chq = df_chq_1.loc[('CHQ', ['열처리', '비열처리']), df_chq_1.columns[:6]]
    fig_chq = create_stacked_bar_chart(
        df_plot_chq,
        [('CHQ', '열처리'), ('CHQ', '비열처리')],
        ['#e54e2b', '#3b4951']
    )
    chart_col, _ = st.columns([0.7, 0.3])   # 왼쪽: 차트, 오른쪽: 여백
    with chart_col:
        st.plotly_chart(fig_chq, use_container_width=True, key="plot_chq_main")

    display_memo('f_32', this_year, current_month)

    st.markdown("<h6>[월별 산업/중국材 판매 추이(B급 제외)]</h6>", unsafe_allow_html=True)
    df_chq_2 = modules.create_df(this_year, current_month, load_data(st.secrets['sheets']['f_33']))
    df_plot_chq2 = df_chq_2.loc[('산업/중국재', ['열처리', '비열처리']), df_chq_2.columns[:6]]
    fig_chq2 = create_stacked_bar_chart(
        df_plot_chq2,
        [('산업/중국재', '열처리'), ('산업/중국재', '비열처리')],
        ['#e54e2b', '#3b4951']
    )
    chart_col, _ = st.columns([0.7, 0.3])   # 왼쪽: 차트, 오른쪽: 여백
    with chart_col:
        st.plotly_chart(fig_chq2, use_container_width=True, key="plot_chq_industrial")

    display_memo('f_33', this_year, current_month)
    st.divider()

    # (3) CD 강종류별 판매현황
    st.markdown("<h5>(3) CD 강종류별 판매현황</h5>", unsafe_allow_html=True)
    st.markdown("<h6>[월별 CD 판매 추이 (산업/중국材 포함, B급 제외)]</h6>", unsafe_allow_html=True)
    df_cd = modules.create_df(this_year, current_month, load_data(st.secrets['sheets']['f_34']))
    df_plot_cd = df_cd.loc[('CD', ['일/탄', '합금강', '쾌삭강']), df_cd.columns[:6]]
    fig_cd = create_stacked_bar_chart(
        df_plot_cd,
        [('CD', '합금강'), ('CD', '쾌삭강'), ('CD', '일/탄')],
        ['#e54e2b', '#a5a5a5', '#3b4951']
    )

    chart_col, _ = st.columns([0.7, 0.3])  # 왼쪽: 차트, 오른쪽: 여백
    with chart_col:
        st.plotly_chart(fig_cd, use_container_width=True, key="plot_cd_main")

    display_memo('f_34', this_year, current_month)

    st.markdown("<h6>[월별 산업/중국材 CD 판매 추이(B급 제외)]</h6>", unsafe_allow_html=True)
    df_cd_2 = modules.create_df(this_year, current_month, load_data(st.secrets['sheets']['f_35']))
    df_plot_cd2 = df_cd_2.loc[('산업/중국재', ['일/탄', '합금강']), df_cd_2.columns[:6]]
    fig_cd2 = create_stacked_bar_chart(
        df_plot_cd2,
        [('산업/중국재', '합금강'), ('산업/중국재', '일/탄')],
        ['#e54e2b', '#3b4951']
    )

    chart_col, _ = st.columns([0.7, 0.3])   # 왼쪽: 차트, 오른쪽: 여백
    with chart_col:
        st.plotly_chart(fig_cd2, use_container_width=True, key="plot_cd_industrial")

    display_memo('f_35', this_year, current_month)
    st.divider()

    # (4) 비가공품 판매현황
    st.markdown("<h5>(4) 비가공품 판매현황</h5>", unsafe_allow_html=True)
    st.markdown("<h6>[월별/품목별 비가공품 판매 추이]</h6>", unsafe_allow_html=True)

    df_process = modules.create_df(this_year, current_month, load_data(st.secrets['sheets']['f_36']), prev_month=5)
    df_plot_process = df_process.loc[('비가공', ['CHQ', 'BAR', '거래처 수']), df_process.columns[-7:]]
    trace_opt = {'name': ('비가공', '거래처 수'), 'color': '#ffc107', 'range': [-50, 120]}

    fig_process = create_stacked_bar_chart(
        df_plot_process,
        [('비가공', 'CHQ'), ('비가공', 'BAR')],
        ['#e54e2b', '#3b4951'],
        trace_options=trace_opt,
        yaxis_range=[0, 7000]
    )

    chart_col, _ = st.columns([0.7, 0.3])  # 왼쪽: 차트, 오른쪽: 여백
    with chart_col:
        st.plotly_chart(fig_process, use_container_width=True, key="plot_process")

    display_memo('f_36', this_year, current_month)
    st.divider()

    # (5) 동일거래처 매입매출현황
    st.markdown("<h5>(5). 동일거래처 매입매출현황</h5>", unsafe_allow_html=True)
    st.markdown("<h6>[월별/품목별 임가공품 판매 추이]</h6>", unsafe_allow_html=True)
    df_same = modules.create_df(this_year, current_month, load_data(st.secrets['sheets']['f_37']))
    df_plot_same = df_same.loc[('매입매출', ['CHQ', 'BAR']), df_same.columns[:6]]
    fig_same = create_stacked_bar_chart(
        df_plot_same,
        [('매입매출', 'CHQ'), ('매입매출', 'BAR')],
        ['#e54e2b', '#3b4951']
    )

    chart_col, _ = st.columns([0.7, 0.3])  # 왼쪽: 차트, 오른쪽: 여백
    with chart_col:
        st.plotly_chart(fig_same, use_container_width=True, key="plot_same")

    display_memo('f_37', this_year, current_month)
    st.divider()


    # (6) PSI 지표
    st.markdown("<h5>(6-1). PSI (입고, 판매, 재고) 지표 (매입매출 포함)</h5>", unsafe_allow_html=True)
    df_psi = modules.update_psi_form(this_year, current_month, load_data(st.secrets['sheets']['f_38_1']))
    display_styled_df(df_psi)

    st.divider()
    st.markdown("<h5>(6-2). PSI (입고, 판매, 재고) 지표 (매입매출 제외)</h5>", unsafe_allow_html=True)
    df_psi_2 = modules.update_psi_2_form(this_year, current_month, load_data(st.secrets['sheets']['f_38_2']))
    display_styled_df(df_psi_2)


# Footer
st.markdown("""
<style>.footer { bottom: 0; left: 0; right: 0; padding: 8px; text-align: center; font-size: 13px; color: #666666;}</style>
<div class="footer">ⓒ 2025 SeAH Special Steel Corp. All rights reserved.</div>
""", unsafe_allow_html=True)