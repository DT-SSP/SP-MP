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
    content = s.lstrip(' ')
    num_spaces = len(s) - len(content)
    indent_level = num_spaces // 2
    return f'<p class="indent-{indent_level}">{content}</p>'


def display_memo(memo_file_key, year, month,):
    file_name = st.secrets['memos'][memo_file_key]
    try:
        df_memo = pd.read_csv(file_name)
        df_filtered = df_memo[(df_memo['년도'] == year) & (df_memo['월'] == month)]
        if df_filtered.empty:
            st.warning(f"{year}년 {month}월 메모를 찾을 수 없습니다.")
            return
        memo_text = df_filtered.iloc[0]['메모']
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
    import numpy as np
    import matplotlib.transforms as mtransforms
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
        "props": [("text-align", "center")],
    },
    {
        "selector": "th, td",
        "props": [("border", "1px solid #000000")],
    },
    {
        "selector": "table",
        "props": [("border-collapse", "collapse")],
    },
]

st.markdown(f"## {this_year}년 {current_month}월 비용 분석")
t1, t2, t3 = st.tabs(['사용량 원단위 추이', '클레임 현황', '영업외 비용 내역'])
st.divider()

# =========================
# 사용량 원단위 추이
# =========================
with t1:
    display_memo('f_43', this_year, current_month)
    st.divider()

    # ── 1) 포항 ──
    st.markdown("### 1) 부재료 사용량 원단위 (포항)", unsafe_allow_html=True)

    file_name = st.secrets["sheets"]["f_43"]

    @st.cache_data(ttl=600)
    def load_submat_df(path: str) -> pd.DataFrame:
        return pd.read_csv(path, encoding="utf-8", thousands=",")

    df_src_pohang = load_submat_df(file_name)

    df_table = modules.create_material_usage_table_pohang(
        year=this_year, month=current_month,
        data=df_src_pohang, window=12, round_digits=1,
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
        .set_properties(subset=[df_show.columns[0]], **{"text-align": "left", "font-weight": "600", "background-color": "#f0f0f0"})
        .set_table_styles(common_table_styles)
        .set_properties(subset=numeric_cols, **{"text-align": "center"})
    )
    st.markdown(f"<div style='display:flex; justify-content:left'>{styled.to_html(index=False)}</div>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:15px; color:#000000;'>※ 사용량원단위 : 부재료사용량/공정처리량</div>", unsafe_allow_html=True)

    try:
        mpl.rcParams['font.family'] = 'Malgun Gothic'
        mpl.rcParams['axes.unicode_minus'] = False
    except Exception:
        pass

    df_plot = df_table.copy()
    months = list(df_plot.columns)
    x = months
    fig = go.Figure()
    for item_name in df_plot.index:
        y = pd.to_numeric(df_plot.loc[item_name], errors="coerce").values.astype(float)
        textpos = ["top center" if i % 2 == 0 else "bottom center" for i in range(len(y))]
        fig.add_trace(go.Scatter(
            x=x, y=y, name=item_name, mode="lines+markers+text",
            line=dict(width=2), marker=dict(size=6),
            text=[f"{v:.1f}" if np.isfinite(v) else "" for v in y],
            textposition=textpos, textfont=dict(size=11),
            hovertemplate="값=%{y:.1f}<extra></extra>", connectgaps=False,
        ))
    fig.update_traces(line=dict(width=3.5))
    fig.update_layout(margin=dict(r=120), title="[포항]",
        legend=dict(orientation="v", x=1.02, y=0.5, xanchor="left", yanchor="middle",
            bgcolor="rgba(255,255,255,0.85)", borderwidth=1, font=dict(size=13), itemsizing="constant", itemwidth=90))
    fig.update_xaxes(type="category", categoryorder="array", categoryarray=x,
        tickmode="array", tickvals=x, ticktext=x, tickangle=-45, showgrid=False)
    fig.update_yaxes(title_text=None, showticklabels=False, zeroline=False, showgrid=True, gridcolor="rgba(0,0,0,0.18)")
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ── 2) 충주1 ──
    st.markdown("### 2) 부재료 사용량 원단위 (충주1)", unsafe_allow_html=True)

    df_src_cj1 = load_submat_df(file_name)
    df_table = modules.create_material_usage_table_chungju1(
        year=this_year, month=current_month,
        data=df_src_cj1, window=12, round_digits=1,
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
        .set_properties(subset=[df_show.columns[0]], **{"text-align": "left", "font-weight": "600", "background-color": "#f0f0f0"})
        .set_table_styles(common_table_styles)
        .set_properties(subset=numeric_cols, **{"text-align": "center"})
    )
    st.markdown(f"<div style='display:flex; justify-content:left'>{styled.to_html(index=False)}</div>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:15px; color:#000000;'>※ 사용량원단위 : 부재료사용량/공정처리량</div>", unsafe_allow_html=True)

    try:
        mpl.rcParams['font.family'] = 'Malgun Gothic'
        mpl.rcParams['axes.unicode_minus'] = False
    except Exception:
        pass

    df_plot = df_table.copy()
    months = list(df_plot.columns)
    x = months
    fig = go.Figure()
    for item_name in df_plot.index:
        y = pd.to_numeric(df_plot.loc[item_name], errors="coerce").values.astype(float)
        textpos = ["top center" if i % 2 == 0 else "bottom center" for i in range(len(y))]
        fig.add_trace(go.Scatter(
            x=x, y=y, name=item_name, mode="lines+markers+text",
            line=dict(width=2), marker=dict(size=6),
            text=[f"{v:.1f}" if np.isfinite(v) else "" for v in y],
            textposition=textpos, textfont=dict(size=11),
            hovertemplate="값=%{y:.1f}<extra></extra>", connectgaps=False,
        ))
    fig.update_traces(line=dict(width=3.5))
    fig.update_layout(margin=dict(r=120), title="[충주1]",
        legend=dict(orientation="v", x=1.02, y=0.5, xanchor="left", yanchor="middle",
            bgcolor="rgba(255,255,255,0.85)", borderwidth=1, font=dict(size=13), itemsizing="constant", itemwidth=90))
    fig.update_xaxes(type="category", categoryorder="array", categoryarray=x,
        tickmode="array", tickvals=x, ticktext=x, tickangle=-45, showgrid=False)
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
    st.markdown("### 3) 부재료 사용량 원단위 (충주2)", unsafe_allow_html=True)

    df_src_cj2 = load_submat_df(file_name)
    df_table = modules.create_material_usage_table_chungju2(
        year=this_year, month=current_month,
        data=df_src_cj2, window=12, round_digits=1,
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
        .set_properties(subset=[df_show.columns[0]], **{"text-align": "left", "font-weight": "600", "background-color": "#f0f0f0"})
        .set_table_styles(common_table_styles)
        .set_properties(subset=numeric_cols, **{"text-align": "center"})
    )
    st.markdown(f"<div style='display:flex; justify-content:left'>{styled.to_html(index=False)}</div>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:left; font-size:15px; color:#000000;'>※ 사용량원단위 : 부재료사용량/공정처리량</div>", unsafe_allow_html=True)

    try:
        mpl.rcParams['font.family'] = 'Malgun Gothic'
        mpl.rcParams['axes.unicode_minus'] = False
    except Exception:
        pass

    df_plot = df_table.copy()
    months = list(df_plot.columns)
    x = months
    fig = go.Figure()
    for i, item_name in enumerate(df_plot.index):
        y = pd.to_numeric(df_plot.loc[item_name], errors="coerce").values.astype(float)
        textpos = ["top center" if j % 2 == 0 else "bottom center" for j in range(len(y))]
        fig.add_trace(go.Scatter(
            x=x, y=y, name=item_name, mode="lines+markers+text",
            line=dict(width=2), marker=dict(size=6),
            text=[f"{v:.1f}" if np.isfinite(v) else "" for v in y],
            textposition=textpos, textfont=dict(size=11),
            hovertemplate="값=%{y:.1f}<extra></extra>", connectgaps=False,
        ))
    fig.update_traces(line=dict(width=3.5))
    fig.update_layout(margin=dict(r=120), title="[충주2]",
        legend=dict(orientation="v", x=1.02, y=0.5, xanchor="left", yanchor="middle",
            bgcolor="rgba(255,255,255,0.85)", borderwidth=1, font=dict(size=13), itemsizing="constant", itemwidth=90))
    fig.update_xaxes(type="category", categoryorder="array", categoryarray=x,
        tickmode="array", tickvals=x, ticktext=x, tickangle=-45, showgrid=False)
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
    df_src_unit = load_submat_df(file_name)  # ← 별도 변수로 분리
    df_table = modules.create_material_usage_table_unit_price(
        year=this_year, month=current_month,
        data=df_src_unit, window=12, round_digits=1,
    )

    df_show = df_table.reset_index()
    df_show.columns.name = None
    numeric_cols = df_show.select_dtypes(include="number").columns
    first_col = df_show.columns[0]

    styled = (
        df_show.style
        .format({col: "{:.1f}" for col in numeric_cols}, na_rep="-")
        .hide(axis="index")
        .set_properties(subset=[first_col], **{"text-align": "left", "font-weight": "600", "background-color": "#f0f0f0", "white-space": "nowrap"})
        .set_table_styles(common_table_styles)
        .set_properties(subset=[c for c in df_show.columns if c in numeric_cols], **{"text-align": "center"})
    )
    st.markdown(f"<div style='display:flex; justify-content:left'>{styled.to_html(index=False)}</div>", unsafe_allow_html=True)

    df_plot = df_table.copy()
    df_plot = df_plot.apply(pd.to_numeric, errors="coerce")
    months = df_plot.columns.tolist()
    x = months

    from plotly.subplots import make_subplots

    n2_label, pw_label = "질소(천㎥)", "전력(천kwh)"
    others = [idx for idx in df_plot.index if idx not in {n2_label, pw_label}]

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

    y1_range = rng(others_vals)
    y2_range = rng(np.r_[y_n2[np.isfinite(y_n2)], y_pw[np.isfinite(y_pw)]])

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.80, 0.25])

    base_colors = ["#1f77b4", "#ff7f0e", "#939393", "#bcbd22", "#000080", "#009900"]
    for i, name in enumerate(others):
        y = pd.to_numeric(df_plot.loc[name], errors="coerce").values.astype(float)
        fig.add_trace(go.Scatter(
            x=x, y=y, name=name, mode="lines+markers+text",
            line=dict(width=2, color=base_colors[i % len(base_colors)]), marker=dict(size=6),
            texttemplate="%{y:.1f}", textposition="top center", textfont=dict(size=10),
            hovertemplate="값=%{y:.1f}<extra></extra>",
        ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=x, y=y_n2, name=n2_label, mode="lines+markers+text",
        line=dict(width=2.4, color="#FFD400"), marker=dict(size=7),
        texttemplate="%{y:.1f}", textposition="top center", textfont=dict(size=10),
        hovertemplate="값=%{y:.1f}<extra></extra>",
    ), row=2, col=1)
    fig.add_trace(go.Scatter(
        x=x, y=y_pw, name=pw_label, mode="lines+markers+text",
        line=dict(width=2.4, color="#BB2649"), marker=dict(size=7),
        texttemplate="%{y:.1f}", textposition="top center", textfont=dict(size=10),
        hovertemplate="값=%{y:.1f}<extra></extra>",
    ), row=2, col=1)

    fig.update_traces(line=dict(width=3.5))
    fig.update_layout(uniformtext_minsize=9, uniformtext_mode="hide", margin=dict(r=120),
        legend=dict(orientation="v", x=1.02, y=0.5, xanchor="left", yanchor="middle",
            bgcolor="rgba(255,255,255,0.85)", borderwidth=1, font=dict(size=13), itemsizing="constant", itemwidth=90))

    for r in (1, 2):
        fig.update_xaxes(type="category", categoryorder="array", categoryarray=x,
            tickmode="array", tickvals=x, ticktext=x, tickangle=-45, showgrid=False, row=r, col=1)

    fig.update_yaxes(range=y1_range, showticklabels=False, zeroline=False, showgrid=True, gridcolor="rgba(0,0,0,0.18)", row=1, col=1)
    fig.update_yaxes(range=y2_range, showticklabels=False, zeroline=False, showgrid=True, gridcolor="rgba(0,0,0,0.18)", row=2, col=1)
    st.plotly_chart(fig, use_container_width=True)

    display_memo('f_46', this_year, current_month)


# =========================
# 클레임 현황
# =========================
with t2:
    st.markdown(f"### 1) 월 평균 클레임 지급액</h4>", unsafe_allow_html=True)

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

    if len(df.index) >= 5:
        df.loc["합계", :] = df.iloc[0:5].sum()
    else:
        df.loc["합계", :] = df.sum()

    df_show = df.reset_index().rename(columns={"index": "(백만원)"})
    df_show.columns.name = None
    numeric_cols = df_show.select_dtypes(include="number").columns
    first_col = df_show.columns[0]

    styled_df = (
        df_show.style
        .format({col: "{:.1f}" for col in numeric_cols}, na_rep="-")
        .hide(axis="index")
        .set_properties(subset=[first_col], **{"text-align": "left", "font-weight": "600", "background-color": "#f0f0f0", "white-space": "nowrap"})
        .set_table_styles(common_table_styles)
        .set_properties(subset=[c for c in df_show.columns if c in numeric_cols], **{"text-align": "center"})
    )
    st.markdown(f"<div style='display: flex; justify-content: left;'>{styled_df.to_html(index=False)}</div>", unsafe_allow_html=True)

    st.divider()

    st.markdown(f"### 2) 당월 클레임 내역</h5>", unsafe_allow_html=True)
    file_name = st.secrets['sheets']['f_48']
    data = load_data(file_name)
    data['실적'] /= 1000000

    df_2 = modules.create_df(this_year, current_month, data, mean="False", prev_year=1)

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
    st.markdown(f"<div style='display: flex; justify-content: left;'>{styled_df.to_html(index=True)}</div>", unsafe_allow_html=True)
    display_memo('f_48', this_year, current_month)


# =========================
# 영업외 비용 내역
# =========================
with t3:
    st.markdown("### 1) 영업외 비용 (최근 3개월)</h4>", unsafe_allow_html=True)

    csv_src = st.secrets['sheets']['f_49']
    df_raw = modules.load_nonop_cost_csv(csv_src)

    df_tbl = modules.create_nonop_cost_3month_by_g2_g4(
        year=this_year, month=current_month, data=df_raw
    )

    num_cols = [c for c in df_tbl.columns if c not in ("구분", "계정", "_row_type")]

    def _fmt(x):
        try:
            v = float(x)
        except:
            return x
        if v == 0:
            return ""
        rounded = round(v / 1_000_000)
        if rounded == 0:
            return ""
        return f"{rounded:,.0f}"

    sty = (
        df_tbl.drop(columns=[c for c in ["_row_type"] if c in df_tbl.columns])
             .style
             .format(_fmt, subset=pd.IndexSlice[:, num_cols])
             .set_properties(**{"text-align": "right", "font-family": "Noto Sans KR"})
             .set_properties(subset=pd.IndexSlice[:, ["구분", "계정"]], **{"text-align": "left"})
    )

    right_idx = df_tbl.index[df_tbl["계정"].astype(str).str.strip().isin(["고철매각작업비", "기타"])]
    sty = sty.set_properties(subset=(right_idx, ["계정"]), **{"text-align": "right", "padding-right": "12px"})

    styles_prod = []
    styles_prod.append({'selector': 'thead th', 'props': [('border-top', '3px solid gray !important')]})
    styles_prod.append({'selector': 'tbody tr:nth-child(6) td:nth-child(2)', 'props': [('border-bottom', '2px solid white !important')]})
    styles_prod.append({'selector': 'tbody tr:nth-child(7) td:nth-child(2)', 'props': [('border-bottom', '2px solid white !important')]})

    for i in range(1, 10 + 1):
        styles_prod.append({"selector": f"tbody tr:nth-child({i}) td:nth-of-type(1)", "props": [("border-bottom", "2px solid white !important")]})
    for i in range(12, 18 + 1):
        styles_prod.append({"selector": f"tbody tr:nth-child({i}) td:nth-of-type(1)", "props": [("border-bottom", "2px solid white !important")]})
    for i in range(1, 11):
        styles_prod.append({"selector": f"tbody tr:nth-child({i}) td:nth-of-type(1)", "props": [("border-right", "3px solid gray !important")]})
    for i in range(12, 20):
        styles_prod.append({"selector": f"tbody tr:nth-child({i}) td:nth-of-type(1)", "props": [("border-right", "3px solid gray !important")]})
    for i in (10, 19):
        styles_prod.append({"selector": f"tbody tr:nth-child({i}) td:nth-of-type(2)", "props": [("border-bottom", "3px solid gray !important")]})

    styles_prod.append({"selector": "td:nth-of-type(2)", "props": [("border-right", "3px solid gray !important")]})
    styles_prod.append({'selector': 'tbody tr:nth-child(11)', 'props': [('border-bottom', '3px solid gray !important')]})
    styles_prod.append({'selector': 'tbody tr:nth-child(1)', 'props': [('border-top', '3px solid gray !important')]})
    styles_prod.append({'selector': 'tbody tr:nth-child(20)', 'props': [('border-bottom', '3px solid gray !important')]})

    sty = sty.set_table_styles(styles_prod, overwrite=False)
    if hasattr(sty, "hide"):
        sty = sty.hide(axis="index")

    st.markdown(f"<div style='display:flex; justify-content:left;'>{sty.to_html(index=False)}</div>", unsafe_allow_html=True)
    display_memo('f_49', this_year, current_month)


# Footer
st.markdown("""
<style>.footer { bottom: 0; left: 0; right: 0; padding: 8px; text-align: center; font-size: 13px; color: #666666;}</style>
<div class="footer">ⓒ 2025 SeAH Special Steel Corp. All rights reserved.</div>
""", unsafe_allow_html=True)