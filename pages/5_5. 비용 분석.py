import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
import plotly.graph_objects as go
import modules
import matplotlib.pyplot as plt
import numpy as np
import matplotlib as mpl
import plotly.graph_objects as go


warnings.filterwarnings('ignore')
st.set_page_config(layout="wide", initial_sidebar_state="expanded")

@st.cache_data(ttl=1800)
def load_data(url):
    data = pd.read_csv(url, thousands=',')
    data['실적'] = round(data['실적']).astype(float)
    data['월'] = data['월'].astype(str).apply(lambda x: x if '월' in x else x + '월')
    data = data.fillna('')
    return data

modules.create_sidebar()
this_year = st.session_state['year']
current_month = st.session_state['month']


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


def display_styled_df(df, styles=None, highlight_cols=None, fmt_int=True,align="left"):
    """
    인덱스를 reset_index()하지 않고 그대로 렌더링합니다.
    - Pandas Styler가 인덱스 셀에 th.row_heading.level* 클래스를 붙여줍니다.
    - highlight_cols: 배경 강조할 컬럼 라벨 리스트(문자열). 예) ['24년 월평균','25년 목표','합계','월평균']
    - fmt_int=True: 숫자형을 천단위 콤마로 표시
    - styles: set_table_styles에 그대로 전달할 추가 CSS [{selector:'...', props:[('k','v'), ...]}]
    """
    styled = df.style

    # 숫자 포맷
    if fmt_int:
        styled = styled.format(
            lambda x: f"{x:,.0f}"
            if isinstance(x, (int, float, np.integer, np.floating)) and pd.notnull(x)
            else x
        )

    # 강조 컬럼 (배경)
    if highlight_cols:
        hi = set(map(str, highlight_cols))
        def _hi(col):
            return ['background-color: #f0f0f0'] * len(col) if str(col.name) in hi else [''] * len(col)
        styled = styled.apply(_hi, axis=0)

    # 기본 스타일
    base_css = [
        {'selector': 'table', 'props': [('border-collapse', 'separate'), ('border-spacing', '0')]},
        {'selector': 'th, td', 'props': [('border', '1px solid #cfcfcf'), ('padding', '6px 8px')]},
        {'selector': 'thead th', 'props': [('border-bottom', '2px solid #888'), ('text-align', 'center')]},
        {'selector': 'th.row_heading', 'props': [('background-color', '#fff')]}
    ]
    if styles:
        base_css.extend(styles)
    styled = styled.set_table_styles(base_css)

    # 공통 글꼴/정렬
    styled = styled.set_properties(**{'text-align': 'right', 'font-family': 'Noto Sans KR'})

    # 렌더링
    html = styled.to_html()  # 인덱스는 그대로(th.row_heading.level*)
    if align == "center":
        wrapper = f"<div style='display:flex; justify-content:center;'>{html}</div>"
    elif align == "right":
        wrapper = f"<div style='display:flex; justify-content:flex-end;'>{html}</div>"
    else:  # left
        wrapper = f"<div style='display:flex; justify-content:flex-start;'>{html}</div>"

    st.markdown(wrapper, unsafe_allow_html=True)

    
def nudge_texts_to_avoid_overlap(ax, min_sep_px=10):
    """
    같은 x 지점에 있는 텍스트들이 겹치지 않도록 세로로 최소 min_sep_px 픽셀 간격 확보.
    ax 안의 모든 Text 객체를 스캔해서 조정합니다.
    """
    import numpy as np
    import matplotlib.transforms as mtransforms

    # x별 텍스트 분류
    by_x = {}
    texts = [t for t in ax.texts if t.get_visible()]
    for t in texts:
        x, y = t.get_position()
        by_x.setdefault(float(x), []).append(t)

    # 픽셀 ↔ 데이터 변환용 스케일
    ylim = ax.get_ylim()
    height_px = ax.bbox.height if ax.bbox.height > 0 else 1
    data_per_px = (ylim[1] - ylim[0]) / height_px
    min_sep_data = min_sep_px * data_per_px

    # x별로 y 기준 정렬 후 위로 조금씩 띄우기
    for x, ts in by_x.items():
        # y(데이터 좌표) 기준 오름차순 정렬
        ts.sort(key=lambda t: t.get_position()[1])
        last_y = -np.inf
        for t in ts:
            x0, y0 = t.get_position()
            y_new = max(y0, last_y + min_sep_data)  # 최소 간격 확보
            if y_new != y0:
                t.set_position((x0, y_new))
            last_y = y_new

    # 조정 후 다시 그리도록
    ax.figure.canvas.draw_idle()


#------------------------------------------------------------------------------------------------

custom_css = """
<style>
table {
    width: 100%;
    border-collapse: collapse;
    font-family: 'Noto Sans KR', sans-serif;
    font-size: 13px;
    line-height: 1.2;  /* 행 높이 줄임 */
}
th, td {
    padding: 3px 6px;  /* 세로 여백 줄임 */
    text-align: right;
    border: 1px solid #ddd;
    vertical-align: middle;
    word-break: keep-all;
    white-space: pre-wrap;
}
thead {
    background-color: #f2f2f2;
    font-weight: bold;
}
.row_heading { display: none !important; }
.blank { display: none !important; }
</style>
"""

#------------------------------------------------------------------------------------------------

# 화면 구성
st.markdown('<div class="centered">', unsafe_allow_html=True)
st.markdown(f"## {this_year}년 {current_month}월 비용 분석")
# t1, t2, t3, t4, t5, t6, t7 = st.tabs(['사용량 원단위 추이_포항', '사용량 원단위 추이_충주1','사용량 원단위 추이_충주2','단가 추이', '월 평균 클레임 지급액','당월 클레임 내역','영업외 비용 내역'])
t1, t2, t3= st.tabs(['사용량 원단위 추이', '클레임 현황','영업외 비용 내역'])
st.divider()
#------------------------------------------------------------------------------------------------

# =========================
# 사용량 원단위 추이_포항
# =========================


with t1:
    display_memo('f_43', this_year, current_month)

    st.divider()

    st.markdown("### 1) 부재료 사용량 원단위 (포항)", unsafe_allow_html=True)

    file_name = st.secrets["sheets"]["f_43"]

    @st.cache_data(ttl=600)
    def load_submat_df(path: str) -> pd.DataFrame:
        # 쉼표 천단위 잘 읽히도록 thousands="," 적용
        return pd.read_csv(path, encoding="utf-8", thousands=",")

    df_src = load_submat_df(file_name)

    # ===== 표 생성 (2월 ~ 데이터의 마지막 월) =====
    df_table = modules.create_material_usage_table_pohang(
        year=this_year,
        month=current_month,
        data=df_src,
        window=12,        # 최근 12개월
        round_digits=1,   # 소수 1자리
    )




    df_show = df_table.reset_index()
    df_show.columns.name = None

    month_cols = df_show.columns[1:]          #

    df_show[month_cols] = df_show[month_cols].apply(
        pd.to_numeric, errors="coerce"
    )

    numeric_cols = month_cols

    styled = (
        df_show.style

        .format({col: "{:.1f}" for col in numeric_cols}, na_rep="-")
        .hide(axis="index")

        # 1) 첫 번째 열(포항) 바디 셀 강조
        .set_properties(
            subset=[df_show.columns[0]],
            **{
                "text-align": "left",
                "font-weight": "600",
                "background-color": "#f0f0f0",
            }
        )

        # 2) 헤더 셀(포항)도 동일 계열로 강조
        .set_table_styles([
            {
                "selector": "th.col_heading.level0.col0",  # 첫 번째 컬럼 헤더
                "props": [
                    ("background-color", "#f0f0f0"),
                    ("font-weight", "700"),
                    ("text-align", "center"),
                ],
            },
            {
                "selector": "th.col_heading",  # 다른 헤더는 가운데 정렬 유지
                "props": [("text-align", "center")],
            },
        ])

        # 3) 숫자 컬럼 가운데 정렬
        .set_properties(
            subset=numeric_cols,
            **{"text-align": "center"}
        )
    )

    st.markdown(
        f"<div style='display:flex; justify-content:left'>{styled.to_html(index=False)}</div>",
        unsafe_allow_html=True
    )


    # st.divider()
    unit = "<div style='text-align:left; font-size:15px; color:#000000;'>※ 사용량원단위 : 부재료사용량/공정처리량</div>"
    st.markdown(unit, unsafe_allow_html=True)


    try:
        mpl.rcParams['font.family'] = 'Malgun Gothic'  # Windows 한글
        mpl.rcParams['axes.unicode_minus'] = False
    except Exception:
        pass



    # ===== 그래프용 데이터: df_table 그대로 사용 (NaN 컬럼 삭제 X) =====
    df_plot = df_table.copy()
    months  = list(df_plot.columns)   # x축 라벨
    x       = months

    fig = go.Figure()

    # ----- 본 그래프 -----
    for item_name in df_plot.index:
        # 각 항목의 월별 값
        y = pd.to_numeric(df_plot.loc[item_name], errors="coerce").values.astype(float)

        # 라벨 겹침 완화
        textpos = ["top center" if i % 2 == 0 else "bottom center" for i in range(len(y))]

        fig.add_trace(go.Scatter(
            x=x,
            y=y,
            name=item_name,
            mode="lines+markers+text",
            line=dict(width=2),
            marker=dict(size=6),
            text=[f"{v:.1f}" if np.isfinite(v) else "" for v in y],  # NaN이면 라벨 공백
            textposition=textpos,
            textfont=dict(size=11),
            hovertemplate="값=%{y:.1f}<extra></extra>",
            connectgaps=False,   
        ))

    fig.update_traces(line=dict(width=3.5))

    # ----- 레이아웃 / 축 설정 -----
    fig.update_layout(margin=dict(r=120))

    fig.update_layout(
        title="[포항]",
        legend=dict(
            orientation="v",
            x=1.02, y=0.5,
            xanchor="left", yanchor="middle",
            bgcolor="rgba(255,255,255,0.85)",
            borderwidth=1,
            font=dict(size=13),
            itemsizing="constant",
            itemwidth=90,
        ),
    )

    fig.update_xaxes(
        type="category",         
        categoryorder="array",   
        categoryarray=x,
        tickmode="array",
        tickvals=x,
        ticktext=x,
        tickangle=-45,           
        showgrid=False,
    )

    fig.update_yaxes(
        title_text=None,
        showticklabels=False,
        zeroline=False,
        showgrid=True,
        gridcolor="rgba(0,0,0,0.18)",
    )

    st.plotly_chart(fig, use_container_width=True)




    st.divider()


    st.markdown("### 2) 부재료 사용량 원단위 (충주1)", unsafe_allow_html=True)

    file_name = st.secrets["sheets"]["f_43"]

    @st.cache_data(ttl=600)
    def load_submat_df(path: str) -> pd.DataFrame:
        # 쉼표 천단위 잘 읽히도록 thousands="," 적용
        return pd.read_csv(path, encoding="utf-8", thousands=",")

    df_src = load_submat_df(file_name)

    # ===== 표 생성 : 기준 연/월 포함 최근 12개월 =====
    df_table = modules.create_material_usage_table_chungju1(
        year=this_year,
        month=current_month,
        data=df_src,
        window=12,        # 기준월 포함 12개월
        round_digits=1,   # 소수 첫째자리 반올림
    )

    # ➜ 인덱스를 컬럼으로 승격
    df_show = df_table.reset_index()
    df_show.columns.name = None


    month_cols = df_show.columns[1:]
    df_show[month_cols] = df_show[month_cols].apply(pd.to_numeric, errors="coerce")
    numeric_cols = month_cols

    styled = (
        df_show.style
        .format({col: "{:.1f}" for col in numeric_cols}, na_rep="-")
        .hide(axis="index")

        # 1) 첫 번째 열(충주1) 바디 셀 강조
        .set_properties(
            subset=[df_show.columns[0]],
            **{
                "text-align": "left",
                "font-weight": "600",
                "background-color": "#f0f0f0",
            }
        )

        # 2) 헤더 셀(충주1)도 동일 계열로 강조
        .set_table_styles([
            {
                "selector": "th.col_heading.level0.col0",  # 첫 번째 컬럼 헤더
                "props": [
                    ("background-color", "#f0f0f0"),
                    ("font-weight", "700"),
                    ("text-align", "center"),
                ],
            },
            {
                "selector": "th.col_heading",  # 다른 헤더는 가운데 정렬 유지
                "props": [("text-align", "center")],
            },
        ])

        # 3) 숫자 컬럼 가운데 정렬
        .set_properties(subset=numeric_cols, **{"text-align": "center"})
    )

    st.markdown(
        f"<div style='display:flex; justify-content:left'>{styled.to_html(index=False)}</div>",
        unsafe_allow_html=True
    )

    # st.divider()
    unit = "<div style='text-align:left; font-size:15px; color:#000000;'>※ 사용량원단위 : 부재료사용량/공정처리량</div>"
    st.markdown(unit, unsafe_allow_html=True)

    # ===== 그래프 =====
    try:
        mpl.rcParams['font.family'] = 'Malgun Gothic'  # Windows 한글
        mpl.rcParams['axes.unicode_minus'] = False
    except Exception:
        pass

    df_plot = df_table.copy()
    months  = list(df_plot.columns)      # x축 라벨
    x       = months                     # 카테고리형 x

    fig = go.Figure()

    # ----- 본 그래프: 라인+마커+값 라벨 -----
    for item_name in df_plot.index:
        y = pd.to_numeric(df_plot.loc[item_name], errors="coerce").values.astype(float)

        # 라벨 겹침 완화: 위/아래 교차 배치
        textpos = ["top center" if i % 2 == 0 else "bottom center" for i in range(len(y))]

        fig.add_trace(go.Scatter(
            x=x, y=y, name=item_name,
            mode="lines+markers+text",
            line=dict(width=2),
            marker=dict(size=6),
            text=[f"{v:.1f}" if np.isfinite(v) else "" for v in y],
            textposition=textpos,
            textfont=dict(size=11),
            hovertemplate="값=%{y:.1f}<extra></extra>",
            connectgaps=False,   # NaN 구간은 끊어서 표시
        ))

    fig.update_traces(line=dict(width=3.5))

    # ----- 레이아웃 (오른쪽 범례) -----
    fig.update_layout(margin=dict(r=120))

    fig.update_layout(
        title="[충주1]",
        legend=dict(
            orientation="v",
            x=1.02, y=0.5,
            xanchor="left", yanchor="middle",
            bgcolor="rgba(255,255,255,0.85)",
            borderwidth=1,
            font=dict(size=13),
            itemsizing="constant",
            itemwidth=90,
        ),
    )

    # x축: 카테고리 라벨 그대로(값 없어도 전부 표시)
    fig.update_xaxes(
        type="category",
        categoryorder="array",
        categoryarray=x,
        tickmode="array",
        tickvals=x,
        ticktext=x,
        tickangle=-45,
        showgrid=False,
    )

    # y축: 라벨 숨김 + 옅은 그리드
    fig.update_yaxes(
        showticklabels=False,
        zeroline=False,
        showgrid=True,
        gridcolor="rgba(0,0,0,0.18)",
    )


    all_vals = pd.to_numeric(df_plot.values.ravel(), errors="coerce").astype(float)
    finite = np.isfinite(all_vals)
    if finite.any():
        ymin = float(np.nanmin(all_vals[finite]))
        ymax = float(np.nanmax(all_vals[finite]))
        pad = max((ymax - ymin) * 0.15, 1e-9)
        fig.update_yaxes(range=[ymin - pad, ymax + pad])

    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    st.markdown("### 3) 부재료 사용량 원단위 (충주2)", unsafe_allow_html=True)

    file_name = st.secrets["sheets"]["f_43"]

    @st.cache_data(ttl=600)
    def load_submat_df(path: str) -> pd.DataFrame:
        # 쉼표 천단위 잘 읽히도록 thousands="," 적용
        return pd.read_csv(path, encoding="utf-8", thousands=",")

    df_src = load_submat_df(file_name)

    # ===== 표 생성 : 기준 연/월 포함 최근 12개월 =====
    df_table = modules.create_material_usage_table_chungju2(
        year=this_year,
        month=current_month,
        data=df_src,
        window=12,        # 기준월 포함 12개월
        round_digits=1,   # 소수 첫째자리 반올림
    )

    # ➜ 인덱스를 컬럼으로 승격
    df_show = df_table.reset_index()
    df_show.columns.name = None


    month_cols = df_show.columns[1:]
    df_show[month_cols] = df_show[month_cols].apply(pd.to_numeric, errors="coerce")
    numeric_cols = month_cols

    styled = (
        df_show.style
        .format({col: "{:.1f}" for col in numeric_cols}, na_rep="-")
        .hide(axis="index")

        # 1) 첫 번째 열(충주2) 바디 셀 강조
        .set_properties(
            subset=[df_show.columns[0]],
            **{
                "text-align": "left",
                "font-weight": "600",
                "background-color": "#f0f0f0",
            }
        )

        # 2) 헤더 셀(충주2)도 동일 계열로 강조
        .set_table_styles([
            {
                "selector": "th.col_heading.level0.col0",  # 첫 번째 컬럼 헤더
                "props": [
                    ("background-color", "#f0f0f0"),
                    ("font-weight", "700"),
                    ("text-align", "center"),
                ],
            },
            {
                "selector": "th.col_heading",  # 다른 헤더는 가운데 정렬 유지
                "props": [("text-align", "center")],
            },
        ])

        # 3) 숫자 컬럼 가운데 정렬
        .set_properties(subset=numeric_cols, **{"text-align": "center"})
    )

    st.markdown(
        f"<div style='display:flex; justify-content:left'>{styled.to_html(index=False)}</div>",
        unsafe_allow_html=True
    )

    # st.divider()
    unit = "<div style='text-align:left; font-size:15px; color:#000000;'>※ 사용량원단위 : 부재료사용량/공정처리량</div>"
    st.markdown(unit, unsafe_allow_html=True)

    # ===== 그래프 =====
    try:
        mpl.rcParams['font.family'] = 'Malgun Gothic'  # Windows 한글
        mpl.rcParams['axes.unicode_minus'] = False
    except Exception:
        pass

    # 준비: df_table 그대로 사용 (NaN 컬럼 삭제 X)
    df_plot = df_table.copy()                     
    months  = list(df_plot.columns)               # x축 카테고리
    x       = months

    fig = go.Figure()

    # ----- 본 그래프: 라인 + 마커 + 값 라벨 -----
    for i, item_name in enumerate(df_plot.index):
        y = pd.to_numeric(df_plot.loc[item_name], errors="coerce").values.astype(float)

        # 라벨 겹침 완화: 위/아래 교차
        textpos = ["top center" if j % 2 == 0 else "bottom center" for j in range(len(y))]

        fig.add_trace(go.Scatter(
            x=x, y=y, name=item_name,
            mode="lines+markers+text",
            line=dict(width=2),
            marker=dict(size=6),
            text=[f"{v:.1f}" if np.isfinite(v) else "" for v in y],
            textposition=textpos,
            textfont=dict(size=11),
            hovertemplate="값=%{y:.1f}<extra></extra>",
            connectgaps=False,   # NaN 구간은 끊어서 표시
        ))
    
    fig.update_traces(line=dict(width=3.5))

    # ----- 레이아웃 (오른쪽 범례) -----
    fig.update_layout(margin=dict(r=120))

    fig.update_layout(
        title="[충주2]",
        legend=dict(
            orientation="v",
            x=1.02, y=0.5,              # x>1 => 플롯 영역 '바깥' 오른쪽
            xanchor="left", yanchor="middle",
            bgcolor="rgba(255,255,255,0.85)",
            borderwidth=1,
            font=dict(size=13),
            itemsizing="constant",
            itemwidth=90,
        )
    )

    # x축: 카테고리 축으로 고정 (값 없어도 라벨은 전부 보이게)
    fig.update_xaxes(
        type="category",
        categoryorder="array",
        categoryarray=x,
        tickmode="array",
        tickvals=x,
        ticktext=x,
        tickangle=-45,
        showgrid=False,
    )

    # y축: 눈금 라벨 숨김 + 옅은 그리드 + 패딩
    fig.update_yaxes(
        showticklabels=False,
        zeroline=False,
        showgrid=True,
        gridcolor="rgba(0,0,0,0.18)",
    )

    all_vals = pd.to_numeric(df_plot.values.ravel(), errors="coerce").astype(float)
    finite = np.isfinite(all_vals)
    if finite.any():
        ymin = float(np.nanmin(all_vals[finite]))
        ymax = float(np.nanmax(all_vals[finite]))
        pad = max((ymax - ymin) * 0.15, 1e-9)
        fig.update_yaxes(range=[ymin - pad, ymax + pad])

    # Streamlit 출력
    st.plotly_chart(fig, use_container_width=True)


    st.divider()


    st.markdown("### 4) 단가 추이", unsafe_allow_html=True)

    file_name = st.secrets["sheets"]["f_46"]

    @st.cache_data(ttl=600)
    def load_submat_df(path: str) -> pd.DataFrame:
        return pd.read_csv(path, encoding="utf-8", thousands=",")

    df_src = load_submat_df(file_name)

    # ===== 표 생성 =====
    df_table = modules.create_material_usage_table_unit_price(
        year=this_year,
        month=current_month,
        data=df_src,
        # start_month=2,
        window=12,
        round_digits=1,   
    )

    # ➜ 인덱스를 컬럼으로 승격 (헤더 한 줄)
    df_show = df_table.reset_index()
    df_show.columns.name = None

    numeric_cols = df_show.select_dtypes(include="number").columns
    first_col = df_show.columns[0]

    # ===== 표 스타일  =====
    styled = (
        df_show.style
        .format({col: "{:.1f}" for col in numeric_cols}, na_rep="-")
        .hide(axis="index")
        # 1) 첫 번째 열 강조 
        .set_properties(
            subset=[first_col],
            **{
                "text-align": "left",
                "font-weight": "600",
                "background-color": "#f0f0f0",
                "white-space": "nowrap",
            }
        )
        # 2) 헤더 스타일 
        .set_table_styles([
            {
                "selector": "th.col_heading.level0.col0",
                "props": [
                    ("background-color", "#f0f0f0"),
                    ("font-weight", "700"),
                    ("text-align", "center")
                ],
            },
            {"selector": "th.col_heading", "props": [("text-align", "center")]},
        ])
        # 3) 숫자 컬럼 정렬 
        .set_properties(subset=[c for c in df_show.columns if c in numeric_cols], **{"text-align": "center"})
    )

    st.markdown(
        f"<div style='display:flex; justify-content:left'>{styled.to_html(index=False)}</div>",
        unsafe_allow_html=True
    )




    # ----- 그래프 불러오기 -----
    df_plot = df_table.copy()
    df_plot = df_plot.apply(pd.to_numeric, errors="coerce")


    months = df_plot.columns.tolist()   # 예: ['24.12','25.01', ...]
    x = months

    from plotly.subplots import make_subplots
    import plotly.graph_objects as go
    import numpy as np

    # 질소 / 전력 vs 나머지 네 개 구분
    n2_label, pw_label = "질소(천㎥)", "전력(천kwh)"
    others = [idx for idx in df_plot.index if idx not in {n2_label, pw_label}]

    # --- 데이터 ---
    y_n2 = pd.to_numeric(df_plot.loc[n2_label], errors="coerce").values.astype(float)
    y_pw = pd.to_numeric(df_plot.loc[pw_label], errors="coerce").values.astype(float)
    others_vals = (
        pd.to_numeric(df_plot.loc[others].values.ravel(), errors="coerce").astype(float)
        if len(others) else np.array([], dtype=float)
    )

    def rng(v, pad_ratio=0.5):
        f = np.isfinite(v)
        if not f.any():
            return [0.0, 1.0]
        vmin, vmax = float(np.nanmin(v[f])), float(np.nanmax(v[f]))
        pad = max((vmax - vmin) * pad_ratio, 1e-9)
        return [vmin - pad, vmax + pad]

    # 위 패널(나머지 4개), 아래 패널(질소/전력) 각각 y축 범위
    y1_range = rng(others_vals)
    y2_range = rng(np.r_[y_n2[np.isfinite(y_n2)], y_pw[np.isfinite(y_pw)]])

    # --- 2행 1열 서브플롯: x축 공유 ---
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.80, 0.25],
    )

    # (1) 위: 질소/전력 뺀 나머지 네 개
    base_colors = ["#1f77b4","#ff7f0e","#939393","#bcbd22","#000080","#009900"]
    for i, name in enumerate(others):
        y = pd.to_numeric(df_plot.loc[name], errors="coerce").values.astype(float)
        fig.add_trace(
            go.Scatter(
                x=x, y=y, name=name,
                mode="lines+markers+text",
                line=dict(width=2, color=base_colors[i % len(base_colors)]),
                marker=dict(size=6),
                texttemplate="%{y:.1f}",
                textposition="top center",
                textfont=dict(size=10),
                hovertemplate="값=%{y:.1f}<extra></extra>",
            ),
            row=1, col=1
        )

    # (2) 아래: 질소 / 전력
    fig.add_trace(
        go.Scatter(
            x=x, y=y_n2, name=n2_label,
            mode="lines+markers+text",
            line=dict(width=2.4, color="#FFD400"), marker=dict(size=7),
            texttemplate="%{y:.1f}",
            textposition="top center",
            textfont=dict(size=10),
            hovertemplate="값=%{y:.1f}<extra></extra>",
        ),
        row=2, col=1
    )
    fig.add_trace(
        go.Scatter(
            x=x, y=y_pw, name=pw_label,
            mode="lines+markers+text",
            line=dict(width=2.4, color="#BB2649"), marker=dict(size=7),
            texttemplate="%{y:.1f}",
            textposition="top center",
            textfont=dict(size=10),
            hovertemplate="값=%{y:.1f}<extra></extra>",
        ),
        row=2, col=1
    )

    fig.update_traces(line=dict(width=3.5))
    fig.update_layout(uniformtext_minsize=9, uniformtext_mode="hide")

    # --- 레이아웃/축/범례 ---
    fig.update_layout(margin=dict(r=120))
    fig.update_layout(
        legend=dict(
            orientation="v",
            x=1.02, y=0.5,
            xanchor="left", yanchor="middle",
            bgcolor="rgba(255,255,255,0.85)",
            borderwidth=1,
            font=dict(size=13),
            itemsizing="constant",
            itemwidth=90,
        )
    )

    for r in (1, 2):
        fig.update_xaxes(
            type="category",
            categoryorder="array",
            categoryarray=x,
            tickmode="array",
            tickvals=x,
            ticktext=x,
            tickangle=-45,
            showgrid=False,
            row=r, col=1,
        )

    fig.update_yaxes(
        range=y1_range,
        showticklabels=False,
        zeroline=False,
        showgrid=True,
        gridcolor="rgba(0,0,0,0.18)",
        row=1, col=1,
    )
    fig.update_yaxes(
        range=y2_range,
        showticklabels=False,
        zeroline=False,
        showgrid=True,
        gridcolor="rgba(0,0,0,0.18)",
        row=2, col=1,
    )

    st.plotly_chart(fig, use_container_width=True)

    display_memo('f_46', this_year, current_month)


with t2:
    
    st.markdown(f"###  1) 월 평균 클레임 지급액</h4>", unsafe_allow_html=True)

    # 1) 모듈에서 연도별 피벗 데이터 가져오기
    pivot = modules.update_monthly_claim_form()   # index: 구분2, columns: 연도(int)

    # 2) 선택 연도(this_year) 기준으로 전전전/전전/전/현 4개 연도 결정
    base_year = int(this_year)
    target_years = [base_year - 3, base_year - 2, base_year - 1, base_year]
    col_labels  = [f"{str(y)[2:]}년" for y in target_years]   

    # 3) 행 순서 강제
    fixed_order = ["선재", "봉강", "부산", "대구", "글로벌"]


    idx = [x for x in fixed_order if x in pivot.index]


    df = pd.DataFrame(0.0, index=idx, columns=col_labels)


    # 4) 연도별 값 채우기 (없는 연도는 0 유지)
    for y, label in zip(target_years, col_labels):
        if y in pivot.columns:
            df[label] = pivot[y].reindex(df.index).fillna(0).round(0)  # 수치 반올림
        else:
            df[label] = 0.0

    # 5) 합계 행 추가 (앞 5개만 합칠지, 전체 합칠지 기존 로직 유지)
    if len(df.index) >= 5:
        df.loc["합계", :] = df.iloc[0:5].sum()
    else:
        df.loc["합계", :] = df.sum()

    # ─────────────────────────────
    # 6) 스타일링 및 출력
    # ─────────────────────────────


    df_show = df.reset_index().rename(columns={"index": "(백만원)"})
    df_show.columns.name = None

    numeric_cols = df_show.select_dtypes(include="number").columns
    first_col = df_show.columns[0]


    styled_df = (
        df_show.style
        .format({col: "{:.1f}" for col in numeric_cols}, na_rep="-")
        .hide(axis="index")

        .set_properties(
            subset=[first_col],
            **{
                "text-align": "left",
                "font-weight": "600",
                "background-color": "#f0f0f0",
                "white-space": "nowrap",
            }
        )
        # 헤더 스타일
        .set_table_styles([
            {
                "selector": "th.col_heading.level0.col0",
                "props": [
                    ("background-color", "#f0f0f0"),
                    ("font-weight", "700"),
                    ("text-align", "center"),
                ],
            },
            {"selector": "th.col_heading", "props": [("text-align", "center")]},
        ])
        # 숫자 컬럼 가운데 정렬
        .set_properties(
            subset=[c for c in df_show.columns if c in numeric_cols],
            **{"text-align": "center"}
        )
    )

    table_html = styled_df.to_html(index=False)
    centered_html = f"<div style='display: flex; justify-content: left;'>{table_html}</div>"
    st.markdown(centered_html, unsafe_allow_html=True)


    st.divider()

    st.markdown(f"### 2) 당월 클레임 내역</h5>", unsafe_allow_html=True)
    file_name = st.secrets['sheets']['f_48']
    data = load_data(file_name)
    data['실적'] /= 1000000

    df_2 = modules.create_df(this_year, current_month, data, mean = "False", prev_year = 1)

    for i in data['구분2'].unique():
        df_2.loc[(i, ' '), :] = df_2.loc[(i, '불량 보상'), :] + df_2.loc[(i, '선별비'), :]

    df_2.loc[:, '증감'] = df_2.iloc[:, -1] - df_2.iloc[:, -2]

    df_2.loc[('합계', '불량 보상'), :] = df_2.iloc[[0, 3, 6, 9, 12]].sum()
    df_2.loc[('합계', '선별비'), :] = df_2.iloc[[1, 4, 7, 10, 13]].sum()
    df_2.loc[('합계', ' '), :] = df_2.iloc[[2, 5, 8, 11, 14]].sum()

    level1_order = ['선재', '봉강', '부산', '대구', '글로벌', '합계']
    level2_order = [' ', '선별비', '불량 보상']

    df_2.index = pd.MultiIndex.from_arrays([
        pd.Categorical(df_2.index.get_level_values(0), categories=level1_order, ordered=True),
        pd.Categorical(df_2.index.get_level_values(1), categories=level2_order, ordered=True)])

    df_2 = df_2.sort_index()
    

    styled_df = (
        df_2.style
        .format(lambda x: f"{x:,.1f}" if isinstance(x, (int, float)) and pd.notnull(x) else x)
        .set_properties(**{'text-align': 'right'})
        .set_properties(**{'font-family': 'Noto Sans KR'})
        
    )



    table_html_2 = styled_df.to_html(index=True)
    centered_html_2 = f"<div style='display: flex; justify-content: left;'>{table_html_2}</div>"
    st.markdown(centered_html_2, unsafe_allow_html=True)
    display_memo('f_48', this_year, current_month)

# =========================
#영업외 비용 내역
# =========================

with t3:
    st.markdown("### 1) 영업외 비용 (최근 3개월)</h4>", unsafe_allow_html=True)

    # 데이터 로드 (secrets)
    csv_src = st.secrets['sheets']['f_49']
    df_raw = modules.load_nonop_cost_csv(csv_src)

    # 표 생성
    df_tbl = modules.create_nonop_cost_3month_by_g2_g4(
        year=this_year,
        month=current_month,
        data=df_raw
    )

    # ---- 100만 단위 반올림 표시 함수 적용 ----
    num_cols = [c for c in df_tbl.columns if c not in ("구분","계정","_row_type")]

    def _fmt(x):
        try:
            v = float(x)
        except:
            return x

        # 실제 값이 0이면 빈칸
        if v == 0:
            return ""

        # 100만 단위 반올림
        rounded = round(v / 1_000_000)

        # 반올림 결과도 0이면 빈칸
        if rounded == 0:
            return ""

        return f"{rounded:,.0f}"



    # ---- 스타일 구성 ----
    sty = (
        df_tbl.drop(columns=[c for c in ["_row_type"] if c in df_tbl.columns])
             .style
             .format(_fmt, subset=pd.IndexSlice[:, num_cols])     # ← 반올림 적용됨
             .set_properties(**{"text-align":"right", "font-family":"Noto Sans KR"})
             .set_properties(subset=pd.IndexSlice[:, ["구분","계정"]], **{"text-align":"left"})
    )

    # 특정 계정 오른쪽 정렬
    right_idx = df_tbl.index[
        df_tbl["계정"].astype(str).str.strip().isin(["고철매각작업비","기타"])
    ]
    sty = sty.set_properties(
        subset=(right_idx, ["계정"]),
        **{"text-align":"right", "padding-right":"12px"}
    )

    # ---- 행 하이라이트 ----
    # def _row_style(row):
    #     t = df_tbl.loc[row.name, "_row_type"]
    #     if t == "section_total":
    #         return ["font-weight:600; background-color:#f5f5f5"] * len(row)
    #     if t == "grand_total":
    #         return ["font-weight:700; background-color:#ededed"] * len(row)
    #     return [""] * len(row)

    # sty = sty.apply(_row_style, axis=1)

    # ---- CSS 커스텀 스타일 ----
    styles_prod = []
    styles_prod.append(
    {'selector': 'thead th', 'props': [('border-top','3px solid gray !important')]})

    styles_prod.append({
        'selector': 'tbody tr:nth-child(6) td:nth-child(2)',
        'props': [('border-bottom', '2px solid white !important')]
    })
    styles_prod.append({
        'selector': 'tbody tr:nth-child(7) td:nth-child(2)',
        'props': [('border-bottom', '2px solid white !important')]
    })

    # 기타비용 위 빈행들
    for i in range(1, 10+1):
        styles_prod.append({
            "selector": f"tbody tr:nth-child({i}) td:nth-of-type(1)",
            "props": [("border-bottom", "2px solid white !important")]
        })

    # 금융비용 위 빈행들
    for i in range(12, 18+1):
        styles_prod.append({
            "selector": f"tbody tr:nth-child({i}) td:nth-of-type(1)",
            "props": [("border-bottom", "2px solid white !important")]
        })

    for i in range(1,11):
        styles_prod.append({
            "selector": f"tbody tr:nth-child({i}) td:nth-of-type(1)",
            "props": [("border-right", "3px solid gray !important")]
        })

    for i in range(12,20):
        styles_prod.append({
            "selector": f"tbody tr:nth-child({i}) td:nth-of-type(1)",
            "props": [("border-right", "3px solid gray !important")]
        })

    for i in (10,19):
        styles_prod.append({
            "selector": f"tbody tr:nth-child({i}) td:nth-of-type(2)",
            "props": [("border-bottom", "3px solid gray !important")]
        })
    
    styles_prod.append({
            "selector": f"td:nth-of-type(2)",
            "props": [("border-right", "3px solid gray !important")]
        })


    styles_prod.append({
        'selector': 'tbody tr:nth-child(11)',
        'props': [('border-bottom', '3px solid gray !important')]
    })

    styles_prod.append({
        'selector': 'tbody tr:nth-child(1)',
        'props': [('border-top', '3px solid gray !important')]
    })



    styles_prod.append({
        'selector': 'tbody tr:nth-child(20)',
        'props': [('border-bottom', '3px solid gray !important')]
    })

    sty = sty.set_table_styles(styles_prod, overwrite=False)


    # ---- 인덱스 숨기기 ----
    if hasattr(sty, "hide"):
        sty = sty.hide(axis="index")

    # 최종 출력
    table_html = sty.to_html(index=False)
    st.markdown(f"<div style='display:flex; justify-content:left;'>{table_html}</div>", unsafe_allow_html=True)

    display_memo('f_49', this_year, current_month)



# Footer
st.markdown("""
<style>.footer { bottom: 0; left: 0; right: 0; padding: 8px; text-align: center; font-size: 13px; color: #666666;}</style>
<div class="footer">ⓒ 2025 SeAH Special Steel Corp. All rights reserved.</div>
""", unsafe_allow_html=True)