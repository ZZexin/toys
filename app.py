import streamlit as st

from modules.registry import TOOLS

st.set_page_config(page_title="Well Log Toolkit", page_icon="🛠️", layout="wide")

st.title("Well Log Toolkit")
st.caption("Extensible Streamlit workspace for well-log workflows.")

st.markdown(
    "Use the sidebar to switch pages. The home page is a launcher and roadmap for future functions."
)

st.subheader("Available Functions")
for tool in TOOLS:
    with st.container(border=True):
        st.markdown(f"### {tool['name']}")
        st.write(tool["description"])
        st.write(f"**Status:** {tool['status']}")
        st.code(tool["page"], language="text")

st.info("Next step: add new pages in `pages/` and register them in `modules/registry.py`.")
