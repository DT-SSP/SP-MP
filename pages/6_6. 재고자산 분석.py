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

def process_inventory_df(df):
    """재고 데이터프레임에 합계, 정상재, 장기재고 열을 계산하여 추가합니다."""
    df_copy = df.copy()
    df_copy.loc['합계'] = df_copy.loc[['3개월 이하', '3개월 초과', '6개월 초과', '1년 초과']].sum()
    df_copy.loc['정상재'] = df_copy.loc['합계'] - df_copy.loc['매입매출']
    df_copy.loc['장기재고'] = df_copy.loc[['6개월 초과', '1년 초과']].sum()
    df_copy.index.name = None
    return df_copy


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


def display_styled_df(df):
    """DataFrame에 스타일을 적용하여 화면 중앙에 표시합니다."""
    styled_df = (
        df.style
        .format(lambda x: f"{x:,.0f}" if isinstance(x, (int, float)) and pd.notnull(x) else x)
        .set_properties(**{'text-align': 'right', 'font-family': 'Noto Sans KR'})
    )
    table_html = styled_df.to_html(index=True)
    centered_html = f"<div style='display: flex; justify-content: left;'>{table_html}</div>"
    st.markdown(centered_html, unsafe_allow_html=True)

def display_inventory_chart(df_plot, bar_traces, scatter_trace, key):
    """설정을 받아 재고 현황 차트를 생성하고 화면에 표시합니다."""
    fig = go.Figure()
    df_plot_T = df_plot.T
    df_plot_T['총합'] = 0

    # Bar Traces 추가
    for trace in bar_traces:
        data_key = trace['name']  # 데이터 조회를 위한 키 (문자열 또는 튜플)
        # 범례 이름을 위한 처리: 튜플이면 2번째 요소 사용, 아니면 그대로 사용
        legend_name = data_key[1] if isinstance(data_key, tuple) else data_key

        fig.add_trace(go.Bar(
            x=df_plot_T.index, y=df_plot_T[data_key], name=legend_name,  # name에 legend_name 사용
            marker_color=trace['color'], text=df_plot_T[data_key],
            texttemplate='%{text:,.0f}', textposition='inside',
            insidetextanchor='middle', insidetextfont=dict(color='white')
        ))
        df_plot_T['총합'] += df_plot_T[data_key]

    # Scatter Trace 추가 (옵션)
    if scatter_trace:
        data_key = scatter_trace['name']
        legend_name = data_key[1] if isinstance(data_key, tuple) else data_key

        fig.add_trace(go.Scatter(
            x=df_plot_T.index, y=df_plot_T[data_key], name=legend_name,  # name에 legend_name 사용
            mode='lines+markers+text', marker=dict(size=8, color=scatter_trace['color']),
            line=dict(width=3, color=scatter_trace['color']), yaxis='y2',
            text=df_plot_T[data_key], textposition="top center",
            textfont=dict(size=15, color='white'), texttemplate='%{text:,.0f}',
            hovertemplate=f"{legend_name}: %{{y}}<extra></extra>"  # hovertemplate에도 legend_name 사용
        ))

    # Annotation 추가
    for i, val in df_plot_T['총합'].items():
        fig.add_annotation(
            x=i, y=val, text=f"<b>{val:,.0f}</b>",
            showarrow=False, yshift=10, font=dict(color='black', size=15)
        )

    # Layout 업데이트
    fig.update_layout(
        height=500, font=dict(size=15), bargap=0.5, barmode='stack', plot_bgcolor='white',
        yaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
        xaxis=dict(showline=True, linewidth=1, linecolor='lightgrey', tickfont=dict(size=18)),
        legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5, font=dict(size=18)),
        margin=dict(t=80, b=20, l=20, r=20)
    )
    if scatter_trace:
        fig.update_layout(yaxis2=dict(
            overlaying='y', side='right', showticklabels=False, showgrid=False, zeroline=False,
            range=scatter_trace.get('range')
        ))

    # 차트 표시


    st.plotly_chart(fig, use_container_width=True, key=key)
# --- Main Streamlit App ---
modules.create_sidebar()
this_year = st.session_state['year']
current_month = st.session_state['month']

# st.image("logo.gif", width=200)
st.markdown(f"## {this_year}년 {current_month}월 재고 분석")

t1, t2, t3, t4 = st.tabs(['재고자산 회전율', '연령별 재고현황', '총 재고 및 장기재고 현황', '등급별 재고현황'])

# 1. 재고자산 회전율
with t1:
    st.markdown("<h4>1. 재고자산 회전율</h4>", unsafe_allow_html=True)
    df_turnover = modules.update_turnover_form(this_year, current_month)
    display_styled_df(df_turnover)

    display_memo('f_50', this_year, current_month)
    st.divider()

# 2. 연령별 재고현황
with t2:
    st.markdown("<h4>2. 연령별 재고현황</h4>", unsafe_allow_html=True)
    data = load_data(st.secrets['sheets']['f_51'])
    data['실적'] /= 1000
    dfs = modules.create_df(this_year, current_month, data, mean="False")

    # 데이터프레임 생성 및 처리
    df_1 = process_inventory_df(dfs.loc['원재료'])
    df_2 = process_inventory_df(dfs.loc['재공품'])
    df_3 = process_inventory_df(dfs.loc['제품'])


    st.markdown("<h6>[원재료 현황]</h6>", unsafe_allow_html=True)

    bar_traces_1 = [
        {'name': '정상재', 'color': '#3b4951'},
        {'name': '매입매출', 'color': '#e54e2b'}
    ]
    scatter_trace_1 = {'name': '장기재고', 'color': '#ffc107', 'range': [500, 5000]}

    display_inventory_chart(
        df_1.loc[['정상재', '매입매출', '장기재고']], 
        bar_traces_1, 
        scatter_trace_1, 
        key="raw_materials_chart"
    )

    # 👉 표를 왼쪽 정렬해서 보여주기
    col_left, col_empty = st.columns([0.7, 0.3])  # 비율은 상황에 맞게 조절
    with col_left:
        display_styled_df(df_1)

    st.divider()

    # 재공품 현황
    st.markdown("<h6>[재공품 현황]</h6>", unsafe_allow_html=True)
    scatter_trace_2 = {'name': '장기재고', 'color': '#ffc107', 'range': [10, 700]}
    display_inventory_chart(df_2.loc[['정상재', '매입매출', '장기재고']], bar_traces_1, scatter_trace_2,
                            key="work_in_progress_chart")
    display_styled_df(df_2)
    st.divider()

    # 제품 현황
    st.markdown("<h6>[제품 현황]</h6>", unsafe_allow_html=True)
    scatter_trace_3 = {'name': '장기재고', 'color': '#ffc107', 'range': [2000, 10000]}
    display_inventory_chart(df_3.loc[['정상재', '매입매출', '장기재고']], bar_traces_1, scatter_trace_3, key="products_chart")
    display_styled_df(df_3)
    st.divider()

# 3. 총 재고 및 장기재고 현황
with t3:
    st.markdown("<h4>3. 총 재고 및 장기재고 현황</h4>", unsafe_allow_html=True)
    df_totals = pd.DataFrame({
        '원재료 합계': df_1.loc['합계'], '원재료_장기재고': df_1.loc['장기재고'],
        '재공품 합계': df_2.loc['합계'], '재공품_장기재고': df_2.loc['장기재고'],
        '제품 합계': df_3.loc['합계'], '제품_장기재고': df_3.loc['장기재고']
    }).T
    df_totals.loc['장기재고'] = df_totals.loc['원재료_장기재고'] + df_totals.loc['재공품_장기재고'] + df_totals.loc['제품_장기재고']

    bar_traces_total = [
        {'name': '원재료 합계', 'color': '#3b4951'},
        {'name': '재공품 합계', 'color': '#e54e2b'},
        {'name': '제품 합계', 'color': '#a5a5a5'}
    ]
    scatter_trace_total = {'name': '장기재고', 'color': '#ffc107', 'range': [2000, 50000]}
    display_inventory_chart(df_totals.loc[['원재료 합계', '재공품 합계', '제품 합계', '장기재고']], bar_traces_total, scatter_trace_total,
                            key="total_inventory_chart")
    display_memo('f_54', this_year, current_month)
    st.divider()

# 4. 등급별 재고현황
with t4:
    st.markdown("<h4>4. 등급별 재고현황</h4>", unsafe_allow_html=True)
    df_cls = modules.create_df(this_year, current_month, load_data(st.secrets['sheets']['f_52']), mean="False")

    plot_rows = [('제품', 'B급'), ('제품', 'C급'), ('제품', 'D급'), ('제품', 'D2급'), ('제품', 'X급'), ('재공품', '재공품')]
    df_plot_cls = df_cls.loc[plot_rows, df_cls.columns[1:]]

    bar_traces_cls = [
        {'name': ('제품', 'B급'), 'color': '#3b4951'},
        {'name': ('제품', 'C급'), 'color': '#e54e2b'},
        {'name': ('제품', 'D급'), 'color': '#a5a5a5'},
        {'name': ('제품', 'D2급'), 'color': '#D5a5a5'},
        {'name': ('제품', 'X급'), 'color': '#70AD47'}
    ]
    scatter_trace_cls = {'name': ('재공품', '재공품'), 'color': '#70AD47', 'range': [10, 250]}
    display_inventory_chart(df_plot_cls, bar_traces_cls, scatter_trace_cls, key="grade_inventory_chart")
    display_memo('f_55', this_year, current_month)
    st.divider()

# Footer
st.markdown("""
<style>.footer { bottom: 0; left: 0; right: 0; padding: 8px; text-align: center; font-size: 13px; color: #666666;}</style>
<div class="footer">ⓒ 2025 SeAH Special Steel Corp. All rights reserved.</div>
""", unsafe_allow_html=True)