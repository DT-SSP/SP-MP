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


# 🟢 [마스터 통일] 모든 탭의 간격을 성공작 스펙으로 일치시키는 display_memo 구현
def display_memo(memo_file_key, year, month, css_class="memo-body"):
    """메모 파일 키와 년/월을 받아 해당 메모를 화면에 표시합니다.
       css_class 인자를 통해 독립된 스타일 울타리를 보장합니다."""
    file_name = st.secrets['memos'][memo_file_key]
    try:
        df_memo = pd.read_csv(file_name)
        df_filtered = df_memo[(df_memo['년도'] == year) & (df_memo['월'] == month)]

        if df_filtered.empty:
            return

        memo_text = df_filtered.iloc[0]['메모']
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
            .{css_class} .indent-0 {{ padding-left: 0px !important; padding-top: 10px; text-indent: -30px !important; font-size: 17px; font-weight: 400;}
            .{css_class} .indent-1 {{ padding-left: 20px !important; padding-top: 5px; text-indent: -10px !important; font-size: 17px; }}
            .{css_class} .indent-2 {{ padding-left: 40px !important; text-indent: 0px !important; font-size: 17px; }}
            .{css_class} .indent-3 {{ padding-left: 60px !important; text-indent: 0px !important; font-size: 12px; }}
            .{css_class} p {{ margin: 0.1rem 0; }}
        </style>
        <div class="{css_class}">{body_content}</div>
        """
        st.markdown(html_code, unsafe_allow_html=True)
    except (FileNotFoundError, KeyError):
        pass


# 🟢 [정렬 고도화] 가로 폭 100% 강제 맞춤 기능이 추가된 표 스타일러
def display_styled_df(df, custom_css_align=""):
    """DataFrame에 스타일을 적용하여 가로폭을 꽉 채워 렌더링합니다."""
    styled_df = (
        df.style
        .format(lambda x: f"{x:,.0f}" if isinstance(x, (int, float)) and pd.notnull(x) else x)
        .set_properties(**{'text-align': 'right', 'font-family': 'Noto Sans KR'})
        .set_table_styles([
            {'selector': 'th, td',
             'props': [('border', '1px solid #aaa'), ('padding', '8px 16px'), ('font-size', '15px')]},
            {'selector': 'thead th', 'props': [('font-weight', '700')]},
            {'selector': 'table', 'props': [('border-collapse', 'collapse')]}
        ])
    )
    table_html = styled_df.to_html(index=True)
    st.markdown(
        f"<div style='width: 100%; max-width: 100%; overflow-x: auto; display: block;'>{custom_css_align}{table_html}</div>",
        unsafe_allow_html=True)


def display_inventory_chart(df_plot, bar_traces, scatter_trace, key):
    """설정을 받아 재고 현황 차트를 생성하고 화면에 표시합니다."""
    fig = go.Figure()
    df_plot_T = df_plot.T
    df_plot_T['총합'] = 0

    for trace in bar_traces:
        data_key = trace['name']
        legend_name = data_key[1] if isinstance(data_key, tuple) else data_key

        fig.add_trace(go.Bar(
            x=df_plot_T.index, y=df_plot_T[data_key], name=legend_name,
            marker_color=trace['color'], text=df_plot_T[data_key],
            texttemplate='%{text:,.0f}', textposition='inside',
            insidetextanchor='middle', insidetextfont=dict(color='white')
        ))
        df_plot_T['총합'] += df_plot_T[data_key]

    if scatter_trace:
        data_key = scatter_trace['name']
        legend_name = data_key[1] if isinstance(data_key, tuple) else data_key

        fig.add_trace(go.Scatter(
            x=df_plot_T.index, y=df_plot_T[data_key], name=legend_name,
            mode='lines+markers+text', marker=dict(size=8, color=scatter_trace['color']),
            line=dict(width=3, color=scatter_trace['color']), yaxis='y2',
            text=df_plot_T[data_key], textposition="top center",
            textfont=dict(size=14, color='black'), texttemplate='%{text:,.0f}',
            hovertemplate=f"{legend_name}: %{{y}}<extra></extra>"
        ))

    for i, val in df_plot_T['총합'].items():
        fig.add_annotation(
            x=i, y=val, text=f"<b>{val:,.0f}</b>",
            showarrow=False, yshift=10, font=dict(color='black', size=15)
        )

    fig.update_layout(
        height=400, font=dict(size=15), bargap=0.4, barmode='stack', plot_bgcolor='white',
        yaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
        xaxis=dict(showline=True, linewidth=1, linecolor='lightgrey', tickfont=dict(size=15)),
        legend=dict(orientation="h", yanchor="bottom", y=-0.35, xanchor="center", x=0.5, font=dict(size=15)),
        margin=dict(t=30, b=10, l=10, r=10)
    )
    if scatter_trace:
        fig.update_layout(yaxis2=dict(
            overlaying='y', side='right', showticklabels=False, showgrid=False, zeroline=False,
            range=scatter_trace.get('range')
        ))

    st.plotly_chart(fig, use_container_width=True, key=key)


# --- Main Streamlit App ---
modules.create_sidebar()
this_year = st.session_state['year']
current_month = st.session_state['month']

st.markdown(f"## {this_year}년 {current_month}월 재고 분석")

# 🟢 [끝선 수직 정렬용 CSS 장치]
t6_table_align_css = """<style>table { width: 100% !important; }</style>"""

# 전용 메모 상하 밀착 울타리 스타일
t6_tight_memo_style = """
<style>
    .t6-tight-memo { margin-top: -10px !important; }
    .t6-tight-memo .indent-0 { padding-left: 0px !important; padding-top: 5px !important; text-indent: -30px !important; font-size: 17px; font-weight: bold; }
    .t6-tight-memo .indent-1 { padding-left: 20px !important; padding-top: 3px !important; text-indent: -10px !important; font-size: 17px; }
    .t6-tight-memo .indent-2 { padding-left: 40px !important; font-size: 17px; }
    .t6-tight-memo .indent-3 { padding-left: 60px !important; font-size: 12px; }
    .t6-tight-memo p { margin: 0.1rem 0 !important; line-height: 1.3 !important; }
</style>
"""
st.markdown(t6_tight_memo_style, unsafe_allow_html=True)

t1, t2, t3, t4 = st.tabs(['재고자산 회전율', '연령별 재고현황', '총 재고 및 장기재고 현황', '등급별 재고현황'])

# =========================================================================
# 1. 재고자산 회전율 (탭 1: 표 6 : 메모 4 완벽 레이아웃 전환 구역)
# =========================================================================
with t1:
    col_l6_1, col_r6_1 = st.columns([6, 4], gap="large")

    with col_l6_1:
        st.markdown("<h4>1. 재고자산 현황</h4>", unsafe_allow_html=True)
        st.markdown("<div style='text-align:right; font-size:15px; color:#666; margin-bottom:5px;'>[단위: 백만원, 톤]</div>",
                    unsafe_allow_html=True)

        try:
            df_turnover = modules.update_turnover_form(this_year, current_month)
            df_show = df_turnover.copy()
            df_show.columns = [f"{c[0]}{c[1]}" if c[0].strip() else c[1] for c in df_turnover.columns]

            rename_map = {}
            for col in df_show.columns:
                if '년말' in col:
                    rename_map[col] = col.strip()
                elif '년' in col and '월' in col:
                    year_part = col[:2]
                    month_part = col[2:].replace('월', '').strip()
                    rename_map[col] = f"{year_part}.{month_part}월"
            df_show = df_show.rename(columns=rename_map)

            df_show = df_show.reset_index()
            df_show.columns = ['구분', ''] + list(df_show.columns[2:])
            df_show['구분'] = df_show.apply(lambda row: row['구분'] if str(row['']).strip() == '' else row[''], axis=1)
            df_show = df_show.drop(columns=[''])
            df_show.columns.name = None

            numeric_cols = [c for c in df_show.columns if c not in ('구분', '전월대비증감률')]


            def color_negative(val):
                return 'color: red' if isinstance(val, (int, float)) and pd.notnull(val) and val < 0 else ''


            styled_df = (
                df_show.style
                .format({col: "{:,.0f}" for col in numeric_cols}, na_rep="-")
                .map(color_negative, subset=numeric_cols)
                .hide(axis='index')
                .set_properties(**{'text-align': 'right'})
                .set_properties(subset=['구분'], **{'text-align': 'left'})
                .set_properties(**{'font-family': 'Noto Sans KR'})
                .set_table_styles([
                    {'selector': 'th, td',
                     'props': [('border', '1px solid #aaa'), ('padding', '8px 16px'), ('font-size', '15px')]},
                    {'selector': 'thead th', 'props': [('font-weight', '700')]},
                    {'selector': 'table', 'props': [('border-collapse', 'collapse')]}
                ])
            )

            html_table = styled_df.to_html(escape=False)
            st.markdown(
                f"<div style='width: 100%; max-width: 100%; overflow-x: auto; display: block;'>{t6_table_align_css}{html_table}</div>",
                unsafe_allow_html=True)

            st.markdown("<div style='text-align:left; font-size:13px; color:#666; margin-top:5px;'>※ 미착품, 저장품 제외</div>",
                        unsafe_allow_html=True)
        except Exception as e:
            st.error(f"재고자산 현황 표 표시 오류: {e}")

    with col_r6_1:
        st.markdown("<h4 style='color:transparent'>1. 재고자산 현황 투명제목</h4>", unsafe_allow_html=True)
        st.markdown("<div style='color:transparent; font-size:15px; margin-bottom:5px;'>[단위]</div>",
                    unsafe_allow_html=True)
        display_memo('f_50', this_year, current_month, css_class="t6-tight-memo")

    st.divider()

# =========================================================================
# 2. 연령별 재고현황 (탭 2: 표 6 : 그래프 4 분할배치 + 아래 대형 메모)
# =========================================================================
with t2:
    st.markdown("<h4>2. 연령별 재고현황</h4>", unsafe_allow_html=True)
    try:
        data = load_data(st.secrets['sheets']['f_51'])
        data['실적'] /= 1000
        dfs = modules.create_df(this_year, current_month, data, mean="False")

        df_1 = process_inventory_df(dfs.loc['원재료'])
        df_2 = process_inventory_df(dfs.loc['재공품'])
        df_3 = process_inventory_df(dfs.loc['제품'])

        bar_traces_1 = [
            {'name': '정상재', 'color': '#3b4951'},
            {'name': '매입매출', 'color': '#e54e2b'}
        ]

        # ── (1) 원재료 현황 구역 ──
        st.markdown("<h4>[원재료 현황]</h4>", unsafe_allow_html=True)
        col_l2_a, col_r2_a = st.columns([6, 4], gap="large")
        with col_l2_a:
            display_styled_df(df_1, custom_css_align=t6_table_align_css)
        with col_r2_a:
            scatter_trace_1 = {'name': '장기재고', 'color': '#ffc107', 'range': [500, 5000]}
            display_inventory_chart(df_1.loc[['정상재', '매입매출', '장기재고']], bar_traces_1, scatter_trace_1,
                                    key="raw_materials_chart")

        st.divider()

        # ── (2) 재공품 현황 구역 ──
        st.markdown("<h4>[재공품 현황]</h4>", unsafe_allow_html=True)
        col_l2_b, col_r2_b = st.columns([6, 4], gap="large")
        with col_l2_b:
            display_styled_df(df_2, custom_css_align=t6_table_align_css)
        with col_r2_b:
            scatter_trace_2 = {'name': '장기재고', 'color': '#ffc107', 'range': [10, 700]}
            display_inventory_chart(df_2.loc[['정상재', '매입매출', '장기재고']], bar_traces_1, scatter_trace_2,
                                    key="work_in_progress_chart")

        st.divider()

        # ── (3) 제품 현황 구역 ──
        st.markdown("<h4>[제품 현황]</h4>", unsafe_allow_html=True)
        col_l2_c, col_r2_c = st.columns([6, 4], gap="large")
        with col_l2_c:
            display_styled_df(df_3, custom_css_align=t6_table_align_css)
        with col_r2_c:
            scatter_trace_3 = {'name': '장기재고', 'color': '#ffc107', 'range': [2000, 10000]}
            display_inventory_chart(df_3.loc[['정상재', '매입매출', '장기재고']], bar_traces_1, scatter_trace_3,
                                    key="products_chart")

        try:
            if 'f_51' in st.secrets.get('memos', {}):
                st.divider()
                display_memo('f_51', this_year, current_month, css_class="t6-tight-memo")
        except:
            pass
        st.divider()
    except Exception as e:
        st.error(f"연령별 재고현황 데이터 처리 오류: {e}")

# =========================================================================
# 🟢 [탭3, 탭4 전용] 표 아래 메모를 오른쪽으로 25px 밀어내는 독립 스타일시트
# =========================================================================
t6_shifted_memo_style = """
<style>
    .t6-shifted-memo { margin-bottom: 12px; padding-left: 25px !important; } /* 👈 25px 오른쪽 이동 */
    .t6-shifted-memo .indent-0 { padding-left: 0px !important; padding-top: 5px !important; text-indent: -30px !important; font-size: 17px; font-weight: bold; }
    .t6-shifted-memo .indent-1 { padding-left: 20px !important; padding-top: 3px !important; text-indent: -10px !important; font-size: 17px; }
    .t6-shifted-memo .indent-2 { padding-left: 40px !important; font-size: 17px; }
    .t6-shifted-memo .indent-3 { padding-left: 60px !important; font-size: 12px; }
    .t6-shifted-memo p { margin: 0.1rem 0 !important; line-height: 1.3 !important; }
</style>
"""
st.markdown(t6_shifted_memo_style, unsafe_allow_html=True)


# =========================================================================
# 3. 총 재고 및 장기재고 현황
# =========================================================================
with t3:
    st.markdown("<h4>3. 총 재고 및 장기재고 현황</h4>", unsafe_allow_html=True)
    try:
        df_totals = pd.DataFrame({
            '원재료 합계': df_1.loc['합계'], '원재료_장기재고': df_1.loc['장기재고'],
            '재공품 합계': df_2.loc['합계'], '재공품_장기재고': df_2.loc['장기재고'],
            '제품 합계': df_3.loc['합계'], '제품_장기재고': df_3.loc['장기재고']
        }).T
        df_totals.loc['장기재고'] = df_totals.loc['원재료_장기재고'] + df_totals.loc['재공품_장기재고'] + df_totals.loc['제품_장기재고']

        # 6:4 좌우 레이아웃 개시
        col_l3, col_r3 = st.columns([6, 4], gap="large")

        with col_l3:
            # 1. 먼저 60% 폭으로 표를 깔끔하게 그리고
            display_styled_df(df_totals.loc[['원재료 합계', '재공품 합계', '제품 합계', '장기재고']], custom_css_align=t6_table_align_css)
            st.markdown("<br>", unsafe_allow_html=True)  # 조밀한 숨쉬기 공간 여백

            # 2. 🟢 [우측 이동 연동] 왼쪽 방 내부 표 바로 밑에 전용 클래스(t6-shifted-memo) 주입
            try:
                if 'f_54' in st.secrets.get('memos', {}):
                    display_memo('f_54', this_year, current_month, css_class="t6-shifted-memo")
            except:
                pass

        with col_r3:
            # 3. 우측 40% 방에는 그래프를 나란히 배치합니다.
            bar_traces_total = [
                {'name': '원재료 합계', 'color': '#3b4951'},
                {'name': '재공품 합계', 'color': '#e54e2b'},
                {'name': '제품 합계', 'color': '#a5a5a5'}
            ]
            scatter_trace_total = {'name': '장기재고', 'color': '#ffc107', 'range': [2000, 50000]}
            display_inventory_chart(df_totals.loc[['원재료 합계', '재공품 합계', '제품 합계', '장기재고']], bar_traces_total,
                                    scatter_trace_total, key="total_inventory_chart")

        st.divider()
    except Exception as e:
        st.error(f"총 재고 및 장기재고 표출 오류: {e}")


# =========================================================================
# 4. 등급별 재고현황 (탭 4: 중복 인덱스 충돌 및 오류 완벽 해결본)
# =========================================================================
with t4:
    st.markdown("<h4>4. 등급별 재고현황</h4>", unsafe_allow_html=True)
    try:
        # 원본 데이터 로드 및 로직 원형 유지
        df_cls = modules.create_df(this_year, current_month, load_data(st.secrets['sheets']['f_52']), mean="False")
        plot_rows = [('제품', 'B급'), ('제품', 'C급'), ('제품', 'D급'), ('제품', 'D2급'), ('제품', 'X급'), ('재공품', '재공품')]

        # 🟢 [오류 해결 핵심] 차트용과 표 표출용 데이터를 완전히 분리하여 인덱스 충돌 원천 차단
        df_chart_cls = df_cls.loc[plot_rows, df_cls.columns[1:]]
        df_table_cls = df_cls.loc[plot_rows, df_cls.columns[1:]].copy()

        # 6:4 좌우 레이아웃 구동
        col_l4, col_r4 = st.columns([6, 4], gap="large")

        with col_l4:
            # MultiIndex를 깨끗하게 한글 '구분' 단일 컬럼으로 변환 (오류 방지 안전망)
            labels = [f"{r[0]} ({r[1]})" for r in df_table_cls.index]
            df_table_cls.index = labels
            df_table_cls.index.name = '구분'

            # 깔끔하게 100% 폭으로 표 출력 (소수점 자동 제거 포함)
            display_styled_df(df_table_cls, custom_css_align=t6_table_align_css)
            st.markdown("<br>", unsafe_allow_html=True)

            # 🟢 [우측 이동 연동] 탭4 역시 전용 클래스(t6-shifted-memo) 주입하여 표 하단 정렬선 일치
            try:
                if 'f_55' in st.secrets.get('memos', {}):
                    display_memo('f_55', this_year, current_month, css_class="t6-shifted-memo")
            except:
                pass

        with col_r4:
            # 안전하게 분리된 데이터로 막대 차트 빌드
            bar_traces_cls = [
                {'name': ('제품', 'B급'), 'color': '#3b4951'},
                {'name': ('제품', 'C급'), 'color': '#e54e2b'},
                {'name': ('제품', 'D급'), 'color': '#a5a5a5'},
                {'name': ('제품', 'D2급'), 'color': '#D5a5a5'},
                {'name': ('제품', 'X급'), 'color': '#70AD47'}
            ]
            scatter_trace_cls = {'name': ('재공품', '재공품'), 'color': '#70AD47', 'range': [10, 250]}
            display_inventory_chart(df_chart_cls, bar_traces_cls, scatter_trace_cls, key="grade_inventory_chart")

        st.divider()
    except Exception as e:
        st.error(f"등급별 재고현황 표출 오류: {e}")

# Footer
st.markdown("""
<style>.footer { bottom: 0; left: 0; right: 0; padding: 8px; text-align: center; font-size: 13px; color: #666666;}</style>
<div class="footer">ⓒ 2026 SeAH Special Steel Corp. All rights reserved.</div>
""", unsafe_allow_html=True)