import streamlit as st
import pandas as pd
import numpy as np

# ------------------------ utilidades ------------------------
MONTHS_NL = ["jan","feb","mrt","apr","mei","jun","jul","aug","sep","okt","nov","dec"]

def order_month_series(s: pd.Series) -> pd.Series:
    s2 = s.astype(str).str.lower().str.strip()
    return pd.Categorical(s2, categories=MONTHS_NL, ordered=True)

def robust_metrics_by_row(arr: np.ndarray):
    """
    arr: shape (n_rows, n_months)
    Devuelve median (n,), MAD(n,), robust_z (n, m)
    """
    med = np.nanmedian(arr, axis=1)
    mad = np.nanmedian(np.abs(arr - med[:, None]), axis=1)
    robust_z = np.abs(arr - med[:, None]) / (mad[:, None] + 1e-9)
    return med, mad, robust_z

def pct_change_along_months(arr: np.ndarray):
    """
    %Δ mes a mes por fila: (v_t - v_{t-1}) / |v_{t-1}|
    shape (n, m-1) -> lo expandimos a (n, m) con NaN en la 1ª col
    """
    prev = arr[:, :-1]
    curr = arr[:, 1:]
    pct = (curr - prev) / (np.abs(prev) + 1e-9)
    pct = np.concatenate([np.full((arr.shape[0], 1), np.nan), pct], axis=1)
    return pct

# ------------------------ página ------------------------
st.header("🔎 Checks de consistencia por mes y 'By nature Niv2'")

up = st.file_uploader("Sube tu Excel (.xlsx)", type=["xlsx"])
if not up:
    st.info("Sube un archivo para comenzar.")
    st.stop()

# Selector de hoja (si hay varias)
xls = pd.ExcelFile(up)
sheet = st.selectbox("Hoja", xls.sheet_names, index=0)
df = pd.read_excel(up, sheet_name=sheet, engine="openpyxl")

# Selección de columnas
all_cols = df.columns.tolist()
num_cols = df.select_dtypes(include="number").columns.tolist()

month_col = st.selectbox("Columna de mes", [c for c in all_cols if c.lower().startswith("maa") or c.lower()=="maand"] + all_cols, index=0)
group_col = st.selectbox("Columna 'By nature Niv2'", [c for c in all_cols if "niv2" in c.lower()] + all_cols, index=0)
value_col = st.selectbox("Métrica numérica a auditar", num_cols, index=(num_cols.index("Interco Eliminations Spain") if "Interco Eliminations Spain" in num_cols else 0))

# Parámetros (ajústalos a tu negocio)
with st.expander("Parámetros de detección"):
    z_thr   = st.slider("Umbral robust-z", 1.0, 6.0, 3.5, 0.1)
    pct_thr = st.slider("Umbral |%Δ| mes a mes", 0.10, 5.0, 1.00, 0.05, help="1.00 = ±100%")
    cv_thr  = st.slider("Umbral CV por Niv2 (resumen)", 0.05, 2.0, 0.60, 0.05)
    min_abs = st.number_input("Mínimo |valor| para considerar (evitar ruido)", 0.0, 1e12, 0.0, 100.0)

# Prepara datos: agrega por mes y Niv2
work = df.copy()
work[month_col] = order_month_series(work[month_col])
grp = (
    work.groupby([group_col, month_col], dropna=False)[value_col]
        .sum(min_count=1)
        .reset_index()
)

# Matriz Niv2 x Mes (orden NL) para cálculos
pivot = grp.pivot(index=group_col, columns=month_col, values=value_col).reindex(columns=MONTHS_NL, fill_value=0)
pivot = pivot.fillna(0.0)
vals = pivot.to_numpy(dtype=float)  # (n_niv2, 12)

# Métricas
med, mad, rZ = robust_metrics_by_row(vals)            # robust-z vs mediana del Niv2
pct = pct_change_along_months(vals)                   # %Δ mes a mes por Niv2
std = np.nanstd(vals, axis=1)
mean_abs = np.nanmean(np.abs(vals), axis=1)
cv = std / (mean_abs + 1e-9)

# Signo “dominante” por Niv2 (mediana) y flag de cambio de signo por celda
sign_base = np.sign(med)
sign_flip = (np.sign(vals) != 0) & (np.sign(vals) != sign_base[:, None])

# Reglas de anomalía por celda
anomaly_rZ  = (rZ >= z_thr) & (np.abs(vals) >= min_abs)
anomaly_pct = (np.abs(pct) >= pct_thr) & (np.abs(vals) >= min_abs)
anomaly_flip = sign_flip & (np.abs(vals) >= min_abs)

any_anom = anomaly_rZ | anomaly_pct | anomaly_flip

# ---- Resumen por Niv2
summary = pd.DataFrame({
    group_col: pivot.index,
    "CV": cv,
    "Meses_anómalos": any_anom.sum(axis=1).astype(int),
    "Mediana": med,
    "MAD": mad,
    "Total_anual_abs": np.abs(vals).sum(axis=1)
}).sort_values(["Meses_anómalos","CV","Total_anual_abs"], ascending=[False, False, False])

st.subheader("Resumen por 'By nature Niv2'")
st.dataframe(summary, use_container_width=True)

# ---- Detalle por celda (Niv2, mes)
long = pivot.reset_index().melt(id_vars=[group_col], var_name="Mes", value_name="Valor")
long["robust_z"] = rZ.reshape(-1, rZ.shape[1]).ravel(order="C")  # mismo orden que pivot? Aseguremos:
# Mejor calcular de forma alineada:
# construimos DataFrame desde matrices para alinear
rZ_df   = pd.DataFrame(rZ, index=pivot.index, columns=pivot.columns).reset_index().melt(id_vars=[group_col], var_name="Mes", value_name="robust_z")
pct_df  = pd.DataFrame(pct, index=pivot.index, columns=pivot.columns).reset_index().melt(id_vars=[group_col], var_name="Mes", value_name="pct_change")
flip_df = pd.DataFrame(anomaly_flip, index=pivot.index, columns=pivot.columns).reset_index().melt(id_vars=[group_col], var_name="Mes", value_name="flip_signo")

# Unimos
det = long.merge(rZ_df, on=[group_col,"Mes"]).merge(pct_df, on=[group_col,"Mes"]).merge(flip_df, on=[group_col,"Mes"])

# Flags
det["anom_rZ"] = (det["robust_z"] >= z_thr) & (det["Valor"].abs() >= min_abs)
det["anom_%"]  = (det["pct_change"].abs() >= pct_thr) & (det["Valor"].abs() >= min_abs)
det["anom"]    = det["anom_rZ"] | det["anom_%"] | det["flip_signo"]

# Severidad heurística
det["score"] = det[["robust_z", "pct_change"]].abs().max(axis=1)
det = det[det["anom"]].sort_values(["score","Valor"], ascending=[False, False])

st.subheader("Detalle de anomalías (por Niv2 y mes)")
st.dataframe(det, use_container_width=True)

# ---- Mapa de calor simple (opcional)
st.subheader("Mapa rápido (celdas anómalas en rojo)")
styled = pivot.style.apply(lambda row: [
    "background-color:#ffdddd" if any_anom[row.name][i] else "" for i, _ in enumerate(row)
], axis=1).format(lambda v: f"{v:,.0f}")
st.dataframe(styled, use_container_width=True)

# Descarga
st.download_button("⬇️ Descargar anomalías (CSV)", data=det.to_csv(index=False).encode("utf-8"), file_name="anomalias_niv2_mes.csv", mime="text/csv")
