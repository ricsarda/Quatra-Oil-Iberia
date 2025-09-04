import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder

df = pd.read_excel("datos.xlsx")
# Ejemplo: ratios
df["Margen_%"] = (df["Ventas"] - df["Coste"]) / df["Ventas"] * 100
df["Variación_%"] = df.groupby("Producto")["Ventas"].pct_change()*100

st.title("Pivot + KPIs + Formato condicional")
col1, col2, col3 = st.columns(3)
col1.metric("Ventas totales", f"{df['Ventas'].sum():,.0f}€")
col2.metric("Margen medio", f"{df['Margen_%'].mean():.2f}%")
col3.metric("Productos", f"{df['Producto'].nunique()}")

gb = GridOptionsBuilder.from_dataframe(df)
gb.configure_default_column(enableValue=True, enableRowGroup=True, enablePivot=True)  # pivot requiere Enterprise
# Formato condicional por reglas en 'Margen_%'
gb.configure_column(
    "Margen_%", type=["numericColumn"],
    cellStyle={'textAlign': 'right'},
    cellClassRules={
        'bg-good': 'x >= 30',   # verde si >=30%
        'bg-warn': 'x < 30 && x >= 15',
        'bg-bad':  'x < 15'
    },
    valueFormatter="value?.toFixed(2) + '%'"
)
go = gb.build()

AgGrid(
    df,
    gridOptions=go,
    enable_enterprise_modules=True,  # requiere licencia para pivot/rowGroup/sideBar
    height=500,
    allow_unsafe_jscode=True
)
