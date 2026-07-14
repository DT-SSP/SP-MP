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

# --- Helper Functions (도우미 함수) ---
@st.cache_data(ttl=1800)
def load_data(url):
    data = pd.read_csv(url, thousands=',')
    data['실적'] = round(data['실적']).astype(float)
    data['월'] = data['월'].astype(str).apply(lambda x: x if '월' in x else x + '월')
    data = data.fillna('')
    return data

def create_indented_html(s):
    content = s.lstrip(' ')
    num_spaces = len(s) - len(content)
    indent_level = num_spaces // 2
    return f'<p class="indent-{indent_level}">{content}</p>'

def create_stacked_bar_chart(df, categories, colors, trace_options=None, yaxis_range=None):
    fig = go.Figure()
    df_T = df.T
    total_series = pd.Series(0.0, index=df_T.index)
    for category in categories:
        total_series += df_T[category]
    for category, color in zip(categories, colors):
        legend_name = category[1] if isinstance(category, tuple) else category
        fig.add_trace(go.Bar(
            x=df_T.index, y=df_T[category], name=legend_name, marker_color=color,
            text=df_T[category], texttemplate='%{text:,.0f}', textposition='inside',
            insidetextanchor='middle', insidetextfont=dict(color='white')
        ))
    for idx, val in total_series.items():
        fig.add_annotation(x=idx, y=val, text=f"<b>{val:,.0f}</b>", showarrow=False,
                           yshift=10, font=dict(color='black', size=15))
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
    yaxis_options = dict(showticklabels=False, showgrid=False, zeroline=False)
    if yaxis_range:
        yaxis_options['range'] = yaxis_range
    fig.update_layout(
        font=dict(size=15), bargap=0.5, barmode='stack', plot_bgcolor='white',
        yaxis=yaxis_options,
        xaxis=dict(showline=True, linewidth=1, linecolor='lightgrey', tickfont=dict(size=18)),
        legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5, font=dict(size=18)),
        margin=dict(t=80, b=20, l=20, r=20)
    )
    if trace_options:
        fig.update_layout(height=600, yaxis2=dict(overlaying='y', side='right', showticklabels=False,
                                                  showgrid=False, zeroline=False, range=trace_options.get('range')))
    return fig

def display_styled_df(df, styles=None, highlight_cols=None, align="left"):
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
    else:
        wrapper = f"<div style='display:flex; justify-content:flex-start;'>{table_html}</div>"
    st.markdown(wrapper, unsafe_allow_html=True)

def display_memo(memo_file_key, year, month, css_class="memo-body"):
    """메모 파일 키와 년/월을 받아 해당 메모를 화면에 표시합니다.
       css_class 인자를 통해 모든 탭의 간격과 스타일 수치를 완벽하게 통일합니다."""
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
            .{css_class} .indent-0 {{ padding-left: 0px !important; padding-top: 10px; text-indent: -30px !important; font-size: 17px; font-weight: 400; }}
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

# --- Main Streamlit App ---
modules.create_sidebar()
this_year = st.session_state['year']
current_month = st.session_state['month']

st.markdown(f"## {this_year}년 {current_month}월 매출 분석")

t1, t2 = st.tabs(['계획대비 매출실적', '판매구성'])

# =========================================================================
# 1. 계획대비 매출실적 (탭 1)
# =========================================================================
with t1:
    st.markdown("<h4>1) 계획대비 매출실적</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:right; font-size:13px; color:#666; margin-bottom:5px;'>[단위: 톤, 백만원, %]</div>", unsafe_allow_html=True)
    try:
        df_agg = modules.update_report_form(this_year, current_month)
        df_agg = df_agg.reset_index()
        df_agg.columns = [
            '구분1', '구분2',
            f"'{str(this_year)[-2:]}년 계획", '전월',
            '당월 계획', '당월 실적', '당월 계획대비', '당월 전월대비',
            '당월누적 계획', '당월누적 실적', '당월누적 계획대비'
        ]
        df_agg['구분'] = df_agg['구분1'].astype(str) + '_' + df_agg['구분2'].astype(str)
        df_agg = df_agg.drop(columns=['구분1', '구분2'])
        cols = ['구분'] + [c for c in df_agg.columns if c != '구분']
        df_agg = df_agg[cols]
        df_agg = df_agg[df_agg['구분'].str.strip() != '_']

        def fmt_val(v):
            if pd.isna(v) or v == 0: return "0"
            if isinstance(v, str):
                s = v.strip()
                if s.endswith('%'):
                    try:
                        fv = float(s.replace('%', ''))
                        if fv < 0: return f'<span style="color:red">{s}</span>'
                        return s
                    except: return s
                return s
            try:
                iv = int(round(float(v)))
                if iv < 0: return f'<span style="color:red">-{abs(iv):,}</span>'
                return f"{iv:,}"
            except: return str(v)

        for c in df_agg.columns:
            if c != '구분':
                df_agg[c] = df_agg[c].apply(fmt_val)

        styles = [
            {'selector': 'thead th', 'props': [('text-align', 'center'), ('font-weight', '700'), ('border', '1px solid #aaa'), ('background-color', 'white'), ('padding', '8px 16px'), ('font-size', '15px')]},
            {'selector': 'tbody td', 'props': [('border', '1px solid #aaa'), ('padding', '8px 16px'), ('text-align', 'right'), ('background-color', 'white'), ('font-size', '15px')]},
            {'selector': 'tbody td:first-child', 'props': [('text-align', 'left'), ('white-space', 'nowrap'), ('background-color', 'white')]},
        ]
        styled = (df_agg.style.set_table_styles(styles).hide(axis='index'))
        st.markdown(f"<div style='overflow-x:auto'>{styled.to_html(escape=False)}</div>", unsafe_allow_html=True)

        try:
            file_name = st.secrets['memos']['f_30']
            df_memo = pd.read_csv(file_name)
            df_filtered = df_memo[(df_memo['년도'] == int(this_year)) & (df_memo['월'] == int(current_month))]

            if not df_filtered.empty:
                memo_text = df_filtered.iloc[0]['메모']
                if isinstance(memo_text, str) and memo_text.strip():
                    str_list = memo_text.split('\n')
                    html_items = [create_indented_html(s) for s in str_list]
                    body_content = "".join(html_items)

                    full_css = "memo-body-full-t1"
                    html_code = f"""
                    <style>
                        .{full_css} {{ font-family: 'Noto Sans KR', sans-serif; word-spacing: 5px; margin-top: 5px; margin-bottom: 20px; }}
                        .{full_css} p {{ margin: 0.1rem 0; }}
                        .{full_css} .indent-0 {{ padding-left: 20px !important; padding-top: 0px !important; font-size: 17px; font-weight: 400; text-indent: 0px !important; }}
                        .{full_css} .indent-1 {{ padding-left: 40px !important; padding-top: 0px !important; font-size: 17px; text-indent: 0px !important; }}
                        .{full_css} .indent-2 {{ padding-left: 60px !important; font-size: 17px; text-indent: 0px !important; }}
                    </style>
                    <div class="{full_css}">{body_content}</div>
                    """
                    st.markdown(html_code, unsafe_allow_html=True)
        except Exception:
            pass
    except Exception as e:
        st.error(f"계획대비 매출실적 표 생성 오류: {e}")

# =========================================================================
    # =========================================================================
with t2:
    st.markdown("<h4>1) 판매구성</h4>", unsafe_allow_html=True)

    # 🟢 [마스터 스타일] 전 표들의 수직 우측 끝선을 하나로 묶어주는 칼정렬 CSS 변수
    t2_table_align_css = """<style>table { width: 100% !important; }</style>"""

    # 그래프 옆 메모 전용 상단 붕 뜸 방지 스타일시트
    t2_chart_style = """
    <style>
        .t2-chart-memo { margin-top: -5px !important; }
        .t2-chart-memo .indent-0 { padding-left: 20px !important; padding-top: 0px !important; text-indent: 0px !important; font-size: 17px; font-weight: bold; }
        .t2-chart-memo .indent-1 { padding-left: 40px !important; padding-top: 0px !important; text-indent: 0px !important; font-size: 17px; }
        .t2-chart-memo .indent-2 { padding-left: 60px !important; text-indent: 0px !important; font-size: 17px; }
        .t2-chart-memo .indent-3 { padding-left: 80px !important; text-indent: 0px !important; font-size: 12px; }
        .t2-chart-memo p { margin: 0.1rem 0 !important; line-height: 1.3 !important; }
    </style>
    """
    st.markdown(t2_chart_style, unsafe_allow_html=True)

    # -------------------------------------------------------------------------
    # (1) 등급별 판매현황
    # -------------------------------------------------------------------------
    col_l2_1, col_r2_1 = st.columns([6, 4], gap="large")

    with col_l2_1:
        st.markdown("<h4>(1) 등급별 판매현황(월평균)</h4>", unsafe_allow_html=True)
        st.markdown("<div style='text-align:right; font-size:13px; color:#666; margin-bottom:5px;'>[단위: 톤]</div>",
                    unsafe_allow_html=True)
        try:
            df_item = modules.update_item_form(
                modules.create_df(this_year, current_month, load_data(st.secrets['sheets']['f_31']), prev_year=3))

            df_item = df_item.reset_index()
            df_item.columns.name = None
            level0 = df_item.iloc[:, 0].astype(str)
            level1 = df_item.iloc[:, 1].astype(str)
            df_item['구분'] = level0.where(level1.str.strip() == '', level1)
            df_item = df_item.drop(columns=[df_item.columns[0], df_item.columns[1]])
            cols = ['구분'] + [c for c in df_item.columns if c != '구분']
            df_item = df_item[cols]

            # 🟢 컬럼명 수정: 월/년 컬럼에 작은따옴표 추가 ('23년 월평균, '24년 월평균 등)
            # 전월대비, % 제외
            new_cols = []
            for col in df_item.columns:
                if col in ['구분', '전월대비', '%']:
                    new_cols.append(col)
                elif '년' in col and '월' in col and not col.startswith("'"):
                    new_cols.append(f"'{col}")
                else:
                    new_cols.append(col)
            df_item.columns = new_cols


            def fmt_item(v):
                if pd.isna(v): return ""
                if isinstance(v, str):
                    s = v.strip()
                    if s.endswith('%'):
                        try:
                            fv = float(s.replace('%', '').replace('p', ''))
                            if fv < 0: return f'<span style="color:red">{s}</span>'
                        except:
                            pass
                    return s
                try:
                    iv = int(round(float(v)))
                    if iv < 0: return f'<span style="color:red">-{abs(iv):,}</span>'
                    return f"{iv:,}"
                except:
                    return str(v)


            for c in df_item.columns:
                if c != '구분':
                    df_item[c] = df_item[c].apply(fmt_item)

            styles_item = [
                {'selector': 'table',
                 'props': [('border-collapse', 'collapse'), ('width', '100%'), ('font-size', '15px')]},
                {'selector': 'thead th',
                 'props': [('text-align', 'center'), ('font-weight', '700'), ('border', '1px solid #aaa'),
                           ('background-color', 'white'), ('padding', '8px 16px'), ('font-size', '15px')]},
                {'selector': 'tbody td',
                 'props': [('border', '1px solid #aaa'), ('padding', '8px 16px'), ('text-align', 'right'),
                           ('background-color', 'white'), ('font-size', '15px')]},
                {'selector': 'tbody td:first-child',
                 'props': [('text-align', 'left'), ('white-space', 'nowrap'), ('background-color', 'white')]},
            ]
            styled = (df_item.style.set_table_styles(styles_item).hide(axis='index'))
            html_table = styled.to_html(escape=False)

            st.markdown(
                f"<div style='width: 100%; max-width: 100%; overflow-x: auto; display: block;'>{t2_table_align_css}{html_table}</div>",
                unsafe_allow_html=True)
        except Exception as e:
            st.error(f"등급별 판매현황 표 생성 오류: {e}")

    with col_r2_1:
        st.markdown("<h4 style='color:transparent'>(1) 등급별 판매현황(월평균)</h4>", unsafe_allow_html=True)
        st.markdown("<div style='color:transparent; font-size:15px; margin-bottom:5px;'>[단위]</div>",
                    unsafe_allow_html=True)

        t2_tight_memo_style = """
        <style>
            .t2-tight-memo { margin-top: -10px !important; }
            .t2-tight-memo .indent-0 { padding-left: 0px !important; padding-top: 5px !important; text-indent: -30px !important; font-size: 17px; font-weight: bold; }
            .t2-tight-memo .indent-1 { padding-left: 20px !important; padding-top: 3px !important; text-indent: -10px !important; font-size: 17px; }
            .t2-tight-memo .indent-2 { padding-left: 40px !important; font-size: 17px; }
            .t2-tight-memo .indent-3 { padding-left: 60px !important; font-size: 12px; }
            .t2-tight-memo p { margin: 0.1rem 0 !important; line-height: 1.3 !important; }
        </style>
        """
        st.markdown(t2_tight_memo_style, unsafe_allow_html=True)
        display_memo('f_31', this_year, current_month, css_class="t2-tight-memo")

        st.divider()

        # -------------------------------------------------------------------------
        # (2) CHQ 제품 판매현황
        # -------------------------------------------------------------------------
        st.markdown("<h4>(2) CHQ 제품 판매현황</h4>", unsafe_allow_html=True)

        # [차트 1]
        col_l2_2a, col_r2_2a = st.columns([6, 4], gap="large")

with col_l2_2a:
    st.markdown("<h4>[월별 CHQ 판매 추이 (산업/중국材 포함, B급 제외)]</h4>", unsafe_allow_html=True)
    try:
        df_chq_1 = modules.create_df(this_year, current_month, load_data(st.secrets['sheets']['f_32']))
        df_plot_chq = df_chq_1.loc[('CHQ', ['열처리', '비열처리']), df_chq_1.columns[:6]]
        fig_chq = create_stacked_bar_chart(df_plot_chq, [('CHQ', '열처리'), ('CHQ', '비열처리')], ['#e54e2b', '#3b4951'])
        fig_chq.update_layout(margin=dict(l=40, r=0, t=20, b=20))
        st.plotly_chart(fig_chq, use_container_width=True, key="plot_chq_main")
    except Exception as e:
        st.error(f"CHQ 판매 추이 차트 생성 오류: {e}")
with col_r2_2a:
    st.markdown("<h4 style='color:transparent'>[월별 CHQ 판매 추이]</h4>", unsafe_allow_html=True)
    display_memo('f_32', this_year, current_month, css_class="t2-chart-memo")

# [차트 2]
col_l2_2b, col_r2_2b = st.columns([6, 4], gap="large")
with col_l2_2b:
    st.markdown("<h4>[월별 산업/중국材 판매 추이(B급 제외)]</h4>", unsafe_allow_html=True)
    try:
        # 🟢 [오타 전면 수정 완료] 기존 secrets 오타를 규격 명칭인 'sheets'로 완벽 변환
        df_chq_2 = modules.create_df(this_year, current_month, load_data(st.secrets['sheets']['f_33']))
        df_plot_chq2 = df_chq_2.loc[('산업/중국재', ['열처리', '비열처리']), df_chq_2.columns[:6]]
        fig_chq2 = create_stacked_bar_chart(df_plot_chq2, [('산업/중국재', '열처리'), ('산업/중국재', '비열처리')], ['#e54e2b', '#3b4951'])
        fig_chq2.update_layout(margin=dict(l=40, r=0, t=20, b=20))
        st.plotly_chart(fig_chq2, use_container_width=True, key="plot_chq_industrial")
    except Exception as e:
        st.error(f"산업/중국재 판매 추이 차트 생성 오류: {e}")
with col_r2_2b:
    st.markdown("<h4 style='color:transparent'>[월별 산업/중국材 판매 추이]</h4>", unsafe_allow_html=True)
    display_memo('f_33', this_year, current_month, css_class="t2-chart-memo")

st.divider()

# -------------------------------------------------------------------------
# (3) CD 강종류별 판매현황
# -------------------------------------------------------------------------
st.markdown("<h4>(3) CD 강종류별 판매현황</h4>", unsafe_allow_html=True)

# [차트 1]
col_l2_3a, col_r2_3a = st.columns([6, 4], gap="large")
with col_l2_3a:
    st.markdown("<h4>[월별 CD 판매 추이 (산업/중국材 포함, B급 제외)]</h4>", unsafe_allow_html=True)
    try:
        df_cd = modules.create_df(this_year, current_month, load_data(st.secrets['sheets']['f_34']))
        df_plot_cd = df_cd.loc[('CD', ['일/탄', '합금강', '쾌삭강']), df_cd.columns[:6]]
        fig_cd = create_stacked_bar_chart(df_plot_cd, [('CD', '합금강'), ('CD', '쾌삭강'), ('CD', '일/탄')], ['#e54e2b', '#a5a5a5', '#3b4951'])
        fig_cd.update_layout(margin=dict(l=40, r=0, t=20, b=20))
        st.plotly_chart(fig_cd, use_container_width=True, key="plot_cd_main")
    except Exception as e:
        st.error(f"CD 판매 추이 차트 생성 오류: {e}")
with col_r2_3a:
    st.markdown("<h4 style='color:transparent'>[월별 CD 판매 추이]</h4>", unsafe_allow_html=True)
    display_memo('f_34', this_year, current_month, css_class="t2-chart-memo")

# [차트 2]
col_l2_3b, col_r2_3b = st.columns([6, 4], gap="large")
with col_l2_3b:
    st.markdown("<h4>[월별 산업/중국材 CD 판매 추이(B급 제외)]</h4>", unsafe_allow_html=True)
    try:
        df_cd_2 = modules.create_df(this_year, current_month, load_data(st.secrets['sheets']['f_35']))
        df_plot_cd2 = df_cd_2.loc[('산업/중국재', ['일/탄', '합금강']), df_cd_2.columns[:6]]
        fig_cd2 = create_stacked_bar_chart(df_plot_cd2, [('산업/중국재', '합금강'), ('산업/중국재', '일/탄')], ['#e54e2b', '#3b4951'])
        fig_cd2.update_layout(margin=dict(l=40, r=0, t=20, b=20))
        st.plotly_chart(fig_cd2, use_container_width=True, key="plot_cd_industrial")
    except Exception as e:
        st.error(f"산업/중국재 CD 판매 추이 차트 생성 오류: {e}")
with col_r2_3b:
    st.markdown("<h4 style='color:transparent'>[월별 산업/중국材 CD 판매 추이]</h4>", unsafe_allow_html=True)
    display_memo('f_35', this_year, current_month, css_class="t2-chart-memo")

st.divider()

# -------------------------------------------------------------------------
# (4) 비가공품 판매현황
# -------------------------------------------------------------------------
col_l2_4, col_r2_4 = st.columns([6, 4], gap="large")
with col_l2_4:
    st.markdown("<h4>(4) 비가공품 판매현황</h4>", unsafe_allow_html=True)
    st.markdown("<h4>[월별/품목별 비가공품 판매 추이]</h4>", unsafe_allow_html=True)
    try:
        df_process = modules.create_df(this_year, current_month, load_data(st.secrets['sheets']['f_36']), prev_month=5)
        df_plot_process = df_process.loc[('비가공', ['CHQ', 'BAR', '거래처 수']), df_process.columns[-7:]]
        trace_opt = {'name': ('비가공', '거래처 수'), 'color': '#ffc107', 'range': [-50, 120]}
        fig_process = create_stacked_bar_chart(df_plot_process, [('비가공', 'CHQ'), ('비가공', 'BAR')], ['#e54e2b', '#3b4951'], trace_options=trace_opt, yaxis_range=[0, 7000])
        fig_process.update_layout(margin=dict(l=40, r=0, t=20, b=20))
        st.plotly_chart(fig_process, use_container_width=True, key="plot_process")
    except Exception as e:
        st.error(f"비가공품 판매 추이 차트 생성 오류: {e}")
with col_r2_4:
    st.markdown("<h4 style='color:transparent'>(4) 비가공품 판매현황</h4>", unsafe_allow_html=True)
    st.markdown("<h4 style='color:transparent'>[월별/품목별 비가공품 판매 추이]</h4>", unsafe_allow_html=True)
    display_memo('f_36', this_year, current_month, css_class="t2-chart-memo")

st.divider()

# -------------------------------------------------------------------------
# (5) 동일거래처 매입매출현황
# -------------------------------------------------------------------------
col_l2_5, col_r2_5 = st.columns([6, 4], gap="large")
with col_l2_5:
    st.markdown("<h4>(5). 동일거래처 매입매출현황</h4>", unsafe_allow_html=True)
    st.markdown("<h4>[월별/품목별 임가공품 판매 추이]</h4>", unsafe_allow_html=True)
    try:
        df_same = modules.create_df(this_year, current_month, load_data(st.secrets['sheets']['f_37']))
        df_plot_same = df_same.loc[('매입매출', ['CHQ', 'BAR']), df_same.columns[:6]]
        fig_same = create_stacked_bar_chart(df_plot_same, [('매입매출', 'CHQ'), ('매입매출', 'BAR')], ['#e54e2b', '#3b4951'])
        fig_same.update_layout(margin=dict(l=40, r=0, t=20, b=20))
        st.plotly_chart(fig_same, use_container_width=True, key="plot_same")
    except Exception as e:
        st.error(f"임가공품 판매 추이 차트 생성 오류: {e}")
with col_r2_5:
    st.markdown("<h4 style='color:transparent'>(5). 동일거래처 매입매출현황</h4>", unsafe_allow_html=True)
    st.markdown("<h4 style='color:transparent'>[월별/품목별 임가공품 판매 추이]</h4>", unsafe_allow_html=True)
    display_memo('f_37', this_year, current_month, css_class="t2-chart-memo")

st.divider()

# 🟢 [정돈 완료] (6) PSI 지표 (with t2: 내부 범위로 정상 포함)
# =========================================================================
psi_styles = [
    {'selector': 'table', 'props': [('border-collapse', 'collapse'), ('width', '100%'), ('font-size', '15px')]},
    {'selector': 'thead th',
     'props': [('text-align', 'center'), ('font-weight', '700'), ('border', '1px solid #aaa'),
               ('background-color', 'white'), ('padding', '8px 16px'), ('font-size', '15px')]},
    {'selector': 'tbody td',
     'props': [('border', '1px solid #aaa'), ('padding', '8px 16px'), ('text-align', 'right'),
               ('background-color', 'white'), ('font-size', '15px')]},
    {'selector': 'tbody th',
     'props': [('border', '1px solid #aaa'), ('padding', '8px 16px'), ('background-color', 'white'),
               ('font-size', '15px')]},
]


# 🟢 PSI 인덱스 변환 함수 (25.5 → '25년 5월)
def convert_psi_index(df):
    new_index = []
    for idx in df.index:
        if isinstance(idx, (int, float)):
            parts = str(idx).split('.')
            if len(parts) == 2:
                year = f"'{parts[0]}"
                month = parts[1]
                new_index.append(f"{year}년 {month}월")
            else:
                new_index.append(str(idx))
        else:
            new_index.append(str(idx))
    df.index = new_index
    return df


# 6-1. 매입매출 포함
col_l2_6a, col_r2_6a = st.columns([6, 4], gap="large")
with col_l2_6a:
    st.markdown("<h4>(6-1). PSI (입고, 판매, 재고) 지표 (매입매출 포함)</h4>", unsafe_allow_html=True)
    st.markdown(
        "<div style='text-align:right; font-size:13px; color:#666; margin-bottom:5px; font-weight:normal;'>[단위: 톤]</div>",
        unsafe_allow_html=True)
    try:
        df_psi = modules.update_psi_form(this_year, current_month, load_data(st.secrets['sheets']['f_38_1']))
        df_psi = convert_psi_index(df_psi)
        styled_psi = df_psi.style.format(lambda x: f"{x:,.0f}" if isinstance(x, (int, float)) and pd.notnull(x) else x).set_table_styles(psi_styles)
        html_table_psi = styled_psi.to_html(escape=False)
        # 🟢 대기열 칼정렬 CSS 강제 주입
        st.markdown(
            f"<div style='width: 100%; max-width: 100%; overflow-x: auto; display: block;'>{t2_table_align_css}{html_table_psi}</div>",
            unsafe_allow_html=True)
    except Exception as e:
        st.error(f"PSI(매입매출 포함) 지표 생성 오류: {e}")
with col_r2_6a:
    st.markdown("<h4 style='color:transparent'>(6-1). PSI 지표 (매입매출 포함)</h4>", unsafe_allow_html=True)
    st.markdown("<div style='color:transparent; font-size:15px; margin-bottom:5px;'>[단위]</div>",
                unsafe_allow_html=True)
    try:
        if 'f_38_1' in st.secrets.get('memos', {}):
            display_memo('f_38_1', this_year, current_month)
    except:
        pass

st.divider()

# 6-2. 매입매출 제외
col_l2_6b, col_r2_6b = st.columns([6, 4], gap="large")
with col_l2_6b:
    st.markdown("<h4>(6-2). PSI (입고, 판매, 재고) 지표 (매입매출 제외)</h4>", unsafe_allow_html=True)
    st.markdown(
        "<div style='text-align:right; font-size:13px; color:#666; margin-bottom:5px; font-weight:normal;'>[단위: 톤]</div>",
        unsafe_allow_html=True)
    try:
        df_psi_2 = modules.update_psi_2_form(this_year, current_month, load_data(st.secrets['sheets']['f_38_2']))
        df_psi_2 = convert_psi_index(df_psi_2)
        styled_psi2 = df_psi_2.style.format(lambda x: f"{x:,.0f}" if isinstance(x, (int, float)) and pd.notnull(x) else x).set_table_styles(psi_styles)
        html_table_psi2 = styled_psi2.to_html(escape=False)
        # 🟢 대기열 칼정렬 CSS 강제 주입
        st.markdown(
            f"<div style='width: 100%; max-width: 100%; overflow-x: auto; display: block;'>{t2_table_align_css}{html_table_psi2}</div>",
            unsafe_allow_html=True)
    except Exception as e:
        st.error(f"PSI(매입매출 제외) 지표 생성 오류: {e}")
with col_r2_6b:
    st.markdown("<h4 style='color:transparent'>(6-2). PSI 지표 (매입매출 제외)</h4>", unsafe_allow_html=True)
    st.markdown("<div style='color:transparent; font-size:15px; margin-bottom:5px;'>[단위]</div>",
                unsafe_allow_html=True)
    try:
        if 'f_38_2' in st.secrets.get('memos', {}):
            display_memo('f_38_2', this_year, current_month)
    except:
        pass

# Footer
st.markdown("""
<style>.footer { bottom: 0; left: 0; right: 0; padding: 8px; text-align: center; font-size: 13px; color: #666666;}</style>
<div class="footer">ⓒ 2025 SeAH Special Steel Corp. All rights reserved.</div>
""", unsafe_allow_html=True)