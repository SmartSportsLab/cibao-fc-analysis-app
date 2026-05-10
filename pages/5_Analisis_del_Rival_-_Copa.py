# ===========================================
# 5_Analisis_del_Rival_-_Copa.py — Análisis del Rival - Copa Concacaf
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
    page_title="Análisis del Rival - Copa Concacaf | Cibao FC",
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
MATCHSTATS_DIR = REPO_ROOT / "data" / "raw" / "concacaf" / "matchstats"
MATCHES_DIR = REPO_ROOT / "data" / "raw" / "concacaf" / "matches"
CIBAO_TEAM_NAME = "Cibao"

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

@st.cache_data(ttl=300)  # Cache expires after 5 minutes (auto-refresh)
def load_all_matches() -> List[Dict]:
    """Carga todos los partidos desde los archivos JSON."""
    matches = []
    
    # Cargar desde matchstats
    if MATCHSTATS_DIR.exists():
        for json_file in MATCHSTATS_DIR.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    matches.append(data)
            except Exception as e:
                st.warning(f" Error cargando {json_file.name}: {e}")
                continue
    
    return matches


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


def get_cibao_matches(matches: List[Dict]) -> List[Dict]:
    """Filtra partidos donde juega Cibao."""
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


def get_upcoming_opponents(cibao_matches: List[Dict]) -> List[Tuple[str, Dict]]:
    """Identifica el próximo oponente basado en el primer partido no jugado."""
    today = datetime.now()
    
    # Separar partidos jugados y no jugados
    played_matches = []
    upcoming_matches = []
    
    for match in cibao_matches:
        status = match.get("status", "").lower()
        match_date = match.get("date")
        
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
    upcoming_matches.sort(key=lambda x: x.get("date") or datetime.max)
    
    # Solo tomar el PRIMER partido próximo (el más cercano)
    if upcoming_matches:
        next_match = upcoming_matches[0]
        opponent = next_match.get("opponent", "Desconocido")
        if opponent:
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
    team_name_lower = team_name.lower().strip()
    team_base = team_name_lower.replace(' fc', '').strip()
    
    for match in matches:
        # Los matches ya tienen la estructura de match_info (con home_team, away_team, etc.)
        match_info = match
        
        if not match_info:
            continue
        
        home = match_info.get("home_team", "")
        away = match_info.get("away_team", "")
        
        # Convertir a string y normalizar
        home_str = str(home).lower().strip() if home else ""
        away_str = str(away).lower().strip() if away else ""
        
        if filter_type == "home":
            # Solo partidos en casa
            home_match = (team_name_lower in home_str or home_str in team_name_lower or
                         team_base in home_str.replace(' fc', '').strip() or
                         home_str.replace(' fc', '').strip() in team_base)
            if home_match:
                filtered.append(match)
        
        elif filter_type == "away":
            # Solo partidos fuera
            away_match = (team_name_lower in away_str or away_str in team_name_lower or
                         team_base in away_str.replace(' fc', '').strip() or
                         away_str.replace(' fc', '').strip() in team_base)
            if away_match:
                filtered.append(match)
        
        elif filter_type == "vs_cibao":
            # Solo partidos contra Cibao
            home_match_cibao = (cibao_name_lower in home_str or home_str in cibao_name_lower or
                               cibao_base in home_str.replace(' fc', '').strip() or
                               home_str.replace(' fc', '').strip() in cibao_base)
            away_match_cibao = (cibao_name_lower in away_str or away_str in cibao_name_lower or
                               cibao_base in away_str.replace(' fc', '').strip() or
                               away_str.replace(' fc', '').strip() in cibao_base)
            home_match_team = (team_name_lower in home_str or home_str in team_name_lower or
                              team_base in home_str.replace(' fc', '').strip() or
                              home_str.replace(' fc', '').strip() in team_base)
            away_match_team = (team_name_lower in away_str or away_str in team_name_lower or
                              team_base in away_str.replace(' fc', '').strip() or
                              away_str.replace(' fc', '').strip() in team_base)
            
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
                value_num = float(value.replace('%', '').replace('A', '').replace('R', '').strip())
                comp_num = float(str(competition_avg).replace('%', '').replace('A', '').replace('R', '').strip())
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
                    f'<span>Comp: {competition_avg}</span>{indicator}'
                    f'</div>'
                )
            except (ValueError, AttributeError):
                # Si no se puede calcular, mostrar sin indicador
                comparison_parts.append(f'<div style="color: #64748B; font-size: 0.85rem; margin-top: 0.5rem;">Comp: {competition_avg}</div>')
        
        # Comparar con Cibao
        if cibao_avg is not None:
            try:
                value_num = float(value.replace('%', '').replace('A', '').replace('R', '').strip())
                cibao_num = float(str(cibao_avg).replace('%', '').replace('A', '').replace('R', '').strip())
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
                    f'<span>Cibao: {cibao_avg}</span>{indicator}'
                    f'</div>'
                )
            except (ValueError, AttributeError):
                # Si no se puede calcular, mostrar sin indicador
                comparison_parts.append(f'<div style="color: #FF9900; font-size: 0.85rem; margin-top: 0.25rem;">Cibao: {cibao_avg}</div>')
        
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
    sorted_matches = sorted(matches, key=lambda x: x.get("date") or datetime.min, reverse=True)
    
    # Obtener solo partidos jugados
    played_matches = [m for m in sorted_matches if m.get("status", "").lower() in ["played", "finished", "ft", "jugado", "finalizado"]]
    
    # Tomar los últimos N, evitando duplicados
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
    headers = ["#", "Fecha", "Oponente", "Resultado", "Marcador", "Lugar", "Disparos/Precisión", "Disparos Recibidos/Precisión"]
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
        
        # Create columns for this row - updated widths
        row_cols = st.columns([0.5, 1.5, 2, 1, 1, 1, 1.5, 1.5])
        
        with row_cols[0]:
            st.markdown(f"<div style='padding:0.5rem 0; color:#D1D5DB;'>{idx}</div>", unsafe_allow_html=True)
        with row_cols[1]:
            st.markdown(f"<div style='padding:0.5rem 0; color:#D1D5DB;'>{match['date']}</div>", unsafe_allow_html=True)
        with row_cols[2]:
            # Make the opponent name clickable
            if st.button(f" {match['opponent']}", key=f"row_btn_{idx-1}", use_container_width=True):
                st.session_state.selected_match_index = idx - 1
                st.rerun()
        with row_cols[3]:
            # Make the result emoji clickable for timeline
            if st.button(f"{match['result_emoji']}", key=f"timeline_btn_{idx-1}", use_container_width=True, help="Ver línea de tiempo"):
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
        "Tackles Totales": ("totalTackle", 20.0),
        "Despejes": ("totalClearance", 20.0),
        "Intercepciones": ("interception", 15.0),
        "Atajadas": ("saves", 8.0),
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
        
        # Obtener valores reales
        opp_val = opponent_metrics.get(metric_key, 0)
        cibao_val = cibao_metrics.get(metric_key, 0)
        
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


def analyze_formations(matches: List[Dict], team_name: str) -> Dict:
    """Analiza las formaciones utilizadas por un equipo."""
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
                    if team_name.lower() in name.lower():
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


def analyze_match_phases(matches: List[Dict], team_name: str) -> Dict:
    """Analiza el rendimiento por fases del partido."""
    phase_stats = {
        "first_15": {"goals_for": 0, "goals_against": 0, "matches": 0},
        "16_30": {"goals_for": 0, "goals_against": 0, "matches": 0},
        "31_45": {"goals_for": 0, "goals_against": 0, "matches": 0},
        "45_plus": {"goals_for": 0, "goals_against": 0, "matches": 0},
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
        phase_stats["45_plus"]["matches"] += 1
        phase_stats["46_60"]["matches"] += 1
        phase_stats["61_75"]["matches"] += 1
        phase_stats["76_90"]["matches"] += 1
        phase_stats["90_plus"]["matches"] += 1
        
        for goal in goals:
            goal_contestant_id = goal.get("contestantId", "")
            time = goal.get("timeMin", 0)
            period = goal.get("periodId") or goal.get("period") or 1
            
            # If period is missing, infer from time
            # First half is typically 0-45, second half is 46-90+
            if period is None or period == 0:
                if time <= 45:
                    period = 1
                else:
                    period = 2
            
            # Ensure period is an integer
            try:
                period = int(period)
            except (ValueError, TypeError):
                # Default to period 1 if conversion fails
                period = 1 if time <= 45 else 2
            
            # Determine if this goal is for the team we're analyzing
            is_team_goal = (goal_contestant_id == team_contestant_id)
            
            # First half phases (period 1)
            if period == 1:
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
                else:
                    # First half stoppage time (45+1' onwards in period 1)
                    if is_team_goal:
                        phase_stats["45_plus"]["goals_for"] += 1
                    else:
                        phase_stats["45_plus"]["goals_against"] += 1
            # Second half phases (period 2)
            elif period == 2:
                if time <= 60:
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
                    # Second half stoppage time (90+1' onwards in period 2)
                    if is_team_goal:
                        phase_stats["90_plus"]["goals_for"] += 1
                    else:
                        phase_stats["90_plus"]["goals_against"] += 1
            else:
                # Handle extra time periods (period 3, 4, etc.) or unknown periods
                # Infer phase from time
                if time <= 60:
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
                    # Stoppage time or extra time
                    if is_team_goal:
                        phase_stats["90_plus"]["goals_for"] += 1
                    else:
                        phase_stats["90_plus"]["goals_against"] += 1
    
    # Calcular promedios - ensure all phases have avg values even if 0
    for phase_key, phase in phase_stats.items():
        if phase["matches"] > 0:
            phase["avg_goals_for"] = phase["goals_for"] / phase["matches"]
            phase["avg_goals_against"] = phase["goals_against"] / phase["matches"]
        else:
            # Ensure averages are 0 if no matches
            phase["avg_goals_for"] = 0.0
            phase["avg_goals_against"] = 0.0
    
    # Ensure all required phases are present
    required_phases = ["first_15", "16_30", "31_45", "45_plus", "46_60", "61_75", "76_90", "90_plus"]
    for phase_key in required_phases:
        if phase_key not in phase_stats:
            phase_stats[phase_key] = {
                "goals_for": 0,
                "goals_against": 0,
                "matches": 0,
                "avg_goals_for": 0.0,
                "avg_goals_against": 0.0
            }
    
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


def get_text_color(hex_color):
    """Determine if text should be black or white based on color brightness."""
    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    # Calculate brightness (0-255)
    brightness = (r * 299 + g * 587 + b * 114) / 1000
    # If brightness is above 128, use black text; otherwise white
    return 'black' if brightness > 128 else 'white'

def create_phase_chart(phase_stats: Dict, team_color: str, metric_config: Dict = None):
    """Crea gráfico de fases del partido."""
    phases = ["0-15'", "16-30'", "31-45'", "45+1'", "46-60'", "61-75'", "76-90'", "90+1'"]
    phase_keys = ["first_15", "16_30", "31_45", "45_plus", "46_60", "61_75", "76_90", "90_plus"]
    
    # Default to average goals if no metric config provided
    if metric_config is None:
        metric_config = {
            "for_key": "avg_goals_for",
            "against_key": "avg_goals_against",
            "y_axis_title": "Promedio de Goles",
            "for_label": "Goles a Favor",
            "against_label": "Goles en Contra"
        }
    
    # Ensure all phase_keys exist in phase_stats
    for key in phase_keys:
        if key not in phase_stats:
            phase_stats[key] = {
                "goals_for": 0,
                "goals_against": 0,
                "matches": 0,
                "avg_goals_for": 0.0,
                "avg_goals_against": 0.0
            }
    
    # Get values based on selected metric
    if metric_config["for_key"] == "goal_difference":
        # Calculate difference for each phase (goals_for - goals_against)
        values_for = [
            phase_stats.get(key, {}).get("goals_for", 0) - phase_stats.get(key, {}).get("goals_against", 0)
            for key in phase_keys
        ]
        values_against = None  # Don't show second trace for difference
    else:
        values_for = [phase_stats.get(key, {}).get(metric_config["for_key"], 0) for key in phase_keys]
        if metric_config.get("against_key"):
            values_against = [phase_stats.get(key, {}).get(metric_config["against_key"], 0) for key in phase_keys]
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
    
    # Determine text colors based on bar color brightness
    goals_for_text_color = get_text_color(goals_for_color)
    
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
        goals_against_text_color = get_text_color(goals_against_color)
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
                if team_name.lower() in name.lower() or name.lower() in team_name.lower():
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
                st.metric("Goles a Favor", f"{most_used[1]['avg_goals_for']:.2f}")
            with col3:
                st.metric("Diferencia de Goles", f"{most_used[1]['avg_goal_difference']:+.2f}")


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
        xaxis=dict(tickangle=-45)
    )
    
    st.plotly_chart(fig, use_container_width=True)


# ===========================================
# INTERFAZ PRINCIPAL
# ===========================================

def main():
    # Título - standardized to match other pages
    titulo_naranja("Análisis del Rival — Copa Concacaf")
    st.markdown("""
    <p style='text-align:center; color:#D1D5DB; font-size:17px;'>
        Análisis detallado de oponentes para preparación táctica y estratégica
    </p>
    """, unsafe_allow_html=True)
    
    # Botón de actualización de datos
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button(" Actualizar Datos", type="primary", use_container_width=True, 
                     help="Actualiza los datos desde los archivos JSON más recientes"):
            # Limpiar cache y recargar
            load_all_matches.clear()
            st.rerun()
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Cargar datos
    with st.spinner("Cargando datos de partidos..."):
        all_matches = load_all_matches()
        cibao_matches = get_cibao_matches(all_matches)
    
    if not cibao_matches:
        st.error("No se encontraron partidos de Cibao. Verifique que los archivos JSON estén en la carpeta correcta.")
        return
    
    # Obtener todos los equipos de todos los partidos
    all_teams_list = get_all_teams_from_matches(all_matches)
    
    # Obtener oponentes de Cibao para marcar próximos
    upcoming_opponents = get_upcoming_opponents(cibao_matches)
    upcoming_opponent_names = {name for name, _ in upcoming_opponents}
    
    # Selector de equipo en la parte superior (visible)
    st.markdown("""
    <h2 style='color:#FF9900; text-align:center; margin-top:20px;'>Seleccionar Equipo para Analizar</h2>
    """, unsafe_allow_html=True)
    
    # Preparar opciones
    if upcoming_opponents:
        opponent_options = []
        opponent_map = {}
        
        for name, match_info in upcoming_opponents:
            display_name = f"{name} (Próximo)"
            opponent_options.append(display_name)
            opponent_map[display_name] = name
        
        for name in all_teams_list:
            if name not in upcoming_opponent_names and name != CIBAO_TEAM_NAME:
                opponent_options.append(name)
                opponent_map[name] = name
        
        if CIBAO_TEAM_NAME not in [opponent_map.get(opt, opt) for opt in opponent_options]:
            opponent_options.append(CIBAO_TEAM_NAME)
            opponent_map[CIBAO_TEAM_NAME] = CIBAO_TEAM_NAME
        
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
        default_index = 0
        for i, team in enumerate(all_teams_list):
            if team == "Defence Force":
                default_index = i
                break
        
        if "opponent_selector_index" not in st.session_state:
            st.session_state.opponent_selector_index = default_index
        
        selected_opponent = st.selectbox(
            "Seleccionar Equipo",
            options=all_teams_list,
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
        <h3 style='margin-top:0; color:#ff7b00;'>Análisis Copa</h3>
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
        
        if next_fixtures.get("concacaf"):
            concacaf_fixture = next_fixtures["concacaf"]
            st.markdown("**Copa Concacaf:**")
            if concacaf_fixture.get("date"):
                st.info(f" {concacaf_fixture.get('date', 'Por definir')}")
            if concacaf_fixture.get("opponent") and concacaf_fixture["opponent"] != "Por definir":
                st.info(f" vs {concacaf_fixture.get('opponent', 'Por definir')}")
        else:
            st.info("**Copa Concacaf:**\n\nSin próximos partidos disponibles")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
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
        
        # Encontrar partidos con este equipo (contra Cibao si es oponente, o todos si es otro equipo)
        if selected_opponent == CIBAO_TEAM_NAME:
            # Si es Cibao, mostrar partidos de Cibao
            team_matches = cibao_matches
            is_cibao = True
        else:
            # Si es otro equipo, buscar partidos contra Cibao
            team_matches = [m for m in cibao_matches if m.get("opponent") == selected_opponent]
            is_cibao = False
        
        if team_matches:
            # Ordenar por fecha
            team_matches.sort(key=lambda x: x.get("date") or datetime.min)
            
            # Último partido
            last_match = team_matches[-1]
            next_match = None
            
            # Buscar próximo partido (no jugado)
            for match in team_matches:
                status_lower = match.get("status", "").lower()
                if status_lower not in ["played", "finished", "ft", "jugado", "finalizado"]:
                    next_match = match
                    break
            
            if next_match:
                st.info(f"**Próximo partido:**\n{next_match.get('date_str', 'Por definir')}")
                if not is_cibao:
                    st.info(f"**Lugar:** {'Casa' if next_match.get('is_home') else 'Fuera'}")
            elif last_match:
                st.info(f"**Último encuentro:**\n{last_match.get('date_str', 'N/D')}")
                if not is_cibao:
                    st.info(f"**Lugar:** {'Casa' if last_match.get('is_home') else 'Fuera'}")
            
            if is_cibao:
                st.info(f"**Partidos totales:** {len(team_matches)}")
            else:
                st.info(f"**Partidos vs Cibao:** {len(team_matches)}")
    
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
        if selected_opponent == CIBAO_TEAM_NAME:
            # Si es Cibao, usar función específica
            team_all_matches = get_opponent_matches_data(all_matches, CIBAO_TEAM_NAME)
            team_averages = calculate_average_metrics(team_all_matches)
        else:
            # Si es otro equipo, obtener todos sus partidos
            team_all_matches = get_opponent_matches_data(all_matches, selected_opponent)
            team_averages = calculate_average_metrics(team_all_matches)
        
        cibao_averages = get_cibao_average_metrics(all_matches)
        competition_averages = get_all_teams_average_metrics(all_matches)
    
    # Preparar datos adicionales para análisis táctico
    matches_with_data = []
    for match_info in team_all_matches:
        match_id = match_info.get("match_id", "")
        for match_data in all_matches:
            match_info_check = extract_match_info(match_data)
            if match_info_check and match_info_check.get("match_id") == match_id:
                matches_with_data.append({
                    **match_info,
                    "match_data": match_data
                })
                break
    
    
    # Crear pestañas para organizar el contenido
    # Use session state to preserve selected tab across reruns
    if 'selected_tab_index' not in st.session_state:
        st.session_state.selected_tab_index = 0
    
    # Tab navigation using radio buttons (preserves state on rerun)
    tab_options = ["Resumen", "Comparación", "Jugadores Clave", "Análisis Táctico y Fases"]
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
    tab3 = selected_tab == "Jugadores Clave"
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
            col_info1, col_info2 = st.columns(2)
            with col_info1:
                # Contar partidos jugados - verificar status o si tiene score data
                played_count = 0
                for m in filtered_matches:
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
                st.metric("Partidos Jugados", played_count)
            with col_info2:
                if selected_opponent != CIBAO_TEAM_NAME:
                    # Contar partidos donde ambos equipos jugaron (head-to-head) - solo partidos jugados
                    h2h_count = 0
                    seen_match_ids = set()  # Para evitar duplicados
                    cibao_name_lower = CIBAO_TEAM_NAME.lower().strip()
                    cibao_base = cibao_name_lower.replace(' fc', '').strip()
                    opponent_name_lower = selected_opponent.lower().strip()
                    opponent_base = opponent_name_lower.replace(' fc', '').strip()
                    
                    for match_data in all_matches:
                        match_info = extract_match_info(match_data)
                        if not match_info:
                            continue
                        
                        match_id = match_info.get("match_id", "")
                        # Evitar duplicados
                        if match_id in seen_match_ids:
                            continue
                        
                        # Solo contar partidos jugados (no futuros)
                        status = match_info.get("status", "").lower()
                        date_str = match_info.get("date", "")
                        is_played = status in ["played", "finished", "ft", "jugado", "finalizado"]
                        
                        # También verificar por fecha si no hay status
                        if not is_played and date_str:
                            try:
                                from datetime import datetime
                                match_date = datetime.strptime(date_str, '%Y-%m-%d')
                                today = datetime.now()
                                if match_date > today:
                                    continue  # Es un partido futuro
                            except:
                                pass
                        
                        if not is_played:
                            continue  # Saltar partidos no jugados
                        
                        home = match_info.get("home_team", "").lower().strip() if match_info.get("home_team") else ""
                        away = match_info.get("away_team", "").lower().strip() if match_info.get("away_team") else ""
                        
                        # Verificar si ambos equipos están en el partido
                        home_match_cibao = (cibao_name_lower in home or home in cibao_name_lower or
                                           cibao_base in home.replace(' fc', '').strip() or
                                           home.replace(' fc', '').strip() in cibao_base)
                        away_match_cibao = (cibao_name_lower in away or away in cibao_name_lower or
                                           cibao_base in away.replace(' fc', '').strip() or
                                           away.replace(' fc', '').strip() in cibao_base)
                        
                        home_match_opponent = (opponent_name_lower in home or home in opponent_name_lower or
                                              opponent_base in home.replace(' fc', '').strip() or
                                              home.replace(' fc', '').strip() in opponent_base)
                        away_match_opponent = (opponent_name_lower in away or away in opponent_name_lower or
                                              opponent_base in away.replace(' fc', '').strip() or
                                              away.replace(' fc', '').strip() in opponent_base)
                        
                        if (home_match_cibao or away_match_cibao) and (home_match_opponent or away_match_opponent):
                            h2h_count += 1
                            seen_match_ids.add(match_id)
                    
                    st.metric("Partidos vs Cibao", h2h_count)
            
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
                recent_matches = get_recent_form(team_all_matches, selected_opponent, num_matches=3)
                filtered_matches_ui = []
                for match in recent_matches:
                    match_data = match.get("match_data")
                    if match_data:
                        opponent_stats = extract_team_stats_from_match(match_data, selected_opponent)
                        if opponent_stats:
                            match["opponent_stats"] = opponent_stats
                            filtered_matches_ui.append(match)
            elif filter_type_ui == "last_5":
                recent_matches = get_recent_form(team_all_matches, selected_opponent, num_matches=5)
                filtered_matches_ui = []
                for match in recent_matches:
                    match_data = match.get("match_data")
                    if match_data:
                        opponent_stats = extract_team_stats_from_match(match_data, selected_opponent)
                        if opponent_stats:
                            match["opponent_stats"] = opponent_stats
                            filtered_matches_ui.append(match)
            else:
                filtered_matches_ui = filter_matches_by_type(team_all_matches, selected_opponent, filter_type_ui, all_matches)
            filtered_averages_ui = calculate_average_metrics(filtered_matches_ui) if filtered_matches_ui else {}
            display_averages_ui = filtered_averages_ui if filtered_averages_ui else team_averages
            
            # Calcular promedios filtrados de competencia y Cibao
            filtered_competition_averages = get_all_teams_average_metrics(all_matches, filter_type_ui, selected_opponent)
            filtered_cibao_averages = get_cibao_average_metrics_filtered(all_matches, filter_type_ui, selected_opponent)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Mostrar resumen de partidos (directamente arriba de Métricas Clave - 12 KPI cards)
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
                st.metric("Partidos Jugados", played_count)
            with col_info2:
                if selected_opponent != CIBAO_TEAM_NAME:
                    # Contar partidos donde ambos equipos jugaron (head-to-head) - solo partidos jugados
                    h2h_count = 0
                    seen_match_ids = set()  # Para evitar duplicados
                    cibao_name_lower = CIBAO_TEAM_NAME.lower().strip()
                    cibao_base = cibao_name_lower.replace(' fc', '').strip()
                    opponent_name_lower = selected_opponent.lower().strip()
                    opponent_base = opponent_name_lower.replace(' fc', '').strip()
                    
                    for match_data in all_matches:
                        match_info = extract_match_info(match_data)
                        if not match_info:
                            continue
                        
                        match_id = match_info.get("match_id", "")
                        # Evitar duplicados
                        if match_id in seen_match_ids:
                            continue
                        
                        # Solo contar partidos jugados (no futuros)
                        status = match_info.get("status", "").lower()
                        date_str = match_info.get("date", "")
                        is_played = status in ["played", "finished", "ft", "jugado", "finalizado"]
                        
                        # También verificar por fecha si no hay status
                        if not is_played and date_str:
                            try:
                                from datetime import datetime
                                match_date = datetime.strptime(date_str, '%Y-%m-%d')
                                today = datetime.now()
                                if match_date > today:
                                    continue  # Es un partido futuro
                            except:
                                pass
                        
                        if not is_played:
                            continue  # Saltar partidos no jugados
                        
                        home = match_info.get("home_team", "").lower().strip() if match_info.get("home_team") else ""
                        away = match_info.get("away_team", "").lower().strip() if match_info.get("away_team") else ""
                        
                        # Verificar si ambos equipos están en el partido
                        home_match_cibao = (cibao_name_lower in home or home in cibao_name_lower or
                                           cibao_base in home.replace(' fc', '').strip() or
                                           home.replace(' fc', '').strip() in cibao_base)
                        away_match_cibao = (cibao_name_lower in away or away in cibao_name_lower or
                                           cibao_base in away.replace(' fc', '').strip() or
                                           away.replace(' fc', '').strip() in cibao_base)
                        home_match_opponent = (opponent_name_lower in home or home in opponent_name_lower or
                                              opponent_base in home.replace(' fc', '').strip() or
                                              home.replace(' fc', '').strip() in opponent_base)
                        away_match_opponent = (opponent_name_lower in away or away in opponent_name_lower or
                                              opponent_base in away.replace(' fc', '').strip() or
                                              away.replace(' fc', '').strip() in opponent_base)
                        
                        if (home_match_cibao or away_match_cibao) and (home_match_opponent or away_match_opponent):
                            h2h_count += 1
                            seen_match_ids.add(match_id)
                    
                    st.metric("Partidos vs Cibao", h2h_count)
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("""
            <h2 style='color:#FF9900; text-align:center; margin-top:20px;'>Métricas Clave</h2>
            """, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Fila 1: Ofensivas
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                goals = display_averages_ui.get("goals", 0)
                comp_goals = filtered_competition_averages.get("goals", 0) if filtered_competition_averages else 0
                cibao_goals = filtered_cibao_averages.get("goals", 0) if filtered_cibao_averages else 0
                display_metric_card(
                    "Goles por 90 min",
                    f"{goals:.2f}",
                    "",
                    f"Promedio en {len(filtered_matches_ui)} partidos",
                    competition_avg=f"{comp_goals:.2f}",
                    cibao_avg=f"{cibao_goals:.2f}"
                )
            
            with col2:
                shots = display_averages_ui.get("totalScoringAtt", 0)
                shots_on_target = display_averages_ui.get("ontargetScoringAtt", 0)
                shot_accuracy = (shots_on_target / shots * 100) if shots > 0 else 0
                comp_shots = filtered_competition_averages.get("totalScoringAtt", 0) if filtered_competition_averages else 0
                cibao_shots = filtered_cibao_averages.get("totalScoringAtt", 0) if filtered_cibao_averages else 0
                display_metric_card(
                    "Disparos por 90 min",
                    f"{shots:.1f}",
                    "",
                    f"{shot_accuracy:.1f}% precisión",
                    competition_avg=f"{comp_shots:.1f}",
                    cibao_avg=f"{cibao_shots:.1f}"
                )
            
            with col3:
                shots_on_target = display_averages_ui.get("ontargetScoringAtt", 0)
                comp_sot = filtered_competition_averages.get("ontargetScoringAtt", 0) if filtered_competition_averages else 0
                cibao_sot = filtered_cibao_averages.get("ontargetScoringAtt", 0) if filtered_cibao_averages else 0
                display_metric_card(
                    "Disparos al Arco por 90 min",
                    f"{shots_on_target:.1f}",
                    "",
                    f"Por 90 minutos",
                    competition_avg=f"{comp_sot:.1f}",
                    cibao_avg=f"{cibao_sot:.1f}"
                )
            
            with col4:
                possession = display_averages_ui.get("possessionPercentage", 0)
                comp_poss = filtered_competition_averages.get("possessionPercentage", 0) if filtered_competition_averages else 0
                cibao_poss = filtered_cibao_averages.get("possessionPercentage", 0) if filtered_cibao_averages else 0
                display_metric_card(
                    "Posesión %",
                    f"{possession:.1f}%",
                    "",
                    f"Promedio",
                )
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Fila 2: Defensivas
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                goals_conceded = display_averages_ui.get("goalsConceded", 0)
                comp_gc = filtered_competition_averages.get("goalsConceded", 0) if filtered_competition_averages else 0
                cibao_gc = filtered_cibao_averages.get("goalsConceded", 0) if filtered_cibao_averages else 0
                display_metric_card(
                    "Goles Recibidos por 90 min",
                    f"{goals_conceded:.2f}",
                    "",
                    f"Por 90 minutos",
                    competition_avg=f"{comp_gc:.2f}",
                    cibao_avg=f"{cibao_gc:.2f}",
                    higher_is_better=False  # Lower is better for goals conceded
                )
            
            with col2:
                saves = display_averages_ui.get("saves", 0)
                comp_saves = filtered_competition_averages.get("saves", 0) if filtered_competition_averages else 0
                cibao_saves = filtered_cibao_averages.get("saves", 0) if filtered_cibao_averages else 0
                display_metric_card(
                    "Atajadas por 90 min",
                    f"{saves:.1f}",
                    "",
                    f"Por 90 minutos",
                    competition_avg=f"{comp_saves:.1f}",
                    cibao_avg=f"{cibao_saves:.1f}"
                )
            
            with col3:
                clearances = display_averages_ui.get("totalClearance", 0)
                comp_clear = filtered_competition_averages.get("totalClearance", 0) if filtered_competition_averages else 0
                cibao_clear = filtered_cibao_averages.get("totalClearance", 0) if filtered_cibao_averages else 0
                display_metric_card(
                    "Despejes por 90 min",
                    f"{clearances:.1f}",
                    "",
                    f"Por 90 minutos",
                    competition_avg=f"{comp_clear:.1f}",
                    cibao_avg=f"{cibao_clear:.1f}"
                )
            
            with col4:
                tackles_won = display_averages_ui.get("wonTackle", 0)
                tackle_success = display_averages_ui.get("tackleSuccess", 0)
                comp_tackles = filtered_competition_averages.get("wonTackle", 0) if filtered_competition_averages else 0
                cibao_tackles = filtered_cibao_averages.get("wonTackle", 0) if filtered_cibao_averages else 0
                display_metric_card(
                    "Tackles Exitosos por 90 min",
                    f"{tackles_won:.1f}",
                    "",
                    f"{tackle_success:.1f}% efectividad",
                    competition_avg=f"{comp_tackles:.1f}",
                    cibao_avg=f"{cibao_tackles:.1f}"
                )
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Fila 3: Set Pieces y Disciplina
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                corners_won = display_averages_ui.get("wonCorners", 0)
                comp_corners = filtered_competition_averages.get("wonCorners", 0) if filtered_competition_averages else 0
                cibao_corners = filtered_cibao_averages.get("wonCorners", 0) if filtered_cibao_averages else 0
                display_metric_card(
                    "Corners Ganados por 90 min",
                    f"{corners_won:.1f}",
                    "",
                    f"Por 90 minutos",
                    competition_avg=f"{comp_corners:.1f}",
                    cibao_avg=f"{cibao_corners:.1f}"
                )
            
            with col2:
                pass_accuracy = display_averages_ui.get("passAccuracy", 0)
                comp_pass_acc = filtered_competition_averages.get("passAccuracy", 0) if filtered_competition_averages else 0
                cibao_pass_acc = filtered_cibao_averages.get("passAccuracy", 0) if filtered_cibao_averages else 0
                display_metric_card(
                    "Precisión de Pases",
                    f"{pass_accuracy:.1f}%",
                    "",
                    f"Promedio",
                    competition_avg=f"{comp_pass_acc:.1f}%",
                    cibao_avg=f"{cibao_pass_acc:.1f}%"
                )
            
            with col3:
                fouls = display_averages_ui.get("fkFoulLost", 0)
                comp_fouls = filtered_competition_averages.get("fkFoulLost", 0) if filtered_competition_averages else 0
                cibao_fouls = filtered_cibao_averages.get("fkFoulLost", 0) if filtered_cibao_averages else 0
                display_metric_card(
                    "Faltas Cometidas",
                    f"{fouls:.1f}",
                    "",
                    f"Por partido",
                    competition_avg=f"{comp_fouls:.1f}",
                    cibao_avg=f"{cibao_fouls:.1f}",
                    higher_is_better=False  # Lower is better for fouls
                )
            
            with col4:
                yellow_cards = display_averages_ui.get("totalYellowCard", 0)
                red_cards = display_averages_ui.get("totalRedCard", 0)
                total_cards = yellow_cards + red_cards
                comp_yellow = filtered_competition_averages.get("totalYellowCard", 0) if filtered_competition_averages else 0
                comp_red = filtered_competition_averages.get("totalRedCard", 0) if filtered_competition_averages else 0
                comp_total = comp_yellow + comp_red
                cibao_yellow = filtered_cibao_averages.get("totalYellowCard", 0) if filtered_cibao_averages else 0
                cibao_red = filtered_cibao_averages.get("totalRedCard", 0) if filtered_cibao_averages else 0
                cibao_total = cibao_yellow + cibao_red
                display_metric_card(
                    "Tarjetas",
                    f"{total_cards:.1f}",
                    "",
                    f"{yellow_cards:.1f}A, {red_cards:.1f}R",
                    competition_avg=f"{comp_total:.1f}",
                    cibao_avg=f"{cibao_total:.1f}",
                    higher_is_better=False  # Lower is better for cards
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
                # Get recent form - this returns matches with match_data
                recent_opponent = get_recent_form(team_all_matches, selected_opponent, num_matches=3)
                # Re-extract stats for the filtered matches to ensure they're available
                filtered_team_matches = []
                for match in recent_opponent:
                    match_data = match.get("match_data")
                    if match_data:
                        opponent_stats = extract_team_stats_from_match(match_data, selected_opponent)
                        if opponent_stats:
                            match["opponent_stats"] = opponent_stats
                            filtered_team_matches.append(match)
                filter_type = "all"
            elif comparison_filter == "Últimos 5 partidos":
                # Get recent form - this returns matches with match_data
                recent_opponent = get_recent_form(team_all_matches, selected_opponent, num_matches=5)
                # Re-extract stats for the filtered matches to ensure they're available
                filtered_team_matches = []
                for match in recent_opponent:
                    match_data = match.get("match_data")
                    if match_data:
                        opponent_stats = extract_team_stats_from_match(match_data, selected_opponent)
                        if opponent_stats:
                            match["opponent_stats"] = opponent_stats
                            filtered_team_matches.append(match)
                filter_type = "all"
            elif comparison_filter == "En Casa":
                filtered_team_matches = filter_matches_by_type(team_all_matches, selected_opponent, "home", all_matches)
                filter_type = "home"
            elif comparison_filter == "Fuera":
                filtered_team_matches = filter_matches_by_type(team_all_matches, selected_opponent, "away", all_matches)
                filter_type = "away"
            
            # Recalculate opponent averages with filtered matches
            filtered_team_averages = calculate_average_metrics(filtered_team_matches) if filtered_team_matches else team_averages
            
            # For Cibao, build matches with stats properly extracted
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
                        match_info["match_data"] = match_data  # Ensure match_data is available
                        cibao_matches_with_stats.append(match_info)
            
            # Apply filters to Cibao matches
            if comparison_filter == "Últimos 3 partidos":
                # Get recent form - this returns matches with match_data
                recent_cibao = get_recent_form(cibao_matches_with_stats, CIBAO_TEAM_NAME, num_matches=3)
                # Re-extract stats for the filtered matches to ensure they're available
                filtered_cibao_matches = []
                for match in recent_cibao:
                    match_data = match.get("match_data")
                    if match_data:
                        cibao_stats = extract_team_stats_from_match(match_data, CIBAO_TEAM_NAME)
                        if cibao_stats:
                            match["cibao_stats"] = cibao_stats
                            filtered_cibao_matches.append(match)
            elif comparison_filter == "Últimos 5 partidos":
                # Get recent form - this returns matches with match_data
                recent_cibao = get_recent_form(cibao_matches_with_stats, CIBAO_TEAM_NAME, num_matches=5)
                # Re-extract stats for the filtered matches to ensure they're available
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
                filtered_cibao_averages = calculate_average_metrics_from_matches(filtered_cibao_matches, "cibao_stats")
            else:
                filtered_cibao_averages = cibao_averages
            
            # Use filtered averages for all charts
            comparison_team_averages = filtered_team_averages
            comparison_cibao_averages = filtered_cibao_averages
            
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
                "Corners", "Tackles Exitosos", "Tackles Totales", "Despejes",
                "Intercepciones", "Atajadas", "Faltas", "Tarjetas Amarillas"
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
                "Tackles Totales por 90 min": {
                    "key": "totalTackle",
                    "chart_type": "bar",
                    "unit": "tackles",
                    "category": "Defensiva"
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
                "Atajadas por 90 min": {
                    "key": "saves",
                    "chart_type": "bar",
                    "unit": "atajadas",
                    "category": "Defensiva"
                },
                "Faltas Cometidas por 90 min": {
                    "key": "fkFoulLost",
                    "chart_type": "bar",
                    "unit": "faltas",
                    "category": "Disciplina",
                    "invert": True
                },
                "Faltas Recibidas por 90 min": {
                    "key": "fkFoulWon",
                    "chart_type": "bar",
                    "unit": "faltas",
                    "category": "Disciplina"
                },
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
                                xaxis=dict(tickangle=-45),
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
            
            # Get discipline metrics
            opp_yellow = comparison_team_averages.get("totalYellowCard", 0)
            opp_red = comparison_team_averages.get("totalRedCard", 0)
            opp_fouls_committed = comparison_team_averages.get("fkFoulLost", 0)
            opp_fouls_won = comparison_team_averages.get("fkFoulWon", 0)
            
            cibao_yellow = comparison_cibao_averages.get("totalYellowCard", 0)
            cibao_red = comparison_cibao_averages.get("totalRedCard", 0)
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
                st.metric("Faltas Recibidas", f"{opp_fouls_won:.1f}")
            
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
                
                fig_cards = go.Figure()
                fig_cards.add_trace(go.Bar(
                    name=selected_opponent,
                    x=card_categories,
                    y=opponent_card_vals,
                    marker_color='#FFFFFF',
                    marker_line=dict(width=0),
                    text=[f"{v:.1f}" for v in opponent_card_vals],
                    textposition='inside',
                    textfont=dict(size=14, color=opponent_text_color, family='Arial Black')
                ))
                
                fig_cards.add_trace(go.Bar(
                    name='Cibao',
                    x=card_categories,
                    y=cibao_card_vals,
                    marker_color='#FF8C00',
                    marker_line=dict(width=0),
                    text=[f"{v:.1f}" for v in cibao_card_vals],
                    textposition='inside',
                    textfont=dict(size=14, color=cibao_text_color, family='Arial Black')
                ))
                
                fig_cards.update_layout(
                    template='plotly_dark',
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    height=400,
                    title="Tarjetas",
                    xaxis_title="Tipo de Tarjeta",
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
                
                st.plotly_chart(fig_cards, use_container_width=True)
            
            # Chart 2: Fouls
            with col2:
                foul_categories = ["Faltas\nCometidas", "Faltas\nRecibidas"]
                opponent_foul_vals = [opp_fouls_committed, opp_fouls_won]
                cibao_foul_vals = [cibao_fouls_committed, cibao_fouls_won]
                
                fig_fouls = go.Figure()
                fig_fouls.add_trace(go.Bar(
                    name=selected_opponent,
                    x=foul_categories,
                    y=opponent_foul_vals,
                    marker_color='#FFFFFF',
                    marker_line=dict(width=0),
                    text=[f"{v:.1f}" for v in opponent_foul_vals],
                    textposition='inside',
                    textfont=dict(size=14, color=opponent_text_color, family='Arial Black')
                ))
                
                fig_fouls.add_trace(go.Bar(
                    name='Cibao',
                    x=foul_categories,
                    y=cibao_foul_vals,
                    marker_color='#FF8C00',
                    marker_line=dict(width=0),
                    text=[f"{v:.1f}" for v in cibao_foul_vals],
                    textposition='inside',
                    textfont=dict(size=14, color=cibao_text_color, family='Arial Black')
                ))
                
                fig_fouls.update_layout(
                    template='plotly_dark',
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    height=400,
                    title="Faltas",
                    xaxis_title="Tipo de Falta",
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
            
            # Get offside data
            opp_offsides = comparison_team_averages.get("totalOffside", 0)
            cibao_offsides = comparison_cibao_averages.get("totalOffside", 0)
            
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
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                name=selected_opponent,
                x=categories,
                y=opponent_vals,
                marker_color='#FFFFFF',
                marker_line=dict(width=0),
                text=[f"{v:.1f}" for v in opponent_vals],
                textposition='inside',
                textfont=dict(size=14, color=opponent_text_color, family='Arial Black')
            ))
            
            fig.add_trace(go.Bar(
                name='Cibao',
                x=categories,
                y=cibao_vals,
                marker_color='#FF8C00',
                marker_line=dict(width=0),
                text=[f"{v:.1f}" for v in cibao_vals],
                textposition='inside',
                textfont=dict(size=14, color=cibao_text_color, family='Arial Black')
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
            
            # Player Offside Analysis Table
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("""
            <h3 style='color:#FF9900; margin-top:20px;'>Jugadores con Más Fuera de Juego</h3>
            """, unsafe_allow_html=True)
            
            # Get player stats for opponent (use team_all_matches which is available in Tab 2)
            if team_all_matches:
                player_stats = extract_player_stats_from_matches(team_all_matches, selected_opponent)
                
                # Filter players with offsides and calculate per 90
                player_offside_data = []
                for player_id, stats in player_stats.items():
                    total_offsides = stats.get("offsides", 0)
                    total_minutes = stats.get("total_minutes", 0)
                    
                    if total_offsides > 0 and total_minutes > 0:
                        offsides_per_90 = (total_offsides / total_minutes) * 90
                        player_position = stats.get("position", "N/A")
                        
                        player_offside_data.append({
                            "Jugador": stats.get("name", "N/A"),
                            "Posición": player_position,
                            "Total Fuera de Juego": int(total_offsides),
                            "Fuera de Juego por 90 min": round(offsides_per_90, 2),
                            "Minutos Jugados": int(total_minutes)
                        })
                
                # Sort by total offsides (descending)
                player_offside_data.sort(key=lambda x: x["Total Fuera de Juego"], reverse=True)
                
                if player_offside_data:
                    # Create DataFrame
                    df_offside_players = pd.DataFrame(player_offside_data)
                    st.dataframe(df_offside_players, use_container_width=True, hide_index=True)
                else:
                    st.info("No hay datos de fuera de juego a nivel de jugador disponibles.")
            else:
                st.info("No hay partidos disponibles para analizar jugadores.")
            
            # Get team color for opponent (for charts) - always white in comparison tab
            opponent_color = '#FFFFFF'  # Always white for opponent in comparison tab
            
            opp_text_color = get_text_color(opponent_color)
            cibao_text_color = get_text_color(CIBAO_COLOR)
            
            # ========== SECCIÓN: SUBSTITUTION PATTERNS ==========
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("---")
            st.markdown("""
            <h2 style='color:#FF9900; text-align:center; margin-top:20px;'>Patrones de Sustituciones</h2>
            """, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Get substitution data
            opp_subs = comparison_team_averages.get("subsMade", 0)
            cibao_subs = comparison_cibao_averages.get("subsMade", 0)
            
            # KPI Cards for Substitutions
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric(f"Sustituciones ({selected_opponent})", f"{opp_subs:.1f}")
            with col2:
                st.metric("Sustituciones (Cibao)", f"{cibao_subs:.1f}")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Substitution Comparison Chart
            categories = ["Sustituciones"]
            opponent_vals = [opp_subs]
            cibao_vals = [cibao_subs]
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                name=selected_opponent,
                x=categories,
                y=opponent_vals,
                marker_color=opponent_color,
                marker_line=dict(width=0),
                text=[f"{v:.1f}" for v in opponent_vals],
                textposition='inside',
                textfont=dict(color=opp_text_color, size=14, family='Arial Black')
            ))
            fig.add_trace(go.Bar(
                name="Cibao",
                x=categories,
                y=cibao_vals,
                marker_color=CIBAO_COLOR,
                marker_line=dict(width=0),
                text=[f"{v:.1f}" for v in cibao_vals],
                textposition='inside',
                textfont=dict(color=cibao_text_color, size=14, family='Arial Black')
            ))
            
            fig.update_layout(
                template='plotly_dark',
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                height=400,
                title="Comparación de Sustituciones",
                xaxis_title="",
                yaxis_title="Promedio por Partido",
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
            if opp_subs > cibao_subs * 1.2:
                st.info(f"**{selected_opponent} hace más sustituciones** ({opp_subs:.1f} vs {cibao_subs:.1f} de Cibao). Esto puede indicar un estilo de juego más rotativo o mayor profundidad en el banquillo.")
            elif cibao_subs > opp_subs * 1.2:
                st.info(f"**Cibao hace más sustituciones** ({cibao_subs:.1f} vs {opp_subs:.1f} del oponente). El oponente tiende a mantener más estabilidad en su alineación.")
            else:
                st.info(f"**Niveles similares de sustituciones** ({opp_subs:.1f} vs {cibao_subs:.1f} de Cibao).")
            
            # ========== SECCIÓN: POSSESSION PATTERNS ==========
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("---")
            st.markdown("""
            <h2 style='color:#FF9900; text-align:center; margin-top:20px;'>Patrones de Posesión</h2>
            """, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Get possession data
            opp_possession = comparison_team_averages.get("possessionPercentage", 0)
            cibao_possession = comparison_cibao_averages.get("possessionPercentage", 0)
            
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
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                name=selected_opponent,
                x=categories,
                y=opponent_vals,
                marker_color=opponent_color,
                marker_line=dict(width=0),
                text=[f"{v:.1f}%" for v in opponent_vals],
                textposition='inside',
                textfont=dict(color=opp_text_color, size=14, family='Arial Black')
            ))
            fig.add_trace(go.Bar(
                name="Cibao",
                x=categories,
                y=cibao_vals,
                marker_color=CIBAO_COLOR,
                marker_line=dict(width=0),
                text=[f"{v:.1f}%" for v in cibao_vals],
                textposition='inside',
                textfont=dict(color=cibao_text_color, size=14, family='Arial Black')
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
            
            # Get passing data
            opp_total_passes = comparison_team_averages.get("totalPass", 0)
            opp_accurate_passes = comparison_team_averages.get("accuratePass", 0)
            opp_pass_accuracy = (opp_accurate_passes / opp_total_passes * 100) if opp_total_passes > 0 else 0
            
            cibao_total_passes = comparison_cibao_averages.get("totalPass", 0)
            cibao_accurate_passes = comparison_cibao_averages.get("accuratePass", 0)
            cibao_pass_accuracy = (cibao_accurate_passes / cibao_total_passes * 100) if cibao_total_passes > 0 else 0
            
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
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                name=selected_opponent,
                x=categories,
                y=opp_display_vals,
                marker_color=opponent_color,
                marker_line=dict(width=0),
                text=[f"{v:.0f}" if i < 2 else f"{v:.1f}%" for i, v in enumerate(opp_display_vals)],
                textposition='inside',
                textfont=dict(color=opp_text_color, size=14, family='Arial Black')
            ))
            fig.add_trace(go.Bar(
                name="Cibao",
                x=categories,
                y=cibao_display_vals,
                marker_color=CIBAO_COLOR,
                marker_line=dict(width=0),
                text=[f"{v:.0f}" if i < 2 else f"{v:.1f}%" for i, v in enumerate(cibao_display_vals)],
                textposition='inside',
                textfont=dict(color=cibao_text_color, size=14, family='Arial Black')
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
    
    # TAB 3: KEY PLAYERS (Jugadores Clave)
    if tab3:
        if selected_opponent and selected_opponent != CIBAO_TEAM_NAME:
            st.markdown("""
            <h2 style='color:#FF9900; text-align:center; margin-top:20px;'>Jugadores Clave de {opponent}</h2>
            """.format(opponent=selected_opponent), unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Get all matches for the opponent
            opponent_matches = get_opponent_matches_data(all_matches, selected_opponent)
            
            if opponent_matches:
                # Extract player stats from all opponent matches
                player_stats = extract_player_stats_from_matches(opponent_matches, selected_opponent)
                
                if player_stats:
                    # Display key players analysis
                    display_key_players_analysis(player_stats, selected_opponent)
                else:
                    st.info("No se pudieron extraer estadísticas de jugadores para este equipo.")
            else:
                st.info("No hay partidos disponibles para este equipo.")
        elif selected_opponent == CIBAO_TEAM_NAME:
            st.info("Selecciona otro equipo para ver sus jugadores clave.")
        else:
            st.warning("Selecciona un equipo para ver sus jugadores clave.")
    
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
            
            # Debug: mostrar el color obtenido
            with st.expander("Debug: Color del Equipo", expanded=False):
                st.write(f"**Equipo seleccionado:** {selected_opponent}")
                st.write(f"**Color obtenido del CSV:** {team_color}")
                st.write(f"**Es Cibao?:** {selected_opponent == CIBAO_TEAM_NAME}")
                st.write(f"**Color de Cibao (CSV):** {cibao_csv_color}")
                st.write(f"**Color de Cibao (constante):** {CIBAO_COLOR}")
                st.write(f"**¿Son iguales?:** {team_color == cibao_csv_color}")
                
                # Show which variation matched (matched_variation is set above)
                if matched_variation:
                    st.write(f" **Variación que coincidió:** '{matched_variation}' = {current_colors[matched_variation]}")
                else:
                    st.write(f" **No se encontró coincidencia exacta** - usando color por defecto: {team_color}")
                
                st.write(f"**Colores disponibles en CSV (equipos principales):**")
                # Show only the original team names (not lowercase variations)
                original_teams = sorted([k for k in current_colors.keys() if k[0].isupper() or k == 'cibao'])
                for team in original_teams[:15]:  # Show first 15 to avoid clutter
                    if team in current_colors:
                        st.write(f"  - {team}: {current_colors[team]}")
                
                st.color_picker("Color Visualizado", value=team_color, key="debug_color_picker", disabled=True)
            
            # Get matches for the selected team
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
            
            if not played_matches:
                st.info("No hay partidos jugados disponibles para este equipo.")
            else:
                st.markdown(f"""
                <h2 style='color:#FF9900; text-align:center; margin-top:20px;'>Análisis Táctico y Fases del Partido — {selected_opponent}</h2>
                """, unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)
                
                # Obtener formaciones disponibles para el filtro
                formation_stats = analyze_formations(played_matches, selected_opponent)
                available_formations = list(formation_stats.keys())
                
                # Filtro de formación
                if available_formations:
                    selected_formation = st.selectbox(
                        "Filtrar por Formación",
                        options=["Todas las Formaciones"] + available_formations,
                        index=0,
                        key="formation_filter_tactical"
                    )
                    
                    # Filtrar partidos por formación si se selecciona una
                    if selected_formation != "Todas las Formaciones":
                        filtered_matches = []
                        for match in played_matches:
                            match_data = match.get("match_data")
                            if match_data:
                                formation = extract_formation_from_match(match_data, selected_opponent)
                                if formation == selected_formation:
                                    filtered_matches.append(match)
                        played_matches = filtered_matches
                        
                        # Recalcular estadísticas con partidos filtrados
                        formation_stats = analyze_formations(played_matches, selected_opponent)
                else:
                    selected_formation = "Todas las Formaciones"
                
                # ========== SECCIÓN 1: FORMACIONES ==========
                st.markdown("---")
                st.markdown("""
                <h3 style='color:#FF9900; margin-top:20px;'>Formaciones</h3>
                """, unsafe_allow_html=True)
                
                if not formation_stats:
                    st.info("No hay datos de formaciones disponibles.")
                else:
                    total_matches = sum([s["count"] for s in formation_stats.values()])
                    most_used = max(formation_stats.items(), key=lambda x: x[1]["count"])
                    best_formation = max([(f, s) for f, s in formation_stats.items() if s["count"] >= 2], 
                                       key=lambda x: x[1].get("win_rate", 0), default=(None, None))
                    
                    # Calculate overall averages for comparison
                    total_wins = sum([s["wins"] for s in formation_stats.values()])
                    total_draws = sum([s["draws"] for s in formation_stats.values()])
                    total_losses = sum([s["losses"] for s in formation_stats.values()])
                    overall_win_rate = (total_wins / total_matches * 100) if total_matches > 0 else 0
                    
                    total_goals_for = sum([s.get("goals_for", 0) for s in formation_stats.values()])
                    total_goals_against = sum([s.get("goals_against", 0) for s in formation_stats.values()])
                    avg_goals_for = total_goals_for / total_matches if total_matches > 0 else 0
                    avg_goals_against = total_goals_against / total_matches if total_matches > 0 else 0
                    
                    # Get best formation stats
                    best_win_rate = best_formation[1].get("win_rate", 0) if best_formation[0] else 0
                    most_used_count = most_used[1]["count"] if most_used else 0
                    most_used_percentage = (most_used_count / total_matches * 100) if total_matches > 0 else 0
                    
                    # KPI Tiles in 3x4 grid (3 rows, 4 columns)
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    # Row 1
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        display_metric_card(
                            "Total de Formaciones",
                            f"{len(formation_stats)}",
                            "",
                            f"Formaciones únicas utilizadas",
                            color="normal"
                        )
                    
                    with col2:
                        display_metric_card(
                            "Partidos Analizados",
                            f"{total_matches}",
                            "",
                            f"Total de partidos con datos",
                            color="normal"
                        )
                    
                    with col3:
                        display_metric_card(
                            "Formación Más Usada",
                            format_formation(most_used[0]) if most_used else "N/A",
                            "",
                            f"{most_used_percentage:.1f}% de los partidos" if most_used else "Sin datos",
                            color="normal"
                        )
                    
                    with col4:
                        if best_formation[0]:
                            display_metric_card(
                                "Mejor Formación",
                                format_formation(best_formation[0]),
                                "",
                                f"{best_win_rate:.1f}% tasa de victoria",
                                color="normal"
                            )
                        else:
                            display_metric_card(
                                "Mejor Formación",
                                "N/A",
                                "",
                                "Datos insuficientes",
                                color="normal"
                            )
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    # Row 2
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        display_metric_card(
                            "Tasa de Victoria",
                            f"{overall_win_rate:.1f}%",
                            "",
                            f"{total_wins} victorias en {total_matches} partidos",
                            color="normal"
                        )
                    
                    with col2:
                        display_metric_card(
                            "Goles por Partido",
                            f"{avg_goals_for:.2f}",
                            "",
                            f"Promedio a favor",
                            color="normal"
                        )
                    
                    with col3:
                        display_metric_card(
                            "Goles Recibidos",
                            f"{avg_goals_against:.2f}",
                            "",
                            f"Promedio en contra",
                            color="normal"
                        )
                    
                    with col4:
                        goal_diff = avg_goals_for - avg_goals_against
                        display_metric_card(
                            "Diferencia de Goles",
                            f"{goal_diff:+.2f}",
                            "",
                            f"Por partido",
                            color="normal"
                        )
                    
                    # Tabla detallada
                    formation_data = []
                    for formation, stats in sorted(formation_stats.items(), key=lambda x: x[1]["count"], reverse=True):
                        formation_data.append({
                            "Formación": format_formation(formation),
                            "Partidos": stats["count"],
                            "Victorias": stats["wins"],
                            "Empates": stats["draws"],
                            "Derrotas": stats["losses"],
                            "Tasa Victoria": f"{stats.get('win_rate', 0):.1f}%",
                            "Goles a Favor": f"{stats.get('avg_goals_for', 0):.2f}",
                            "Goles en Contra": f"{stats.get('avg_goals_against', 0):.2f}",
                            "Diferencia": f"{stats.get('avg_goal_difference', 0):.2f}"
                        })
                    
                    df = pd.DataFrame(formation_data)
                    st.dataframe(df, use_container_width=True, hide_index=True)
                
                # ========== SECCIÓN 2: FASES DEL PARTIDO ==========
                st.markdown("---")
                st.markdown("""
                <h3 style='color:#FF9900; margin-top:20px;'>Fases del Partido</h3>
                """, unsafe_allow_html=True)
                
                # Recalcular con partidos filtrados (si hay filtro de formación)
                phase_stats = analyze_match_phases(played_matches, selected_opponent)
                
                # Dropdown menu for metric selection
                metric_options = {
                    "Promedio de Goles": {
                        "for_key": "avg_goals_for",
                        "against_key": "avg_goals_against",
                        "y_axis_title": "Promedio de Goles",
                        "for_label": "Goles a Favor (Promedio)",
                        "against_label": "Goles en Contra (Promedio)"
                    },
                    "Total de Goles": {
                        "for_key": "goals_for",
                        "against_key": "goals_against",
                        "y_axis_title": "Total de Goles",
                        "for_label": "Goles a Favor (Total)",
                        "against_label": "Goles en Contra (Total)"
                    },
                    "Diferencia de Goles": {
                        "for_key": "goal_difference",
                        "against_key": None,
                        "y_axis_title": "Diferencia de Goles",
                        "for_label": "Diferencia (GF - GC)",
                        "against_label": None
                    }
                }
                
                selected_metric = st.selectbox(
                    "Seleccionar Métrica:",
                    options=list(metric_options.keys()),
                    index=0,
                    key=f"phase_metric_{selected_opponent}"
                )
                
                metric_config = metric_options[selected_metric]
                
                col1, col2, col3 = st.columns(3)
                
                total_goals_for = sum([p["goals_for"] for p in phase_stats.values()])
                total_goals_against = sum([p["goals_against"] for p in phase_stats.values()])
                best_phase = max(phase_stats.items(), key=lambda x: x[1]["goals_for"] - x[1]["goals_against"])
                
                with col1:
                    st.metric("Goles a Favor (Total)", total_goals_for)
                with col2:
                    st.metric("Goles en Contra (Total)", total_goals_against)
                with col3:
                    phase_names = {"first_15": "0-15'", "16_30": "16-30'", "31_45": "31-45'", 
                                  "45_plus": "45+1'", "46_60": "46-60'", "61_75": "61-75'", 
                                  "76_90": "76-90'", "90_plus": "90+1'"}
                    st.metric("Mejor Fase", phase_names.get(best_phase[0], "N/A"))
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                # Use the team_color we already calculated from CSV (it's already correct)
                chart_color = team_color
                
                # Pass verified color directly to chart with selected metric
                fig = create_phase_chart(phase_stats, chart_color, metric_config)
                if fig:
                    st.plotly_chart(fig, use_container_width=True, key=f"phase_chart_{selected_opponent}_{chart_color}")
                
                # Tabla detallada - ensure all phases are included
                phase_data = []
                phase_names = {"first_15": "0-15'", "16_30": "16-30'", "31_45": "31-45'", 
                              "45_plus": "45+1'", "46_60": "46-60'", "61_75": "61-75'", 
                              "76_90": "76-90'", "90_plus": "90+1'"}
                
                # Ensure all phases exist in phase_stats
                for key in phase_names.keys():
                    if key not in phase_stats:
                        phase_stats[key] = {
                            "goals_for": 0,
                            "goals_against": 0,
                            "matches": 0,
                            "avg_goals_for": 0.0,
                            "avg_goals_against": 0.0
                        }
                
                for key, name in phase_names.items():
                    stats = phase_stats.get(key, {
                        "goals_for": 0,
                        "goals_against": 0,
                        "matches": 0,
                        "avg_goals_for": 0.0,
                        "avg_goals_against": 0.0
                    })
                    phase_data.append({
                        "Fase": name,
                        "Goles a Favor": stats.get("goals_for", 0),
                        "Goles en Contra": stats.get("goals_against", 0),
                        "Diferencia": stats.get("goals_for", 0) - stats.get("goals_against", 0),
                        "Promedio GF": f"{stats.get('avg_goals_for', 0.0):.2f}",
                        "Promedio GC": f"{stats.get('avg_goals_against', 0.0):.2f}"
                    })
                
                df = pd.DataFrame(phase_data)
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                # ========== SECCIÓN 4: SET PIECES ==========
                st.markdown("---")
                st.markdown("""
                <h3 style='color:#FF9900; margin-top:20px;'>Set Pieces</h3>
                """, unsafe_allow_html=True)
                
                # Recalcular con partidos filtrados (si hay filtro de formación)
                set_pieces_stats = analyze_set_pieces(played_matches, selected_opponent)
                
                if set_pieces_stats["matches"] == 0:
                    st.info("No hay datos de set pieces disponibles.")
                else:
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.markdown("""
                        <h3 style='color:#FF9900; margin-top:20px;'>Corners</h3>
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
                        <h3 style='color:#FF9900; margin-top:20px;'>Tiros Libres</h3>
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
                        <h3 style='color:#FF9900; margin-top:20px;'>Penales</h3>
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
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    categories = ["Corners\nGanados", "Corners\nRecibidos", "Faltas a\nFavor", "Faltas en\nContra"]
                    values = [
                        set_pieces_stats["corners"].get("avg_won", 0),
                        set_pieces_stats["corners"].get("avg_lost", 0),
                        set_pieces_stats["free_kicks"].get("avg_won", 0),
                        set_pieces_stats["free_kicks"].get("avg_lost", 0)
                    ]
                    
                    # Use the team_color we already calculated from CSV (it's already correct)
                    chart_color = team_color
                    
                    # Use lighter version of team color for opponent stats
                    opponent_color = lighten_color(chart_color, factor=0.7)
                    
                    # Determine text colors for each bar based on their color brightness
                    text_colors = [
                        get_text_color(chart_color),      # Corners Ganados
                        get_text_color(opponent_color),   # Corners Recibidos
                        get_text_color(chart_color),      # Faltas a Favor
                        get_text_color(opponent_color)    # Faltas en Contra
                    ]
                    
                    fig = go.Figure()
                    fig.add_trace(go.Bar(
                        x=categories,
                        y=values,
                        marker_color=[chart_color, opponent_color, chart_color, opponent_color],  # Use marker_color directly with list
                        marker_line=dict(width=0),  # Remove border
                        text=[f"{v:.2f}" for v in values],
                        textposition='inside',  # Anchor text inside the bar
                        textfont=dict(color=text_colors, size=14, family="Arial Black")
                    ))
                    
                    fig.update_layout(
                        template='plotly_dark',
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        height=400,
                        xaxis_title="Tipo de Set Piece",
                        yaxis_title="Promedio por Partido",
                        showlegend=False,
                        font=dict(color='white')
                    )
                    
                    st.plotly_chart(fig, use_container_width=True, key=f"set_pieces_chart_{selected_opponent}_{chart_color}")
        else:
            st.info("Selecciona un equipo para ver su análisis táctico.")


if __name__ == "__main__":
    main()
