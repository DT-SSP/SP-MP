import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
import modules

# ======== 스타일 ========
custom_home_css = """
<style>
body {
    background-color: #ffffff;
    margin: 0 !important;
    padding: 0 !important;
}
.block-container {
    padding-top: 1rem !important;
}
.centered {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    margin-top: 60px;
}
.centered img {
    margin-bottom: 20px;
}
h1 {
    font-size: 38px;
    font-weight: 700;
    color: #2c3e50;
}
.section-label {
    font-size: 16px;
    color: #000000;
    font-weight: bold;
    margin-bottom: 10px;
}
.card {
    background-color: #f9fbfd;
    padding: 14px 18px;
    border-radius: 10px;
    margin-bottom: 16px;
    font-size: 15px;
    line-height: 1.5;
}
</style>
"""

st.set_page_config(
    page_title="세아특수강 경영실적보고",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(custom_home_css, unsafe_allow_html=True)

# ======== 상단 타이틀 ========
st.markdown('<div class="centered">', unsafe_allow_html=True)
st.image("logo.gif", width=200)
st.markdown("## 세아특수강 경영 실적 보고", unsafe_allow_html=True)
st.divider()

# ======== 본문 콘텐츠 구성 ========
top_left, top_right = st.columns([1, 1])

with top_left:
    st.markdown("<div class='section-label'>📌 대시보드 개요</div>", unsafe_allow_html=True)
    st.markdown("""
    <div class='card'>
        세아특수강의 월별 실적을 체계적으로 관리하기 위한 DX 기반 분석 시스템입니다.<br>
        당월 기준 실적 및 예상 비교, 누적 당성률, 메모 등을 한눈에 확인할 수 있습니다.
    </div>
    """, unsafe_allow_html=True)

with top_right:
    st.markdown("<div class='section-label'>🎯 활용 목적</div>", unsafe_allow_html=True)
    st.markdown("""
    <div class='card'>
        매출부터 생산, 비용, 재고, 채권, 손익 등 주요 경영 지표 현황을 직관적으로 파악하고, 월별 성과와 차이를 분석하며<br>
        전략 방향성을 개선하기 위한 실시간 참고 자료로 사용 가능합니다.
    </div>
    """, unsafe_allow_html=True)

# ======== 푸터 ========
st.markdown("""
<style>
.footer {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    padding: 8px;
    background-color: rgba(255, 255, 255, 0.9);
    text-align: center;
    font-size: 13px;
    color: #666666;
    z-index: 100;
    box-shadow: 0 -1px 4px rgba(0, 0, 0, 0.05);
}
</style>
<div class="footer">
  ⓒ 2025 SeAH Special Steel Corp. All rights reserved.
</div>
""", unsafe_allow_html=True)