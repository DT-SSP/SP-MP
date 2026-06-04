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

        # 년도/월 기준으로 필터
        df_filtered = df_memo[(df_memo['년도'] == year) & (df_memo['월'] == month)]

        if df_filtered.empty:
            return

        # 여러 행이 있을 경우, 일단 첫 번째 행 사용
        memo_text = df_filtered.iloc[0]['메모']

        if not isinstance(memo_text, str) or not memo_text.strip():
            return

        str_list = memo_text.split('\n')
        html_items = [create_indented_html(s) for s in str_list]
        body_content = "".join(html_items)

        # 🟢 [수치 통일 완성] 성공한 페이지의 좁은 간격 스펙(0px, -30px)으로 완전 통일!
        html_code = f"""
        <style>
            .{css_class} {{
                font-family: 'Noto Sans KR', sans-serif;
                word-spacing: 5px;
                margin-bottom: 12px;
            }}
            /* padding과 마이너스 내어쓰기 수치를 좁은 성공작 버전과 1:1 일치시켰습니다 */
            .{css_class} .indent-0 {{ padding-left: 0px !important; padding-top: 10px; text-indent: -30px !important; font-size: 17px; font-weight: bold; }}
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

# 1. 계획대비 매출실적
# 1. 계획대비 매출실적
with t1:
    st.markdown("<h4>1. 계획대비 매출실적</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:right; font-size:15px; color:#666; margin-bottom:5px;'>[단위: 톤, 백만원, %]</div>",
                unsafe_allow_html=True)
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
                        if fv < 0:
                            return f'<span style="color:red">{s}</span>'
                        return s
                    except:
                        return s
                return s
            try:
                iv = int(round(float(v)))
                if iv < 0: return f'<span style="color:red">-{abs(iv):,}</span>'
                return f"{iv:,}"
            except:
                return str(v)


        for c in df_agg.columns:
            if c != '구분':
                df_agg[c] = df_agg[c].apply(fmt_val)

        styles = [
            {'selector': 'thead th', 'props': [('text-align', 'center'), ('font-weight', '700'),
                                               ('border', '1px solid #aaa'), ('background-color', 'white'),
                                               ('padding', '8px 16px'), ('font-size', '15px')]},
            {'selector': 'tbody td', 'props': [('border', '1px solid #aaa'), ('padding', '8px 16px'),
                                               ('text-align', 'right'), ('background-color', 'white'),
                                               ('font-size', '15px')]},
            {'selector': 'tbody td:first-child', 'props': [('text-align', 'left'), ('white-space', 'nowrap'),
                                                           ('background-color', 'white')]},
        ]
        styled = (df_agg.style.set_table_styles(styles).hide(axis='index'))
        st.markdown(f"<div style='overflow-x:auto'>{styled.to_html(escape=False)}</div>", unsafe_allow_html=True)

        # =========================================================================
        # 🟢 [Full 화면 전용] 위아래 밀착형 수동 메모 마운트 시스템
        # =========================================================================
        try:
            file_name = st.secrets['memos']['f_30']
            df_memo = pd.read_csv(file_name)
            df_filtered = df_memo[(df_memo['년도'] == int(this_year)) & (df_memo['월'] == int(current_month))]

            if not df_filtered.empty:
                memo_text = df_filtered.iloc[0]['메모']

                # 방어코드: 데이터가 비어있거나 문자열이 아니면 패스
                if isinstance(memo_text, str) and memo_text.strip():
                    str_list = memo_text.split('\n')
                    html_items = [create_indented_html(s) for s in str_list]
                    body_content = "".join(html_items)

                    # css_class를 고유하게 격리하고, 상단 여백 제거(!important) 및 들여쓰기 보정
                    full_css = "memo-body-full-t1"
                    html_code = f"""
                    <style>
                        .{full_css} {{
                            font-family: 'Noto Sans KR', sans-serif;
                            word-spacing: 5px;
                            margin-top: 5px; /* 표 밑에 바짝 붙도록 간격 최소화 */
                            margin-bottom: 20px;
                        }}
                        /* 0.1rem 간격 유지 및 상단 패딩 리셋으로 위로 완벽 밀착 */
                        .{full_css} p {{ margin: 0.1rem 0; }}
                        .{full_css} .indent-0 {{ padding-left: 20px !important; padding-top: 0px !important; font-size: 17px; font-weight: bold; text-indent: 0px !important; }}
                        .{full_css} .indent-1 {{ padding-left: 40px !important; padding-top: 0px !important; font-size: 17px; text-indent: 0px !important; }}
                        .{full_css} .indent-2 {{ padding-left: 60px !important; font-size: 17px; text-indent: 0px !important; }}
                    </style>
                    <div class="{full_css}">{body_content}</div>
                    """
                    st.markdown(html_code, unsafe_allow_html=True)
        except Exception:
            pass  # 메모 로드 오류 시 화면을 깨뜨리지 않고 안전하게 통과

    except Exception as e:
        st.error(f"계획대비 매출실적 표 생성 오류: {e}")

# 2. 판매구성
with t2:
    st.markdown("<h4>2. 판매구성</h4>", unsafe_allow_html=True)

    # 🟢 [마스터 스타일] 그래프 옆 메모의 상단 붕 뜸 방지 및 글자 가출 차단 격리 CSS
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

    # =========================================================================
    # (1) 등급별 판매현황 (6:4 비율 좌우 분할)
    # =========================================================================
    col_l2_1, col_r2_1 = st.columns([6, 4], gap="large")

    with col_l2_1:
        st.markdown("<h4>(1) 등급별 판매현황(월평균)</h4>", unsafe_allow_html=True)
        # 🟢 [수정사항 2] 전체 화면 오른쪽 끝이 아닌, 60% 영역 표의 우측 어깨 위에 바짝 안착시킴
        st.markdown("<div style='text-align:right; font-size:15px; color:#666; margin-bottom:5px;'>[단위: 톤]</div>",
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


            def fmt_item(v):
                if pd.isna(v): return ""
                if isinstance(v, str):
                    s = v.strip()
                    if s.endswith('%'):
                        try:
                            fv = float(s.replace('%', '').replace('p', ''))
                            if fv < 0:
                                return f'<span style="color:red">{s}</span>'
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

            # 🟢 [표 폭 100% 고정] 글로벌 오염 없이 이 표만 가로 폭을 꽉 채워 아래 차트들과 끝선을 맞춥니다.
            styles_item = [
                {'selector': 'table',
                 'props': [('border-collapse', 'collapse'), ('width', '100%'), ('font-size', '15px')]},
                {'selector': 'thead th', 'props': [('text-align', 'center'), ('font-weight', '700'),
                                                   ('border', '1px solid #aaa'), ('background-color', 'white'),
                                                   ('padding', '8px 16px'), ('font-size', '15px')]},
                {'selector': 'tbody td', 'props': [('border', '1px solid #aaa'), ('padding', '8px 16px'),
                                                   ('text-align', 'right'), ('background-color', 'white'),
                                                   ('font-size', '15px')]},
                {'selector': 'tbody td:first-child', 'props': [('text-align', 'left'), ('white-space', 'nowrap'),
                                                               ('background-color', 'white')]},
            ]
            styled = (df_item.style.set_table_styles(styles_item).hide(axis='index'))

            # 🟢 [핵심 추가] 손익요약 탭 성공 공식을 그대로 가져와 가로 폭 끝 길이를 6 영역 끝까지 완벽하게 밀어내는 CSS
            custom_css = """<style>table { width: 100% !important; }</style>"""
            html_table = styled.to_html(escape=False)

            # 컨테이너 내부에 custom_css와 html_table을 혼합하여 가로 폭 정렬 마운트
            st.markdown(
                f"<div style='width: 100%; max-width: 100%; overflow-x: auto; display: block;'>{custom_css}{html_table}</div>",
                unsafe_allow_html=True)

        except Exception as e:
            st.error(f"등급별 판매현황 표 생성 오류: {e}")

        with col_r2_1:
            st.markdown("<h4 style='color:transparent'>(1) 등급별 판매현황(월평균)</h4>", unsafe_allow_html=True)
            st.markdown("<div style='color:transparent; font-size:15px; margin-bottom:5px;'>[단위]</div>",
                        unsafe_allow_html=True)

            # 🟢 [수정사항 1] 표와 메모 사이 간격을 타이트하게 조이고 전달해주신 성공한 6:4 페이지 스펙을 담은 전용 스타일
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

            # 표 옆의 메모에 t2-tight-memo 클래스를 동적 매핑하여 깔끔하게 결합합니다.
            display_memo('f_31', this_year, current_month, css_class="t2-tight-memo")

    st.divider()

    # =========================================================================
    # (2) CHQ 제품 판매현황 (6:4 비율 좌우 분할)
    # =========================================================================
    st.markdown("<h4>(2) CHQ 제품 판매현황</h4>", unsafe_allow_html=True)

    # [차트 1] 월별 CHQ 판매 추이
    col_l2_2a, col_r2_2a = st.columns([6, 4], gap="large")
    with col_l2_2a:
        st.markdown("<h4>[월별 CHQ 판매 추이 (산업/중국材 포함, B급 제외)]</h4>", unsafe_allow_html=True)
        try:
            df_chq_1 = modules.create_df(this_year, current_month, load_data(st.secrets['sheets']['f_32']))
            df_plot_chq = df_chq_1.loc[('CHQ', ['열처리', '비열처리']), df_chq_1.columns[:6]]
            fig_chq = create_stacked_bar_chart(df_plot_chq, [('CHQ', '열처리'), ('CHQ', '비열처리')], ['#e54e2b', '#3b4951'])
            # 🟢 [끝선 동기화] Plotly 내부의 우측 여백 패딩을 0으로 지워 표 끝선 위치와 수직 일치시킴
            fig_chq.update_layout(margin=dict(l=40, r=0, t=20, b=20))
            st.plotly_chart(fig_chq, use_container_width=True, key="plot_chq_main")
        except Exception as e:
            st.error(f"CHQ 판매 추이 차트 생성 오류: {e}")
    with col_r2_2a:
        st.markdown("<h4 style='color:transparent'>[월별 CHQ 판매 추이]</h4>", unsafe_allow_html=True)
        # 🟢 [붕 뜸 현상 방지] 차트 옆메모 전용 클래스(t2-chart-memo)를 명시적으로 주입
        display_memo('f_32', this_year, current_month, css_class="t2-chart-memo")

    # [차트 2] 월별 산업/중국재 판매 추이
    col_l2_2b, col_r2_2b = st.columns([6, 4], gap="large")
    with col_l2_2b:
        st.markdown("<h4>[월별 산업/중국材 판매 추이(B급 제외)]</h4>", unsafe_allow_html=True)
        try:
            df_chq_2 = modules.create_df(this_year, current_month, load_data(st.secrets['secrets']['f_33']))
            df_plot_chq2 = df_chq_2.loc[('산업/중국재', ['열처리', '비열처리']), df_chq_2.columns[:6]]
            fig_chq2 = create_stacked_bar_chart(df_plot_chq2, [('산업/중국재', '열처리'), ('산업/중국재', '비열처리')],
                                                ['#e54e2b', '#3b4951'])
            # 🟢 끝선 동기화
            fig_chq2.update_layout(margin=dict(l=40, r=0, t=20, b=20))
            st.plotly_chart(fig_chq2, use_container_width=True, key="plot_chq_industrial")
        except Exception as e:
            st.error(f"산업/중국재 판매 추이 차트 생성 오류: {e}")
    with col_r2_2b:
        st.markdown("<h4 style='color:transparent'>[월별 산업/중국材 판매 추이]</h4>", unsafe_allow_html=True)
        display_memo('f_33', this_year, current_month, css_class="t2-chart-memo")

    st.divider()

    # =========================================================================
    # (3) CD 강종류별 판매현황 (6:4 비율 좌우 분할)
    # =========================================================================
    st.markdown("<h4>(3) CD 강종류별 판매현황</h4>", unsafe_allow_html=True)

    # [차트 1] 월별 CD 판매 추이
    col_l2_3a, col_r2_3a = st.columns([6, 4], gap="large")
    with col_l2_3a:
        st.markdown("<h4>[월별 CD 판매 추이 (산업/중국材 포함, B급 제외)]</h4>", unsafe_allow_html=True)
        try:
            df_cd = modules.create_df(this_year, current_month, load_data(st.secrets['sheets']['f_34']))
            df_plot_cd = df_cd.loc[('CD', ['일/탄', '합금강', '쾌삭강']), df_cd.columns[:6]]
            fig_cd = create_stacked_bar_chart(df_plot_cd, [('CD', '합금강'), ('CD', '쾌삭강'), ('CD', '일/탄')],
                                              ['#e54e2b', '#a5a5a5', '#3b4951'])
            # 🟢 끝선 동기화
            fig_cd.update_layout(margin=dict(l=40, r=0, t=20, b=20))
            st.plotly_chart(fig_cd, use_container_width=True, key="plot_cd_main")
        except Exception as e:
            st.error(f"CD 판매 추이 차트 생성 오류: {e}")
    with col_r2_3a:
        st.markdown("<h4 style='color:transparent'>[월별 CD 판매 추이]</h4>", unsafe_allow_html=True)
        display_memo('f_34', this_year, current_month, css_class="t2-chart-memo")

    # [차트 2] 월별 산업/중국재 CD 판매 추이
    col_l2_3b, col_r2_3b = st.columns([6, 4], gap="large")
    with col_l2_3b:
        st.markdown("<h4>[월별 산업/중국材 CD 판매 추이(B급 제외)]</h4>", unsafe_allow_html=True)
        try:
            df_cd_2 = modules.create_df(this_year, current_month, load_data(st.secrets['sheets']['f_35']))
            df_plot_cd2 = df_cd_2.loc[('산업/중국재', ['일/탄', '합금강']), df_cd_2.columns[:6]]
            fig_cd2 = create_stacked_bar_chart(df_plot_cd2, [('산업/중국재', '합금강'), ('산업/중국재', '일/탄')],
                                               ['#e54e2b', '#3b4951'])
            # 🟢 끝선 동기화
            fig_cd2.update_layout(margin=dict(l=40, r=0, t=20, b=20))
            st.plotly_chart(fig_cd2, use_container_width=True, key="plot_cd_industrial")
        except Exception as e:
            st.error(f"산업/중국재 CD 판매 추이 차트 생성 오류: {e}")
    with col_r2_3b:
        st.markdown("<h4 style='color:transparent'>[월별 산업/중국材 CD 판매 추이]</h4>", unsafe_allow_html=True)
        display_memo('f_35', this_year, current_month, css_class="t2-chart-memo")

    st.divider()

    # =========================================================================
    # (4) 비가공품 판매현황 (6:4 비율 좌우 분할)
    # =========================================================================
    col_l2_4, col_r2_4 = st.columns([6, 4], gap="large")
    with col_l2_4:
        st.markdown("<h4>(4) 비가공품 판매현황</h4>", unsafe_allow_html=True)
        st.markdown("<h4>[월별/품목별 비가공품 판매 추이]</h4>", unsafe_allow_html=True)
        try:
            df_process = modules.create_df(this_year, current_month, load_data(st.secrets['sheets']['f_36']),
                                           prev_month=5)
            df_plot_process = df_process.loc[('비가공', ['CHQ', 'BAR', '거래처 수']), df_process.columns[-7:]]
            trace_opt = {'name': ('비가공', '거래처 수'), 'color': '#ffc107', 'range': [-50, 120]}
            fig_process = create_stacked_bar_chart(df_plot_process, [('비가공', 'CHQ'), ('비가공', 'BAR')],
                                                   ['#e54e2b', '#3b4951'], trace_options=trace_opt,
                                                   yaxis_range=[0, 7000])
            # 🟢 끝선 동기화
            fig_process.update_layout(margin=dict(l=40, r=0, t=20, b=20))
            st.plotly_chart(fig_process, use_container_width=True, key="plot_process")
        except Exception as e:
            st.error(f"비가공품 판매 추이 차트 생성 오류: {e}")
    with col_r2_4:
        st.markdown("<h4 style='color:transparent'>(4) 비가공품 판매현황</h4>", unsafe_allow_html=True)
        st.markdown("<h4 style='color:transparent'>[월별/품목별 비가공품 판매 추이]</h4>", unsafe_allow_html=True)
        display_memo('f_36', this_year, current_month, css_class="t2-chart-memo")

    st.divider()

    # =========================================================================
    # (5) 동일거래처 매입매출현황 (6:4 비율 좌우 분할)
    # =========================================================================
    col_l2_5, col_r2_5 = st.columns([6, 4], gap="large")
    with col_l2_5:
        st.markdown("<h4>(5). 동일거래처 매입매출현황</h4>", unsafe_allow_html=True)
        st.markdown("<h4>[월별/품목별 임가공품 판매 추이]</h4>", unsafe_allow_html=True)
        try:
            df_same = modules.create_df(this_year, current_month, load_data(st.secrets['sheets']['f_37']))
            df_plot_same = df_same.loc[('매입매출', ['CHQ', 'BAR']), df_same.columns[:6]]
            fig_same = create_stacked_bar_chart(df_plot_same, [('매입매출', 'CHQ'), ('매입매출', 'BAR')],
                                                ['#e54e2b', '#3b4951'])
            # 🟢 끝선 동기화
            fig_same.update_layout(margin=dict(l=40, r=0, t=20, b=20))
            st.plotly_chart(fig_same, use_container_width=True, key="plot_same")
        except Exception as e:
            st.error(f"임가공품 판매 추이 차트 생성 오류: {e}")
    with col_r2_5:
        st.markdown("<h4 style='color:transparent'>(5). 동일거래처 매입매출현황</h4>", unsafe_allow_html=True)
        st.markdown("<h4 style='color:transparent'>[월별/품목별 임가공품 판매 추이]</h4>", unsafe_allow_html=True)
        display_memo('f_37', this_year, current_month, css_class="t2-chart-memo")

    st.divider()

    # =========================================================================
    # (6) PSI 지표 (6:4 비율 좌우 분할) -> 판매구성 표와 100% 동일하게 일치 교정
    # =========================================================================
    # ⚠️ 원본 고유 스타일 스펙 100% 유지
    psi_styles = [
        {'selector': 'table', 'props': [('border-collapse', 'collapse'), ('width', '100%'), ('font-size', '15px')]},
        {'selector': 'thead th', 'props': [('text-align', 'center'), ('font-weight', '700'),
                                           ('border', '1px solid #aaa'), ('background-color', 'white'),
                                           ('padding', '8px 16px'), ('font-size', '15px')]},
        {'selector': 'tbody td', 'props': [('border', '1px solid #aaa'), ('padding', '8px 16px'),
                                           ('text-align', 'right'), ('background-color', 'white'),
                                           ('font-size', '15px')]},
        {'selector': 'tbody th', 'props': [('border', '1px solid #aaa'), ('padding', '8px 16px'),
                                           ('background-color', 'white'), ('font-size', '15px')]},
    ]

    # 가로 폭 강제 일치 전용 CSS 선언
    custom_css = """<style>table { width: 100% !important; }</style>"""

    # -------------------------------------------------------------------------
    # 6-1. 매입매출 포함
    # -------------------------------------------------------------------------
    col_l2_6a, col_r2_6a = st.columns([6, 4], gap="large")

    with col_l2_6a:
        st.markdown("<h4>(6-1). PSI (입고, 판매, 재고) 지표 (매입매출 포함)</h4>", unsafe_allow_html=True)
        # 🟢 [수정사항] 단위를 표 바로 우측 어깨 위(오른쪽 위) 위치로 바짝 붙여 안착
        st.markdown(
            "<div style='text-align:right; font-size:15px; color:#666; margin-bottom:5px; font-weight:normal;'>[단위: 톤]</div>",
            unsafe_allow_html=True)

        try:
            # ⚠️ 원본 데이터 변수 및 처리 로직 100% 원본 그대로 유지
            df_psi = modules.update_psi_form(this_year, current_month, load_data(st.secrets['sheets']['f_38_1']))

            # 🟢 손익요약 탭 성공 공식을 그대로 적용하여 끝선을 완벽히 동기화
            styled_psi = (df_psi.style.set_table_styles(psi_styles))
            html_table_psi = styled_psi.to_html(escape=False)
            st.markdown(
                f"<div style='width: 100%; max-width: 100%; overflow-x: auto; display: block;'>{custom_css}{html_table_psi}</div>",
                unsafe_allow_html=True)

        except Exception as e:
            st.error(f"PSI(매입매출 포함) 지표 생성 오류: {e}")

    with col_r2_6a:
        st.markdown("<h4 style='color:transparent'>(6-1). PSI 지표 (매입매출 포함)</h4>", unsafe_allow_html=True)
        st.markdown("<div style='color:transparent; font-size:15px; margin-bottom:5px;'>[단위]</div>",
                    unsafe_allow_html=True)
        # 상단에서 통일 완료한 콤팩트 수치 버전으로 깔끔하게 매핑 호출
        display_memo('f_38_1', this_year, current_month)

    st.divider()

    # -------------------------------------------------------------------------
    # 6-2. 매입매출 제외
    # -------------------------------------------------------------------------
    col_l2_6b, col_r2_6b = st.columns([6, 4], gap="large")

    with col_l2_6b:
        st.markdown("<h4>(6-2). PSI (입고, 판매, 재고) 지표 (매입매출 제외)</h4>", unsafe_allow_html=True)
        # 🟢 [수정사항] 단위를 표 바로 우측 어깨 위(오른쪽 위) 위치로 바짝 붙여 안착
        st.markdown(
            "<div style='text-align:right; font-size:15px; color:#666; margin-bottom:5px; font-weight:normal;'>[단위: 톤]</div>",
            unsafe_allow_html=True)

        try:
            # ⚠️ 원본 데이터 변수 및 처리 로직 100% 원본 그대로 유지
            df_psi_2 = modules.update_psi_2_form(this_year, current_month, load_data(st.secrets['sheets']['f_38_2']))

            # 🟢 끝선 완벽 동기화 렌더링
            styled_psi2 = (df_psi_2.style.set_table_styles(psi_styles))
            html_table_psi2 = styled_psi2.to_html(escape=False)
            st.markdown(
                f"<div style='width: 100%; max-width: 100%; overflow-x: auto; display: block;'>{custom_css}{html_table_psi2}</div>",
                unsafe_allow_html=True)

        except Exception as e:
            st.error(f"PSI(매입매출 제외) 지표 생성 오류: {e}")

    with col_r2_6b:
        st.markdown("<h4 style='color:transparent'>(6-2). PSI 지표 (매입매출 제외)</h4>", unsafe_allow_html=True)
        st.markdown("<div style='color:transparent; font-size:15px; margin-bottom:5px;'>[단위]</div>",
                    unsafe_allow_html=True)
        display_memo('f_38_2', this_year, current_month)


# Footer
st.markdown("""
<style>.footer { bottom: 0; left: 0; right: 0; padding: 8px; text-align: center; font-size: 13px; color: #666666;}</style>
<div class="footer">ⓒ 2025 SeAH Special Steel Corp. All rights reserved.</div>
""", unsafe_allow_html=True)