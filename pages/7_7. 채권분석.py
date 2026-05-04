import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
import modules

warnings.filterwarnings('ignore')
st.set_page_config(layout="wide", initial_sidebar_state="expanded")

modules.create_sidebar()

year  = int(st.session_state['year'])
month = int(st.session_state['month'])

st.markdown(f"## {year}년 {month}월 채권 분석")

t1, = st.tabs(['외상매출금 및 받을어음 현황'])

with t1:
    st.markdown("<h4>1) 외상매출금 및 받을어음 현황</h4>", unsafe_allow_html=True)

    try:
        file_name = st.secrets['sheets']['f_56']
        raw = pd.read_csv(file_name, dtype=str)

        item_col = None
        for c in ['구분2', '구분1', '구분3']:
            if c in raw.columns:
                unique_vals = raw[c].astype(str).str.strip().unique().tolist()
                if any(v in unique_vals for v in ['원화', '외화', '자수', '타수']):
                    item_col = c
                    break

        if item_col is None:
            st.error("데이터에서 원화/외화/자수/타수 항목을 찾을 수 없습니다.")
            st.stop()

        raw[item_col] = raw[item_col].astype(str).str.strip()
        raw['연도'] = pd.to_numeric(raw['연도'], errors='coerce').astype('Int64')
        raw['월']   = pd.to_numeric(raw['월'],   errors='coerce').astype('Int64')
        raw['실적'] = pd.to_numeric(
            raw['실적'].astype(str).str.replace(',', '', regex=False).str.strip(),
            errors='coerce'
        ).fillna(0.0)

        def prev_month(y, m, n):
            m -= n
            while m <= 0:
                m += 12
                y -= 1
            return y, m

        yend1_y, yend1_m = year - 2, 12
        yend2_y, yend2_m = year - 1, 12
        m2_y, m2_m = prev_month(year, month, 2)
        m1_y, m1_m = prev_month(year, month, 1)
        m0_y, m0_m = year, month

        col_specs = [
            (yend1_y, yend1_m, f"{str(yend1_y)[-2:]}년 12월"),
            (yend2_y, yend2_m, f"{str(yend2_y)[-2:]}년 12월"),
            (m2_y,    m2_m,    f"{str(m2_y)[-2:]}년 {m2_m}월"),
            (m1_y,    m1_m,    f"{str(m1_y)[-2:]}년 {m1_m}월"),
            (m0_y,    m0_m,    f"{str(m0_y)[-2:]}년 {m0_m}월"),
        ]

        seen_labels, unique_specs = {}, []
        for spec in col_specs:
            label = spec[2]
            if label not in seen_labels:
                seen_labels[label] = True
                unique_specs.append(spec)
        col_specs = unique_specs
        col_labels = [s[2] for s in col_specs]

        def get_val(item, y, m):
            mask = (
                (raw[item_col] == item) &
                (raw['연도']   == y) &
                (raw['월']     == m)
            )
            vals = raw.loc[mask, '실적']
            if vals.empty:
                return 0.0
            return float(vals.sum()) / 1e8

        target_items = ['원화', '외화', '자수', '타수']
        raw_data = {}
        for item in target_items:
            raw_data[item] = {label: get_val(item, y, m) for (y, m, label) in col_specs}

        subtotal_ar   = {l: raw_data['원화'][l] + raw_data['외화'][l] for l in col_labels}
        subtotal_note = {l: raw_data['자수'][l] + raw_data['타수'][l] for l in col_labels}
        grand_total   = {l: subtotal_ar[l] + subtotal_note[l] for l in col_labels}

        base_total = grand_total[col_labels[-1]] if grand_total[col_labels[-1]] != 0 else 1

        def composition(val):
            return f"{round(val / base_total * 100)}%"

        def fmt(v):
            if v == 0:
                return ""
            return f"{int(round(v)):,}"

        table_rows = [
            ('원화',       raw_data['원화'],  False, raw_data['원화'][col_labels[-1]]),
            ('외화',       raw_data['외화'],  False, raw_data['외화'][col_labels[-1]]),
            ('외상매출금', subtotal_ar,       True,  subtotal_ar[col_labels[-1]]),
            ('자수',       raw_data['자수'],  False, raw_data['자수'][col_labels[-1]]),
            ('타수',       raw_data['타수'],  False, raw_data['타수'][col_labels[-1]]),
            ('받을어음',   subtotal_note,     True,  subtotal_note[col_labels[-1]]),
            ('합계',       grand_total,       True,  grand_total[col_labels[-1]]),
        ]

        css = """
        <style>
        .ar-table {
            border-collapse: collapse;
            font-family: 'Noto Sans KR', sans-serif;
            font-size: 14px;
        }
        .ar-table th, .ar-table td {
            border: 1px solid #999;
            padding: 7px 12px;
            text-align: right;
        }
        .ar-table thead tr {
            border-top: 2px solid #333;
            border-bottom: 2px solid #333;
        }
        .ar-table thead th {
            text-align: center;
            font-weight: 700;
            background-color: #fff;
        }
        .ar-table td.label-col {
            text-align: left;
        }
        .ar-table tr.bold-row td {
            font-weight: 700;
        }
        .ar-table tr.normal-row td {
            font-weight: 400;
        }
        .ar-table tr:last-child {
            border-bottom: 2px solid #333;
        }
        .unit-text {
            text-align: right;
            font-size: 13px;
            color: #666;
            margin-bottom: 4px;
        }
        </style>
        """

        header_html = "<thead><tr><th>구분</th>"
        for l in col_labels:
            header_html += f"<th>{l}</th>"
        header_html += "<th>구성</th></tr></thead>"

        body_html = "<tbody>"
        for label, data_dict, is_bold, comp_val in table_rows:
            row_class = "bold-row" if is_bold else "normal-row"
            body_html += f"<tr class='{row_class}'>"
            body_html += f"<td class='label-col'>{label}</td>"
            for l in col_labels:
                body_html += f"<td>{fmt(data_dict[l])}</td>"
            body_html += f"<td>{composition(comp_val)}</td>"
            body_html += "</tr>"
        body_html += "</tbody>"

        html = f"""
        {css}
        <div class='unit-text'>[단위 : 억원, %]</div>
        <table class='ar-table'>
            {header_html}
            {body_html}
        </table>
        """

        st.markdown(html, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"외상매출금 및 받을어음 현황 표 생성 중 오류: {e}")