import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from auth import require_login
import warnings
import plotly.graph_objects as go
import modules
import matplotlib.pyplot as plt
import matplotlib as mpl
from plotly.subplots import make_subplots

warnings.filterwarnings('ignore')
st.set_page_config(layout="wide", initial_sidebar_state="expanded")
require_login()

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
    content = s.lstrip(' ')
    num_spaces = len(s) - len(content)
    indent_level = num_spaces // 2
    return f'<p class="indent-{indent_level}">{content}</p>'


# 🟢 [마스터 통일] 모든 페이지 성공작 스펙과 완벽하게 일치시킨 독립형 display_memo 함수 정의
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
            /* 표 옆에 들뜨지 않고 완벽하게 밀착되는 좁은 간격 수치 이식 */
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


def display_styled_df(df, styles=None, highlight_cols=None, fmt_int=True, align="left"):
    styled = df.style
    if fmt_int:
        styled = styled.format(
            lambda x: f"{x:,.0f}"
            if isinstance(x, (int, float, np.integer, np.floating)) and pd.notnull(x)
            else x
        )
    if highlight_cols:
        hi = set(map(str, highlight_cols))

        def _hi(col):
            return ['background-color: #f0f0f0'] * len(col) if str(col.name) in hi else [''] * len(col)

        styled = styled.apply(_hi, axis=0)
    base_css = [
        {'selector': 'table', 'props': [('border-collapse', 'separate'), ('border-spacing', '0')]},
        {'selector': 'th, td', 'props': [('border', '1px solid #cfcfcf'), ('padding', '6px 8px')]},
        {'selector': 'thead th', 'props': [('border-bottom', '2px solid #888'), ('text-align', 'center')]},
        {'selector': 'th.row_heading', 'props': [('background-color', '#fff')]}
    ]
    if styles:
        base_css.extend(styles)
    styled = styled.set_table_styles(base_css)
    styled = styled.set_properties(**{'text-align': 'right', 'font-family': 'Noto Sans KR'})
    html = styled.to_html()
    if align == "center":
        wrapper = f"<div style='display:flex; justify-content:center;'>{html}</div>"
    elif align == "right":
        wrapper = f"<div style='display:flex; justify-content:flex-end;'>{html}</div>"
    else:
        wrapper = f"<div style='display:flex; justify-content:flex-start;'>{html}</div>"
    st.markdown(wrapper, unsafe_allow_html=True)


def nudge_texts_to_avoid_overlap(ax, min_sep_px=10):
    by_x = {}
    texts = [t for t in ax.texts if t.get_visible()]
    for t in texts:
        x, y = t.get_position()
        by_x.setdefault(float(x), []).append(t)
    ylim = ax.get_ylim()
    height_px = ax.bbox.height if ax.bbox.height > 0 else 1
    data_per_px = (ylim[1] - ylim[0]) / height_px
    min_sep_data = min_sep_px * data_per_px
    for x, ts in by_x.items():
        ts.sort(key=lambda t: t.get_position()[1])
        last_y = -np.inf
        for t in ts:
            x0, y0 = t.get_position()
            y_new = max(y0, last_y + min_sep_data)
            if y_new != y0:
                t.set_position((x0, y_new))
            last_y = y_new
    ax.figure.canvas.draw_idle()


# 공통 table_styles
common_table_styles = [
    {
        "selector": "th.col_heading.level0.col0",
        "props": [
            ("background-color", "#f0f0f0"),
            ("font-weight", "700"),
            ("text-align", "center"),
        ],
    },
    {
        "selector": "th.col_heading",
        "props": [("text-align", "center"), ("font-weight", "700")],
    },
    {
        "selector": "th, td",
        "props": [("border", "1px solid #aaa"), ("padding", "8px 16px"), ("font-size", "15px")],
    },
    {
        "selector": "table",
        "props": [("border-collapse", "collapse")],
    },
]

st.markdown(f"## {this_year}년 {current_month}월 비용 분석")

# 🟢 [너비 칼정렬 전용 장치] 표들의 우측 마감 한계선을 일직선으로 결합시키는 CSS 변수
t5_table_align_css = """<style>table { width: 100% !important; }</style>"""

t1, t2, t3 = st.tabs(['사용량 원단위 추이', '클레임 현황', '영업외 비용 내역'])
st.divider()

# =========================================================================
# 사용량 원단위 추이 (탭 1 - 원본 로직 완전 보존)
# =========================================================================
with t1:
    display_memo('f_43', this_year, current_month)
    st.divider()

    # ── 1) 포항 ──
    st.markdown("<h4>1) 부재료 사용량 원단위 (포항)</h4>", unsafe_allow_html=True)
    file_name = st.secrets["sheets"]["f_43"]


    @st.cache_data(ttl=600)
    def load_submat_df(path: str) -> pd.DataFrame:
        return pd.read_csv(path, encoding="utf-8", thousands=",")


    df_src_pohang = load_submat_df(file_name)
    df_table = modules.create_material_usage_table_pohang(
        year=this_year, month=current_month, data=df_src_pohang, window=12, round_digits=1,
    )

    df_show = df_table.reset_index()
    df_show.columns.name = None
    month_cols = df_show.columns[1:]
    df_show[month_cols] = df_show[month_cols].apply(pd.to_numeric, errors="coerce")
    numeric_cols = month_cols

    styled = (
        df_show.style
        .format({col: "{:.1f}" for col in numeric_cols}, na_rep="-")
        .hide(axis="index")
        .set_properties(subset=[df_show.columns[0]],
                        **{"text-align": "left", "font-weight": "600", "background-color": "#f0f0f0"})
        .set_table_styles(common_table_styles)
        .set_properties(subset=numeric_cols, **{"text-align": "center"})
    )
    st.markdown(f"<div style='display:flex; justify-content:left'>{styled.to_html(index=False)}</div>",
                unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:15px; color:#000000;'>※ 사용량원단위 : 부재료사용량/공정처리량</div>",
                unsafe_allow_html=True)

    df_plot = df_table.copy()
    months = list(df_plot.columns)
    x = months
    fig = go.Figure()
    for item_name in df_plot.index:
        y = pd.to_numeric(df_plot.loc[item_name], errors="coerce").values.astype(float)
        textpos = ["top center" if i % 2 == 0 else "bottom center" for i in range(len(y))]
        fig.add_trace(go.Scatter(
            x=x, y=y, name=item_name, mode="lines+markers+text",
            line=dict(width=3.5), marker=dict(size=6),
            text=[f"{v:.1f}" if np.isfinite(v) else "" for v in y],
            textposition=textpos, textfont=dict(size=11),
            hovertemplate="값=%{y:.1f}<extra></extra>", connectgaps=False,
        ))
    fig.update_layout(margin=dict(r=120), title="[포항]",
                      legend=dict(orientation="v", x=1.02, y=0.5, xanchor="left", yanchor="middle",
                                  bgcolor="rgba(255,255,255,0.85)", borderwidth=1, font=dict(size=13),
                                  itemsizing="constant", itemwidth=90))
    fig.update_xaxes(type="category", categoryorder="array", categoryarray=x, tickangle=-45, showgrid=False)
    fig.update_yaxes(showticklabels=False, zeroline=False, showgrid=True, gridcolor="rgba(0,0,0,0.18)")
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ── 2) 충주1 ──
    st.markdown("<h4>2) 부재료 사용량 원단위 (충주1)</h4>", unsafe_allow_html=True)
    df_src_cj1 = load_submat_df(file_name)
    df_table = modules.create_material_usage_table_chungju1(
        year=this_year, month=current_month, data=df_src_cj1, window=12, round_digits=1,
    )
    df_show = df_table.reset_index()
    df_show.columns.name = None
    df_show[month_cols] = df_show[month_cols].apply(pd.to_numeric, errors="coerce")

    styled = (
        df_show.style
        .format({col: "{:.1f}" for col in numeric_cols}, na_rep="-")
        .hide(axis="index")
        .set_properties(subset=[df_show.columns[0]],
                        **{"text-align": "left", "font-weight": "600", "background-color": "#f0f0f0"})
        .set_table_styles(common_table_styles)
        .set_properties(subset=numeric_cols, **{"text-align": "center"})
    )
    st.markdown(f"<div style='display:flex; justify-content:left'>{styled.to_html(index=False)}</div>",
                unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:15px; color:#000000;'>※ 사용량원단위 : 부재료사용량/공정처리량</div>",
                unsafe_allow_html=True)

    df_plot = df_table.copy()
    fig = go.Figure()
    for item_name in df_plot.index:
        y = pd.to_numeric(df_plot.loc[item_name], errors="coerce").values.astype(float)
        textpos = ["top center" if i % 2 == 0 else "bottom center" for i in range(len(y))]
        fig.add_trace(go.Scatter(
            x=x, y=y, name=item_name, mode="lines+markers+text",
            line=dict(width=3.5), marker=dict(size=6),
            text=[f"{v:.1f}" if np.isfinite(v) else "" for v in y],
            textposition=textpos, textfont=dict(size=11),
            hovertemplate="값=%{y:.1f}<extra></extra>", connectgaps=False,
        ))
    fig.update_layout(margin=dict(r=120), title="[충주1]",
                      legend=dict(orientation="v", x=1.02, y=0.5, xanchor="left", yanchor="middle",
                                  bgcolor="rgba(255,255,255,0.85)", borderwidth=1, font=dict(size=13),
                                  itemsizing="constant", itemwidth=90))
    fig.update_xaxes(type="category", categoryorder="array", categoryarray=x, tickangle=-45, showgrid=False)
    fig.update_yaxes(showticklabels=False, zeroline=False, showgrid=True, gridcolor="rgba(0,0,0,0.18)")
    all_vals = pd.to_numeric(df_plot.values.ravel(), errors="coerce").astype(float)
    finite = np.isfinite(all_vals)
    if finite.any():
        ymin, ymax = float(np.nanmin(all_vals[finite])), float(np.nanmax(all_vals[finite]))
        pad = max((ymax - ymin) * 0.15, 1e-9)
        fig.update_yaxes(range=[ymin - pad, ymax + pad])
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ── 3) 충주2 ──
    st.markdown("<h4>3) 부재료 사용량 원단위 (충주2)</h4>", unsafe_allow_html=True)
    df_src_cj2 = load_submat_df(file_name)
    df_table = modules.create_material_usage_table_chungju2(
        year=this_year, month=current_month, data=df_src_cj2, window=12, round_digits=1,
    )
    df_show = df_table.reset_index()
    df_show.columns.name = None
    df_show[month_cols] = df_show[month_cols].apply(pd.to_numeric, errors="coerce")

    styled = (
        df_show.style
        .format({col: "{:.1f}" for col in numeric_cols}, na_rep="-")
        .hide(axis="index")
        .set_properties(subset=[df_show.columns[0]],
                        **{"text-align": "left", "font-weight": "600", "background-color": "#f0f0f0"})
        .set_table_styles(common_table_styles)
        .set_properties(subset=numeric_cols, **{"text-align": "center"})
    )
    st.markdown(f"<div style='display:flex; justify-content:left'>{styled.to_html(index=False)}</div>",
                unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:15px; color:#000000;'>※ 사용량원단위 : 부재료사용량/공정처리량</div>",
                unsafe_allow_html=True)

    df_plot = df_table.copy()
    fig = go.Figure()
    for item_name in df_plot.index:
        y = pd.to_numeric(df_plot.loc[item_name], errors="coerce").values.astype(float)
        textpos = ["top center" if j % 2 == 0 else "bottom center" for j in range(len(y))]
        fig.add_trace(go.Scatter(
            x=x, y=y, name=item_name, mode="lines+markers+text",
            line=dict(width=3.5), marker=dict(size=6),
            text=[f"{v:.1f}" if np.isfinite(v) else "" for v in y],
            textposition=textpos, textfont=dict(size=11),
            hovertemplate="값=%{y:.1f}<extra></extra>", connectgaps=False,
        ))
    fig.update_layout(margin=dict(r=120), title="[충주2]",
                      legend=dict(orientation="v", x=1.02, y=0.5, xanchor="left", yanchor="middle",
                                  bgcolor="rgba(255,255,255,0.85)", borderwidth=1, font=dict(size=13),
                                  itemsizing="constant", itemwidth=90))
    fig.update_xaxes(type="category", categoryorder="array", categoryarray=x, tickangle=-45, showgrid=False)
    fig.update_yaxes(showticklabels=False, zeroline=False, showgrid=True, gridcolor="rgba(0,0,0,0.18)")
    all_vals = pd.to_numeric(df_plot.values.ravel(), errors="coerce").astype(float)
    finite = np.isfinite(all_vals)
    if finite.any():
        ymin, ymax = float(np.nanmin(all_vals[finite])), float(np.nanmax(all_vals[finite]))
        pad = max((ymax - ymin) * 0.15, 1e-9)
        fig.update_yaxes(range=[ymin - pad, ymax + pad])
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ── 4) 단가 추이 ──
    st.markdown("<h4>4) 단가 추이</h4>", unsafe_allow_html=True)
    file_name = st.secrets["sheets"]["f_46"]
    df_src_unit = load_submat_df(file_name)
    df_table = modules.create_material_usage_table_unit_price(
        year=this_year, month=current_month, data=df_src_unit, window=12, round_digits=1,
    )
    df_show = df_table.reset_index()
    df_show.columns.name = None
    numeric_cols = df_show.select_dtypes(include="number").columns
    first_col = df_show.columns[0]

    styled = (
        df_show.style
        .format({col: "{:.1f}" for col in numeric_cols}, na_rep="-")
        .hide(axis="index")
        .set_properties(subset=[first_col],
                        **{"text-align": "left", "font-weight": "600", "background-color": "#f0f0f0",
                           "white-space": "nowrap"})
        .set_table_styles(common_table_styles)
        .set_properties(subset=[c for c in df_show.columns if c in numeric_cols], **{"text-align": "center"})
    )
    st.markdown(f"<div style='display:flex; justify-content:left'>{styled.to_html(index=False)}</div>",
                unsafe_allow_html=True)

    df_plot = df_table.copy()
    df_plot = df_plot.apply(pd.to_numeric, errors="coerce")
    months = df_plot.columns.tolist()
    x = months

    n2_label, pw_label = "질소(천㎥)", "전력(천kwh)"
    others = [idx for idx in df_plot.index if idx not in {n2_label, pw_label}]
    y_n2 = pd.to_numeric(df_plot.loc[n2_label], errors="coerce").values.astype(float)
    y_pw = pd.to_numeric(df_plot.loc[pw_label], errors="coerce").values.astype(float)
    others_vals = pd.to_numeric(df_plot.loc[others].values.ravel(), errors="coerce").astype(float) if len(
        others) else np.array([], dtype=float)


    def rng(v, pad_ratio=0.5):
        f = np.isfinite(v)
        if not f.any(): return [0.0, 1.0]
        vmin, vmax = float(np.nanmin(v[f])), float(np.nanmax(v[f]))
        pad = max((vmax - vmin) * pad_ratio, 1e-9)
        return [vmin - pad, vmax + pad]


    y1_range = rng(others_vals)
    y2_range = rng(np.r_[y_n2[np.isfinite(y_n2)], y_pw[np.isfinite(y_pw)]])

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.80, 0.25])
    base_colors = ["#1f77b4", "#ff7f0e", "#939393", "#bcbd22", "#000080", "#009900"]
    for i, name in enumerate(others):
        y = pd.to_numeric(df_plot.loc[name], errors="coerce").values.astype(float)
        fig.add_trace(go.Scatter(
            x=x, y=y, name=name, mode="lines+markers+text",
            line=dict(width=3.5, color=base_colors[i % len(base_colors)]), marker=dict(size=6),
            texttemplate="%{y:.1f}", textposition="top center", textfont=dict(size=10),
            hovertemplate="값=%{y:.1f}<extra></extra>",
        ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=x, y=y_n2, name=n2_label, mode="lines+markers+text",
        line=dict(width=3.5, color="#FFD400"), marker=dict(size=7),
        texttemplate="%{y:.1f}", textposition="top center", textfont=dict(size=10),
        hovertemplate="값=%{y:.1f}<extra></extra>",
    ), row=2, col=1)
    fig.add_trace(go.Scatter(
        x=x, y=y_pw, name=pw_label, mode="lines+markers+text",
        line=dict(width=3.5, color="#BB2649"), marker=dict(size=7),
        texttemplate="%{y:.1f}", textposition="top center", textfont=dict(size=10),
        hovertemplate="값=%{y:.1f}<extra></extra>",
    ), row=2, col=1)

    fig.update_layout(uniformtext_minsize=9, uniformtext_mode="hide", margin=dict(r=120),
                      legend=dict(orientation="v", x=1.02, y=0.5, xanchor="left", yanchor="middle",
                                  bgcolor="rgba(255,255,255,0.85)", borderwidth=1, font=dict(size=13),
                                  itemsizing="constant", itemwidth=90))
    for r in (1, 2):
        fig.update_xaxes(type="category", categoryorder="array", categoryarray=x, tickangle=-45, showgrid=False, row=r,
                         col=1)
    fig.update_yaxes(range=y1_range, showticklabels=False, zeroline=False, showgrid=True, gridcolor="rgba(0,0,0,0.18)",
                     row=1, col=1)
    fig.update_yaxes(range=y2_range, showticklabels=False, zeroline=False, showgrid=True, gridcolor="rgba(0,0,0,0.18)",
                     row=2, col=1)
    st.plotly_chart(fig, use_container_width=True)

    display_memo('f_46', this_year, current_month)

# 클레임 현황 (탭 2)
# =========================================================================
with t2:
    # 1) 월 평균 클레임 지급액 (6:4 레이아웃 적용)
    col_l2_1, col_r2_1 = st.columns([6, 4], gap="large")

    with col_l2_1:
        st.markdown("<h4>1) 월 평균 클레임 지급액</h4>", unsafe_allow_html=True)
        st.markdown("<div style='text-align:right; font-size:13px; color:#666; margin-bottom:5px;'>[단위: 백만원]</div>",
                    unsafe_allow_html=True)

        pivot = modules.update_monthly_claim_form()
        base_year = int(this_year)
        target_years = [base_year - 3, base_year - 2, base_year - 1, base_year]
        col_labels = [f"{str(y)[2:]}년" for y in target_years]
        fixed_order = ["선재", "봉강", "부산", "대구", "글로벌"]
        idx = [x for x in fixed_order if x in pivot.index]
        df = pd.DataFrame(0.0, index=idx, columns=col_labels)

        for y, label in zip(target_years, col_labels):
            if y in pivot.columns:
                df[label] = pivot[y].reindex(df.index).fillna(0).round(0)
            else:
                df[label] = 0.0

        df.loc["합계", :] = df.iloc[0:5].sum() if len(df.index) >= 5 else df.sum()

        df_show = df.reset_index().rename(columns={"index": "구분"})
        df_show.columns.name = None
        numeric_cols = df_show.select_dtypes(include="number").columns
        first_col = df_show.columns[0]

        styled_df = (
            df_show.style
            .format({col: "{:.1f}" for col in numeric_cols}, na_rep="-")
            .hide(axis="index")
            .set_properties(**{"text-align": "right", "background-color": "white"})
            # 💡 수정된 부분: "font-weight": "700"을 "normal"로 변경하여 볼드체 해제
            .set_properties(subset=[first_col],
                            **{"text-align": "left", "font-weight": "normal", "background-color": "white",
                               "white-space": "nowrap"})
            .set_table_styles(common_table_styles)
            .set_table_styles([{"selector": "th", "props": [("background-color", "white !important")]}],
                              overwrite=False)
            .set_properties(subset=[c for c in df_show.columns if c in numeric_cols], **{"text-align": "right"})
        )
        st.markdown(f"<div style='display: flex; justify-content: left;'>{styled_df.to_html(index=False)}</div>",
                    unsafe_allow_html=True)

    with col_r2_1:
        st.markdown("<h4 style='color:transparent'>1) 월 평균 클레임 지급액 헤더맞춤</h4>", unsafe_allow_html=True)

    st.divider()

    col_l2_2, col_r2_2 = st.columns([6, 4], gap="large")

    with col_l2_2:
        st.markdown("<h4>2) 당월 클레임 내역</h4>", unsafe_allow_html=True)

        try:
            file_name = st.secrets['sheets']['f_48']
            data = load_data(file_name)
            data['실적'] /= 1000000

            df_2 = modules.create_df(this_year, current_month, data, mean="False", prev_year=1)
            month_cols = [c for c in df_2.columns if '년말' not in str(c)][-3:]
            df_2 = df_2[month_cols]

            rename_map = {}
            for col in df_2.columns:
                col_str = str(col)
                if '년' in col_str and '월' in col_str:
                    year_part = col_str.split('년')[0].strip()[-2:]
                    month_part = col_str.split('년')[1].replace('월', '').strip()
                    rename_map[col] = f"{year_part}.{month_part}월"
            df_2 = df_2.rename(columns=rename_map)

            for i in data['구분2'].unique():
                df_2.loc[(i, ' '), :] = df_2.loc[(i, '불량 보상'), :] + df_2.loc[(i, '선별비'), :]

            df_2.loc[('합계', '불량 보상'), :] = df_2.iloc[[0, 3, 6, 9, 12]].sum()
            df_2.loc[('합계', '선별비'), :] = df_2.iloc[[1, 4, 7, 10, 13]].sum()
            df_2.loc[('합계', ' '), :] = df_2.iloc[[2, 5, 8, 11, 14]].sum()

            df_2['증감'] = df_2.iloc[:, -1] - df_2.iloc[:, -2]

            level1_order = ['선재', '봉강', '부산', '대구', '글로벌', '합계']
            level2_order = [' ', '선별비', '불량 보상']

            df_2.index = pd.MultiIndex.from_arrays([
                pd.Categorical(df_2.index.get_level_values(0), categories=level1_order, ordered=True),
                pd.Categorical(df_2.index.get_level_values(1), categories=level2_order, ordered=True)])
            df_2 = df_2.sort_index()

            df_show = df_2.reset_index()
            df_show.columns = ['lv1', 'lv2'] + list(df_2.columns)
            df_show['클레임비'] = df_show.apply(lambda row: row['lv1'] if row['lv2'].strip() == '' else row['lv2'], axis=1)
            df_show = df_show.drop(columns=['lv1', 'lv2'])
            cols = ['클레임비'] + [c for c in df_show.columns if c != '클레임비']
            df_show = df_show[cols]
            df_show.columns.name = None
            numeric_cols = df_show.select_dtypes(include='number').columns

            # 🟢 [수정] DB에서 구분3 값들 동적 추출
            구분3_values = set()
            for idx, row in data.iterrows():
                g3 = str(row['구분3']).strip() if pd.notna(row['구분3']) else ''
                if g3:
                    구분3_values.add(g3)


            def format_claim_label(claim_text):
                clean_text = str(claim_text).strip()
                # 구분3 값이면 들여쓰기
                if clean_text in 구분3_values:
                    return f'<span style="padding-left:16px">{clean_text}</span>'
                return claim_text


            df_show['클레임비'] = df_show['클레임비'].apply(format_claim_label)


            def color_negative(val):
                return 'color: red' if isinstance(val, (int, float)) and pd.notnull(val) and val < 0 else ''


            styled_df2 = (
                df_show.style
                .format({col: "{:,.1f}" for col in numeric_cols}, na_rep="-")
                .map(color_negative, subset=['증감'])
                .hide(axis='index')
                .set_properties(**{'text-align': 'right'})
                .set_properties(subset=['클레임비'], **{'text-align': 'left'})
                .set_properties(**{'font-family': 'Noto Sans KR'})
                .set_table_styles([
                    {'selector': 'th, td',
                     'props': [('border', '1px solid #aaa'), ('padding', '8px 16px'), ('font-size', '15px')]},
                    {'selector': 'thead th', 'props': [('font-weight', '700'), ('text-align', 'center')]},
                    {'selector': 'table', 'props': [('border-collapse', 'collapse')]}
                ])
            )

            # 🟢 끝선 동기화 렌더링 마운트
            html_table2 = styled_df2.to_html(escape=False)
            st.markdown(
                f"<div style='width: 100%; max-width: 100%; overflow-x: auto; display: block;'>{t5_table_align_css}{html_table2}</div>",
                unsafe_allow_html=True)
        except Exception as e:
            st.error(f"당월 클레임 내역 표 생성 오류: {e}")

    with col_r2_2:
        st.markdown("<h4 style='color:transparent'>2) 당월 클레임 내역 헤더맞춤</h4>", unsafe_allow_html=True)
        st.markdown("<div style='color:transparent; font-size:15px; margin-bottom:5px;'>[단위]</div>",
                    unsafe_allow_html=True)
        # 🟢 타이트 콤팩트 스펙 주입 연동
        display_memo('f_48', this_year, current_month, css_class="t5-tight-memo")
# 영업외 비용 내역 (탭 3 - 계층 구조 + 합계 행 + 항목 수정)
# =========================================================================
with t3:
    # 🟢 [6:4 좌우 완전 분할 뼈대 구축]
    col_l3, col_r3 = st.columns([6, 4], gap="large")

    with col_l3:
        st.markdown("<h4>1) 영업외 비용 (최근 3개월)</h4>", unsafe_allow_html=True)
        # 🟢 단위 표시 어깨 안착
        st.markdown("<div style='text-align:right; font-size:13px; color:#666; margin-bottom:5px;'>[단위: 백만원]</div>",
                    unsafe_allow_html=True)

        try:
            csv_src = st.secrets['sheets']['f_49']
            df_raw = modules.load_nonop_cost_csv(csv_src)
            df_tbl = modules.create_nonop_cost_3month_by_g2_g4(year=this_year, month=current_month, data=df_raw)

            num_cols = [c for c in df_tbl.columns if c not in ("구분", "계정", "_row_type", "증감")]
            rename_map = {}
            for c in num_cols:
                clean = c.replace("'", "").replace(" 실적", "").strip()
                rename_map[c] = clean
            df_tbl = df_tbl.rename(columns=rename_map)
            new_num_cols = [rename_map.get(c, c) for c in num_cols]

            # 🟢 계층 구조 항목 순서 정의
            hierarchy_item_names = [
                "기부금",
                "유형자산처분손실",
                "지급수수료(영업외)",
                "고철매각작업비",
                "잡손실",
                "사용권자산처분손실",
                "기타비용",
                "기타비용 합계",
                "이자비용",
                "외환차손",
                "외화환산손실",
                "기타파생상품평가손실",
                "리스부채 이자비용",
                "금융비용 합계",
                "합계",
            ]

            # 🟢 기본 데이터에서 필터링
            df_show3 = df_tbl.drop(columns=['_row_type']).copy()
            df_show3['구분'] = df_show3.apply(
                lambda row: row['구분'] if str(row['계정']).strip() == '' else row['계정'],
                axis=1
            )
            df_show3 = df_show3.drop(columns=['계정'])

            # 🟢 df_raw에서 구분2 -> Lv class 매핑 추출
            lv_map_raw = {}
            for idx, row in df_raw.iterrows():
                item_name = str(row.get('구분2', '')).strip()
                lv_class = row.get('Lv class', 0)
                if item_name and item_name not in lv_map_raw:
                    lv_map_raw[item_name] = int(lv_class) if pd.notna(lv_class) else 0

            # 모듈 label -> 데이터 구분2 이름 매핑
            name_mapping = {
                "기타비용": "기타비용(영업외)",
                "외화차손": "외환차손",
            }

            # 모듈 label 기준으로 lv_map 재구축
            lv_map = {}
            for module_label, data_name in name_mapping.items():
                if data_name in lv_map_raw:
                    lv_map[module_label] = lv_map_raw[data_name]

            # 일치하는 항목들 추가
            for item_name, lv_val in lv_map_raw.items():
                if item_name not in name_mapping.values():
                    lv_map[item_name] = lv_val

            # 합계 행들은 Lv=0으로 설정
            lv_map['기타비용 합계'] = 0
            lv_map['금융비용 합계'] = 0
            lv_map['계'] = 0

            # 🟢 df_show3의 각 행에 Lv class 추가
            df_show3['Lv class'] = df_show3['구분'].map(lv_map).fillna(1).astype(int)

            # 🟢 계층 구조 순서대로 재정렬 및 합계 행 추가
            rows_list = []

            # 합계 행들을 위한 그룹별 합계 계산 (표에 표시될 항목들만)
            basic_items_g1 = ["기부금", "유형자산처분손실", "지급수수료(영업외)",
                              "잡손실", "사용권자산처분손실", "기타비용"]
            basic_items_g2 = ["이자비용", "외환차손", "외화환산손실", "기타파생상품평가손실", "리스부채 이자비용"]

            for item_name in hierarchy_item_names:
                # 기본 항목들 (데이터에 존재)
                if item_name in ["기부금", "유형자산처분손실", "지급수수료(영업외)", "고철매각작업비",
                                 "잡손실", "사용권자산처분손실", "기타비용",
                                 "이자비용", "외환차손", "외화환산손실", "기타파생상품평가손실", "리스부채 이자비용"]:
                    row_data = df_show3[df_show3['구분'] == item_name]
                    if len(row_data) > 0:
                        rows_list.append(row_data.iloc[0])

                # 기타비용 합계 행 생성
                elif item_name == "기타비용 합계":
                    row_sum = pd.Series()
                    row_sum['구분'] = "기타비용 합계"
                    row_sum['Lv class'] = lv_map.get('기타비용 합계', 0)
                    for col in new_num_cols:
                        col_sum = 0
                        for basic_item in basic_items_g1:
                            basic_row = df_show3[df_show3['구분'] == basic_item]
                            if len(basic_row) > 0:
                                val = basic_row.iloc[0][col]
                                if pd.notna(val) and val != '':
                                    try:
                                        col_sum += float(val)
                                    except:
                                        pass
                        row_sum[col] = col_sum
                    # 증감 계산
                    if len(new_num_cols) >= 2:
                        row_sum['증감'] = float(row_sum[new_num_cols[-1]]) - float(row_sum[new_num_cols[0]])
                    rows_list.append(row_sum)

                # 금융비용 합계 행 생성
                elif item_name == "금융비용 합계":
                    row_sum = pd.Series()
                    row_sum['구분'] = "금융비용 합계"
                    row_sum['Lv class'] = lv_map.get('금융비용 합계', 0)
                    for col in new_num_cols:
                        col_sum = 0
                        for basic_item in basic_items_g2:
                            basic_row = df_show3[df_show3['구분'] == basic_item]
                            if len(basic_row) > 0:
                                val = basic_row.iloc[0][col]
                                if pd.notna(val) and val != '':
                                    try:
                                        col_sum += float(val)
                                    except:
                                        pass
                        row_sum[col] = col_sum
                    # 증감 계산
                    if len(new_num_cols) >= 2:
                        row_sum['증감'] = float(row_sum[new_num_cols[-1]]) - float(row_sum[new_num_cols[0]])
                    rows_list.append(row_sum)

                # 합계 행 생성 (모듈의 "계"를 "합계"로 표시)
                elif item_name == "합계":
                    row_sum = pd.Series()
                    row_sum['구분'] = "합계"
                    row_sum['Lv class'] = lv_map.get('계', 0)
                    for col in new_num_cols:
                        col_sum = 0
                        for basic_item in basic_items_g1 + basic_items_g2:
                            basic_row = df_show3[df_show3['구분'] == basic_item]
                            if len(basic_row) > 0:
                                val = basic_row.iloc[0][col]
                                if pd.notna(val) and val != '':
                                    try:
                                        col_sum += float(val)
                                    except:
                                        pass
                        row_sum[col] = col_sum
                    # 증감 계산
                    if len(new_num_cols) >= 2:
                        row_sum['증감'] = float(row_sum[new_num_cols[-1]]) - float(row_sum[new_num_cols[0]])
                    rows_list.append(row_sum)

            df_show3 = pd.DataFrame(rows_list).reset_index(drop=True)
            cols3 = ['구분', 'Lv class'] + new_num_cols + ['증감']
            df_show3 = df_show3[cols3]
            all_num_cols = new_num_cols + ['증감']


            # 🟢 포맷팅 함수
            def _fmt(x):
                try:
                    v = float(x)
                except:
                    return x
                if pd.isna(v):
                    return ""
                rounded = round(v / 1_000_000)
                return f"{rounded:,.0f}"


            def get_color_for_val(val):
                try:
                    v = float(val)
                    return 'red' if v < 0 else 'black'
                except:
                    return 'black'


            # 🟢 순수 HTML 테이블 생성 (계층 구조 + 스타일 포함)
            html_parts = [
                '<table style="border-collapse: collapse; width: 100%; font-family: Noto Sans KR; font-size: 15px;">']

            # 헤더 행
            html_parts.append('<thead>')
            html_parts.append('<tr>')
            html_parts.append(
                '<th style="border: 1px solid #aaa; padding: 8px 16px; font-weight: 700; background: #fff; text-align: center;">구분</th>')
            for col in new_num_cols:
                html_parts.append(
                    f'<th style="border: 1px solid #aaa; padding: 8px 16px; font-weight: 700; background: #fff; text-align: center;">{col}</th>')
            html_parts.append(
                '<th style="border: 1px solid #aaa; padding: 8px 16px; font-weight: 700; background: #fff; text-align: center;">증감</th>')
            html_parts.append('</tr>')
            html_parts.append('</thead>')

            # 데이터 행
            html_parts.append('<tbody>')
            for idx, row in df_show3.iterrows():
                label = str(row['구분']).strip()
                lv = int(row['Lv class']) if pd.notna(row['Lv class']) else 0
                indent_px = lv * 16

                # 합계 행 여부
                is_summary = '합계' in label
                fw = '700' if is_summary else '400'

                html_parts.append('<tr>')
                html_parts.append(
                    f'<td style="border: 1px solid #aaa; padding: 8px 16px; text-align: left; font-weight: {fw}; white-space: pre;"><span style="display:inline-block; padding-left:{indent_px}px;">{label}</span></td>')

                # 숫자 컬럼들
                for col in new_num_cols:
                    val = row[col]
                    formatted_val = _fmt(val)
                    html_parts.append(
                        f'<td style="border: 1px solid #aaa; padding: 8px 16px; text-align: right; font-weight: {fw};">{formatted_val}</td>')

                # 증감 컬럼
                inc_val = row['증감']
                inc_formatted = _fmt(inc_val)
                inc_color = get_color_for_val(inc_val)
                html_parts.append(
                    f'<td style="border: 1px solid #aaa; padding: 8px 16px; text-align: right; font-weight: {fw}; color: {inc_color};">{inc_formatted}</td>')

                html_parts.append('</tr>')
            html_parts.append('</tbody>')
            html_parts.append('</table>')

            html_table3 = '\n'.join(html_parts)
            st.markdown(
                f"<div style='width: 100%; max-width: 100%; overflow-x: auto; display: block;'>{html_table3}</div>",
                unsafe_allow_html=True)
        except Exception as e:
            st.error(f"영업외 비용 표 생성 오류: {e}")

    with col_r3:
        st.markdown("<h4 style='color:transparent'>1) 영업외 비용 헤더맞춤</h4>", unsafe_allow_html=True)
        st.markdown("<div style='color:transparent; font-size:15px; margin-bottom:5px;'>[단위]</div>",
                    unsafe_allow_html=True)
        display_memo('f_49', this_year, current_month, css_class="t5-tight-memo")

# =========================
# Footer (하단 고정바 중복 및 오타 정리)
# =========================
st.markdown("""
<style>.footer { bottom: 0; left: 0; right: 0; padding: 8px; text-align: center; font-size: 13px; color: #666666;}</style>
<div class="footer">ⓒ 2026 SeAH Special Steel Corp. All rights reserved.</div>
""", unsafe_allow_html=True)