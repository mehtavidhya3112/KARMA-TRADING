import streamlit as st
import sys, os, traceback

ROOT = os.path.abspath(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

st.set_page_config(page_title="KARMA Debug", page_icon="🔥", layout="wide")
st.title("Debug Mode")
st.write(f"ROOT path: {ROOT}")
st.write(f"sys.path: {sys.path[:3]}")
st.write(f"Files in ROOT: {os.listdir(ROOT)}")

try:
    import pytz
    st.success("pytz OK")
    import yfinance
    st.success("yfinance OK")
    import pandas
    st.success("pandas OK")
    from utils import bg_scanner
    st.success("bg_scanner OK")
except Exception as e:
    st.error(f"FAILED: {e}")
    st.code(traceback.format_exc())