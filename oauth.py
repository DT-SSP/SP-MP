# auth.py
import streamlit as st

ALLOWED_USERS = st.secrets["admin"]["allowed_emails"]

def require_login():
    user = st.session_state.get("user")
    if not user:
        st.error("⛔ 로그인 필요: 먼저 홈 화면에서 로그인해 주세요.")
        st.stop()
    elif user.get("email") not in ALLOWED_USERS:
        st.error("⛔ 접근 불가: 권한이 없습니다.")
        st.stop()
