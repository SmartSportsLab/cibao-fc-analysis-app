import os
import json
import pandas as pd
import streamlit as st
from pathlib import Path
import sys

# Try to import fix_team_headers at module level for better reliability
try:
    from src.data_processing.fix_wyscout_headers import fix_team_headers
    FIX_TEAM_HEADERS_AVAILABLE = True
except ImportError:
    try:
        # Add src/data_processing to path
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        src_data_processing = os.path.join(BASE_DIR, "src", "data_processing")
        if src_data_processing not in sys.path:
            sys.path.insert(0, src_data_processing)
        from fix_wyscout_headers import fix_team_headers
        FIX_TEAM_HEADERS_AVAILABLE = True
    except ImportError:
        FIX_TEAM_HEADERS_AVAILABLE = False
        fix_team_headers = None


# ==============================
# CONFIGURACIÓN DE RUTAS
# ==============================
# Try multiple methods to find the data directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

# Fallback: if the above doesn't work, try relative to current working directory
if not os.path.exists(DATA_DIR):
    # Try relative to current working directory
    cwd_data_dir = os.path.join(os.getcwd(), "data")
    if os.path.exists(cwd_data_dir):
        DATA_DIR = cwd_data_dir


# ==============================
# FUNCIÓN: OBTENER CACHE KEY BASADO EN MODIFICACIÓN DE ARCHIVOS
# ==============================
def get_data_cache_key() -> int:
    """
    Genera una clave de cache basada en el tiempo de modificación de los archivos JSON.
    Cuando los archivos cambian, la clave cambia, invalidando automáticamente el cache.
    """
    folder = Path(DATA_DIR) / "processed" / "Wyscout"
    if not folder.exists():
        return 0
    
    # Use individual JSON files (no consolidated file)
    consolidated_files = [
        "Liga_Mayor_Clean_Per_90_Consolidated.json",
        "Wyscout_Data_Consolidated.json",
        "export_summary.json"
    ]
    
    # Find the most recent individual JSON file
    max_mtime = 0
    for json_file in folder.glob("*.json"):
        if json_file.name not in consolidated_files:
            max_mtime = max(max_mtime, json_file.stat().st_mtime)
    
    # Convertir a int para usar como cache key
    return int(max_mtime * 1000)  # Multiply by 1000 to preserve precision


# ==============================
# FUNCIONES AUXILIARES
# ==============================
def load_json(path: str) -> pd.DataFrame:
    """Carga un archivo JSON y devuelve un DataFrame normalizado."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if "data" in data:
        return pd.json_normalize(data["data"])
    return pd.DataFrame(data)


def load_excel(path: str) -> pd.DataFrame:
    """Carga un archivo Excel."""
    return pd.read_excel(path)


# ==============================
# FUNCIÓN: CARGAR ARCHIVOS PER90
# ==============================
@st.cache_data(ttl=60)  # Short TTL - cache invalidates when files change
def load_per90_data(_cache_key: int = None) -> pd.DataFrame:
    """
    Carga todos los archivos JSON de rendimiento (per90)
    desde data/processed/Wyscout/
    
    Prioriza el archivo consolidado si existe, sino carga archivos individuales.
    
    Args:
        _cache_key: Internal cache key based on file modification time.
                    Changing this invalidates the cache automatically.
    """
    folder = os.path.join(DATA_DIR, "processed", "Wyscout")
    
    # Try to resolve absolute path if relative doesn't work
    if not os.path.exists(folder):
        # Try absolute path
        abs_folder = os.path.abspath(folder)
        if os.path.exists(abs_folder):
            folder = abs_folder
        else:
            # Try relative to current working directory
            cwd_folder = os.path.join(os.getcwd(), "data", "processed", "Wyscout")
            if os.path.exists(cwd_folder):
                folder = cwd_folder
            else:
                error_msg = f"La carpeta no existe: {folder} (tried: {abs_folder}, {cwd_folder})"
                print(f" {error_msg}")
                raise FileNotFoundError(error_msg)

    if not os.path.exists(folder):
        raise FileNotFoundError(f"La carpeta no existe: {folder} (absolute: {os.path.abspath(folder)})")

    # Load individual JSON files per team (no consolidated file - removed to prevent stale data issues)
    consolidated_files = [
        "Liga_Mayor_Clean_Per_90_Consolidated.json",
        "Wyscout_Data_Consolidated.json",
        "export_summary.json"  # Also exclude summary file
    ]
    all_data = []
    skipped_old_format = []
    
    # Check if folder has any files
    if not os.path.exists(folder):
        raise FileNotFoundError(f"La carpeta no existe: {folder}")
    
    try:
        files_in_folder = os.listdir(folder)
    except Exception as e:
        raise FileNotFoundError(f"No se puede leer la carpeta {folder}: {e}")
    
    print(f" Checking folder: {folder}")
    print(f"   Files found: {len(files_in_folder)}")
    
    for file in files_in_folder:
        # Excluir archivos consolidados ya intentados y archivos temporales
        if file.endswith(".json") and not any(cf in file for cf in consolidated_files):
            path = os.path.join(folder, file)
            try:
                df = load_json(path)
                
                # SIMPLE CHECK: File must have NEW format columns ("Passes" and "Shots")
                # If it doesn't, it's an old/invalid file - skip it
                has_new_format = "Passes" in df.columns and "Shots" in df.columns
                
                if not has_new_format:
                    # This is an OLD or invalid format file
                    skipped_old_format.append(file)
                    print(f" Skipping invalid file: {file} (missing 'Passes' or 'Shots' columns)")
                    print(f"   Please re-upload Excel files to generate correct JSON files.")
                    continue
                
                # File is valid - add it
                df["source_file"] = file
                all_data.append(df)
                print(f" Loaded: {file} ({len(df.columns)} columns)")
            except Exception as e:
                print(f" Error cargando {file}: {e}")
    
    if skipped_old_format:
        print(f" Skipped {len(skipped_old_format)} OLD format JSON files. Please delete them and re-upload Excel files to generate NEW format JSON files.")

    if not all_data:
        json_files_count = len([f for f in files_in_folder if f.endswith('.json')])
        consolidated_count = len([f for f in files_in_folder if any(cf in f for cf in consolidated_files)])
        
        error_msg = f"No se encontraron archivos JSON válidos en {folder}.\n"
        error_msg += f"  - Total archivos en carpeta: {len(files_in_folder)}\n"
        error_msg += f"  - Archivos JSON encontrados: {json_files_count}\n"
        error_msg += f"  - Archivos consolidados excluidos: {consolidated_count}\n"
        error_msg += f"  - Archivos OLD format excluidos: {len(skipped_old_format)}\n"
        error_msg += f"  - Archivos válidos cargados: {len(all_data)}\n"
        
        if json_files_count > 0:
            error_msg += f"\n  Archivos JSON en carpeta:\n"
            for f in [f for f in files_in_folder if f.endswith('.json')][:10]:
                error_msg += f"    - {f}\n"
            if json_files_count > 10:
                error_msg += f"    ... y {json_files_count - 10} más\n"
        
        if skipped_old_format:
            error_msg += f"\n  Archivos OLD format excluidos:\n"
            for f in skipped_old_format[:5]:
                error_msg += f"    - {f}\n"
        
        print(f" {error_msg}")
        raise ValueError(error_msg)

    # Concatenate all DataFrames, preserving ALL columns (even if some files don't have all columns)
    # This ensures we get the full set of columns from files with 181 columns, not just the common 110
    result = pd.concat(all_data, ignore_index=True, sort=False)
    
    # Verify we have key columns
    has_passes = "Passes" in result.columns
    has_shots = "Shots" in result.columns
    if not (has_passes and has_shots):
        print(f" WARNING: Missing key columns after concatenation!")
        print(f"   Has 'Passes': {has_passes}, Has 'Shots': {has_shots}")
        print(f"   Total columns: {len(result.columns)}")
        print(f"   Sample columns: {list(result.columns)[:20]}")
    
    print(f" Cargados {len(all_data)} archivos individuales ({len(result)} filas, {len(result.columns)} columnas)")
    if has_passes and has_shots:
        print(f"    Key columns 'Passes' and 'Shots' are present")
    return result


# ==============================
# FUNCIÓN: CARGAR ARCHIVOS DE EQUIPOS
# ==============================
@st.cache_data
def load_team_excels() -> dict:
    """Carga todos los archivos Excel de equipos desde data/raw/wyscout/teams/"""
    folder = os.path.join(DATA_DIR, "raw", "wyscout", "teams")
    team_files = {}

    if not os.path.exists(folder):
        raise FileNotFoundError(f"La carpeta no existe: {folder}")

    for file in os.listdir(folder):
        if file.endswith(".xlsx"):
            path = os.path.join(folder, file)
            try:
                df = load_excel(path)
                team_name = os.path.splitext(file)[0].replace("Team Stats ", "")
                team_files[team_name] = df
            except Exception as e:
                print(f" Error cargando {file}: {e}")

    return team_files


# ==============================
# FUNCIÓN: CARGAR RESÚMENES GLOBALES
# ==============================
@st.cache_data
def load_global_summary() -> dict:
    """Carga archivos JSON o Excel desde data/raw/wyscout/global/"""
    folder = os.path.join(DATA_DIR, "raw", "wyscout", "global")
    summary_files = {}

    if not os.path.exists(folder):
        raise FileNotFoundError(f"La carpeta no existe: {folder}")

    for file in os.listdir(folder):
        path = os.path.join(folder, file)
        if file.endswith(".json"):
            summary_files[file] = load_json(path)
        elif file.endswith(".xlsx"):
            summary_files[file] = load_excel(path)

    return summary_files
