import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder

st.header("📊 Pivots (sin licencia Enterprise)")

up = st.file_uploader("Sube un .xlsx", type=["xlsx"])
if not up:
    st.info("Selecciona un archivo para continuar.")
    st.stop()

df = pd.read_excel(up, engine="openpyxl")

tab_preset, tab_flexible = st.tabs(["🎯 Vista preset", "🛠️ Vista flexible"])

# -------------------- VISTA PRESET --------------------
with tab_preset:
    # Nombres según tus capturas (ajústalos si difieren)
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

    missing = [c for c in [COL_YEAR, COL_MONTH, ROW_L1, ROW_L2, MEASURE] if c not in df.columns]
    if missing:
        st.error(f"Faltan columnas en el Excel: {missing}")
        st.stop()

    # Filtros adicionales opcionales (como en tu Excel)
    with st.expander("Filtros"):
        resp_col = st.selectbox("Responsible (opcional)", ["(Todos)"] + sorted(df["Responsible"].dropna().unique().tolist())) \
            if "Responsible" in df.columns else "(Todos)"
        bl_col   = st.selectbox("Business Line (opcional)", ["(Todos)"] + sorted(df["Business Line"].dropna().unique().tolist())) \
            if "Business Line" in df.columns else "(Todos)"
        comp_col = st.selectbox("Company (opcional)", ["(Todos)"] + sorted(df["Company"].dropna().unique().tolist())) \
            if "Company" in df.columns else "(Todos)"

    years = sorted(df[COL_YEAR].dropna().unique())
    year_sel = st.selectbox("Año (Jaar)", years, index=len(years)-1)

    dff = df[df[COL_YEAR] == year_sel].copy()
    if resp_col != "(Todos)" and "Responsible" in dff.columns:
        dff = dff[dff["Responsible"] == resp_col]
    if bl_col != "(Todos)" and "Business Line" in dff.columns:
        dff = dff[dff["Business Line"] == bl_col]
    if comp_col != "(Todos)" and "Company" in dff.columns:
        dff = dff[dff["Company"] == comp_col]

    dff[COL_MONTH] = dff[COL_MONTH].astype(str).str.lower()
    dff[COL_MONTH] = pd.Categorical(dff[COL_MONTH], categories=MONTH_ORDER, ordered=True)

    pivot = pd.pivot_table(
        dff, index=[ROW_L1, ROW_L2], columns=COL_MONTH, values=MEASURE,
        aggfunc="sum", fill_value=0, dropna=False
    )

    # Orden Niv0 personalizado
    order_map = {name: i for i, name in enumerate(NIV0_ORDER)}
    lvl0 = pivot.index.get_level_values(0).astype(str).map(lambda x: order_map.get(x, 999))
    pivot = pivot.iloc[lvl0.argsort(kind="stable")]

    # Reordenar meses, total columna y ocultar filas "todo 0" si se marca
    pivot = pivot.reindex(columns=MONTH_ORDER, fill_value=0)
    pivot["Total Año"] = pivot.sum(axis=1)

    hide_zero = st.checkbox("Ocultar líneas con total 0", value=True)
    if hide_zero:
        pivot = pivot[pivot.abs().sum(axis=1) != 0]

    # Fila Grand Total
    total_row = pd.DataFrame([pivot.sum()], index=pd.MultiIndex.from_tuples([("Grand Total","")], names=[ROW_L1, ROW_L2]))
    out = pd.concat([pivot, total_row]).reset_index()

    # Mostrar en AG Grid
    gb = GridOptionsBuilder.from_dataframe(out)
    for c in [*MONTH_ORDER, "Total Año"]:
        if c in out.columns:
            gb.configure_column(c, type=["numericColumn"],
                                valueFormatter="value == null ? '' : Intl.NumberFormat().format(value)",
                                cellStyle={"textAlign": "right"}, aggFunc="sum")
    gb.configure_column(ROW_L1, cellClassRules={"row-total": "value === 'Grand Total'"})
    go = gb.build()

    st.markdown("""
    <style>
    .ag-theme-streamlit .row-total { font-weight:700; }
    </style>
    """, unsafe_allow_html=True)

    AgGrid(out, gridOptions=go, height=620, allow_unsafe_jscode=True)

# -------------------- VISTA FLEXIBLE --------------------
with tab_flexible:
    st.caption("Elige filas/columnas/valor/función. Recalculamos la pivot con pandas (sin drag & drop).")

    # Selección de campos
    all_cols = df.columns.tolist()
    num_cols = df.select_dtypes(include="number").columns.tolist()

    cols_rows = st.multiselect("Filas", [c for c in all_cols if c not in num_cols], default=["By nature Niv0","By nature Niv2"] if "By nature Niv0" in all_cols and "By nature Niv2" in all_cols else [])
    col_cols  = st.selectbox("Columnas", [None] + [c for c in all_cols if c not in num_cols], index=( [None] + [c for c in all_cols if c not in num_cols] ).index("Maand") if "Maand" in all_cols else 0)
    val_col   = st.selectbox("Valor (numérico)", num_cols, index=(num_cols.index("Interco Eliminations Spain") if "Interco Eliminations Spain" in num_cols else 0))
    agg       = st.selectbox("Agregación", ["sum","mean","median","max","min","count"], index=0)

    # Filtros rápidos (opcionales)
    with st.expander("Filtros opcionales"):
        filt_year = st.selectbox("Filtrar Jaar", ["(Todos)"] + sorted(df["Jaar"].dropna().unique().tolist())) if "Jaar" in df.columns else "(Todos)"
        filt_company = st.selectbox("Filtrar Company", ["(Todos)"] + sorted(df["Company"].dropna().unique().tolist())) if "Company" in df.columns else "(Todos)"
    dff2 = df.copy()
    if "Jaar" in dff2.columns and filt_year != "(Todos)":
        dff2 = dff2[dff2["Jaar"] == filt_year]
    if "Company" in dff2.columns and filt_company != "(Todos)":
        dff2 = dff2[dff2["Company"] == filt_company]

    # Orden meses si el usuario usa Maand como columnas
    if col_cols == "Maand" and "Maand" in dff2.columns:
        month_order = ["jan","feb","mrt","apr","mei","jun","jul","aug","sep","okt","nov","dec"]
        dff2["Maand"] = dff2["Maand"].astype(str).str.lower()
        dff2["Maand"] = pd.Categorical(dff2["Maand"], categories=month_order, ordered=True)

    if not cols_rows and not col_cols:
        st.warning("Selecciona al menos una fila o una columna.")
    else:
        pt = pd.pivot_table(
            dff2, index=cols_rows if cols_rows else None, columns=col_cols if col_cols else None,
            values=val_col, aggfunc=agg, fill_value=0, dropna=False
        )

        # Quitar filas todo 0 si se marca
        hide_zero2 = st.checkbox("Ocultar filas con todo 0", value=False, key="hide0flex")
        if hide_zero2:
            pt = pt[(pt.abs().sum(axis=1) if isinstance(pt, pd.DataFrame) else (pt != 0)) != 0]

        out2 = pt.reset_index() if isinstance(pt, pd.DataFrame) else pt.to_frame().reset_index()

        gb2 = GridOptionsBuilder.from_dataframe(out2)
        for c in out2.select_dtypes(include="number").columns:
            gb2.configure_column(c, type=["numericColumn"],
                                 valueFormatter="value == null ? '' : Intl.NumberFormat().format(value)",
                                 cellStyle={"textAlign": "right"})
        go2 = gb2.build()
        AgGrid(out2, gridOptions=go2, height=620, allow_unsafe_jscode=True)
