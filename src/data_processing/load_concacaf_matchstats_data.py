from pathlib import Path
import pandas as pd
import streamlit as st


# =========================================================
#  LOADER DE DATOS - CONCACAF MATCHSTATS
# =========================================================
# Carga las métricas consolidadas de los partidos de la Copa Concacaf.
# Devuelve:
#   - df_cibao: métricas del Cibao FC (por partido)
#   - df_rivales: métricas de los rivales
# =========================================================

@st.cache_data
def load_concacaf_matchstats_data(
    filepath: str = "data/raw/concacaf/scripts/concacaf_matchstats_consolidado.csv",
):
    # --- Construir ruta absoluta desde la raíz del proyecto ---
    path = Path(__file__).parents[2] / filepath

    # --- Verificación de existencia ---
    if not path.exists():
        raise FileNotFoundError(f" No se encontró el archivo en: {path.resolve()}")

    # --- Cargar CSV consolidado ---
    try:
        df = pd.read_csv(path, encoding="utf-8-sig")
    except Exception as e:
        raise RuntimeError(f" Error al leer el CSV: {e}")

    # --- Limpieza básica ---
    df.columns = df.columns.str.strip()
    if "match_date" in df.columns:
        df["match_date"] = pd.to_datetime(df["match_date"], errors="coerce")

    # Asegurarse de que existen columnas clave
    required_cols = {"team", "home_team", "away_team", "match_id"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f" Faltan columnas requeridas: {missing}")

    # --- Filtrar partidos donde juegue Cibao FC ---
    df_cibao = df[
        (df["home_team"].str.contains("Cibao", case=False, na=False))
        | (df["away_team"].str.contains("Cibao", case=False, na=False))
    ].copy()

    # --- Identificar equipo y rival ---
    df_cibao["is_home"] = df_cibao["home_team"].str.contains("Cibao", case=False, na=False)
    df_cibao["equipo"] = df_cibao.apply(
        lambda x: x["home_team"] if x["is_home"] else x["away_team"], axis=1
    )
    df_cibao["rival"] = df_cibao.apply(
        lambda x: x["away_team"] if x["is_home"] else x["home_team"], axis=1
    )

    # --- Filtrar métricas numéricas ---
    numeric_cols = df_cibao.select_dtypes("number").columns.tolist()
    df_cibao_metrics = df_cibao[
        ["match_id", "match_date", "equipo", "rival"] + numeric_cols
    ].copy()

    # --- Crear dataset de rivales (por si se quiere comparar directamente) ---
    df_rivales = (
        df_cibao_metrics.copy()
        .rename(columns=lambda c: f"{c}_Rival" if c not in ["match_id", "match_date"] else c)
    )

    # --- Merge Cibao + Rival (por partido) ---
    df_merged = pd.merge(
        df_cibao_metrics, df_rivales, on=["match_id", "match_date"], how="left"
    )

    # --- Ordenar por fecha ---
    df_merged = df_merged.sort_values("match_date").reset_index(drop=True)

    return df_merged, df_cibao, df_rivales
