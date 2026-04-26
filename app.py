import streamlit as st
import sys, os, traceback

ROOT = os.path.abspath(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

st.set_page_config(page_title="KARMA PA Scanner", page_icon="🔥", layout="wide")

try:
    from utils.bg_scanner import BgScanner
    st.success("Utils loaded successfully!")
except Exception as e:
    st.error(f"Import error: {e}")
    st.code(traceback.format_exc())
    st.stop()

st.title("KARMA PRICE ACTION SCANNER")
st.write("App is working!")