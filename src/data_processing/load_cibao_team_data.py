from pathlib import Path
import pandas as pd
import streamlit as st
import re

# =========================================================
#  LOADER DE DATOS - CIBAO FC
# =========================================================
# Carga los datos de la hoja "Cibao" del archivo Excel principal.
# Devuelve:
#   - df_cibao: métricas del Cibao FC (por partido)
#   - df_rivales: métricas de los rivales emparejados
# =========================================================

def extract_team_from_match_str(match_str):
    """Helper function to extract team name from match string."""
    if pd.isna(match_str) or not match_str:
        return ""
    match_str = str(match_str)
    # Format: "Cibao - Universidad O&M 2:1" or "Atlántico - Cibao 0:5"
    parts = match_str.replace(" vs ", " - ").split(" - ")
    if len(parts) >= 2:
        # Check if Cibao is in first part (home)
        if "Cibao" in parts[0]:
            return "Cibao"
        # Check if Cibao is in second part (away)
        elif "Cibao" in parts[1]:
            return "Cibao"
    return ""

@st.cache_data
def load_cibao_team_data(filepath: str = "data/raw/wyscout/Global/Liga_Mayor_Clean_Per_90.xlsx"):
    """
    Carga datos de Cibao desde archivos procesados.
    Prioridad: JSON files (nuevos) > Excel file (fallback)
    """
    # First try to load from processed JSON files (newest data)
    try:
        from src.data_processing.loaders import load_per90_data
        df_all = load_per90_data()
        
        if not df_all.empty and "Team" in df_all.columns:
            # Filter for Cibao
            df_cibao = df_all[df_all["Team"].str.lower() == "cibao"].copy()
            df_rivales = df_all[df_all["Team"].str.lower() != "cibao"].copy()
            
            if not df_cibao.empty:
                # Merge with opponent data (same as Excel logic below)
                if "Date" in df_cibao.columns:
                    df_cibao["Date"] = pd.to_datetime(df_cibao["Date"], errors="coerce")
                df_cibao = df_cibao.dropna(subset=["Team"])
                df_cibao = df_cibao.sort_values("Date").reset_index(drop=True)
                
                # Add opponent columns if Match column exists
                if "Match" in df_cibao.columns and not df_rivales.empty:
                    df_rivales_renamed = df_rivales.rename(
                        columns=lambda x: f"{x}_Rival" if x not in ["Match", "Date"] else x
                    )
                    df_cibao = pd.merge(df_cibao, df_rivales_renamed, on=["Match", "Date"], how="left")
                
                return df_cibao, df_rivales
    except Exception as e:
        # Fall through to Excel loading if JSON fails
        pass
    
    # Fallback: Load from Excel file
    # --- Construir ruta absoluta desde la raíz del proyecto ---
    path = Path(__file__).parents[2] / filepath

    # --- Verificación de existencia ---
    #  NO USAMOS st.error() dentro de una función cacheada → levantamos una excepción
    if not path.exists():
        raise FileNotFoundError(f" No se encontró el archivo en: {path.resolve()}")

    # --- Cargar hoja específica ---
    try:
        # First try to load "Cibao" sheet
        df = pd.read_excel(path, sheet_name="Cibao")
    except (ValueError, KeyError) as e:
        # If "Cibao" sheet doesn't exist, try "TeamStats" sheet and filter for Cibao
        try:
            xls = pd.ExcelFile(path)
            if "TeamStats" in xls.sheet_names:
                df = pd.read_excel(path, sheet_name="TeamStats")
                # Extract team names from Match column if Team column is not valid
                if "Team" in df.columns and len(df) > 0 and df["Team"].iloc[0] == "TeamStats":
                    # Extract team names from Match column
                    if "Match" in df.columns:
                        # Create rows for Cibao matches only
                        all_rows = []
                        for idx, row in df.iterrows():
                            match_str = row.get("Match", "")
                            if pd.notna(match_str) and match_str and "Cibao" in str(match_str):
                                row_copy = row.copy()
                                row_copy["Team"] = "Cibao"
                                all_rows.append(row_copy)
                        if all_rows:
                            df = pd.DataFrame(all_rows)
                        else:
                            raise RuntimeError(f" No se encontraron partidos de Cibao en el archivo Excel")
                    else:
                        raise RuntimeError(f" No se pudo determinar los equipos desde el archivo Excel")
                else:
                    # Filter for Cibao only if Team column is valid
                    if "Team" in df.columns:
                        df = df[df["Team"].str.lower() == "cibao"].copy()
                        if df.empty:
                            raise RuntimeError(f" No se encontraron datos de Cibao en el archivo Excel")
            else:
                # Try first available sheet
                sheet_names = xls.sheet_names
                if sheet_names:
                    df = pd.read_excel(path, sheet_name=sheet_names[0])
                    # Filter for Cibao if Team column exists
                    if "Team" in df.columns:
                        df = df[df["Team"].str.lower() == "cibao"].copy()
                else:
                    raise RuntimeError(f" El archivo Excel no contiene hojas")
        except Exception as e2:
            raise RuntimeError(f" Error al leer el Excel: {e2}")
    except Exception as e:
        #  Igual aquí: no usamos st.error(), sino lanzamos la excepción
        raise RuntimeError(f" Error al leer el Excel: {e}")

    # --- Limpieza básica ---
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    
    # Only drop rows where both Team and Match are missing
    if "Team" in df.columns and "Match" in df.columns:
        df = df.dropna(subset=["Team", "Match"])
    elif "Match" in df.columns:
        df = df.dropna(subset=["Match"])

    # --- Separar filas del Cibao y de los rivales ---
    df_cibao = df[df["Team"].str.lower() == "cibao"].copy()
    df_rivales = df[df["Team"].str.lower() != "cibao"].copy()

    # --- Renombrar columnas de rivales para diferenciarlas ---
    df_rivales = df_rivales.rename(
        columns=lambda x: f"{x}_Rival" if x not in ["Match", "Date"] else x
    )

    # --- Combinar ambos conjuntos por Match y Date ---
    df_cibao = pd.merge(df_cibao, df_rivales, on=["Match", "Date"], how="left")

    # --- Ordenar por fecha ---
    df_cibao = df_cibao.sort_values("Date").reset_index(drop=True)

    #  Eliminamos st.toast() (no permitido dentro del cache)
    # Devolvemos data limpia
    return df_cibao, df_rivales
