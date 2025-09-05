import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder

st.header("📊 Pivots – modo libre (drag & drop) y vista preset")
up = st.file_uploader("Sube tu .xlsx", type=["xlsx"])
if not up:
    st.info("Selecciona un archivo para continuar.")
    st.stop()

df = pd.read_excel(up, engine="openpyxl")

modo_libre = st.toggle("🔀 Modo libre (drag & drop tipo Excel)", value=True)

if modo_libre:
    st.caption("Arrastra campos en el panel de columnas/pivot. (Requiere AG Grid Enterprise)")
    gb = GridOptionsBuilder.from_dataframe(df)

    # Habilitar capacidades de Pivot/Group/Value en TODAS las columnas
    gb.configure_default_column(
        enablePivot=True, enableRowGroup=True, enableValue=True,
        filter=True, floatingFilter=True    # filtros visibles bajo cabeceras
    )

    # Construimos y ajustamos opciones del grid para modo Pivot + paneles
    go = gb.build()
    go["pivotMode"] = True                                 # activa el modo Pivot
    go["sideBar"] = {                                     # panel lateral de columnas y filtros
        "toolPanels": ["columns", "filters"],
        "defaultToolPanel": "columns"
    }
    go["pivotPanelShow"] = "always"                       # muestra el Pivot Panel arriba
    # Puedes iniciar con algunos campos ya colocados si quieres:
    # por ejemplo, que Jaar vaya a columnas y Maand también:
    # for coldef in go["columnDefs"]:
    #     if coldef["field"] == "Jaar":
    #         coldef["pivot"] = True
    #     if coldef["field"] == "Maand":
    #         coldef["pivot"] = True
    #     if coldef["field"] in ["By nature Niv0", "By nature Niv2"]:
    #         coldef["rowGroup"] = True
    #     if coldef["field"] == "Interco Eliminations Spain":
    #         coldef["aggFunc"] = "sum"

    # Para ocultar "ceros" en MODO LIBRE:
    # - Activa filtros numéricos (ya activados arriba) y usa el filtro "not equal 0"
    #   en las columnas de valores que tengas en ese momento.
    #   También puedes predefinir un filterModel si conoces el nombre de la columna visible.
    #   (El nombre de la columna agregada cambia según el pivot, por eso no lo fijo aquí.)
    AgGrid(
        df,
        gridOptions=go,
        height=650,
        allow_unsafe_jscode=True,
        enable_enterprise_modules=True,   # <-- imprescindible para Pivot/ToolPanels Enterprise
        # license_key="TU-CLAVE-SI-LA-TIENES"
    )

else:
    # ---------- VISTA PRESET (pandas) ----------
    # Ajusta estos nombres a tu dataset real:
    COL_YEAR   = "Jaar"
    COL_MONTH  = "Maand"
    ROW_L1     = "By nature Niv0"
    ROW_L2     = "By nature Niv2"
    MEASURE    = "Interco Eliminations Spain"

    MONTH_ORDER = ["jan","feb","mrt","apr","mei","jun","jul","aug","sep","okt","nov","dec"]
    NIV0_ORDER = [
        "Sales","Inventory Change Sales","Cost Of Sales","Cost Of Services",
        "Other Operating Costs","Other Operating Income","Personnel Expenses",
        "Depreciations","Volume"
    ]

    if COL_YEAR not in df.columns or COL_MONTH not in df.columns:
        st.error("No encuentro columnas Jaar/Maand en el Excel.")
        st.stop()

    years = sorted(df[COL_YEAR].dropna().unique())
    year_sel = st.selectbox("Año (Jaar)", years, index=len(years)-1)
    dff = df[df[COL_YEAR] == year_sel].copy()

    dff[COL_MONTH] = dff[COL_MONTH].astype(str).str.lower()
    dff[COL_MONTH] = pd.Categorical(dff[COL_MONTH], categories=MONTH_ORDER, ordered=True)

    for col in [ROW_L1, ROW_L2, MEASURE]:
        if col not in dff.columns:
            st.error(f"Falta la columna '{col}' en el Excel.")
            st.stop()

    pivot = pd.pivot_table(
        dff, index=[ROW_L1, ROW_L2], columns=COL_MONTH, values=MEASURE,
        aggfunc="sum", fill_value=0, dropna=False
    )
    # Orden filas por Niv0 custom
    order_map = {name: i for i, name in enumerate(NIV0_ORDER)}
    lvl0 = pivot.index.get_level_values(0).astype(str).map(lambda x: order_map.get(x, 999))
    pivot = pivot.iloc[lvl0.argsort(kind="stable")]
    # Reordenar meses y añadir total
    pivot = pivot.reindex(columns=MONTH_ORDER, fill_value=0)
    pivot["Total Año"] = pivot.sum(axis=1)

    # 🔎 Ocultar filas cuyo total (o todos los meses) sea 0
    mask = pivot.abs().sum(axis=1) != 0
    pivot = pivot[mask]

    # Fila Grand Total
    total_row = pd.DataFrame([pivot.sum()], index=pd.MultiIndex.from_tuples([("Grand Total","")], names=[ROW_L1, ROW_L2]))
    pivot_full = pd.concat([pivot, total_row])

    out = pivot_full.reset_index()

    gb = GridOptionsBuilder.from_dataframe(out)
    for c in MONTH_ORDER + ["Total Año"]:
        if c in out.columns:
            gb.configure_column(
                c, type=["numericColumn"],
                valueFormatter="value == null ? '' : Intl.NumberFormat().format(value)",
                cellStyle={"textAlign":"right"}, aggFunc="sum"
            )
    gb.configure_column(ROW_L1, cellClassRules={"row-total": "value === 'Grand Total'"})
    go = gb.build()

    st.markdown("""
    <style>
    .ag-theme-streamlit .row-total { font-weight:700; }
    </style>
    """, unsafe_allow_html=True)

    AgGrid(out, gridOptions=go, height=650, allow_unsafe_jscode=True)
