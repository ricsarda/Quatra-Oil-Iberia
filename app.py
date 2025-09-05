import streamlit as st

pivots = st.Page("pages/pivots.py", title="Pivots (AG Grid)", icon=":material/pivot_table_chart:")

st.set_page_config(page_title="Analytics Hub", page_icon="📊", layout="wide")

nav = st.navigation({
    "Explorar": [pivots],
    # "Análisis": [st.Page("pages/kpis.py", title="KPIs", icon=":material/monitoring:")],
})
nav.run()
