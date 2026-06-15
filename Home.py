import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
import requests as py_requests
from urllib.parse import urlencode
import modules

# ======== Google OAuth2 설정 ========
GOOGLE_CLIENT_ID = st.secrets["google_oauth"]["GOOGLE_CLIENT_ID"]
GOOGLE_CLIENT_SECRET = st.secrets["google_oauth"]["GOOGLE_CLIENT_SECRET"]
REDIRECT_URI = st.secrets["google_oauth"]["REDIRECT_URI"]

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

def get_authorization_url():
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    return f"{AUTH_URL}?{urlencode(params)}"

def exchange_code_for_token(code):
    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    response = py_requests.post(TOKEN_URL, data=data)
    return response.json()

def get_user_info(access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    response = py_requests.get(USERINFO_URL, headers=headers)
    return response.json()

# ======== 페이지 설정 ========
st.set_page_config(
    page_title="세아특수강 경영실적보고",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ======== 인증 처리 ========
code = st.query_params.get("code", None)
user_info = None

if code:
    tokens = exchange_code_for_token(code)
    if tokens.get("access_token"):
        user_info = get_user_info(tokens["access_token"])
        st.session_state["user"] = user_info
else:
    user_info = st.session_state.get("user", None)

# 로그인하지 않은 경우 로그인 페이지 표시
if not user_info:
    st.markdown("<h2>Google 로그인 필요</h2>", unsafe_allow_html=True)
    st.markdown("이 서비스를 이용하려면 Google 로그인이 필요합니다.")
    auth_url = get_authorization_url()
    st.markdown(f"[👉 Google 계정으로 로그인하기]({auth_url})", unsafe_allow_html=True)
    st.stop()

# ======== 프로필 표시 + 로그아웃 ========
def render_sidebar_profile(user):
    name = user.get("name", "사용자")
    email = user.get("email", "")
    picture_url = user.get("picture", "")

    with st.sidebar:
        st.markdown("""
        <style>
        .profile-name {
            font-size: 16px;
            margin-top: 10px;
            color: #1f2937;
        }
        .profile-email {
            font-size: 13px;
            color: #6b7280;
        }
        </style>
        """, unsafe_allow_html=True)

        st.markdown('<div class="profile-box">', unsafe_allow_html=True)

        if picture_url:
            st.image(picture_url, width=80)

        st.markdown(f"<div class='profile-name'>{name}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='profile-email'>{email}</div>", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

        if st.button("🔓 로그아웃", key="logout_button"):
            for key in ["user"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

render_sidebar_profile(user_info)

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