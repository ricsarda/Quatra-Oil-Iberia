import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder

st.header("📊 Pivots interactivos (sube tu Excel)")

up = st.file_uploader("Sube un .xlsx", type=["xlsx"])
if not up:
    st.info("Selecciona un archivo para continuar.")
    st.stop()

# Lee el fichero subido (file-like) con openpyxl:
df = pd.read_excel(up, engine="openpyxl")  # <- aquí estaba tu error

# Ratios opcionales (ajusta nombres de columnas a tu caso)
df = df.copy()
if {"Ventas", "Coste"} <= set(df.columns):
    ventas = df["Ventas"].replace(0, pd.NA)
    df["Margen_%"] = (df["Ventas"] - df["Coste"]) / ventas * 100
if {"Producto", "Ventas"} <= set(df.columns):
    df = df.sort_values(["Producto"])
    df["Variación_%"] = df.groupby("Producto")["Ventas"].pct_change() * 100

c1, c2, c3 = st.columns(3)
if "Ventas" in df.columns:
    c1.metric("Ventas totales", f"{df['Ventas'].sum():,.0f}")
if "Margen_%" in df.columns:
    c2.metric("Margen medio", f"{pd.to_numeric(df['Margen_%'], errors='coerce').mean():.2f}%")
c3.metric("Filas", f"{len(df):,}")

st.divider()

gb = GridOptionsBuilder.from_dataframe(df)
gb.configure_default_column(enableValue=True, enableRowGroup=True, enablePivot=True)  # pivot real = Enterprise
gb.configure_side_bar()

if "Margen_%" in df.columns:
    gb.configure_column(
        "Margen_%", type=["numericColumn"],
        valueFormatter="value == null ? '' : (Number(value).toFixed(2) + '%')",
        cellStyle={'textAlign': 'right'},
        cellClassRules={
            'bg-good': 'Number(x) >= 30',
            'bg-warn': 'Number(x) < 30 && Number(x) >= 15',
            'bg-bad':  'Number(x) < 15'
        },
    )

for col in df.select_dtypes(include="number").columns:
    gb.configure_column(col, aggFunc="sum")

st.markdown("""
<style>
.ag-theme-streamlit .bg-good { background: #d2f8d2 !important; }
.ag-theme-streamlit .bg-warn { background: #fff5cc !important; }
.ag-theme-streamlit .bg-bad  { background: #ffd6d6 !important; }
</style>
""", unsafe_allow_html=True)

AgGrid(
    df,
    gridOptions=gb.build(),
    height=620,
    enable_enterprise_modules=True,   # si tienes licencia, tendrás Pivot
    allow_unsafe_jscode=True
)
