import streamlit as st
import pandas as pd
import numpy as np

MONTHS = ["jan","feb","mrt","apr","mei","jun","jul","aug","sep","okt","nov","dec"]

def order_month(s):
    s2 = s.astype(str).str.lower().str.strip()
    return pd.Categorical(s2, categories=MONTHS, ordered=True)

st.header("🔎 Análisis de variación mes a mes y CV")

up = st.file_uploader("Sube tu Excel", type=["xlsx"])
if not up:
    st.stop()

df = pd.read_excel(up, engine="openpyxl")

month_col = "Maand"
niv2_col  = "By nature Niv2"
val_col   = "Interco Eliminations Spain"

# Prepara datos
df[month_col] = order_month(df[month_col])
grp = df.groupby([niv2_col, month_col])[val_col].sum(min_count=1).reset_index()

pivot = grp.pivot(index=niv2_col, columns=month_col, values=val_col).reindex(columns=MONTHS, fill_value=0)
vals = pivot.to_numpy(float)

# % variación mes a mes
pct = (vals[:,1:] - vals[:,:-1]) / (np.abs(vals[:,:-1]) + 1e-9)
pct = np.concatenate([np.full((vals.shape[0],1), np.nan), pct], axis=1)

# CV por Niv2
std = np.nanstd(vals, axis=1)
mean_abs = np.nanmean(np.abs(vals), axis=1)
cv = std / (mean_abs + 1e-9)

# Resumen
summary = pd.DataFrame({
    niv2_col: pivot.index,
    "CV": cv,
    "Meses con salto fuerte": (np.abs(pct) > 0.5).sum(axis=1)  # >50%
}).sort_values("CV", ascending=False)

st.subheader("Resumen por Niv2")
st.dataframe(summary, use_container_width=True)

# Detalle de anomalías
det = []
for i, niv in enumerate(pivot.index):
    for j, m in enumerate(pivot.columns):
        if j == 0: continue
        if np.abs(pct[i,j]) > 0.5:  # umbral configurable
            det.append({
                niv2_col: niv,
                "Mes": m,
                "Valor": vals[i,j],
                "%Δ vs prev": pct[i,j]
            })

det = pd.DataFrame(det)
st.subheader("Detalle de saltos (>50%)")
st.dataframe(det, use_container_width=True)

# Mapa visual
st.subheader("Mapa visual de anomalías")
styled = pivot.style.apply(lambda row: [
    "background-color:#ffdddd" if not np.isnan(pct[row.name==pivot.index,i]) and np.abs(pct[row.name==pivot.index,i])>0.5 else "" 
    for i in range(len(row))
], axis=1).format("{:,.0f}".format)
st.dataframe(styled, use_container_width=True)
