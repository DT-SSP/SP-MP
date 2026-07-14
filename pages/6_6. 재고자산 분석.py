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

# 🟢 [오류 수정] modules.update_turnover_form 내부의 작은따옴표 포함 int 변환 버그("20'26") 우회 보정 로직
def fixed_update_turnover_form(year, month):
    file_name = st.secrets['sheets']['f_50']
    turnover = pd.read_csv(file_name, thousands=',')
    turnover['실적'] = round(turnover['실적']).astype(float)
    df = modules.create_turnover_form(year, month)

    for i in df.columns[:-2]:
        if '년말' in i[1]:
            yy = int('20' + i[1][:2].replace("'", ""))
            mm = 12
            temp = turnover[(turnover['연도'] == yy) & (turnover['월'] == mm)]
            vals = temp['실적'].values
            if len(vals) == 0:
                continue
            df.iloc[:-2, df.columns.get_loc(i)] = vals
        else:
            parts = i[1].replace('월', '').split('.')
            yy = int('20' + parts[0].replace("'", "")) # 💡 작은따옴표(')를 완전히 제거하여 "20'26" 에러 방지
            mm = int(parts[1])
            temp = turnover[(turnover['연도'] == yy) & (turnover['월'] == mm)]
            vals = temp['실적'].values
            if len(vals) == 0:
                continue
            df.iloc[:-2, df.columns.get_loc(i)] = vals

    for r in [0, 1, 3, 5, 7, 8]:
        df.iloc[r, :] = round(df.iloc[r, :] / 1_000_000, 0)
        df.iloc[9, :] = df.iloc[9, :] + df.iloc[r, :]
    for r in [2, 4, 6]:
        df.iloc[r, :] = round(df.iloc[r, :] / 1_000, 0)
        df.iloc[10, :] = df.iloc[10, :] + df.iloc[r, :]

    df.loc[:, ('전월대비', '증감')] = (df.iloc[:, -3] - df.iloc[:, -4]).values
    df[('전월대비', '증감률')] = round((df.iloc[:, -2] / df.iloc[:, -4]) * 100, 1)
    df = df.fillna(0)
    df.iloc[:, -1] = df.iloc[:, -1].astype(object).apply(lambda x: f"{x}%")
    return df

# 에러가 발생하는 모듈 함수를 안전한 수정본 함수로 강제 대체합니다.
modules.update_turnover_form = fixed_update_turnover_form


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
            .{css_class} .indent-0 {{ padding-left: 0px !important; padding-top: 3px; text-indent: -30px !important; font-size: 17px; font-weight: 400; }}
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


# 🟢 [정렬 고도화] 재고자산분석 전용 표 스타일러 (인덱스 완전 제거)
def display_styled_df(df, custom_css_align="", first_col_align="right"):
    """DataFrame에 스타일을 적용하여 가로폭을 꽉 채워 렌더링합니다. (인덱스 제거)"""
    styled_df = (
        df.style
        .format(lambda x: f"{x:,.0f}" if isinstance(x, (int, float)) and pd.notnull(x) else x)
        .set_properties(**{'text-align': 'right', 'font-family': 'Noto Sans KR'})
        .set_table_styles([
            {'selector': 'th, td',
             'props': [('border', '1px solid #aaa'), ('padding', '8px 16px'), ('font-size', '15px')]},
            {'selector': 'thead th', 'props': [('font-weight', '700')]},
            {'selector': 'tbody td:first-child', 'props': [('text-align', first_col_align)]},
            {'selector': 'table', 'props': [('border-collapse', 'collapse')]}
        ])
    )
    table_html = styled_df.to_html()

    # HTML에서 인덱스 컬럼 제거
    import re
    # <thead>에서 첫 번째 <th></th> 제거
    table_html = re.sub(r'<thead>.*?<tr>\s*<th[^>]*></th>\s*', '<thead>\n<tr>', table_html, flags=re.DOTALL)
    # <tbody>의 각 <tr>에서 첫 번째 <td>숫자</td> 제거
    table_html = re.sub(r'<tr>\s*<td[^>]*>\s*\d+\s*</td>\s*', '<tr>', table_html)

    st.markdown(
        f"<div style='width: 100%; max-width: 100%; overflow-x: auto; display: block;'>{custom_css_align}{table_html}</div>",
        unsafe_allow_html=True)


def display_inventory_chart(df_plot, bar_traces, scatter_trace, key):
    """설정을 받아 재고 현황 차트를 생성하고 화면에 표시합니다."""
    import plotly.graph_objects as go
    import streamlit as st
    import pandas as pd
    import numpy as np

    fig = go.Figure()

    # 1. 막대 그래프 (정상재, 매입매출만 표시)
    for trace in bar_traces:
        # 'y_column'이 있으면 사용, 없으면 'name' 사용
        data_key = trace.get('y_column') or trace.get('name')

        # 정상재, 매입매출 행만 추출
        if data_key in df_plot.index:
            y_val = df_plot.loc[data_key]
        else:
            y_val = pd.Series(0.0, index=df_plot.columns)

        # 안전하게 숫자로 변환
        y_val = pd.to_numeric(y_val, errors='coerce')
        y_val = np.nan_to_num(y_val, nan=0.0)

        # 정상재는 크기 13, 매입매출은 크기 10
        text_size = 13 if data_key == '정상재' else 10

        fig.add_trace(go.Bar(
            x=df_plot.columns,
            y=y_val,
            name=trace['name'],
            marker_color=trace['color'],
            text=y_val,
            texttemplate='%{text:,.0f}',
            textposition='inside',
            textfont=dict(color='white', size=text_size)
        ))

    # 2. 꺾은선 그래프 (장기재고)
    if scatter_trace:
        data_key = scatter_trace['name']

        if data_key in df_plot.index:
            scatter_y = df_plot.loc[data_key]
        else:
            scatter_y = pd.Series(0.0, index=df_plot.columns)

        scatter_y = pd.to_numeric(scatter_y, errors='coerce')
        scatter_y = np.nan_to_num(scatter_y, nan=0.0)

        fig.add_trace(go.Scatter(
            x=df_plot.columns,
            y=scatter_y,
            name=data_key,
            mode='lines+markers+text',
            marker=dict(size=8, color=scatter_trace['color']),
            line=dict(width=3, color=scatter_trace['color']),
            yaxis='y2',
            text=scatter_y,
            textposition="top center",
            textfont=dict(size=14, color=scatter_trace['color']),
            texttemplate='%{text:,.0f}',
            hovertemplate=f"{data_key}: %{{y}}<extra></extra>"
        ))

    # 3. 합계 값을 막대 상단에 표기
    if '정상재' in df_plot.index and '매입매출' in df_plot.index:
        total = df_plot.loc['정상재'] + df_plot.loc['매입매출']
        for col, val in total.items():
            fig.add_annotation(
                x=col, y=val, text=f"<b>{val:,.0f}</b>",
                showarrow=False, yshift=10, font=dict(color='black', size=15)
            )

    # 4. 레이아웃 설정
    fig.update_layout(
        height=400,
        font=dict(size=15),
        bargap=0.4,
        barmode='stack',
        plot_bgcolor='white',
        yaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
        xaxis=dict(showline=True, linewidth=1, linecolor='lightgrey', tickfont=dict(size=15)),
        legend=dict(orientation="h", yanchor="bottom", y=-0.35, xanchor="center", x=0.5, font=dict(size=15)),
        margin=dict(t=30, b=10, l=10, r=10)
    )

    # 5. 우측 Y축 (장기재고 범위)
    if scatter_trace:
        fig.update_layout(yaxis2=dict(
            overlaying='y',
            side='right',
            showticklabels=False,
            showgrid=False,
            zeroline=False,
            range=scatter_trace.get('range'),
            anchor='x'
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
#재고자산회전율
with t1:
    col_l6_1, col_r6_1 = st.columns([6, 4], gap="large")

    with col_l6_1:
        st.markdown("<h4>1) 재고자산 현황</h4>", unsafe_allow_html=True)
        st.markdown("<div style='text-align:right; font-size:13px; color:#666; margin-bottom:5px;'>[단위: 백만원, 톤]</div>",
                    unsafe_allow_html=True)

        try:
            df_turnover = modules.update_turnover_form(this_year, current_month)
            df_show = df_turnover.copy()
            df_show.columns = [f"{c[0]}{c[1]}" if c[0].strip() else c[1] for c in df_turnover.columns]

            # 🟢 컬럼명 정규화: 작은따옴표 추가 (중복 생성 에러 완전 해결)
            rename_map = {}
            for col in df_show.columns:
                col_clean = str(col).replace("'", "").strip()  # 기존에 존재하던 불필요한 따옴표 제거
                if '년말' in col_clean:
                    rename_map[col] = f"'{col_clean}"
                elif '년' in col_clean and '월' in col_clean:
                    rename_map[col] = f"'{col_clean}"
                elif '.' in col_clean and '월' in col_clean:
                    parts = col_clean.split('.')
                    year_part = parts[0]
                    month_part = parts[1].replace('월', '').strip()
                    rename_map[col] = f"'{year_part}년 {month_part}월"
                else:
                    rename_map[col] = col
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
                # 💡 [수정] 'thead th' 규칙에 'text-align': 'center !important'를 명시하여 컬럼명만 가운데 정렬로 지정했습니다.
                .set_table_styles([
                    {'selector': 'th, td',
                     'props': [('border', '1px solid #aaa'), ('padding', '8px 16px'), ('font-size', '15px')]},
                    {'selector': 'thead th',
                     'props': [('font-weight', '700'), ('text-align', 'center !important')]},
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
with t2:

    st.markdown("<h4>1) 연령별 재고현황</h4>", unsafe_allow_html=True)


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

        # 🔑 전월대비 컬럼 추가 함수

        def add_monthly_comparison(df):

            """26년 1월(마지막) 옆에 전월대비(26년1월-25년12월) 컬럼 추가"""

            df_new = df.copy()

            # 컬럼 길이가 충분하면 마지막과 마지막-1을 26y1m, 25y12m으로 간주

            if len(df_new.columns) >= 2:

                col_25y12m = df_new.columns[-2]  # 25년 12월 (마지막에서 2번째)

                col_26y1m = df_new.columns[-1]   # 26년 1월 (마지막)

                # 전월대비 계산 (26년 1월 - 25년 12월)

                comparison = df_new[col_26y1m] - df_new[col_25y12m]

                # 맨 끝에 추가

                df_new['전월대비'] = comparison

            return df_new

        # 각 데이터프레임에 전월대비 컬럼 추가

        df_1_display = add_monthly_comparison(df_1)

        df_2_display = add_monthly_comparison(df_2)

        df_3_display = add_monthly_comparison(df_3)

        # 🟢 컬럼명 정규화 함수
        def normalize_column_names(df):
            """컬럼명에 작은따옴표 추가 (전월대비 제외)"""
            new_cols = []
            for col in df.columns:
                col_str = str(col)
                if col_str == '전월대비':
                    new_cols.append(col_str)
                elif '년' in col_str and '월' in col_str:
                    if not col_str.startswith("'"):
                        # 26년 1월 → '26년 1월
                        if '.' in col_str:
                            parts = col_str.split('.')
                            new_cols.append(f"'{parts[0]}년 {parts[1]}월")
                        else:
                            new_cols.append(f"'{col_str}")
                    else:
                        new_cols.append(col_str)
                else:
                    new_cols.append(col_str)
            df.columns = new_cols
            return df

        # 각 데이터프레임에 컬럼명 정규화 적용
        df_1_display = normalize_column_names(df_1_display)
        df_2_display = normalize_column_names(df_2_display)
        df_3_display = normalize_column_names(df_3_display)

        # ── (1) 원재료 현황 구역 ──

        st.markdown("<h4>[원재료 현황]</h4>", unsafe_allow_html=True)
        st.markdown("<div style='text-align:right; font-size:13px; color:#666; margin-bottom:5px;'>[단위:톤]</div>",
                    unsafe_allow_html=True)

        col_l2_a, col_r2_a = st.columns([6, 4], gap="large")

        with col_l2_a:

            styled_df = (

                df_1_display.style

                .format(lambda x: f"{x:,.0f}" if isinstance(x, (int, float)) and pd.notnull(x) else x)

                .set_properties(**{'text-align': 'right', 'font-family': 'Noto Sans KR'})

                .set_table_styles([

                    {'selector': 'th, td',

                     'props': [('border', '1px solid #aaa'), ('padding', '8px 16px'), ('font-size', '15px')]},

                    {'selector': 'thead th',

                     'props': [('font-weight', '700'), ('text-align', 'center !important')]},

                    {'selector': 'table', 'props': [('border-collapse', 'collapse')]}

                ])

                .applymap(lambda x: 'color: red' if isinstance(x, (int, float)) and pd.notnull(x) and x < 0 else '',

                           subset=['전월대비'])

            )

            table_html = styled_df.to_html()

            st.markdown(

                f"<div style='width: 100%; max-width: 100%; overflow-x: auto; display: block;'>{t6_table_align_css}{table_html}</div>",

                unsafe_allow_html=True

            )

        with col_r2_a:

            scatter_trace_1 = {'name': '장기재고', 'color': '#ffc107', 'range': [0, 1500]}

            display_inventory_chart(df_1.loc[['정상재', '매입매출', '장기재고']], bar_traces_1, scatter_trace_1,

                                   key="raw_materials_chart")

        st.divider()

        # ── (2) 재공품 현황 구역 ──

        st.markdown("<h4>[재공품 현황]</h4>", unsafe_allow_html=True)
        st.markdown("<div style='text-align:right; font-size:13px; color:#666; margin-bottom:5px;'>[단위:톤]</div>",
                    unsafe_allow_html=True)

        col_l2_b, col_r2_b = st.columns([6, 4], gap="large")

        with col_l2_b:

            styled_df = (

                df_2_display.style

                .format(lambda x: f"{x:,.0f}" if isinstance(x, (int, float)) and pd.notnull(x) else x)

                .set_properties(**{'text-align': 'right', 'font-family': 'Noto Sans KR'})

                .set_table_styles([

                    {'selector': 'th, td',

                     'props': [('border', '1px solid #aaa'), ('padding', '8px 16px'), ('font-size', '15px')]},

                    {'selector': 'thead th',

                     'props': [('font-weight', '700'), ('text-align', 'center !important')]},

                    {'selector': 'table', 'props': [('border-collapse', 'collapse')]}

                ])

                .applymap(lambda x: 'color: red' if isinstance(x, (int, float)) and pd.notnull(x) and x < 0 else '',

                           subset=['전월대비'])

            )

            table_html = styled_df.to_html()

            st.markdown(

                f"<div style='width: 100%; max-width: 100%; overflow-x: auto; display: block;'>{t6_table_align_css}{table_html}</div>",

                unsafe_allow_html=True

            )

        with col_r2_b:

            scatter_trace_2 = {'name': '장기재고', 'color': '#ffc107', 'range': [0, 300]}

            display_inventory_chart(df_2.loc[['정상재', '매입매출', '장기재고']], bar_traces_1, scatter_trace_2,

                                   key="work_in_progress_chart")

        st.divider()

        # ── (3) 제품 현황 구역 ──

        st.markdown("<h4>[제품 현황]</h4>", unsafe_allow_html=True)

        st.markdown("<div style='text-align:right; font-size:13px; color:#666; margin-bottom:5px;'>[단위:톤]</div>",
                    unsafe_allow_html=True)

        col_l2_c, col_r2_c = st.columns([6, 4], gap="large")

        with col_l2_c:

            styled_df = (

                df_3_display.style

                .format(lambda x: f"{x:,.0f}" if isinstance(x, (int, float)) and pd.notnull(x) else x)

                .set_properties(**{'text-align': 'right', 'font-family': 'Noto Sans KR'})

                .set_table_styles([

                    {'selector': 'th, td',

                     'props': [('border', '1px solid #aaa'), ('padding', '8px 16px'), ('font-size', '15px')]},

                    {'selector': 'thead th',

                     'props': [('font-weight', '700'), ('text-align', 'center !important')]},

                    {'selector': 'table', 'props': [('border-collapse', 'collapse')]}

                ])

                .applymap(lambda x: 'color: red' if isinstance(x, (int, float)) and pd.notnull(x) and x < 0 else '',

                           subset=['전월대비'])

            )

            table_html = styled_df.to_html()

            st.markdown(

                f"<div style='width: 100%; max-width: 100%; overflow-x: auto; display: block;'>{t6_table_align_css}{table_html}</div>",

                unsafe_allow_html=True

            )

        with col_r2_c:

            scatter_trace_3 = {'name': '장기재고', 'color': '#ffc107', 'range': [0, 5000]}

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


# 🟢 [탭3, 탭4 전용] 표 아래 메모를 오른쪽으로 25px 밀어내는 독립 스타일시트
# =========================================================================
t6_shifted_memo_style = """
<style>
    .t6-shifted-memo { margin-bottom: 12px; padding-left: 25px !important; } /* 👈 25px 오른쪽 이동 */
    .t6-shifted-memo .indent-0 { padding-left: 0px !important; padding-top: 5px !important; text-indent: -30px !important; font-size: 17px; font-weight: normal; }
    .t6-shifted-memo .indent-1 { padding-left: 20px !important; padding-top: 3px !important; text-indent: -10px !important; font-size: 17px; }
    .t6-shifted-memo .indent-2 { padding-left: 40px !important; font-size: 17px; }
    .t6-shifted-memo .indent-3 { padding-left: 60px !important; font-size: 12px; }
    .t6-shifted-memo p { margin: 0.1rem 0 !important; line-height: 1.3 !important; }
</style>
"""
st.markdown(t6_shifted_memo_style, unsafe_allow_html=True)

# 3. 총 재고 및 장기재고 현황
# =========================================================================
with t3:
    st.markdown("<h4>1) 총 재고 및 장기재고 현황</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:right; font-size:13px; color:#666; margin-bottom:5px;'>[단위:톤]</div>",
                unsafe_allow_html=True)
    try:
        df_totals = pd.DataFrame({
            '원재료 합계': df_1.loc['합계'], '원재료_장기재고': df_1.loc['장기재고'],
            '재공품 합계': df_2.loc['합계'], '재공품_장기재고': df_2.loc['장기재고'],
            '제품 합계': df_3.loc['합계'], '제품_장기재고': df_3.loc['장기재고']
        }).T
        df_totals.loc['장기재고'] = df_totals.loc['원재료_장기재고'] + df_totals.loc['재공품_장기재고'] + df_totals.loc['제품_장기재고']

        # 🟢 컬럼명 정규화: 작은따옴표 추가
        new_cols = []
        for col in df_totals.columns:
            col_str = str(col)
            if '년' in col_str and '월' in col_str:
                if not col_str.startswith("'"):
                    if '.' in col_str:
                        parts = col_str.split('.')
                        new_cols.append(f"'{parts[0]}년 {parts[1]}월")
                    else:
                        new_cols.append(f"'{col_str}")
                else:
                    new_cols.append(col_str)
            else:
                new_cols.append(col_str)
        df_totals.columns = new_cols

        # 6:4 좌우 레이아웃 개시
        col_l3, col_r3 = st.columns([6, 4], gap="large")

        with col_l3:
            # 1. 먼저 60% 폭으로 표를 깔끔하게 그리고
            header_center_css = "<style>thead th { text-align: center !important; }</style>"

            # 💡 [수정] 소계 행 추가 (원재료 합계 + 재공품 합계 + 제품 합계)
            df_totals.loc['소계'] = df_totals.loc['원재료 합계'] + df_totals.loc['재공품 합계'] + df_totals.loc['제품 합계']

            # 💡 [수정] 표 표시 순서 변경
            display_styled_df(df_totals.loc[['원재료 합계', '재공품 합계', '제품 합계', '소계', '장기재고']],
                              custom_css_align=f"{t6_table_align_css}{header_center_css}")
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
                {'name': '원재료', 'color': '#3b4951', 'y_column': '원재료 합계'},
                {'name': '재공품', 'color': '#e54e2b', 'y_column': '재공품 합계'},
                {'name': '제품', 'color': '#a5a5a5', 'y_column': '제품 합계'}
            ]
            scatter_trace_total = {'name': '장기재고', 'color': '#ffc107', 'range': [0, 8000], 'y_column': '장기재고'}

            # 차트 그리기 함수 호출
            display_inventory_chart(df_totals.loc[['원재료 합계', '재공품 합계', '제품 합계', '장기재고']], bar_traces_total,
                                    scatter_trace_total, key="total_inventory_chart")

        st.divider()
    except Exception as e:
        st.error(f"총 재고 및 장기재고 표출 오류: {e}")

# 4. 등급별 재고현황 (탭 4: 재공품 최상단 배치 버전)

# =========================================================================
with t4:
    st.markdown("<h4>1) 등급별 재고현황</h4>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:right; font-size:13px; color:#666; margin-bottom:5px;'>[단위:톤]</div>",
                unsafe_allow_html=True)
    try:
        # 원본 데이터 로드 및 로직 원형 유지
        df_cls = modules.create_df(this_year, current_month, load_data(st.secrets['sheets']['f_52']), mean="False")

        # 🟢 컬럼명 정규화: 작은따옴표 추가
        new_cols = []
        for col in df_cls.columns:
            col_str = str(col)
            if '년' in col_str and '월' in col_str:
                if not col_str.startswith("'"):
                    if '.' in col_str:
                        parts = col_str.split('.')
                        new_cols.append(f"'{parts[0]}년 {parts[1]}월")
                    else:
                        new_cols.append(f"'{col_str}")
                else:
                    new_cols.append(col_str)
            else:
                new_cols.append(col_str)
        df_cls.columns = new_cols

        # 💡 [수정] 데이터 로드 후 즉시 KG → 톤 변환 (÷1000)
        df_cls = df_cls.iloc[:, 1:].apply(lambda x: x / 1000 if pd.api.types.is_numeric_dtype(x) else x, axis=0)
        df_cls.insert(0, '구분', [''] * len(df_cls))  # 구분 열 복원

        plot_rows = [('제품', 'B급'), ('제품', 'C급'), ('제품', 'D급'), ('제품', 'D2급'), ('제품', 'X급'), ('재공품', '재공품')]

        # 데이터 슬라이싱 및 인덱스 정제
        df_chart_cls = df_cls.loc[plot_rows, df_cls.columns[1:]].copy()
        df_table_cls = df_cls.loc[plot_rows, df_cls.columns[1:]].copy()

        # 💡 [수정] 제품합계 행 추가 (B급 + C급 + D급 + D2급 + X급)
        product_total = df_table_cls.loc[[('제품', 'B급'), ('제품', 'C급'), ('제품', 'D급'), ('제품', 'D2급'), ('제품', 'X급')]].sum()

        # 💡 [수정] pd.concat으로 제품합계 행 추가 (MultiIndex 호환)
        product_total_df = pd.DataFrame([product_total],
                                        index=pd.MultiIndex.from_tuples([('제품', '합계')], names=df_table_cls.index.names))
        df_table_cls = pd.concat([df_table_cls, product_total_df])
        df_chart_cls = pd.concat([df_chart_cls, product_total_df])

        # 💡 [수정] 행 순서 변경: B급 → C급 → D급 → D2급 → X급 → 제품합계 → 재공품
        plot_rows_new = [('제품', 'B급'), ('제품', 'C급'), ('제품', 'D급'), ('제품', 'D2급'), ('제품', 'X급'), ('제품', '합계'),
                         ('재공품', '재공품')]
        df_chart_cls = df_chart_cls.loc[plot_rows_new]
        df_table_cls = df_table_cls.loc[plot_rows_new]

        # 차트용 데이터프레임의 멀티인덱스를 단일 문자열로 완전 변환
        chart_labels = [f"{r[0]}({r[1]})" if r[1] != '합계' else f"{r[0]}({r[1]})" for r in df_chart_cls.index]
        df_chart_cls.index = chart_labels

        # 6:4 좌우 레이아웃 구동
        col_l4, col_r4 = st.columns([6, 4], gap="large")

        with col_l4:
            labels = [f"{r[0]} ({r[1]})" for r in df_table_cls.index]
            df_table_cls.index = labels
            df_table_cls.index.name = '구분'

            df_table_cls = df_table_cls.reset_index()
            df_table_cls = df_table_cls.reset_index(drop=True)

            # 🔑 display_styled_df 대신 직접 HTML로 렌더링
            styled_df = (
                df_table_cls.style
                .hide(axis='index')
                .format(lambda x: f"{x:,.0f}" if isinstance(x, (int, float)) and pd.notnull(x) else x)
                # 기본적으로 모든 데이터를 오른쪽 정렬로 지정 (숫자 정렬)
                .set_properties(**{'text-align': 'right', 'font-family': 'Noto Sans KR'})
                # 💡 [수정] '구분' 열 데이터만 왼쪽 정렬로 명확히 지정
                .set_properties(subset=['구분'], **{'text-align': 'left'})
                .set_table_styles([
                    {'selector': 'th, td',
                     'props': [('border', '1px solid #aaa'), ('padding', '8px 16px'), ('font-size', '15px')]},
                    # 컬럼명 헤더 스타일 (가운데 정렬 지정)
                    {'selector': 'thead th',
                     'props': [('font-weight', '700'), ('text-align', 'center !important')]},
                    {'selector': 'table', 'props': [('border-collapse', 'collapse')]}
                ])
            )
            table_html = styled_df.to_html()
            st.markdown(
                f"<div style='width: 100%; max-width: 100%; overflow-x: auto; display: block;'>{t6_table_align_css}{table_html}</div>",
                unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # [우측 이동 연동] 탭4 역시 전용 클래스(t6-shifted-memo) 주입하여 표 하단 정렬선 일치
            try:
                if 'f_55' in st.secrets.get('memos', {}):
                    display_memo('f_55', this_year, current_month, css_class="t6-shifted-memo")
            except:
                pass

        with col_r4:
            # 🟢 [수정 완료] 재공품이 가장 나중에 그려져서 막대 꼭대기(맨 위)에 쌓이도록 순서를 맨 뒤로 바꿨습니다.
            bar_traces_cls = [
                {'name': '제품(B급)', 'color': '#3b4951'},
                {'name': '제품(C급)', 'color': '#e54e2b'},
                {'name': '제품(D급)', 'color': '#a5a5a5'},
                {'name': '제품(D2급)', 'color': '#D5a5a5'},
                {'name': '제품(X급)', 'color': '#8faadc'},
                {'name': '재공품(재공품)', 'color': '#70AD47'}
            ]

            scatter_trace_cls = None



            display_inventory_chart(df_chart_cls, bar_traces_cls, scatter_trace_cls, key="grade_inventory_chart")

        st.divider()
    except Exception as e:
        st.error(f"등급별 재고현황 표출 오류: {e}")

# Footer
st.markdown("""
<style>.footer { bottom: 0; left: 0; right: 0; padding: 8px; text-align: center; font-size: 13px; color: #666666;}</style>
<div class="footer">ⓒ 2026 SeAH Special Steel Corp. All rights reserved.</div>
""", unsafe_allow_html=True)