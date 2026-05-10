# ===========================================
# 2_Analisis_del_Rival_-_Liga.py — Análisis del Rival - Liga Mayor
# ===========================================
import streamlit as st
import json
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import csv
import requests
from bs4 import BeautifulSoup
import re
import unicodedata

# Tema Plotly oscuro
pio.templates.default = "plotly_dark"

# === IMPORTA EL TEMA OSCURO GLOBAL + TÍTULOS NARANJA ===
from src.utils.global_dark_theme import inject_dark_theme, titulo_naranja
from src.utils.navigation import render_top_navigation

# ===========================================
# COLORES DE EQUIPOS
# ===========================================
def load_team_colors():
    """Carga los colores de los equipos desde el CSV."""
    colors = {}
    color_file = Path(__file__).resolve().parent.parent / "assets" / "Esquema de Colores.csv"
    try:
        with open(color_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                team_name = row['Equipo'].strip()
                hex_color = row['Hex Color'].strip()
                # Asegurar que el color tenga el formato correcto
                if not hex_color.startswith('#'):
                    hex_color = '#' + hex_color
                colors[team_name] = hex_color
                # También agregar variaciones comunes del nombre
                colors[team_name.lower()] = hex_color
                # Agregar sin acentos y espacios
                colors[team_name.replace(' ', '').lower()] = hex_color
    except Exception as e:
        st.warning(f"No se pudo cargar el archivo de colores: {e}")
        # Color por defecto para Cibao
        colors['Cibao'] = '#FF9900'
        colors['cibao'] = '#FF9900'
    return colors

def get_team_color(team_name: str) -> str:
    """Obtiene el color de un equipo con búsqueda flexible."""
    if not team_name:
        return "#CCCCCC"
    
    # Normalizar el nombre del equipo (quitar espacios extra, normalizar)
    normalized_name = team_name.strip()
    
    # Primero intentar coincidencia exacta
    if normalized_name in TEAM_COLORS:
        return TEAM_COLORS[normalized_name]
    
    # Intentar coincidencia case-insensitive
    team_lower = normalized_name.lower()
    if team_lower in TEAM_COLORS:
        return TEAM_COLORS[team_lower]
    
    # Intentar coincidencia parcial (buscar si el nombre del equipo contiene alguna clave)
    # Primero buscar coincidencias más largas (más específicas)
    # IMPORTANT: Avoid matching "Cibao" when looking for other teams
    best_match = None
    best_match_len = 0
    for csv_team, color in TEAM_COLORS.items():
        csv_team_lower = csv_team.lower()
        # Si el nombre del CSV está contenido en el nombre del equipo o viceversa
        # BUT: Don't match if it's a very short substring (to avoid false matches)
        if (csv_team_lower in team_lower or team_lower in csv_team_lower) and len(csv_team) >= 3:
            # Preferir coincidencias más largas y más específicas
            match_score = len(csv_team)
            # Bonus for exact substring match
            if csv_team_lower == team_lower[:len(csv_team_lower)] or team_lower == csv_team_lower[:len(team_lower)]:
                match_score += 100
            if match_score > best_match_len:
                best_match = color
                best_match_len = match_score
    
    if best_match:
        return best_match
    
    # Si no se encuentra, usar gris claro (NO usar el color de Cibao como fallback)
    return "#CCCCCC"

TEAM_COLORS = load_team_colors()
CIBAO_COLOR = get_team_color('Cibao')  # Color oficial de Cibao

# Debug: verificar que los colores se cargaron correctamente
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--debug-colors":
        print("Colores cargados:")
        for team, color in TEAM_COLORS.items():
            print(f"  {team}: {color}")

# ===========================================
# FUNCIONES DE TRADUCCIÓN
# ===========================================
def translate_position(position: str) -> str:
    """Traduce la posición del jugador al español."""
    if not position or position == "Unknown":
        return "Desconocido"
    
    position_lower = position.lower().strip()
    
    # Mapeo de posiciones comunes
    position_map = {
        "goalkeeper": "Portero",
        "gk": "Portero",
        "defender": "Defensor",
        "def": "Defensor",
        "defensive midfielder": "Mediocampista Defensivo",
        "defensive mid": "Mediocampista Defensivo",
        "cdm": "Mediocampista Defensivo",
        "midfielder": "Mediocampista",
        "mid": "Mediocampista",
        "cm": "Mediocampista",
        "attacking midfielder": "Mediocampista Ofensivo",
        "attacking mid": "Mediocampista Ofensivo",
        "cam": "Mediocampista Ofensivo",
        "winger": "Extremo",
        "wing": "Extremo",
        "left winger": "Extremo Izquierdo",
        "right winger": "Extremo Derecho",
        "striker": "Delantero",
        "forward": "Delantero",
        "fwd": "Delantero",
        "cf": "Delantero Centro",
        "center forward": "Delantero Centro",
        "left back": "Lateral Izquierdo",
        "right back": "Lateral Derecho",
        "lb": "Lateral Izquierdo",
        "rb": "Lateral Derecho",
        "center back": "Defensor Central",
        "cb": "Defensor Central",
        "central defender": "Defensor Central",
        "unknown": "Desconocido"
    }
    
    # Buscar coincidencia exacta primero
    if position_lower in position_map:
        return position_map[position_lower]
    
    # Buscar coincidencia parcial
    for key, translation in position_map.items():
        if key in position_lower or position_lower in key:
            return translation
    
    # Si no hay coincidencia, devolver la posición original con primera letra mayúscula
    return position.capitalize() if position else "Desconocido"

# ===========================================
# CONFIGURACIÓN
# ===========================================
st.set_page_config(
    page_title="Análisis del Rival - Liga Mayor | Cibao FC",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------- ACTIVAR TEMA OSCURO GLOBAL ----------
inject_dark_theme()

# ---------- TOP NAVIGATION BAR ----------
render_top_navigation()

# ===========================================
# ESTILOS ADICIONALES - TEXTO MÁS GRANDE PARA LEGIBILIDAD
# ===========================================
st.markdown("""
<style>
    /* Texto general del cuerpo - mantener grande para legibilidad */
    .stApp {
        font-size: 1.3rem !important;
    }
    
    /* Párrafos y texto general */
    p, div, span, label {
        font-size: 1.3rem !important;
    }
    
    /* Tablas */
    .stDataFrame {
        font-size: 1.4rem !important;
    }
    
    .stDataFrame table {
        font-size: 1.4rem !important;
    }
    
    .stDataFrame th {
        font-size: 1.5rem !important;
        font-weight: bold !important;
        padding: 12px !important;
    }
    
    /* Table headers - black text, bold, orange background */
    div[data-testid="stDataFrame"] table thead th,
    div[data-testid="stDataFrame"] table th,
    .stDataFrame table thead th,
    .stDataFrame table th,
    .dataframe thead th,
    .dataframe th {
        color: #000000 !important;
        font-weight: 900 !important;
        background-color: #ff8c00 !important;
    }
    
    .stDataFrame td {
        font-size: 1.4rem !important;
        padding: 10px !important;
    }
    
    /* Métricas de Streamlit */
    [data-testid="stMetricValue"] {
        font-size: 2.5rem !important;
    }
    
    [data-testid="stMetricLabel"] {
        font-size: 1.4rem !important;
    }
    
    [data-testid="stMetricDelta"] {
        font-size: 1.3rem !important;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        font-size: 1.3rem !important;
    }
    
    /* Custom tab styling to match original st.tabs() appearance */
    /* Hide radio button circles completely */
    div[data-testid="stRadio"] > div > label > div[data-baseweb="radio"] {
        display: none !important;
    }
    
    /* Hide the actual radio input */
    div[data-testid="stRadio"] input[type="radio"] {
        display: none !important;
    }
    
    /* Container styling */
    div[data-testid="stRadio"] > div {
        flex-direction: row !important;
        gap: 0 !important;
        background-color: transparent !important;
    }
    
    /* Base label styling - inactive tabs */
    div[data-testid="stRadio"] > div > label {
        background-color: rgba(255, 255, 255, 0.05) !important;
        color: rgba(255, 255, 255, 0.6) !important;
        padding: 0.75rem 1.5rem !important;
        border-radius: 0 !important;
        margin: 0 !important;
        border: none !important;
        font-weight: 600 !important;
        cursor: pointer !important;
        transition: all 0.2s !important;
    }
    
    /* Active/selected tab - orange background like original */
    div[data-testid="stRadio"] > div > label:has(input:checked),
    div[data-testid="stRadio"] > div > label[aria-checked="true"] {
        background-color: #FF9900 !important;
        color: white !important;
    }
    
    /* Hover effect for inactive tabs */
    div[data-testid="stRadio"] > div > label:not(:has(input:checked)):hover {
        background-color: rgba(255, 255, 255, 0.1) !important;
        color: white !important;
    }
    
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        font-size: 1.6rem !important;
    }
    
    /* Selectores y controles */
    .stSelectbox label,
    .stRadio label,
    .stMultiselect label {
        font-size: 1.4rem !important;
        font-weight: 500 !important;
    }
    
    .stSelectbox [class*="selectbox"],
    .stRadio [class*="radio"],
    .stMultiselect [class*="multiselect"] {
        font-size: 1.3rem !important;
    }
    
    /* Info boxes y warnings */
    .stInfo, .stWarning, .stError, .stSuccess {
        font-size: 1.3rem !important;
    }
    
    /* Pestañas */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 55px;
        padding: 12px 24px;
        font-size: 1.4rem !important;
        font-weight: 500 !important;
    }
    
    .stTabs [aria-selected="true"] {
        font-size: 1.5rem !important;
        font-weight: 600 !important;
    }
    
    /* Botones - exclude home and navigation buttons (handled by nav module) */
    .stButton button:not([key^="home_btn"]):not([key^="nav_"]) {
        font-size: 1.3rem !important;
        padding: 0.5rem 1.5rem !important;
    }
</style>
""", unsafe_allow_html=True)

# ===========================================
# RUTAS DE DATOS
# ===========================================
REPO_ROOT = Path(__file__).parents[1]
WYSCOUT_RAW_DIR = REPO_ROOT / "data" / "raw" / "wyscout" / "Global"
WYSCOUT_PROCESSED_DIR = REPO_ROOT / "data" / "processed" / "Wyscout"
CIBAO_TEAM_NAME = "Cibao"

# Import data loaders
from src.data_processing.load_cibao_team_data import load_cibao_team_data
from src.data_processing.loaders import load_per90_data

# Try to import fix_wyscout_headers at module level (if available)
try:
    from src.data_processing.fix_wyscout_headers import fix_team_headers
    FIX_WYSCOUT_HEADERS_AVAILABLE = True
except ImportError:
    FIX_WYSCOUT_HEADERS_AVAILABLE = False
    fix_team_headers = None

# ===========================================
# FUNCIONES DE OBTENCIÓN DE PRÓXIMOS PARTIDOS
# ===========================================
def fetch_next_fixture_from_scoresway(url: str) -> Optional[Dict]:
    """Obtiene el próximo partido desde una página de Scoresway."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        tables = soup.find_all('table')
        
        for table in tables:
            rows = table.find_all('tr')
            
            for row in rows:
                row_text = row.get_text()
                
                if re.search(r'\d{2}/\d{2}/\d{4}', row_text) or re.search(r'\d{2}:\d{2}', row_text):
                    date_match = re.search(r'(\d{2}/\d{2}/\d{4})', row_text)
                    date_str = date_match.group(1) if date_match else None
                    
                    time_match = re.search(r'(\d{2}:\d{2})', row_text)
                    time_str = time_match.group(1) if time_match else None
                    
                    teams_match = re.search(r'([A-Za-z\s]+?)\s+v\s+([A-Za-z\s]+?)(?:\s|$)', row_text, re.IGNORECASE)
                    if teams_match:
                        team1 = teams_match.group(1).strip()
                        team2 = teams_match.group(2).strip()
                        
                        opponent = team2 if "Cibao" not in team2 else team1
                        
                        match_link = row.find('a', href=re.compile(r'/match/view/'))
                        match_url = None
                        if match_link:
                            match_url = match_link.get('href', '')
                            if not match_url.startswith('http'):
                                match_url = f"https://www.scoresway.com{match_url}"
                        
                        full_date = f"{date_str} {time_str}" if date_str and time_str else (date_str or time_str or "Por definir")
                        
                        return {
                            "url": match_url,
                            "date": full_date,
                            "opponent": opponent,
                            "venue": "Por definir"
                        }
        
        return None
    except Exception as e:
        return None


@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_next_fixtures() -> Dict[str, Optional[Dict]]:
    """Obtiene los próximos partidos de Concacaf Cup y Liga Mayor."""
    concacaf_url = "https://www.scoresway.com/en_GB/soccer/concacaf-caribbean-cup-2025/bygi47fmsxgbzysjdf9u481lg/teams/view/6lrtx6i2hsf52v8fh1j43f6cp"
    liga_mayor_url = "https://www.scoresway.com/en_GB/soccer/liga-mayor-2025-2026/6tlslyufw6rjrjgemsur1xo9g/teams/view/6lrtx6i2hsf52v8fh1j43f6cp"
    
    fixtures = {
        "concacaf": None,
        "liga_mayor": None
    }
    
    try:
        fixtures["concacaf"] = fetch_next_fixture_from_scoresway(concacaf_url)
    except Exception as e:
        pass
    
    try:
        fixtures["liga_mayor"] = fetch_next_fixture_from_scoresway(liga_mayor_url)
    except Exception as e:
        pass
    
    return fixtures

# ===========================================
# FUNCIONES DE CARGA DE DATOS
# ===========================================

def extract_team_from_match(match_str: str, is_home: bool = True) -> str:
    """Extrae el nombre del equipo desde la columna Match."""
    if pd.isna(match_str) or not match_str:
        return ""
    
    match_str = str(match_str)
    # Formato típico: "Cibao - Universidad O&M 2:1" o "Atlántico - Cibao 0:5"
    # Separar por " - " o " vs "
    parts = match_str.replace(" vs ", " - ").split(" - ")
    if len(parts) >= 2:
        # Remover el resultado (formato como "2:1" o "0:5")
        # El resultado está en la última parte
        team_part = parts[0].strip() if is_home else parts[1].strip()
        # Remover resultado si está al final (formato "Team 2:1")
        team_part = re.sub(r'\s+\d+:\d+$', '', team_part).strip()
        return team_part
    return ""

@st.cache_data(ttl=60)  # Short TTL - cache invalidates when files change
def load_liga_data(_cache_key: int = None) -> pd.DataFrame:
    """Carga todos los datos de Liga Mayor desde Wyscout.
    
    Args:
        _cache_key: Cache key based on file modification time. When files change, 
                    this key changes, invalidating the cache automatically.
    """
    try:
        # Get cache key based on file modification time (if not provided)
        if _cache_key is None:
            get_data_cache_key = None
            try:
                from src.data_processing.loaders import get_data_cache_key
            except ImportError:
                # Fallback 1: add src/data_processing to sys.path
                import sys
                from pathlib import Path
                repo_root = Path(__file__).parents[1]
                src_data_processing_path = repo_root / "src" / "data_processing"
                if src_data_processing_path.exists() and str(src_data_processing_path) not in sys.path:
                    sys.path.insert(0, str(src_data_processing_path))
                try:
                    from loaders import get_data_cache_key
                except ImportError:
                    # Fallback 2: add repo root to sys.path and import with full path
                    if str(repo_root) not in sys.path:
                        sys.path.insert(0, str(repo_root))
                    from src.data_processing.loaders import get_data_cache_key
            
            if get_data_cache_key is None:
                # If we can't import, just use 0 as cache key (cache will still work, just won't auto-invalidate)
                cache_key = 0
            else:
                cache_key = get_data_cache_key()
        else:
            cache_key = _cache_key
        
        # Load per 90 data from processed JSON files (cache key auto-invalidates when files change)
        df = load_per90_data(_cache_key=cache_key)
        if not df.empty and "Team" in df.columns:
            # Verify Team column has actual team names (not header rows)
            # Check if first value is a valid team name (not "TeamStats" or similar)
            first_team_value = df["Team"].iloc[0] if len(df) > 0 else None
            is_valid_team_data = (
                df["Team"].nunique() > 1 or  # Multiple teams = valid
                (first_team_value is not None and 
                 str(first_team_value).lower() not in ["teamstats", "team", "equipo", ""] and
                 pd.notna(first_team_value))
            )
            
            if is_valid_team_data:
                # Check data source and format
                data_source = "JSON (via load_per90_data)"
                # All data is in NEW FORMAT (fix_wyscout_headers is always applied during upload)
                # No OLD format detection - assume all data is correct
                data_source += " (NEW format)"
                
                # Store source info for debugging
                df.attrs['data_source'] = data_source
                
                return df
            else:
                # Invalid team data - show error
                error_msg = f" JSON data has invalid Team column. First value: {first_team_value}, Unique teams: {df['Team'].nunique()}"
                print(error_msg)
                st.error(error_msg + " Please upload files using the Upload page to regenerate JSON files.")
                return pd.DataFrame()
    except Exception as e:
        # JSON loading failed - show error to user
        import traceback
        error_msg = f" Error loading JSON files: {e}"
        print(error_msg)
        print(f"Traceback: {traceback.format_exc()}")
        st.error(f" Could not load JSON files from data/processed/Wyscout/. Error: {str(e)}. Please upload files using the Upload page to generate JSON files.")
        # Return empty DataFrame - no fallback to Excel
        return pd.DataFrame()


def extract_match_info(match_data: Dict) -> Optional[Dict]:
    """Extrae información clave de un partido."""
    try:
        match_info = match_data.get("matchInfo", {})
        live_data = match_data.get("liveData", {})
        match_details = live_data.get("matchDetails", {})
        
        # Obtener equipos
        contestants = match_info.get("contestant", [])
        if len(contestants) < 2:
            return None
        
        home_team = None
        away_team = None
        for contestant in contestants:
            position = contestant.get("position", "").lower()
            name = contestant.get("name") or contestant.get("shortName") or contestant.get("officialName", "")
            if position == "home":
                home_team = name
            elif position == "away":
                away_team = name
        
        # Si no hay posición, usar orden
        if not home_team and contestants:
            home_team = contestants[0].get("name") or contestants[0].get("shortName", "")
        if not away_team and len(contestants) > 1:
            away_team = contestants[1].get("name") or contestants[1].get("shortName", "")
        
        # Obtener fecha
        match_date_str = match_info.get("localDate", "")
        match_date = None
        if match_date_str:
            try:
                match_date = datetime.strptime(match_date_str, "%Y-%m-%d")
            except:
                pass
        
        # Estado del partido
        match_status_raw = match_details.get("matchStatus", "Scheduled")
        # Traducir estados comunes
        status_translation = {
            "Scheduled": "Programado",
            "Played": "Jugado",
            "Finished": "Finalizado",
            "FT": "Finalizado",
            "Not Started": "No Iniciado"
        }
        match_status = status_translation.get(match_status_raw, match_status_raw)
        
        # Si el status está vacío o es Unknown, verificar si hay score (indica que fue jugado)
        if not match_status or match_status == "Unknown" or match_status == {}:
            scores = match_details.get("scores", {})
            if scores and (scores.get("ft") or scores.get("total")):
                match_status = "Jugado"  # Si hay score, el partido fue jugado
        
        return {
            "match_id": match_info.get("id", ""),
            "date": match_date,
            "date_str": match_date_str,
            "home_team": home_team,
            "away_team": away_team,
            "status": match_status,
            "description": match_info.get("description", f"{home_team} vs {away_team}"),
            "match_data": match_data  # Guardar datos completos
        }
    except Exception as e:
        return None


def remove_accents(text):
    """Remove accents from text to normalize team names and match strings.
    
    This helps with matching teams that have accents (e.g., Atlético, Atlántico, San Cristóbal)
    by converting them to their non-accented equivalents (Atletico, Atlantico, San Cristobal).
    """
    if pd.isna(text) or not text:
        return text if isinstance(text, str) else ""
    
    text = str(text)
    # Normalize Unicode to NFD (decomposed form) - separates base characters from combining marks
    nfd = unicodedata.normalize('NFD', text)
    # Remove combining marks (accents) - keep only base characters
    no_accents = ''.join(c for c in nfd if unicodedata.category(c) != 'Mn')
    return no_accents

def get_all_teams_from_liga_data(df: pd.DataFrame) -> List[str]:
    """Obtiene lista de todos los equipos únicos de los datos de Liga Mayor."""
    if df.empty or "Team" not in df.columns:
        return []
    
    # Get all unique team names
    teams = df["Team"].unique().tolist()
    teams = [t for t in teams if pd.notna(t) and str(t).strip()]
    
    # Clean team names: remove patterns like " (1)", " (2)", etc.
    def clean_team_name(name: str) -> str:
        """Remove duplicate suffixes like (1), (2) from team names."""
        # Remove patterns like " (1)", " (2)", etc. at the end
        cleaned = re.sub(r'\s*\(\d+\)\s*$', '', str(name).strip())
        return cleaned.strip()
    
    # Normalize team name for comparison (case-insensitive, accent-insensitive)
    def normalize_for_comparison(name: str) -> str:
        """Normalize team name for duplicate detection."""
        cleaned = clean_team_name(name)
        # Remove accents and convert to lowercase for comparison
        normalized = remove_accents(cleaned).lower().strip()
        return normalized
    
    # Create a mapping of normalized names to best original name
    # Prefer the version without the suffix, and prefer properly capitalized versions
    team_map = {}
    
    for team in teams:
        cleaned = clean_team_name(team)
        normalized = normalize_for_comparison(team)
        
        # If we haven't seen this normalized name, use current cleaned name
        if normalized not in team_map:
            team_map[normalized] = cleaned
        else:
            # Prefer version without suffix
            current_has_suffix = bool(re.search(r'\(\d+\)$', str(team)))
            existing_has_suffix = bool(re.search(r'\(\d+\)$', str(team_map[normalized])))
            
            # If current doesn't have suffix but existing does, replace it
            if not current_has_suffix and existing_has_suffix:
                team_map[normalized] = cleaned
            # If both have or don't have suffix, prefer properly capitalized version
            elif current_has_suffix == existing_has_suffix and cleaned:
                existing_cleaned = team_map[normalized]
                # Prefer version that starts with capital letter (if both exist)
                if existing_cleaned and cleaned[0].isupper() and (not existing_cleaned or not existing_cleaned[0].isupper()):
                    team_map[normalized] = cleaned
    
    # Return unique cleaned team names, sorted
    unique_teams = sorted(list(set(team_map.values())))
    return unique_teams

def get_cibao_matches_liga(df: pd.DataFrame) -> pd.DataFrame:
    """Filtra partidos donde juega Cibao."""
    if df.empty:
        return pd.DataFrame()
    cibao_matches = df[df["Team"].str.lower() == "cibao"].copy()
    return cibao_matches

def get_cibao_matches_old_structure(matches: List[Dict]) -> List[Dict]:
    """Filtra partidos donde juega Cibao (estructura antigua para compatibilidad)."""
    cibao_matches = []
    
    for match_data in matches:
        match_info = extract_match_info(match_data)
        if not match_info:
            continue
        
        # Verificar si Cibao juega en este partido
        home = match_info["home_team"] or ""
        away = match_info["away_team"] or ""
        
        if CIBAO_TEAM_NAME.lower() in home.lower() or CIBAO_TEAM_NAME.lower() in away.lower():
            # Identificar el oponente
            if CIBAO_TEAM_NAME.lower() in home.lower():
                opponent = away
                is_home = True
            else:
                opponent = home
                is_home = False
            
            match_info["opponent"] = opponent
            match_info["is_home"] = is_home
            cibao_matches.append(match_info)
    
    return cibao_matches


def format_formation(formation: str) -> str:
    """Formatea una formación agregando guiones entre números (ej: 4231 -> 4-2-3-1)."""
    if not formation:
        return formation
    
    # Si ya tiene guiones, devolver tal cual
    if '-' in formation:
        return formation
    
    # Si es solo números, agregar guiones
    if formation.isdigit():
        return '-'.join(formation)
    
    return formation


def get_upcoming_opponents(cibao_matches) -> List[Tuple[str, Dict]]:
    """Identifica el próximo oponente basado en el primer partido no jugado."""
    today = datetime.now()
    
    # Handle DataFrame input - convert to list of dicts
    if isinstance(cibao_matches, pd.DataFrame):
        if cibao_matches.empty:
            return []
        matches_list = cibao_matches.to_dict('records')
    else:
        matches_list = cibao_matches if isinstance(cibao_matches, list) else []
    
    # Separar partidos jugados y no jugados
    played_matches = []
    upcoming_matches = []
    
    for match in matches_list:
        if not isinstance(match, dict):
            continue
        status = match.get("status", "").lower() if match.get("status") else ""
        match_date = match.get("date") or match.get("Date")
        
        # Si el partido ya se jugó
        if status in ["played", "finished", "ft", "jugado", "finalizado"]:
            played_matches.append(match)
        # Si está programado o es futuro
        elif status in ["scheduled", "not started", "programado", "no iniciado", ""] or (match_date and match_date > today):
            upcoming_matches.append(match)
        # Si no hay status claro, verificar por fecha
        elif match_date and match_date > today:
            upcoming_matches.append(match)
        else:
            played_matches.append(match)
    
    # Ordenar partidos futuros por fecha (el más próximo primero)
    upcoming_matches.sort(key=lambda x: x.get("date") or x.get("Date") or datetime.max)
    
    # Solo tomar el PRIMER partido próximo (el más cercano)
    if upcoming_matches:
        next_match = upcoming_matches[0]
        # Extract opponent from Match column if opponent key doesn't exist
        opponent = next_match.get("opponent")
        if not opponent and "Match" in next_match:
            match_str = next_match.get("Match", "")
            # Extract opponent from match string (e.g., "Cibao - Universidad O&M 2:1")
            if match_str and isinstance(match_str, str):
                parts = match_str.split(" - ")
                if len(parts) >= 2:
                    # Determine if Cibao is home or away
                    if "Cibao" in parts[0]:
                        opponent = parts[1].split()[0] if parts[1] else ""
                    else:
                        opponent = parts[0].split()[0] if parts[0] else ""
        
        if opponent and opponent != "Desconocido":
            return [(opponent, next_match)]
    
    # Si no hay partidos futuros, retornar lista vacía
    return []


def get_all_opponents(cibao_matches: List[Dict]) -> List[str]:
    """Obtiene lista de todos los oponentes únicos."""
    opponents = set()
    for match in cibao_matches:
        opponent = match.get("opponent")
        if opponent:
            opponents.add(opponent)
    return sorted(list(opponents))


def get_wyscout_to_scoresway_mapping() -> Dict[str, str]:
    """Retorna el mapeo completo de columnas Wyscout a keys de Scoresway.
    
    Nota: fix_wyscout_headers siempre se aplica durante la carga de datos.
    Todos los datos están en NEW FORMAT:
    - "Shots On Target" (no "Shots / on target")
    - "Passes Accurate" (no "Passes / accurate")
    - "Duels Won" (no "Duels / won")
    - etc.
    """
    return {
        # Ofensivas (usar nombres después de fix_wyscout_headers)
        "Goals": "goals",
        "xG": "xg",
        "Shots On Target": "ontargetScoringAtt",  # NEW FORMAT (after fix_wyscout_headers)
        "Shots": "totalScoringAtt",  # NEW FORMAT (after fix_wyscout_headers)
        "Shots Per 90": "totalScoringAtt",  # Per 90 version
        "Shots On Target Per 90": "ontargetScoringAtt",  # Per 90 version
        "Shots Per 90": "totalScoringAtt",  # Per 90 version
        "Shots On Target Per 90": "ontargetScoringAtt",  # Per 90 version
        "Shots From Outside Penalty Area On Target": "shots_outside_box",  # NEW FORMAT
        
        # Defensivas
        "Conceded goals": "goalsConceded",
        "Shots Against On Target": "shots_against_on_target",  # NEW FORMAT
        "Clearances": "totalClearance",
        "Interceptions": "interception",
        
        # Posesión y Pases
        "Possession, %": "possessionPercentage",
        "Possession %": "possessionPercentage",  # Alternative format without comma
        "Passes Accurate": "accuratePass",  # NEW FORMAT (count) - this is accurate passes count, NOT percentage
        "Passes": "totalPass",  # NEW FORMAT (after fix_wyscout_headers)
        "Passes Accurate %": "passes_accurate_pct",  # Pass accuracy percentage (after fix_wyscout_headers)
        "Forward Passes Accurate": "forward_passes_accurate",  # NEW FORMAT
        "Back Passes Accurate": "back_passes_accurate",  # NEW FORMAT
        "Lateral Passes Accurate": "lateral_passes_accurate",  # NEW FORMAT
        "Long Passes Accurate": "long_passes_accurate",  # NEW FORMAT
        "Progressive Passes Accurate": "progressive_passes_accurate",  # NEW FORMAT
        
        # Duelos y Tackles
        "Duels Won": "duels_won",  # NEW FORMAT
        "Offensive Duels Won": "offensive_duels_won",  # NEW FORMAT
        "Defensive Duels Won": "defensive_duels_won",  # NEW FORMAT
        "Aerial Duels Won": "aerial_duels_won",  # NEW FORMAT
        "Sliding Tackles Successful": "wonTackle",  # NEW FORMAT
        
        # Set Pieces
        "Corners With Shots": "corners_with_shots",  # NEW FORMAT
        "Corners": "wonCorners",  # NEW FORMAT (total corners)
        "Free Kicks With Shots": "free_kicks_with_shots",  # NEW FORMAT
        "Penalties Converted": "penalties_converted",  # NEW FORMAT
        
        # Disciplina
        "Fouls": "fkFoulLost",
        "Yellow cards": "totalYellowCard",
        "Yellow Cards": "totalYellowCard",  # Wyscout format
        "Yellow Cards Per 90": "totalYellowCard",  # Per 90 format
        "Red cards": "totalRedCard",
        "Red Cards": "totalRedCard",  # Wyscout format
        "Red Cards Per 90": "totalRedCard",  # Per 90 format
        "Offsides": "offsides",
        
        # Otras
        "Touches in penalty area": "touches_in_penalty_area",
        "Deep completed passes": "deep_passes",
        "Crosses Accurate": "crosses_accurate",  # NEW FORMAT
        
        # Métricas adicionales
        "PPDA": "ppda",
        "Match Tempo": "match_tempo",  # Wyscout tempo metric
        "Counterattacks With Shots": "counter_attacks",  # NEW FORMAT
        "Counter Attacks": "counter_attacks",  # Después de fix (total counter attacks)
        "Counter Attacks With Shots": "counter_attacks_with_shots",  # Después de fix (con disparos)
        "Defensive Duels Won %": "defensive_duels_won_pct",
        "Offensive Duels Won %": "offensive_duels_won_pct",
        "Aerial Duels Won %": "aerial_duels_won_pct",
        "Passes Accurate %": "passes_accurate_pct",
        "Long pass %": "long_pass_pct",
        "Shots Against": "shots_against",  # Total shots against (después de fix)
        "Shots Against On Target": "shots_against_on_target",  # NEW FORMAT
    }

def calculate_team_averages_from_df(df: pd.DataFrame, team_name: str, already_filtered: bool = False) -> Dict[str, float]:
    """Calcula promedios de métricas para un equipo desde DataFrame de Liga Mayor.
    
    Args:
        df: DataFrame con datos de partidos
        team_name: Nombre del equipo
        already_filtered: Si True, asume que el DataFrame ya está filtrado por equipo y no filtra de nuevo
    """
    if df.empty:
        return {}
    
    # Verificar que existe la columna Team
    if "Team" not in df.columns:
        return {}
    
    # Si el DataFrame ya está filtrado, verificar que tiene datos antes de usarlo
    if already_filtered:
        # Verify DataFrame is not empty and has Team column
        if df.empty or "Team" not in df.columns:
            return {}
        # Use the DataFrame directly (assume it's already filtered by team)
        team_df = df.copy()
    else:
        # Intentar matching flexible del nombre del equipo
        team_name_no_accents = remove_accents(team_name).lower().strip()
        team_df = df[df["Team"].apply(lambda x: remove_accents(str(x)).lower().strip() == team_name_no_accents)].copy()
        
        # Si no hay coincidencia exacta, intentar matching parcial
        if team_df.empty:
            # Buscar coincidencias parciales (el nombre del equipo contiene el nombre buscado o viceversa)
            for col_team in df["Team"].unique():
                if pd.notna(col_team):
                    col_team_no_accents = remove_accents(str(col_team)).lower().strip()
                    # Coincidencia parcial
                    if team_name_no_accents in col_team_no_accents or col_team_no_accents in team_name_no_accents:
                        team_df = df[df["Team"].apply(lambda x: remove_accents(str(x)).lower().strip() == col_team_no_accents)].copy()
                        break
    
    if team_df.empty:
        return {}
    
    # Seleccionar columnas numéricas (incluyendo porcentajes que pueden tener % en el nombre)
    # Primero obtener columnas numéricas estándar
    numeric_cols = team_df.select_dtypes(include=[np.number]).columns.tolist()
    
    # También incluir columnas con % en el nombre que son numéricas
    # Las columnas con % suelen ser float64, así que deberían estar en numeric_cols ya
    # Pero verificamos explícitamente por si acaso
    pct_cols = [col for col in team_df.columns if '%' in str(col) and col not in numeric_cols]
    for col in pct_cols:
        # Verificar si la columna es realmente numérica
        if pd.api.types.is_numeric_dtype(team_df[col]):
            if col not in numeric_cols:
                numeric_cols.append(col)
        else:
            # Intentar convertir a numérico
            try:
                pd.to_numeric(team_df[col], errors='raise')
                if col not in numeric_cols:
                    numeric_cols.append(col)
            except (ValueError, TypeError):
                pass  # No es numérica, omitir
    
    # CRITICAL FIX: Also try to convert object/string columns that look numeric
    # This handles cases where JSON loaded numbers as strings
    for col in team_df.columns:
        if col not in numeric_cols and col not in ["Match", "Date", "Team", "Competition", "Scheme"]:
            # Try to convert to numeric
            try:
                converted = pd.to_numeric(team_df[col], errors='coerce')
                # If at least 50% of values are numeric, include it
                if converted.notna().sum() / len(team_df) > 0.5:
                    numeric_cols.append(col)
            except (ValueError, TypeError):
                pass
    
    # Obtener mapeo completo
    column_mapping = get_wyscout_to_scoresway_mapping()
    
    # Calcular promedios
    # SKIP OLD FORMAT columns and UNNAMED columns - they should not exist, but if they do, ignore them
    old_format_patterns = [" / ", " /accurate", " /won", " / with", " /on target"]
    
    averages = {}
    for col in numeric_cols:
        if col not in ["Match", "Date", "Team"]:  # Excluir columnas no numéricas
            # Skip OLD format columns (should not exist, but check just in case)
            if any(pattern in str(col) for pattern in old_format_patterns):
                continue  # Skip OLD format columns entirely
            
            # Skip "Unnamed" columns (these are artifacts from Excel processing that should have been fixed)
            if "Unnamed" in str(col):
                continue  # Skip Unnamed columns entirely
            
            avg_value = team_df[col].mean()
            if pd.notna(avg_value):
                # Usar nombre mapeado si existe (para compatibilidad con Scoresway)
                metric_key = column_mapping.get(col)
                if metric_key:
                    averages[metric_key] = float(avg_value)
                # También mantener el nombre original para compatibilidad (NEW format only)
                averages[col] = float(avg_value)
                # Y un nombre normalizado (convertir % a _pct)
                normalized_name = col.lower().replace(" ", "_").replace("/", "_").replace(",", "").replace("(", "").replace(")", "").replace("%", "_pct")
                averages[normalized_name] = float(avg_value)
    
    
    # Calcular métricas derivadas que no están directamente en Wyscout
    # Total shots: aproximar desde shots on target (Wyscout no tiene total shots directamente)
    if "ontargetScoringAtt" in averages and averages["ontargetScoringAtt"] > 0:
        # Estimar total shots (normalmente ~3x shots on target, pero esto es aproximado)
        # Sin datos reales, dejamos esto vacío o usamos una estimación conservadora
        pass
    
    # Tackle success: calcular si tenemos wonTackle y total tackles
    if "wonTackle" in averages:
        # Wyscout tiene "Sliding tackles / successful" pero no total tackles
        # Dejamos tackleSuccess como 0 o calculamos si hay datos
        if "wonTackle" in averages and averages["wonTackle"] > 0:
            # Sin total tackles, no podemos calcular porcentaje
            averages["tackleSuccess"] = 0  # Placeholder
    
    # Pass accuracy percentage: Calculate from accuratePass and totalPass
    # After fix_wyscout_headers: "Passes Accurate" is the count, "Passes Accurate %" is the percentage
    if "accuratePass" in averages and "totalPass" in averages:
        if averages["totalPass"] > 0:
            pass_accuracy_pct = (averages["accuratePass"] / averages["totalPass"]) * 100
            averages["passAccuracy"] = round(pass_accuracy_pct, 1)
        else:
            averages["passAccuracy"] = 0
    elif "passes_accurate_pct" in averages:
        # Use the percentage directly if available
        averages["passAccuracy"] = averages["passes_accurate_pct"]
    elif "Passes Accurate %" in averages:
        # Use the percentage directly if available (original column name)
        averages["passAccuracy"] = averages["Passes Accurate %"]
    
    # Corner stats: After fix_wyscout_headers, we have:
    # - "Corners" (total corners) → "wonCorners"
    # - "Corners With Shots" (corners with shots) → "corners_with_shots"
    # Don't overwrite wonCorners - it should already be set from "Corners" column
    # Only set it from corners_with_shots if wonCorners is not already set
    if "wonCorners" not in averages or averages.get("wonCorners", 0) == 0:
        # Fallback: use corners_with_shots if total corners not available
        if "corners_with_shots" in averages:
            averages["wonCorners"] = averages.get("corners_with_shots", 0)
    
    # NOTA: No usamos fallback para duelos específicos (defensive/offensive/aerial)
    # porque los exports simplificados solo tienen "Duels Won %" general.
    # Mostrar el mismo valor para los tres sería engañoso, así que mostramos "N/A"
    # si los específicos no están disponibles. Para obtener estos datos, se necesitan
    # exports más detallados de Wyscout que incluyan "Defensive duels / won", etc.
    
    return averages

def calculate_competition_averages(df: pd.DataFrame) -> Dict[str, float]:
    """Calcula promedios de métricas para toda la competencia desde DataFrame de Liga Mayor."""
    if df.empty:
        return {}
    
    # Seleccionar columnas numéricas (igual que en calculate_team_averages_from_df)
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    
    # También incluir columnas con % en el nombre que son numéricas
    pct_cols = [col for col in df.columns if '%' in str(col) and col not in numeric_cols]
    for col in pct_cols:
        if pd.api.types.is_numeric_dtype(df[col]):
            if col not in numeric_cols:
                numeric_cols.append(col)
        else:
            try:
                pd.to_numeric(df[col], errors='raise')
                if col not in numeric_cols:
                    numeric_cols.append(col)
            except (ValueError, TypeError):
                pass
    
    # Usar el mismo mapeo completo
    column_mapping = get_wyscout_to_scoresway_mapping()
    
    competition_averages = {}
    for col in numeric_cols:
        if col not in ["Match", "Date", "Team"]:
            avg_value = df[col].mean()
            if pd.notna(avg_value):
                # Usar nombre mapeado si existe
                metric_key = column_mapping.get(col)
                if metric_key:
                    competition_averages[metric_key] = float(avg_value)
                # También mantener el nombre original
                competition_averages[col] = float(avg_value)
                # Y nombre normalizado (convertir % a _pct, igual que en team averages)
                normalized_name = col.lower().replace(" ", "_").replace("/", "_").replace(",", "").replace("(", "").replace(")", "").replace("%", "_pct")
                competition_averages[normalized_name] = float(avg_value)
    
    # Calcular métricas derivadas para competencia también
    # Don't overwrite wonCorners - it should already be set from "Corners" column
    # Only set it from corners_with_shots if wonCorners is not already set
    if "wonCorners" not in competition_averages or competition_averages.get("wonCorners", 0) == 0:
        # Fallback: use corners_with_shots if total corners not available
        if "corners_with_shots" in competition_averages:
            competition_averages["wonCorners"] = competition_averages.get("corners_with_shots", 0)
    
    # NOTA: No usamos fallback para duelos específicos (igual que en team averages)
    # para evitar mostrar valores idénticos engañosos
    
    return competition_averages

def get_all_teams_from_matches(all_matches: List[Dict]) -> List[str]:
    """Obtiene lista de todos los equipos únicos de todos los partidos."""
    teams = set()
    for match_data in all_matches:
        match_info = extract_match_info(match_data)
        if match_info:
            home_team = match_info.get("home_team")
            away_team = match_info.get("away_team")
            if home_team:
                teams.add(home_team)
            if away_team:
                teams.add(away_team)
    return sorted(list(teams))


def filter_matches_by_type(matches: List[Dict], team_name: str, filter_type: str, all_matches: List[Dict] = None) -> List[Dict]:
    """Filtra partidos por tipo: 'all', 'home', 'away', 'vs_cibao'."""
    if filter_type == "all":
        return matches
    
    filtered = []
    cibao_name_lower = "Cibao".lower().strip()
    cibao_base = cibao_name_lower.replace(' fc', '').strip()
    team_name_no_accents = remove_accents(team_name).lower().strip()
    team_base = team_name_no_accents.replace(' fc', '').strip()
    
    for match in matches:
        # Los matches ya tienen la estructura de match_info (con home_team, away_team, etc.)
        match_info = match
        
        if not match_info:
            continue
        
        # ALWAYS derive is_home from Match string - home team is ALWAYS first in "Home - Away" format
        # This is the ONLY reliable way to determine home/away
        match_str = str(match_info.get("Match", "")).strip()
        is_home = False  # Default to False
        match_team_name_cleaned = None  # Initialize for use in vs_cibao check
        
        # Format: "Home Team - Away Team score:score"
        # Home team is ALWAYS the first part before " - "
        if match_str and match_str != "nan" and " - " in match_str:
            parts = match_str.split(" - ")
            if len(parts) >= 2:
                home_team = parts[0].strip()
                # Remove score if present (e.g., "Team 2:1" → "Team")
                home_team = re.sub(r'\s+\d+:\d+$', '', home_team).strip()
                
                # Get team name from match itself, fallback to parameter
                match_team_name = str(match_info.get("Team", "")).strip() or team_name
                # Clean team name (remove (1), (2) suffixes) for better matching
                match_team_name_cleaned = re.sub(r'\s*\(\d+\)\s*$', '', match_team_name).strip()
                
                # Normalize both for comparison
                team_name_no_accents = remove_accents(match_team_name_cleaned).lower().strip()
                home_team_no_accents = remove_accents(home_team).lower().strip()
                
                # Remove " FC" suffixes and clean both sides
                team_clean = team_name_no_accents.replace(' fc', '').strip()
                home_clean = home_team_no_accents.replace(' fc', '').strip()
                
                # Check if team name matches home team (with flexible matching)
                # If team name matches the first part (home team), it's a home game
                is_home = (team_name_no_accents in home_team_no_accents or
                          home_team_no_accents in team_name_no_accents or
                          team_clean in home_clean or
                          home_clean in team_clean)
        
        # Apply filters for Wyscout data structure
        if match_str and match_str != "nan" and " - " in match_str:
            # Wyscout data structure - use is_home field (derived from Match string)
            if filter_type == "home":
                if is_home:
                    filtered.append(match)
            elif filter_type == "away":
                if not is_home:
                    filtered.append(match)
            elif filter_type == "vs_cibao":
                # For Wyscout data, check if BOTH the selected team AND Cibao are in the Match string
                match_str_no_accents = remove_accents(match_str).lower()
                cibao_name_no_accents = remove_accents("Cibao").lower()
                team_name_no_accents_check = remove_accents(match_team_name_cleaned).lower().strip() if match_team_name_cleaned else remove_accents(team_name).lower().strip()
                # Both teams must be in the match string
                if cibao_name_no_accents in match_str_no_accents and team_name_no_accents_check in match_str_no_accents:
                    filtered.append(match)
        else:
            # Scoresway data structure - use home_team/away_team
            home = match_info.get("home_team", "")
            away = match_info.get("away_team", "")
            
            # Convertir a string y normalizar
            home_str = str(home).lower().strip() if home else ""
            away_str = str(away).lower().strip() if away else ""
            
            if filter_type == "home":
                # Solo partidos en casa
                home_match = (team_name_no_accents in remove_accents(home_str) or remove_accents(home_str) in team_name_no_accents or
                             team_base in remove_accents(home_str).replace(' fc', '').strip() or
                             remove_accents(home_str).replace(' fc', '').strip() in team_base)
                if home_match:
                    filtered.append(match)
            
            elif filter_type == "away":
                # Solo partidos fuera
                away_match = (team_name_no_accents in remove_accents(away_str) or remove_accents(away_str) in team_name_no_accents or
                             team_base in remove_accents(away_str).replace(' fc', '').strip() or
                             remove_accents(away_str).replace(' fc', '').strip() in team_base)
                if away_match:
                    filtered.append(match)
            
            elif filter_type == "vs_cibao":
                # Solo partidos contra Cibao
                cibao_name_no_accents = remove_accents("Cibao").lower().strip()
                cibao_base = cibao_name_no_accents.replace(' fc', '').strip()
                home_match_cibao = (cibao_name_no_accents in remove_accents(home_str) or remove_accents(home_str) in cibao_name_no_accents or
                                   cibao_base in remove_accents(home_str).replace(' fc', '').strip() or
                                   remove_accents(home_str).replace(' fc', '').strip() in cibao_base)
                away_match_cibao = (cibao_name_no_accents in remove_accents(away_str) or remove_accents(away_str) in cibao_name_no_accents or
                                   cibao_base in remove_accents(away_str).replace(' fc', '').strip() or
                                   remove_accents(away_str).replace(' fc', '').strip() in cibao_base)
                home_match_team = (team_name_no_accents in remove_accents(home_str) or remove_accents(home_str) in team_name_no_accents or
                                  team_base in remove_accents(home_str).replace(' fc', '').strip() or
                                  remove_accents(home_str).replace(' fc', '').strip() in team_base)
                away_match_team = (team_name_no_accents in remove_accents(away_str) or remove_accents(away_str) in team_name_no_accents or
                                  team_base in remove_accents(away_str).replace(' fc', '').strip() or
                                  remove_accents(away_str).replace(' fc', '').strip() in team_base)
                
                if (home_match_cibao or away_match_cibao) and (home_match_team or away_match_team):
                    filtered.append(match)
    
    return filtered


def extract_team_stats_from_match(match_data: Dict, team_name: str) -> Optional[Dict]:
    """Extrae estadísticas de un equipo específico de un partido."""
    try:
        live_data = match_data.get("liveData", {})
        lineups = live_data.get("lineUp", [])
        
        # Buscar el lineup del equipo
        team_lineup = None
        team_name_lower = team_name.lower().strip()
        team_base = team_name_lower.replace(' fc', '').strip()
        
        for lineup in lineups:
            contestant_id = lineup.get("contestantId", "")
            # Verificar si este lineup corresponde al equipo
            match_info = match_data.get("matchInfo", {})
            contestants = match_info.get("contestant", [])
            
            for contestant in contestants:
                if contestant.get("id") == contestant_id:
                    name = contestant.get("name") or contestant.get("shortName") or contestant.get("officialName", "")
                    # Matching más flexible: verificar si el nombre del equipo está en el nombre del contestant o viceversa
                    name_lower = name.lower().strip() if name else ""
                    name_base = name_lower.replace(' fc', '').strip()
                    
                    if (team_name_lower in name_lower or 
                        name_lower in team_name_lower or
                        team_base in name_base or
                        name_base in team_base):
                        team_lineup = lineup
                        break
            
            if team_lineup:
                break
        
        if not team_lineup:
            return None
        
        # Extraer estadísticas
        stats_list = team_lineup.get("stat", [])
        stats_dict = {}
        
        for stat in stats_list:
            stat_type = stat.get("type", "")
            value = stat.get("value", "0")
            
            # Convertir a número si es posible
            try:
                if isinstance(value, str):
                    stats_dict[stat_type] = float(value)
                else:
                    stats_dict[stat_type] = value
            except:
                stats_dict[stat_type] = 0
        
        return stats_dict
    except Exception as e:
        return None


def get_opponent_matches_data(all_matches: List[Dict], opponent_name: str) -> List[Dict]:
    """Obtiene todos los partidos donde aparece el oponente (no solo contra Cibao)."""
    opponent_matches = []
    seen_match_ids = set()  # Para evitar duplicados
    
    # Normalizar nombre del oponente para matching más flexible
    opponent_name_lower = opponent_name.lower().strip()
    # Remover sufijos comunes para matching más flexible
    opponent_base = opponent_name_lower.replace(' fc', '').replace(' fc', '').strip()
    
    for match_data in all_matches:
        match_info = extract_match_info(match_data)
        if not match_info:
            continue
        
        match_id = match_info.get("match_id", "")
        
        # Evitar duplicados usando match_id
        if match_id in seen_match_ids:
            continue
        seen_match_ids.add(match_id)
        
        home = match_info.get("home_team", "")
        away = match_info.get("away_team", "")
        
        # Verificar si el oponente juega en este partido (matching más flexible)
        home_lower = home.lower().strip() if home else ""
        away_lower = away.lower().strip() if away else ""
        
        # Matching: verificar si el nombre del oponente está en el nombre del equipo o viceversa
        home_match = (opponent_name_lower in home_lower or 
                     home_lower in opponent_name_lower or
                     opponent_base in home_lower.replace(' fc', '').strip() or
                     home_lower.replace(' fc', '').strip() in opponent_base)
        
        away_match = (opponent_name_lower in away_lower or 
                     away_lower in opponent_name_lower or
                     opponent_base in away_lower.replace(' fc', '').strip() or
                     away_lower.replace(' fc', '').strip() in opponent_base)
        
        if home_match or away_match:
            # Extraer estadísticas del oponente (si están disponibles)
            opponent_stats = extract_team_stats_from_match(match_data, opponent_name)
            if opponent_stats:
                match_info["opponent_stats"] = opponent_stats
            # Agregar el partido incluso si no hay estadísticas (para contar partidos jugados)
            opponent_matches.append(match_info)
    
    return opponent_matches


def get_cibao_average_metrics(all_matches: List[Dict]) -> Dict[str, float]:
    """Calcula promedios de métricas clave para Cibao."""
    cibao_matches = []
    
    for match_data in all_matches:
        match_info = extract_match_info(match_data)
        if not match_info:
            continue
        
        home = match_info.get("home_team", "")
        away = match_info.get("away_team", "")
        
        # Verificar si Cibao juega en este partido
        if CIBAO_TEAM_NAME.lower() in home.lower() or CIBAO_TEAM_NAME.lower() in away.lower():
            cibao_stats = extract_team_stats_from_match(match_data, CIBAO_TEAM_NAME)
            if cibao_stats:
                match_info["cibao_stats"] = cibao_stats
                cibao_matches.append(match_info)
    
    return calculate_average_metrics_from_matches(cibao_matches, "cibao_stats")


def calculate_average_metrics(opponent_matches: List[Dict]) -> Dict[str, float]:
    """Calcula promedios de métricas clave para el oponente."""
    return calculate_average_metrics_from_matches(opponent_matches, "opponent_stats")


def get_all_teams_average_metrics(all_matches: List[Dict], filter_type: str = "all", opponent_name: str = None) -> Dict[str, float]:
    """Calcula promedios de métricas clave para todos los equipos en la competencia, opcionalmente filtrados."""
    all_teams_stats = []
    
    # Obtener todos los equipos únicos
    all_teams = get_all_teams_from_matches(all_matches)
    
    # Para cada equipo, obtener sus partidos y estadísticas
    for team_name in all_teams:
        team_matches = get_opponent_matches_data(all_matches, team_name)
        
        # Aplicar filtro si es necesario
        if filter_type != "all":
            if filter_type == "vs_cibao":
                # Para "vs_cibao", filtrar partidos donde el equipo jugó contra Cibao
                team_matches = filter_matches_by_type(team_matches, team_name, filter_type, all_matches)
            else:
                # Para otros filtros (home, away)
                team_matches = filter_matches_by_type(team_matches, team_name, filter_type, all_matches)
        
        for match in team_matches:
            stats = match.get("opponent_stats", {})
            if stats:
                all_teams_stats.append(stats)
    
    # Calcular promedios de todas las estadísticas
    if not all_teams_stats:
        return {}
    
    # Métricas a calcular
    metrics_to_sum = {
        "goals": 0,
        "goalsConceded": 0,
        "totalScoringAtt": 0,
        "ontargetScoringAtt": 0,
        "wonCorners": 0,
        "lostCorners": 0,
        "fkFoulWon": 0,
        "fkFoulLost": 0,
        "totalYellowCard": 0,
        "totalRedCard": 0,
        "saves": 0,
        "possessionPercentage": 0,
        "totalPass": 0,
        "accuratePass": 0,
        "totalTackle": 0,
        "wonTackle": 0,
        "totalClearance": 0,
        "subsMade": 0,
    }
    
    match_count = len(all_teams_stats)
    
    for stats in all_teams_stats:
        for metric in metrics_to_sum:
            value = stats.get(metric, 0)
            try:
                metrics_to_sum[metric] += float(value)
            except:
                pass
    
    if match_count == 0:
        return {}
    
    # Calcular promedios
    averages = {}
    for metric, total in metrics_to_sum.items():
        averages[metric] = total / match_count
    
    # Calcular métricas derivadas
    if averages.get("totalPass", 0) > 0:
        pass_accuracy = (averages.get("accuratePass", 0) / averages["totalPass"]) * 100
        averages["passAccuracy"] = round(pass_accuracy, 1)
    else:
        averages["passAccuracy"] = 0
    
    if averages.get("totalTackle", 0) > 0:
        tackle_success = (averages.get("wonTackle", 0) / averages["totalTackle"]) * 100
        averages["tackleSuccess"] = round(tackle_success, 1)
    else:
        averages["tackleSuccess"] = 0
    
    if averages.get("totalScoringAtt", 0) > 0:
        shot_accuracy = (averages.get("ontargetScoringAtt", 0) / averages["totalScoringAtt"]) * 100
        averages["shotAccuracy"] = round(shot_accuracy, 1)
    else:
        averages["shotAccuracy"] = 0
    
    # Redondear valores
    for key, value in averages.items():
        if isinstance(value, float):
            averages[key] = round(value, 2)
    
    return averages


def get_cibao_average_metrics_filtered(all_matches: List[Dict], filter_type: str = "all", opponent_name: str = None) -> Dict[str, float]:
    """Calcula promedios de métricas clave para Cibao, opcionalmente filtrados por tipo de partido."""
    cibao_matches = []
    
    for match_data in all_matches:
        match_info = extract_match_info(match_data)
        if not match_info:
            continue
        
        home = match_info.get("home_team", "")
        away = match_info.get("away_team", "")
        
        # Verificar si Cibao juega en este partido
        if CIBAO_TEAM_NAME.lower() in home.lower() or CIBAO_TEAM_NAME.lower() in away.lower():
            cibao_stats = extract_team_stats_from_match(match_data, CIBAO_TEAM_NAME)
            if cibao_stats:
                match_info["cibao_stats"] = cibao_stats
                cibao_matches.append(match_info)
    
    # Aplicar filtro si es necesario
    if filter_type != "all":
        if filter_type == "vs_cibao" and opponent_name:
            # Para "vs_cibao", filtrar partidos donde Cibao jugó contra el oponente seleccionado
            filtered_cibao_matches = []
            cibao_name_lower = CIBAO_TEAM_NAME.lower().strip()
            opponent_name_lower = opponent_name.lower().strip() if opponent_name else ""
            opponent_base = opponent_name_lower.replace(' fc', '').strip()
            cibao_base = cibao_name_lower.replace(' fc', '').strip()
            
            for match in cibao_matches:
                home = match.get("home_team", "")
                away = match.get("away_team", "")
                home_str = str(home).lower().strip() if home else ""
                away_str = str(away).lower().strip() if away else ""
                
                home_match_cibao = (cibao_name_lower in home_str or home_str in cibao_name_lower or
                                   cibao_base in home_str.replace(' fc', '').strip() or
                                   home_str.replace(' fc', '').strip() in cibao_base)
                away_match_cibao = (cibao_name_lower in away_str or away_str in cibao_name_lower or
                                   cibao_base in away_str.replace(' fc', '').strip() or
                                   away_str.replace(' fc', '').strip() in cibao_base)
                home_match_opponent = (opponent_name_lower in home_str or home_str in opponent_name_lower or
                                      opponent_base in home_str.replace(' fc', '').strip() or
                                      home_str.replace(' fc', '').strip() in opponent_base)
                away_match_opponent = (opponent_name_lower in away_str or away_str in opponent_name_lower or
                                      opponent_base in away_str.replace(' fc', '').strip() or
                                      away_str.replace(' fc', '').strip() in opponent_base)
                
                if (home_match_cibao or away_match_cibao) and (home_match_opponent or away_match_opponent):
                    filtered_cibao_matches.append(match)
            
            cibao_matches = filtered_cibao_matches
        else:
            # Para otros filtros (home, away), usar la función estándar
            cibao_matches = filter_matches_by_type(cibao_matches, CIBAO_TEAM_NAME, filter_type, all_matches)
    
    return calculate_average_metrics_from_matches(cibao_matches, "cibao_stats")


def get_match_duration_minutes(match: Dict) -> float:
    """Extrae la duración del partido en minutos desde los datos del partido."""
    try:
        match_data = match.get("match_data")
        if not match_data:
            return 90.0  # Default a 90 minutos si no hay datos
        
        live_data = match_data.get("liveData", {})
        match_details = live_data.get("matchDetails", {})
        
        # Intentar obtener duración del partido
        match_length_min = match_details.get("matchLengthMin")
        match_length_sec = match_details.get("matchLengthSec", 0)
        
        if match_length_min is not None:
            # Convertir segundos a minutos fraccionarios
            total_minutes = float(match_length_min) + (float(match_length_sec) / 60.0)
            return max(90.0, total_minutes)  # Mínimo 90 minutos
        
        # Si no hay matchLengthMin, intentar calcular desde periodos
        periods = match_details.get("period", [])
        if periods:
            total_minutes = 0
            for period in periods if isinstance(periods, list) else [periods]:
                period_min = period.get("lengthMin", 45)
                period_sec = period.get("lengthSec", 0)
                total_minutes += float(period_min) + (float(period_sec) / 60.0)
            if total_minutes > 0:
                return max(90.0, total_minutes)
        
        # Default a 90 minutos
        return 90.0
    except Exception:
        return 90.0  # Default a 90 minutos en caso de error


def calculate_average_metrics_from_matches(matches: List[Dict], stats_key: str) -> Dict[str, float]:
    """Calcula promedios de métricas clave desde una lista de partidos, normalizando a per 90 minutos cuando corresponde."""
    if not matches:
        return {}
    
    # Métricas que deben normalizarse a per 90 (count-based)
    count_metrics = {
        "goals": 0,
        "goalsConceded": 0,
        "totalScoringAtt": 0,  # Disparos totales
        "ontargetScoringAtt": 0,  # Disparos al arco
        "wonCorners": 0,
        "lostCorners": 0,
        "fkFoulWon": 0,
        "fkFoulLost": 0,
        "totalYellowCard": 0,
        "totalRedCard": 0,
        "saves": 0,
        "totalPass": 0,
        "accuratePass": 0,
        "totalTackle": 0,
        "wonTackle": 0,
        "totalClearance": 0,
        "interception": 0,
        "totalOffside": 0,
        "subsMade": 0,
    }
    
    # Métricas que ya están estandarizadas (porcentajes)
    percentage_metrics = {
        "possessionPercentage": 0,
    }
    
    match_count = 0
    total_minutes = 0.0
    
    for match in matches:
        stats = match.get(stats_key, {})
        if not stats:
            continue
        
        match_count += 1
        
        # Obtener duración del partido
        match_minutes = get_match_duration_minutes(match)
        total_minutes += match_minutes
        
        # Sumar métricas count-based
        for metric in count_metrics:
            value = stats.get(metric, 0)
            try:
                count_metrics[metric] += float(value)
            except:
                pass
        
        # Sumar métricas de porcentaje (promedio simple)
        for metric in percentage_metrics:
            value = stats.get(metric, 0)
            try:
                percentage_metrics[metric] += float(value)
            except:
                pass
    
    if match_count == 0:
        return {}
    
    # Calcular promedios
    averages = {}
    
    # Normalizar métricas count-based a per 90 minutos
    if total_minutes > 0:
        for metric, total in count_metrics.items():
            # Normalizar: (total / total_minutes) * 90
            averages[metric] = (total / total_minutes) * 90.0
    else:
        # Fallback: promedio simple por partido (asumiendo 90 min por partido)
        for metric, total in count_metrics.items():
            averages[metric] = total / match_count
    
    # Calcular promedios de porcentajes (ya están estandarizados)
    for metric, total in percentage_metrics.items():
        averages[metric] = total / match_count
    
    # Calcular métricas derivadas (ya normalizadas)
    if averages.get("totalPass", 0) > 0:
        pass_accuracy = (averages.get("accuratePass", 0) / averages["totalPass"]) * 100
        averages["passAccuracy"] = round(pass_accuracy, 1)
    else:
        averages["passAccuracy"] = 0
    
    if averages.get("totalTackle", 0) > 0:
        tackle_success = (averages.get("wonTackle", 0) / averages["totalTackle"]) * 100
        averages["tackleSuccess"] = round(tackle_success, 1)
    else:
        averages["tackleSuccess"] = 0
    
    if averages.get("totalScoringAtt", 0) > 0:
        shot_accuracy = (averages.get("ontargetScoringAtt", 0) / averages["totalScoringAtt"]) * 100
        averages["shotAccuracy"] = round(shot_accuracy, 1)
    else:
        averages["shotAccuracy"] = 0
    
    # Redondear valores
    for key, value in averages.items():
        if isinstance(value, float):
            averages[key] = round(value, 2)
    
    return averages


def display_metric_card(label: str, value: str, icon: str = "", delta: str = "", color: str = "normal", 
                       competition_avg: str = None, cibao_avg: str = None, higher_is_better: bool = True):
    """Muestra una tarjeta de métrica con estilo mejorado, incluyendo indicadores visuales de comparación."""
    color_map = {
        "normal": "#1E293B",
        "good": "#10B981",
        "bad": "#EF4444",
        "warning": "#F59E0B"
    }
    bg_color = color_map.get(color, color_map["normal"])
    
    # Solo mostrar icono si no está vacío
    if icon:
        icon_html = f'<div style="font-size: 2rem; margin-bottom: 0.5rem;">{icon}</div>'
    else:
        icon_html = ''
    
    # Construir el HTML evitando conflictos de comillas
    # Removed delta display - no longer showing "Por 90 min" or "Promedio" text
    delta_html = ''
    
    # Calcular diferencias y crear indicadores visuales
    comparison_html = ""
    if competition_avg is not None or cibao_avg is not None:
        comparison_parts = []
        
        # Comparar con competencia
        if competition_avg is not None:
            try:
                # Remove any arrows (↑ ↓) from the competition_avg string
                comp_avg_clean = str(competition_avg).replace('↑', '').replace('↓', '').strip()
                value_num = float(value.replace('%', '').replace('A', '').replace('R', '').strip())
                comp_num = float(comp_avg_clean.replace('%', '').replace('A', '').replace('R', '').strip())
                diff = value_num - comp_num
                
                # Determinar si es mejor o peor
                if higher_is_better:
                    is_better = diff > 0
                else:
                    is_better = diff < 0
                
                # Crear indicador visual (sin flechas)
                if abs(diff) > 0.01:  # Solo mostrar si hay diferencia significativa
                    diff_color = "#10B981" if is_better else "#EF4444"
                    diff_str = f"{diff:+.2f}".replace('+', '+').replace('-', '-')
                    if '%' in value:
                        diff_str += '%'
                    indicator = f'<span style="color: {diff_color}; font-weight: bold; margin-left: 0.3rem;">{diff_str}</span>'
                else:
                    indicator = '<span style="color: #94A3B8; margin-left: 0.3rem;">≈</span>'
                
                comparison_parts.append(
                    f'<div style="color: #64748B; font-size: 0.85rem; margin-top: 0.5rem; display: flex; align-items: center; justify-content: center;">'
                    f'<span>Liga: {comp_avg_clean}</span>{indicator}'
                    f'</div>'
                )
            except (ValueError, AttributeError):
                # Si no se puede calcular, mostrar sin indicador
                comp_avg_clean = str(competition_avg).replace('↑', '').replace('↓', '').strip()
                comparison_parts.append(f'<div style="color: #64748B; font-size: 0.85rem; margin-top: 0.5rem;">Liga: {comp_avg_clean}</div>')
        
        # Comparar con Cibao
        if cibao_avg is not None:
            try:
                # Remove any arrows (↑ ↓) from the cibao_avg string
                cibao_avg_clean = str(cibao_avg).replace('↑', '').replace('↓', '').strip()
                value_num = float(value.replace('%', '').replace('A', '').replace('R', '').strip())
                cibao_num = float(cibao_avg_clean.replace('%', '').replace('A', '').replace('R', '').strip())
                diff = value_num - cibao_num
                
                # Determinar si es mejor o peor
                if higher_is_better:
                    is_better = diff > 0
                else:
                    is_better = diff < 0
                
                # Crear indicador visual (sin flechas)
                if abs(diff) > 0.01:  # Solo mostrar si hay diferencia significativa
                    diff_color = "#10B981" if is_better else "#EF4444"
                    diff_str = f"{diff:+.2f}".replace('+', '+').replace('-', '-')
                    if '%' in value:
                        diff_str += '%'
                    indicator = f'<span style="color: {diff_color}; font-weight: bold; margin-left: 0.3rem;">{diff_str}</span>'
                else:
                    indicator = '<span style="color: #94A3B8; margin-left: 0.3rem;">≈</span>'
                
                comparison_parts.append(
                    f'<div style="color: #FF9900; font-size: 0.85rem; margin-top: 0.25rem; display: flex; align-items: center; justify-content: center;">'
                    f'<span>Cibao: {cibao_avg_clean}</span>{indicator}'
                    f'</div>'
                )
            except (ValueError, AttributeError):
                # Si no se puede calcular, mostrar sin indicador
                cibao_avg_clean = str(cibao_avg).replace('↑', '').replace('↓', '').strip()
                comparison_parts.append(f'<div style="color: #FF9900; font-size: 0.85rem; margin-top: 0.25rem;">Cibao: {cibao_avg_clean}</div>')
        
        comparison_html = ''.join(comparison_parts)
    
    # Construir HTML de forma más segura
    html_parts = [
        f'<div style="background: linear-gradient(135deg, {bg_color} 0%, rgba(30, 41, 59, 0.8) 100%); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; padding: 1.5rem; text-align: center; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3); transition: transform 0.2s;">',
        icon_html,
        f'<div style="color: #94A3B8; font-size: 1.2rem; margin-bottom: 0.5rem; font-weight: 500;">{label}</div>',
        f'<div style="color: #FFFFFF; font-size: 2rem; font-weight: bold;">{value}</div>',
        delta_html,
        comparison_html,
        '</div>'
    ]
    
    html_content = ''.join(html_parts)
    st.markdown(html_content, unsafe_allow_html=True)


def extract_match_result(match_data: Dict, team_name: str) -> Optional[Dict]:
    """Extrae el resultado de un partido para un equipo específico."""
    try:
        live_data = match_data.get("liveData", {})
        match_details = live_data.get("matchDetails", {})
        match_info = match_data.get("matchInfo", {})
        
        # Obtener equipos
        contestants = match_info.get("contestant", [])
        home_team = None
        away_team = None
        team_is_home = None
        
        for contestant in contestants:
            position = contestant.get("position", "").lower()
            name = contestant.get("name") or contestant.get("shortName") or contestant.get("officialName", "")
            if position == "home":
                home_team = name
            elif position == "away":
                away_team = name
        
        # Si no hay posición, usar orden
        if not home_team and contestants:
            home_team = contestants[0].get("name") or contestants[0].get("shortName", "")
        if not away_team and len(contestants) > 1:
            away_team = contestants[1].get("name") or contestants[1].get("shortName", "")
        
        # Determinar si el equipo es local o visitante
        if team_name.lower() in (home_team or "").lower():
            team_is_home = True
            opponent_name = away_team
        elif team_name.lower() in (away_team or "").lower():
            team_is_home = False
            opponent_name = home_team
        else:
            return None
        
        # Obtener marcador
        scores = match_details.get("scores", {})
        total_scores = scores.get("total", {})
        home_goals = total_scores.get("home", 0)
        away_goals = total_scores.get("away", 0)
        
        # Determinar goles del equipo y del oponente
        if team_is_home:
            team_goals = home_goals
            opponent_goals = away_goals
        else:
            team_goals = away_goals
            opponent_goals = home_goals
        
        # Determinar resultado (W/D/L)
        if team_goals > opponent_goals:
            result = "W"  # Win / Victoria
            result_emoji = ""
        elif team_goals < opponent_goals:
            result = "L"  # Loss / Derrota
            result_emoji = ""
        else:
            result = "D"  # Draw / Empate
            result_emoji = ""
        
        # Obtener fecha
        match_date_str = match_info.get("localDate", "")
        
        return {
            "date": match_date_str,
            "opponent": opponent_name,
            "team_goals": team_goals,
            "opponent_goals": opponent_goals,
            "result": result,
            "result_emoji": result_emoji,
            "is_home": team_is_home,
            "score": f"{team_goals}-{opponent_goals}"
        }
    except Exception as e:
        return None


def get_recent_form(matches: List[Dict], team_name: str, num_matches: Optional[int] = 5) -> List[Dict]:
    """Obtiene los últimos N partidos con sus resultados. Si num_matches es None, devuelve todos."""
    recent_matches = []
    seen_match_ids = set()  # Para evitar duplicados
    
    # Ordenar partidos por fecha (más recientes primero)
    sorted_matches = sorted(matches, key=lambda x: x.get("date") or x.get("Date") or datetime.min, reverse=True)
    
    # Obtener solo partidos jugados
    played_matches = [m for m in sorted_matches if m.get("status", "").lower() in ["played", "finished", "ft", "jugado", "finalizado"]]
    
    # Si no hay match_data, asumimos que es Wyscout DataFrame data (todos son partidos jugados)
    # Para Wyscout data, el match dict ya contiene toda la información
    if played_matches and not any(m.get("match_data") for m in played_matches):
        # Es Wyscout DataFrame data - crear resultados simples desde los datos del match
        for match in played_matches:
            # Use Match + Date + Team as unique ID to avoid duplicates
            # Include Team because each match has two rows (one per team)
            # Normalize all values to ensure consistent matching
            
            # Get and normalize Match string
            match_str_raw = match.get('Match', '')
            match_str = str(match_str_raw).strip() if pd.notna(match_str_raw) and match_str_raw else ""
            # Normalize: remove extra whitespace, but keep original for display
            match_str_normalized = re.sub(r'\s+', ' ', match_str).strip() if match_str else ""
            
            # Get and normalize Date
            date_val = match.get('Date') or match.get('date')
            date_str = ""
            if pd.notna(date_val) and date_val:
                try:
                    if isinstance(date_val, pd.Timestamp):
                        date_str = date_val.strftime("%Y-%m-%d")
                    elif isinstance(date_val, str):
                        # Try to parse and normalize
                        parsed_date = pd.to_datetime(date_val)
                        date_str = parsed_date.strftime("%Y-%m-%d")
                    else:
                        # Convert to string and extract date part
                        date_str = str(date_val).split()[0] if " " in str(date_val) else str(date_val)
                        # Try to normalize format
                        try:
                            parsed_date = pd.to_datetime(date_str)
                            date_str = parsed_date.strftime("%Y-%m-%d")
                        except:
                            pass
                except Exception:
                    date_str = str(date_val).split()[0] if " " in str(date_val) else str(date_val)
            
            # Get and normalize Team
            team_val_raw = match.get('Team', '')
            team_val = str(team_val_raw).strip() if pd.notna(team_val_raw) and team_val_raw else ""
            
            # Create unique match_id including Team to ensure we only get one row per team per match
            # Use normalized values for consistent deduplication
            # This ensures that even if the same match appears multiple times in source data,
            # we only process it once per team
            match_id = f"{match_str_normalized}|{date_str}|{team_val}"
            
            # Skip if match_id is empty or we've already seen this exact combination
            if not match_id or match_id == "||" or match_id in seen_match_ids:
                continue
            seen_match_ids.add(match_id)
            
            # Extract basic match information
            # Note: match_str was already extracted above for match_id, but we'll get it again for clarity
            match_str = str(match.get("Match", "")).strip()
            
            # Extract actual score from match string (e.g., "Home Team - Away Team 3:1")
            # The score is at the end of the match string
            # Format: "Home Team - Away Team Score" where Score is "HomeGoals:AwayGoals"
            score_match = re.search(r'(\d+):(\d+)\s*$', match_str)
            if score_match:
                home_goals = int(score_match.group(1))
                away_goals = int(score_match.group(2))
                
                # Determine if selected team is home or away to assign goals correctly
                match_parts = re.split(r'\s*-\s*', match_str)
                if len(match_parts) >= 2:
                    home_team = match_parts[0].strip()
                    team_name_lower = team_name.lower().strip()
                    home_team_lower = home_team.lower().strip()
                    
                    # Check if selected team is home team
                    is_home_team = (team_name_lower in home_team_lower or home_team_lower in team_name_lower)
                    
                    if is_home_team:
                        # Selected team is home: goals_for = home_goals, goals_against = away_goals
                        goals_for = home_goals
                        goals_against = away_goals
                    else:
                        # Selected team is away: goals_for = away_goals, goals_against = home_goals
                        goals_for = away_goals
                        goals_against = home_goals
                else:
                    # Fallback if can't parse teams: assume first number is for selected team (less reliable)
                    goals_for = home_goals
                    goals_against = away_goals
            else:
                # Fallback: try to use Goals/Conceded goals if available (but these are per-90, so round them)
                goals_for_raw = match.get("Goals", 0)
                goals_against_raw = match.get("Conceded goals", 0)
                
                # Safely convert goals_for
                try:
                    if pd.isna(goals_for_raw) or goals_for_raw is None:
                        goals_for = 0
                    elif isinstance(goals_for_raw, (int, float)):
                        # Check for NaN or inf
                        if pd.isna(goals_for_raw) or goals_for_raw == float('inf') or goals_for_raw == float('-inf'):
                            goals_for = 0
                        elif goals_for_raw < 10:
                            goals_for = int(round(goals_for_raw))
                        else:
                            goals_for = int(goals_for_raw)
                    else:
                        # Try to convert string or other types
                        goals_for = int(float(str(goals_for_raw))) if str(goals_for_raw).replace('.', '').replace('-', '').isdigit() else 0
                except (ValueError, TypeError, OverflowError):
                    goals_for = 0
                
                # Safely convert goals_against
                try:
                    if pd.isna(goals_against_raw) or goals_against_raw is None:
                        goals_against = 0
                    elif isinstance(goals_against_raw, (int, float)):
                        # Check for NaN or inf
                        if pd.isna(goals_against_raw) or goals_against_raw == float('inf') or goals_against_raw == float('-inf'):
                            goals_against = 0
                        elif goals_against_raw < 10:
                            goals_against = int(round(goals_against_raw))
                        else:
                            goals_against = int(goals_against_raw)
                    else:
                        # Try to convert string or other types
                        goals_against = int(float(str(goals_against_raw))) if str(goals_against_raw).replace('.', '').replace('-', '').isdigit() else 0
                except (ValueError, TypeError, OverflowError):
                    goals_against = 0
            
            # Determinar resultado (W/L/D) basado en goles
            if goals_for > goals_against:
                result = "W"
                result_emoji = ""
            elif goals_for < goals_against:
                result = "L"
                result_emoji = ""
            else:
                result = "D"
                result_emoji = ""
            
            # Helper function to normalize team name (remove suffixes, standardize)
            def normalize_team_name_for_display(name: str) -> str:
                """Normalize team name for consistent display."""
                if not name or pd.isna(name):
                    return name
                # Remove (1), (2) suffixes
                cleaned = re.sub(r'\s*\(\d+\)\s*$', '', str(name).strip())
                return cleaned.strip()
            
            # Determine if team is home or away based on Match string format
            # Format: "Home Team - Away Team Score"
            # Split by " - " to get home and away teams
            match_parts = re.split(r'\s*-\s*', match_str)
            if len(match_parts) >= 2:
                # Remove score from second part
                home_team = match_parts[0].strip()
                away_team = re.sub(r'\s*\d+:\d+.*$', '', match_parts[1]).strip()
                
                # Normalize team names for comparison
                home_team_normalized = normalize_team_name_for_display(home_team)
                away_team_normalized = normalize_team_name_for_display(away_team)
                team_name_normalized = normalize_team_name_for_display(team_name)
                
                # Check if selected team is home or away (case-insensitive, accent-insensitive)
                team_name_lower = remove_accents(team_name_normalized).lower().strip()
                home_team_lower = remove_accents(home_team_normalized).lower().strip()
                away_team_lower = remove_accents(away_team_normalized).lower().strip()
                
                # Determine is_home based on position in Match string
                if team_name_lower in home_team_lower or home_team_lower in team_name_lower:
                    is_home = True
                    opponent_name = away_team_normalized  # Use normalized name
                elif team_name_lower in away_team_lower or away_team_lower in team_name_lower:
                    is_home = False
                    opponent_name = home_team_normalized  # Use normalized name
                else:
                    # Fallback: use existing is_home if available
                    is_home = match.get("is_home", False)
                    # Extract opponent by removing selected team from match string
                    opponent_raw = match_str.replace(team_name, "").strip(" -")
                    opponent_name = normalize_team_name_for_display(
                        re.sub(r'\s*\d+:\d+.*$', '', opponent_raw).strip()
                    )
            else:
                # Fallback if Match string format is unexpected
                is_home = match.get("is_home", False)
                opponent_raw = match_str.replace(team_name, "").strip(" -")
                opponent_name = normalize_team_name_for_display(
                    re.sub(r'\s*\d+:\d+.*$', '', opponent_raw).strip()
                )
            
            # Format date to remove time component
            date_value = match.get("date") or match.get("Date")
            if date_value:
                if isinstance(date_value, pd.Timestamp):
                    date_str = date_value.strftime("%Y-%m-%d")
                elif isinstance(date_value, str):
                    # Try to parse and format
                    try:
                        from datetime import datetime as dt
                        parsed_date = pd.to_datetime(date_value)
                        date_str = parsed_date.strftime("%Y-%m-%d")
                    except:
                        # If parsing fails, just remove time portion if present
                        date_str = str(date_value).split()[0] if " " in str(date_value) else str(date_value)
                else:
                    date_str = str(date_value).split()[0] if " " in str(date_value) else str(date_value)
            else:
                date_str = ""
            
            # Validate match data before appending - skip invalid rows
            # Check if opponent_name is valid (not empty, None, nan, or just whitespace)
            opponent_valid = (
                opponent_name and 
                str(opponent_name).strip().lower() not in ["", "nan", "none", "n/a", "null"] and
                not pd.isna(opponent_name) if isinstance(opponent_name, (int, float)) else True
            )
            
            # Check if match_str is valid (not empty or just team name)
            match_str_valid = (
                match_str and 
                str(match_str).strip() != "" and
                str(match_str).strip() != str(team_name).strip() and
                "-" in str(match_str)  # Should contain " - " separator
            )
            
            # Check if date_str is valid
            date_valid = date_str and str(date_str).strip() != "" and str(date_str).strip().lower() not in ["nan", "none", "n/a"]
            
            # Only append if all validations pass
            if opponent_valid and match_str_valid and date_valid:
                # Extract shots data from match (DataFrame row)
                shots = match.get("Shots", 0)
                shots_on_target = match.get("Shots On Target", 0)
                shots_against = match.get("Shots Against", 0)
                shots_against_on_target = match.get("Shots Against On Target", 0)
                
                # Convert to numeric if they're strings
                try:
                    shots = float(shots) if pd.notna(shots) else 0
                    shots_on_target = float(shots_on_target) if pd.notna(shots_on_target) else 0
                    shots_against = float(shots_against) if pd.notna(shots_against) else 0
                    shots_against_on_target = float(shots_against_on_target) if pd.notna(shots_against_on_target) else 0
                except (ValueError, TypeError):
                    shots = shots_on_target = shots_against = shots_against_on_target = 0
                
                recent_matches.append({
                    "match_id": match_id,
                    "date": date_str,
                    "opponent": opponent_name,
                    "result": result,
                    "result_emoji": result_emoji,
                    "score": f"{goals_for}-{goals_against}",
                    "goals_for": goals_for,
                    "goals_against": goals_against,
                    "is_home": is_home,
                    "Shots": shots,
                    "Shots On Target": shots_on_target,
                    "Shots Against": shots_against,
                    "Shots Against On Target": shots_against_on_target
                })
            # Skip invalid matches silently (they're likely data quality issues)
            
            if num_matches is not None and len(recent_matches) >= num_matches:
                break
    else:
        # Es Concacaf JSON data - usar lógica original
        for match in played_matches:
            match_id = match.get("match_id", "")
            
            # Evitar duplicados
            if match_id in seen_match_ids:
                continue
            seen_match_ids.add(match_id)
            
            match_data = match.get("match_data")
            if not match_data:
                continue
            
            result = extract_match_result(match_data, team_name)
            if result:
                # Incluir match_data para poder acceder a las estadísticas detalladas
                result["match_data"] = match_data
                result["match_id"] = match_id
                recent_matches.append(result)
                
                # Detener cuando tengamos suficientes partidos únicos (solo si num_matches no es None)
                if num_matches is not None and len(recent_matches) >= num_matches:
                    break
    
    return recent_matches


def display_recent_form(recent_matches: List[Dict], team_name: str):
    """Muestra el formulario reciente en un formato visual."""
    if not recent_matches:
        st.info("No hay suficientes partidos jugados para mostrar el formulario reciente.")
        return
    
    # Calcular estadísticas de forma
    wins = sum(1 for m in recent_matches if m.get("result") == "W")
    draws = sum(1 for m in recent_matches if m.get("result") == "D")
    losses = sum(1 for m in recent_matches if m.get("result") == "L")
    
    # Mostrar resumen de forma
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Últimos Partidos", len(recent_matches))
    
    with col2:
        st.metric("Victorias", wins)
    
    with col3:
        st.metric("Empates", draws)
    
    with col4:
        st.metric("Derrotas", losses)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Mostrar cadena de resultados (W/D/L)
    form_string = "".join([m.get("result_emoji", "?") for m in recent_matches if m.get("result")])
    st.markdown(f"""
    <div style='
        background: rgba(30, 41, 59, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 1.5rem;
        text-align: center;
        margin-bottom: 1rem;
    '>
        <div style='color: #94A3B8; font-size: 0.9rem; margin-bottom: 0.5rem;'>Forma Reciente</div>
        <div style='display: flex; align-items: center; justify-content: center; gap: 1rem; color: #FFFFFF; font-size: 2.5rem; font-weight: bold; letter-spacing: 0.5rem;'>
            <span style='color: #94A3B8; font-size: 0.8rem; font-weight: normal; letter-spacing: normal;'>Más reciente</span>
            <span>{form_string}</span>
            <span style='color: #94A3B8; font-size: 0.8rem; font-weight: normal; letter-spacing: normal;'>Más antiguo</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Mostrar tabla de partidos recientes
    st.markdown("""
    <h3 style='color:#ff8c00; margin-top:20px;'>Detalle de Partidos Recientes</h3>
    """, unsafe_allow_html=True)
    
    # Removed matches_data list as we're using custom HTML table now
    # This was only used for display, but we're rendering directly with columns
    
    # Initialize session state for selected match and timeline
    if "selected_match_index" not in st.session_state:
        st.session_state.selected_match_index = None
    if "selected_timeline_index" not in st.session_state:
        st.session_state.selected_timeline_index = None
    
    # Create a clickable table using Streamlit components
    # Header row - updated column widths for new headers
    header_cols = st.columns([0.5, 1.5, 2, 1, 1, 1, 1.5, 1.5])
    headers = ["#", "Fecha", "Oponente", "Resultado", "Marcador (Score)", "Lugar", "Disparos/Precisión", "Disparos Recibidos/Precisión"]
    for i, header in enumerate(headers):
        with header_cols[i]:
            st.markdown(f"""
            <div style='color:#FF9900; font-weight:600; padding:0.5rem 0; border-bottom:2px solid #FF9900;'>
                {header}
            </div>
            """, unsafe_allow_html=True)
    
    # Data rows - each row is clickable via a button
    for idx, match in enumerate(recent_matches, 1):
        venue = "Casa" if match.get("is_home", False) else "Fuera"
        
        # Extract shots statistics from match data
        match_data = match.get("match_data")
        team_shots = 0
        team_shots_on_target = 0
        team_shots_pct = 0.0
        opp_shots = 0
        opp_shots_on_target = 0
        opp_shots_pct = 0.0
        
        if match_data:
            # Scoresway/Concacaf format - extract from match_data
            team_stats = extract_team_stats_from_match(match_data, team_name)
            opponent_name = match.get("opponent", "")
            opponent_stats = extract_team_stats_from_match(match_data, opponent_name) if opponent_name else None
            
            if team_stats:
                team_shots = int(team_stats.get("totalScoringAtt", 0))
                team_shots_on_target = int(team_stats.get("ontargetScoringAtt", 0))
                if team_shots > 0:
                    team_shots_pct = (team_shots_on_target / team_shots) * 100
            
            if opponent_stats:
                opp_shots = int(opponent_stats.get("totalScoringAtt", 0))
                opp_shots_on_target = int(opponent_stats.get("ontargetScoringAtt", 0))
                if opp_shots > 0:
                    opp_shots_pct = (opp_shots_on_target / opp_shots) * 100
        else:
            # Wyscout format - extract directly from match dictionary
            # The shots data should already be in the match dict (added in get_recent_form)
            team_shots = int(float(match.get("Shots", 0))) if pd.notna(match.get("Shots")) else 0
            team_shots_on_target = int(float(match.get("Shots On Target", 0))) if pd.notna(match.get("Shots On Target")) else 0
            opp_shots = int(float(match.get("Shots Against", 0))) if pd.notna(match.get("Shots Against")) else 0
            opp_shots_on_target = int(float(match.get("Shots Against On Target", 0))) if pd.notna(match.get("Shots Against On Target")) else 0
            
            if team_shots > 0:
                team_shots_pct = (team_shots_on_target / team_shots) * 100
            if opp_shots > 0:
                opp_shots_pct = (opp_shots_on_target / opp_shots) * 100
        
        # Create columns for this row - updated widths
        row_cols = st.columns([0.5, 1.5, 2, 1, 1, 1, 1.5, 1.5])
        
        with row_cols[0]:
            st.markdown(f"<div style='padding:0.5rem 0; color:#D1D5DB;'>{idx}</div>", unsafe_allow_html=True)
        with row_cols[1]:
            # Format date to show only date, not time
            date_value = match.get('date', '')
            if date_value:
                if isinstance(date_value, str) and " " in date_value:
                    # Remove time portion if present
                    date_display = date_value.split()[0]
                elif isinstance(date_value, pd.Timestamp):
                    date_display = date_value.strftime("%Y-%m-%d")
                else:
                    date_display = str(date_value).split()[0] if " " in str(date_value) else str(date_value)
            else:
                date_display = "N/A"
            st.markdown(f"<div style='padding:0.5rem 0; color:#D1D5DB;'>{date_display}</div>", unsafe_allow_html=True)
        with row_cols[2]:
            # Make the opponent name clickable
            if st.button(f" {match['opponent']}", key=f"row_btn_{idx-1}", use_container_width=True):
                st.session_state.selected_match_index = idx - 1
                st.rerun()
        with row_cols[3]:
            # Make the result emoji clickable for timeline
            result_emoji = match.get("result_emoji", "?")
            if st.button(f"{result_emoji}", key=f"timeline_btn_{idx-1}", use_container_width=True, help="Ver línea de tiempo"):
                # Toggle timeline - if already selected, close it; otherwise open it
                if st.session_state.selected_timeline_index == idx - 1:
                    st.session_state.selected_timeline_index = None
                else:
                    st.session_state.selected_timeline_index = idx - 1
                st.rerun()
        with row_cols[4]:
            st.markdown(f"<div style='padding:0.5rem 0; color:#D1D5DB;'>{match['score']}</div>", unsafe_allow_html=True)
        with row_cols[5]:
            st.markdown(f"<div style='padding:0.5rem 0; color:#D1D5DB;'>{venue}</div>", unsafe_allow_html=True)
        with row_cols[6]:
            # Team shots / shots on target %
            shots_display = f"{team_shots}/{team_shots_on_target} ({team_shots_pct:.0f}%)"
            st.markdown(f"<div style='padding:0.5rem 0; color:#D1D5DB;'>{shots_display}</div>", unsafe_allow_html=True)
        with row_cols[7]:
            # Opponent shots / shots on target %
            opp_shots_display = f"{opp_shots}/{opp_shots_on_target} ({opp_shots_pct:.0f}%)"
            st.markdown(f"<div style='padding:0.5rem 0; color:#D1D5DB;'>{opp_shots_display}</div>", unsafe_allow_html=True)
        
        # Display timeline popout if this row is selected
        if st.session_state.selected_timeline_index == idx - 1:
            display_match_timeline(match, team_name, match.get("opponent", "Oponente"), idx - 1)
        
        # Add separator line
        st.markdown("<div style='border-bottom:1px solid rgba(255,255,255,0.1); margin:0.25rem 0;'></div>", unsafe_allow_html=True)
    
    # Display modal popup if a match is selected
    if st.session_state.selected_match_index is not None:
        selected_match = recent_matches[st.session_state.selected_match_index]
        display_match_modal(selected_match, team_name)


def extract_match_events(match_data: Dict, team_name: str, opponent_name: str) -> List[Dict]:
    """Extrae todos los eventos del partido (goles, tarjetas, sustituciones, VAR) y los ordena cronológicamente."""
    if not match_data:
        return []
    
    live_data = match_data.get("liveData", {})
    if not live_data:
        return []
    
    events = []
    
    # Get team IDs from matchInfo
    match_info_data = match_data.get("matchInfo", {})
    contestants = match_info_data.get("contestant", [])
    
    # Map contestant IDs to team names
    contestant_to_team = {}
    for contestant in contestants:
        contestant_id = contestant.get("id", "")
        team_name_from_contestant = contestant.get("name") or contestant.get("shortName", "")
        contestant_to_team[contestant_id] = team_name_from_contestant
    
    # Extract goals
    goals = live_data.get("goal", [])
    for goal in goals:
        contestant_id = goal.get("contestantId", "")
        event_team = contestant_to_team.get(contestant_id, "")
        is_team_event = (event_team == team_name)
        
        goal_type = goal.get("type", "G")
        goal_type_text = {
            "G": "Gol",
            "PG": "Gol de Penalti",
            "OG": "Gol en Contra",
            "FG": "Gol de Falta"
        }.get(goal_type, "Gol")
        
        scorer_name = goal.get("scorerName", "Desconocido")
        assist_name = goal.get("assistPlayerName", "")
        
        home_score = goal.get("homeScore", 0)
        away_score = goal.get("awayScore", 0)
        
        # Build goal description with assist if available
        if assist_name:
            goal_details = f"{goal_type_text} - {scorer_name} (Asistencia: {assist_name})"
        else:
            goal_details = f"{goal_type_text} - {scorer_name}"
        
        events.append({
            "type": "goal",
            "time": goal.get("timeMin", 0),
            "time_display": goal.get("timeMinSec", f"{goal.get('timeMin', 0)}'"),
            "period": goal.get("periodId", 1),
            "player": scorer_name,
            "assist": assist_name,
            "team": team_name if is_team_event else opponent_name,
            "details": goal_details,
            "score": f"{home_score}-{away_score}",
            "icon": "",
            "color": "#10B981" if is_team_event else "#EF4444"
        })
    
    # Extract cards
    cards = live_data.get("card", [])
    for card in cards:
        contestant_id = card.get("contestantId", "")
        event_team = contestant_to_team.get(contestant_id, "")
        is_team_event = (event_team == team_name)
        
        card_type = card.get("type", "")
        card_type_text = {
            "YC": "Tarjeta Amarilla",
            "RC": "Tarjeta Roja",
            "Y2C": "Segunda Amarilla"
        }.get(card_type, "Tarjeta")
        
        card_reason = card.get("cardReason", "")
        reason_text = f" - {card_reason}" if card_reason else ""
        
        events.append({
            "type": "card",
            "time": card.get("timeMin", 0),
            "time_display": card.get("timeMinSec", f"{card.get('timeMin', 0)}'"),
            "period": card.get("periodId", 1),
            "player": card.get("playerName", "Desconocido"),
            "team": team_name if is_team_event else opponent_name,
            "details": f"{card_type_text}{reason_text} - {card.get('playerName', 'Desconocido')}",
            "icon": "" if card_type == "YC" else "",
            "color": "#F59E0B" if card_type == "YC" else "#EF4444"
        })
    
    # Extract substitutions
    substitutions = live_data.get("substitute", [])
    for sub in substitutions:
        contestant_id = sub.get("contestantId", "")
        event_team = contestant_to_team.get(contestant_id, "")
        is_team_event = (event_team == team_name)
        
        player_on = sub.get("playerOnName", "Desconocido")
        player_off = sub.get("playerOffName", "Desconocido")
        sub_reason = sub.get("subReason", "Táctica")
        
        events.append({
            "type": "substitution",
            "time": sub.get("timeMin", 0),
            "time_display": sub.get("timeMinSec", f"{sub.get('timeMin', 0)}'"),
            "period": sub.get("periodId", 1),
            "player": f"{player_off} → {player_on}",
            "team": team_name if is_team_event else opponent_name,
            "details": f"Sustitución: {player_off} sale, {player_on} entra ({sub_reason})",
            "icon": "",
            "color": "#3B82F6"
        })
    
    # Extract VAR decisions
    var_decisions = live_data.get("VAR", [])
    for var in var_decisions:
        contestant_id = var.get("contestantId", "")
        event_team = contestant_to_team.get(contestant_id, "")
        is_team_event = (event_team == team_name)
        
        var_type = var.get("type", "VAR")
        decision = var.get("decision", "")
        outcome = var.get("outcome", "")
        
        events.append({
            "type": "var",
            "time": var.get("timeMin", 0),
            "time_display": var.get("timeMinSec", f"{var.get('timeMin', 0)}'"),
            "period": var.get("periodId", 1),
            "player": var.get("playerName", ""),
            "team": team_name if is_team_event else opponent_name,
            "details": f"VAR: {var_type} - {decision} ({outcome})",
            "icon": "",
            "color": "#8B5CF6"
        })
    
    # Sort events by period and time
    events.sort(key=lambda x: (x["period"], x["time"]))
    
    return events


def display_match_timeline(match: Dict, team_name: str, opponent_name: str, match_index: int):
    """Muestra la línea de tiempo de eventos del partido en un popout."""
    match_data = match.get("match_data")
    if not match_data:
        return
    
    events = extract_match_events(match_data, team_name, opponent_name)
    
    # Get match summary info
    live_data = match_data.get("liveData", {})
    match_details = live_data.get("matchDetails", {})
    match_info_data = match_data.get("matchInfo", {})
    match_details_extra = live_data.get("matchDetailsExtra", {})
    
    # Extract final score
    scores = match_details.get("scores", {})
    ft_score = scores.get("ft", {})
    home_score = ft_score.get("home", 0) if ft_score else 0
    away_score = ft_score.get("away", 0) if ft_score else 0
    
    # Get team names
    contestants = match_info_data.get("contestant", [])
    home_team_name = ""
    away_team_name = ""
    for contestant in contestants:
        position = contestant.get("position", "").lower()
        name = contestant.get("name") or contestant.get("shortName", "")
        if position == "home":
            home_team_name = name
        elif position == "away":
            away_team_name = name
    
    # Get attendance and referee
    attendance = match_details_extra.get("attendance", "")
    match_official = match_details_extra.get("matchOfficial", [])
    referee_name = ""
    if match_official:
        for official in match_official:
            if official.get("type") == "Referee":
                referee_name = official.get("name", "")
                break
    
    # Get injury time info (convert from seconds to minutes)
    periods = match_details.get("period", [])
    injury_time_info = []
    for period in periods:
        period_id = period.get("id", 0)
        injury_time_seconds = period.get("announcedInjuryTime", 0)
        if injury_time_seconds > 0:
            injury_time_minutes = injury_time_seconds // 60  # Convert seconds to minutes
            period_name = "1er Tiempo" if period_id == 1 else "2do Tiempo"
            injury_time_info.append(f"{period_name}: +{injury_time_minutes}'")
    
    if not events:
        st.info("No hay eventos disponibles para este partido.")
        return
    
    # Display timeline
    st.markdown("""
    <style>
    .timeline-container {
        background: rgba(30, 41, 59, 0.8);
        border: 2px solid #FF9900;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
    }
    .timeline-summary {
        background: rgba(255, 153, 0, 0.1);
        border: 1px solid rgba(255, 153, 0, 0.3);
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1.5rem;
    }
    .timeline-summary-row {
        display: flex;
        justify-content: space-between;
        margin: 0.5rem 0;
        color: #D1D5DB;
    }
    .timeline-summary-label {
        color: #94A3B8;
        font-weight: 500;
    }
    .timeline-event {
        display: flex;
        align-items: center;
        padding: 0.75rem;
        margin: 0.5rem 0;
        border-left: 3px solid;
        border-radius: 4px;
        background: rgba(255, 255, 255, 0.05);
    }
    .timeline-time {
        font-weight: bold;
        min-width: 60px;
        color: #FF9900;
    }
    .timeline-icon {
        font-size: 1.5rem;
        margin: 0 1rem;
    }
    .timeline-details {
        flex: 1;
        color: #D1D5DB;
    }
    .timeline-team {
        font-size: 0.9rem;
        color: #94A3B8;
        margin-top: 0.25rem;
    }
    </style>
    <div class="timeline-container">
        <h4 style='color:#FF9900; margin-top:0; margin-bottom:1rem;'>Línea de Tiempo del Partido</h4>
    """, unsafe_allow_html=True)
    
    # Display match summary
    st.markdown("""
    <div class="timeline-summary">
    """, unsafe_allow_html=True)
    
    # Result row
    st.markdown(f"""
    <div class="timeline-summary-row">
        <span class="timeline-summary-label">Resultado Final:</span>
        <span style="font-weight: bold; color: #FF9900;">{home_team_name} {home_score} - {away_score} {away_team_name}</span>
    </div>
    """, unsafe_allow_html=True)
    
    if referee_name:
        st.markdown(f"""
        <div class="timeline-summary-row">
            <span class="timeline-summary-label">Árbitro:</span>
            <span>{referee_name}</span>
        </div>
        """, unsafe_allow_html=True)
    
    if attendance:
        st.markdown(f"""
        <div class="timeline-summary-row">
            <span class="timeline-summary-label">Asistencia:</span>
            <span>{attendance}</span>
        </div>
        """, unsafe_allow_html=True)
    
    if injury_time_info:
        st.markdown(f"""
        <div class="timeline-summary-row">
            <span class="timeline-summary-label">Tiempo Adicional:</span>
            <span>{', '.join(injury_time_info)}</span>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Group events by period
    first_half = [e for e in events if e["period"] == 1]
    second_half = [e for e in events if e["period"] == 2]
    
    if first_half:
        st.markdown("<h5 style='color:#94A3B8; margin-top:1rem;'>Primer Tiempo</h5>", unsafe_allow_html=True)
        for event in first_half:
            # Build event HTML properly
            if event['type'] == 'goal':
                # Goals always show score
                event_html = f"""
                <div class="timeline-event" style="border-left-color: {event['color']};">
                    <div class="timeline-time">{event['time_display']}</div>
                    <div class="timeline-icon">{event['icon']}</div>
                    <div class="timeline-details">
                        <div style="font-weight: 600;">{event['details']}</div>
                        <div style="color: #94A3B8; font-size: 0.9rem; margin-top: 0.25rem;">Marcador: {event['score']}</div>
                        <div class="timeline-team">{event['team']}</div>
                    </div>
                </div>
                """
            else:
                # Other events (cards, subs, VAR)
                event_html = f"""
                <div class="timeline-event" style="border-left-color: {event['color']};">
                    <div class="timeline-time">{event['time_display']}</div>
                    <div class="timeline-icon">{event['icon']}</div>
                    <div class="timeline-details">
                        <div>{event['details']}</div>
                        <div class="timeline-team">{event['team']}</div>
                    </div>
                </div>
                """
            
            st.markdown(event_html, unsafe_allow_html=True)
    
    if second_half:
        st.markdown("<h5 style='color:#94A3B8; margin-top:1rem;'>Segundo Tiempo</h5>", unsafe_allow_html=True)
        for event in second_half:
            # Build event HTML properly
            if event['type'] == 'goal':
                # Goals always show score
                event_html = f"""
                <div class="timeline-event" style="border-left-color: {event['color']};">
                    <div class="timeline-time">{event['time_display']}</div>
                    <div class="timeline-icon">{event['icon']}</div>
                    <div class="timeline-details">
                        <div style="font-weight: 600;">{event['details']}</div>
                        <div style="color: #94A3B8; font-size: 0.9rem; margin-top: 0.25rem;">Marcador: {event['score']}</div>
                        <div class="timeline-team">{event['team']}</div>
                    </div>
                </div>
                """
            else:
                # Other events (cards, subs, VAR)
                event_html = f"""
                <div class="timeline-event" style="border-left-color: {event['color']};">
                    <div class="timeline-time">{event['time_display']}</div>
                    <div class="timeline-icon">{event['icon']}</div>
                    <div class="timeline-details">
                        <div>{event['details']}</div>
                        <div class="timeline-team">{event['team']}</div>
                    </div>
                </div>
                """
            
            st.markdown(event_html, unsafe_allow_html=True)
    
    # Close timeline container
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Add a close button
    if st.button(" Cerrar Línea de Tiempo", key=f"close_timeline_{match_index}", use_container_width=True):
        st.session_state.selected_timeline_index = None
        st.rerun()


def display_match_modal(match: Dict, team_name: str):
    """Muestra métricas detalladas de un partido específico en formato KPI tiles en un modal popup."""
    match_data = match.get("match_data")
    if not match_data:
        st.warning("No se encontraron datos detallados para este partido.")
        return
    
    # Extraer estadísticas del equipo y del oponente
    team_stats = extract_team_stats_from_match(match_data, team_name)
    opponent_name = match.get("opponent", "Oponente")
    opponent_stats = extract_team_stats_from_match(match_data, opponent_name)
    
    if not team_stats:
        st.warning("No se pudieron extraer las estadísticas del equipo para este partido.")
        return
    
    venue = "Casa" if match.get("is_home") else "Fuera"
    
    # Create modal popup window with prominent styling
    st.markdown("""
    <style>
    .match-modal-container {
        background: linear-gradient(135deg, #1E293B 0%, rgba(30, 41, 59, 0.98) 100%);
        border: 4px solid #FF9900;
        border-radius: 16px;
        padding: 2rem;
        margin: 2rem 0;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.9);
        position: relative;
    }
    </style>
    <div class="match-modal-container">
    """, unsafe_allow_html=True)
    
    # Header with close button
    col_close, col_title, _ = st.columns([1, 9, 1])
    with col_close:
        if st.button("", key="close_modal_top", help="Cerrar ventana", use_container_width=True):
            st.session_state.selected_match_index = None
            st.rerun()
    
    with col_title:
        st.markdown(f"""
        <h2 style='color:#FF9900; text-align:center; margin-top:0; margin-bottom:0.5rem;'>
            {team_name} vs {opponent_name}
        </h2>
        <p style='text-align:center; color:#94A3B8; font-size:1rem; margin-bottom:1.5rem;'>
            {match.get('date', 'N/A')} | {venue} | Resultado: {match.get('score', 'N/A')} {match.get('result_emoji', '')}
        </p>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Métricas del equipo seleccionado
    st.markdown(f"""
    <h3 style='color:#FF9900; text-align:center; margin-top:20px;'>Métricas Clave - {team_name}</h3>
    """, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Fila 1: Ofensivas
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        goals = team_stats.get("goals", 0)
        opp_goals = opponent_stats.get("goals", 0) if opponent_stats else 0
        display_metric_card(
            "Goles",
            f"{goals:.0f}",
            "",
            f"vs {opp_goals:.0f} del oponente",
            competition_avg=None,
            cibao_avg=None
        )
    
    with col2:
        shots = team_stats.get("totalScoringAtt", 0)
        shots_on_target = team_stats.get("ontargetScoringAtt", 0)
        shot_accuracy = (shots_on_target / shots * 100) if shots > 0 else 0
        opp_shots = opponent_stats.get("totalScoringAtt", 0) if opponent_stats else 0
        display_metric_card(
            "Disparos",
            f"{shots:.0f}",
            "",
            f"{shot_accuracy:.1f}% precisión | vs {opp_shots:.0f}",
        )
    
    with col3:
        shots_on_target = team_stats.get("ontargetScoringAtt", 0)
        opp_sot = opponent_stats.get("ontargetScoringAtt", 0) if opponent_stats else 0
        display_metric_card(
            "Disparos al Arco",
            f"{shots_on_target:.0f}",
            "",
            f"vs {opp_sot:.0f} del oponente",
        )
    
    with col4:
        possession = team_stats.get("possessionPercentage", 0)
        opp_poss = opponent_stats.get("possessionPercentage", 0) if opponent_stats else 0
        display_metric_card(
            "Posesión %",
            f"{possession:.1f}%",
            "",
            f"vs {opp_poss:.1f}% del oponente",
        )
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Fila 2: Defensivas
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        goals_conceded = team_stats.get("goalsConceded", 0)
        display_metric_card(
            "Goles Recibidos",
            f"{goals_conceded:.0f}",
            "",
            "",
        )
    
    with col2:
        saves = team_stats.get("saves", 0)
        opp_saves = opponent_stats.get("saves", 0) if opponent_stats else 0
        display_metric_card(
            "Atajadas",
            f"{saves:.0f}",
            "",
            f"vs {opp_saves:.0f} del oponente",
        )
    
    with col3:
        clearances = team_stats.get("totalClearance", 0)
        opp_clear = opponent_stats.get("totalClearance", 0) if opponent_stats else 0
        display_metric_card(
            "Despejes",
            f"{clearances:.0f}",
            "",
            f"vs {opp_clear:.0f} del oponente",
        )
    
    with col4:
        tackles_won = team_stats.get("wonTackle", 0)
        total_tackles = team_stats.get("totalTackle", 0)
        tackle_success = (tackles_won / total_tackles * 100) if total_tackles > 0 else 0
        opp_tackles = opponent_stats.get("wonTackle", 0) if opponent_stats else 0
        display_metric_card(
            "Tackles Exitosos",
            f"{tackles_won:.0f}",
            "",
            f"{tackle_success:.1f}% efectividad | vs {opp_tackles:.0f}",
        )
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Fila 3: Set Pieces y Disciplina
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        corners_won = team_stats.get("wonCorners", 0)
        opp_corners = opponent_stats.get("wonCorners", 0) if opponent_stats else 0
        display_metric_card(
            "Corners Ganados",
            f"{corners_won:.0f}",
            "",
            f"vs {opp_corners:.0f} del oponente",
        )
    
    with col2:
        total_pass = team_stats.get("totalPass", 0)
        accurate_pass = team_stats.get("accuratePass", 0)
        pass_accuracy = (accurate_pass / total_pass * 100) if total_pass > 0 else 0
        opp_pass_acc = 0
        if opponent_stats:
            opp_total = opponent_stats.get("totalPass", 0)
            opp_accurate = opponent_stats.get("accuratePass", 0)
            opp_pass_acc = (opp_accurate / opp_total * 100) if opp_total > 0 else 0
        display_metric_card(
            "Precisión de Pases",
            f"{pass_accuracy:.1f}%",
            "",
            f"vs {opp_pass_acc:.1f}% del oponente",
        )
    
    with col3:
        fouls = team_stats.get("fkFoulLost", 0)
        opp_fouls = opponent_stats.get("fkFoulLost", 0) if opponent_stats else 0
        display_metric_card(
            "Faltas Cometidas",
            f"{fouls:.0f}",
            "",
            f"vs {opp_fouls:.0f} del oponente",
        )
    
    with col4:
        yellow_cards = team_stats.get("totalYellowCard", 0)
        red_cards = team_stats.get("totalRedCard", 0)
        total_cards = yellow_cards + red_cards
        opp_yellow = opponent_stats.get("totalYellowCard", 0) if opponent_stats else 0
        opp_red = opponent_stats.get("totalRedCard", 0) if opponent_stats else 0
        opp_total = opp_yellow + opp_red
        display_metric_card(
            "Tarjetas",
            f"{total_cards:.0f}",
            "",
            f"{yellow_cards:.0f}A, {red_cards:.0f}R | vs {opp_total:.0f}",
        )
    
    # Close button at bottom (prominent)
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button(" Cerrar Ventana", key="close_modal_bottom", use_container_width=True, type="primary"):
            st.session_state.selected_match_index = None
            st.rerun()
    
    # Close modal HTML
    st.markdown("""
    </div>
    """, unsafe_allow_html=True)


def calculate_single_match_metrics(stats: Dict, opponent_stats: Dict = None) -> Dict[str, float]:
    """Calcula métricas derivadas para un partido individual."""
    metrics = {}
    
    # Precisión de pases
    total_pass = stats.get("totalPass", 0)
    accurate_pass = stats.get("accuratePass", 0)
    if total_pass > 0:
        metrics["passAccuracy"] = (accurate_pass / total_pass) * 100
    else:
        metrics["passAccuracy"] = 0
    
    # Efectividad de tackles
    total_tackle = stats.get("totalTackle", 0)
    won_tackle = stats.get("wonTackle", 0)
    if total_tackle > 0:
        metrics["tackleSuccess"] = (won_tackle / total_tackle) * 100
    else:
        metrics["tackleSuccess"] = 0
    
    # Precisión de disparos
    total_shots = stats.get("totalScoringAtt", 0)
    shots_on_target = stats.get("ontargetScoringAtt", 0)
    if total_shots > 0:
        metrics["shotAccuracy"] = (shots_on_target / total_shots) * 100
    else:
        metrics["shotAccuracy"] = 0
    
    return metrics


def create_radar_chart(opponent_metrics: Dict[str, float], cibao_metrics: Dict[str, float], opponent_name: str, selected_metrics: List[str] = None) -> go.Figure:
    """Crea un gráfico de radar comparando oponente vs Cibao."""
    
    # Todas las métricas disponibles con sus configuraciones
    all_radar_metrics = {
        "Goles": ("goals", 5.0),
        "Goles Recibidos": ("goalsConceded", 3.0, True),  # Invertir (menos es mejor)
        "Disparos": ("totalScoringAtt", 20.0),
        "Disparos al Arco": ("ontargetScoringAtt", 10.0),
        "Posesión": ("possessionPercentage", 100.0),
        "Precisión Pases": ("passAccuracy", 100.0),
        "Pases Totales": ("totalPass", 500.0),
        "Pases Precisos": ("accuratePass", 400.0),
        "Corners": ("wonCorners", 10.0),
        "Tackles Exitosos": ("wonTackle", 15.0),
        "Despejes": ("totalClearance", 20.0),
        "Intercepciones": ("interception", 15.0),
        "Faltas": ("fkFoulLost", 15.0),
        "Tarjetas Amarillas": ("totalYellowCard", 5.0),
    }
    
    # Si no se especifican métricas, usar las predeterminadas
    if selected_metrics is None:
        selected_metrics = [
            "Goles", "Goles Recibidos", "Disparos", "Posesión",
            "Precisión Pases", "Corners", "Tackles Exitosos", "Despejes"
        ]
    
    # Filtrar métricas seleccionadas
    radar_metrics = {k: v for k, v in all_radar_metrics.items() if k in selected_metrics}
    
    categories = []
    categories_with_scale = []  # Categorías con escala incluida
    opponent_values = []
    cibao_values = []
    metric_ranges = []  # Para almacenar el rango de cada métrica
    metric_actual_values = []  # Para almacenar valores reales para hover
    label_to_range_map = {}  # Mapeo explícito de label a rango para asegurar consistencia
    
    # Primera pasada: calcular el rango dinámico para cada métrica
    for label, metric_info in radar_metrics.items():
        if isinstance(metric_info, tuple):
            if len(metric_info) == 3:
                metric_key, default_max, invert = metric_info
            else:
                metric_key, default_max = metric_info
                invert = False
        else:
            metric_key = metric_info
            default_max = 100.0
            invert = False
        
        # Obtener valores reales - try multiple key variations
        # The averages dict might have: mapped key, original column name, or normalized name
        # Also try common column name variations
        def get_metric_value(metrics_dict, key):
            """Try multiple key variations to find the metric value"""
            # Try direct key
            if key in metrics_dict:
                val = metrics_dict[key]
                if val is not None and val != 0:
                    return val
            
            # Try lowercase
            if key.lower() in metrics_dict:
                val = metrics_dict[key.lower()]
                if val is not None and val != 0:
                    return val
            
            # Try with underscores replaced by spaces
            key_with_spaces = key.replace("_", " ")
            if key_with_spaces in metrics_dict:
                val = metrics_dict[key_with_spaces]
                if val is not None and val != 0:
                    return val
            
            # Try common column name variations based on metric_key
            column_name_variations = {
                "goals": ["Goals", "goals"],
                "goalsConceded": ["Conceded goals", "Conceded Goals", "Goals Conceded"],
                "totalScoringAtt": ["Shots", "shots", "Total Scoring Att"],
                "ontargetScoringAtt": ["Shots On Target", "Shots on Target"],
                "possessionPercentage": ["Possession, %", "Possession %", "Possession"],
                "passAccuracy": ["Passes Accurate", "Pass Accuracy"],
                "totalPass": ["Passes", "passes"],
                "accuratePass": ["Passes Accurate", "Accurate Passes"],
                "wonCorners": ["Corners", "corners"],
                "wonTackle": ["Tackles Exitosos", "Successful Tackles", "Sliding Tackles Successful"],
                "totalClearance": ["Clearances", "clearances"],
            }
            
            if key in column_name_variations:
                for var_key in column_name_variations[key]:
                    if var_key in metrics_dict:
                        val = metrics_dict[var_key]
                        if val is not None and val != 0:
                            return val
            
            # Return 0 if not found
            return 0
        
        opp_val = get_metric_value(opponent_metrics, metric_key)
        cibao_val = get_metric_value(cibao_metrics, metric_key)
        
        # Para métricas invertidas, usar el valor original para calcular el rango
        if invert:
            # Para métricas invertidas, el rango va de 0 a max_val
            # pero mostramos valores más bajos como mejores
            actual_opp = opp_val
            actual_cibao = cibao_val
            max_val = max(default_max, actual_opp * 1.2, actual_cibao * 1.2, 1.0)
            min_val = 0
        else:
            # Para métricas normales, encontrar el máximo entre ambos valores
            actual_opp = opp_val
            actual_cibao = cibao_val
            max_val = max(default_max, actual_opp * 1.2, actual_cibao * 1.2, 1.0)
            min_val = 0
        
        metric_ranges.append((min_val, max_val))
        label_to_range_map[label] = (min_val, max_val)  # Guardar en el mapeo también
        metric_actual_values.append({
            'opponent': actual_opp,
            'cibao': actual_cibao,
            'invert': invert
        })
    
    # Segunda pasada: normalizar cada métrica a su propia escala (0-100)
    for idx, (label, metric_info) in enumerate(radar_metrics.items()):
        if isinstance(metric_info, tuple):
            if len(metric_info) == 3:
                metric_key, _, invert = metric_info
            else:
                metric_key, _ = metric_info
                invert = False
        else:
            metric_key = metric_info
            invert = False
        
        categories.append(label)
        
        min_val, max_val = metric_ranges[idx]
        actual_vals = metric_actual_values[idx]
        
        # Crear etiqueta con escala específica para cada métrica
        if label in ["Posesión", "Precisión Pases", "Precisión Disparos", "Efectividad Tackles"]:
            # Porcentajes
            scale_label = f"{label}<br><span style='font-size:0.75em; color:#94A3B8;'>(0-{max_val:.0f}%)</span>"
        else:
            # Valores numéricos
            if min_val == 0:
                scale_label = f"{label}<br><span style='font-size:0.75em; color:#94A3B8;'>(0-{max_val:.1f})</span>"
            else:
                scale_label = f"{label}<br><span style='font-size:0.75em; color:#94A3B8;'>({min_val:.1f}-{max_val:.1f})</span>"
        
        categories_with_scale.append(scale_label)
        
        # Obtener valores reales
        opp_val = actual_vals['opponent']
        cibao_val = actual_vals['cibao']
        
        # Normalizar a escala 0-100 basada en el rango de esta métrica específica
        if invert:
            # Para métricas invertidas: valor más bajo = mejor = más alto en el gráfico
            # Normalizar: (max_val - val) / (max_val - min_val) * 100
            range_size = max_val - min_val if max_val > min_val else 1
            opp_normalized = ((max_val - opp_val) / range_size) * 100
            cibao_normalized = ((max_val - cibao_val) / range_size) * 100
        else:
            # Para métricas normales: valor más alto = mejor = más alto en el gráfico
            range_size = max_val - min_val if max_val > min_val else 1
            opp_normalized = ((opp_val - min_val) / range_size) * 100
            cibao_normalized = ((cibao_val - min_val) / range_size) * 100
        
        # Asegurar que estén en el rango 0-100
        opp_normalized = max(0, min(100, opp_normalized))
        cibao_normalized = max(0, min(100, cibao_normalized))
        
        opponent_values.append(opp_normalized)
        cibao_values.append(cibao_normalized)
    
    # Crear gráfico de radar
    fig = go.Figure()
    
    # Oponente - usar blanco para todos los equipos excepto Cibao (que usa naranja)
    if opponent_name == "Cibao" or "Cibao" in opponent_name:
        opponent_color = CIBAO_COLOR
    else:
        opponent_color = '#FFFFFF'  # Blanco para mejor visibilidad en fondo negro
    opponent_rgb = tuple(int(opponent_color[i:i+2], 16) for i in (1, 3, 5))
    opponent_fillcolor = f'rgba({opponent_rgb[0]}, {opponent_rgb[1]}, {opponent_rgb[2]}, 0.2)'
    
    # Crear hover text con valores reales para ambos equipos
    # IMPORTANTE: Iterar en el mismo orden que cuando construimos metric_actual_values
    hover_text = []
    
    # Usar el mismo orden que radar_metrics.items() para garantizar consistencia
    for idx, (label, metric_info) in enumerate(radar_metrics.items()):
        # Extraer metric_key para verificar valores directamente desde los diccionarios originales
        if isinstance(metric_info, tuple):
            if len(metric_info) == 3:
                metric_key, _, _ = metric_info
            else:
                metric_key, _ = metric_info
        else:
            metric_key = metric_info
        
        # Obtener valores directamente de los diccionarios originales para garantizar corrección
        opp_val_from_dict = opponent_metrics.get(metric_key, 0)
        cibao_val_from_dict = cibao_metrics.get(metric_key, 0)
        
        # También obtener de metric_actual_values para verificar
        actual_vals = metric_actual_values[idx]
        opp_val_stored = actual_vals['opponent']
        cibao_val_stored = actual_vals['cibao']
        
        # Usar los valores del diccionario original (más confiable)
        opp_val = opp_val_from_dict
        cibao_val = cibao_val_from_dict
        
        # Formatear valores según el tipo
        if label in ["Posesión", "Precisión Pases", "Precisión Disparos", "Efectividad Tackles", "Shot Accuracy", "Pass Accuracy", "Tackle Success"]:
            # Porcentajes
            hover = f"{label}<br>Cibao: {cibao_val:.1f}%<br>{opponent_name}: {opp_val:.1f}%"
        else:
            # Valores numéricos
            hover = f"{label}<br>Cibao: {cibao_val:.2f}<br>{opponent_name}: {opp_val:.2f}"
        
        hover_text.append(hover)
    
    # Cerrar el círculo para hover también
    hover_text.append(hover_text[0])
    
    fig.add_trace(go.Scatterpolar(
        r=opponent_values + [opponent_values[0]],  # Cerrar el círculo
        theta=categories_with_scale + [categories_with_scale[0]],  # Usar categorías con escala
        fill='toself',
        name=opponent_name,
        line=dict(color=opponent_color, width=3),
        fillcolor=opponent_fillcolor,
        hovertemplate='%{text}<extra></extra>',
        text=hover_text
    ))
    
    # Cibao - usar color oficial
    cibao_color = CIBAO_COLOR
    # Convertir hex a RGB para el fillcolor
    cibao_rgb = tuple(int(cibao_color[i:i+2], 16) for i in (1, 3, 5))
    cibao_fillcolor = f'rgba({cibao_rgb[0]}, {cibao_rgb[1]}, {cibao_rgb[2]}, 0.2)'
    
    fig.add_trace(go.Scatterpolar(
        r=cibao_values + [cibao_values[0]],  # Cerrar el círculo
        theta=categories_with_scale + [categories_with_scale[0]],  # Usar categorías con escala
        fill='toself',
        name='Cibao',
        line=dict(color=cibao_color, width=3),
        fillcolor=cibao_fillcolor,
        hovertemplate='%{text}<extra></extra>',
        text=hover_text
    ))
    
    # No agregar anotaciones de escala (tick marks)
    scale_annotations = []
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickfont=dict(size=16, color='#94A3B8'),
                gridcolor='rgba(148, 163, 184, 0.3)',
                showticklabels=False  # Ocultar las etiquetas 0, 20, 40, 60, 80, 100
            ),
            angularaxis=dict(
                tickfont=dict(size=15, color='#FFFFFF'),
                linecolor='rgba(148, 163, 184, 0.3)'
            )
        ),
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=600,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=1.0,
            xanchor="left",
            x=0.0,
            font=dict(size=16, color='#FFFFFF')
        ),
        title=dict(
            text="Comparación de Fortalezas y Debilidades",
            font=dict(size=24, color='#FFFFFF'),
            x=0.5,
            y=1.0,
            yanchor="top"
        ),
        annotations=scale_annotations
    )
    
    return fig


def extract_formation_from_match(match_data: Dict, team_name: str) -> Optional[str]:
    """Extrae la formación utilizada por un equipo en un partido."""
    try:
        live_data = match_data.get("liveData", {})
        lineups = live_data.get("lineUp", [])
        
        # Buscar el lineup del equipo
        team_lineup = None
        for lineup in lineups:
            contestant_id = lineup.get("contestantId", "")
            match_info = match_data.get("matchInfo", {})
            contestants = match_info.get("contestant", [])
            
            for contestant in contestants:
                if contestant.get("id") == contestant_id:
                    name = contestant.get("name") or contestant.get("shortName") or contestant.get("officialName", "")
                    if team_name.lower() in name.lower():
                        team_lineup = lineup
                        break
            
            if team_lineup:
                break
        
        if not team_lineup:
            return None
        
        # Buscar formationUsed en los stats
        stats_list = team_lineup.get("stat", [])
        for stat in stats_list:
            if stat.get("type") == "formationUsed":
                formation = stat.get("value", "")
                return format_formation(formation) if formation else None
        
        # Alternativa: buscar en formationUsed directamente en el lineup
        formation = team_lineup.get("formationUsed", "")
        if formation:
            return format_formation(formation)
        
        return None
    except Exception as e:
        return None


def analyze_formations_from_df(df: pd.DataFrame, team_name: str) -> Dict:
    """Analiza las formaciones utilizadas por un equipo desde DataFrame de Wyscout."""
    formation_stats = {}
    
    if df.empty or "Scheme" not in df.columns:
        return formation_stats
    
    team_name_no_accents = remove_accents(team_name).lower().strip()
    team_df = df[df["Team"].apply(lambda x: remove_accents(str(x)).lower().strip() == team_name_no_accents)].copy()
    if team_df.empty:
        return formation_stats
    
    for _, row in team_df.iterrows():
        formation = str(row.get("Scheme", "")).strip() if pd.notna(row.get("Scheme")) else ""
        if not formation or formation == "":
            continue
        
        # Normalizar formación (remover espacios, etc.)
        formation = format_formation(formation)
        
        # Inicializar estadísticas de esta formación si no existe
        if formation not in formation_stats:
            formation_stats[formation] = {
                "count": 0,
                "wins": 0,
                "draws": 0,
                "losses": 0,
                "goals_for": 0,
                "goals_against": 0,
                "matches": []
            }
        
        formation_stats[formation]["count"] += 1
        
        # Extraer resultado desde Match column o Goals
        goals = row.get("Goals", 0)
        if pd.isna(goals):
            goals = 0
        
        # Intentar extraer resultado del Match string (ej: "Cibao - Opponent 2:1")
        match_str = str(row.get("Match", ""))
        opponent_goals = 0
        result = "D"  # Default draw
        
        if match_str and " - " in match_str:
            # Formato: "Team1 - Team2 2:1" o "Team1 - Team2"
            parts = match_str.split(" - ")
            if len(parts) >= 2:
                # Extraer score si existe
                score_part = parts[1] if len(parts) > 1 else ""
                # Buscar patrón de score (ej: "2:1", "0:5")
                score_match = re.search(r'(\d+):(\d+)', score_part)
                if score_match:
                    team_goals = int(score_match.group(1))
                    opponent_goals = int(score_match.group(2))
                    # Determinar si este equipo es home o away
                    team_name_in_match = team_name.lower() in parts[0].lower()
                    if team_name_in_match:
                        # Este equipo es home
                        goals = team_goals
                        opponent_goals = opponent_goals
                    else:
                        # Este equipo es away
                        goals = opponent_goals
                        opponent_goals = team_goals
                    
                    if goals > opponent_goals:
                        result = "W"
                    elif goals < opponent_goals:
                        result = "L"
                    else:
                        result = "D"
        
        # Actualizar estadísticas
        if result == "W":
            formation_stats[formation]["wins"] += 1
        elif result == "L":
            formation_stats[formation]["losses"] += 1
        else:
            formation_stats[formation]["draws"] += 1
        
        formation_stats[formation]["goals_for"] += int(goals)
        formation_stats[formation]["goals_against"] += int(opponent_goals)
        
        # Extraer oponente y fecha
        opponent = "N/D"
        if match_str and " - " in match_str:
            parts = match_str.split(" - ")
            if len(parts) >= 2:
                # El oponente está en la otra parte
                if team_name.lower() in parts[0].lower():
                    opponent = parts[1].split()[0] if parts[1] else "N/D"
                else:
                    opponent = parts[0].split()[0] if parts[0] else "N/D"
        
        date_str = str(row.get("Date", "N/D"))
        if pd.notna(row.get("Date")):
            try:
                date_str = row["Date"].strftime("%Y-%m-%d")
            except:
                pass
        
        formation_stats[formation]["matches"].append({
            "date": date_str,
            "opponent": opponent,
            "score": f"{int(goals)}:{int(opponent_goals)}",
            "result": result
        })
    
    # Calcular porcentajes y promedios
    for formation, stats in formation_stats.items():
        total = stats["count"]
        if total > 0:
            stats["win_rate"] = (stats["wins"] / total) * 100
            stats["avg_goals_for"] = stats["goals_for"] / total
            stats["avg_goals_against"] = stats["goals_against"] / total
            stats["goal_difference"] = stats["goals_for"] - stats["goals_against"]
            stats["avg_goal_difference"] = stats["goal_difference"] / total
    
    return formation_stats

def analyze_formations(matches: List[Dict], team_name: str) -> Dict:
    """Analiza las formaciones utilizadas por un equipo (Scoresway JSON format)."""
    formation_stats = {}
    
    for match in matches:
        match_data = match.get("match_data")
        if not match_data:
            continue
        
        formation = extract_formation_from_match(match_data, team_name)
        if not formation:
            continue
        
        # Inicializar estadísticas de esta formación si no existe
        if formation not in formation_stats:
            formation_stats[formation] = {
                "count": 0,
                "wins": 0,
                "draws": 0,
                "losses": 0,
                "goals_for": 0,
                "goals_against": 0,
                "matches": []
            }
        
        formation_stats[formation]["count"] += 1
        
        # Extraer resultado
        result = extract_match_result(match_data, team_name)
        if result:
            if result["result"] == "W":
                formation_stats[formation]["wins"] += 1
            elif result["result"] == "L":
                formation_stats[formation]["losses"] += 1
            else:
                formation_stats[formation]["draws"] += 1
            
            formation_stats[formation]["goals_for"] += result.get("team_goals", 0)
            formation_stats[formation]["goals_against"] += result.get("opponent_goals", 0)
            formation_stats[formation]["matches"].append({
                "date": match.get("date_str", "N/D"),
                "opponent": result.get("opponent", "N/D"),
                "score": result.get("score", "N/D"),
                "result": result["result"]
            })
    
    # Calcular porcentajes y promedios
    for formation, stats in formation_stats.items():
        total = stats["count"]
        if total > 0:
            stats["win_rate"] = (stats["wins"] / total) * 100
            stats["avg_goals_for"] = stats["goals_for"] / total
            stats["avg_goals_against"] = stats["goals_against"] / total
            stats["goal_difference"] = stats["goals_for"] - stats["goals_against"]
            stats["avg_goal_difference"] = stats["goal_difference"] / total
    
    return formation_stats


def extract_player_stats_from_matches(matches: List[Dict], team_name: str) -> Dict:
    """Extrae estadísticas de jugadores de todos los partidos."""
    player_stats = {}
    
    for match in matches:
        match_data = match.get("match_data")
        if not match_data:
            continue
        
        live_data = match_data.get("liveData", {})
        lineups = live_data.get("lineUp", [])
        
        # Buscar el lineup del equipo
        team_lineup = None
        for lineup in lineups:
            contestant_id = lineup.get("contestantId", "")
            match_info = match_data.get("matchInfo", {})
            contestants = match_info.get("contestant", [])
            
            for contestant in contestants:
                if contestant.get("id") == contestant_id:
                    name = contestant.get("name") or contestant.get("shortName") or contestant.get("officialName", "")
                    if remove_accents(team_name).lower() in remove_accents(name).lower():
                        team_lineup = lineup
                        break
            
            if team_lineup:
                break
        
        if not team_lineup:
            continue
        
        # Procesar jugadores del lineup
        players = team_lineup.get("player", [])
        for player in players:
            player_id = player.get("playerId", "")
            player_name = player.get("matchName") or f"{player.get('shortFirstName', '')} {player.get('shortLastName', '')}".strip()
            
            if not player_id or not player_name:
                continue
            
            if player_id not in player_stats:
                player_stats[player_id] = {
                    "name": player_name,
                    "position": translate_position(player.get("position", "Unknown")),
                    "shirt_number": player.get("shirtNumber", 0),
                    "goals": 0,
                    "assists": 0,
                    "total_shots": 0,
                    "shots_on_target": 0,
                    "total_passes": 0,
                    "accurate_passes": 0,
                    "total_tackles": 0,
                    "won_tackles": 0,
                    "clearances": 0,
                    "interceptions": 0,
                    "saves": 0,
                    "offsides": 0,
                    "matches_played": 0,
                    "matches_started": 0,
                    "total_minutes": 0,
                    "matches": []
                }
            
            # Extraer stats del jugador
            stats_list = player.get("stat", [])
            for stat in stats_list:
                stat_type = stat.get("type", "")
                value = stat.get("value", "0")
                
                try:
                    # Convert value to int/float
                    if isinstance(value, str):
                        # Try int first, then float
                        try:
                            num_value = int(value)
                        except:
                            try:
                                num_value = float(value)
                            except:
                                num_value = 0
                    else:
                        num_value = int(value) if isinstance(value, (int, float)) else 0
                    
                    if stat_type == "goals":
                        player_stats[player_id]["goals"] += num_value
                    elif stat_type == "goalAssist":
                        player_stats[player_id]["assists"] += num_value
                    elif stat_type == "totalScoringAtt":
                        player_stats[player_id]["total_shots"] += num_value
                    elif stat_type == "ontargetScoringAtt":
                        player_stats[player_id]["shots_on_target"] += num_value
                    elif stat_type == "totalPass":
                        player_stats[player_id]["total_passes"] += num_value
                    elif stat_type == "accuratePass":
                        player_stats[player_id]["accurate_passes"] += num_value
                    elif stat_type == "totalTackle":
                        player_stats[player_id]["total_tackles"] += num_value
                    elif stat_type == "wonTackle":
                        player_stats[player_id]["won_tackles"] += num_value
                    elif stat_type == "totalClearance":
                        player_stats[player_id]["clearances"] += num_value
                    elif stat_type == "interception":
                        player_stats[player_id]["interceptions"] += num_value
                    elif stat_type == "saves":
                        player_stats[player_id]["saves"] += num_value
                    elif stat_type == "totalOffside":
                        player_stats[player_id]["offsides"] += num_value
                    elif stat_type == "minsPlayed":
                        player_stats[player_id]["total_minutes"] += num_value
                    elif stat_type == "gameStarted":
                        if num_value == 1:
                            player_stats[player_id]["matches_started"] += 1
                except Exception as e:
                    # Silently skip invalid stats
                    pass
            
            player_stats[player_id]["matches_played"] += 1
            player_stats[player_id]["matches"].append({
                "date": match.get("date_str", "N/D"),
                "opponent": match.get("away_team") if match.get("home_team") == team_name else match.get("home_team", "N/D")
            })
        
        # También extraer goles y asistencias del array "goal"
        goals = live_data.get("goal", [])
        match_info = match_data.get("matchInfo", {})
        contestants = match_info.get("contestant", [])
        
        for goal in goals:
            contestant_id = goal.get("contestantId", "")
            # Verificar si este gol es del equipo que estamos analizando
            for contestant in contestants:
                if contestant.get("id") == contestant_id:
                    name = contestant.get("name") or contestant.get("shortName") or contestant.get("officialName", "")
                    if team_name.lower() in name.lower():
                        scorer_id = goal.get("scorerId", "")
                        scorer_name = goal.get("scorerName", "")
                        assist_id = goal.get("assistPlayerId", "")
                        assist_name = goal.get("assistPlayerName", "")
                        
                        # Agregar gol al goleador
                        if scorer_id and scorer_id in player_stats:
                            player_stats[scorer_id]["goals"] += 1
                        elif scorer_name:
                            # Buscar por nombre si no encontramos por ID
                            for pid, pstat in player_stats.items():
                                if scorer_name.lower() in pstat["name"].lower() or pstat["name"].lower() in scorer_name.lower():
                                    player_stats[pid]["goals"] += 1
                                    break
                        
                        # Agregar asistencia
                        if assist_id and assist_id in player_stats:
                            player_stats[assist_id]["assists"] += 1
                        elif assist_name:
                            for pid, pstat in player_stats.items():
                                if assist_name.lower() in pstat["name"].lower() or pstat["name"].lower() in assist_name.lower():
                                    player_stats[pid]["assists"] += 1
                                    break
                    break
    
    return player_stats


def get_competition_position_offside_average(all_matches: List[Dict], target_position: str) -> float:
    """Calcula el promedio de fuera de juego por 90 minutos para una posición específica en la competencia."""
    if not target_position or target_position == "N/A":
        return 0.0
    
    total_offsides = 0
    total_minutes = 0
    
    # Normalize target position for matching (case-insensitive)
    target_normalized = target_position.strip()
    
    # Get all unique teams
    all_teams = set()
    for match in all_matches:
        home_team = match.get("home_team")
        away_team = match.get("away_team")
        if home_team:
            all_teams.add(home_team)
        if away_team:
            all_teams.add(away_team)
    
    # Extract player stats for all teams
    for team_name in all_teams:
        team_matches = get_opponent_matches_data(all_matches, team_name)
        if not team_matches:
            continue
        
        player_stats = extract_player_stats_from_matches(team_matches, team_name)
        
        # Filter for players with matching position (exact match, case-insensitive)
        for player_id, stats in player_stats.items():
            position = stats.get("position", "").strip()
            player_offsides = stats.get("offsides", 0)
            player_minutes = stats.get("total_minutes", 0)
            
            # Exact position match (case-insensitive) - include ALL players in position, not just those with offsides
            if position.lower() == target_normalized.lower() and player_minutes > 0:
                total_offsides += player_offsides
                total_minutes += player_minutes
    
    # Calculate average: total offsides / total minutes * 90
    if total_minutes > 0:
        return (total_offsides / total_minutes) * 90
    return 0.0


def analyze_set_pieces(matches: List[Dict], team_name: str) -> Dict:
    """Analiza estadísticas de set pieces."""
    set_pieces_stats = {
        "corners": {"won": 0, "lost": 0, "total": 0},
        "free_kicks": {"won": 0, "lost": 0, "total": 0},
        "penalties": {"taken": 0, "scored": 0, "missed": 0},
        "matches": 0
    }
    
    for match in matches:
        match_data = match.get("match_data")
        if not match_data:
            continue
        
        stats = match.get("opponent_stats", {})
        if not stats:
            continue
        
        set_pieces_stats["matches"] += 1
        
        # Corners
        corners_won = stats.get("wonCorners", 0)
        corners_lost = stats.get("lostCorners", 0)
        set_pieces_stats["corners"]["won"] += corners_won
        set_pieces_stats["corners"]["lost"] += corners_lost
        set_pieces_stats["corners"]["total"] += (corners_won + corners_lost)
        
        # Free kicks (fouls won/lost)
        fk_won = stats.get("fkFoulWon", 0)
        fk_lost = stats.get("fkFoulLost", 0)
        set_pieces_stats["free_kicks"]["won"] += fk_won
        set_pieces_stats["free_kicks"]["lost"] += fk_lost
        set_pieces_stats["free_kicks"]["total"] += (fk_won + fk_lost)
        
        # Penalties (necesitaríamos eventos específicos, por ahora usar stats si están disponibles)
        # Esto requeriría buscar en los eventos del partido
    
    # Calcular promedios
    if set_pieces_stats["matches"] > 0:
        matches_count = set_pieces_stats["matches"]
        set_pieces_stats["corners"]["avg_won"] = set_pieces_stats["corners"]["won"] / matches_count
        set_pieces_stats["corners"]["avg_lost"] = set_pieces_stats["corners"]["lost"] / matches_count
        set_pieces_stats["free_kicks"]["avg_won"] = set_pieces_stats["free_kicks"]["won"] / matches_count
        set_pieces_stats["free_kicks"]["avg_lost"] = set_pieces_stats["free_kicks"]["lost"] / matches_count
    
    return set_pieces_stats


def display_set_pieces_analysis(set_pieces_stats: Dict, team_name: str):
    """Muestra análisis de set pieces."""
    if not set_pieces_stats or set_pieces_stats["matches"] == 0:
        st.info("No hay datos de set pieces disponibles.")
        return
    
    st.markdown("""
    <h3 style='color:#ff8c00; margin-top:20px;'>Análisis de Set Pieces</h3>
    """, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <h4 style='color:#ff8c00; margin-top:15px;'>Corners</h4>
        """, unsafe_allow_html=True)
        corners_won = set_pieces_stats["corners"]["won"]
        corners_lost = set_pieces_stats["corners"]["lost"]
        avg_won = set_pieces_stats["corners"].get("avg_won", 0)
        avg_lost = set_pieces_stats["corners"].get("avg_lost", 0)
        
        st.metric("Corners Ganados", f"{corners_won}", delta=f"{avg_won:.2f} por partido")
        st.metric("Corners Recibidos", f"{corners_lost}", delta=f"{avg_lost:.2f} por partido")
        
        if corners_won + corners_lost > 0:
            win_rate = (corners_won / (corners_won + corners_lost)) * 100
            st.metric("Tasa de Ganancia", f"{win_rate:.1f}%")
    
    with col2:
        st.markdown("""
        <h4 style='color:#ff8c00; margin-top:15px;'>Tiros Libres</h4>
        """, unsafe_allow_html=True)
        fk_won = set_pieces_stats["free_kicks"]["won"]
        fk_lost = set_pieces_stats["free_kicks"]["lost"]
        avg_won = set_pieces_stats["free_kicks"].get("avg_won", 0)
        avg_lost = set_pieces_stats["free_kicks"].get("avg_lost", 0)
        
        st.metric("Faltas a Favor", f"{fk_won}", delta=f"{avg_won:.2f} por partido")
        st.metric("Faltas en Contra", f"{fk_lost}", delta=f"{avg_lost:.2f} por partido")
        
        if fk_won + fk_lost > 0:
            win_rate = (fk_won / (fk_won + fk_lost)) * 100
            st.metric("Tasa de Ganancia", f"{win_rate:.1f}%")
    
    with col3:
        st.markdown("""
        <h4 style='color:#ff8c00; margin-top:15px;'>Penales</h4>
        """, unsafe_allow_html=True)
        penalties_taken = set_pieces_stats["penalties"]["taken"]
        penalties_scored = set_pieces_stats["penalties"]["scored"]
        penalties_missed = set_pieces_stats["penalties"]["missed"]
        
        st.metric("Penales Ejecutados", f"{penalties_taken}", delta="Total")
        if penalties_taken > 0:
            conversion_rate = (penalties_scored / penalties_taken) * 100
            st.metric("Conversión", f"{conversion_rate:.1f}%", delta=f"{penalties_scored}/{penalties_taken}")
        else:
            st.info("Sin datos de penales")
    
    # Gráfico de set pieces
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""
    <h3 style='color:#ff8c00; margin-top:20px;'>Comparación de Set Pieces</h3>
    """, unsafe_allow_html=True)
    
    categories = ["Corners\nGanados", "Corners\nRecibidos", "Faltas a\nFavor", "Faltas en\nContra"]
    values = [
        set_pieces_stats["corners"].get("avg_won", 0),
        set_pieces_stats["corners"].get("avg_lost", 0),
        set_pieces_stats["free_kicks"].get("avg_won", 0),
        set_pieces_stats["free_kicks"].get("avg_lost", 0)
    ]
    
    fig = go.Figure()
    # Use adaptive text colors
    colors = ['#10B981', '#EF4444', '#10B981', '#EF4444']
    text_colors = [get_text_color(color) for color in colors]
    fig.add_trace(go.Bar(
        x=categories,
        y=values,
        marker_color=colors,
        marker_line=dict(width=0),
        text=[f"{v:.2f}" for v in values],
        textposition='inside',
        textfont=dict(color=text_colors, size=14, family="Arial Black")
    ))
    
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=400,
        xaxis_title="Tipo de Set Piece",
        yaxis_title="Promedio por Partido",
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)


def analyze_match_phases_from_df(df: pd.DataFrame, team_name: str) -> Dict:
    """Analiza el rendimiento por fases del partido desde DataFrame de Wyscout.
    Nota: Wyscout no tiene datos de goles por fase, así que retornamos estructura vacía con mensaje."""
    phase_stats = {
        "first_15": {"goals_for": 0, "goals_against": 0, "matches": 0},
        "16_30": {"goals_for": 0, "goals_against": 0, "matches": 0},
        "31_45": {"goals_for": 0, "goals_against": 0, "matches": 0},
        "46_60": {"goals_for": 0, "goals_against": 0, "matches": 0},
        "61_75": {"goals_for": 0, "goals_against": 0, "matches": 0},
        "76_90": {"goals_for": 0, "goals_against": 0, "matches": 0},
        "90_plus": {"goals_for": 0, "goals_against": 0, "matches": 0}
    }
    
    # Wyscout team stats no incluyen datos de goles por fase temporal
    # Retornamos estructura vacía pero con conteo de partidos
    if not df.empty and "Team" in df.columns:
        team_name_no_accents = remove_accents(team_name).lower().strip()
        team_df = df[df["Team"].apply(lambda x: remove_accents(str(x)).lower().strip() == team_name_no_accents)].copy()
        match_count = len(team_df)
        
        # Actualizar conteo de partidos para todas las fases
        for phase in phase_stats:
            phase_stats[phase]["matches"] = match_count
    
    return phase_stats

def analyze_match_phases(matches: List[Dict], team_name: str) -> Dict:
    """Analiza el rendimiento por fases del partido (Scoresway JSON format)."""
    phase_stats = {
        "first_15": {"goals_for": 0, "goals_against": 0, "matches": 0},
        "16_30": {"goals_for": 0, "goals_against": 0, "matches": 0},
        "31_45": {"goals_for": 0, "goals_against": 0, "matches": 0},
        "46_60": {"goals_for": 0, "goals_against": 0, "matches": 0},
        "61_75": {"goals_for": 0, "goals_against": 0, "matches": 0},
        "76_90": {"goals_for": 0, "goals_against": 0, "matches": 0},
        "90_plus": {"goals_for": 0, "goals_against": 0, "matches": 0}
    }
    
    for match in matches:
        match_data = match.get("match_data")
        if not match_data:
            continue
        
        match_info_data = match_data.get("matchInfo", {})
        if not match_info_data:
            continue
        
        # Get team IDs and names from matchInfo
        contestants = match_info_data.get("contestant", [])
        if len(contestants) < 2:
            continue
        
        # Find which contestant is the team we're analyzing
        team_contestant_id = None
        team_name_lower = team_name.lower().strip()
        team_base = team_name_lower.replace(' fc', '').strip()
        
        for contestant in contestants:
            name = contestant.get("name") or contestant.get("shortName") or contestant.get("officialName", "")
            name_lower = name.lower().strip() if name else ""
            name_base = name_lower.replace(' fc', '').strip()
            
            if (team_name_lower in name_lower or 
                name_lower in team_name_lower or
                team_base in name_base or
                name_base in team_base):
                team_contestant_id = contestant.get("id", "")
                break
        
        if not team_contestant_id:
            continue
        
        # Get goals from liveData
        live_data = match_data.get("liveData", {})
        goals = live_data.get("goal", [])
        
        phase_stats["first_15"]["matches"] += 1
        phase_stats["16_30"]["matches"] += 1
        phase_stats["31_45"]["matches"] += 1
        phase_stats["46_60"]["matches"] += 1
        phase_stats["61_75"]["matches"] += 1
        phase_stats["76_90"]["matches"] += 1
        phase_stats["90_plus"]["matches"] += 1
        
        for goal in goals:
            goal_contestant_id = goal.get("contestantId", "")
            time = goal.get("timeMin", 0)
            
            # Determine if this goal is for the team we're analyzing
            is_team_goal = (goal_contestant_id == team_contestant_id)
            
            if time <= 15:
                if is_team_goal:
                    phase_stats["first_15"]["goals_for"] += 1
                else:
                    phase_stats["first_15"]["goals_against"] += 1
            elif time <= 30:
                if is_team_goal:
                    phase_stats["16_30"]["goals_for"] += 1
                else:
                    phase_stats["16_30"]["goals_against"] += 1
            elif time <= 45:
                if is_team_goal:
                    phase_stats["31_45"]["goals_for"] += 1
                else:
                    phase_stats["31_45"]["goals_against"] += 1
            elif time <= 60:
                if is_team_goal:
                    phase_stats["46_60"]["goals_for"] += 1
                else:
                    phase_stats["46_60"]["goals_against"] += 1
            elif time <= 75:
                if is_team_goal:
                    phase_stats["61_75"]["goals_for"] += 1
                else:
                    phase_stats["61_75"]["goals_against"] += 1
            elif time <= 90:
                if is_team_goal:
                    phase_stats["76_90"]["goals_for"] += 1
                else:
                    phase_stats["76_90"]["goals_against"] += 1
            else:
                if is_team_goal:
                    phase_stats["90_plus"]["goals_for"] += 1
                else:
                    phase_stats["90_plus"]["goals_against"] += 1
    
    # Calcular promedios
    for phase in phase_stats.values():
        if phase["matches"] > 0:
            phase["avg_goals_for"] = phase["goals_for"] / phase["matches"]
            phase["avg_goals_against"] = phase["goals_against"] / phase["matches"]
    
    return phase_stats


def analyze_event_patterns(matches: List[Dict], team_name: str) -> Dict:
    """Analiza patrones de eventos (cuándo ocurren goles, tarjetas, sustituciones)."""
    patterns = {
        "goal_times": [],
        "card_times": [],
        "substitution_times": [],
        "goals_after_scoring": {"for": 0, "against": 0},
        "goals_after_conceding": {"for": 0, "against": 0}
    }
    
    for match in matches:
        match_data = match.get("match_data")
        if not match_data:
            continue
        
        match_info_data = match_data.get("matchInfo", {})
        if not match_info_data:
            continue
        
        # Get team IDs
        contestants = match_info_data.get("contestant", [])
        if len(contestants) < 2:
            continue
        
        team_contestant_id = None
        opponent_contestant_id = None
        team_name_no_accents = remove_accents(team_name).lower().strip()
        team_base = team_name_no_accents.replace(' fc', '').strip()
        
        for contestant in contestants:
            name = contestant.get("name") or contestant.get("shortName") or contestant.get("officialName", "")
            name_no_accents = remove_accents(name).lower().strip() if name else ""
            name_base = name_no_accents.replace(' fc', '').strip()
            
            if (team_name_no_accents in name_no_accents or
                name_no_accents in team_name_no_accents or
                team_base in name_base or
                name_base in team_base):
                team_contestant_id = contestant.get("id", "")
            else:
                opponent_contestant_id = contestant.get("id", "")
        
        if not team_contestant_id:
            continue
        
        # Get opponent name for events
        opponent_name = ""
        for contestant in contestants:
            if contestant.get("id") == opponent_contestant_id:
                opponent_name = contestant.get("name") or contestant.get("shortName", "")
                break
        
        events = extract_match_events(match_data, team_name, opponent_name)
        
        last_goal_time = None
        last_goal_team = None
        
        for event in events:
            if event["type"] == "goal":
                time = event.get("time", 0)
                is_team = event.get("is_team", False)
                patterns["goal_times"].append({"time": time, "is_team": is_team})
                
                if last_goal_time is not None:
                    time_diff = time - last_goal_time
                    if time_diff <= 10:  # Gol dentro de 10 minutos
                        if last_goal_team == team_name and is_team:
                            patterns["goals_after_scoring"]["for"] += 1
                        elif last_goal_team == team_name and not is_team:
                            patterns["goals_after_scoring"]["against"] += 1
                        elif last_goal_team != team_name and is_team:
                            patterns["goals_after_conceding"]["for"] += 1
                        elif last_goal_team != team_name and not is_team:
                            patterns["goals_after_conceding"]["against"] += 1
                
                last_goal_time = time
                last_goal_team = team_name if is_team else opponent_name
            
            elif event["type"] == "card":
                patterns["card_times"].append(event.get("time", 0))
            
            elif event["type"] == "substitution":
                patterns["substitution_times"].append(event.get("time", 0))
    
    return patterns


def analyze_momentum(matches: List[Dict], team_name: str) -> Dict:
    """Analiza cambios de momentum durante los partidos."""
    momentum_data = {
        "comebacks": 0,
        "blown_leads": 0,
        "comeback_wins": 0,
        "comeback_draws": 0,
        "comeback_losses": 0
    }
    
    for match in matches:
        match_data = match.get("match_data")
        if not match_data:
            continue
        
        match_info_data = match_data.get("matchInfo", {})
        if not match_info_data:
            continue
        
        # Get team IDs
        contestants = match_info_data.get("contestant", [])
        if len(contestants) < 2:
            continue
        
        team_contestant_id = None
        team_name_no_accents = remove_accents(team_name).lower().strip()
        team_base = team_name_no_accents.replace(' fc', '').strip()
        
        for contestant in contestants:
            name = contestant.get("name") or contestant.get("shortName") or contestant.get("officialName", "")
            name_no_accents = remove_accents(name).lower().strip() if name else ""
            name_base = name_no_accents.replace(' fc', '').strip()
            
            if (team_name_no_accents in name_no_accents or
                name_no_accents in team_name_no_accents or
                team_base in name_base or
                name_base in team_base):
                team_contestant_id = contestant.get("id", "")
                break
        
        if not team_contestant_id:
            continue
        
        # Get opponent name
        opponent_name = ""
        for contestant in contestants:
            if contestant.get("id") != team_contestant_id:
                opponent_name = contestant.get("name") or contestant.get("shortName", "")
                break
        
        events = extract_match_events(match_data, team_name, opponent_name)
        goals = [e for e in events if e["type"] == "goal"]
        
        if len(goals) < 2:
            continue
        
        # Calcular score en cada momento
        team_score = 0
        opp_score = 0
        was_leading = False
        was_trailing = False
        came_back = False
        blew_lead = False
        
        for goal in goals:
            if goal.get("is_team", False):
                team_score += 1
            else:
                opp_score += 1
            
            if team_score > opp_score:
                if was_trailing:
                    came_back = True
                was_leading = True
                was_trailing = False
            elif team_score < opp_score:
                if was_leading:
                    blew_lead = True
                was_trailing = True
                was_leading = False
            else:
                was_leading = False
                was_trailing = False
        
        if came_back:
            momentum_data["comebacks"] += 1
            result = extract_match_result(match_data, team_name)
            if result:
                if result["result"] == "W":
                    momentum_data["comeback_wins"] += 1
                elif result["result"] == "D":
                    momentum_data["comeback_draws"] += 1
                else:
                    momentum_data["comeback_losses"] += 1
        
        if blew_lead:
            momentum_data["blown_leads"] += 1
    
    return momentum_data


def create_formation_chart(formation_stats: Dict, team_color: str):
    """Crea gráfico de formaciones."""
    if not formation_stats:
        return None
    
    formations = list(formation_stats.keys())
    win_rates = [formation_stats[f].get("win_rate", 0) for f in formations]
    counts = [formation_stats[f].get("count", 0) for f in formations]
    
    # Asegurar que el color tenga el formato correcto
    if not team_color.startswith('#'):
        team_color = '#' + team_color
    
    fig = go.Figure()
    
    # Determine text color based on bar color brightness
    text_color = get_text_color(team_color)
    
    fig.add_trace(go.Bar(
        x=formations,
        y=win_rates,
        marker_color=team_color,  # Use marker_color directly (more reliable than marker dict)
        marker_line=dict(width=0),  # Remove border
        text=[f"{wr:.1f}%" for wr in win_rates],
        textposition='inside',  # Anchor text inside the bar
        textfont=dict(color=text_color, size=14, family="Arial Black"),
        name="Tasa de Victoria",
        hovertemplate="<b>%{x}</b><br>Tasa de Victoria: %{y:.1f}%<br>Partidos: %{customdata}<extra></extra>",
        customdata=counts
    ))
    
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=400,
        xaxis_title="Formación",
        yaxis_title="Tasa de Victoria (%)",
        showlegend=False,
        font=dict(color='white')
    )
    
    return fig


def lighten_color(hex_color: str, factor: float = 0.5) -> str:
    """Lighten a hex color by a factor (0-1). Factor of 0.5 makes it 50% lighter."""
    # Remove # if present
    hex_color = hex_color.lstrip('#')
    
    # Convert to RGB
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    
    # Lighten by moving towards white (255, 255, 255)
    r = int(r + (255 - r) * factor)
    g = int(g + (255 - g) * factor)
    b = int(b + (255 - b) * factor)
    
    # Ensure values are within 0-255
    r = min(255, max(0, r))
    g = min(255, max(0, g))
    b = min(255, max(0, b))
    
    # Convert back to hex
    return f"#{r:02x}{g:02x}{b:02x}"


def get_text_color(hex_color, team_name=None):
    """Determine if text should be black or white based on color brightness or team-specific rules."""
    # Team-specific text color rules (for Análisis Táctico y Fases tab)
    team_text_color_rules = {
        "Moca": "black",
        "Atlántico": "white",
        "Atlético Pantoja": "black",
        "Delfines Del Este": "white",
        "Don Bosco Jarabacoa": "black",
        "Salcedo": "white",
        "Universidad O&M": "white",
        "Vega Real": "white",
        "Cibao": "black"
    }
    
    # If team name is provided and has a specific rule, use it
    if team_name:
        team_name_normalized = team_name.strip()
        # Check exact match first
        if team_name_normalized in team_text_color_rules:
            return team_text_color_rules[team_name_normalized]
        # Check case-insensitive match
        for team, color in team_text_color_rules.items():
            if team_name_normalized.lower() == team.lower():
                return color
    
    # Default: calculate based on color brightness
    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    # Calculate brightness (0-255)
    brightness = (r * 299 + g * 587 + b * 114) / 1000
    # If brightness is above 128, use black text; otherwise white
    return 'black' if brightness > 128 else 'white'

def create_phase_chart(phase_stats: Dict, team_color: str, metric_config: Dict = None, team_name: str = None):
    """Crea gráfico de fases del partido."""
    phases = ["0-15'", "16-30'", "31-45'", "46-60'", "61-75'", "76-90'", "90+'"]
    phase_keys = ["first_15", "16_30", "31_45", "46_60", "61_75", "76_90", "90_plus"]
    
    # Default to average goals if no metric config provided
    if metric_config is None:
        metric_config = {
            "for_key": "avg_goals_for",
            "against_key": "avg_goals_against",
            "y_axis_title": "Promedio de Goles",
            "for_label": "Goles a Favor",
            "against_label": "Goles en Contra"
        }
    
    # Get values based on selected metric
    if metric_config["for_key"] == "goal_difference":
        # Calculate difference for each phase (goals_for - goals_against)
        values_for = [
            phase_stats[key].get("goals_for", 0) - phase_stats[key].get("goals_against", 0)
            for key in phase_keys
        ]
        values_against = None  # Don't show second trace for difference
    else:
        values_for = [phase_stats[key].get(metric_config["for_key"], 0) for key in phase_keys]
        if metric_config.get("against_key"):
            values_against = [phase_stats[key].get(metric_config["against_key"], 0) for key in phase_keys]
        else:
            values_against = None
    
    # Asegurar que el color tenga el formato correcto
    if not team_color.startswith('#'):
        team_color = '#' + team_color
    
    # CRITICAL: Store original color to verify it's not being changed
    original_color = team_color
    
    # For tactical analysis tab: use opponent's color for goals scored, lighter shade for goals conceded
    goals_for_color = team_color
    goals_against_color = lighten_color(team_color, factor=0.75)  # 75% lighter (more distinct)
    
    # Debug: verify color is correct (will show in console if there's an issue)
    if goals_for_color != original_color:
        import sys
        print(f"WARNING: Color changed from {original_color} to {goals_for_color}", file=sys.stderr)
    
    # Determine colors
    goals_for_color = team_color
    if values_against is not None:
        goals_against_color = lighten_color(team_color, factor=0.75)  # 75% lighter (more distinct)
    else:
        goals_against_color = None
    
    fig = go.Figure()
    
    # Determine text colors based on bar color brightness or team-specific rules
    goals_for_text_color = get_text_color(goals_for_color, team_name=team_name)
    
    # Format text based on metric type
    if metric_config["for_key"] == "goal_difference":
        text_format = [f"{v:+.1f}" for v in values_for]
    elif "avg" in metric_config["for_key"]:
        text_format = [f"{v:.2f}" for v in values_for]
    else:
        text_format = [f"{int(v)}" for v in values_for]
    
    fig.add_trace(go.Bar(
        x=phases,
        y=values_for,
        name=metric_config["for_label"],
        marker_color=goals_for_color,
        marker_line=dict(width=0),
        text=text_format,
        textposition='inside',
        textfont=dict(color=goals_for_text_color, size=14, family="Arial Black")
    ))
    
    # Add second trace only if against_key is provided
    if values_against is not None:
        goals_against_text_color = get_text_color(goals_against_color, team_name=team_name)
        if "avg" in metric_config["against_key"]:
            text_format_against = [f"{v:.2f}" for v in values_against]
        else:
            text_format_against = [f"{int(v)}" for v in values_against]
        
        fig.add_trace(go.Bar(
            x=phases,
            y=values_against,
            name=metric_config["against_label"],
            marker_color=goals_against_color,
            marker_line=dict(width=0),
            text=text_format_against,
            textposition='inside',
            textfont=dict(color=goals_against_text_color, size=14, family="Arial Black")
        ))
    
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=400,
        xaxis_title="Fase del Partido",
        yaxis_title=metric_config["y_axis_title"],
        barmode='group',
        font=dict(color='white'),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    return fig


def create_goal_timing_chart(patterns: Dict, team_color: str):
    """Crea gráfico de distribución temporal de goles."""
    goal_times = patterns.get("goal_times", [])
    if not goal_times:
        return None
    
    team_goals = [g["time"] for g in goal_times if g.get("is_team", False)]
    opp_goals = [g["time"] for g in goal_times if not g.get("is_team", False)]
    
    # Asegurar que el color tenga el formato correcto
    if not team_color.startswith('#'):
        team_color = '#' + team_color
    
    # Use a much lighter, more distinct color for opponent goals
    # For overlay histograms, we need very distinct colors
    opponent_color = lighten_color(team_color, factor=0.9)  # 90% lighter for maximum distinction
    
    # Create phase-based bins instead of automatic binning for better clarity
    # Use 15-minute intervals: 0-15, 15-30, 30-45, 45-60, 60-75, 75-90, 90+
    phase_bins = [0, 15, 30, 45, 60, 75, 90, 120]  # 120 to catch any extra time
    
    # Count goals in each phase for team
    team_counts = [0] * (len(phase_bins) - 1)
    for goal_time in team_goals:
        for i in range(len(phase_bins) - 1):
            if phase_bins[i] <= goal_time < phase_bins[i + 1]:
                team_counts[i] += 1
                break
    
    # Count goals in each phase for opponent
    opp_counts = [0] * (len(phase_bins) - 1)
    for goal_time in opp_goals:
        for i in range(len(phase_bins) - 1):
            if phase_bins[i] <= goal_time < phase_bins[i + 1]:
                opp_counts[i] += 1
                break
    
    # Create phase labels
    phase_labels = ["0-15'", "15-30'", "30-45'", "45-60'", "60-75'", "75-90'", "90+'"]
    
    fig = go.Figure()
    
    # Add team goals trace
    fig.add_trace(go.Bar(
        x=phase_labels,
        y=team_counts,
        name="Goles a Favor",
        marker_color=team_color,
        marker_line=dict(width=0),
        opacity=0.8,
        text=[f"{count}" if count > 0 else "" for count in team_counts],
        textposition='inside',
        textfont=dict(color=get_text_color(team_color), size=14, family="Arial Black")
    ))
    
    # Add opponent goals trace
    fig.add_trace(go.Bar(
        x=phase_labels,
        y=opp_counts,
        name="Goles en Contra",
        marker_color=opponent_color,
        marker_line=dict(width=0),
        opacity=0.8,
        text=[f"{count}" if count > 0 else "" for count in opp_counts],
        textposition='inside',
        textfont=dict(color=get_text_color(opponent_color), size=14, family="Arial Black")
    ))
    
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=400,
        xaxis_title="Fase del Partido",
        yaxis_title="Cantidad de Goles",
        barmode='group',  # Changed from 'overlay' to 'group' for better visibility
        font=dict(color='white'),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    return fig


def analyze_timeline_patterns(matches: List[Dict], team_name: str) -> Dict:
    """Analiza patrones temporales de goles (cuándo marcan y reciben)."""
    timeline_stats = {
        "goals_for": {"0-15": 0, "16-30": 0, "31-45": 0, "46-60": 0, "61-75": 0, "76-90": 0, "90+": 0},
        "goals_against": {"0-15": 0, "16-30": 0, "31-45": 0, "46-60": 0, "61-75": 0, "76-90": 0, "90+": 0},
        "total_goals_for": 0,
        "total_goals_against": 0
    }
    
    for match in matches:
        match_data = match.get("match_data")
        if not match_data:
            continue
        
        live_data = match_data.get("liveData", {})
        goals = live_data.get("goal", [])
        match_info = match_data.get("matchInfo", {})
        contestants = match_info.get("contestant", [])
        
        for goal in goals:
            contestant_id = goal.get("contestantId", "")
            time_min = goal.get("timeMin", 0)
            period_id = goal.get("periodId", 1)  # 1 = first half, 2 = second half
            
            # Determinar período de tiempo
            if period_id == 1:
                if time_min <= 15:
                    period = "0-15"
                elif time_min <= 30:
                    period = "16-30"
                else:
                    period = "31-45"
            else:  # period_id == 2
                if time_min <= 60:
                    period = "46-60"
                elif time_min <= 75:
                    period = "61-75"
                elif time_min <= 90:
                    period = "76-90"
                else:
                    period = "90+"
            
            # Verificar si el gol es del equipo analizado
            for contestant in contestants:
                if contestant.get("id") == contestant_id:
                    name = contestant.get("name") or contestant.get("shortName") or contestant.get("officialName", "")
                    if team_name.lower() in name.lower():
                        timeline_stats["goals_for"][period] += 1
                        timeline_stats["total_goals_for"] += 1
                    else:
                        timeline_stats["goals_against"][period] += 1
                        timeline_stats["total_goals_against"] += 1
                    break
    
    return timeline_stats


def display_timeline_patterns(timeline_stats: Dict, team_name: str):
    """Muestra patrones temporales de goles."""
    if timeline_stats["total_goals_for"] == 0 and timeline_stats["total_goals_against"] == 0:
        st.info("No hay datos de goles para análisis temporal.")
        return
    
    st.markdown("""
    <h3 style='color:#ff8c00; margin-top:20px;'>Patrones Temporales de Goles</h3>
    """, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    periods = ["0-15", "16-30", "31-45", "46-60", "61-75", "76-90", "90+"]
    goals_for = [timeline_stats["goals_for"][p] for p in periods]
    goals_against = [timeline_stats["goals_against"][p] for p in periods]
    
    # Gráfico de barras
    fig = go.Figure()
    
    # Use adaptive text colors
    goals_for_color = '#10B981'
    goals_against_color = '#EF4444'
    goals_for_text_color = get_text_color(goals_for_color)
    goals_against_text_color = get_text_color(goals_against_color)
    
    fig.add_trace(go.Bar(
        name="Goles a Favor",
        x=periods,
        y=goals_for,
        marker_color=goals_for_color,
        marker_line=dict(width=0),
        text=goals_for,
        textposition='inside',
        textfont=dict(color=goals_for_text_color, size=14, family="Arial Black")
    ))
    
    fig.add_trace(go.Bar(
        name="Goles en Contra",
        x=periods,
        y=goals_against,
        marker_color=goals_against_color,
        marker_line=dict(width=0),
        text=goals_against,
        textposition='inside',
        textfont=dict(color=goals_against_text_color, size=14, family="Arial Black")
    ))
    
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=500,
        xaxis_title="Minuto del Partido",
        yaxis_title="Cantidad de Goles",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5
        ),
        barmode='group'
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Estadísticas clave
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""
    <h3 style='color:#ff8c00; margin-top:20px;'>Insights Temporales</h3>
    """, unsafe_allow_html=True)
    
    # Encontrar períodos más productivos
    max_goals_period = max(periods, key=lambda p: timeline_stats["goals_for"][p])
    max_goals_value = timeline_stats["goals_for"][max_goals_period]
    
    # Encontrar períodos más vulnerables
    max_conceded_period = max(periods, key=lambda p: timeline_stats["goals_against"][p])
    max_conceded_value = timeline_stats["goals_against"][max_conceded_period]
    
    col1, col2 = st.columns(2)
    
    with col1:
        if max_goals_value > 0:
            percentage = (max_goals_value / timeline_stats["total_goals_for"]) * 100 if timeline_stats["total_goals_for"] > 0 else 0
            st.metric(
                "Período Más Productivo",
                f"Minutos {max_goals_period}",
                delta=f"{max_goals_value} goles ({percentage:.1f}% del total)"
            )
        else:
            st.info("Sin goles registrados")
    
    with col2:
        if max_conceded_value > 0:
            percentage = (max_conceded_value / timeline_stats["total_goals_against"]) * 100 if timeline_stats["total_goals_against"] > 0 else 0
            st.metric(
                "Período Más Vulnerable",
                f"Minutos {max_conceded_period}",
                delta=f"{max_conceded_value} goles recibidos ({percentage:.1f}% del total)"
            )
        else:
            st.info("Sin goles recibidos")
    
    # Análisis de primera y segunda parte
    first_half_goals = sum(timeline_stats["goals_for"][p] for p in ["0-15", "16-30", "31-45"])
    second_half_goals = sum(timeline_stats["goals_for"][p] for p in ["46-60", "61-75", "76-90", "90+"])
    first_half_conceded = sum(timeline_stats["goals_against"][p] for p in ["0-15", "16-30", "31-45"])
    second_half_conceded = sum(timeline_stats["goals_against"][p] for p in ["46-60", "61-75", "76-90", "90+"])
    
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Primera Parte**")
        st.metric("Goles a Favor", first_half_goals)
        st.metric("Goles en Contra", first_half_conceded)
    
    with col2:
        st.markdown("**Segunda Parte**")
        st.metric("Goles a Favor", second_half_goals)
        st.metric("Goles en Contra", second_half_conceded)
    
    if timeline_stats["total_goals_for"] > 0:
        second_half_pct = (second_half_goals / timeline_stats["total_goals_for"]) * 100
        if second_half_pct >= 60:
            st.success(f"**Insight:** Este equipo marca {second_half_pct:.1f}% de sus goles en la segunda parte. Mantener la concentración defensiva en el segundo tiempo es crucial.")


def analyze_vulnerabilities(opponent_metrics: Dict, cibao_metrics: Dict, opponent_name: str) -> List[str]:
    """Identifica vulnerabilidades del oponente basándose en comparación con Cibao y promedios."""
    vulnerabilities = []
    
    # Comparar goles recibidos
    opp_goals_conceded = opponent_metrics.get("goalsConceded", 0)
    cibao_goals_conceded = cibao_metrics.get("goalsConceded", 0)
    if opp_goals_conceded > cibao_goals_conceded * 1.2:  # 20% más
        vulnerabilities.append(f"**Defensa vulnerable:** Recibe {opp_goals_conceded:.2f} goles por partido (vs {cibao_goals_conceded:.2f} de Cibao). Oportunidad para atacar.")
    
    # Comparar precisión de pases
    opp_pass_acc = opponent_metrics.get("passAccuracy", 0)
    cibao_pass_acc = cibao_metrics.get("passAccuracy", 0)
    if opp_pass_acc < cibao_pass_acc - 5:  # 5% menos
        vulnerabilities.append(f"**Pases imprecisos:** {opp_pass_acc:.1f}% de precisión (vs {cibao_pass_acc:.1f}% de Cibao). Presionar alto puede forzar errores.")
    
    # Comparar tackles exitosos
    opp_tackle_success = opponent_metrics.get("tackleSuccess", 0)
    cibao_tackle_success = cibao_metrics.get("tackleSuccess", 0)
    if opp_tackle_success < cibao_tackle_success - 10:  # 10% menos
        vulnerabilities.append(f"**Tackles débiles:** {opp_tackle_success:.1f}% de efectividad (vs {cibao_tackle_success:.1f}% de Cibao). Aprovechar espacios en el medio campo.")
    
    # Analizar tarjetas (disciplina)
    opp_yellow = opponent_metrics.get("totalYellowCard", 0)
    opp_red = opponent_metrics.get("totalRedCard", 0)
    if opp_yellow > 2.5:  # Más de 2.5 tarjetas amarillas por partido
        vulnerabilities.append(f"**Disciplina débil:** {opp_yellow:.1f} tarjetas amarillas por partido. Aprovechar faltas y situaciones de set pieces.")
    
    # Analizar corners recibidos
    opp_corners_lost = opponent_metrics.get("lostCorners", 0)
    if opp_corners_lost > 5:  # Más de 5 corners recibidos por partido
        vulnerabilities.append(f"**Vulnerable en corners:** Recibe {opp_corners_lost:.1f} corners por partido. Trabajar jugadas a balón parado.")
    
    # Analizar posesión (si es baja, pueden ser vulnerables a presión)
    opp_possession = opponent_metrics.get("possessionPercentage", 0)
    if opp_possession < 45:
        vulnerabilities.append(f"**Baja posesión:** Solo {opp_possession:.1f}% de posesión promedio. Presionar alto puede recuperar balones rápidamente.")
    
    return vulnerabilities


def generate_match_recommendations(
    opponent_metrics: Dict,
    cibao_metrics: Dict,
    formation_stats: Dict,
    timeline_stats: Dict,
    set_pieces_stats: Dict,
    vulnerabilities: List[str],
    opponent_name: str
) -> List[str]:
    """Genera recomendaciones automáticas para la preparación del partido."""
    recommendations = []
    
    # Recomendaciones basadas en formaciones
    if formation_stats:
        sorted_formations = sorted(formation_stats.items(), key=lambda x: x[1]["count"], reverse=True)
        if sorted_formations:
            most_used = sorted_formations[0]
            formation = most_used[0]
            usage_pct = (most_used[1]["count"] / sum(s["count"] for _, s in formation_stats.items())) * 100
            if usage_pct >= 60:
                recommendations.append(f"**Formación esperada:** {formation} (usada en {usage_pct:.0f}% de partidos). Preparar tácticas específicas para esta formación.")
    
    # Recomendaciones basadas en patrones temporales
    if timeline_stats["total_goals_for"] > 0:
        second_half_pct = (sum(timeline_stats["goals_for"][p] for p in ["46-60", "61-75", "76-90", "90+"]) / timeline_stats["total_goals_for"]) * 100
        if second_half_pct >= 60:
            recommendations.append(f"**Concentración en segunda parte:** Marcan {second_half_pct:.0f}% de goles después del minuto 45. Mantener intensidad defensiva todo el partido.")
    
    # Recomendaciones basadas en set pieces
    if set_pieces_stats["matches"] > 0:
        corners_avg = set_pieces_stats["corners"].get("avg_won", 0)
        if corners_avg > 6:
            recommendations.append(f"**Atención a corners:** Obtienen {corners_avg:.1f} corners por partido. Trabajar defensa de balón parado y transiciones rápidas.")
    
    # Recomendaciones basadas en vulnerabilidades
    if vulnerabilities:
        recommendations.extend([f"**Explotar:** {v}" for v in vulnerabilities[:3]])  # Top 3 vulnerabilidades
    
    # Recomendaciones generales basadas en comparación
    opp_goals = opponent_metrics.get("goals", 0)
    cibao_goals = cibao_metrics.get("goals", 0)
    if opp_goals < cibao_goals * 0.8:
        recommendations.append(f"**Ventaja ofensiva:** Cibao marca más goles ({cibao_goals:.2f} vs {opp_goals:.2f}). Mantener presión ofensiva.")
    
    opp_possession = opponent_metrics.get("possessionPercentage", 0)
    cibao_possession = cibao_metrics.get("possessionPercentage", 0)
    if opp_possession < cibao_possession - 10:
        recommendations.append(f"**Control del juego:** Cibao tiene ventaja en posesión ({cibao_possession:.1f}% vs {opp_possession:.1f}%). Dominar el ritmo del partido.")
    
    return recommendations


def create_player_radar_chart(players_data: List[Dict], selected_metrics: List[str] = None) -> go.Figure:
    """Crea un gráfico de radar para comparar múltiples jugadores."""
    if not players_data or len(players_data) < 2:
        return None
    
    # Métricas disponibles para jugadores
    available_metrics = {
        "Goles por 90": ("goals_per_90", False),
        "Asistencias por 90": ("assists_per_90", False),
        "Disparos por 90": ("shots_per_90", False),
        "Disparos al Arco por 90": ("shots_on_target_per_90", False),
        "Precisión Disparos": ("shot_accuracy", False),
        "Pases por 90": ("passes_per_90", False),
        "Pases Precisos por 90": ("accurate_passes_per_90", False),
        "Precisión Pases": ("pass_accuracy", False),
        "Tackles por 90": ("tackles_per_90", False),
        "Tackles Exitosos por 90": ("won_tackles_per_90", False),
        "Efectividad Tackles": ("tackle_success", False),
        "Despejes por 90": ("clearances_per_90", False),
        "Intercepciones por 90": ("interceptions_per_90", False),
        "Atajadas por 90": ("saves_per_90", False),
        "Minutos por Partido": ("minutes_per_match", False),
    }
    
    # Si no se especifican métricas, usar todas
    if not selected_metrics:
        selected_metrics = list(available_metrics.keys())
    
    # Filtrar métricas válidas
    radar_metrics = {k: v for k, v in available_metrics.items() if k in selected_metrics}
    
    if not radar_metrics:
        return None
    
    # Calcular valores para cada jugador
    player_values = {}
    metric_ranges = {}
    
    for metric_label, (metric_key, invert) in radar_metrics.items():
        values = []
        for player in players_data:
            val = player.get(metric_key, 0)
            # Only include non-zero values for range calculation if we have at least one non-zero value
            # Otherwise, if all values are 0, we'll use a small default range
            values.append(val)
        
        if values:
            # Filter out None values and ensure we have numeric values
            numeric_values = [v for v in values if v is not None and isinstance(v, (int, float))]
            if numeric_values:
                min_val = min(numeric_values)
                max_val = max(numeric_values)
                # If all values are 0, set a small default range to avoid division by zero
                if min_val == 0 and max_val == 0:
                    min_val = 0
                    max_val = 1  # Small default range for zero values
                # Añadir padding del 10% para mejor visualización
                range_padding = (max_val - min_val) * 0.1 if max_val > min_val else max_val * 0.1
                metric_ranges[metric_label] = {
                    "min": max(0, min_val - range_padding),
                    "max": max_val + range_padding,
                    "invert": invert
                }
            else:
                # Fallback if no valid values
                metric_ranges[metric_label] = {
                    "min": 0,
                    "max": 1,
                    "invert": invert
                }
    
    # Normalizar valores para cada jugador
    normalized_data = {}
    for player in players_data:
        player_name = player.get("name", "Unknown")
        normalized_values = []
        hover_text = []
        
        for metric_label, (metric_key, invert) in radar_metrics.items():
            val = player.get(metric_key, 0)
            range_info = metric_ranges[metric_label]
            min_val = range_info["min"]
            max_val = range_info["max"]
            invert = range_info["invert"]
            
            # Normalizar a escala 0-100
            if invert:
                range_size = max_val - min_val if max_val > min_val else 1
                normalized = ((max_val - val) / range_size) * 100
            else:
                range_size = max_val - min_val if max_val > min_val else 1
                normalized = ((val - min_val) / range_size) * 100
            
            normalized = max(0, min(100, normalized))
            normalized_values.append(normalized)
            
            # Crear hover text con valor real
            if metric_label in ["Precisión Disparos", "Precisión Pases", "Efectividad Tackles"]:
                hover = f"{metric_label}<br>{player_name}: {val:.1f}%"
            else:
                hover = f"{metric_label}<br>{player_name}: {val:.2f}"
            hover_text.append(hover)
        
        # Cerrar el círculo
        normalized_values.append(normalized_values[0])
        hover_text.append(hover_text[0])
        
        normalized_data[player_name] = {
            "values": normalized_values,
            "hover": hover_text
        }
    
    # Crear gráfico
    fig = go.Figure()
    
    # Colores para jugadores - usar color de Cibao para jugadores de Cibao, blanco para otros
    cibao_color = '#FF8C00'  # Color oficial de Cibao
    opponent_color = '#FFFFFF'  # Blanco para mejor visibilidad en fondo negro
    
    categories = [f"{label} ({metric_ranges[label]['min']:.1f}-{metric_ranges[label]['max']:.1f})" 
                  for label in radar_metrics.keys()]
    categories.append(categories[0])  # Cerrar el círculo
    
    for idx, player in enumerate(players_data):
        player_name = player.get("name", "Unknown")
        team = player.get("team", "Unknown")
        
        # Asignar color según el equipo
        if team == "Cibao":
            color = cibao_color
        else:
            color = opponent_color
        
        rgb = tuple(int(color[i:i+2], 16) for i in (1, 3, 5))
        fillcolor = f'rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, 0.2)'
        
        data = normalized_data[player_name]
        
        # Mostrar nombre con equipo en la leyenda
        display_name = f"{player_name} ({team})"
        
        fig.add_trace(go.Scatterpolar(
            r=data["values"],
            theta=categories,
            fill='toself',
            name=display_name,
            line=dict(color=color, width=3),
            fillcolor=fillcolor,
            hovertemplate='%{text}<extra></extra>',
            text=data["hover"]
        ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickfont=dict(size=16, color='#94A3B8'),
                gridcolor='rgba(148, 163, 184, 0.3)',
                showticklabels=False
            ),
            angularaxis=dict(
                tickfont=dict(size=15, color='#FFFFFF'),
                linecolor='rgba(148, 163, 184, 0.3)'
            )
        ),
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=600,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            font=dict(size=18, color='#FFFFFF')
        ),
        title=dict(
            text="Comparación de Jugadores",
            font=dict(size=24, color='#FFFFFF'),
            x=0.5
        )
    )
    
    return fig


def generate_comparison_summary(opponent_metrics: Dict, cibao_metrics: Dict, opponent_name: str) -> Dict:
    """Genera un resumen de comparación con ventajas clave."""
    insights = {
        "cibao_advantages": [],
        "opponent_advantages": []
    }
    
    # Comparar métricas clave
    metrics_to_compare = [
        ("goals", "Goles", "marca más goles", "marca menos goles", False),
        ("goalsConceded", "Goles Recibidos", "recibe menos goles", "recibe más goles", True),
        ("possessionPercentage", "Posesión", "tiene más posesión", "tiene menos posesión", False),
        ("passAccuracy", "Precisión de Pases", "tiene mejor precisión de pases", "tiene peor precisión de pases", False),
        ("totalScoringAtt", "Disparos", "dispara más", "dispara menos", False),
        ("wonCorners", "Corners", "obtiene más corners", "obtiene menos corners", False),
        ("wonTackle", "Tackles Exitosos", "tiene más tackles exitosos", "tiene menos tackles exitosos", False),
    ]
    
    for metric_tuple in metrics_to_compare:
        if len(metric_tuple) == 5:
            metric_key, metric_name, cibao_better, opp_better, invert = metric_tuple
        else:
            metric_key, metric_name, cibao_better, opp_better = metric_tuple
            invert = False
        opp_val = opponent_metrics.get(metric_key, 0)
        cibao_val = cibao_metrics.get(metric_key, 0)
        
        if invert:
            # Para métricas donde menos es mejor (como goles recibidos)
            if cibao_val < opp_val * 0.9:  # Cibao es al menos 10% mejor
                diff_pct = ((opp_val - cibao_val) / opp_val * 100) if opp_val > 0 else 0
                insights["cibao_advantages"].append(
                    f"Cibao {cibao_better} ({cibao_val:.2f} vs {opp_val:.2f} de {opponent_name}, {diff_pct:.0f}% mejor)"
                )
            elif opp_val < cibao_val * 0.9:  # Oponente es al menos 10% mejor
                diff_pct = ((cibao_val - opp_val) / cibao_val * 100) if cibao_val > 0 else 0
                insights["opponent_advantages"].append(
                    f"{opponent_name} {opp_better} ({opp_val:.2f} vs {cibao_val:.2f} de Cibao, {diff_pct:.0f}% mejor)"
                )
        else:
            # Para métricas donde más es mejor
            if cibao_val > opp_val * 1.05:  # Cibao es al menos 5% mejor (umbral más bajo)
                diff_pct = ((cibao_val - opp_val) / opp_val * 100) if opp_val > 0 else 0
                if metric_key == "possessionPercentage" or metric_key == "passAccuracy":
                    insights["cibao_advantages"].append(
                        f"Cibao {cibao_better} ({cibao_val:.1f}% vs {opp_val:.1f}% de {opponent_name}, {diff_pct:.0f}% mejor)"
                    )
                else:
                    insights["cibao_advantages"].append(
                        f"Cibao {cibao_better} ({cibao_val:.2f} vs {opp_val:.2f} de {opponent_name}, {diff_pct:.0f}% mejor)"
                    )
            elif opp_val > cibao_val * 1.05:  # Oponente es al menos 5% mejor (umbral más bajo)
                diff_pct = ((opp_val - cibao_val) / cibao_val * 100) if cibao_val > 0 else 0
                if metric_key == "possessionPercentage" or metric_key == "passAccuracy":
                    insights["opponent_advantages"].append(
                        f"{opponent_name} {opp_better} ({opp_val:.1f}% vs {cibao_val:.1f}% de Cibao, {diff_pct:.0f}% mejor)"
                    )
                else:
                    insights["opponent_advantages"].append(
                        f"{opponent_name} {opp_better} ({opp_val:.2f} vs {cibao_val:.2f} de Cibao, {diff_pct:.0f}% mejor)"
                    )
    
    # Limitar a top 5 para cada categoría
    insights["cibao_advantages"] = insights["cibao_advantages"][:5]
    insights["opponent_advantages"] = insights["opponent_advantages"][:5]
    
    return insights


def get_performance_by_phase(matches: List[Dict], team_name: str) -> Dict:
    """Extrae estadísticas de primera y segunda parte para un equipo usando eventos de goles."""
    phase_stats = {
        "first_half": {"goals": 0, "goals_conceded": 0, "matches": set()},
        "second_half": {"goals": 0, "goals_conceded": 0, "matches": set()}
    }
    
    for match in matches:
        match_data = match.get("match_data")
        if not match_data:
            continue
        
        try:
            live_data = match_data.get("liveData", {})
            match_info = match_data.get("matchInfo", {})
            
            # Identificar qué equipo es el nuestro
            contestants = match_info.get("contestant", [])
            team_contestant_id = None
            opponent_contestant_id = None
            
            for contestant in contestants:
                name = contestant.get("name") or contestant.get("shortName", "")
                contestant_id = contestant.get("id")
                team_name_no_accents = remove_accents(team_name).lower()
                name_no_accents = remove_accents(name).lower() if name else ""
                if team_name_no_accents in name_no_accents or name_no_accents in team_name_no_accents:
                    team_contestant_id = contestant_id
                else:
                    opponent_contestant_id = contestant_id
            
            if not team_contestant_id:
                continue
            
            # Obtener eventos de goles
            events = live_data.get("event", [])
            match_id = match_info.get("id", "")
            
            for event in events:
                event_type = event.get("typeId", "")
                # Tipo 16 = Goal
                if event_type == "16" or event_type == 16:
                    period_id = event.get("periodId", "")
                    contestant_id = event.get("contestantId", "")
                    
                    # Convertir periodId a string si es número
                    if isinstance(period_id, int):
                        period_id = str(period_id)
                    
                    # Primera parte (periodId = "1" o 1)
                    if period_id == "1" or period_id == 1:
                        if contestant_id == team_contestant_id:
                            phase_stats["first_half"]["goals"] += 1
                        else:
                            phase_stats["first_half"]["goals_conceded"] += 1
                        phase_stats["first_half"]["matches"].add(match_id)
                    # Segunda parte (periodId = "2" o 2)
                    elif period_id == "2" or period_id == 2:
                        if contestant_id == team_contestant_id:
                            phase_stats["second_half"]["goals"] += 1
                        else:
                            phase_stats["second_half"]["goals_conceded"] += 1
                        phase_stats["second_half"]["matches"].add(match_id)
        
        except Exception as e:
            continue
    
    # Convertir sets a counts y calcular promedios
    first_half_match_count = len(phase_stats["first_half"]["matches"])
    second_half_match_count = len(phase_stats["second_half"]["matches"])
    
    if first_half_match_count > 0:
        phase_stats["first_half"]["avg_goals"] = phase_stats["first_half"]["goals"] / first_half_match_count
        phase_stats["first_half"]["avg_goals_conceded"] = phase_stats["first_half"]["goals_conceded"] / first_half_match_count
        phase_stats["first_half"]["matches"] = first_half_match_count
    else:
        phase_stats["first_half"]["avg_goals"] = 0
        phase_stats["first_half"]["avg_goals_conceded"] = 0
        phase_stats["first_half"]["matches"] = 0
    
    if second_half_match_count > 0:
        phase_stats["second_half"]["avg_goals"] = phase_stats["second_half"]["goals"] / second_half_match_count
        phase_stats["second_half"]["avg_goals_conceded"] = phase_stats["second_half"]["goals_conceded"] / second_half_match_count
        phase_stats["second_half"]["matches"] = second_half_match_count
    else:
        phase_stats["second_half"]["avg_goals"] = 0
        phase_stats["second_half"]["avg_goals_conceded"] = 0
        phase_stats["second_half"]["matches"] = 0
    
    return phase_stats


def create_phase_comparison_chart(opponent_phase_stats: Dict, cibao_phase_stats: Dict, opponent_name: str) -> go.Figure:
    """Crea un gráfico comparando rendimiento por fase del partido."""
    fig = go.Figure()
    
    phases = ["Primera Parte", "Segunda Parte"]
    
    # Goles a favor
    opponent_goals_for = [
        opponent_phase_stats["first_half"]["avg_goals"],
        opponent_phase_stats["second_half"]["avg_goals"]
    ]
    cibao_goals_for = [
        cibao_phase_stats["first_half"]["avg_goals"],
        cibao_phase_stats["second_half"]["avg_goals"]
    ]
    
    # Goles en contra
    opponent_goals_against = [
        opponent_phase_stats["first_half"]["avg_goals_conceded"],
        opponent_phase_stats["second_half"]["avg_goals_conceded"]
    ]
    cibao_goals_against = [
        cibao_phase_stats["first_half"]["avg_goals_conceded"],
        cibao_phase_stats["second_half"]["avg_goals_conceded"]
    ]
    
    # Use adaptive text colors
    opponent_color = '#FFFFFF'
    cibao_color = '#FF8C00'
    cibao_against_color = '#F97316'
    opponent_text_color = get_text_color(opponent_color)
    cibao_text_color = get_text_color(cibao_color)
    cibao_against_text_color = get_text_color(cibao_against_color)
    
    # Agregar barras para goles a favor
    fig.add_trace(go.Bar(
        name=f'{opponent_name} - Goles a Favor',
        x=phases,
        y=opponent_goals_for,
        marker_color=opponent_color,
        marker_line=dict(width=0),
        text=[f"{v:.2f}" for v in opponent_goals_for],
        textposition='inside',
        textfont=dict(size=14, color=opponent_text_color, family='Arial Black')
    ))
    
    fig.add_trace(go.Bar(
        name='Cibao - Goles a Favor',
        x=phases,
        y=cibao_goals_for,
        marker_color=cibao_color,
        marker_line=dict(width=0),
        text=[f"{v:.2f}" for v in cibao_goals_for],
        textposition='inside',
        textfont=dict(size=14, color=cibao_text_color, family='Arial Black')
    ))
    
    # Agregar barras para goles en contra (con patrón diferente)
    fig.add_trace(go.Bar(
        name=f'{opponent_name} - Goles en Contra',
        x=phases,
        y=[-v for v in opponent_goals_against],  # Negativo para mostrar abajo
        marker_color=opponent_color,
        marker_line=dict(width=0),
        text=[f"{v:.2f}" for v in opponent_goals_against],
        textposition='inside',
        textfont=dict(size=14, color=opponent_text_color, family='Arial Black')
    ))
    
    fig.add_trace(go.Bar(
        name='Cibao - Goles en Contra',
        x=phases,
        y=[-v for v in cibao_goals_against],  # Negativo para mostrar abajo
        marker_color=cibao_against_color,
        marker_line=dict(width=0),
        text=[f"{v:.2f}" for v in cibao_goals_against],
        textposition='inside',
        textfont=dict(size=14, color=cibao_against_text_color, family='Arial Black')
    ))
    
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=400,
        title="Goles por Fase del Partido",
        xaxis_title="Fase",
        yaxis_title="Goles Promedio",
        barmode='group',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            font=dict(size=12)
        ),
        font=dict(size=12, color='white')
    )
    
    return fig


def generate_strengths_weaknesses(opponent_metrics: Dict, cibao_metrics: Dict, opponent_name: str) -> Dict:
    """Genera análisis de fortalezas y debilidades clave."""
    result = {
        "cibao_strengths": [],
        "cibao_weaknesses": [],
        "opponent_strengths": [],
        "opponent_weaknesses": []
    }
    
    # Definir métricas y umbrales
    metrics_config = [
        ("goals", "Goles", 0.2, "superioridad ofensiva significativa", False),
        ("goalsConceded", "Goles Recibidos", 0.2, "defensa más sólida", True),
        ("possessionPercentage", "Posesión", 10, "mayor control del juego", False),
        ("passAccuracy", "Precisión de Pases", 5, "mejor calidad de pases", False),
        ("totalScoringAtt", "Disparos", 2, "mayor creación de oportunidades", False),
        ("wonCorners", "Corners", 1, "mejor en jugadas a balón parado", False),
        ("wonTackle", "Tackles Exitosos", 1, "mejor recuperación de balón", False),
        ("totalClearance", "Despejes", 2, "mejor defensa aérea", False),
    ]
    
    for metric_tuple in metrics_config:
        metric_key, metric_name, threshold, description, invert = metric_tuple
        opp_val = opponent_metrics.get(metric_key, 0)
        cibao_val = cibao_metrics.get(metric_key, 0)
        
        if invert:
            # Para métricas donde menos es mejor
            if cibao_val < opp_val * (1 - threshold):
                diff = opp_val - cibao_val
                result["cibao_strengths"].append({
                    "metric": metric_name,
                    "description": f"{description}. Cibao: {cibao_val:.2f}, {opponent_name}: {opp_val:.2f} (diferencia: {diff:.2f})"
                })
            elif opp_val < cibao_val * (1 - threshold):
                diff = cibao_val - opp_val
                result["opponent_strengths"].append({
                    "metric": metric_name,
                    "description": f"{description}. {opponent_name}: {opp_val:.2f}, Cibao: {cibao_val:.2f} (diferencia: {diff:.2f})"
                })
            elif cibao_val > opp_val * (1 + threshold):
                diff = cibao_val - opp_val
                result["cibao_weaknesses"].append({
                    "metric": metric_name,
                    "description": f"Área de mejora. Cibao: {cibao_val:.2f}, {opponent_name}: {opp_val:.2f} (diferencia: {diff:.2f})"
                })
            elif opp_val > cibao_val * (1 + threshold):
                diff = opp_val - cibao_val
                result["opponent_weaknesses"].append({
                    "metric": metric_name,
                    "description": f"Debilidad explotable. {opponent_name}: {opp_val:.2f}, Cibao: {cibao_val:.2f} (diferencia: {diff:.2f})"
                })
        else:
            # Para métricas donde más es mejor
            if cibao_val > opp_val * (1 + threshold):
                diff = cibao_val - opp_val
                if metric_key in ["possessionPercentage", "passAccuracy"]:
                    result["cibao_strengths"].append({
                        "metric": metric_name,
                        "description": f"{description}. Cibao: {cibao_val:.1f}%, {opponent_name}: {opp_val:.1f}% (diferencia: {diff:.1f}%)"
                    })
                else:
                    result["cibao_strengths"].append({
                        "metric": metric_name,
                        "description": f"{description}. Cibao: {cibao_val:.2f}, {opponent_name}: {opp_val:.2f} (diferencia: {diff:.2f})"
                    })
            elif opp_val > cibao_val * (1 + threshold):
                diff = opp_val - cibao_val
                if metric_key in ["possessionPercentage", "passAccuracy"]:
                    result["opponent_strengths"].append({
                        "metric": metric_name,
                        "description": f"{description}. {opponent_name}: {opp_val:.1f}%, Cibao: {cibao_val:.1f}% (diferencia: {diff:.1f}%)"
                    })
                else:
                    result["opponent_strengths"].append({
                        "metric": metric_name,
                        "description": f"{description}. {opponent_name}: {opp_val:.2f}, Cibao: {cibao_val:.2f} (diferencia: {diff:.2f})"
                    })
            elif cibao_val < opp_val * (1 - threshold):
                diff = opp_val - cibao_val
                if metric_key in ["possessionPercentage", "passAccuracy"]:
                    result["cibao_weaknesses"].append({
                        "metric": metric_name,
                        "description": f"Área de mejora. Cibao: {cibao_val:.1f}%, {opponent_name}: {opp_val:.1f}% (diferencia: {diff:.1f}%)"
                    })
                else:
                    result["cibao_weaknesses"].append({
                        "metric": metric_name,
                        "description": f"Área de mejora. Cibao: {cibao_val:.2f}, {opponent_name}: {opp_val:.2f} (diferencia: {diff:.2f})"
                    })
            elif opp_val < cibao_val * (1 - threshold):
                diff = cibao_val - opp_val
                if metric_key in ["possessionPercentage", "passAccuracy"]:
                    result["opponent_weaknesses"].append({
                        "metric": metric_name,
                        "description": f"Debilidad explotable. {opponent_name}: {opp_val:.1f}%, Cibao: {cibao_val:.1f}% (diferencia: {diff:.1f}%)"
                    })
                else:
                    result["opponent_weaknesses"].append({
                        "metric": metric_name,
                        "description": f"Debilidad explotable. {opponent_name}: {opp_val:.2f}, Cibao: {cibao_val:.2f} (diferencia: {diff:.2f})"
                    })
    
    # Limitar a top 4 para cada categoría
    result["cibao_strengths"] = result["cibao_strengths"][:4]
    result["cibao_weaknesses"] = result["cibao_weaknesses"][:4]
    result["opponent_strengths"] = result["opponent_strengths"][:4]
    result["opponent_weaknesses"] = result["opponent_weaknesses"][:4]
    
    return result


def display_key_players_analysis(player_stats: Dict, team_name: str):
    """Muestra análisis de jugadores clave."""
    if not player_stats:
        st.info("No hay datos de jugadores disponibles para este equipo.")
        return
    
    # Convertir a lista y ordenar
    players_list = list(player_stats.values())
    
    # Search and filter functionality
    st.markdown("""
    <h3 style='color:#ff8c00; margin-top:20px;'>Buscar y Filtrar</h3>
    """, unsafe_allow_html=True)
    
    # Player dropdown
    player_names = sorted([p["name"] for p in players_list if p.get("name")])
    selected_player_dropdown = st.selectbox(
        "Seleccionar jugador:",
        options=["Todos los jugadores"] + player_names,
        key="player_dropdown",
        help="Selecciona un jugador para resaltar sus estadísticas"
    )
    
    # Text search (alternative to dropdown)
    search_query = st.text_input(
        "Buscar jugador por nombre:",
        key="player_search",
        placeholder="Escribe el nombre del jugador...",
        help="Busca un jugador para resaltar sus estadísticas en todas las tablas"
    )
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Determine which player to highlight
    search_query_normalized = ""
    if selected_player_dropdown and selected_player_dropdown != "Todos los jugadores":
        search_query_normalized = selected_player_dropdown.lower().strip()
    elif search_query:
        search_query_normalized = search_query.strip().lower()
    
    # Inject CSS once at the beginning (always, for consistent table styling)
    st.markdown("""
    <style>
    .player-table {
        width: 100%;
        border-collapse: collapse;
        background-color: #1e1e1e;
        color: white;
        margin: 10px 0;
        font-size: 1.4rem !important;
    }
    .player-table th {
        background-color: #2d2d2d;
        color: #FF9900;
        padding: 10px;
        text-align: left;
        border: 1px solid #444;
        font-size: 1.5rem !important;
        font-weight: bold !important;
    }
    .player-table td {
        padding: 8px;
        border: 1px solid #444;
        font-size: 1.4rem !important;
    }
    .player-table tr:hover {
        background-color: #333;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Helper function to highlight rows in DataFrame and return HTML
    def highlight_player_row(df, search_term):
        """Highlights rows where the player name matches the search term and returns HTML."""
        if not search_term or df.empty:
            return None
        
        def style_row(row):
            player_name = str(row.get("Jugador", "")).lower().strip()
            search_term_lower = search_term.lower().strip()
            # Try exact match first, then substring match
            if player_name == search_term_lower:
                return ['background-color: #FF9900; color: #000000; font-weight: bold;'] * len(row)
            elif search_term_lower in player_name:
                return ['background-color: #FF9900; color: #000000; font-weight: bold;'] * len(row)
            return [''] * len(row)
        
        styled_df = df.style.apply(style_row, axis=1)
        # Convert to HTML and add class for styling
        html = styled_df.to_html(escape=False, index=False, classes='player-table')
        return html
    
    # Use all players (no metric filtering)
    filtered_players = players_list
    
    # ========== OFFENSIVE METRICS ==========
    st.markdown("""
    <h2 style='color:#ff8c00; margin-top:30px; text-align:center;'>Métricas Ofensivas</h2>
    """, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Table 1: Goals & Shots
    st.markdown("""
    <h3 style='color:#ff8c00; margin-top:20px;'>Goles y Disparos</h3>
    """, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Prepare goals and shots data
    goals_shots_data = []
    for player in filtered_players:
        minutes = player.get("total_minutes", 0)
        if minutes > 0:
            goals = player.get("goals", 0)
            goals_per_90 = (goals / minutes * 90) if minutes > 0 else 0
            total_shots = player.get("total_shots", 0)
            shots_on_target = player.get("shots_on_target", 0)
            shots_per_90 = (total_shots / minutes * 90) if minutes > 0 else 0
            shots_on_target_per_90 = (shots_on_target / minutes * 90) if minutes > 0 else 0
            shot_accuracy = (shots_on_target / total_shots * 100) if total_shots > 0 else 0
            
            goals_shots_data.append({
                "Jugador": player["name"],
                "Equipo": team_name,
                "Posición": translate_position(player.get("position", "Unknown")),
                "Goles": goals,
                "Goles/90": f"{goals_per_90:.2f}",
                "Disparos": total_shots,
                "Disparos/90": f"{shots_per_90:.2f}",
                "Disparos al Arco": shots_on_target,
                "Disparos al Arco/90": f"{shots_on_target_per_90:.2f}",
                "Precisión %": f"{shot_accuracy:.1f}%",
                "Partidos": player.get("matches_played", 0),
                "Minutos": minutes
            })
    
    # Sort by goals descending
    goals_shots_data = sorted(goals_shots_data, key=lambda x: x["Goles"], reverse=True)
    
    if goals_shots_data:
        df_goals_shots = pd.DataFrame(goals_shots_data)
        if search_query_normalized:
            styled_html = highlight_player_row(df_goals_shots, search_query_normalized)
            if styled_html:
                st.markdown(styled_html, unsafe_allow_html=True)
            else:
                st.dataframe(df_goals_shots, use_container_width=True, hide_index=True)
        else:
            st.dataframe(df_goals_shots, use_container_width=True, hide_index=True)
    else:
        st.info("No hay datos de goles y disparos disponibles.")
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("---")
    
    # Table 2: Assists & Passing
    st.markdown("""
    <h3 style='color:#ff8c00; margin-top:20px;'>Asistencias y Pases</h3>
    """, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Prepare assists and passing data
    assists_passing_data = []
    for player in filtered_players:
        minutes = player.get("total_minutes", 0)
        if minutes > 0:
            assists = player.get("assists", 0)
            assists_per_90 = (assists / minutes * 90) if minutes > 0 else 0
            total_passes = player.get("total_passes", 0)
            accurate_passes = player.get("accurate_passes", 0)
            passes_per_90 = (total_passes / minutes * 90) if minutes > 0 else 0
            accurate_passes_per_90 = (accurate_passes / minutes * 90) if minutes > 0 else 0
            pass_accuracy = (accurate_passes / total_passes * 100) if total_passes > 0 else 0
            
            assists_passing_data.append({
                "Jugador": player["name"],
                "Equipo": team_name,
                "Posición": translate_position(player.get("position", "Unknown")),
                "Asistencias": assists,
                "Asistencias/90": f"{assists_per_90:.2f}",
                "Pases": total_passes,
                "Pases/90": f"{passes_per_90:.2f}",
                "Pases Precisos": accurate_passes,
                "Pases Precisos/90": f"{accurate_passes_per_90:.2f}",
                "Precisión %": f"{pass_accuracy:.1f}%",
                "Partidos": player.get("matches_played", 0),
                "Minutos": minutes
            })
    
    # Sort by assists descending
    assists_passing_data = sorted(assists_passing_data, key=lambda x: x["Asistencias"], reverse=True)
    
    if assists_passing_data:
        df_assists_passing = pd.DataFrame(assists_passing_data)
        if search_query_normalized:
            styled_html = highlight_player_row(df_assists_passing, search_query_normalized)
            if styled_html:
                st.markdown(styled_html, unsafe_allow_html=True)
            else:
                st.dataframe(df_assists_passing, use_container_width=True, hide_index=True)
        else:
            st.dataframe(df_assists_passing, use_container_width=True, hide_index=True)
    else:
        st.info("No hay datos de asistencias y pases disponibles.")
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("---")
    
    # ========== DEFENSIVE METRICS ==========
    st.markdown("""
    <h2 style='color:#ff8c00; margin-top:30px; text-align:center;'>Métricas Defensivas</h2>
    """, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Table 3: Tackles & Interceptions
    st.markdown("""
    <h3 style='color:#ff8c00; margin-top:20px;'>Tackles e Intercepciones</h3>
    """, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Prepare tackles and interceptions data
    tackles_interceptions_data = []
    for player in filtered_players:
        minutes = player.get("total_minutes", 0)
        if minutes > 0:
            total_tackles = player.get("total_tackles", 0)
            won_tackles = player.get("won_tackles", 0)
            tackles_per_90 = (total_tackles / minutes * 90) if minutes > 0 else 0
            won_tackles_per_90 = (won_tackles / minutes * 90) if minutes > 0 else 0
            tackle_success = (won_tackles / total_tackles * 100) if total_tackles > 0 else 0
            interceptions = player.get("interceptions", 0)
            interceptions_per_90 = (interceptions / minutes * 90) if minutes > 0 else 0
            
            tackles_interceptions_data.append({
                "Jugador": player["name"],
                "Equipo": team_name,
                "Posición": translate_position(player.get("position", "Unknown")),
                "Tackles": total_tackles,
                "Tackles/90": f"{tackles_per_90:.2f}",
                "Tackles Exitosos": won_tackles,
                "Tackles Exitosos/90": f"{won_tackles_per_90:.2f}",
                "Efectividad %": f"{tackle_success:.1f}%",
                "Intercepciones": interceptions,
                "Intercepciones/90": f"{interceptions_per_90:.2f}",
                "Partidos": player.get("matches_played", 0),
                "Minutos": minutes
            })
    
    # Sort by total tackles descending
    tackles_interceptions_data = sorted(tackles_interceptions_data, key=lambda x: x["Tackles"], reverse=True)
    
    if tackles_interceptions_data:
        df_tackles_interceptions = pd.DataFrame(tackles_interceptions_data)
        if search_query_normalized:
            styled_html = highlight_player_row(df_tackles_interceptions, search_query_normalized)
            if styled_html:
                st.markdown(styled_html, unsafe_allow_html=True)
            else:
                st.dataframe(df_tackles_interceptions, use_container_width=True, hide_index=True)
        else:
            st.dataframe(df_tackles_interceptions, use_container_width=True, hide_index=True)
    else:
        st.info("No hay datos de tackles e intercepciones disponibles.")
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("---")
    
    # Table 4: Clearances & Saves
    st.markdown("""
    <h3 style='color:#ff8c00; margin-top:20px;'>Despejes y Atajadas</h3>
    """, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Prepare clearances and saves data
    clearances_saves_data = []
    for player in filtered_players:
        minutes = player.get("total_minutes", 0)
        if minutes > 0:
            clearances = player.get("clearances", 0)
            clearances_per_90 = (clearances / minutes * 90) if minutes > 0 else 0
            saves = player.get("saves", 0)
            saves_per_90 = (saves / minutes * 90) if minutes > 0 else 0
            
            clearances_saves_data.append({
                "Jugador": player["name"],
                "Equipo": team_name,
                "Posición": translate_position(player.get("position", "Unknown")),
                "Despejes": clearances,
                "Despejes/90": f"{clearances_per_90:.2f}",
                "Atajadas": saves,
                "Atajadas/90": f"{saves_per_90:.2f}",
                "Partidos": player.get("matches_played", 0),
                "Minutos": minutes
            })
    
    # Sort by clearances descending
    clearances_saves_data = sorted(clearances_saves_data, key=lambda x: x["Despejes"], reverse=True)
    
    if clearances_saves_data:
        df_clearances_saves = pd.DataFrame(clearances_saves_data)
        if search_query_normalized:
            styled_html = highlight_player_row(df_clearances_saves, search_query_normalized)
            if styled_html:
                st.markdown(styled_html, unsafe_allow_html=True)
            else:
                st.dataframe(df_clearances_saves, use_container_width=True, hide_index=True)
        else:
            st.dataframe(df_clearances_saves, use_container_width=True, hide_index=True)
    else:
        st.info("No hay datos de despejes y atajadas disponibles.")


def display_formation_analysis(formation_stats: Dict, team_name: str):
    """Muestra el análisis de formaciones."""
    if not formation_stats:
        st.info("No hay datos de formaciones disponibles para este equipo.")
        return
    
    # Ordenar por frecuencia
    sorted_formations = sorted(
        formation_stats.items(),
        key=lambda x: x[1]["count"],
        reverse=True
    )
    
    st.markdown("""
    <h3 style='color:#ff8c00; margin-top:20px;'>Formaciones Más Utilizadas</h3>
    """, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Crear DataFrame para mostrar
    formation_data = []
    for formation, stats in sorted_formations:
        formation_data.append({
            "Formación": formation,
            "Partidos": stats["count"],
            "Victorias": stats["wins"],
            "Empates": stats["draws"],
            "Derrotas": stats["losses"],
            "% Victorias": f"{stats['win_rate']:.1f}%",
            "Goles a Favor": f"{stats['avg_goals_for']:.2f}",
            "Goles en Contra": f"{stats['avg_goals_against']:.2f}",
            "Diferencia": f"{stats['avg_goal_difference']:+.2f}"
        })
    
    df_formations = pd.DataFrame(formation_data)
    st.dataframe(df_formations, use_container_width=True, hide_index=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Gráfico de barras: frecuencia de formaciones
    if len(sorted_formations) > 0:
        formations = [f[0] for f in sorted_formations]
        counts = [f[1]["count"] for f in sorted_formations]
        win_rates = [f[1]["win_rate"] for f in sorted_formations]
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            name="Partidos",
            x=formations,
            y=counts,
            marker_color='#EF4444',
            text=counts,
            textposition='outside',
            yaxis='y'
        ))
        
        fig.add_trace(go.Scatter(
            name="% Victorias",
            x=formations,
            y=win_rates,
            mode='lines+markers',
            line=dict(color='#10B981', width=3),
            marker=dict(size=10, color='#10B981'),
            yaxis='y2',
            text=[f"{wr:.1f}%" for wr in win_rates],
            textposition='top center'
        ))
        
        fig.update_layout(
            template='plotly_dark',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            height=500,
            xaxis_title="Formación",
            yaxis=dict(title="Partidos", side='left'),
            yaxis2=dict(title="% Victorias", side='right', overlaying='y', range=[0, 100]),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="center",
                x=0.5
            ),
            title=dict(
                text="Frecuencia y Efectividad de Formaciones",
                font=dict(size=16, color='#FFFFFF'),
                x=0.5
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Mostrar detalles de la formación más usada
        if sorted_formations:
            most_used = sorted_formations[0]
            st.markdown(f"""
            <h3 style='color:#ff8c00; margin-top:20px;'>Formación Principal: <strong>{most_used[0]}</strong></h3>
            """, unsafe_allow_html=True)
            st.markdown(f"**Utilizada en {most_used[1]['count']} partidos** ({most_used[1]['count']/sum(s['count'] for _, s in sorted_formations)*100:.1f}% del total)")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Victorias", most_used[1]["wins"], delta=f"{most_used[1]['win_rate']:.1f}%")
            with col2:
                st.metric("Goles a Favor", f"{most_used[1]['avg_goals_for']:.2f}", delta="Por partido")
            with col3:
                st.metric("Diferencia de Goles", f"{most_used[1]['avg_goal_difference']:+.2f}", delta="Por partido")


def display_comparison_charts(opponent_metrics: Dict[str, float], cibao_metrics: Dict[str, float], opponent_name: str):
    """Muestra gráficos de comparación lado a lado."""
    
    # Métricas para comparar
    comparison_metrics = [
        ("Goles", "goals", "", "Por partido"),
        ("Goles Recibidos", "goalsConceded", "", "Por partido"),
        ("Disparos", "totalScoringAtt", "", "Por partido"),
        ("Posesión", "possessionPercentage", "", "%"),
        ("Precisión Pases", "passAccuracy", "", "%"),
        ("Corners Ganados", "wonCorners", "", "Por partido"),
    ]
    
    # Crear gráfico de barras comparativo
    categories = [m[0] for m in comparison_metrics]
    opponent_vals = [opponent_metrics.get(m[1], 0) for m in comparison_metrics]
    cibao_vals = [cibao_metrics.get(m[1], 0) for m in comparison_metrics]
    
    fig = go.Figure()
    
    # Use adaptive text colors
    opponent_color = '#FFFFFF'
    cibao_color = '#FF8C00'
    opponent_text_color = get_text_color(opponent_color)
    cibao_text_color = get_text_color(cibao_color)
    
    fig.add_trace(go.Bar(
        name=opponent_name,
        x=categories,
        y=opponent_vals,
        marker_color=opponent_color,
        marker_line=dict(width=0),
        text=[f"{v:.2f}" for v in opponent_vals],
        textposition='inside',
        textfont=dict(size=14, color=opponent_text_color, family='Arial Black')
    ))
    
    fig.add_trace(go.Bar(
        name='Cibao',
        x=categories,
        y=cibao_vals,
        marker_color=cibao_color,
        marker_line=dict(width=0),
        text=[f"{v:.2f}" for v in cibao_vals],
        textposition='inside',
        textfont=dict(size=14, color=cibao_text_color, family='Arial Black')
    ))
    
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=500,
        margin=dict(t=80, b=100, l=50, r=50),  # Increased bottom margin for horizontal labels on mobile
        xaxis_title="Métricas",
        yaxis_title="Valor",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5
        ),
        barmode='group',
        xaxis=dict(tickangle=0, tickfont=dict(size=12))  # Horizontal labels for better mobile experience
    )
    
    st.plotly_chart(fig, use_container_width=True)


# ===========================================
# INTERFAZ PRINCIPAL
# ===========================================

def main():
    # Título - standardized to match other pages
    titulo_naranja("Análisis del Rival — Liga Mayor")
    st.markdown("""
    <p style='text-align:center; color:#D1D5DB; font-size:17px;'>
        Análisis detallado de oponentes para preparación táctica y estratégica
    </p>
    """, unsafe_allow_html=True)
    
    # Botón de actualización de datos
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button(" Actualizar Datos", type="primary", use_container_width=True, 
                     help="Actualiza los datos desde los archivos Wyscout más recientes"):
            # Limpiar cache y recargar
            load_liga_data.clear()
            load_cibao_team_data.clear()
            st.rerun()
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Cargar datos
    with st.spinner("Cargando datos de Liga Mayor..."):
        # Get cache key to ensure cache invalidates when files change
        try:
            from src.data_processing.loaders import get_data_cache_key
            cache_key = get_data_cache_key()
        except ImportError:
            cache_key = None
        df_liga = load_liga_data(_cache_key=cache_key)
        
        # Try to load Cibao data, but handle if sheet doesn't exist
        try:
            df_cibao, df_rivales = load_cibao_team_data()
        except (RuntimeError, FileNotFoundError, KeyError) as e:
            # If Cibao sheet doesn't exist, extract from df_liga instead
            if not df_liga.empty and "Team" in df_liga.columns:
                df_cibao = df_liga[df_liga["Team"].str.lower() == "cibao"].copy()
                df_rivales = df_liga[df_liga["Team"].str.lower() != "cibao"].copy()
            else:
                df_cibao = pd.DataFrame()
                df_rivales = pd.DataFrame()
        
        cibao_matches = get_cibao_matches_liga(df_liga)
    
    if df_liga.empty:
        st.error("No se encontraron datos de Liga Mayor. Verifique que los archivos estén en la carpeta correcta.")
        return
    
    # Obtener todos los equipos de los datos
    all_teams_list = get_all_teams_from_liga_data(df_liga)
    
    # Obtener oponentes de Cibao para marcar próximos
    # For Liga data, we may not have upcoming matches in the same format
    # So we'll just get an empty list if there are no upcoming matches
    try:
        upcoming_opponents = get_upcoming_opponents(cibao_matches)
        upcoming_opponent_names = {name for name, _ in upcoming_opponents} if upcoming_opponents else set()
    except Exception as e:
        # If there's an error, just continue without upcoming opponents
        upcoming_opponents = []
        upcoming_opponent_names = set()
    
    # Selector de equipo en la parte superior (visible)
    st.markdown("""
    <h2 style='color:#FF9900; text-align:center; margin-top:20px;'>Seleccionar Equipo para Analizar</h2>
    """, unsafe_allow_html=True)
    
    # Preparar opciones
    if upcoming_opponents:
        opponent_options = []
        opponent_map = {}
        
        for name, match_info in upcoming_opponents:
            display_name = name
            opponent_options.append(display_name)
            opponent_map[display_name] = name
        
        for name in all_teams_list:
            if name not in upcoming_opponent_names and name != CIBAO_TEAM_NAME:
                opponent_options.append(name)
                opponent_map[name] = name
        
        if CIBAO_TEAM_NAME not in [opponent_map.get(opt, opt) for opt in opponent_options]:
            opponent_options.append(CIBAO_TEAM_NAME)
            opponent_map[CIBAO_TEAM_NAME] = CIBAO_TEAM_NAME
        
        # Sort options alphabetically
        opponent_options = sorted(opponent_options, key=lambda x: x.lower())
        
        default_index = 0
        for i, opt in enumerate(opponent_options):
            mapped_name = opponent_map.get(opt, opt)
            if "Defence Force" in opt or mapped_name == "Defence Force":
                default_index = i
                break
        
        if "opponent_selector_index" not in st.session_state:
            st.session_state.opponent_selector_index = default_index
        
        selected_display = st.selectbox(
            "Seleccionar Equipo",
            options=opponent_options,
            index=st.session_state.opponent_selector_index,
            key="opponent_selector_main",
            help="Selecciona el equipo que deseas analizar",
            label_visibility="visible"
        )
        
        current_index = opponent_options.index(selected_display)
        st.session_state.opponent_selector_index = current_index
        selected_opponent = opponent_map[selected_display]
    else:
        # Sort teams alphabetically
        sorted_teams_list = sorted(all_teams_list, key=lambda x: x.lower())
        
        default_index = 0
        for i, team in enumerate(sorted_teams_list):
            if team == "Defence Force":
                default_index = i
                break
        
        if "opponent_selector_index" not in st.session_state:
            st.session_state.opponent_selector_index = default_index
        
        selected_opponent = st.selectbox(
            "Seleccionar Equipo",
            options=sorted_teams_list,
            index=st.session_state.opponent_selector_index,
            key="opponent_selector_main",
            help="Selecciona el equipo que deseas analizar",
            label_visibility="visible"
        )
        
        current_index = all_teams_list.index(selected_opponent)
        st.session_state.opponent_selector_index = current_index
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Sidebar: Información adicional
    with st.sidebar:
        st.markdown("""
        <h3 style='margin-top:0; color:#ff7b00;'>Análisis Liga</h3>
        <hr style='margin-top:6px; margin-bottom:20px; opacity:0.3;'>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        st.info(f"**Equipo seleccionado:**\n\n**{selected_opponent}**")
        
        st.markdown("---")
        
        # Información sobre actualización de datos
        with st.expander("ℹ Actualización de Datos", expanded=False):
            st.markdown("""
            **¿Cómo se actualizan los datos?**
            
            • Los datos se actualizan **automáticamente cada 5 minutos**
            
            • O haz clic en **" Actualizar Datos"** arriba para actualizar inmediatamente
            
            • Después de ejecutar el script de scraping, espera 5 minutos o usa el botón de actualización
            """)
        
        st.markdown("---")
        
        # Próximos partidos
        st.subheader(" Próximos Partidos")
        
        # Obtener próximos partidos desde Scoresway
        with st.spinner("Obteniendo próximos partidos..."):
            next_fixtures = get_next_fixtures()
        
        if next_fixtures.get("liga_mayor"):
            liga_fixture = next_fixtures["liga_mayor"]
            st.markdown("**Liga Mayor:**")
            if liga_fixture.get("date"):
                st.info(f" {liga_fixture.get('date', 'Por definir')}")
            if liga_fixture.get("opponent") and liga_fixture["opponent"] != "Por definir":
                st.info(f" vs {liga_fixture.get('opponent', 'Por definir')}")
        else:
            st.info("**Liga Mayor:**\n\nSin próximos partidos disponibles")
        
        st.markdown("---")
        
        # Información del equipo seleccionado
        st.subheader("Información")
        
        # Encontrar partidos con este equipo desde DataFrame
        if selected_opponent == CIBAO_TEAM_NAME:
            team_df_info = cibao_matches
            is_cibao = True
        else:
            # Buscar partidos del equipo seleccionado (use flexible matching)
            # Try exact match first
            team_df_info = df_liga[df_liga["Team"].str.lower() == selected_opponent.lower()].copy()
            
            # If no exact match, try flexible matching (substring match)
            if team_df_info.empty and not df_liga.empty:
                selected_opponent_normalized = selected_opponent.lower().strip().replace(' fc', '').replace(' fc', '').strip()
                
                def team_name_match(team_name):
                    if pd.isna(team_name):
                        return False
                    team_name_normalized = str(team_name).lower().strip().replace(' fc', '').replace(' fc', '').strip()
                    # Check if selected opponent name is in team name or vice versa
                    return (selected_opponent_normalized in team_name_normalized or 
                           team_name_normalized in selected_opponent_normalized or
                           selected_opponent_normalized.replace(' del ', ' de ') in team_name_normalized.replace(' del ', ' de ') or
                           team_name_normalized.replace(' del ', ' de ') in selected_opponent_normalized.replace(' del ', ' de '))
                
                team_df_info = df_liga[df_liga["Team"].apply(team_name_match)].copy()
            is_cibao = False
        
        if not team_df_info.empty:
            # Ordenar por fecha si existe columna Date
            if "Date" in team_df_info.columns:
                team_df_info = team_df_info.sort_values("Date", na_position='last')
                last_match_date = team_df_info["Date"].iloc[-1] if len(team_df_info) > 0 else None
                if last_match_date and pd.notna(last_match_date):
                    if isinstance(last_match_date, pd.Timestamp):
                        st.info(f"**Último encuentro:**\n{last_match_date.strftime('%Y-%m-%d')}")
                    else:
                        st.info(f"**Último encuentro:**\n{str(last_match_date)}")
            
            # Contar partidos
            total_matches = len(team_df_info)
            if is_cibao:
                st.info(f"**Partidos totales:** {total_matches}")
            else:
                # Contar partidos vs Cibao (si hay columna Match que indique oponente)
                st.info(f"**Partidos en datos:** {total_matches}")
    
    # Contenido principal
    st.markdown("---")
    
    # Mostrar información del equipo seleccionado
    # ---------- PAGE TITLE ----------
    titulo_naranja(f"Análisis del Rival — {selected_opponent}")
    
    st.markdown("""
    <p style='text-align:center; color:#D1D5DB; font-size:17px;'>
    Análisis completo del <b>rendimiento</b>, <b>tendencias</b> y <b>características tácticas</b> del equipo seleccionado.<br>
    Diseñado para soporte táctico del staff técnico — decisiones claras, con contexto.
    </p>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Obtener todos los partidos del equipo seleccionado y métricas
    with st.spinner(f"Calculando métricas de {selected_opponent} y Cibao..."):
        # Calcular promedios desde DataFrame
        try:
            team_averages = calculate_team_averages_from_df(df_liga, selected_opponent)
            cibao_averages = calculate_team_averages_from_df(df_liga, CIBAO_TEAM_NAME)
            
            # Debug: mostrar información si no se encontraron métricas
            if not team_averages and not df_liga.empty:
                # Verificar qué equipos están disponibles
                available_teams = df_liga["Team"].unique().tolist() if "Team" in df_liga.columns else []
                if available_teams:
                    st.warning(f" No se encontraron datos para '{selected_opponent}'. Equipos disponibles: {', '.join(sorted(available_teams)[:10])}")
        except Exception as e:
            st.error(f"Error calculando métricas: {str(e)}")
            team_averages = {}
            cibao_averages = {}
        
        # Calcular promedios de competencia (todos los equipos)
        # Usar la misma función de mapeo que calculate_team_averages_from_df
        competition_averages = {}
        if not df_liga.empty:
            # Seleccionar columnas numéricas (igual que en calculate_team_averages_from_df)
            numeric_cols = df_liga.select_dtypes(include=[np.number]).columns.tolist()
            
            # También incluir columnas con % en el nombre que son numéricas
            pct_cols = [col for col in df_liga.columns if '%' in str(col) and col not in numeric_cols]
            for col in pct_cols:
                if pd.api.types.is_numeric_dtype(df_liga[col]):
                    if col not in numeric_cols:
                        numeric_cols.append(col)
                else:
                    try:
                        pd.to_numeric(df_liga[col], errors='raise')
                        if col not in numeric_cols:
                            numeric_cols.append(col)
                    except (ValueError, TypeError):
                        pass
            
            # Usar el mismo mapeo completo
            column_mapping = get_wyscout_to_scoresway_mapping()
            
            for col in numeric_cols:
                if col not in ["Match", "Date", "Team"]:
                    avg_value = df_liga[col].mean()
                    if pd.notna(avg_value):
                        # Usar nombre mapeado si existe
                        metric_key = column_mapping.get(col)
                        if metric_key:
                            competition_averages[metric_key] = float(avg_value)
                        # También mantener el nombre original
                        competition_averages[col] = float(avg_value)
                        # Y nombre normalizado (convertir % a _pct, igual que en team averages)
                        normalized_name = col.lower().replace(" ", "_").replace("/", "_").replace(",", "").replace("(", "").replace(")", "").replace("%", "_pct")
                        competition_averages[normalized_name] = float(avg_value)
            
            # Calcular métricas derivadas para competencia también
            if "corners_with_shots" in competition_averages:
                competition_averages["wonCorners"] = competition_averages.get("corners_with_shots", 0)
            
            # NOTA: No usamos fallback para duelos específicos (igual que en team averages)
            # para evitar mostrar valores idénticos engañosos
    
    # Preparar datos del equipo seleccionado
    # Use flexible matching to handle name variations (e.g., "Delfines De Este" vs "Delfines Del Este")
    # Also handle cleaned names (without "(1)" suffixes) matching against original data
    # Normalize accents for consistent matching (data is normalized during upload)
    if not df_liga.empty:
        # Normalize accents in selected opponent name (data is already normalized during upload)
        selected_opponent_no_accents = remove_accents(selected_opponent)
        selected_opponent_normalized = selected_opponent_no_accents.lower().strip().replace(' fc', '').replace(' fc', '').strip()
        
        # Clean the selected opponent name (remove "(1)" suffixes) for matching
        selected_opponent_cleaned = re.sub(r'\s*\(\d+\)\s*$', '', selected_opponent_normalized)
        
        # Define flexible matching function to get ALL variations (exact + cleaned)
        def team_name_match(team_name):
            if pd.isna(team_name):
                return False
            team_name_str = str(team_name).lower().strip()
            # Normalize accents (data should already be normalized, but do it here too for safety)
            team_name_no_accents = remove_accents(team_name_str)
            team_name_normalized = team_name_no_accents.replace(' fc', '').replace(' fc', '').strip()
            # Clean the team name from data (remove "(1)" suffixes)
            team_name_cleaned = re.sub(r'\s*\(\d+\)\s*$', '', team_name_normalized)
            
            # Check exact match first (with accent normalization)
            if team_name_no_accents == selected_opponent_no_accents.lower():
                return True
            
            # Check if cleaned names match (handles "(1)" variations)
            if selected_opponent_cleaned == team_name_cleaned:
                return True
            
            # Also check if selected opponent name is in team name or vice versa
            return (selected_opponent_normalized in team_name_normalized or 
                   team_name_normalized in selected_opponent_normalized or
                   selected_opponent_normalized.replace(' del ', ' de ') in team_name_normalized.replace(' del ', ' de ') or
                   team_name_normalized.replace(' del ', ' de ') in selected_opponent_normalized.replace(' del ', ' de '))
        
        # Use flexible matching to get ALL rows (including variations like "Salcedo" and "Salcedo (1)")
        team_df = df_liga[df_liga["Team"].apply(team_name_match)].copy()
    else:
        team_df = pd.DataFrame()
    
    cibao_df = df_liga[df_liga["Team"].str.lower() == CIBAO_TEAM_NAME.lower()].copy() if not df_liga.empty else pd.DataFrame()
    
    # Convert team_df to list of dicts for compatibility with existing functions
    # For Wyscout data, all rows are "played" matches (they're statistics, not fixtures)
    # IMPORTANT: Remove duplicates by Match+Date to avoid double counting
    team_all_matches = []
    seen_match_date = set()  # Track unique Match+Date combinations
    
    if not team_df.empty:
        # First, filter out rows with invalid Match or Date values (NaN, empty, or invalid formats)
        if "Match" in team_df.columns and "Date" in team_df.columns:
            # Remove rows where Match is NaN or doesn't contain " - " (invalid match format)
            valid_match_mask = (
                team_df["Match"].notna() & 
                (team_df["Match"].astype(str).str.contains(" - ", na=False))
            )
            # Remove rows where Date is NaN or not a valid date
            valid_date_mask = team_df["Date"].notna()
            # Combine both conditions
            team_df = team_df[valid_match_mask & valid_date_mask].copy()
        
        # Then, remove duplicates from DataFrame itself (in case there are duplicate rows)
        # Use a more robust deduplication: Match+Date+Team to ensure we don't remove valid matches
        if "Match" in team_df.columns and "Date" in team_df.columns and "Team" in team_df.columns:
            # Drop duplicates based on Match+Date+Team, keeping first occurrence
            team_df = team_df.drop_duplicates(subset=["Match", "Date", "Team"], keep="first").copy()
        elif "Match" in team_df.columns and "Date" in team_df.columns:
            # Fallback to Match+Date if Team column not available
            team_df = team_df.drop_duplicates(subset=["Match", "Date"], keep="first").copy()
        
        for idx, row in team_df.iterrows():
            match_dict = row.to_dict()
            
            # Create unique identifier for this match
            # Use Match+Date+Team to be more precise (avoid removing valid matches with same Match string)
            match_str = str(match_dict.get("Match", "")).strip()
            team_name_in_match = str(match_dict.get("Team", "")).strip()
            date_val = match_dict.get("Date")
            if pd.notna(date_val):
                if isinstance(date_val, pd.Timestamp):
                    date_str = date_val.strftime("%Y-%m-%d")
                else:
                    date_str = str(date_val).strip()
            else:
                date_str = ""
            
            # Use Team+Date+Match+Index for more precise deduplication
            # Include index as fallback to ensure we don't accidentally remove valid matches
            # This ensures we don't accidentally remove matches that have the same Match string
            # but are actually different matches (e.g., if Match column has formatting issues)
            # Only use index if Match or Date is missing to avoid over-deduplication
            if not match_str or not date_str:
                # If Match or Date is missing, use index to ensure uniqueness
                match_date_key = f"{team_name_in_match}_{date_str}_{match_str}_{idx}"
            else:
                # If both Match and Date exist, use them (more reliable)
                match_date_key = f"{team_name_in_match}_{date_str}_{match_str}"
            
            # Skip if we've already processed this exact combination
            if match_date_key in seen_match_date:
                continue
            seen_match_date.add(match_date_key)
            
            # Add status field to indicate it's a played match (Wyscout data = played matches)
            match_dict["status"] = "played"
            # Add date field if Date column exists
            if "Date" in match_dict and pd.notna(match_dict["Date"]):
                if isinstance(match_dict["Date"], pd.Timestamp):
                    match_dict["date"] = match_dict["Date"].strftime("%Y-%m-%d")
                else:
                    match_dict["date"] = str(match_dict["Date"])
            
            # ALWAYS derive is_home from Match string (ignore any stored values - they may be wrong floats)
            # Home team is ALWAYS first in "Home Team - Away Team" format
            # This matches how Moca works (Moca has no is_home column, so it always derives)
            team_name = str(match_dict.get("Team", "")).strip()
            # Clean team name (remove (1), (2) suffixes) for better matching
            team_name_cleaned = re.sub(r'\s*\(\d+\)\s*$', '', team_name).strip()
            
            is_home = False  # Default to False
            if match_str and team_name_cleaned and " - " in match_str:
                # Extract teams from match string (format: "Home Team - Away Team score:score")
                # The first team is ALWAYS home, second is ALWAYS away
                parts = match_str.split(" - ")
                if len(parts) >= 2:
                    home_team = parts[0].strip()
                    # Remove score if present (format: "Team 2:1")
                    home_team = re.sub(r'\s+\d+:\d+$', '', home_team).strip()
                    
                    # Normalize both for comparison
                    team_name_lower = team_name_cleaned.lower().strip()
                    home_team_lower = home_team.lower().strip()
                    
                    # Remove " FC" suffixes and clean both sides
                    team_clean = team_name_lower.replace(' fc', '').strip()
                    home_clean = home_team_lower.replace(' fc', '').strip()
                    
                    # Check if team name matches home team (with flexible matching)
                    # If team name matches the first part (home team), it's a home game
                    is_home = (team_name_lower in home_team_lower or 
                              home_team_lower in team_name_lower or
                              team_clean in home_clean or
                              home_clean in team_clean)
            
            # ALWAYS store as boolean (not float) - overwrite any existing value
            match_dict["is_home"] = bool(is_home)
            
            # Also add is_home to the DataFrame row for filtering
            # We'll update the DataFrame after processing all rows
            
            team_all_matches.append(match_dict)
    
    # Create compatibility variable for functions that expect all_matches
    # Convert entire df_liga to list of dicts for compatibility
    all_matches = []
    if not df_liga.empty:
        for _, row in df_liga.iterrows():
            match_dict = row.to_dict()
            match_dict["status"] = "played"  # Wyscout data = played matches
            if "Date" in match_dict and pd.notna(match_dict["Date"]):
                if isinstance(match_dict["Date"], pd.Timestamp):
                    match_dict["date"] = match_dict["Date"].strftime("%Y-%m-%d")
                else:
                    match_dict["date"] = str(match_dict["Date"])
            
            # Derive is_home from Match string if not already present
            if "is_home" not in match_dict or pd.isna(match_dict.get("is_home")):
                match_str = str(match_dict.get("Match", ""))
                team_name = str(match_dict.get("Team", "")).strip()
                if match_str and team_name:
                    # Extract teams from match string (format: "Team1 - Team2 score:score")
                    # The first team is home, second is away
                    parts = match_str.split(" - ")
                    if len(parts) >= 2:
                        home_team = parts[0].strip()
                        # Check if this team is the home team
                        team_name_lower = team_name.lower()
                        home_team_lower = home_team.lower()
                        # Check if team name matches home team (with some flexibility)
                        if (team_name_lower in home_team_lower or 
                            home_team_lower in team_name_lower or
                            team_name_lower.replace(' fc', '').strip() in home_team_lower.replace(' fc', '').strip() or
                            home_team_lower.replace(' fc', '').strip() in team_name_lower.replace(' fc', '').strip()):
                            match_dict["is_home"] = True
                        else:
                            match_dict["is_home"] = False
                    else:
                        # Fallback: default to False if we can't determine
                        match_dict["is_home"] = False
                else:
                    match_dict["is_home"] = False
            
            all_matches.append(match_dict)
    
    # Crear pestañas para organizar el contenido
    # Use session state to preserve selected tab across reruns
    if 'selected_tab_index' not in st.session_state:
        st.session_state.selected_tab_index = 0
    
    # Tab navigation using radio buttons (preserves state on rerun)
    tab_options = ["Resumen", "Comparación", "Análisis Táctico y Fases"]
    
    # Ensure the stored index is valid (in case tabs were removed)
    if st.session_state.selected_tab_index >= len(tab_options):
        st.session_state.selected_tab_index = 0
    
    selected_tab = st.radio(
        "",
        options=tab_options,
        index=st.session_state.selected_tab_index,
        key="tab_selector",
        horizontal=True,
        label_visibility="collapsed"
    )
    
    # Update session state with selected tab index
    st.session_state.selected_tab_index = tab_options.index(selected_tab)
    
    # Create tab content containers (using conditional rendering instead of st.tabs)
    tab1 = selected_tab == "Resumen"
    tab2 = selected_tab == "Comparación"
    tab4 = selected_tab == "Análisis Táctico y Fases"
    
    # TAB 1: RESUMEN (Métricas clave + Radar)
    if tab1:
        if team_averages:
            # Calcular datos iniciales sin filtro (para Forma Reciente)
            filtered_matches = team_all_matches
            filtered_averages = team_averages
            display_averages = team_averages
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Forma Reciente (movido arriba, antes de las métricas clave)
            st.markdown("""
            <h2 style='color:#FF9900; text-align:center; margin-top:20px;'>Forma Reciente</h2>
            """, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            
            if filtered_matches:
                # Selector de filtro de partidos
                recent_form_filter = st.radio(
                    "Mostrar:",
                    options=["Todos los partidos", "Últimos 3 partidos", "Últimos 5 partidos", "En Casa", "Fuera"],
                    horizontal=True,
                    key="recent_form_filter"
                )
                
                # Aplicar filtro según la selección
                if recent_form_filter == "Todos los partidos":
                    filtered_matches_for_form = filtered_matches
                    num_matches = None
                elif recent_form_filter == "Últimos 3 partidos":
                    filtered_matches_for_form = filtered_matches
                    num_matches = 3
                elif recent_form_filter == "Últimos 5 partidos":
                    filtered_matches_for_form = filtered_matches
                    num_matches = 5
                elif recent_form_filter == "En Casa":
                    filtered_matches_for_form = filter_matches_by_type(filtered_matches, selected_opponent, "home", all_matches)
                    num_matches = None
                elif recent_form_filter == "Fuera":
                    filtered_matches_for_form = filter_matches_by_type(filtered_matches, selected_opponent, "away", all_matches)
                    num_matches = None
                else:
                    filtered_matches_for_form = filtered_matches
                    num_matches = None
                
                # Obtener partidos recientes (siempre procesar a través de get_recent_form para obtener resultados)
                recent_form = get_recent_form(filtered_matches_for_form, selected_opponent, num_matches=num_matches)
                
                if recent_form:
                    display_recent_form(recent_form, selected_opponent)
                else:
                    st.info("No hay suficientes partidos jugados para mostrar el formulario reciente.")
            else:
                st.info("No hay partidos disponibles para este equipo.")
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("---")
            
            # Mostrar resumen de partidos (movido directamente arriba de Métricas Clave - 12 KPI cards)
            # Top section: Show only "Partidos Jugados" (unfiltered)
            # "Partidos vs Cibao" is shown in filtered section below to avoid duplication
            col_info1 = st.columns(1)[0]
            with col_info1:
                # Contar partidos jugados
                # For Wyscout data, all rows are played matches (they're statistics)
                # For Scoresway data, check status field
                played_count = 0
                seen_matches = set()  # Track unique matches to avoid double counting
                
                for m in filtered_matches:
                    # Skip invalid matches (where Match is NaN, empty, or doesn't contain " - ")
                    match_str = str(m.get("Match", "")).strip() if "Match" in m else ""
                    if not match_str or match_str.lower() in ["nan", "none", ""] or " - " not in match_str:
                        continue
                    
                    # For Wyscout DataFrame rows, create unique match identifier
                    match_id = None
                    if "Match" in m and "Date" in m:
                        date_str = str(m.get("Date", ""))
                        # Skip if Date is also invalid
                        if date_str.lower() in ["nan", "none", ""]:
                            continue
                        match_id = f"{match_str}_{date_str}"
                    elif "match_id" in m:
                        match_id = str(m.get("match_id", ""))
                    
                    # Skip if we've already counted this match
                    if match_id and match_id in seen_matches:
                        continue
                    
                    status = m.get("status", "")
                    # Verificar status
                    if isinstance(status, str) and status.lower() in ["played", "finished", "ft", "jugado", "finalizado"]:
                        played_count += 1
                        if match_id:
                            seen_matches.add(match_id)
                    # Si no tiene status válido, verificar si tiene score (indica que fue jugado)
                    elif m.get("match_data"):
                        match_data = m.get("match_data", {})
                        live_data = match_data.get("liveData", {})
                        match_details = live_data.get("matchDetails", {})
                        scores = match_details.get("scores", {})
                        if scores and (scores.get("ft") or scores.get("total")):
                            played_count += 1
                            if match_id:
                                seen_matches.add(match_id)
                        # También verificar por fecha pasada (si no hay score pero la fecha pasó, probablemente fue jugado)
                        elif m.get("date"):
                            from datetime import datetime
                            match_date = m.get("date")
                            if isinstance(match_date, str):
                                try:
                                    match_date = datetime.strptime(match_date, '%Y-%m-%d')
                                except:
                                    pass
                            if isinstance(match_date, datetime):
                                today = datetime.now()
                                if match_date < today:
                                    played_count += 1
                                    if match_id:
                                        seen_matches.add(match_id)
                    # For Wyscout DataFrame rows, if they have Goals or other stats, they're played
                    elif "Goals" in m or "xG" in m:
                        played_count += 1
                        if match_id:
                            seen_matches.add(match_id)
                    # If no other check passed but it's in filtered_matches and has a Match field, count it
                    elif "Match" in m and m.get("Match"):
                        played_count += 1
                        if match_id:
                            seen_matches.add(match_id)
                
                st.metric("Partidos Jugados", played_count)
            # Removed col_info2 - "Partidos vs Cibao" is shown in filtered section below to avoid duplication
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Filtro de partidos (UI movido aquí para estar junto a Métricas Clave)
            filter_options_ui = {
                "Todos los partidos": "all",
                "Últimos 3 partidos": "last_3",
                "Últimos 5 partidos": "last_5",
                "En Casa": "home",
                "Fuera": "away",
            }
            if selected_opponent != CIBAO_TEAM_NAME:
                filter_options_ui["Partidos vs Cibao"] = "vs_cibao"
            
            # Obtener el índice del filtro actual para mantener la selección
            current_filter_keys = list(filter_options_ui.keys())
            try:
                current_index = current_filter_keys.index(selected_filter) if selected_filter in current_filter_keys else 0
            except:
                current_index = 0
            
            selected_filter_ui = st.radio(
                "Filtrar por:",
                options=current_filter_keys,
                horizontal=True,
                key="match_filter_ui",
                index=current_index
            )
            filter_type_ui = filter_options_ui[selected_filter_ui]
            
            # Recalcular con el filtro seleccionado
            if filter_type_ui == "last_3":
                # Get last 3 matches for the selected team by sorting and filtering
                # Filter matches for the selected team
                team_filtered = []
                team_name_lower = selected_opponent.lower().strip()
                for match in team_all_matches:
                    match_str = str(match.get("Match", "")).lower()
                    if team_name_lower in match_str:
                        team_filtered.append(match)
                
                # Sort by date (most recent first)
                team_filtered.sort(key=lambda x: (
                    pd.to_datetime(x.get("Date") or x.get("date") or "1900-01-01", errors='coerce')
                ), reverse=True)
                
                # Take last 3
                filtered_matches_ui = team_filtered[:3] if len(team_filtered) >= 3 else team_filtered
            elif filter_type_ui == "last_5":
                # Get last 5 matches for the selected team by sorting and filtering
                # Filter matches for the selected team
                team_filtered = []
                team_name_lower = selected_opponent.lower().strip()
                for match in team_all_matches:
                    match_str = str(match.get("Match", "")).lower()
                    if team_name_lower in match_str:
                        team_filtered.append(match)
                
                # Sort by date (most recent first)
                team_filtered.sort(key=lambda x: (
                    pd.to_datetime(x.get("Date") or x.get("date") or "1900-01-01", errors='coerce')
                ), reverse=True)
                
                # Take last 5
                filtered_matches_ui = team_filtered[:5] if len(team_filtered) >= 5 else team_filtered
            elif filter_type_ui == "home" or filter_type_ui == "away" or filter_type_ui == "vs_cibao":
                # Apply filter using filter_matches_by_type
                filtered_matches_ui = filter_matches_by_type(team_all_matches, selected_opponent, filter_type_ui, all_matches)
            else:
                # For "all" or other cases, use all matches
                filtered_matches_ui = team_all_matches
            
            # Calculate averages from filtered matches (DataFrame-based)
            # For Wyscout data, use the original DataFrame filtering instead of converting dicts back
            if isinstance(df_liga, pd.DataFrame) and not df_liga.empty and "Team" in df_liga.columns:
                # Filter DataFrame directly for better accuracy
                # Normalize accents (data is already normalized during upload, but normalize selected name too)
                selected_opponent_no_accents = remove_accents(selected_opponent)
                selected_opponent_normalized = selected_opponent_no_accents.lower().strip().replace(' fc', '').replace(' fc', '').strip()
                
                # Try exact match first (case-insensitive, strip whitespace, with accent normalization)
                filtered_team_df = df_liga[df_liga["Team"].apply(lambda x: remove_accents(str(x)).lower().strip() == selected_opponent_no_accents.lower().strip())].copy()
                
                # If no exact match, try flexible matching (partial match)
                if filtered_team_df.empty:
                    def team_name_match(team_name):
                        if pd.isna(team_name):
                            return False
                        # Normalize accents for both sides
                        team_name_no_accents = remove_accents(str(team_name))
                        team_name_normalized = team_name_no_accents.lower().strip().replace(' fc', '').replace(' fc', '').strip()
                        selected_normalized = selected_opponent_normalized
                        # Try various matching strategies
                        # 1. Exact match (already tried above)
                        # 2. Selected name is contained in team name (e.g., "Delfines" in "Delfines Del Este")
                        # 3. Team name is contained in selected name
                        # 4. Handle "Del" vs "De" variations
                        return (selected_normalized in team_name_normalized or 
                               team_name_normalized in selected_normalized or
                               selected_normalized.replace(' del ', ' de ') in team_name_normalized.replace(' del ', ' de ') or
                               team_name_normalized.replace(' del ', ' de ') in selected_normalized.replace(' del ', ' de ') or
                               # Special case: "Delfines" should match "Delfines Del Este"
                               (selected_normalized == "delfines" and "delfines" in team_name_normalized and "del este" in team_name_normalized))
                    
                    filtered_team_df = df_liga[df_liga["Team"].apply(team_name_match)].copy()
                
                # ALWAYS derive is_home from Match string (ignore any existing column - it may have wrong float values)
                # This ensures consistency, especially for teams with accents in their names
                # Data is normalized during upload (no accents), but normalize here too for safety
                if "Match" in filtered_team_df.columns:
                    def derive_is_home(row):
                        match_str = str(row.get("Match", "")).strip()
                        team_name = str(row.get("Team", "")).strip()
                        
                        if not match_str or match_str == "nan" or not team_name:
                            return False
                        
                        if " - " not in match_str:
                            return False
                        
                        parts = match_str.split(" - ")
                        if len(parts) < 2:
                            return False
                        
                        home_team = parts[0].strip()
                        # Remove score if present (e.g., "Team 2:1" → "Team")
                        home_team = re.sub(r'\s+\d+:\d+$', '', home_team).strip()
                        
                        # Clean team name (remove (1), (2) suffixes) for better matching
                        team_name_cleaned = re.sub(r'\s*\(\d+\)\s*$', '', team_name).strip()
                        
                        # Normalize accents for both (data should already be normalized, but do it here too)
                        team_name_no_accents = remove_accents(team_name_cleaned)
                        home_team_no_accents = remove_accents(home_team)
                        
                        # Normalize both for comparison (handle accents properly)
                        team_name_lower = team_name_no_accents.lower().strip()
                        home_team_lower = home_team_no_accents.lower().strip()
                        
                        # Remove " FC" suffixes and clean both sides
                        team_clean = team_name_lower.replace(' fc', '').strip()
                        home_clean = home_team_lower.replace(' fc', '').strip()
                        
                        # Check if team name matches home team (with flexible matching)
                        # This handles accents correctly by normalizing them first
                        is_home = (team_name_lower in home_team_lower or 
                                  home_team_lower in team_name_lower or
                                  team_clean in home_clean or
                                  home_clean in team_clean)
                        
                        return bool(is_home)
                    
                    # ALWAYS overwrite is_home column (even if it exists) to ensure correct boolean values
                    filtered_team_df["is_home"] = filtered_team_df.apply(derive_is_home, axis=1).astype(bool)
                
                # Apply UI filter to the DataFrame
                if filter_type_ui != "all":
                    if filter_type_ui == "last_3":
                        # Sort by date and take last 3
                        if "Date" in filtered_team_df.columns:
                            filtered_team_df = filtered_team_df.sort_values("Date", ascending=False).head(3).copy()
                    elif filter_type_ui == "last_5":
                        # Sort by date and take last 5
                        if "Date" in filtered_team_df.columns:
                            filtered_team_df = filtered_team_df.sort_values("Date", ascending=False).head(5).copy()
                    elif filter_type_ui == "home":
                        # Filter for home matches
                        # is_home should always be derived above, but check anyway
                        if "is_home" in filtered_team_df.columns:
                            # Use boolean comparison (ensure it's boolean, not float)
                            filtered_team_df = filtered_team_df[filtered_team_df["is_home"].astype(bool) == True].copy()
                        elif "Match" in filtered_team_df.columns:
                            # Derive is_home from Match string
                            def is_home_match(row):
                                match_str = str(row.get("Match", ""))
                                team_name = str(row.get("Team", "")).strip()
                                if match_str and team_name:
                                    parts = match_str.split(" - ")
                                    if len(parts) >= 2:
                                        home_team = parts[0].strip()
                                        return team_name.lower() in home_team.lower() or home_team.lower() in team_name.lower()
                                return False
                            filtered_team_df = filtered_team_df[filtered_team_df.apply(is_home_match, axis=1)].copy()
                    elif filter_type_ui == "away":
                        # Filter for away matches
                        # is_home should always be derived above, but check anyway
                        if "is_home" in filtered_team_df.columns:
                            # Use boolean comparison (ensure it's boolean, not float)
                            filtered_team_df = filtered_team_df[filtered_team_df["is_home"].astype(bool) == False].copy()
                        elif "Match" in filtered_team_df.columns:
                            # Derive is_home from Match string
                            def is_away_match(row):
                                match_str = str(row.get("Match", ""))
                                team_name = str(row.get("Team", "")).strip()
                                if match_str and team_name:
                                    parts = match_str.split(" - ")
                                    if len(parts) >= 2:
                                        home_team = parts[0].strip()
                                        return not (team_name.lower() in home_team.lower() or home_team.lower() in team_name.lower())
                                return True
                            filtered_team_df = filtered_team_df[filtered_team_df.apply(is_away_match, axis=1)].copy()
                    elif filter_type_ui == "vs_cibao":
                        # Filter for matches vs Cibao
                        if "Match" in filtered_team_df.columns:
                            cibao_name_no_accents = remove_accents(CIBAO_TEAM_NAME).lower()
                            def is_vs_cibao_match(row):
                                match_str_no_accents = remove_accents(str(row.get("Match", ""))).lower()
                                team_name_no_accents = remove_accents(str(row.get("Team", ""))).lower().strip()
                                # Check if both Cibao and the selected team are in the match string
                                return cibao_name_no_accents in match_str_no_accents and team_name_no_accents in match_str_no_accents
                            filtered_team_df = filtered_team_df[filtered_team_df.apply(is_vs_cibao_match, axis=1)].copy()
                
                # Calculate averages from filtered DataFrame (already filtered by team, so pass already_filtered=True)
                filtered_averages_ui = calculate_team_averages_from_df(filtered_team_df, selected_opponent, already_filtered=True) if not filtered_team_df.empty else {}
            elif filtered_matches_ui:
                # Fallback: convert dicts to DataFrame (less reliable)
                filtered_df = pd.DataFrame(filtered_matches_ui)
                # Ensure Team column exists
                if "Team" not in filtered_df.columns and selected_opponent:
                    filtered_df["Team"] = selected_opponent
                # filtered_matches_ui already contains only matches for selected_opponent, so already_filtered=True
                filtered_averages_ui = calculate_team_averages_from_df(filtered_df, selected_opponent, already_filtered=True) if not filtered_df.empty else {}
            else:
                filtered_averages_ui = {}
            display_averages_ui = filtered_averages_ui if filtered_averages_ui else team_averages
            
            # Calcular promedios filtrados de competencia y Cibao
            # Apply the same filter to league/competition averages as applied to the opponent
            if isinstance(df_liga, pd.DataFrame) and not df_liga.empty and "Team" in df_liga.columns:
                # Start with all league data
                filtered_competition_df = df_liga.copy()
                
                # Derive is_home from Match string for all teams (if not already present)
                if "Match" in filtered_competition_df.columns and "is_home" not in filtered_competition_df.columns:
                    def derive_is_home_for_competition(row):
                        match_str = str(row.get("Match", "")).strip()
                        team_name = str(row.get("Team", "")).strip()
                        
                        if not match_str or match_str == "nan" or not team_name or " - " not in match_str:
                            return False
                        
                        parts = match_str.split(" - ")
                        if len(parts) < 2:
                            return False
                        
                        home_team = parts[0].strip()
                        home_team = re.sub(r'\s+\d+:\d+$', '', home_team).strip()
                        
                        team_name_cleaned = re.sub(r'\s*\(\d+\)\s*$', '', team_name).strip()
                        team_name_no_accents = remove_accents(team_name_cleaned)
                        home_team_no_accents = remove_accents(home_team)
                        
                        team_name_lower = team_name_no_accents.lower().strip()
                        home_team_lower = home_team_no_accents.lower().strip()
                        
                        team_clean = team_name_lower.replace(' fc', '').strip()
                        home_clean = home_team_lower.replace(' fc', '').strip()
                        
                        is_home = (team_name_lower in home_team_lower or 
                                  home_team_lower in team_name_lower or
                                  team_clean in home_clean or
                                  home_clean in team_clean)
                        
                        return bool(is_home)
                    
                    filtered_competition_df["is_home"] = filtered_competition_df.apply(derive_is_home_for_competition, axis=1).astype(bool)
                elif "Match" in filtered_competition_df.columns:
                    # Re-derive is_home to ensure it's correct (overwrite any existing values)
                    def derive_is_home_for_competition(row):
                        match_str = str(row.get("Match", "")).strip()
                        team_name = str(row.get("Team", "")).strip()
                        
                        if not match_str or match_str == "nan" or not team_name or " - " not in match_str:
                            return False
                        
                        parts = match_str.split(" - ")
                        if len(parts) < 2:
                            return False
                        
                        home_team = parts[0].strip()
                        home_team = re.sub(r'\s+\d+:\d+$', '', home_team).strip()
                        
                        team_name_cleaned = re.sub(r'\s*\(\d+\)\s*$', '', team_name).strip()
                        team_name_no_accents = remove_accents(team_name_cleaned)
                        home_team_no_accents = remove_accents(home_team)
                        
                        team_name_lower = team_name_no_accents.lower().strip()
                        home_team_lower = home_team_no_accents.lower().strip()
                        
                        team_clean = team_name_lower.replace(' fc', '').strip()
                        home_clean = home_team_lower.replace(' fc', '').strip()
                        
                        is_home = (team_name_lower in home_team_lower or 
                                  home_team_lower in team_name_lower or
                                  team_clean in home_clean or
                                  home_clean in team_clean)
                        
                        return bool(is_home)
                    
                    filtered_competition_df["is_home"] = filtered_competition_df.apply(derive_is_home_for_competition, axis=1).astype(bool)
                
                # Apply UI filter to competition DataFrame (same filters as opponent)
                if filter_type_ui != "all":
                    if filter_type_ui == "last_3":
                        # Get last 3 matches for each team, then calculate averages
                        if "Date" in filtered_competition_df.columns:
                            # Group by team and get last 3 matches per team
                            filtered_competition_df = filtered_competition_df.groupby("Team").apply(
                                lambda x: x.sort_values("Date", ascending=False).head(3)
                            ).reset_index(drop=True)
                    elif filter_type_ui == "last_5":
                        # Get last 5 matches for each team, then calculate averages
                        if "Date" in filtered_competition_df.columns:
                            # Group by team and get last 5 matches per team
                            filtered_competition_df = filtered_competition_df.groupby("Team").apply(
                                lambda x: x.sort_values("Date", ascending=False).head(5)
                            ).reset_index(drop=True)
                    elif filter_type_ui == "home":
                        # Filter to all home matches across all teams
                        if "is_home" in filtered_competition_df.columns:
                            filtered_competition_df = filtered_competition_df[filtered_competition_df["is_home"].astype(bool) == True].copy()
                        elif "Match" in filtered_competition_df.columns:
                            def is_home_match_competition(row):
                                match_str = str(row.get("Match", ""))
                                team_name = str(row.get("Team", "")).strip()
                                if match_str and team_name:
                                    parts = match_str.split(" - ")
                                    if len(parts) >= 2:
                                        home_team = parts[0].strip()
                                        return team_name.lower() in home_team.lower() or home_team.lower() in team_name.lower()
                                return False
                            filtered_competition_df = filtered_competition_df[filtered_competition_df.apply(is_home_match_competition, axis=1)].copy()
                    elif filter_type_ui == "away":
                        # Filter to all away matches across all teams
                        if "is_home" in filtered_competition_df.columns:
                            filtered_competition_df = filtered_competition_df[filtered_competition_df["is_home"].astype(bool) == False].copy()
                        elif "Match" in filtered_competition_df.columns:
                            def is_away_match_competition(row):
                                match_str = str(row.get("Match", ""))
                                team_name = str(row.get("Team", "")).strip()
                                if match_str and team_name:
                                    parts = match_str.split(" - ")
                                    if len(parts) >= 2:
                                        home_team = parts[0].strip()
                                        return not (team_name.lower() in home_team.lower() or home_team.lower() in team_name.lower())
                                return True
                            filtered_competition_df = filtered_competition_df[filtered_competition_df.apply(is_away_match_competition, axis=1)].copy()
                    elif filter_type_ui == "vs_cibao" and selected_opponent != CIBAO_TEAM_NAME:
                        # Filter to all matches where Cibao was involved (league average from matches vs Cibao)
                        cibao_name_no_accents = remove_accents(CIBAO_TEAM_NAME).lower()
                        def is_vs_cibao_match_competition(row):
                            match_str_no_accents = remove_accents(str(row.get("Match", ""))).lower()
                            # Check if Cibao is in the match string
                            return cibao_name_no_accents in match_str_no_accents
                        filtered_competition_df = filtered_competition_df[filtered_competition_df.apply(is_vs_cibao_match_competition, axis=1)].copy()
                
                # Calculate filtered competition averages from filtered DataFrame
                if not filtered_competition_df.empty:
                    # Use the same logic as initial competition_averages calculation
                    numeric_cols = filtered_competition_df.select_dtypes(include=[np.number]).columns.tolist()
                    
                    # Also include columns with % in the name that are numeric
                    pct_cols = [col for col in filtered_competition_df.columns if '%' in str(col) and col not in numeric_cols]
                    for col in pct_cols:
                        if pd.api.types.is_numeric_dtype(filtered_competition_df[col]):
                            if col not in numeric_cols:
                                numeric_cols.append(col)
                        else:
                            try:
                                pd.to_numeric(filtered_competition_df[col], errors='raise')
                                if col not in numeric_cols:
                                    numeric_cols.append(col)
                            except (ValueError, TypeError):
                                pass
                    
                    # Use the same mapping
                    column_mapping = get_wyscout_to_scoresway_mapping()
                    
                    filtered_competition_averages = {}
                    for col in numeric_cols:
                        if col not in ["Match", "Date", "Team"]:
                            avg_value = filtered_competition_df[col].mean()
                            if pd.notna(avg_value):
                                # Use mapped name if exists
                                metric_key = column_mapping.get(col)
                                if metric_key:
                                    filtered_competition_averages[metric_key] = float(avg_value)
                                # Also keep original name
                                filtered_competition_averages[col] = float(avg_value)
                                # And normalized name
                                normalized_name = col.lower().replace(" ", "_").replace("/", "_").replace(",", "").replace("(", "").replace(")", "").replace("%", "_pct")
                                filtered_competition_averages[normalized_name] = float(avg_value)
                    
                    # Calculate derived metrics for competition
                    if "corners_with_shots" in filtered_competition_averages:
                        filtered_competition_averages["wonCorners"] = filtered_competition_averages.get("corners_with_shots", 0)
                else:
                    # Fallback to unfiltered if filtered is empty
                    filtered_competition_averages = competition_averages.copy() if competition_averages else {}
            else:
                # Fallback: use unfiltered averages
                filtered_competition_averages = competition_averages.copy() if competition_averages else {}
            
            # Apply the same filter to Cibao's stats as applied to the opponent
            if isinstance(df_liga, pd.DataFrame) and not df_liga.empty and "Team" in df_liga.columns:
                # Filter Cibao DataFrame directly (same approach as opponent)
                cibao_name_normalized = remove_accents(CIBAO_TEAM_NAME).lower().strip().replace(' fc', '').replace(' fc', '').strip()
                
                # Filter for Cibao team
                filtered_cibao_df_base = df_liga[df_liga["Team"].apply(lambda x: remove_accents(str(x)).lower().strip() == remove_accents(CIBAO_TEAM_NAME).lower().strip())].copy()
                if filtered_cibao_df_base.empty:
                    filtered_cibao_df_base = df_liga[df_liga["Team"].apply(lambda x: cibao_name_normalized in remove_accents(str(x)).lower().strip().replace(' fc', '') or remove_accents(str(x)).lower().strip().replace(' fc', '') in cibao_name_normalized)].copy()
                
                # Derive is_home from Match string (same as opponent)
                if "Match" in filtered_cibao_df_base.columns:
                    def derive_cibao_is_home(row):
                        match_str = str(row.get("Match", "")).strip()
                        team_name = str(row.get("Team", "")).strip()
                        
                        if not match_str or match_str == "nan" or not team_name or " - " not in match_str:
                            return False
                        
                        parts = match_str.split(" - ")
                        if len(parts) < 2:
                            return False
                        
                        home_team = parts[0].strip()
                        home_team = re.sub(r'\s+\d+:\d+$', '', home_team).strip()
                        
                        team_name_cleaned = re.sub(r'\s*\(\d+\)\s*$', '', team_name).strip()
                        team_name_no_accents = remove_accents(team_name_cleaned)
                        home_team_no_accents = remove_accents(home_team)
                        
                        team_name_lower = team_name_no_accents.lower().strip()
                        home_team_lower = home_team_no_accents.lower().strip()
                        
                        team_clean = team_name_lower.replace(' fc', '').strip()
                        home_clean = home_team_lower.replace(' fc', '').strip()
                        
                        is_home = (team_name_lower in home_team_lower or 
                                  home_team_lower in team_name_lower or
                                  team_clean in home_clean or
                                  home_clean in team_clean)
                        
                        return bool(is_home)
                    
                    filtered_cibao_df_base["is_home"] = filtered_cibao_df_base.apply(derive_cibao_is_home, axis=1).astype(bool)
                
                # Apply UI filter to Cibao DataFrame (same filters as opponent)
                filtered_cibao_df = filtered_cibao_df_base.copy()
                if filter_type_ui != "all":
                    if filter_type_ui == "last_3":
                        if "Date" in filtered_cibao_df.columns:
                            filtered_cibao_df = filtered_cibao_df.sort_values("Date", ascending=False).head(3).copy()
                    elif filter_type_ui == "last_5":
                        if "Date" in filtered_cibao_df.columns:
                            filtered_cibao_df = filtered_cibao_df.sort_values("Date", ascending=False).head(5).copy()
                    elif filter_type_ui == "home":
                        if "is_home" in filtered_cibao_df.columns:
                            filtered_cibao_df = filtered_cibao_df[filtered_cibao_df["is_home"].astype(bool) == True].copy()
                        elif "Match" in filtered_cibao_df.columns:
                            def is_cibao_home_match(row):
                                match_str = str(row.get("Match", ""))
                                team_name = str(row.get("Team", "")).strip()
                                if match_str and team_name:
                                    parts = match_str.split(" - ")
                                    if len(parts) >= 2:
                                        home_team = parts[0].strip()
                                        return team_name.lower() in home_team.lower() or home_team.lower() in team_name.lower()
                                return False
                            filtered_cibao_df = filtered_cibao_df[filtered_cibao_df.apply(is_cibao_home_match, axis=1)].copy()
                    elif filter_type_ui == "away":
                        if "is_home" in filtered_cibao_df.columns:
                            filtered_cibao_df = filtered_cibao_df[filtered_cibao_df["is_home"].astype(bool) == False].copy()
                        elif "Match" in filtered_cibao_df.columns:
                            def is_cibao_away_match(row):
                                match_str = str(row.get("Match", ""))
                                team_name = str(row.get("Team", "")).strip()
                                if match_str and team_name:
                                    parts = match_str.split(" - ")
                                    if len(parts) >= 2:
                                        home_team = parts[0].strip()
                                        return not (team_name.lower() in home_team.lower() or home_team.lower() in team_name.lower())
                                return True
                            filtered_cibao_df = filtered_cibao_df[filtered_cibao_df.apply(is_cibao_away_match, axis=1)].copy()
                    elif filter_type_ui == "vs_cibao" and selected_opponent != CIBAO_TEAM_NAME:
                        # Filter for matches vs the selected opponent
                        opponent_name_no_accents = remove_accents(selected_opponent).lower()
                        def is_cibao_vs_opponent_match(row):
                            match_str_no_accents = remove_accents(str(row.get("Match", ""))).lower()
                            team_name_no_accents = remove_accents(str(row.get("Team", ""))).lower().strip()
                            # Check if both Cibao and the selected opponent are in the match string
                            return cibao_name_normalized in match_str_no_accents and opponent_name_no_accents in match_str_no_accents
                        filtered_cibao_df = filtered_cibao_df[filtered_cibao_df.apply(is_cibao_vs_opponent_match, axis=1)].copy()
                
                # Calculate filtered Cibao averages from filtered DataFrame
                filtered_cibao_averages = calculate_team_averages_from_df(filtered_cibao_df, CIBAO_TEAM_NAME, already_filtered=True) if not filtered_cibao_df.empty else {}
                # Fallback to unfiltered if filtered is empty
                if not filtered_cibao_averages:
                    filtered_cibao_averages = cibao_averages.copy() if cibao_averages else {}
            else:
                # Fallback: use unfiltered averages
                filtered_cibao_averages = cibao_averages.copy() if cibao_averages else {}
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Mostrar resumen de partidos (directamente arriba de Métricas Clave - 12 KPI cards)
            # Calculate h2h_count once before displaying
            h2h_count = 0
            if selected_opponent != CIBAO_TEAM_NAME:
                cibao_name_no_accents = remove_accents(CIBAO_TEAM_NAME).lower()
                opponent_name_no_accents = remove_accents(selected_opponent).lower()
                for match in filtered_matches_ui:
                    match_str_no_accents = remove_accents(str(match.get("Match", ""))).lower()
                    if cibao_name_no_accents in match_str_no_accents and opponent_name_no_accents in match_str_no_accents:
                        h2h_count += 1
            
            col_info1, col_info2 = st.columns(2)
            with col_info1:
                # Contar partidos jugados - verificar status o si tiene score data
                played_count = 0
                for m in filtered_matches_ui:
                    status = m.get("status", "")
                    # Verificar status
                    if isinstance(status, str) and status.lower() in ["played", "finished", "ft", "jugado", "finalizado"]:
                        played_count += 1
                    # Si no tiene status válido, verificar si tiene score (indica que fue jugado)
                    elif m.get("match_data"):
                        match_data = m.get("match_data", {})
                        live_data = match_data.get("liveData", {})
                        match_details = live_data.get("matchDetails", {})
                        scores = match_details.get("scores", {})
                        if scores and (scores.get("ft") or scores.get("total")):
                            played_count += 1
                        # También verificar por fecha pasada (si no hay score pero la fecha pasó, probablemente fue jugado)
                        elif m.get("date"):
                            from datetime import datetime
                            match_date = m.get("date")
                            if isinstance(match_date, str):
                                try:
                                    match_date = datetime.strptime(match_date, '%Y-%m-%d')
                                except:
                                    pass
                            if isinstance(match_date, datetime):
                                today = datetime.now()
                                if match_date < today:
                                    played_count += 1
                # Show "Partidos vs Cibao" instead of "Partidos Jugados" when filter is "vs_cibao"
                if filter_type_ui == "vs_cibao" and selected_opponent != CIBAO_TEAM_NAME:
                    # When filtered to vs_cibao, show h2h_count instead of played_count
                    st.metric("Partidos vs Cibao", h2h_count)
                else:
                    st.metric("Partidos Jugados", played_count)
            with col_info2:
                if selected_opponent != CIBAO_TEAM_NAME and filter_type_ui != "vs_cibao":
                    # Only show "Partidos vs Cibao" when filter is NOT vs_cibao (to avoid duplication)
                    st.metric("Partidos vs Cibao", h2h_count)
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("""
            <h2 style='color:#FF9900; text-align:center; margin-top:20px;'>Métricas Clave</h2>
            """, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Fila 1: Goals, xG, Conceded goals, PPDA
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                # 1. Goals
                goals = display_averages_ui.get("goals", 0)
                comp_goals = filtered_competition_averages.get("goals", 0) if filtered_competition_averages else 0
                cibao_goals = filtered_cibao_averages.get("goals", 0) if filtered_cibao_averages else 0
                display_metric_card(
                    "Goles",
                    f"{goals:.2f}",
                    "",
                    f"Por 90 minutos",
                    competition_avg=f"{comp_goals:.2f}",
                    cibao_avg=f"{cibao_goals:.2f}"
                )
            
            with col2:
                # 2. xG
                xg = display_averages_ui.get("xg", 0)
                comp_xg = filtered_competition_averages.get("xg", 0) if filtered_competition_averages else 0
                cibao_xg = filtered_cibao_averages.get("xg", 0) if filtered_cibao_averages else 0
                display_metric_card(
                    "xG",
                    f"{xg:.2f}",
                    "",
                    f"Por 90 minutos",
                    competition_avg=f"{comp_xg:.2f}",
                    cibao_avg=f"{cibao_xg:.2f}"
                )
            
            with col3:
                # 3. Conceded goals
                goals_conceded = display_averages_ui.get("goalsConceded", 0)
                comp_gc = filtered_competition_averages.get("goalsConceded", 0) if filtered_competition_averages else 0
                cibao_gc = filtered_cibao_averages.get("goalsConceded", 0) if filtered_cibao_averages else 0
                display_metric_card(
                    "Goles Recibidos",
                    f"{goals_conceded:.2f}",
                    "",
                    f"Por 90 minutos",
                    competition_avg=f"{comp_gc:.2f}",
                    cibao_avg=f"{cibao_gc:.2f}",
                    higher_is_better=False  # Lower is better
                )
            
            with col4:
                # 4. PPDA
                ppda = display_averages_ui.get("ppda", 0)
                comp_ppda = filtered_competition_averages.get("ppda", 0) if filtered_competition_averages else 0
                cibao_ppda = filtered_cibao_averages.get("ppda", 0) if filtered_cibao_averages else 0
                ppda_display = f"{ppda:.2f}" if ppda > 0 else "N/A"
                comp_ppda_display = f"{comp_ppda:.2f}" if comp_ppda > 0 else "N/A"
                cibao_ppda_display = f"{cibao_ppda:.2f}" if cibao_ppda > 0 else "N/A"
                display_metric_card(
                    "PPDA",
                    ppda_display,
                    "",
                    f"Promedio" if ppda > 0 else "Datos no disponibles",
                    competition_avg=comp_ppda_display,
                    cibao_avg=cibao_ppda_display,
                    higher_is_better=False  # Lower is better (more defensive pressure)
                )
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Fila 2: Defensive Duels Won %, Offensive Duels Won %, Aerial Duels Won %, Counter Attacks
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                # 5. Defensive Duels Won %
                # Try multiple key variations (check for None explicitly, not just falsy)
                # Note: Data uses "Win %" not "Won %"
                def_duels_won_pct = (display_averages_ui.get("defensive_duels_win__pct") if display_averages_ui.get("defensive_duels_win__pct") is not None else
                                    display_averages_ui.get("Defensive Duels Win %") if display_averages_ui.get("Defensive Duels Win %") is not None else
                                    display_averages_ui.get("defensive_duels_won_pct") if display_averages_ui.get("defensive_duels_won_pct") is not None else
                                    display_averages_ui.get("Defensive Duels Won %") if display_averages_ui.get("Defensive Duels Won %") is not None else
                                    display_averages_ui.get("defensive_duels_won__pct") if display_averages_ui.get("defensive_duels_won__pct") is not None else 0)
                comp_def_pct = (filtered_competition_averages.get("defensive_duels_win__pct") if filtered_competition_averages and filtered_competition_averages.get("defensive_duels_win__pct") is not None else
                               filtered_competition_averages.get("Defensive Duels Win %") if filtered_competition_averages and filtered_competition_averages.get("Defensive Duels Win %") is not None else
                               filtered_competition_averages.get("defensive_duels_won_pct") if filtered_competition_averages and filtered_competition_averages.get("defensive_duels_won_pct") is not None else
                               filtered_competition_averages.get("Defensive Duels Won %") if filtered_competition_averages and filtered_competition_averages.get("Defensive Duels Won %") is not None else
                               filtered_competition_averages.get("defensive_duels_won__pct") if filtered_competition_averages and filtered_competition_averages.get("defensive_duels_won__pct") is not None else 0) if filtered_competition_averages else 0
                cibao_def_pct = (filtered_cibao_averages.get("defensive_duels_win__pct") if filtered_cibao_averages and filtered_cibao_averages.get("defensive_duels_win__pct") is not None else
                                filtered_cibao_averages.get("Defensive Duels Win %") if filtered_cibao_averages and filtered_cibao_averages.get("Defensive Duels Win %") is not None else
                                filtered_cibao_averages.get("defensive_duels_won_pct") if filtered_cibao_averages and filtered_cibao_averages.get("defensive_duels_won_pct") is not None else
                                filtered_cibao_averages.get("Defensive Duels Won %") if filtered_cibao_averages and filtered_cibao_averages.get("Defensive Duels Won %") is not None else
                                filtered_cibao_averages.get("defensive_duels_won__pct") if filtered_cibao_averages and filtered_cibao_averages.get("defensive_duels_won__pct") is not None else 0) if filtered_cibao_averages else 0
                def_pct_display = f"{def_duels_won_pct:.1f}%" if def_duels_won_pct > 0 else "N/A"
                comp_def_pct_display = f"{comp_def_pct:.1f}%" if comp_def_pct > 0 else "N/A"
                cibao_def_pct_display = f"{cibao_def_pct:.1f}%" if cibao_def_pct > 0 else "N/A"
                display_metric_card(
                    "Duelos Defensivos Ganados %",
                    def_pct_display,
                    "",
                    f"Promedio" if def_duels_won_pct > 0 else "Datos no disponibles",
                    competition_avg=comp_def_pct_display,
                    cibao_avg=cibao_def_pct_display
                )
            
            with col2:
                # 6. Offensive Duels Won %
                # Try multiple key variations (check for None explicitly)
                # Note: Data uses "Win %" not "Won %"
                off_duels_won_pct = (display_averages_ui.get("offensive_duels_win__pct") if display_averages_ui.get("offensive_duels_win__pct") is not None else
                                    display_averages_ui.get("Offensive Duels Win %") if display_averages_ui.get("Offensive Duels Win %") is not None else
                                    display_averages_ui.get("offensive_duels_won_pct") if display_averages_ui.get("offensive_duels_won_pct") is not None else
                                    display_averages_ui.get("Offensive Duels Won %") if display_averages_ui.get("Offensive Duels Won %") is not None else
                                    display_averages_ui.get("offensive_duels_won__pct") if display_averages_ui.get("offensive_duels_won__pct") is not None else 0)
                comp_off_pct = (filtered_competition_averages.get("offensive_duels_win__pct") if filtered_competition_averages and filtered_competition_averages.get("offensive_duels_win__pct") is not None else
                               filtered_competition_averages.get("Offensive Duels Win %") if filtered_competition_averages and filtered_competition_averages.get("Offensive Duels Win %") is not None else
                               filtered_competition_averages.get("offensive_duels_won_pct") if filtered_competition_averages and filtered_competition_averages.get("offensive_duels_won_pct") is not None else
                               filtered_competition_averages.get("Offensive Duels Won %") if filtered_competition_averages and filtered_competition_averages.get("Offensive Duels Won %") is not None else
                               filtered_competition_averages.get("offensive_duels_won__pct") if filtered_competition_averages and filtered_competition_averages.get("offensive_duels_won__pct") is not None else 0) if filtered_competition_averages else 0
                cibao_off_pct = (filtered_cibao_averages.get("offensive_duels_win__pct") if filtered_cibao_averages and filtered_cibao_averages.get("offensive_duels_win__pct") is not None else
                                filtered_cibao_averages.get("Offensive Duels Win %") if filtered_cibao_averages and filtered_cibao_averages.get("Offensive Duels Win %") is not None else
                                filtered_cibao_averages.get("offensive_duels_won_pct") if filtered_cibao_averages and filtered_cibao_averages.get("offensive_duels_won_pct") is not None else
                                filtered_cibao_averages.get("Offensive Duels Won %") if filtered_cibao_averages and filtered_cibao_averages.get("Offensive Duels Won %") is not None else
                                filtered_cibao_averages.get("offensive_duels_won__pct") if filtered_cibao_averages and filtered_cibao_averages.get("offensive_duels_won__pct") is not None else 0) if filtered_cibao_averages else 0
                off_pct_display = f"{off_duels_won_pct:.1f}%" if off_duels_won_pct > 0 else "N/A"
                comp_off_pct_display = f"{comp_off_pct:.1f}%" if comp_off_pct > 0 else "N/A"
                cibao_off_pct_display = f"{cibao_off_pct:.1f}%" if cibao_off_pct > 0 else "N/A"
                display_metric_card(
                    "Duelos Ofensivos Ganados %",
                    off_pct_display,
                    "",
                    f"Promedio" if off_duels_won_pct > 0 else "Datos no disponibles",
                    competition_avg=comp_off_pct_display,
                    cibao_avg=cibao_off_pct_display
                )
            
            with col3:
                # 7. Aerial Duels Won %
                # Try multiple key variations (check for None explicitly)
                # Note: Data uses "Win %" not "Won %"
                aerial_duels_won_pct = (display_averages_ui.get("aerial_duels_win__pct") if display_averages_ui.get("aerial_duels_win__pct") is not None else
                                       display_averages_ui.get("Aerial Duels Win %") if display_averages_ui.get("Aerial Duels Win %") is not None else
                                       display_averages_ui.get("aerial_duels_won_pct") if display_averages_ui.get("aerial_duels_won_pct") is not None else
                                       display_averages_ui.get("Aerial Duels Won %") if display_averages_ui.get("Aerial Duels Won %") is not None else
                                       display_averages_ui.get("aerial_duels_won__pct") if display_averages_ui.get("aerial_duels_won__pct") is not None else 0)
                comp_aerial_pct = (filtered_competition_averages.get("aerial_duels_win__pct") if filtered_competition_averages and filtered_competition_averages.get("aerial_duels_win__pct") is not None else
                                  filtered_competition_averages.get("Aerial Duels Win %") if filtered_competition_averages and filtered_competition_averages.get("Aerial Duels Win %") is not None else
                                  filtered_competition_averages.get("aerial_duels_won_pct") if filtered_competition_averages and filtered_competition_averages.get("aerial_duels_won_pct") is not None else
                                  filtered_competition_averages.get("Aerial Duels Won %") if filtered_competition_averages and filtered_competition_averages.get("Aerial Duels Won %") is not None else
                                  filtered_competition_averages.get("aerial_duels_won__pct") if filtered_competition_averages and filtered_competition_averages.get("aerial_duels_won__pct") is not None else 0) if filtered_competition_averages else 0
                cibao_aerial_pct = (filtered_cibao_averages.get("aerial_duels_win__pct") if filtered_cibao_averages and filtered_cibao_averages.get("aerial_duels_win__pct") is not None else
                                   filtered_cibao_averages.get("Aerial Duels Win %") if filtered_cibao_averages and filtered_cibao_averages.get("Aerial Duels Win %") is not None else
                                   filtered_cibao_averages.get("aerial_duels_won_pct") if filtered_cibao_averages and filtered_cibao_averages.get("aerial_duels_won_pct") is not None else
                                   filtered_cibao_averages.get("Aerial Duels Won %") if filtered_cibao_averages and filtered_cibao_averages.get("Aerial Duels Won %") is not None else
                                   filtered_cibao_averages.get("aerial_duels_won__pct") if filtered_cibao_averages and filtered_cibao_averages.get("aerial_duels_won__pct") is not None else 0) if filtered_cibao_averages else 0
                aerial_pct_display = f"{aerial_duels_won_pct:.1f}%" if aerial_duels_won_pct > 0 else "N/A"
                comp_aerial_pct_display = f"{comp_aerial_pct:.1f}%" if comp_aerial_pct > 0 else "N/A"
                cibao_aerial_pct_display = f"{cibao_aerial_pct:.1f}%" if cibao_aerial_pct > 0 else "N/A"
                display_metric_card(
                    "Duelos Aéreos Ganados %",
                    aerial_pct_display,
                    "",
                    f"Promedio" if aerial_duels_won_pct > 0 else "Datos no disponibles",
                    competition_avg=comp_aerial_pct_display,
                    cibao_avg=cibao_aerial_pct_display
                )
            
            with col4:
                # 8. Counter Attacks
                # Try multiple key variations (check for None explicitly)
                counter_attacks = (display_averages_ui.get("counter_attacks") if display_averages_ui.get("counter_attacks") is not None else
                                  display_averages_ui.get("Counter Attacks") if display_averages_ui.get("Counter Attacks") is not None else
                                  display_averages_ui.get("Counterattacks With Shots") if display_averages_ui.get("Counterattacks With Shots") is not None else 0)
                comp_counter = (filtered_competition_averages.get("counter_attacks") if filtered_competition_averages and filtered_competition_averages.get("counter_attacks") is not None else
                               filtered_competition_averages.get("Counter Attacks") if filtered_competition_averages and filtered_competition_averages.get("Counter Attacks") is not None else
                               filtered_competition_averages.get("Counterattacks With Shots") if filtered_competition_averages and filtered_competition_averages.get("Counterattacks With Shots") is not None else 0) if filtered_competition_averages else 0
                cibao_counter = (filtered_cibao_averages.get("counter_attacks") if filtered_cibao_averages and filtered_cibao_averages.get("counter_attacks") is not None else
                                filtered_cibao_averages.get("Counter Attacks") if filtered_cibao_averages and filtered_cibao_averages.get("Counter Attacks") is not None else
                                filtered_cibao_averages.get("Counterattacks With Shots") if filtered_cibao_averages and filtered_cibao_averages.get("Counterattacks With Shots") is not None else 0) if filtered_cibao_averages else 0
                counter_display = f"{counter_attacks:.1f}" if counter_attacks > 0 else "N/A"
                comp_counter_display = f"{comp_counter:.1f}" if comp_counter > 0 else "N/A"
                cibao_counter_display = f"{cibao_counter:.1f}" if cibao_counter > 0 else "N/A"
                display_metric_card(
                    "Contraataques",
                    counter_display,
                    "",
                    f"Por 90 minutos" if counter_attacks > 0 else "Datos no disponibles",
                    competition_avg=comp_counter_display,
                    cibao_avg=cibao_counter_display
                )
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Fila 3: Passes Accurate %, Long pass %, Shots, Shots Against
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                # 9. Passes Accurate %
                # Try multiple key variations
                passes_accurate_pct = (display_averages_ui.get("pass_accuracy__pct") if display_averages_ui.get("pass_accuracy__pct") is not None else
                                      display_averages_ui.get("Pass Accuracy %") if display_averages_ui.get("Pass Accuracy %") is not None else
                                      display_averages_ui.get("passes_accurate_pct") if display_averages_ui.get("passes_accurate_pct") is not None else 0)
                comp_pa_pct = (filtered_competition_averages.get("pass_accuracy__pct") if filtered_competition_averages and filtered_competition_averages.get("pass_accuracy__pct") is not None else
                              filtered_competition_averages.get("Pass Accuracy %") if filtered_competition_averages and filtered_competition_averages.get("Pass Accuracy %") is not None else
                              filtered_competition_averages.get("passes_accurate_pct") if filtered_competition_averages and filtered_competition_averages.get("passes_accurate_pct") is not None else 0) if filtered_competition_averages else 0
                cibao_pa_pct = (filtered_cibao_averages.get("pass_accuracy__pct") if filtered_cibao_averages and filtered_cibao_averages.get("pass_accuracy__pct") is not None else
                               filtered_cibao_averages.get("Pass Accuracy %") if filtered_cibao_averages and filtered_cibao_averages.get("Pass Accuracy %") is not None else
                               filtered_cibao_averages.get("passes_accurate_pct") if filtered_cibao_averages and filtered_cibao_averages.get("passes_accurate_pct") is not None else 0) if filtered_cibao_averages else 0
                pa_pct_display = f"{passes_accurate_pct:.1f}%" if passes_accurate_pct > 0 else "N/A"
                comp_pa_pct_display = f"{comp_pa_pct:.1f}%" if comp_pa_pct > 0 else "N/A"
                cibao_pa_pct_display = f"{cibao_pa_pct:.1f}%" if cibao_pa_pct > 0 else "N/A"
                display_metric_card(
                    "Precisión de Pases %",
                    pa_pct_display,
                    "",
                    f"Promedio" if passes_accurate_pct > 0 else "Datos no disponibles",
                    competition_avg=comp_pa_pct_display,
                    cibao_avg=cibao_pa_pct_display
                )
            
            with col2:
                # 10. Long pass %
                # Try multiple key variations
                long_pass_pct = (display_averages_ui.get("long_pass_pct") or 
                                display_averages_ui.get("Long pass %") or
                                display_averages_ui.get("long_pass__pct") or 0)
                comp_long_pct = (filtered_competition_averages.get("long_pass_pct") or 
                                filtered_competition_averages.get("Long pass %") or
                                filtered_competition_averages.get("long_pass__pct") or 0) if filtered_competition_averages else 0
                cibao_long_pct = (filtered_cibao_averages.get("long_pass_pct") or 
                                 filtered_cibao_averages.get("Long pass %") or
                                 filtered_cibao_averages.get("long_pass__pct") or 0) if filtered_cibao_averages else 0
                long_pct_display = f"{long_pass_pct:.1f}%" if long_pass_pct > 0 else "N/A"
                comp_long_pct_display = f"{comp_long_pct:.1f}%" if comp_long_pct > 0 else "N/A"
                cibao_long_pct_display = f"{cibao_long_pct:.1f}%" if cibao_long_pct > 0 else "N/A"
                display_metric_card(
                    "Pases Largos %",
                    long_pct_display,
                    "",
                    f"Promedio" if long_pass_pct > 0 else "Datos no disponibles",
                    competition_avg=comp_long_pct_display,
                    cibao_avg=cibao_long_pct_display
                )
            
            with col3:
                # 11. Shots
                shots = display_averages_ui.get("totalScoringAtt", 0)
                comp_shots = filtered_competition_averages.get("totalScoringAtt", 0) if filtered_competition_averages else 0
                cibao_shots = filtered_cibao_averages.get("totalScoringAtt", 0) if filtered_cibao_averages else 0
                display_metric_card(
                    "Disparos",
                    f"{shots:.1f}",
                    "",
                    f"Por 90 minutos",
                    competition_avg=f"{comp_shots:.1f}",
                    cibao_avg=f"{cibao_shots:.1f}"
                )
            
            with col4:
                # 12. Shots Against
                # Try multiple key variations
                shots_against = (display_averages_ui.get("Shots Against") if display_averages_ui.get("Shots Against") is not None else
                                display_averages_ui.get("shots_against") if display_averages_ui.get("shots_against") is not None else 0)
                comp_shots_against = (filtered_competition_averages.get("Shots Against") if filtered_competition_averages and filtered_competition_averages.get("Shots Against") is not None else
                                     filtered_competition_averages.get("shots_against") if filtered_competition_averages and filtered_competition_averages.get("shots_against") is not None else 0) if filtered_competition_averages else 0
                cibao_shots_against = (filtered_cibao_averages.get("Shots Against") if filtered_cibao_averages and filtered_cibao_averages.get("Shots Against") is not None else
                                      filtered_cibao_averages.get("shots_against") if filtered_cibao_averages and filtered_cibao_averages.get("shots_against") is not None else 0) if filtered_cibao_averages else 0
                shots_against_display = f"{shots_against:.1f}" if shots_against > 0 else "N/A"
                comp_shots_against_display = f"{comp_shots_against:.1f}" if comp_shots_against > 0 else "N/A"
                cibao_shots_against_display = f"{cibao_shots_against:.1f}" if cibao_shots_against > 0 else "N/A"
                display_metric_card(
                    "Disparos en Contra",
                    shots_against_display,
                    "",
                    f"Por 90 minutos" if shots_against > 0 else "Datos no disponibles",
                    competition_avg=comp_shots_against_display,
                    cibao_avg=cibao_shots_against_display,
                    higher_is_better=False  # Lower is better
                )
            
            st.markdown("<br>", unsafe_allow_html=True)
        else:
            st.warning("No se pudieron calcular las métricas del equipo.")
    
    # TAB 2: COMPARACIÓN (Gráficos comparativos + Radar Chart)
    if tab2:
        if team_averages and cibao_averages and selected_opponent != CIBAO_TEAM_NAME:
            st.markdown(f"""
            <h2 style='color:#FF9900; text-align:center; margin-top:20px;'>Comparación Directa: {selected_opponent} vs Cibao</h2>
            """, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Filter selector for comparison tab
            comparison_filter = st.radio(
                "Filtrar partidos:",
                options=["Todos los partidos", "Últimos 3 partidos", "Últimos 5 partidos", "En Casa", "Fuera"],
                horizontal=True,
                key="comparison_filter",
                help="Selecciona qué partidos incluir en la comparación"
            )
            
            # Apply filter to matches and calculate averages
            if comparison_filter == "Todos los partidos":
                filtered_team_matches = team_all_matches
                filter_type = "all"
            elif comparison_filter == "Últimos 3 partidos":
                # Get last 3 matches for the selected team by sorting and filtering
                team_filtered = []
                team_name_lower = selected_opponent.lower().strip()
                for match in team_all_matches:
                    match_str = str(match.get("Match", "")).lower()
                    if team_name_lower in match_str:
                        team_filtered.append(match)
                
                # Sort by date (most recent first)
                team_filtered.sort(key=lambda x: (
                    pd.to_datetime(x.get("Date") or x.get("date") or "1900-01-01", errors='coerce')
                ), reverse=True)
                
                # Take last 3
                filtered_team_matches = team_filtered[:3] if len(team_filtered) >= 3 else team_filtered
                filter_type = "all"
            elif comparison_filter == "Últimos 5 partidos":
                # Get last 5 matches for the selected team by sorting and filtering
                team_filtered = []
                team_name_lower = selected_opponent.lower().strip()
                for match in team_all_matches:
                    match_str = str(match.get("Match", "")).lower()
                    if team_name_lower in match_str:
                        team_filtered.append(match)
                
                # Sort by date (most recent first)
                team_filtered.sort(key=lambda x: (
                    pd.to_datetime(x.get("Date") or x.get("date") or "1900-01-01", errors='coerce')
                ), reverse=True)
                
                # Take last 5
                filtered_team_matches = team_filtered[:5] if len(team_filtered) >= 5 else team_filtered
                filter_type = "all"
            elif comparison_filter == "En Casa":
                filtered_team_matches = filter_matches_by_type(team_all_matches, selected_opponent, "home", all_matches)
                filter_type = "home"
            elif comparison_filter == "Fuera":
                filtered_team_matches = filter_matches_by_type(team_all_matches, selected_opponent, "away", all_matches)
                filter_type = "away"
            
            # Recalculate opponent averages with filtered matches
            # Use DataFrame-based filtering (same as Resumen tab) for consistency
            if isinstance(df_liga, pd.DataFrame) and not df_liga.empty and "Team" in df_liga.columns:
                # Filter DataFrame directly for better accuracy (same approach as Resumen tab)
                selected_opponent_normalized = selected_opponent.lower().strip().replace(' fc', '').replace(' fc', '').strip()
                
                # Try exact match first (case-insensitive, strip whitespace)
                filtered_team_df = df_liga[df_liga["Team"].str.lower().str.strip() == selected_opponent.lower().strip()].copy()
                
                # If no exact match, try flexible matching (partial match)
                if filtered_team_df.empty:
                    def team_name_match(team_name):
                        if pd.isna(team_name):
                            return False
                        team_name_normalized = str(team_name).lower().strip().replace(' fc', '').replace(' fc', '').strip()
                        selected_normalized = selected_opponent.lower().strip().replace(' fc', '').replace(' fc', '').strip()
                        # Try various matching strategies
                        # 1. Exact match (already tried above)
                        # 2. Selected name is contained in team name (e.g., "Delfines" in "Delfines Del Este")
                        # 3. Team name is contained in selected name
                        # 4. Handle "Del" vs "De" variations
                        return (selected_normalized in team_name_normalized or 
                               team_name_normalized in selected_normalized or
                               selected_normalized.replace(' del ', ' de ') in team_name_normalized.replace(' del ', ' de ') or
                               team_name_normalized.replace(' del ', ' de ') in selected_normalized.replace(' del ', ' de ') or
                               # Special case: "Delfines" should match "Delfines Del Este"
                               (selected_normalized == "delfines" and "delfines" in team_name_normalized and "del este" in team_name_normalized))
                    
                    filtered_team_df = df_liga[df_liga["Team"].apply(team_name_match)].copy()
                
                # Apply UI filter to the DataFrame
                if comparison_filter != "Todos los partidos":
                    if comparison_filter == "Últimos 3 partidos":
                        # Sort by date and take last 3
                        if "Date" in filtered_team_df.columns:
                            filtered_team_df = filtered_team_df.sort_values("Date", ascending=False).head(3).copy()
                    elif comparison_filter == "Últimos 5 partidos":
                        # Sort by date and take last 5
                        if "Date" in filtered_team_df.columns:
                            filtered_team_df = filtered_team_df.sort_values("Date", ascending=False).head(5).copy()
                    elif comparison_filter == "En Casa":
                        # Filter for home matches
                        if "is_home" in filtered_team_df.columns:
                            filtered_team_df = filtered_team_df[filtered_team_df["is_home"] == True].copy()
                        elif "Match" in filtered_team_df.columns:
                            # Derive is_home from Match string
                            def is_home_match(row):
                                match_str = str(row.get("Match", ""))
                                team_name = str(row.get("Team", "")).strip()
                                if match_str and team_name:
                                    parts = match_str.split(" - ")
                                    if len(parts) >= 2:
                                        home_team = parts[0].strip()
                                        return team_name.lower() in home_team.lower() or home_team.lower() in team_name.lower()
                                return False
                            filtered_team_df = filtered_team_df[filtered_team_df.apply(is_home_match, axis=1)].copy()
                    elif comparison_filter == "Fuera":
                        # Filter for away matches
                        if "is_home" in filtered_team_df.columns:
                            filtered_team_df = filtered_team_df[filtered_team_df["is_home"] == False].copy()
                        elif "Match" in filtered_team_df.columns:
                            # Derive is_home from Match string
                            def is_away_match(row):
                                match_str = str(row.get("Match", ""))
                                team_name = str(row.get("Team", "")).strip()
                                if match_str and team_name:
                                    parts = match_str.split(" - ")
                                    if len(parts) >= 2:
                                        home_team = parts[0].strip()
                                        return not (team_name.lower() in home_team.lower() or home_team.lower() in team_name.lower())
                                return True
                            filtered_team_df = filtered_team_df[filtered_team_df.apply(is_away_match, axis=1)].copy()
                
                # Calculate averages from filtered DataFrame
                filtered_team_averages = calculate_team_averages_from_df(filtered_team_df, selected_opponent, already_filtered=True) if not filtered_team_df.empty else {}
            elif filtered_team_matches:
                # Fallback: convert dicts to DataFrame (less reliable)
                filtered_team_df = pd.DataFrame(filtered_team_matches)
                if not filtered_team_df.empty:
                    # Ensure Team column exists (filtered_team_matches already contains only selected_opponent matches)
                    if "Team" not in filtered_team_df.columns and selected_opponent:
                        filtered_team_df["Team"] = selected_opponent
                    filtered_team_averages = calculate_team_averages_from_df(filtered_team_df, selected_opponent, already_filtered=True)
                else:
                    filtered_team_averages = team_averages
            else:
                filtered_team_averages = team_averages
            
            # For Cibao, filter matches from df_liga (Wyscout data) or all_matches (Scoresway data)
            # Initialize filtered_cibao_averages to ensure it's always set
            filtered_cibao_averages = cibao_averages.copy() if cibao_averages else {}
            
            # Check if we're using Wyscout DataFrame data
            if isinstance(df_liga, pd.DataFrame) and not df_liga.empty and "Team" in df_liga.columns:
                # Filter Cibao matches from DataFrame directly (same approach as opponent)
                cibao_name_normalized = CIBAO_TEAM_NAME.lower().strip().replace(' fc', '').replace(' fc', '').strip()
                
                # Initial filter for Cibao
                filtered_cibao_df_base = df_liga[df_liga["Team"].str.lower().str.strip() == cibao_name_normalized].copy()
                if filtered_cibao_df_base.empty:
                    # Fallback to flexible matching if exact fails
                    filtered_cibao_df_base = df_liga[df_liga["Team"].apply(lambda x: cibao_name_normalized in str(x).lower().strip().replace(' fc', '') or str(x).lower().strip().replace(' fc', '') in cibao_name_normalized)].copy()
                
                # Apply UI filter to the DataFrame (same logic as opponent filtering)
                if comparison_filter == "Últimos 3 partidos":
                    if "Date" in filtered_cibao_df_base.columns:
                        filtered_cibao_df = filtered_cibao_df_base.sort_values("Date", ascending=False).head(3).copy()
                    else:
                        filtered_cibao_df = filtered_cibao_df_base.copy()
                elif comparison_filter == "Últimos 5 partidos":
                    if "Date" in filtered_cibao_df_base.columns:
                        filtered_cibao_df = filtered_cibao_df_base.sort_values("Date", ascending=False).head(5).copy()
                    else:
                        filtered_cibao_df = filtered_cibao_df_base.copy()
                elif comparison_filter == "En Casa":
                    # Filter for home matches
                    if "is_home" in filtered_cibao_df_base.columns:
                        filtered_cibao_df = filtered_cibao_df_base[filtered_cibao_df_base["is_home"] == True].copy()
                    elif "Match" in filtered_cibao_df_base.columns:
                        # Derive is_home from Match string
                        def is_home_match(row):
                            match_str = str(row.get("Match", ""))
                            team_name = str(row.get("Team", "")).strip()
                            if match_str and team_name:
                                parts = match_str.split(" - ")
                                if len(parts) >= 2:
                                    home_team = parts[0].strip()
                                    return team_name.lower() in home_team.lower() or home_team.lower() in team_name.lower()
                            return False
                        filtered_cibao_df = filtered_cibao_df_base[filtered_cibao_df_base.apply(is_home_match, axis=1)].copy()
                    else:
                        filtered_cibao_df = filtered_cibao_df_base.copy()
                elif comparison_filter == "Fuera":
                    # Filter for away matches
                    if "is_home" in filtered_cibao_df_base.columns:
                        filtered_cibao_df = filtered_cibao_df_base[filtered_cibao_df_base["is_home"] == False].copy()
                    elif "Match" in filtered_cibao_df_base.columns:
                        # Derive is_home from Match string
                        def is_away_match(row):
                            match_str = str(row.get("Match", ""))
                            team_name = str(row.get("Team", "")).strip()
                            if match_str and team_name:
                                parts = match_str.split(" - ")
                                if len(parts) >= 2:
                                    home_team = parts[0].strip()
                                    return not (team_name.lower() in home_team.lower() or home_team.lower() in team_name.lower())
                            return True
                        filtered_cibao_df = filtered_cibao_df_base[filtered_cibao_df_base.apply(is_away_match, axis=1)].copy()
                    else:
                        filtered_cibao_df = filtered_cibao_df_base.copy()
                else:  # Todos los partidos
                    filtered_cibao_df = filtered_cibao_df_base.copy()
                
                # Calculate averages from filtered DataFrame
                filtered_cibao_averages = calculate_team_averages_from_df(filtered_cibao_df, CIBAO_TEAM_NAME, already_filtered=True) if not filtered_cibao_df.empty else {}
                if not filtered_cibao_averages:
                    filtered_cibao_averages = cibao_averages.copy() if cibao_averages else {}
            else:
                # Fallback: old Scoresway structure
                cibao_matches_with_stats = []
                for match_data in all_matches:
                    match_info = extract_match_info(match_data)
                    if not match_info:
                        continue
                    
                    home = match_info.get("home_team", "")
                    away = match_info.get("away_team", "")
                    
                    # Check if Cibao plays in this match
                    if CIBAO_TEAM_NAME.lower() in home.lower() or CIBAO_TEAM_NAME.lower() in away.lower():
                        cibao_stats = extract_team_stats_from_match(match_data, CIBAO_TEAM_NAME)
                        if cibao_stats:
                            match_info["cibao_stats"] = cibao_stats
                            match_info["match_data"] = match_data
                            cibao_matches_with_stats.append(match_info)
                
                # Apply filters to Cibao matches
                if comparison_filter == "Últimos 3 partidos":
                    recent_cibao = get_recent_form(cibao_matches_with_stats, CIBAO_TEAM_NAME, num_matches=3)
                    filtered_cibao_matches = []
                    for match in recent_cibao:
                        match_data = match.get("match_data")
                        if match_data:
                            cibao_stats = extract_team_stats_from_match(match_data, CIBAO_TEAM_NAME)
                            if cibao_stats:
                                match["cibao_stats"] = cibao_stats
                                filtered_cibao_matches.append(match)
                elif comparison_filter == "Últimos 5 partidos":
                    recent_cibao = get_recent_form(cibao_matches_with_stats, CIBAO_TEAM_NAME, num_matches=5)
                    filtered_cibao_matches = []
                    for match in recent_cibao:
                        match_data = match.get("match_data")
                        if match_data:
                            cibao_stats = extract_team_stats_from_match(match_data, CIBAO_TEAM_NAME)
                            if cibao_stats:
                                match["cibao_stats"] = cibao_stats
                                filtered_cibao_matches.append(match)
                elif comparison_filter == "En Casa":
                    filtered_cibao_matches = filter_matches_by_type(cibao_matches_with_stats, CIBAO_TEAM_NAME, "home", all_matches)
                elif comparison_filter == "Fuera":
                    filtered_cibao_matches = filter_matches_by_type(cibao_matches_with_stats, CIBAO_TEAM_NAME, "away", all_matches)
                else:  # Todos los partidos
                    filtered_cibao_matches = cibao_matches_with_stats
                
                # Calculate Cibao averages from filtered matches
                if filtered_cibao_matches:
                    # Always recalculate from filtered matches, don't fall back to cibao_averages
                    filtered_cibao_averages = calculate_average_metrics_from_matches(filtered_cibao_matches, "cibao_stats")
                # If empty, keep the initialized value (which is a copy of cibao_averages)
            
            # Use filtered averages for all charts
            comparison_team_averages = filtered_team_averages
            comparison_cibao_averages = filtered_cibao_averages
            
            # Ensure we have valid data for radar chart
            # If averages are empty dict or None, use fallback
            if not comparison_team_averages or (isinstance(comparison_team_averages, dict) and len(comparison_team_averages) == 0):
                comparison_team_averages = team_averages
            
            if not comparison_cibao_averages or (isinstance(comparison_cibao_averages, dict) and len(comparison_cibao_averages) == 0):
                comparison_cibao_averages = cibao_averages
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Radar Chart: Fortalezas y Debilidades (movido desde Resumen)
            st.markdown("""
            <h2 style='color:#FF9900; text-align:center; margin-top:20px;'>Comparación de Fortalezas y Debilidades</h2>
            """, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Selector de métricas para el radar chart
            all_available_metrics = [
                "Goles", "Goles Recibidos", "Disparos", "Disparos al Arco",
                "Posesión", "Precisión Pases", "Pases Totales", "Pases Precisos",
                "Corners", "Tackles Exitosos", "Despejes",
                "Intercepciones", "Faltas", "Tarjetas Amarillas"
            ]
            
            default_metrics = [
                "Goles", "Goles Recibidos", "Disparos", "Posesión",
                "Precisión Pases", "Corners", "Tackles Exitosos", "Despejes"
            ]
            
            selected_radar_metrics = st.multiselect(
                "Seleccionar métricas para comparar:",
                options=all_available_metrics,
                default=default_metrics,
                key="radar_metrics_selector",
                help="Selecciona las métricas que deseas comparar en el gráfico de radar"
            )
            
            if selected_radar_metrics:
                # Usar métricas filtradas del equipo para el radar chart
                radar_fig = create_radar_chart(comparison_team_averages, comparison_cibao_averages, selected_opponent, selected_radar_metrics)
                st.plotly_chart(radar_fig, use_container_width=True)
            else:
                st.info("Selecciona al menos una métrica para mostrar el gráfico de radar.")
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("---")
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Gráficos comparativos dinámicos con selector de métricas
            st.markdown("""
            <h2 style='color:#FF9900; text-align:center; margin-top:20px;'>Comparación de Métricas: {opponent} vs Cibao</h2>
            """.format(opponent=selected_opponent), unsafe_allow_html=True)
            st.markdown(f"""
            <p style='text-align:center; color:#D1D5DB; font-size:16px; margin-bottom:20px;'>
                Compara métricas clave entre <strong>{selected_opponent}</strong> y <strong>Cibao</strong>
            </p>
            """, unsafe_allow_html=True)
            
            # Definir métricas disponibles con sus configuraciones
            available_comparison_metrics = {
                "Goles por 90 min": {
                    "key": "goals",
                    "chart_type": "bar",
                    "unit": "goles",
                    "category": "Ofensiva"
                },
                "Goles Recibidos por 90 min": {
                    "key": "goalsConceded",
                    "chart_type": "bar",
                    "unit": "goles",
                    "category": "Defensiva",
                    "invert": True
                },
                "Disparos por 90 min": {
                    "key": "totalScoringAtt",
                    "chart_type": "bar",
                    "unit": "disparos",
                    "category": "Ofensiva"
                },
                "Disparos al Arco por 90 min": {
                    "key": "ontargetScoringAtt",
                    "chart_type": "bar",
                    "unit": "disparos",
                    "category": "Ofensiva"
                },
                "Precisión de Disparos": {
                    "key": "shotAccuracy",
                    "chart_type": "bar",
                    "unit": "%",
                    "category": "Ofensiva"
                },
                "Posesión": {
                    "key": "possessionPercentage",
                    "chart_type": "bar",
                    "unit": "%",
                    "category": "Control"
                },
                "Pases Totales por 90 min": {
                    "key": "totalPass",
                    "chart_type": "bar",
                    "unit": "pases",
                    "category": "Control"
                },
                "Pases Precisos por 90 min": {
                    "key": "accuratePass",
                    "chart_type": "bar",
                    "unit": "pases",
                    "category": "Control"
                },
                "Precisión de Pases": {
                    "key": "passAccuracy",
                    "chart_type": "bar",
                    "unit": "%",
                    "category": "Control"
                },
                "Corners Ganados por 90 min": {
                    "key": "wonCorners",
                    "chart_type": "bar",
                    "unit": "corners",
                    "category": "Set Pieces"
                },
                "Corners Recibidos por 90 min": {
                    "key": "lostCorners",
                    "chart_type": "bar",
                    "unit": "corners",
                    "category": "Set Pieces",
                    "invert": True
                },
                "Tackles Exitosos por 90 min": {
                    "key": "wonTackle",
                    "chart_type": "bar",
                    "unit": "tackles",
                    "category": "Defensiva"
                },
                "Efectividad de Tackles": {
                    "key": "tackleSuccess",
                    "chart_type": "bar",
                    "unit": "%",
                    "category": "Defensiva"
                },
                "Despejes por 90 min": {
                    "key": "totalClearance",
                    "chart_type": "bar",
                    "unit": "despejes",
                    "category": "Defensiva"
                },
                "Intercepciones por 90 min": {
                    "key": "interception",
                    "chart_type": "bar",
                    "unit": "intercepciones",
                    "category": "Defensiva"
                },
                "Faltas Cometidas por 90 min": {
                    "key": "fkFoulLost",
                    "chart_type": "bar",
                    "unit": "faltas",
                    "category": "Disciplina",
                    "invert": True
                },
                # Note: Faltas Recibidas removed - not available in Wyscout data
                "Tarjetas Amarillas por 90 min": {
                    "key": "totalYellowCard",
                    "chart_type": "bar",
                    "unit": "tarjetas",
                    "category": "Disciplina",
                    "invert": True
                },
                "Tarjetas Rojas por 90 min": {
                    "key": "totalRedCard",
                    "chart_type": "bar",
                    "unit": "tarjetas",
                    "category": "Disciplina",
                    "invert": True
                },
            }
            
            # Agrupar métricas por categoría para mejor organización
            metrics_by_category = {}
            for metric_name, metric_def in available_comparison_metrics.items():
                category = metric_def.get("category", "Otros")
                if category not in metrics_by_category:
                    metrics_by_category[category] = []
                metrics_by_category[category].append(metric_name)
            
            # Crear opciones ordenadas por categoría
            metric_options = []
            for category in sorted(metrics_by_category.keys()):
                metric_options.extend(sorted(metrics_by_category[category]))
            
            # Selector de métricas
            col_selector1, col_selector2 = st.columns([2, 1])
            with col_selector1:
                selected_comparison_metrics = st.multiselect(
                    "Seleccionar métricas para comparar:",
                    options=metric_options,
                    default=["Goles por 90 min", "Posesión", "Precisión de Pases", "Disparos por 90 min"],
                    key="comparison_metrics_selector",
                    help="Selecciona las métricas que deseas comparar entre el oponente y Cibao"
                )
            
            with col_selector2:
                display_mode = st.radio(
                    "Modo de visualización:",
                    ["Individual", "Combinado"],
                    key="comparison_display_mode",
                    help="Individual: un gráfico por métrica | Combinado: todas las métricas en un gráfico"
                )
            
            if selected_comparison_metrics:
                if display_mode == "Individual":
                    # Mostrar un gráfico por cada métrica seleccionada
                    for metric_name in selected_comparison_metrics:
                        if metric_name in available_comparison_metrics:
                            metric_def = available_comparison_metrics[metric_name]
                            metric_key = metric_def["key"]
                            unit = metric_def.get("unit", "")
                            
                            # Obtener valores de las métricas filtradas
                            # Handle both OLD and NEW format column names
                            opponent_val = comparison_team_averages.get(metric_key, 0)
                            cibao_val = comparison_cibao_averages.get(metric_key, 0)
                            
                            # Crear gráfico de barras
                            fig = go.Figure()
                            
                            # Use adaptive text colors
                            opponent_text_color = get_text_color('#FFFFFF')
                            cibao_text_color = get_text_color('#FF8C00')
                            
                            fig.add_trace(go.Bar(
                                name=selected_opponent,
                                x=[metric_name],
                                y=[opponent_val],
                                marker_color='#FFFFFF',
                                text=[f"{opponent_val:.2f}"],
                                textposition='inside',
                                textfont=dict(size=14, color=opponent_text_color, family='Arial Black')
                            ))
                            
                            fig.add_trace(go.Bar(
                                name='Cibao',
                                x=[metric_name],
                                y=[cibao_val],
                                marker_color='#FF8C00',
                                text=[f"{cibao_val:.2f}"],
                                textposition='inside',
                                textfont=dict(size=14, color=cibao_text_color, family='Arial Black')
                            ))
                            
                            fig.update_layout(
                                template='plotly_dark',
                                paper_bgcolor='rgba(0,0,0,0)',
                                plot_bgcolor='rgba(0,0,0,0)',
                                height=300,
                                title=f"{metric_name}",
                                xaxis_title="",
                                yaxis_title=f"Valor ({unit})" if unit else "Valor",
                                showlegend=True,
                                legend=dict(
                                    orientation="h",
                                    yanchor="bottom",
                                    y=1.02,
                                    xanchor="center",
                                    x=0.5,
                                    font=dict(size=14)
                                ),
                                barmode='group',
                                font=dict(size=12, color='white')
                            )
                            
                            st.plotly_chart(fig, use_container_width=True)
                            st.markdown("<br>", unsafe_allow_html=True)
                else:
                    # Modo combinado: todas las métricas en un gráfico
                    # First, collect all metrics and their values
                    all_metrics_data = []
                    for metric_name in selected_comparison_metrics:
                        if metric_name in available_comparison_metrics:
                            metric_key = available_comparison_metrics[metric_name]["key"]
                            opponent_val = comparison_team_averages.get(metric_key, 0)
                            cibao_val = comparison_cibao_averages.get(metric_key, 0)
                            max_val = max(abs(opponent_val), abs(cibao_val))
                            all_metrics_data.append({
                                "name": metric_name,
                                "key": metric_key,
                                "opponent_val": opponent_val,
                                "cibao_val": cibao_val,
                                "max_val": max_val
                            })
                    
                    if all_metrics_data:
                        # Find the overall maximum value across all metrics
                        overall_max = max([m["max_val"] for m in all_metrics_data]) if all_metrics_data else 1
                        
                        # Separate metrics into large-scale (for combined chart) and small-scale (for individual charts)
                        # A metric is considered "small-scale" if its max value is less than 5% of the overall max
                        threshold = overall_max * 0.05
                        large_scale_metrics = []
                        small_scale_metrics = []
                        
                        for metric_data in all_metrics_data:
                            if metric_data["max_val"] < threshold and overall_max > 0:
                                small_scale_metrics.append(metric_data)
                            else:
                                large_scale_metrics.append(metric_data)
                        
                        # Create combined chart with large-scale metrics
                        if large_scale_metrics:
                            categories = [m["name"] for m in large_scale_metrics]
                            opponent_vals = [m["opponent_val"] for m in large_scale_metrics]
                            cibao_vals = [m["cibao_val"] for m in large_scale_metrics]
                            
                            fig = go.Figure()
                            
                            # Use adaptive text colors
                            opponent_text_color = get_text_color('#FFFFFF')
                            cibao_text_color = get_text_color('#FF8C00')
                            
                            fig.add_trace(go.Bar(
                                name=selected_opponent,
                                x=categories,
                                y=opponent_vals,
                                marker_color='#FFFFFF',
                                marker_line=dict(width=0),
                                text=[f"{v:.2f}" for v in opponent_vals],
                                textposition='inside',
                                textfont=dict(size=14, color=opponent_text_color, family='Arial Black')
                            ))
                            
                            fig.add_trace(go.Bar(
                                name='Cibao',
                                x=categories,
                                y=cibao_vals,
                                marker_color='#FF8C00',
                                marker_line=dict(width=0),
                                text=[f"{v:.2f}" for v in cibao_vals],
                                textposition='inside',
                                textfont=dict(size=14, color=cibao_text_color, family='Arial Black')
                            ))
                            
                            fig.update_layout(
                                template='plotly_dark',
                                paper_bgcolor='rgba(0,0,0,0)',
                                plot_bgcolor='rgba(0,0,0,0)',
                                height=400,
                                margin=dict(t=80, b=100, l=50, r=50),  # Increased bottom margin for horizontal labels on mobile
                                title="Comparación de Múltiples Métricas",
                                xaxis_title="Métricas",
                                yaxis_title="Valor",
                                barmode='group',
                                legend=dict(
                                    orientation="h",
                                    yanchor="bottom",
                                    y=1.02,
                                    xanchor="center",
                                    x=0.5,
                                    font=dict(size=14)
                                ),
                                xaxis=dict(tickangle=0, tickfont=dict(size=12)),  # Horizontal labels for better mobile experience
                                font=dict(size=12, color='white')
                            )
                            
                            st.plotly_chart(fig, use_container_width=True)
                        
                        # Create individual charts for small-scale metrics
                        if small_scale_metrics:
                            st.markdown("<br>", unsafe_allow_html=True)
                            st.markdown("""
                            <h3 style='color:#FF9900; margin-top:20px;'>Métricas con Escala Diferente</h3>
                            <p style='color:#D1D5DB; font-size:14px; margin-bottom:15px;'>
                                Las siguientes métricas se muestran por separado debido a su escala diferente:
                            </p>
                            """, unsafe_allow_html=True)
                            
                            # Use adaptive text colors
                            opponent_text_color = get_text_color('#FFFFFF')
                            cibao_text_color = get_text_color('#FF8C00')
                            
                            for metric_data in small_scale_metrics:
                                metric_name = metric_data["name"]
                                metric_def = available_comparison_metrics[metric_name]
                                unit = metric_def.get("unit", "")
                                
                                fig = go.Figure()
                                
                                fig.add_trace(go.Bar(
                                    name=selected_opponent,
                                    x=[metric_name],
                                    y=[metric_data["opponent_val"]],
                                    marker_color='#FFFFFF',
                                    marker_line=dict(width=0),
                                    text=[f"{metric_data['opponent_val']:.2f}"],
                                    textposition='inside',
                                    textfont=dict(size=14, color=opponent_text_color, family='Arial Black')
                                ))
                                
                                fig.add_trace(go.Bar(
                                    name='Cibao',
                                    x=[metric_name],
                                    y=[metric_data["cibao_val"]],
                                    marker_color='#FF8C00',
                                    marker_line=dict(width=0),
                                    text=[f"{metric_data['cibao_val']:.2f}"],
                                    textposition='inside',
                                    textfont=dict(size=14, color=cibao_text_color, family='Arial Black')
                                ))
                                
                                fig.update_layout(
                                    template='plotly_dark',
                                    paper_bgcolor='rgba(0,0,0,0)',
                                    plot_bgcolor='rgba(0,0,0,0)',
                                    height=300,
                                    title=f"{metric_name}",
                                    xaxis_title="",
                                    yaxis_title=f"Valor ({unit})" if unit else "Valor",
                                    showlegend=True,
                                    legend=dict(
                                        orientation="h",
                                        yanchor="bottom",
                                        y=1.02,
                                        xanchor="center",
                                        x=0.5,
                                        font=dict(size=14)
                                    ),
                                    barmode='group',
                                    font=dict(size=12, color='white')
                                )
                                
                                st.plotly_chart(fig, use_container_width=True)
                                st.markdown("<br>", unsafe_allow_html=True)
            else:
                st.info("Selecciona al menos una métrica para mostrar la comparación.")
            
            # ========== SECCIÓN: DISCIPLINE COMPARISON ==========
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("---")
            st.markdown("""
            <h2 style='color:#FF9900; text-align:center; margin-top:20px;'>Análisis de Disciplina</h2>
            """, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Get discipline metrics - try multiple column name variations
            opp_yellow = (comparison_team_averages.get("totalYellowCard") or 
                         comparison_team_averages.get("Yellow Cards") or 
                         comparison_team_averages.get("Yellow Cards Per 90") or 
                         comparison_team_averages.get("yellow_cards") or 0)
            opp_red = (comparison_team_averages.get("totalRedCard") or 
                      comparison_team_averages.get("Red Cards") or 
                      comparison_team_averages.get("Red Cards Per 90") or 
                      comparison_team_averages.get("red_cards") or 0)
            opp_fouls_committed = comparison_team_averages.get("fkFoulLost", 0)
            opp_fouls_won = comparison_team_averages.get("fkFoulWon", 0)
            
            cibao_yellow = (comparison_cibao_averages.get("totalYellowCard") or 
                           comparison_cibao_averages.get("Yellow Cards") or 
                           comparison_cibao_averages.get("Yellow Cards Per 90") or 
                           comparison_cibao_averages.get("yellow_cards") or 0)
            cibao_red = (comparison_cibao_averages.get("totalRedCard") or 
                        comparison_cibao_averages.get("Red Cards") or 
                        comparison_cibao_averages.get("Red Cards Per 90") or 
                        comparison_cibao_averages.get("red_cards") or 0)
            cibao_fouls_committed = comparison_cibao_averages.get("fkFoulLost", 0)
            cibao_fouls_won = comparison_cibao_averages.get("fkFoulWon", 0)
            
            # KPI Cards for Discipline
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Tarjetas Amarillas", f"{opp_yellow:.1f}")
            with col2:
                st.metric("Tarjetas Rojas", f"{opp_red:.1f}")
            with col3:
                st.metric("Faltas Cometidas", f"{opp_fouls_committed:.1f}")
            with col4:
                # Empty column - Faltas Recibidas not available in Wyscout data
                st.empty()
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Use adaptive text colors
            opponent_text_color = get_text_color('#FFFFFF')
            cibao_text_color = get_text_color('#FF8C00')
            
            # Two charts side by side
            col1, col2 = st.columns(2)
            
            # Chart 1: Cards
            with col1:
                card_categories = ["Tarjetas\nAmarillas"]
                opponent_card_vals = [opp_yellow]
                cibao_card_vals = [cibao_yellow]
                
                # Calculate max value to determine if bars are too small
                all_card_values = [v for v in opponent_card_vals + cibao_card_vals if v is not None and v > 0]
                max_card_val = max(all_card_values) if all_card_values else 1
                threshold = max_card_val * 0.05
                
                # Determine text position and color for each bar
                opp_card_positions = ['outside' if v < threshold else 'inside' for v in opponent_card_vals]
                opp_card_colors = ['white' if v < threshold else opponent_text_color for v in opponent_card_vals]
                cibao_card_positions = ['outside' if v < threshold else 'inside' for v in cibao_card_vals]
                cibao_card_colors = ['white' if v < threshold else cibao_text_color for v in cibao_card_vals]
                
                fig_cards = go.Figure()
                fig_cards.add_trace(go.Bar(
                    name=selected_opponent,
                    x=card_categories,
                    y=opponent_card_vals,
                    marker_color='#FFFFFF',
                    marker_line=dict(width=0),
                    text=[f"{v:.1f}" for v in opponent_card_vals],
                    textposition=opp_card_positions,
                    textfont=dict(size=14, color=opp_card_colors, family='Arial Black')
                ))
                
                fig_cards.add_trace(go.Bar(
                    name='Cibao',
                    x=card_categories,
                    y=cibao_card_vals,
                    marker_color='#FF8C00',
                    marker_line=dict(width=0),
                    text=[f"{v:.1f}" for v in cibao_card_vals],
                    textposition=cibao_card_positions,
                    textfont=dict(size=14, color=cibao_card_colors, family='Arial Black')
                ))
                
                # Set y-axis range to ensure bars are visible even when values are 0
                max_card_display = max(max(opponent_card_vals), max(cibao_card_vals)) if opponent_card_vals or cibao_card_vals else 1
                yaxis_range = [0, max(max_card_display * 1.1, 0.5)]  # At least 0.5 range to show bars
                
                fig_cards.update_layout(
                    template='plotly_dark',
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    height=400,
                    title="Tarjetas",
                    xaxis_title="",  # Remove "Tipo de Tarjeta" label
                    yaxis_title="Promedio por 90 min",
                    yaxis=dict(range=yaxis_range),  # Set explicit range
                    barmode='group',
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="center",
                        x=0.5,
                        font=dict(size=14)
                    ),
                    font=dict(size=12, color='white')
                )
                
                st.plotly_chart(fig_cards, use_container_width=True)
            
            # Chart 2: Fouls (only Faltas Cometidas - Wyscout doesn't provide Faltas Recibidas)
            with col2:
                foul_categories = ["Faltas\nCometidas"]
                opponent_foul_vals = [opp_fouls_committed]
                cibao_foul_vals = [cibao_fouls_committed]
                
                # Calculate max value to determine if bars are too small
                all_foul_values = [v for v in opponent_foul_vals + cibao_foul_vals if v is not None and v > 0]
                max_foul_val = max(all_foul_values) if all_foul_values else 1
                threshold = max_foul_val * 0.05
                
                # Determine text position and color for each bar
                opp_foul_positions = ['outside' if v < threshold else 'inside' for v in opponent_foul_vals]
                opp_foul_colors = ['white' if v < threshold else opponent_text_color for v in opponent_foul_vals]
                cibao_foul_positions = ['outside' if v < threshold else 'inside' for v in cibao_foul_vals]
                cibao_foul_colors = ['white' if v < threshold else cibao_text_color for v in cibao_foul_vals]
                
                fig_fouls = go.Figure()
                fig_fouls.add_trace(go.Bar(
                    name=selected_opponent,
                    x=foul_categories,
                    y=opponent_foul_vals,
                    marker_color='#FFFFFF',
                    marker_line=dict(width=0),
                    text=[f"{v:.1f}" for v in opponent_foul_vals],
                    textposition=opp_foul_positions,
                    textfont=dict(size=14, color=opp_foul_colors, family='Arial Black')
                ))
                
                fig_fouls.add_trace(go.Bar(
                    name='Cibao',
                    x=foul_categories,
                    y=cibao_foul_vals,
                    marker_color='#FF8C00',
                    marker_line=dict(width=0),
                    text=[f"{v:.1f}" for v in cibao_foul_vals],
                    textposition=cibao_foul_positions,
                    textfont=dict(size=14, color=cibao_foul_colors, family='Arial Black')
                ))
                
                fig_fouls.update_layout(
                    template='plotly_dark',
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    height=400,
                    title="Faltas Cometidas",
                    xaxis_title="",
                    yaxis_title="Promedio por 90 min",
                    barmode='group',
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="center",
                        x=0.5,
                        font=dict(size=14)
                    ),
                    font=dict(size=12, color='white')
                )
                
                st.plotly_chart(fig_fouls, use_container_width=True)
            
            # ========== SECCIÓN: OFFSIDE ANALYSIS ==========
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("---")
            st.markdown("""
            <h2 style='color:#FF9900; text-align:center; margin-top:20px;'>Análisis de Fuera de Juego</h2>
            """, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Get offside data from 'Offsides' column
            opp_offsides = comparison_team_averages.get("offsides", 0)
            cibao_offsides = comparison_cibao_averages.get("offsides", 0)
            
            # KPI Cards for Offsides
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric(f"Fuera de Juego ({selected_opponent})", f"{opp_offsides:.1f}")
            with col2:
                st.metric("Fuera de Juego (Cibao)", f"{cibao_offsides:.1f}")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Offside Comparison Chart
            categories = ["Fuera de Juego"]
            opponent_vals = [opp_offsides]
            cibao_vals = [cibao_offsides]
            
            # Calculate max value to determine if bars are too small
            all_offside_values = [v for v in opponent_vals + cibao_vals if v is not None and v > 0]
            max_offside_val = max(all_offside_values) if all_offside_values else 1
            threshold = max_offside_val * 0.05
            
            # Determine text position and color for each bar
            opp_offside_positions = ['outside' if v < threshold else 'inside' for v in opponent_vals]
            opp_offside_colors = ['white' if v < threshold else opponent_text_color for v in opponent_vals]
            cibao_offside_positions = ['outside' if v < threshold else 'inside' for v in cibao_vals]
            cibao_offside_colors = ['white' if v < threshold else cibao_text_color for v in cibao_vals]
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                name=selected_opponent,
                x=categories,
                y=opponent_vals,
                marker_color='#FFFFFF',
                marker_line=dict(width=0),
                text=[f"{v:.1f}" for v in opponent_vals],
                textposition=opp_offside_positions,
                textfont=dict(size=14, color=opp_offside_colors, family='Arial Black')
            ))
            
            fig.add_trace(go.Bar(
                name='Cibao',
                x=categories,
                y=cibao_vals,
                marker_color='#FF8C00',
                marker_line=dict(width=0),
                text=[f"{v:.1f}" for v in cibao_vals],
                textposition=cibao_offside_positions,
                textfont=dict(size=14, color=cibao_offside_colors, family='Arial Black')
            ))
            
            fig.update_layout(
                template='plotly_dark',
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                height=400,
                title="Comparación de Fuera de Juego",
                xaxis_title="",
                yaxis_title="Promedio por 90 min",
                barmode='group',
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="center",
                    x=0.5,
                    font=dict(size=14)
                ),
                font=dict(size=12, color='white')
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Add insights
            st.markdown("<br>", unsafe_allow_html=True)
            if opp_offsides > cibao_offsides * 1.2:
                st.info(f"**{selected_opponent} tiene más fuera de juego** ({opp_offsides:.1f} vs {cibao_offsides:.1f} de Cibao). Esto puede indicar un juego más agresivo o una línea defensiva más alta del oponente.")
            elif cibao_offsides > opp_offsides * 1.2:
                st.info(f"**Cibao tiene más fuera de juego** ({cibao_offsides:.1f} vs {opp_offsides:.1f} del oponente). El oponente mantiene mejor la línea defensiva.")
            else:
                st.info(f"**Niveles similares de fuera de juego** ({opp_offsides:.1f} vs {cibao_offsides:.1f} de Cibao).")
            
            # Player Offside Analysis Table removed
            
            # Get team color for opponent (for charts) - always white in comparison tab
            opponent_color = '#FFFFFF'  # Always white for opponent in comparison tab
            
            opp_text_color = get_text_color(opponent_color)
            cibao_text_color = get_text_color(CIBAO_COLOR)
            
            # Substitution section removed - not available in Wyscout data
            
            # ========== SECCIÓN: POSSESSION PATTERNS ==========
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("---")
            st.markdown("""
            <h2 style='color:#FF9900; text-align:center; margin-top:20px;'>Patrones de Posesión</h2>
            """, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Get possession data - try multiple keys
            opp_possession = (comparison_team_averages.get("possessionPercentage") or 
                            comparison_team_averages.get("Possession %") or 
                            comparison_team_averages.get("Possession, %") or 
                            comparison_team_averages.get("possession_pct") or 0)
            cibao_possession = (comparison_cibao_averages.get("possessionPercentage") or 
                              comparison_cibao_averages.get("Possession %") or 
                              comparison_cibao_averages.get("Possession, %") or 
                              comparison_cibao_averages.get("possession_pct") or 0)
            
            # KPI Cards for Possession
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric(f"Posesión ({selected_opponent})", f"{opp_possession:.1f}%")
            with col2:
                st.metric("Posesión (Cibao)", f"{cibao_possession:.1f}%")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Possession Comparison Chart
            categories = ["Posesión %"]
            opponent_vals = [opp_possession]
            cibao_vals = [cibao_possession]
            
            # Calculate max value to determine if bars are too small
            all_possession_values = [v for v in opponent_vals + cibao_vals if v is not None and v > 0]
            max_possession_val = max(all_possession_values) if all_possession_values else 1
            threshold = max_possession_val * 0.05
            
            # Determine text position and color for each bar
            opp_possession_positions = ['outside' if v < threshold else 'inside' for v in opponent_vals]
            opp_possession_colors = ['white' if v < threshold else opp_text_color for v in opponent_vals]
            cibao_possession_positions = ['outside' if v < threshold else 'inside' for v in cibao_vals]
            cibao_possession_colors = ['white' if v < threshold else cibao_text_color for v in cibao_vals]
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                name=selected_opponent,
                x=categories,
                y=opponent_vals,
                marker_color=opponent_color,
                marker_line=dict(width=0),
                text=[f"{v:.1f}%" for v in opponent_vals],
                textposition=opp_possession_positions,
                textfont=dict(color=opp_possession_colors, size=14, family='Arial Black')
            ))
            fig.add_trace(go.Bar(
                name="Cibao",
                x=categories,
                y=cibao_vals,
                marker_color=CIBAO_COLOR,
                marker_line=dict(width=0),
                text=[f"{v:.1f}%" for v in cibao_vals],
                textposition=cibao_possession_positions,
                textfont=dict(color=cibao_possession_colors, size=14, family='Arial Black')
            ))
            
            fig.update_layout(
                template='plotly_dark',
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                height=400,
                title="Comparación de Posesión",
                xaxis_title="",
                yaxis_title="Porcentaje de Posesión",
                barmode='group',
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="center",
                    x=0.5,
                    font=dict(size=14)
                ),
                font=dict(size=12, color='white')
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Add insights
            st.markdown("<br>", unsafe_allow_html=True)
            if opp_possession > cibao_possession + 10:
                st.info(f"**{selected_opponent} domina más la posesión** ({opp_possession:.1f}% vs {cibao_possession:.1f}% de Cibao). Preparar estrategia de contraataque y presión alta.")
            elif cibao_possession > opp_possession + 10:
                st.info(f"**Cibao domina más la posesión** ({cibao_possession:.1f}% vs {opp_possession:.1f}% del oponente). Mantener control del juego y ritmo.")
            else:
                st.info(f"**Posesión equilibrada** ({opp_possession:.1f}% vs {cibao_possession:.1f}% de Cibao). El partido será disputado en el centro del campo.")
            
            # ========== SECCIÓN: PASSING STATS ==========
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("---")
            st.markdown("""
            <h2 style='color:#FF9900; text-align:center; margin-top:20px;'>Estadísticas de Pases</h2>
            """, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Get passing data from processed columns (NEW FORMAT):
            # "Passes" → maps to "totalPass" (total passes)
            # "Passes Accurate" → maps to "accuratePass" (accurate passes count)
            # "Passes Accurate %" → maps to "passes_accurate_pct" (pass accuracy percentage)
            # Column 2: "Passes Accurate" → maps to "accuratePass" (accurate passes count) - FIXED!
            # Column 3: "Passes Accurate %" → maps to "passes_accurate_pct" (pass accuracy percentage)
            
            # Try multiple key variations to find the data (mapped, original, normalized)
            opp_total_passes = (comparison_team_averages.get("totalPass") or 
                               comparison_team_averages.get("Passes") or 0)
            if opp_total_passes == 0:
                # Try normalized name
                opp_total_passes = comparison_team_averages.get("passes", 0)
            
            # For accurate passes, check mapped key "accuratePass" (from "Passes Accurate") - FIXED!
            opp_accurate_passes = (comparison_team_averages.get("accuratePass") or 
                                  comparison_team_averages.get("Passes Accurate") or 0)
            if opp_accurate_passes == 0:
                # Try normalized name
                opp_accurate_passes = comparison_team_averages.get("passes_accurate", 0)
            
            # For pass accuracy percentage, use the direct column "Passes Accurate %" → "passes_accurate_pct"
            opp_pass_accuracy = (comparison_team_averages.get("passes_accurate_pct") or
                                comparison_team_averages.get("Passes Accurate %") or 0)
            if not opp_pass_accuracy or opp_pass_accuracy == 0:
                # Calculate if we have both total and accurate
                if opp_total_passes > 0 and opp_accurate_passes > 0:
                    opp_pass_accuracy = (opp_accurate_passes / opp_total_passes * 100)
            
            # Same for Cibao (NEW FORMAT only)
            cibao_total_passes = (comparison_cibao_averages.get("totalPass") or 
                                 comparison_cibao_averages.get("Passes") or 0)
            if cibao_total_passes == 0:
                cibao_total_passes = comparison_cibao_averages.get("passes", 0)
            
            # For accurate passes (NEW FORMAT only)
            cibao_accurate_passes = (comparison_cibao_averages.get("accuratePass") or 
                                    comparison_cibao_averages.get("Passes Accurate") or 0)
            if cibao_accurate_passes == 0:
                cibao_accurate_passes = comparison_cibao_averages.get("passes_accurate", 0)
            
            cibao_pass_accuracy = (comparison_cibao_averages.get("passes_accurate_pct") or
                                   comparison_cibao_averages.get("Passes Accurate %") or
                                   comparison_cibao_averages.get("Pass Accuracy %") or 0)
            if not cibao_pass_accuracy or cibao_pass_accuracy == 0:
                if cibao_total_passes > 0 and cibao_accurate_passes > 0:
                    cibao_pass_accuracy = (cibao_accurate_passes / cibao_total_passes * 100)
            
            # KPI Cards for Passing
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(f"Pases Totales ({selected_opponent})", f"{opp_total_passes:.0f}")
            with col2:
                st.metric("Pases Totales (Cibao)", f"{cibao_total_passes:.0f}")
            with col3:
                st.metric(f"Precisión ({selected_opponent})", f"{opp_pass_accuracy:.1f}%")
            with col4:
                st.metric("Precisión (Cibao)", f"{cibao_pass_accuracy:.1f}%")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Passing Comparison Chart
            categories = ["Pases Totales", "Pases Precisos", "Precisión %"]
            opponent_vals = [opp_total_passes, opp_accurate_passes, opp_pass_accuracy]
            cibao_vals = [cibao_total_passes, cibao_accurate_passes, cibao_pass_accuracy]
            
            # Normalize values for display (passes in hundreds, accuracy as percentage)
            opp_display_vals = [opp_total_passes, opp_accurate_passes, opp_pass_accuracy]
            cibao_display_vals = [cibao_total_passes, cibao_accurate_passes, cibao_pass_accuracy]
            
            # Calculate max value to determine if bars are too small
            all_pass_values = [v for v in opp_display_vals + cibao_display_vals if v is not None and v > 0]
            max_pass_val = max(all_pass_values) if all_pass_values else 1
            threshold = max_pass_val * 0.05
            
            # Determine text position and color for each bar
            opp_pass_positions = ['outside' if v < threshold else 'inside' for v in opp_display_vals]
            opp_pass_colors = ['white' if v < threshold else opp_text_color for v in opp_display_vals]
            cibao_pass_positions = ['outside' if v < threshold else 'inside' for v in cibao_display_vals]
            cibao_pass_colors = ['white' if v < threshold else cibao_text_color for v in cibao_display_vals]
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                name=selected_opponent,
                x=categories,
                y=opp_display_vals,
                marker_color=opponent_color,
                marker_line=dict(width=0),
                text=[f"{v:.0f}" if i < 2 else f"{v:.1f}%" for i, v in enumerate(opp_display_vals)],
                textposition=opp_pass_positions,
                textfont=dict(color=opp_pass_colors, size=14, family='Arial Black')
            ))
            fig.add_trace(go.Bar(
                name="Cibao",
                x=categories,
                y=cibao_display_vals,
                marker_color=CIBAO_COLOR,
                marker_line=dict(width=0),
                text=[f"{v:.0f}" if i < 2 else f"{v:.1f}%" for i, v in enumerate(cibao_display_vals)],
                textposition=cibao_pass_positions,
                textfont=dict(color=cibao_pass_colors, size=14, family='Arial Black')
            ))
            
            fig.update_layout(
                template='plotly_dark',
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                height=400,
                title="Comparación de Pases",
                xaxis_title="Métrica",
                yaxis_title="Valor",
                barmode='group',
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="center",
                    x=0.5,
                    font=dict(size=14)
                ),
                font=dict(size=12, color='white')
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Add insights
            st.markdown("<br>", unsafe_allow_html=True)
            if opp_pass_accuracy > cibao_pass_accuracy + 5:
                st.info(f"**{selected_opponent} tiene mejor precisión de pases** ({opp_pass_accuracy:.1f}% vs {cibao_pass_accuracy:.1f}% de Cibao). Presionar alto para interrumpir su juego de pases.")
            elif cibao_pass_accuracy > opp_pass_accuracy + 5:
                st.info(f"**Cibao tiene mejor precisión de pases** ({cibao_pass_accuracy:.1f}% vs {opp_pass_accuracy:.1f}% del oponente). Aprovechar la ventaja en construcción de juego.")
            else:
                st.info(f"**Precisión de pases similar** ({opp_pass_accuracy:.1f}% vs {cibao_pass_accuracy:.1f}% de Cibao).")
            
            if opp_total_passes > cibao_total_passes * 1.2:
                st.info(f"**{selected_opponent} juega más pases** ({opp_total_passes:.0f} vs {cibao_total_passes:.0f} de Cibao). Equipo más orientado a la posesión.")
            elif cibao_total_passes > opp_total_passes * 1.2:
                st.info(f"**Cibao juega más pases** ({cibao_total_passes:.0f} vs {opp_total_passes:.0f} del oponente). Mayor construcción de juego.")
        elif selected_opponent == CIBAO_TEAM_NAME:
            st.info("Selecciona otro equipo para ver comparación con Cibao")
        else:
            st.warning("No se pudieron calcular las métricas para la comparación.")
    
    # TAB 4: ANÁLISIS TÁCTICO Y FASES (Consolidado)
    if tab4:
        if not selected_opponent:
            st.info(" **Selecciona un equipo desde el selector en la barra lateral** para ver su análisis táctico y fases del partido.")
        elif selected_opponent:
            # Reload colors directly from CSV - this is the source of truth
            current_colors = load_team_colors()
            
            # Get team color DIRECTLY from CSV with comprehensive matching
            # IMPORTANT: On tactical analysis tab, we're analyzing the OPPONENT, so use opponent's color
            team_color = None
            normalized_name = selected_opponent.strip()
            
            # Create multiple variations of the team name to try matching
            name_variations = [
                normalized_name,  # Original
                normalized_name.lower(),  # Lowercase
                normalized_name.replace(' FC', '').strip(),  # Remove " FC"
                normalized_name.replace(' FC', '').strip().lower(),  # Remove " FC" + lowercase
                normalized_name.replace(' ', '').lower(),  # Remove spaces + lowercase
                normalized_name.replace(' FC', '').replace(' ', '').lower(),  # Remove " FC" and spaces + lowercase
            ]
            
            # Try each variation until we find a match
            matched_variation = None
            for variation in name_variations:
                if variation in current_colors:
                    team_color = current_colors[variation]
                    matched_variation = variation
                    break
            
            # If still no match, try partial matching (but skip Cibao)
            if not team_color:
                normalized_lower = normalized_name.lower().replace(' fc', '').strip()
                for csv_team, color in current_colors.items():
                    csv_team_lower = csv_team.lower()
                    # Skip Cibao variations to avoid false matches
                    if 'cibao' in csv_team_lower:
                        continue
                    # Try matching core team names (remove common suffixes)
                    csv_core = csv_team_lower.replace(' fc', '').replace(' ', '').strip()
                    name_core = normalized_lower.replace(' ', '').strip()
                    if csv_core == name_core or (len(csv_core) >= 5 and csv_core in name_core) or (len(name_core) >= 5 and name_core in csv_core):
                        team_color = color
                        break
            
            # Final fallback: use default gray (NOT white, NOT Cibao's color)
            if not team_color:
                team_color = "#CCCCCC"
            
            # Ensure team_color has # prefix
            if team_color and not team_color.startswith('#'):
                team_color = '#' + team_color
            
            # CRITICAL SAFETY CHECK: Never use Cibao's color for non-Cibao teams
            # Get Cibao's actual color from CSV to compare
            cibao_csv_color = current_colors.get('Cibao', CIBAO_COLOR)
            if not cibao_csv_color.startswith('#'):
                cibao_csv_color = '#' + cibao_csv_color
            
            if selected_opponent != CIBAO_TEAM_NAME and team_color == cibao_csv_color:
                # This should never happen, but if it does, force gray
                team_color = "#CCCCCC"
            
            # Check if we have Wyscout DataFrame data (team_df) or Scoresway JSON data (all_matches)
            has_wyscout_data = isinstance(team_df, pd.DataFrame) and not team_df.empty
            has_scoresway_data = all_matches and len(all_matches) > 0
            
            # For Wyscout data, we can proceed directly with team_df
            # For Scoresway data, we need to process matches
            if has_wyscout_data:
                # Wyscout data: use team_df directly, no need to check played_matches
                played_matches = []  # Empty for Wyscout, we use team_df instead
            else:
                # Scoresway data: process matches
                if selected_opponent == CIBAO_TEAM_NAME:
                    team_matches = get_opponent_matches_data(all_matches, CIBAO_TEAM_NAME)
                else:
                    team_matches = get_opponent_matches_data(all_matches, selected_opponent)
                
                # Prepare matches with data
                matches_with_data = []
                for match_info in team_matches:
                    match_id = match_info.get("match_id", "")
                    for match_data in all_matches:
                        match_info_check = extract_match_info(match_data)
                        if match_info_check and match_info_check.get("match_id") == match_id:
                            matches_with_data.append({
                                **match_info,
                                "match_data": match_data
                            })
                            break
                
                # Only played matches
                played_matches = [m for m in matches_with_data if m.get("status", "").lower() in ["played", "finished", "ft", "jugado", "finalizado"]]
            
            # Show content if we have either Wyscout data or played matches
            if not has_wyscout_data and not played_matches:
                st.info("No hay partidos jugados disponibles para este equipo.")
            else:
                st.markdown(f"""
                <h2 style='color:#FF9900; text-align:center; margin-top:20px;'>Análisis Táctico y Fases del Partido — {selected_opponent}</h2>
                """, unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)
                
                # Calculate team averages for tactical analysis
                if isinstance(team_df, pd.DataFrame) and not team_df.empty:
                    tactical_team_averages = calculate_team_averages_from_df(team_df, selected_opponent)
                    # Calculate competition averages for comparison
                    tactical_competition_averages = calculate_competition_averages(df_liga)
                    # Calculate Cibao averages for comparison
                    tactical_cibao_averages = calculate_team_averages_from_df(df_liga, CIBAO_TEAM_NAME)
                else:
                    tactical_team_averages = {}
                    tactical_competition_averages = {}
                
                # ========== SECCIÓN 1.5: PLAYING STYLE PROFILE ==========
                st.markdown("---")
                st.markdown("""
                <h3 style='color:#FF9900; margin-top:20px;'>Perfil de Estilo de Juego</h3>
                """, unsafe_allow_html=True)
                
                if tactical_team_averages and isinstance(team_df, pd.DataFrame) and not team_df.empty:
                    # Get key metrics for playing style
                    possession = tactical_team_averages.get("possessionPercentage", 0) or tactical_team_averages.get("Possession, %", 0) or 0
                    long_passes = tactical_team_averages.get("longPasses", 0) or tactical_team_averages.get("Long Passes", 0) or 0
                    crosses = tactical_team_averages.get("crosses", 0) or tactical_team_averages.get("Crosses", 0) or 0
                    ppda = tactical_team_averages.get("ppda", 0) or tactical_team_averages.get("PPDA", 0) or 0
                    match_tempo = (tactical_team_averages.get("Match Tempo") or 
                                  tactical_team_averages.get("match_tempo") or 
                                  tactical_team_averages.get("Average passes per possession") or 0)
                    
                    # Competition averages
                    comp_possession = tactical_competition_averages.get("possessionPercentage", 0) or tactical_competition_averages.get("Possession, %", 0) or 0
                    comp_long_passes = tactical_competition_averages.get("longPasses", 0) or tactical_competition_averages.get("Long Passes", 0) or 0
                    comp_crosses = tactical_competition_averages.get("crosses", 0) or tactical_competition_averages.get("Crosses", 0) or 0
                    comp_ppda = tactical_competition_averages.get("ppda", 0) or tactical_competition_averages.get("PPDA", 0) or 0
                    comp_match_tempo = (tactical_competition_averages.get("Match Tempo") or 
                                       tactical_competition_averages.get("match_tempo") or 
                                       tactical_competition_averages.get("Average passes per possession") or 0)
                    
                    # KPI Cards
                    col1, col2, col3, col4, col5 = st.columns(5)
                    # Get Cibao values for comparison
                    cibao_possession = tactical_cibao_averages.get("possessionPercentage", 0) or tactical_cibao_averages.get("Possession, %", 0) or 0
                    cibao_long_passes = tactical_cibao_averages.get("longPasses", 0) or tactical_cibao_averages.get("Long Passes", 0) or 0
                    cibao_crosses = tactical_cibao_averages.get("crosses", 0) or tactical_cibao_averages.get("Crosses", 0) or 0
                    cibao_ppda = tactical_cibao_averages.get("ppda", 0) or tactical_cibao_averages.get("PPDA", 0) or 0
                    cibao_match_tempo = (tactical_cibao_averages.get("Match Tempo") or 
                                        tactical_cibao_averages.get("match_tempo") or 
                                        tactical_cibao_averages.get("Average passes per possession") or 0)
                    
                    with col1:
                        display_metric_card(
                            "Posesión %",
                            f"{possession:.1f}%",
                            "",
                            f"Liga: {comp_possession:.1f}%",
                            color="normal",
                            cibao_avg=f"{cibao_possession:.1f}%"
                        )
                    with col2:
                        display_metric_card(
                            "Pases Largos x90",
                            f"{long_passes:.1f}",
                            "",
                            f"Liga: {comp_long_passes:.1f}",
                            color="normal",
                            cibao_avg=f"{cibao_long_passes:.1f}"
                        )
                    with col3:
                        display_metric_card(
                            "Centros x90",
                            f"{crosses:.1f}",
                            "",
                            f"Liga: {comp_crosses:.1f}",
                            color="normal",
                            cibao_avg=f"{cibao_crosses:.1f}"
                        )
                    with col4:
                        display_metric_card(
                            "PPDA",
                            f"{ppda:.2f}" if ppda > 0 else "N/A",
                            "",
                            f"Liga: {comp_ppda:.2f}" if comp_ppda > 0 else "N/A",
                            color="normal",
                            cibao_avg=f"{cibao_ppda:.2f}" if cibao_ppda > 0 else "N/A",
                            higher_is_better=False
                        )
                    with col5:
                        display_metric_card(
                            "Tempo del Partido",
                            f"{match_tempo:.1f}",
                            "",
                            f"Liga: {comp_match_tempo:.1f}",
                            color="normal",
                            cibao_avg=f"{cibao_match_tempo:.1f}"
                        )
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    # Column chart for playing style
                    base_color = team_color if team_color.startswith('#') else f'#{team_color}'
                    
                    # Helper function to determine if color is light (needs black text) or dark (needs white text)
                    def hex_to_rgb(hex_color):
                        """Convert hex color to RGB tuple."""
                        hex_color = hex_color.lstrip('#')
                        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
                    
                    def is_grey_or_black(hex_color):
                        """Check if a color is grey or black - if so, use white text."""
                        hex_str = str(hex_color).upper().lstrip('#')
                        # Explicitly check for common grey/black hex values
                        grey_black_hexes = ['888888', '666666', '555555', '444444', '333333', '222222', '111111', '000000',
                                            '999999', '777777', 'AAAAAA', 'BBBBBB']
                        if hex_str in grey_black_hexes:
                            return True
                        rgb = hex_to_rgb(hex_color)
                        r, g, b = rgb
                        # Check if it's black or very dark
                        if r < 50 and g < 50 and b < 50:
                            return True
                        # Check if it's grey: R, G, B are all equal (pure grey) or very close (within 10)
                        if r == g == b:
                            return True
                        if abs(r - g) <= 10 and abs(g - b) <= 10 and abs(r - b) <= 10:
                            # If average brightness is less than 200, it's dark grey
                            if (r + g + b) / 3 < 200:
                                return True
                        return False
                    
                    # Use get_text_color with team name for team-specific rules
                    team_text_color = get_text_color(base_color, team_name=selected_opponent)
                    
                    fig = go.Figure()
                    
                    categories = ["Posesión %", "Pases Largos x90", "Centros x90", "PPDA", "Tempo"]
                    team_values = [possession, long_passes, crosses, ppda, match_tempo]
                    comp_values = [comp_possession, comp_long_passes, comp_crosses, comp_ppda, comp_match_tempo]
                    
                    # Calculate max value to determine if bars are too small
                    all_values = [v for v in team_values + comp_values if v is not None and v > 0]
                    max_val = max(all_values) if all_values else 1
                    # Bar is "too small" if it's less than 10% of max value (more aggressive threshold)
                    threshold = max_val * 0.10
                    # Also consider absolute threshold - if bar is less than 5 units, place label outside
                    absolute_threshold = 5.0
                    
                    # Determine text position and color for each bar
                    # Labels outside bars (small bars) are always white
                    # Labels inside bars: white for dark bars, black for light bars
                    team_text_positions = ['outside' if (v < threshold or v < absolute_threshold) else 'inside' for v in team_values]
                    # Use get_text_color with team name for team-specific rules
                    base_text_color = get_text_color(base_color, team_name=selected_opponent)
                    team_text_colors = ['white' if (v < threshold or v < absolute_threshold) else base_text_color for v in team_values]
                    comp_text_positions = ['outside' if (v < threshold or v < absolute_threshold) else 'inside' for v in comp_values]
                    # League average labels are always white
                    comp_text_colors = ['#FFFFFF' for v in comp_values]  # League average bars are always dark gray, so always white text
                    
                    fig.add_trace(go.Bar(
                        name=selected_opponent,
                        x=categories,
                        y=team_values,
                        marker_color=base_color,
                        text=[f"{v:.1f}" if i < 3 else f"{v:.2f}" if i == 3 else f"{v:.1f}" for i, v in enumerate(team_values)],
                        textposition=team_text_positions,
                        insidetextanchor='middle',
                        textfont=dict(size=14, color=team_text_colors, family="Arial Black"),
                        cliponaxis=False
                    ))
                    
                    fig.add_trace(go.Bar(
                        name='Promedio Liga',
                        x=categories,
                        y=comp_values,
                        marker_color='#888888',
                        opacity=0.7,
                        text=[f"{v:.1f}" if i < 3 else f"{v:.2f}" if i == 3 else f"{v:.1f}" for i, v in enumerate(comp_values)],
                        textposition=comp_text_positions,
                        insidetextanchor='middle',
                        textfont=dict(size=14, color='#FFFFFF', family="Arial Black"),  # Always white for league average labels
                        cliponaxis=False
                    ))
                    
                    # Calculate y-axis range to ensure all bars are tall enough for labels
                    if all_values:
                        # Ensure minimum range so small bars are still readable, add extra space for outside labels
                        min_range = max(max_val * 1.3, 10)  # At least 10 units or 30% above max for outside labels
                        yaxis_range = [0, min_range]
                    else:
                        yaxis_range = None
                    
                    fig.update_layout(
                        barmode='group',
                        template='plotly_dark',
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        height=450,
                        margin=dict(t=100, b=100, l=50, r=50),  # Increased bottom margin for horizontal labels on mobile
                        yaxis_title="Valor",
                        xaxis_title="",
                        showlegend=True,
                        legend=dict(font=dict(color='white', family="Arial Black", size=14)),
                        font=dict(color='white', family="Arial Black", size=14),
                        xaxis=dict(tickangle=0, tickfont=dict(size=12)),  # Horizontal labels for better mobile experience
                        yaxis=dict(range=yaxis_range)
                    )
                    
                    st.plotly_chart(fig, use_container_width=True, key=f"style_chart_{selected_opponent}")
                else:
                    st.info("No hay datos disponibles para el análisis de estilo de juego.")
                
                # ========== SECCIÓN 1.6: PASSING PATTERNS ==========
                st.markdown("---")
                st.markdown("""
                <h3 style='color:#FF9900; margin-top:20px;'>Patrones de Pases</h3>
                """, unsafe_allow_html=True)
                
                if tactical_team_averages and isinstance(team_df, pd.DataFrame) and not team_df.empty:
                    # Get passing pattern metrics - try multiple column name variations
                    progressive_passes = (tactical_team_averages.get("Progressive Passes") or 
                                          tactical_team_averages.get("Progressive Passes Per 90") or 
                                          tactical_team_averages.get("Progressive Passes Accurate") or 
                                          tactical_team_averages.get("progressivePassesAccurate") or 0)
                    long_passes = (tactical_team_averages.get("Long Passes") or 
                                  tactical_team_averages.get("Long Passes Per 90") or 
                                  tactical_team_averages.get("longPasses") or 0)
                    passes_to_final_third = (tactical_team_averages.get("Passes to Final Third") or 
                                            tactical_team_averages.get("Passes to Final Third Per 90") or 
                                            tactical_team_averages.get("Passes to Final Third Accurate") or 
                                            tactical_team_averages.get("Passes To Final Third Accurate") or 
                                            tactical_team_averages.get("passesToFinalThirdAccurate") or 0)
                    deep_passes = (tactical_team_averages.get("Deep Completed Passes") or 
                                  tactical_team_averages.get("Deep Completed Passes Per 90") or 
                                  tactical_team_averages.get("Deep completed passes") or 
                                  tactical_team_averages.get("deepCompletedPasses") or 0)
                    avg_passes_per_possession = (tactical_team_averages.get("Average Passes Per Possession") or 
                                                tactical_team_averages.get("Average passes per possession") or 0)
                    avg_pass_length = (tactical_team_averages.get("Average Pass Length") or 
                                      tactical_team_averages.get("Average pass length") or 0)
                    
                    # Competition averages
                    comp_progressive = (tactical_competition_averages.get("Progressive Passes") or 
                                      tactical_competition_averages.get("Progressive Passes Per 90") or 
                                      tactical_competition_averages.get("Progressive Passes Accurate") or 
                                      tactical_competition_averages.get("progressivePassesAccurate") or 0)
                    comp_long_passes = (tactical_competition_averages.get("Long Passes") or 
                                       tactical_competition_averages.get("Long Passes Per 90") or 
                                       tactical_competition_averages.get("longPasses") or 0)
                    comp_final_third = (tactical_competition_averages.get("Passes to Final Third") or 
                                       tactical_competition_averages.get("Passes to Final Third Per 90") or 
                                       tactical_competition_averages.get("Passes to Final Third Accurate") or 
                                       tactical_competition_averages.get("Passes To Final Third Accurate") or 
                                       tactical_competition_averages.get("passesToFinalThirdAccurate") or 0)
                    comp_deep_passes = (tactical_competition_averages.get("Deep Completed Passes") or 
                                       tactical_competition_averages.get("Deep Completed Passes Per 90") or 
                                       tactical_competition_averages.get("Deep completed passes") or 
                                       tactical_competition_averages.get("deepCompletedPasses") or 0)
                    comp_avg_passes_per_possession = (tactical_competition_averages.get("Average Passes Per Possession") or 
                                                      tactical_competition_averages.get("Average passes per possession") or 0)
                    comp_avg_pass_length = (tactical_competition_averages.get("Average Pass Length") or 
                                           tactical_competition_averages.get("Average pass length") or 0)
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    # Column chart for passing patterns
                    base_color = team_color if team_color.startswith('#') else f'#{team_color}'
                    
                    # Helper function to determine if color is light (needs black text) or dark (needs white text)
                    def hex_to_rgb(hex_color):
                        """Convert hex color to RGB tuple."""
                        hex_color = hex_color.lstrip('#')
                        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
                    
                    def is_grey_or_black(hex_color):
                        """Check if a color is grey or black - if so, use white text."""
                        hex_str = str(hex_color).upper().lstrip('#')
                        # Explicitly check for common grey/black hex values
                        grey_black_hexes = ['888888', '666666', '555555', '444444', '333333', '222222', '111111', '000000',
                                            '999999', '777777', 'AAAAAA', 'BBBBBB']
                        if hex_str in grey_black_hexes:
                            return True
                        rgb = hex_to_rgb(hex_color)
                        r, g, b = rgb
                        # Check if it's black or very dark
                        if r < 50 and g < 50 and b < 50:
                            return True
                        # Check if it's grey: R, G, B are all equal (pure grey) or very close (within 10)
                        if r == g == b:
                            return True
                        if abs(r - g) <= 10 and abs(g - b) <= 10 and abs(r - b) <= 10:
                            # If average brightness is less than 200, it's dark grey
                            if (r + g + b) / 3 < 200:
                                return True
                        return False
                    
                    # Use get_text_color with team name for team-specific rules
                    team_text_color = get_text_color(base_color, team_name=selected_opponent)
                    
                    fig = go.Figure()
                    
                    categories = ["Pases Progresivos", "Pases Largos", "Pases al Tercer Final", "Pases Profundos", "Pases por Posesión", "Longitud Promedio"]
                    team_values = [progressive_passes, long_passes, passes_to_final_third, deep_passes, avg_passes_per_possession, avg_pass_length]
                    comp_values = [comp_progressive, comp_long_passes, comp_final_third, comp_deep_passes, comp_avg_passes_per_possession, comp_avg_pass_length]
                    
                    # Calculate max value to determine if bars are too small
                    all_values = [v for v in team_values + comp_values if v is not None and v > 0]
                    max_val = max(all_values) if all_values else 1
                    # Bar is "too small" if it's less than 10% of max value (more aggressive threshold)
                    threshold = max_val * 0.10
                    # Also consider absolute threshold - if bar is less than 5 units, place label outside
                    absolute_threshold = 5.0
                    
                    # Determine text position and color for each bar
                    # Labels outside bars (small bars) are always white
                    # Labels inside bars: white for dark bars, black for light bars
                    team_text_positions = ['outside' if (v < threshold or v < absolute_threshold) else 'inside' for v in team_values]
                    # Use get_text_color with team name for team-specific rules
                    base_text_color = get_text_color(base_color, team_name=selected_opponent)
                    team_text_colors = ['white' if (v < threshold or v < absolute_threshold) else base_text_color for v in team_values]
                    comp_text_positions = ['outside' if (v < threshold or v < absolute_threshold) else 'inside' for v in comp_values]
                    comp_text_colors = ['#FFFFFF' for v in comp_values]  # League average bars are always dark gray, so always white text
                    
                    fig.add_trace(go.Bar(
                        name=selected_opponent,
                        x=categories,
                        y=team_values,
                        marker_color=base_color,
                        text=[f"{v:.1f}" if i < 5 else f"{v:.1f}m" for i, v in enumerate(team_values)],
                        textposition=team_text_positions,
                        insidetextanchor='middle',
                        textfont=dict(size=14, color=team_text_colors, family="Arial Black"),
                        cliponaxis=False
                    ))
                    
                    fig.add_trace(go.Bar(
                        name='Promedio Liga',
                        x=categories,
                        y=comp_values,
                        marker_color='#888888',
                        opacity=0.7,
                        text=[f"{v:.1f}" if i < 5 else f"{v:.1f}m" for i, v in enumerate(comp_values)],
                        textposition=comp_text_positions,
                        insidetextanchor='middle',
                        textfont=dict(size=14, color='#FFFFFF', family="Arial Black"),  # Always white for league average labels
                        cliponaxis=False
                    ))
                    
                    # Calculate y-axis range to ensure all bars are tall enough for labels
                    if all_values:
                        # Ensure minimum range so small bars are still readable, add extra space for outside labels
                        min_range = max(max_val * 1.3, 10)  # At least 10 units or 30% above max for outside labels
                        yaxis_range = [0, min_range]
                    else:
                        yaxis_range = None
                    
                    fig.update_layout(
                        barmode='group',
                        template='plotly_dark',
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        height=450,
                        margin=dict(t=100, b=100, l=50, r=50),  # Increased bottom margin for horizontal labels on mobile
                        yaxis_title="Por 90 minutos",
                        xaxis_title="",
                        showlegend=True,
                        legend=dict(font=dict(color='white', family="Arial Black", size=14)),
                        font=dict(color='white', family="Arial Black", size=14),
                        xaxis=dict(tickangle=0, tickfont=dict(size=12)),  # Horizontal labels for better mobile experience
                        yaxis=dict(range=yaxis_range)
                    )
                    
                    st.plotly_chart(fig, use_container_width=True, key=f"passing_patterns_chart_{selected_opponent}")
                else:
                    st.info("No hay datos disponibles para el análisis de patrones de pases.")
                
                # ========== SECCIÓN 1.7: ATTACKING METHODS ==========
                st.markdown("---")
                st.markdown("""
                <h3 style='color:#FF9900; margin-top:20px;'>Métodos de Ataque</h3>
                """, unsafe_allow_html=True)
                
                if tactical_team_averages and isinstance(team_df, pd.DataFrame) and not team_df.empty:
                    # Get attacking method metrics - try multiple column name variations
                    positional_attacks = (tactical_team_averages.get("Positional Attacks") or 
                                          tactical_team_averages.get("Positional Attacks Per 90") or 
                                          tactical_team_averages.get("positionalAttacks") or 0)
                    positional_with_shots = (tactical_team_averages.get("Positional Attacks With Shot") or 
                                            tactical_team_averages.get("Positional Attacks With Shot Per 90") or 
                                            tactical_team_averages.get("Positional Attacks With Shots") or 
                                            tactical_team_averages.get("positionalAttacksWithShots") or 0)
                    positional_shot_pct = (positional_with_shots / positional_attacks * 100) if positional_attacks > 0 else 0
                    
                    counter_attacks = (tactical_team_averages.get("Counterattacks") or 
                                      tactical_team_averages.get("Counterattacks Per 90") or 
                                      tactical_team_averages.get("Counter Attacks") or 
                                      tactical_team_averages.get("counterAttacks") or 0)
                    counter_with_shots = (tactical_team_averages.get("Counterattacks With Shot") or 
                                         tactical_team_averages.get("Counterattacks With Shot Per 90") or 
                                         tactical_team_averages.get("Counter Attacks With Shots") or 
                                         tactical_team_averages.get("counterAttacksWithShots") or 0)
                    counter_shot_pct = (counter_with_shots / counter_attacks * 100) if counter_attacks > 0 else 0
                    
                    set_pieces = tactical_team_averages.get("setPieces", 0) or tactical_team_averages.get("Set Pieces", 0) or 0
                    set_pieces_with_shots = tactical_team_averages.get("setPiecesWithShots", 0) or tactical_team_averages.get("Set Pieces With Shots", 0) or 0
                    set_pieces_shot_pct = (set_pieces_with_shots / set_pieces * 100) if set_pieces > 0 else 0
                    
                    # Competition averages
                    comp_positional = (tactical_competition_averages.get("Positional Attacks") or 
                                      tactical_competition_averages.get("Positional Attacks Per 90") or 
                                      tactical_competition_averages.get("positionalAttacks") or 0)
                    comp_positional_with_shots = (tactical_competition_averages.get("Positional Attacks With Shot") or 
                                                 tactical_competition_averages.get("Positional Attacks With Shot Per 90") or 
                                                 tactical_competition_averages.get("Positional Attacks With Shots") or 
                                                 tactical_competition_averages.get("positionalAttacksWithShots") or 0)
                    comp_counter = (tactical_competition_averages.get("Counterattacks") or 
                                   tactical_competition_averages.get("Counterattacks Per 90") or 
                                   tactical_competition_averages.get("Counter Attacks") or 
                                   tactical_competition_averages.get("counterAttacks") or 0)
                    comp_counter_with_shots = (tactical_competition_averages.get("Counterattacks With Shot") or 
                                              tactical_competition_averages.get("Counterattacks With Shot Per 90") or 
                                              tactical_competition_averages.get("Counter Attacks With Shots") or 
                                              tactical_competition_averages.get("counterAttacksWithShots") or 0)
                    comp_set_pieces = tactical_competition_averages.get("setPieces", 0) or tactical_competition_averages.get("Set Pieces", 0) or 0
                    
                    # Cibao averages
                    cibao_positional = (tactical_cibao_averages.get("Positional Attacks") or 
                                       tactical_cibao_averages.get("Positional Attacks Per 90") or 
                                       tactical_cibao_averages.get("positionalAttacks") or 0)
                    cibao_counter = (tactical_cibao_averages.get("Counterattacks") or 
                                    tactical_cibao_averages.get("Counterattacks Per 90") or 
                                    tactical_cibao_averages.get("Counter Attacks") or 
                                    tactical_cibao_averages.get("counterAttacks") or 0)
                    cibao_positional_with_shots = (tactical_cibao_averages.get("Positional Attacks With Shot") or 
                                                   tactical_cibao_averages.get("Positional Attacks With Shot Per 90") or 
                                                   tactical_cibao_averages.get("Positional Attacks With Shots") or 
                                                   tactical_cibao_averages.get("positionalAttacksWithShots") or 0)
                    cibao_counter_with_shots = (tactical_cibao_averages.get("Counterattacks With Shot") or 
                                               tactical_cibao_averages.get("Counterattacks With Shot Per 90") or 
                                               tactical_cibao_averages.get("Counter Attacks With Shots") or 
                                               tactical_cibao_averages.get("counterAttacksWithShots") or 0)
                    cibao_positional_shot_pct = (cibao_positional_with_shots / cibao_positional * 100) if cibao_positional > 0 else 0
                    cibao_counter_shot_pct = (cibao_counter_with_shots / cibao_counter * 100) if cibao_counter > 0 else 0
                    
                    # KPI Cards
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        display_metric_card(
                            "Ataques Posicionales",
                            f"{positional_attacks:.1f}",
                            "",
                            f"Liga: {comp_positional:.1f}",
                            color="normal",
                            cibao_avg=f"{cibao_positional:.1f}"
                        )
                    with col2:
                        display_metric_card(
                            "Efectividad Posicional",
                            f"{positional_shot_pct:.1f}%",
                            "",
                            "Con disparos",
                            color="normal",
                            cibao_avg=f"{cibao_positional_shot_pct:.1f}%"
                        )
                    with col3:
                        display_metric_card(
                            "Contraataques",
                            f"{counter_attacks:.1f}",
                            "",
                            f"Liga: {comp_counter:.1f}",
                            color="normal",
                            cibao_avg=f"{cibao_counter:.1f}"
                        )
                    with col4:
                        display_metric_card(
                            "Efectividad Contraataques",
                            f"{counter_shot_pct:.1f}%",
                            "",
                            "Con disparos",
                            color="normal",
                            cibao_avg=f"{cibao_counter_shot_pct:.1f}%"
                        )
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    # Grouped bar chart for positional attacks
                    base_color = team_color if team_color.startswith('#') else f'#{team_color}'
                    
                    # Helper function to determine if color is light (needs black text) or dark (needs white text)
                    def hex_to_rgb(hex_color):
                        """Convert hex color to RGB tuple."""
                        hex_color = hex_color.lstrip('#')
                        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
                    
                    def is_grey_or_black(hex_color):
                        """Check if a color is grey or black - if so, use white text."""
                        hex_str = str(hex_color).upper().lstrip('#')
                        # Explicitly check for common grey/black hex values
                        grey_black_hexes = ['888888', '666666', '555555', '444444', '333333', '222222', '111111', '000000',
                                            '999999', '777777', 'AAAAAA', 'BBBBBB']
                        if hex_str in grey_black_hexes:
                            return True
                        rgb = hex_to_rgb(hex_color)
                        r, g, b = rgb
                        # Check if it's black or very dark
                        if r < 50 and g < 50 and b < 50:
                            return True
                        # Check if it's grey: R, G, B are all equal (pure grey) or very close (within 10)
                        if r == g == b:
                            return True
                        if abs(r - g) <= 10 and abs(g - b) <= 10 and abs(r - b) <= 10:
                            # If average brightness is less than 200, it's dark grey
                            if (r + g + b) / 3 < 200:
                                return True
                        return False
                    
                    # Use get_text_color with team name for team-specific rules
                    team_text_color = get_text_color(base_color, team_name=selected_opponent)
                    
                    fig = go.Figure()
                    
                    # Calculate max value to determine if bars are too small
                    all_attack_values = [positional_attacks, comp_positional, positional_with_shots, comp_positional_with_shots]
                    max_attack_val = max([v for v in all_attack_values if v is not None and v > 0]) if any(v > 0 for v in all_attack_values) else 1
                    threshold = max_attack_val * 0.05
                    
                    # Determine text position and color for each bar
                    # Labels outside bars (small bars) are always white
                    # Labels inside bars: white for dark bars, black for light bars
                    pos_attacks_pos = 'outside' if positional_attacks < threshold else 'inside'
                    # Use get_text_color with team name for team-specific rules
                    base_text_color = get_text_color(base_color, team_name=selected_opponent)
                    pos_attacks_color = 'white' if positional_attacks < threshold else base_text_color
                    comp_pos_attacks_pos = 'outside' if comp_positional < threshold else 'inside'
                    comp_pos_attacks_color = '#FFFFFF'  # League average bars are always dark gray
                    
                    pos_shots_pos = 'outside' if positional_with_shots < threshold else 'inside'
                    pos_shots_color = 'white' if positional_with_shots < threshold else base_text_color
                    comp_pos_shots_pos = 'outside' if comp_positional_with_shots < threshold else 'inside'
                    comp_pos_shots_color = '#FFFFFF'  # League average bars are always dark gray
                    
                    fig.add_trace(go.Bar(
                        name='Ataques Posicionales',
                        x=[selected_opponent, 'Promedio Liga'],
                        y=[positional_attacks, comp_positional],
                        marker_color=base_color,
                        text=[f"{positional_attacks:.1f}", f"{comp_positional:.1f}"],
                        textposition=[pos_attacks_pos, comp_pos_attacks_pos],
                        insidetextanchor='middle',
                        textfont=dict(size=14, color=[pos_attacks_color, '#FFFFFF'], family='Arial Black'),  # League average always white
                        cliponaxis=False
                    ))
                    
                    fig.add_trace(go.Bar(
                        name='Ataques Posicionales con Disparos',
                        x=[selected_opponent, 'Promedio Liga'],
                        y=[positional_with_shots, comp_positional_with_shots],
                        marker_color=base_color,
                        opacity=0.6,
                        text=[f"{positional_with_shots:.1f}", f"{comp_positional_with_shots:.1f}"],
                        textposition=[pos_shots_pos, comp_pos_shots_pos],
                        insidetextanchor='middle',
                        textfont=dict(size=14, color=[pos_shots_color, '#FFFFFF'], family='Arial Black'),  # League average always white
                        cliponaxis=False
                    ))
                    
                    # Calculate y-axis range to ensure all bars are tall enough for labels
                    all_attack_values_list = [v for v in [positional_attacks, positional_with_shots, comp_positional, comp_positional_with_shots] if v is not None and v > 0]
                    if all_attack_values_list:
                        max_attack_val_for_range = max(all_attack_values_list)
                        # Ensure minimum range so small bars are still readable
                        min_range = max(max_attack_val_for_range * 1.2, 10)  # At least 10 units or 20% above max
                        yaxis_range = [0, min_range]
                    else:
                        yaxis_range = None
                    
                    fig.update_layout(
                        barmode='group',
                        template='plotly_dark',
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        height=450,
                        margin=dict(t=100, b=60, l=50, r=50),  # Increased top margin for outside labels
                        yaxis_title="Por 90 minutos",
                        xaxis_title="",
                        showlegend=True,
                        legend=dict(font=dict(color='white')),
                        font=dict(color='white'),
                        yaxis=dict(range=yaxis_range)
                    )
                    
                    st.plotly_chart(fig, use_container_width=True, key=f"attacking_methods_chart_{selected_opponent}")
                else:
                    st.info("No hay datos disponibles para el análisis de métodos de ataque.")
                
                # ========== SECCIÓN 1.8: PRESSING & DEFENSIVE INTENSITY ==========
                st.markdown("---")
                st.markdown("""
                <h3 style='color:#FF9900; margin-top:20px;'>Presión e Intensidad Defensiva</h3>
                """, unsafe_allow_html=True)
                
                if tactical_team_averages and isinstance(team_df, pd.DataFrame) and not team_df.empty:
                    # Get defensive metrics
                    ppda = tactical_team_averages.get("ppda", 0) or tactical_team_averages.get("PPDA", 0) or 0
                    defensive_duels_won_pct = (tactical_team_averages.get("Defensive Duels Win %") or 
                                              tactical_team_averages.get("Defensive Duels Won %") or 
                                              tactical_team_averages.get("defensiveDuelsWonPct") or 
                                              tactical_team_averages.get("defensive_duels_won_pct") or 0)
                    aerial_duels_won_pct = (tactical_team_averages.get("Aerial Duels Win %") or 
                                          tactical_team_averages.get("Aerial Duels Won %") or 
                                          tactical_team_averages.get("aerialDuelsWonPct") or 
                                          tactical_team_averages.get("aerial_duels_won_pct") or 0)
                    interceptions = (tactical_team_averages.get("Interceptions") or 
                                   tactical_team_averages.get("Interceptions Per 90") or 
                                   tactical_team_averages.get("interceptions") or 0)
                    recoveries = tactical_team_averages.get("recoveries", 0) or tactical_team_averages.get("Recoveries", 0) or 0
                    recoveries_high = tactical_team_averages.get("Recoveries High", 0) or 0
                    
                    # Competition averages
                    comp_ppda = tactical_competition_averages.get("ppda", 0) or tactical_competition_averages.get("PPDA", 0) or 0
                    comp_defensive_pct = (tactical_competition_averages.get("Defensive Duels Win %") or 
                                         tactical_competition_averages.get("Defensive Duels Won %") or 
                                         tactical_competition_averages.get("defensiveDuelsWonPct") or 
                                         tactical_competition_averages.get("defensive_duels_won_pct") or 0)
                    comp_aerial_pct = (tactical_competition_averages.get("Aerial Duels Win %") or 
                                      tactical_competition_averages.get("Aerial Duels Won %") or 
                                      tactical_competition_averages.get("aerialDuelsWonPct") or 
                                      tactical_competition_averages.get("aerial_duels_won_pct") or 0)
                    comp_interceptions = (tactical_competition_averages.get("Interceptions") or 
                                         tactical_competition_averages.get("Interceptions Per 90") or 
                                         tactical_competition_averages.get("interceptions") or 0)
                    comp_recoveries = tactical_competition_averages.get("recoveries", 0) or tactical_competition_averages.get("Recoveries", 0) or 0
                    
                    # Cibao averages
                    cibao_ppda = tactical_cibao_averages.get("ppda", 0) or tactical_cibao_averages.get("PPDA", 0) or 0
                    cibao_defensive_pct = (tactical_cibao_averages.get("Defensive Duels Win %") or 
                                          tactical_cibao_averages.get("Defensive Duels Won %") or 
                                          tactical_cibao_averages.get("defensiveDuelsWonPct") or 
                                          tactical_cibao_averages.get("defensive_duels_won_pct") or 0)
                    cibao_aerial_pct = (tactical_cibao_averages.get("Aerial Duels Win %") or 
                                       tactical_cibao_averages.get("Aerial Duels Won %") or 
                                       tactical_cibao_averages.get("aerialDuelsWonPct") or 
                                       tactical_cibao_averages.get("aerial_duels_won_pct") or 0)
                    cibao_interceptions = (tactical_cibao_averages.get("Interceptions") or 
                                          tactical_cibao_averages.get("Interceptions Per 90") or 
                                          tactical_cibao_averages.get("interceptions") or 0)
                    
                    # KPI Cards
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        # Lower PPDA = more intense pressing
                        display_metric_card(
                            "PPDA",
                            f"{ppda:.1f}",
                            "",
                            f"Liga: {comp_ppda:.1f}",
                            color="normal",
                            cibao_avg=f"{cibao_ppda:.1f}",
                            higher_is_better=False
                        )
                    with col2:
                        display_metric_card(
                            "Duelos Defensivos %",
                            f"{defensive_duels_won_pct:.1f}%",
                            "",
                            f"Liga: {comp_defensive_pct:.1f}%",
                            color="normal",
                            cibao_avg=f"{cibao_defensive_pct:.1f}%"
                        )
                    with col3:
                        display_metric_card(
                            "Duelos Aéreos %",
                            f"{aerial_duels_won_pct:.1f}%",
                            "",
                            f"Liga: {comp_aerial_pct:.1f}%",
                            color="normal",
                            cibao_avg=f"{cibao_aerial_pct:.1f}%"
                        )
                    with col4:
                        display_metric_card(
                            "Intercepciones",
                            f"{interceptions:.1f}",
                            "",
                            f"Liga: {comp_interceptions:.1f}",
                            color="normal",
                            cibao_avg=f"{cibao_interceptions:.1f}"
                        )
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    # Comparison chart for defensive metrics
                    metrics_names = ["PPDA\n(Menor=Mejor)", "Duelos Def.\nGanados %", "Duelos Aéreos\nGanados %", "Intercepciones"]
                    team_values = [ppda, defensive_duels_won_pct, aerial_duels_won_pct, interceptions]
                    comp_values = [comp_ppda, comp_defensive_pct, comp_aerial_pct, comp_interceptions]
                    
                    # Normalize PPDA for comparison (invert so lower is better visually)
                    max_ppda = max(ppda, comp_ppda) * 1.2 if max(ppda, comp_ppda) > 0 else 20
                    normalized_ppda_team = ((max_ppda - ppda) / max_ppda) * 100 if max_ppda > 0 else 0
                    normalized_ppda_comp = ((max_ppda - comp_ppda) / max_ppda) * 100 if max_ppda > 0 else 0
                    
                    # Use normalized PPDA for chart
                    chart_team_values = [normalized_ppda_team, defensive_duels_won_pct, aerial_duels_won_pct, interceptions]
                    chart_comp_values = [normalized_ppda_comp, comp_defensive_pct, comp_aerial_pct, comp_interceptions]
                    
                    fig = go.Figure()
                    
                    # Helper function to determine if color is light (needs black text) or dark (needs white text)
                    def hex_to_rgb(hex_color):
                        """Convert hex color to RGB tuple."""
                        hex_color = hex_color.lstrip('#')
                        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
                    
                    def is_grey_or_black(hex_color):
                        """Check if a color is grey or black - if so, use white text."""
                        hex_str = str(hex_color).upper().lstrip('#')
                        # Explicitly check for common grey/black hex values
                        grey_black_hexes = ['888888', '666666', '555555', '444444', '333333', '222222', '111111', '000000',
                                            '999999', '777777', 'AAAAAA', 'BBBBBB']
                        if hex_str in grey_black_hexes:
                            return True
                        rgb = hex_to_rgb(hex_color)
                        r, g, b = rgb
                        # Check if it's black or very dark
                        if r < 50 and g < 50 and b < 50:
                            return True
                        # Check if it's grey: R, G, B are all equal (pure grey) or very close (within 10)
                        if r == g == b:
                            return True
                        if abs(r - g) <= 10 and abs(g - b) <= 10 and abs(r - b) <= 10:
                            # If average brightness is less than 200, it's dark grey
                            if (r + g + b) / 3 < 200:
                                return True
                        return False
                    
                    # Use get_text_color with team name for team-specific rules
                    team_text_color = get_text_color(team_color, team_name=selected_opponent)
                    
                    # Calculate max value to determine if bars are too small
                    all_def_values = [v for v in chart_team_values + chart_comp_values if v is not None and v > 0]
                    max_def_val = max(all_def_values) if all_def_values else 1
                    threshold = max_def_val * 0.05
                    
                    # Determine text position and color for each bar
                    # Labels outside bars (small bars) are always white
                    # Labels inside bars: white for dark bars, black for light bars
                    team_def_text_positions = ['outside' if v < threshold else 'inside' for v in chart_team_values]
                    # Use get_text_color with team name for team-specific rules
                    base_text_color = get_text_color(team_color, team_name=selected_opponent)
                    team_def_text_colors = ['white' if v < threshold else base_text_color for v in chart_team_values]
                    comp_def_text_positions = ['outside' if v < threshold else 'inside' for v in chart_comp_values]
                    comp_def_text_colors = ['#FFFFFF' for v in chart_comp_values]  # League average bars are always dark gray
                    
                    fig.add_trace(go.Bar(
                        name=selected_opponent,
                        x=metrics_names,
                        y=chart_team_values,
                        marker_color=team_color,
                        text=[f"{team_values[0]:.1f}", f"{team_values[1]:.1f}%", f"{team_values[2]:.1f}%", f"{team_values[3]:.1f}"],
                        textposition=team_def_text_positions,
                        insidetextanchor='middle',
                        textfont=dict(size=14, color=team_def_text_colors, family='Arial Black'),
                        cliponaxis=False
                    ))
                    
                    fig.add_trace(go.Bar(
                        name='Promedio Liga',
                        x=metrics_names,
                        y=chart_comp_values,
                        marker_color='#888888',
                        opacity=0.7,
                        text=[f"{comp_values[0]:.1f}", f"{comp_values[1]:.1f}%", f"{comp_values[2]:.1f}%", f"{comp_values[3]:.1f}"],
                        textposition=comp_def_text_positions,
                        insidetextanchor='middle',
                        textfont=dict(size=14, color='#FFFFFF', family='Arial Black'),  # Always white for league average labels
                        cliponaxis=False
                    ))
                    
                    # Calculate y-axis range to ensure all bars are tall enough for labels
                    all_values = [v for v in chart_team_values + chart_comp_values if v is not None and v > 0]
                    if all_values:
                        max_val = max(all_values)
                        # Ensure minimum range so small bars are still readable
                        min_range = max(max_val * 1.2, 10)  # At least 10 units or 20% above max
                        yaxis_range = [0, min_range]
                    else:
                        yaxis_range = None
                    
                    fig.update_layout(
                        barmode='group',
                        template='plotly_dark',
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        height=450,
                        margin=dict(t=100, b=60, l=50, r=50),  # Increased top margin for outside labels
                        yaxis_title="Valor Normalizado",
                        xaxis_title="",
                        showlegend=True,
                        legend=dict(font=dict(color='white')),
                        font=dict(color='white'),
                        yaxis=dict(range=yaxis_range)
                    )
                    
                    st.plotly_chart(fig, use_container_width=True, key=f"defensive_intensity_chart_{selected_opponent}")
                else:
                    st.info("No hay datos disponibles para el análisis de presión e intensidad defensiva.")
                
                # ========== SECCIÓN 4: SET PIECES ==========
                st.markdown("---")
                st.markdown("""
                <h3 style='color:#FF9900; margin-top:20px;'>Set Pieces</h3>
                """, unsafe_allow_html=True)
                
                if tactical_team_averages and isinstance(team_df, pd.DataFrame) and not team_df.empty:
                    # Get set pieces metrics from Wyscout data - try multiple column name variations
                    corners = (tactical_team_averages.get("Corners") or 
                              tactical_team_averages.get("Corners Per 90") or 
                              tactical_team_averages.get("corners") or 0)
                    corners_with_shots = (tactical_team_averages.get("Corners With Shot") or 
                                         tactical_team_averages.get("Corners With Shot Per 90") or 
                                         tactical_team_averages.get("Corners With Shots") or 
                                         tactical_team_averages.get("cornersWithShots") or 0)
                    corners_shot_pct = (corners_with_shots / corners * 100) if corners > 0 else 0
                    
                    free_kicks = (tactical_team_averages.get("Free Kicks") or 
                                 tactical_team_averages.get("Free Kicks Per 90") or 
                                 tactical_team_averages.get("freeKicks") or 0)
                    free_kicks_with_shots = (tactical_team_averages.get("Free Kicks With Shot") or 
                                            tactical_team_averages.get("Free Kicks With Shot Per 90") or 
                                            tactical_team_averages.get("Free Kicks With Shots") or 
                                            tactical_team_averages.get("freeKicksWithShots") or 0)
                    free_kicks_shot_pct = (free_kicks_with_shots / free_kicks * 100) if free_kicks > 0 else 0
                    
                    penalties = tactical_team_averages.get("penalties", 0) or tactical_team_averages.get("Penalties", 0) or 0
                    penalties_converted = tactical_team_averages.get("penaltiesConverted", 0) or tactical_team_averages.get("Penalties Converted", 0) or 0
                    penalties_pct = (penalties_converted / penalties * 100) if penalties > 0 else 0
                    
                    throw_ins = tactical_team_averages.get("throwIns", 0) or tactical_team_averages.get("Throw Ins", 0) or 0
                    throw_ins_accurate = tactical_team_averages.get("throwInsAccurate", 0) or tactical_team_averages.get("Throw Ins Accurate", 0) or 0
                    throw_ins_pct = (throw_ins_accurate / throw_ins * 100) if throw_ins > 0 else 0
                    
                    # Competition averages
                    comp_corners = (tactical_competition_averages.get("Corners") or 
                                   tactical_competition_averages.get("Corners Per 90") or 
                                   tactical_competition_averages.get("corners") or 0)
                    comp_corners_with_shots = (tactical_competition_averages.get("Corners With Shot") or 
                                              tactical_competition_averages.get("Corners With Shot Per 90") or 
                                              tactical_competition_averages.get("Corners With Shots") or 
                                              tactical_competition_averages.get("cornersWithShots") or 0)
                    comp_free_kicks = (tactical_competition_averages.get("Free Kicks") or 
                                      tactical_competition_averages.get("Free Kicks Per 90") or 
                                      tactical_competition_averages.get("freeKicks") or 0)
                    comp_free_kicks_with_shots = (tactical_competition_averages.get("Free Kicks With Shot") or 
                                                  tactical_competition_averages.get("Free Kicks With Shot Per 90") or 
                                                  tactical_competition_averages.get("Free Kicks With Shots") or 
                                                  tactical_competition_averages.get("freeKicksWithShots") or 0)
                    comp_penalties = tactical_competition_averages.get("penalties", 0) or tactical_competition_averages.get("Penalties", 0) or 0
                    comp_penalties_converted = tactical_competition_averages.get("penaltiesConverted", 0) or tactical_competition_averages.get("Penalties Converted", 0) or 0
                    comp_throw_ins = tactical_competition_averages.get("throwIns", 0) or tactical_competition_averages.get("Throw Ins", 0) or 0
                    comp_throw_ins_accurate = tactical_competition_averages.get("throwInsAccurate", 0) or tactical_competition_averages.get("Throw Ins Accurate", 0) or 0
                    
                    # Helper functions for color manipulation (reuse if already defined, otherwise define here)
                    def hex_to_rgb(hex_color):
                        """Convert hex color to RGB tuple."""
                        hex_color = hex_color.lstrip('#')
                        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
                    
                    def rgb_to_hex(rgb):
                        """Convert RGB tuple to hex color."""
                        return '#{:02x}{:02x}{:02x}'.format(int(rgb[0]), int(rgb[1]), int(rgb[2]))
                    
                    def lighten_color(hex_color, factor=0.3):
                        """Lighten a hex color by a factor (0-1)."""
                        rgb = hex_to_rgb(hex_color)
                        lightened = tuple(min(255, c + (255 - c) * factor) for c in rgb)
                        return rgb_to_hex(lightened)
                    
                    def darken_color(hex_color, factor=0.3):
                        """Darken a hex color by a factor (0-1)."""
                        rgb = hex_to_rgb(hex_color)
                        darkened = tuple(max(0, c * (1 - factor)) for c in rgb)
                        return rgb_to_hex(darkened)
                    
                    base_color = team_color if team_color.startswith('#') else f'#{team_color}'
                    lighter_color = lighten_color(base_color, factor=0.6)
                    darker_color = darken_color(base_color, factor=0.6)
                    
                    # Helper function to determine if color is light (needs black text) or dark (needs white text)
                    def is_grey_or_black(hex_color):
                        """Check if a color is grey or black - if so, use white text."""
                        hex_str = str(hex_color).upper().lstrip('#')
                        # Explicitly check for common grey/black hex values
                        grey_black_hexes = ['888888', '666666', '555555', '444444', '333333', '222222', '111111', '000000',
                                            '999999', '777777', 'AAAAAA', 'BBBBBB']
                        if hex_str in grey_black_hexes:
                            return True
                        rgb = hex_to_rgb(hex_color)
                        r, g, b = rgb
                        # Check if it's black or very dark
                        if r < 50 and g < 50 and b < 50:
                            return True
                        # Check if it's grey: R, G, B are all equal (pure grey) or very close (within 10)
                        if r == g == b:
                            return True
                        if abs(r - g) <= 10 and abs(g - b) <= 10 and abs(r - b) <= 10:
                            # If average brightness is less than 200, it's dark grey
                            if (r + g + b) / 3 < 200:
                                return True
                        return False
                    
                    # Column chart for Corners
                    st.markdown("#### Corners")
                    st.markdown(f"**Efectividad: {corners_shot_pct:.1f}%** (Corners con disparos: {corners_with_shots:.1f} de {corners:.1f} total)")
                    # Calculate max value to determine if bars are too small
                    all_corners_values = [corners, corners_with_shots, comp_corners, comp_corners_with_shots]
                    all_corners_values_clean = [v for v in all_corners_values if v is not None and v > 0]
                    max_corners_val = max(all_corners_values_clean) if all_corners_values_clean else 1
                    threshold = max_corners_val * 0.05
                    
                    # Determine text position and color for each bar
                    # Labels outside bars (small bars) are always white
                    # Labels inside bars: white for dark bars, black for light bars
                    team_corners_positions = ['outside' if v < threshold else 'inside' for v in [corners, corners_with_shots]]
                    # Use get_text_color with team name for team-specific rules
                    base_text_color = get_text_color(base_color, team_name=selected_opponent)
                    team_corners_colors = ['white' if v < threshold else base_text_color for v in [corners, corners_with_shots]]
                    comp_corners_positions = ['outside' if v < threshold else 'inside' for v in [comp_corners, comp_corners_with_shots]]
                    comp_corners_colors = ['#FFFFFF' for v in [comp_corners, comp_corners_with_shots]]  # League average bars are always dark gray
                    
                    fig_corners = go.Figure()
                    fig_corners.add_trace(go.Bar(
                        name=selected_opponent,
                        x=["Total", "Con Disparos"],
                        y=[corners, corners_with_shots],
                        marker_color=base_color,
                        text=[f"{corners:.1f}", f"{corners_with_shots:.1f}"],
                        textposition=team_corners_positions,
                        insidetextanchor='middle',
                        textfont=dict(size=14, color=team_corners_colors, family='Arial Black'),
                        cliponaxis=False
                    ))
                    fig_corners.add_trace(go.Bar(
                        name='Promedio Liga',
                        x=["Total", "Con Disparos"],
                        y=[comp_corners, comp_corners_with_shots],
                        marker_color='#888888',
                        opacity=0.7,
                        text=[f"{comp_corners:.1f}", f"{comp_corners_with_shots:.1f}"],
                        textposition=comp_corners_positions,
                        insidetextanchor='middle',
                        textfont=dict(size=14, color=comp_corners_colors, family='Arial Black'),  # Always white for league average labels
                        cliponaxis=False
                    ))
                    fig_corners.update_layout(
                        barmode='group',
                        template='plotly_dark',
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        height=450,
                        margin=dict(t=100, b=60, l=50, r=50),  # Increased top margin for outside labels
                        yaxis_title="Por 90 Minutos",
                        showlegend=True,
                        legend=dict(font=dict(color='white')),
                        font=dict(color='white')
                    )
                    st.plotly_chart(fig_corners, use_container_width=True, key=f"corners_chart_{selected_opponent}")
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    # Column chart for Free Kicks
                    st.markdown("#### Tiros Libres")
                    st.markdown(f"**Efectividad: {free_kicks_shot_pct:.1f}%** (Tiros libres con disparos: {free_kicks_with_shots:.1f} de {free_kicks:.1f} total)")
                    # Calculate max value to determine if bars are too small
                    all_fk_values = [free_kicks, free_kicks_with_shots, comp_free_kicks, comp_free_kicks_with_shots]
                    all_fk_values_clean = [v for v in all_fk_values if v is not None and v > 0]
                    max_fk_val = max(all_fk_values_clean) if all_fk_values_clean else 1
                    threshold = max_fk_val * 0.05
                    
                    # Determine text position and color for each bar
                    # Labels outside bars (small bars) are always white
                    # Labels inside bars: white for dark bars, black for light bars
                    team_fk_positions = ['outside' if v < threshold else 'inside' for v in [free_kicks, free_kicks_with_shots]]
                    # Use get_text_color with team name for team-specific rules
                    base_text_color = get_text_color(base_color, team_name=selected_opponent)
                    team_fk_colors = ['white' if v < threshold else base_text_color for v in [free_kicks, free_kicks_with_shots]]
                    comp_fk_positions = ['outside' if v < threshold else 'inside' for v in [comp_free_kicks, comp_free_kicks_with_shots]]
                    comp_fk_colors = ['#FFFFFF' for v in [comp_free_kicks, comp_free_kicks_with_shots]]  # League average bars are always dark gray
                    
                    fig_fk = go.Figure()
                    fig_fk.add_trace(go.Bar(
                        name=selected_opponent,
                        x=["Total", "Con Disparos"],
                        y=[free_kicks, free_kicks_with_shots],
                        marker_color=base_color,
                        text=[f"{free_kicks:.1f}", f"{free_kicks_with_shots:.1f}"],
                        textposition=team_fk_positions,
                        insidetextanchor='middle',
                        textfont=dict(size=14, color=team_fk_colors, family='Arial Black'),
                        cliponaxis=False
                    ))
                    fig_fk.add_trace(go.Bar(
                        name='Promedio Liga',
                        x=["Total", "Con Disparos"],
                        y=[comp_free_kicks, comp_free_kicks_with_shots],
                        marker_color='#888888',
                        opacity=0.7,
                        text=[f"{comp_free_kicks:.1f}", f"{comp_free_kicks_with_shots:.1f}"],
                        textposition=comp_fk_positions,
                        insidetextanchor='middle',
                        textfont=dict(size=14, color=comp_fk_colors, family='Arial Black'),  # Always white for league average labels
                        cliponaxis=False
                    ))
                    fig_fk.update_layout(
                        barmode='group',
                        template='plotly_dark',
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        height=450,
                        margin=dict(t=100, b=60, l=50, r=50),  # Increased top margin for outside labels
                        yaxis_title="Por 90 Minutos",
                        showlegend=True,
                        legend=dict(font=dict(color='white')),
                        font=dict(color='white')
                    )
                    st.plotly_chart(fig_fk, use_container_width=True, key=f"free_kicks_chart_{selected_opponent}")
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    # Column chart for Penalties
                    st.markdown("#### Penales")
                    st.markdown(f"**Conversión: {penalties_pct:.1f}%** (Penales convertidos: {penalties_converted:.1f} de {penalties:.1f} total)")
                    # Calculate max value to determine if bars are too small
                    all_penalties_values = [penalties, penalties_converted, comp_penalties, comp_penalties_converted]
                    all_penalties_values_clean = [v for v in all_penalties_values if v is not None and v > 0]
                    max_penalties_val = max(all_penalties_values_clean) if all_penalties_values_clean else 1
                    threshold = max_penalties_val * 0.05
                    
                    # Determine text position and color for each bar
                    # Labels outside bars (small bars) are always white
                    # Labels inside bars: white for dark bars, black for light bars
                    team_penalties_positions = ['outside' if v < threshold else 'inside' for v in [penalties, penalties_converted]]
                    # Use get_text_color with team name for team-specific rules
                    base_text_color = get_text_color(base_color, team_name=selected_opponent)
                    team_penalties_colors = ['white' if v < threshold else base_text_color for v in [penalties, penalties_converted]]
                    comp_penalties_positions = ['outside' if v < threshold else 'inside' for v in [comp_penalties, comp_penalties_converted]]
                    comp_penalties_colors = ['#FFFFFF' for v in [comp_penalties, comp_penalties_converted]]  # League average bars are always dark gray
                    
                    fig_penalties = go.Figure()
                    fig_penalties.add_trace(go.Bar(
                        name=selected_opponent,
                        x=["Total", "Convertidos"],
                        y=[penalties, penalties_converted],
                        marker_color=base_color,
                        text=[f"{penalties:.1f}", f"{penalties_converted:.1f}"],
                        textposition=team_penalties_positions,
                        insidetextanchor='middle',
                        textfont=dict(size=14, color=team_penalties_colors, family='Arial Black'),
                        cliponaxis=False
                    ))
                    fig_penalties.add_trace(go.Bar(
                        name='Promedio Liga',
                        x=["Total", "Convertidos"],
                        y=[comp_penalties, comp_penalties_converted],
                        marker_color='#888888',
                        opacity=0.7,
                        text=[f"{comp_penalties:.1f}", f"{comp_penalties_converted:.1f}"],
                        textposition=comp_penalties_positions,
                        insidetextanchor='middle',
                        textfont=dict(size=14, color='#FFFFFF', family='Arial Black'),  # Always white for league average labels
                        cliponaxis=False
                    ))
                    fig_penalties.update_layout(
                        barmode='group',
                        template='plotly_dark',
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        height=450,
                        margin=dict(t=100, b=60, l=50, r=50),  # Increased top margin for outside labels
                        yaxis_title="Por 90 Minutos",
                        showlegend=True,
                        legend=dict(font=dict(color='white')),
                        font=dict(color='white')
                    )
                    st.plotly_chart(fig_penalties, use_container_width=True, key=f"penalties_chart_{selected_opponent}")
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    # Column chart for Throw Ins
                    st.markdown("#### Saques de Banda")
                    st.markdown(f"**Precisión: {throw_ins_pct:.1f}%** (Saques precisos: {throw_ins_accurate:.1f} de {throw_ins:.1f} total)")
                    # Calculate max value to determine if bars are too small
                    all_throw_ins_values = [throw_ins, throw_ins_accurate, comp_throw_ins, comp_throw_ins_accurate]
                    all_throw_ins_values_clean = [v for v in all_throw_ins_values if v is not None and v > 0]
                    max_throw_ins_val = max(all_throw_ins_values_clean) if all_throw_ins_values_clean else 1
                    threshold = max_throw_ins_val * 0.05
                    
                    # Determine text position and color for each bar
                    # Labels outside bars (small bars) are always white
                    # Labels inside bars: white for dark bars, black for light bars
                    team_throw_ins_positions = ['outside' if v < threshold else 'inside' for v in [throw_ins, throw_ins_accurate]]
                    # Use get_text_color with team name for team-specific rules
                    base_text_color = get_text_color(base_color, team_name=selected_opponent)
                    team_throw_ins_colors = ['white' if v < threshold else base_text_color for v in [throw_ins, throw_ins_accurate]]
                    comp_throw_ins_positions = ['outside' if v < threshold else 'inside' for v in [comp_throw_ins, comp_throw_ins_accurate]]
                    comp_throw_ins_colors = ['#FFFFFF' for v in [comp_throw_ins, comp_throw_ins_accurate]]  # League average bars are always dark gray
                    
                    fig_throw_ins = go.Figure()
                    fig_throw_ins.add_trace(go.Bar(
                        name=selected_opponent,
                        x=["Total", "Precisos"],
                        y=[throw_ins, throw_ins_accurate],
                        marker_color=base_color,
                        text=[f"{throw_ins:.1f}", f"{throw_ins_accurate:.1f}"],
                        textposition=team_throw_ins_positions,
                        insidetextanchor='middle',
                        textfont=dict(size=14, color=team_throw_ins_colors, family='Arial Black'),
                        cliponaxis=False
                    ))
                    fig_throw_ins.add_trace(go.Bar(
                        name='Promedio Liga',
                        x=["Total", "Precisos"],
                        y=[comp_throw_ins, comp_throw_ins_accurate],
                        marker_color='#888888',
                        opacity=0.7,
                        text=[f"{comp_throw_ins:.1f}", f"{comp_throw_ins_accurate:.1f}"],
                        textposition=comp_throw_ins_positions,
                        insidetextanchor='middle',
                        textfont=dict(size=14, color='#FFFFFF', family='Arial Black'),  # Always white for league average labels
                        cliponaxis=False
                    ))
                    fig_throw_ins.update_layout(
                        barmode='group',
                        template='plotly_dark',
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        height=450,
                        margin=dict(t=100, b=60, l=50, r=50),  # Increased top margin for outside labels
                        yaxis_title="Por 90 Minutos",
                        showlegend=True,
                        legend=dict(font=dict(color='white')),
                        font=dict(color='white')
                    )
                    st.plotly_chart(fig_throw_ins, use_container_width=True, key=f"throw_ins_chart_{selected_opponent}")
                else:
                    st.info("No hay datos disponibles para el análisis de set pieces.")
        else:
            st.info("Selecciona un equipo para ver su análisis táctico.")


if __name__ == "__main__":
    main()
