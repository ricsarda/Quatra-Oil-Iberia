
import streamlit as st

# Define páginas (por archivo o por función)
home = st.Page("pages/pivots.py", title="Pivots (AG Grid)", icon=":material/pivot_table_chart:")

# En el futuro, añade más páginas:
# kpis = st.Page("pages/kpis.py", title="KPIs y gráficos", icon=":material/monitoring:")
# limpieza = st.Page("pages/cleaning.py", title="Limpieza de datos", icon=":material/cleaning_services:")

st.set_page_config(page_title="Analytics Hub", page_icon="📊", layout="wide")

# Menú de navegación (puedes agrupar en secciones)
pg = st.navigation({
    "Explorar": [home],
    # "Análisis": [kpis],
    # "Herramientas": [limpieza],
})

# Ejecuta la página seleccionada
pg.run()

