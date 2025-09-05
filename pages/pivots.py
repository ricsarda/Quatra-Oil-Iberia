import streamlit as st
import pandas as pd
import numpy as np
from st_aggrid import AgGrid, GridOptionsBuilder

st.header("📊 Pivots – Vista preconfigurada (Jaar/Maand)")

up = st.file_uploader("Sube tu .xlsx", type=["xlsx"])
if not up:
    st.info("Selecciona un archivo para continuar.")
    st.stop()

# Lee Excel
df = pd.read_excel(up, engine="openpyxl")

# === CONFIGURACIÓN DEL PRESET (ajusta si tus nombres difieren) ===
COL_YEAR   = "Jaar"
COL_MONTH  = "Maand"
ROW_L1     = "By nature Niv0"
ROW_L2     = "By nature Niv2"
MEASURE    = "Interco Eliminations Spain"

# Orden de meses (según tu captura: jan, feb, mrt, apr, mei, jun, jul, aug, sep, okt, nov, dec)
MONTH_ORDER = ["jan","feb","mrt","apr","mei","jun","jul","aug","sep","okt","nov","dec"]

# Orden de Niv0 (según tus filas visibles)
NIV0_ORDER = [
    "Sales",
    "Inventory Change Sales",
    "Cost Of Sales",
    "Cost Of Services",
    "Other Operating Costs",
    "Other Operating Income",
    "Personnel Expenses",
    "Depreciations",
]

# ---- Filtros UI ----
if COL_YEAR not in df.columns:
    st.error(f"No encuentro la columna '{COL_YEAR}' en el Excel.")
    st.stop()

years = sorted(x for x in df[COL_YEAR].dropna().unique())
year_sel = st.selectbox("Año (Jaar)", years, index=len(years)-1)

# Filtra por año seleccionado
dff = df[df[COL_YEAR] == year_sel].copy()

# Normaliza mes a categoría ordenada
if COL_MONTH not in dff.columns:
    st.error(f"No encuentro la columna '{COL_MONTH}' en el Excel.")
    st.stop()

dff[COL_MONTH] = dff[COL_MONTH].astype(str).str.lower()
dff[COL_MONTH] = pd.Categorical(dff[COL_MONTH], categories=MONTH_ORDER, ordered=True)

# Validaciones de columnas de filas y valor
for col in [ROW_L1, ROW_L2, MEASURE]:
    if col not in dff.columns:
        st.error(f"No encuentro la columna '{col}' en el Excel.")
        st.stop()

# Pivot: filas jerárquicas (Niv0, Niv2) x columnas Mes; Valores = suma del measure
pivot = pd.pivot_table(
    dff,
    index=[ROW_L1, ROW_L2],
    columns=COL_MONTH,
    values=MEASURE,
    aggfunc="sum",
    fill_value=0,
    dropna=False,
)

# Orden de filas: primero por Niv0 (orden personalizado) y dentro por Niv2 alfabético
pivot = pivot.sort_index(level=[0,1])  # base
# Aplica orden de Niv0 con Categorical
lvl0 = pivot.index.get_level_values(0).astype(str)
order_map = {name: i for i, name in enumerate(NIV0_ORDER)}
order_series = lvl0.map(lambda x: order_map.get(x, len(NIV0_ORDER)+1))
pivot = pivot.iloc[order_series.argsort(kind="stable")]

# Asegura el orden de columnas de meses y añade "Grand Total" columna
pivot = pivot.reindex(columns=MONTH_ORDER, fill_value=0)
pivot["Grand Total"] = pivot.sum(axis=1)

# Añade fila Grand Total (total general)
total_row = pd.DataFrame([pivot.sum()], index=pd.MultiIndex.from_tuples([("Grand Total","")], names=[ROW_L1, ROW_L2]))
pivot_full = pd.concat([pivot, total_row])

# Formatea para mostrar (opcional: más limpio)
display_df = pivot_full.reset_index()

# === Muestra KPIs rápidos ===
c1, c2 = st.columns(2)
c1.metric("Total general del año", f"{pivot_full.loc[('Grand Total',''),'Grand Total']:,.2f}")
c2.metric("Filas (Niv0/Niv2)", f"{pivot.shape[0]:,}")

st.divider()

# === AG Grid ===
gb = GridOptionsBuilder.from_dataframe(display_df)

# Alineación a la derecha y separadores de miles para números
for col in MONTH_ORDER + ["Grand Total"]:
    if col in display_df.columns:
        gb.configure_column(
            col,
            type=["numericColumn"],
            valueFormatter="value == null ? '' : Intl.NumberFormat().format(value)",
            cellStyle={'textAlign':'right'},
            aggFunc="sum"
        )

# Estilos condicionales de ejemplo: resaltar totales
gb.configure_column("Grand Total",
    cellClassRules={
        'bg-total': 'true'  # toda la columna
    },
    valueFormatter="value == null ? '' : Intl.NumberFormat().format(value)",
    cellStyle={'textAlign':'right'}
)

# Colorea la fila 'Grand Total'
gb.configure_column(ROW_L1, cellClassRules={'row-total': f"value === 'Grand Total'"})

grid_options = gb.build()

st.markdown("""
<style>
.ag-theme-streamlit .bg-total { background:#E8F4FF !important; font-weight:600; }
.ag-theme-streamlit .row-total { font-weight:700; }
</style>
""", unsafe_allow_html=True)

AgGrid(
    display_df,
    gridOptions=grid_options,
    height=620,
    allow_unsafe_jscode=True
)
