# ===========================================
# 3_Exportar_Reporte_PDF.py — Exportar Reporte PDF
# ===========================================
import streamlit as st
import sys
from pathlib import Path

# Add parent directory to path so we can import from src
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import json
import csv
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import io
import requests
from bs4 import BeautifulSoup
import re

# === IMPORTS ===
from src.utils.global_dark_theme import inject_dark_theme, titulo_naranja
from src.utils.navigation import render_top_navigation

# === DATA LOADING ===
# Initialize variables first to avoid scoping issues
load_per90_data = None
load_cibao_team_data = None
DATA_LOADING_AVAILABLE = False

# Import at module level
try:
    from src.data_processing.loaders import load_per90_data
    from src.data_processing.load_cibao_team_data import load_cibao_team_data
    DATA_LOADING_AVAILABLE = True
except ImportError as e:
    # Variables already set to None above
    pass

# Inject dark theme
inject_dark_theme()

# Navigation
render_top_navigation()

# Page title
titulo_naranja(" Exportar Reporte PDF")

st.markdown("---")

# Constants
CIBAO_TEAM_NAME = "Cibao"

def main():
    """Main function for PDF export page"""
    
    # Check if data loading functions are available (use globals() to avoid scoping issues)
    load_per90_func = globals().get('load_per90_data')
    load_cibao_func = globals().get('load_cibao_team_data')
    data_available = globals().get('DATA_LOADING_AVAILABLE', False)
    
    if not data_available or load_per90_func is None or load_cibao_func is None:
        st.error(" Error: No se pudieron importar las funciones de carga de datos. Por favor, verifica que los módulos estén disponibles.")
        return
    
    # Load data
    with st.spinner("Cargando datos..."):
        try:
            df_liga = load_per90_func()
            cibao_data = load_cibao_func()
        except Exception as e:
            st.error(f"Error cargando datos: {e}")
            import traceback
            with st.expander(" Detalles del error"):
                st.code(traceback.format_exc())
            return
    
    if df_liga is None or df_liga.empty:
        st.error("No se pudieron cargar los datos de la liga.")
        return
    
    # Get unique teams (excluding Cibao)
    # Clean team names to remove duplicate suffixes like " (1)", " (2)", etc.
    def clean_team_name(name: str) -> str:
        """Remove duplicate suffixes like (1), (2) from team names."""
        import re
        cleaned = re.sub(r'\s*\(\d+\)\s*$', '', str(name).strip())
        return cleaned.strip()
    
    # Get all unique team names
    all_teams = df_liga["Team"].unique().tolist()
    all_teams = [t for t in all_teams if pd.notna(t) and str(t).strip()]
    
    # Create a mapping of cleaned names to original names
    # Prefer the version without the suffix if both exist
    team_map = {}
    for team in all_teams:
        cleaned = clean_team_name(team)
        # If we haven't seen this cleaned name, or if current team doesn't have a suffix
        if cleaned not in team_map or not re.search(r'\(\d+\)$', str(team)):
            team_map[cleaned] = team
    
    # Get unique cleaned team names, excluding Cibao
    available_teams = sorted([team for team in team_map.keys() 
                             if team.lower() != CIBAO_TEAM_NAME.lower()])
    
    if not available_teams:
        st.warning("No hay equipos disponibles para analizar.")
        return
    
    # ===========================================
    # STEP 1: SELECT TEAM
    # ===========================================
    st.markdown("### 1⃣ Seleccionar Equipo Rival")
    selected_opponent = st.selectbox(
        "Elige el equipo que deseas analizar:",
        options=available_teams,
        key="pdf_export_opponent",
        help="Selecciona el equipo rival para el cual generar el reporte"
    )
    
    if not selected_opponent:
        st.info("Por favor, selecciona un equipo para continuar.")
        return
    
    st.markdown("---")
    
    # ===========================================
    # STEP 2: SECTION-BASED SELECTION (OPTION 1)
    # ===========================================
    st.markdown("### 2⃣ Seleccionar Elementos para el Reporte")
    st.markdown("Selecciona qué secciones deseas incluir en el PDF. Puedes expandir cada sección para ver más opciones.")
    
    # Initialize selections in session state
    if 'pdf_selections' not in st.session_state:
        st.session_state.pdf_selections = {
            'recent_form': True,
            'key_metrics': True,
            'radar_charts': True,
            'radar_types': ['all', 'past_5'],
            'radar_metrics': ['Goles', 'Disparos', 'Pases Totales', 'Corners', 'Tackles Totales']
        }
    
    # ===== SECTION 1: RECENT FORM =====
    with st.expander(" **Forma Reciente (Últimos Partidos)**", expanded=True):
        include_recent_form = st.checkbox(
            "Incluir tabla de forma reciente",
            value=st.session_state.pdf_selections.get('recent_form', True),
            key="check_recent_form",
            help="Muestra los últimos partidos del equipo con resultados y estadísticas básicas"
        )
        
        if include_recent_form:
            num_matches = st.slider(
                "Número de partidos a incluir",
                min_value=3,
                max_value=10,
                value=5,
                key="num_recent_matches",
                help="Selecciona cuántos partidos recientes mostrar"
            )
            
            st.info(f" Se incluirá una tabla con los últimos {num_matches} partidos del equipo, mostrando: fecha, oponente, resultado, goles a favor/en contra, y estadísticas clave.")
        else:
            num_matches = 5
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # ===== SECTION 2: KEY METRICS =====
    with st.expander(" **Métricas Clave**", expanded=True):
        include_key_metrics = st.checkbox(
            "Incluir métricas clave",
            value=st.session_state.pdf_selections.get('key_metrics', True),
            key="check_key_metrics",
            help="Muestra un resumen de las métricas más importantes del equipo"
        )
        
        if include_key_metrics:
            st.markdown("**Métricas que se incluirán:**")
            key_metrics_list = [
                "Goles", "Goles Recibidos", "Disparos", "Disparos al Arco",
                "Pases Totales", "Pases Precisos", "Precisión de Pases %",
                "Posesión %", "Corners", "Tackles Exitosos", "Despejes"
            ]
            
            selected_key_metrics = st.multiselect(
                "Personalizar métricas clave (opcional):",
                options=key_metrics_list,
                default=key_metrics_list,
                key="select_key_metrics",
                help="Por defecto se incluyen todas las métricas principales"
            )
            
            if not selected_key_metrics:
                selected_key_metrics = key_metrics_list
            
            st.info(f" Se incluirá un resumen con {len(selected_key_metrics)} métricas clave calculadas sobre los últimos {num_matches} partidos.")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # ===== SECTION 3: RADAR CHARTS =====
    with st.expander(" **Gráficos de Radar (Comparación)**", expanded=True):
        include_radar_charts = st.checkbox(
            "Incluir gráficos de radar",
            value=st.session_state.pdf_selections.get('radar_charts', True),
            key="check_radar_charts",
            help="Gráficos de comparación visual entre el equipo rival y Cibao"
        )
        
        if include_radar_charts:
            st.markdown("**Tipos de gráficos de radar:**")
            
            radar_type_options = {
                "Todos los partidos": "all",
                "Últimos 5 partidos": "past_5",
                "Partidos en casa": "home",
                "Partidos fuera": "away"
            }
            
            selected_radar_types = st.multiselect(
                "Selecciona qué gráficos de radar incluir:",
                options=list(radar_type_options.keys()),
                default=["Todos los partidos", "Últimos 5 partidos"],
                key="select_radar_types",
                help="Puedes seleccionar uno o más tipos de comparación"
            )
            
            if not selected_radar_types:
                st.warning(" Por favor, selecciona al menos un tipo de gráfico de radar.")
            else:
                st.markdown("**Métricas para los gráficos de radar:**")
                
                all_radar_metrics = [
                    "Goles", "Goles Recibidos", "Disparos", "Disparos al Arco",
                    "Pases Totales", "Pases Precisos", "Precisión Pases %",
                    "Posesión", "Corners", "Faltas", "Tarjetas Amarillas",
                    "Tackles Totales", "Tackles Exitosos", "Intercepciones",
                    "Despejes", "Atajadas"
                ]
                
                selected_radar_metrics = st.multiselect(
                    "Selecciona las métricas a comparar:",
                    options=all_radar_metrics,
                    default=st.session_state.pdf_selections.get('radar_metrics', [
                        "Goles", "Disparos", "Pases Totales", "Corners", "Tackles Totales"
                    ]),
                    key="select_radar_metrics",
                    help="Selecciona las métricas que deseas comparar visualmente"
                )
                
                if not selected_radar_metrics:
                    st.warning(" Por favor, selecciona al menos una métrica para los gráficos de radar.")
                else:
                    st.info(f" Se generarán {len(selected_radar_types)} gráfico(s) de radar comparando {len(selected_radar_metrics)} métricas entre {selected_opponent} y Cibao.")
    
    st.markdown("---")
    
    # ===========================================
    # STEP 3: PREVIEW & GENERATE
    # ===========================================
    st.markdown("### 3⃣ Generar y Descargar Reporte")
    
    # Summary of selections
    with st.expander(" Resumen de Selecciones", expanded=False):
        st.markdown(f"**Equipo seleccionado:** {selected_opponent}")
        st.markdown(f"**Forma Reciente:** {' Incluido' if include_recent_form else ' No incluido'}")
        if include_recent_form:
            st.markdown(f"  - Partidos: {num_matches}")
        st.markdown(f"**Métricas Clave:** {' Incluido' if include_key_metrics else ' No incluido'}")
        st.markdown(f"**Gráficos de Radar:** {' Incluido' if include_radar_charts else ' No incluido'}")
        if include_radar_charts and selected_radar_types:
            st.markdown(f"  - Tipos: {', '.join(selected_radar_types)}")
            st.markdown(f"  - Métricas: {len(selected_radar_metrics) if selected_radar_metrics else 0}")
    
    # Validation
    can_generate = True
    if include_radar_charts:
        if not selected_radar_types or not selected_radar_metrics:
            can_generate = False
            st.error(" Por favor, completa la selección de gráficos de radar antes de generar el PDF.")
    
    # Generate button
    if st.button(" Generar Reporte PDF", type="primary", use_container_width=True, disabled=not can_generate):
        if not can_generate:
            return
        
        with st.spinner(" Generando reporte PDF... Esto puede tomar unos momentos."):
            try:
                # Import helper functions from analysis page
                # We need to import without executing module-level code (like render_top_navigation)
                # Use a custom approach: read the file, modify it to skip navigation, then execute
                import types
                
                analysis_page_path = project_root / "pages" / "2_Analisis_del_Rival_-_Liga.py"
                
                # Read the file
                with open(analysis_page_path, 'r', encoding='utf-8') as f:
                    code = f.read()
                
                # Replace navigation and theme calls with no-ops to avoid duplicate keys
                modified_code = code.replace('render_top_navigation()', 'pass  # Skipped during import')
                modified_code = modified_code.replace('inject_dark_theme()', 'pass  # Skipped during import')
                
                # Set up execution environment with all necessary imports
                exec_globals = {
                    '__name__': 'analysis_module',
                    '__file__': str(analysis_page_path),
                    'st': st,
                    'pd': pd,
                    'np': np,
                    'go': go,
                    'Path': Path,
                    'datetime': datetime,
                    'List': List,
                    'Dict': Dict,
                    'Optional': Optional,
                    'Tuple': Tuple,
                    'json': json,
                    'csv': csv,
                    'requests': requests,
                    'BeautifulSoup': BeautifulSoup,
                    're': re,
                }
                
                # Import plotly.io
                try:
                    import plotly.io as pio
                    exec_globals['pio'] = pio
                except:
                    pass
                
                # Import utility functions but make them no-ops to avoid duplicate UI elements
                try:
                    from src.utils.global_dark_theme import inject_dark_theme, titulo_naranja
                    from src.utils.navigation import render_top_navigation
                    # Use no-op versions to prevent duplicate UI elements
                    exec_globals['inject_dark_theme'] = lambda: None
                    exec_globals['render_top_navigation'] = lambda: None
                    exec_globals['titulo_naranja'] = lambda x: None
                except:
                    exec_globals['inject_dark_theme'] = lambda: None
                    exec_globals['render_top_navigation'] = lambda: None
                    exec_globals['titulo_naranja'] = lambda x: None
                
                # Import data loading functions
                try:
                    from src.data_processing.load_cibao_team_data import load_cibao_team_data
                    from src.data_processing.loaders import load_per90_data
                    exec_globals['load_cibao_team_data'] = load_cibao_team_data
                    exec_globals['load_per90_data'] = load_per90_data
                except:
                    pass
                
                # Import fix_wyscout_headers if available
                try:
                    from src.data_processing.fix_wyscout_headers import fix_team_headers
                    exec_globals['fix_team_headers'] = fix_team_headers
                    exec_globals['FIX_WYSCOUT_HEADERS_AVAILABLE'] = True
                except:
                    exec_globals['FIX_WYSCOUT_HEADERS_AVAILABLE'] = False
                    exec_globals['fix_team_headers'] = None
                
                # Execute the modified code
                exec(compile(modified_code, str(analysis_page_path), 'exec'), exec_globals)
                
                # Get the functions we need
                calculate_team_averages_from_df = exec_globals.get('calculate_team_averages_from_df')
                create_radar_chart = exec_globals.get('create_radar_chart')
                
                if not calculate_team_averages_from_df or not create_radar_chart:
                    raise ImportError("Could not import required functions from analysis page")
                
                # Get opponent and Cibao data
                # Handle cleaned team names (without "(1)" suffixes) matching against original data
                selected_opponent_normalized = selected_opponent.lower().strip()
                selected_opponent_cleaned = re.sub(r'\s*\(\d+\)\s*$', '', selected_opponent_normalized)
                
                # Try exact match first
                opponent_df = df_liga[df_liga["Team"].str.lower() == selected_opponent.lower()].copy()
                
                # If no exact match, try matching against cleaned names (handle "(1)" variations)
                if opponent_df.empty:
                    def team_name_match(team_name):
                        if pd.isna(team_name):
                            return False
                        team_name_str = str(team_name).lower().strip()
                        team_name_cleaned = re.sub(r'\s*\(\d+\)\s*$', '', team_name_str)
                        # Check if cleaned names match
                        return selected_opponent_cleaned == team_name_cleaned
                    
                    opponent_df = df_liga[df_liga["Team"].apply(team_name_match)].copy()
                
                cibao_df = df_liga[df_liga["Team"].str.lower() == CIBAO_TEAM_NAME.lower()].copy()
                
                if opponent_df.empty or cibao_df.empty:
                    st.error(f" No se encontraron datos para {selected_opponent} o Cibao.")
                    return
                
                # Collect data based on selections
                recent_matches = None
                key_metrics = None
                radar_charts = {}
                
                # 1. Recent Form
                if include_recent_form:
                    try:
                        if "Date" in opponent_df.columns:
                            recent_opponent = opponent_df.sort_values("Date", ascending=False).head(num_matches)
                            
                            recent_matches = []
                            for _, row in recent_opponent.iterrows():
                                match_str = str(row.get("Match", ""))
                                date_str = str(row.get("Date", ""))
                                
                                # Parse match result
                                goals_for = row.get("Goals", 0)
                                goals_against = row.get("Goals Against", 0)
                                
                                # Determine if opponent was home or away
                                if match_str and selected_opponent:
                                    parts = match_str.split(" - ")
                                    if len(parts) >= 2:
                                        home_team = parts[0].strip()
                                        is_home = selected_opponent.lower() in home_team.lower()
                                        
                                        if is_home:
                                            opponent_goals = goals_for
                                            opponent_goals_against = goals_against
                                        else:
                                            opponent_goals = goals_against
                                            opponent_goals_against = goals_for
                                    else:
                                        opponent_goals = goals_for
                                        opponent_goals_against = goals_against
                                else:
                                    opponent_goals = goals_for
                                    opponent_goals_against = goals_against
                                
                                # Get opponent name from match string
                                if match_str:
                                    parts = match_str.split(" - ")
                                    if len(parts) >= 2:
                                        home_team = parts[0].strip()
                                        away_team = parts[1].split()[0] if len(parts[1].split()) > 0 else ""
                                        
                                        if selected_opponent.lower() in home_team.lower():
                                            opponent_name = away_team
                                        else:
                                            opponent_name = home_team
                                    else:
                                        opponent_name = "Unknown"
                                else:
                                    opponent_name = "Unknown"
                                
                                recent_matches.append({
                                    "date": date_str,
                                    "opponent": opponent_name,
                                    "match": match_str,
                                    "goals_for": opponent_goals,
                                    "goals_against": opponent_goals_against,
                                    "result": "W" if opponent_goals > opponent_goals_against else ("L" if opponent_goals < opponent_goals_against else "D")
                                })
                    except Exception as e:
                        st.warning(f" Error generando forma reciente: {e}")
                
                # 2. Key Metrics
                if include_key_metrics:
                    try:
                        if "Date" in opponent_df.columns:
                            past_n_opponent = opponent_df.sort_values("Date", ascending=False).head(num_matches)
                            
                            key_metrics = {}
                            metric_mapping = {
                                "Goles": "Goals",
                                "Goles Recibidos": "Goals Against",
                                "Disparos": "Shots",
                                "Disparos al Arco": "Shots On Target",
                                "Pases Totales": "Passes",
                                "Pases Precisos": "Passes Accurate",
                                "Precisión de Pases %": "Pass Accuracy",
                                "Posesión %": "Possession %",
                                "Corners": "Corners",
                                "Tackles Exitosos": "Tackles Won",
                                "Despejes": "Clearances"
                            }
                            
                            for metric_name in selected_key_metrics:
                                col_name = metric_mapping.get(metric_name, metric_name)
                                if col_name in past_n_opponent.columns:
                                    if "%" in metric_name:
                                        key_metrics[metric_name] = past_n_opponent[col_name].mean()
                                    else:
                                        key_metrics[metric_name] = past_n_opponent[col_name].mean()
                    except Exception as e:
                        st.warning(f" Error generando métricas clave: {e}")
                
                # 3. Radar Charts
                if include_radar_charts and selected_radar_types and selected_radar_metrics:
                    try:
                        team_averages = calculate_team_averages_from_df(opponent_df, selected_opponent, already_filtered=True)
                        cibao_averages = calculate_team_averages_from_df(cibao_df, CIBAO_TEAM_NAME, already_filtered=True)
                        
                        radar_type_map = {
                            "Todos los partidos": "all",
                            "Últimos 5 partidos": "past_5",
                            "Partidos en casa": "home",
                            "Partidos fuera": "away"
                        }
                        
                        # Generate each selected radar chart
                        for radar_type_name in selected_radar_types:
                            radar_type_key = radar_type_map.get(radar_type_name)
                            
                            if radar_type_key == "all":
                                if team_averages and cibao_averages:
                                    radar_fig = create_radar_chart(team_averages, cibao_averages, selected_opponent, selected_radar_metrics)
                                    try:
                                        from plotly.io import to_image
                                        radar_bytes = to_image(radar_fig, format='png', width=800, height=600, engine='kaleido')
                                        if radar_bytes and len(radar_bytes) > 0:
                                            radar_charts['all'] = radar_bytes
                                    except:
                                        radar_charts['all'] = radar_fig
                            
                            elif radar_type_key == "past_5":
                                if "Date" in opponent_df.columns:
                                    past_5_opponent = opponent_df.sort_values("Date", ascending=False).head(5)
                                    past_5_cibao = cibao_df.sort_values("Date", ascending=False).head(5)
                                    
                                    past_5_team_avg = calculate_team_averages_from_df(past_5_opponent, selected_opponent, already_filtered=True)
                                    past_5_cibao_avg = calculate_team_averages_from_df(past_5_cibao, CIBAO_TEAM_NAME, already_filtered=True)
                                    
                                    if past_5_team_avg and past_5_cibao_avg:
                                        radar_fig = create_radar_chart(past_5_team_avg, past_5_cibao_avg, selected_opponent, selected_radar_metrics)
                                        try:
                                            from plotly.io import to_image
                                            radar_bytes = to_image(radar_fig, format='png', width=800, height=600, engine='kaleido')
                                            if radar_bytes and len(radar_bytes) > 0:
                                                radar_charts['past_5'] = radar_bytes
                                        except:
                                            radar_charts['past_5'] = radar_fig
                            
                            elif radar_type_key in ["home", "away"]:
                                # Home/Away logic
                                def is_home(row):
                                    match_str = str(row.get("Match", ""))
                                    team_name = str(row.get("Team", "")).strip()
                                    if match_str and team_name:
                                        parts = match_str.split(" - ")
                                        if len(parts) >= 2:
                                            home_team = parts[0].strip()
                                            return team_name.lower() in home_team.lower() or home_team.lower() in team_name.lower()
                                    return False
                                
                                def is_away(row):
                                    return not is_home(row)
                                
                                if radar_type_key == "home":
                                    home_opponent = opponent_df[opponent_df.apply(is_home, axis=1)]
                                    home_cibao = cibao_df[cibao_df.apply(is_home, axis=1)]
                                    
                                    if not home_opponent.empty and not home_cibao.empty:
                                        home_team_avg = calculate_team_averages_from_df(home_opponent, selected_opponent, already_filtered=True)
                                        home_cibao_avg = calculate_team_averages_from_df(home_cibao, CIBAO_TEAM_NAME, already_filtered=True)
                                        
                                        if home_team_avg and home_cibao_avg:
                                            radar_fig = create_radar_chart(home_team_avg, home_cibao_avg, selected_opponent, selected_radar_metrics)
                                            try:
                                                from plotly.io import to_image
                                                radar_bytes = to_image(radar_fig, format='png', width=800, height=600, engine='kaleido')
                                                if radar_bytes and len(radar_bytes) > 0:
                                                    radar_charts['home'] = radar_bytes
                                            except:
                                                radar_charts['home'] = radar_fig
                                
                                else:  # away
                                    away_opponent = opponent_df[opponent_df.apply(is_away, axis=1)]
                                    away_cibao = cibao_df[cibao_df.apply(is_away, axis=1)]
                                    
                                    if not away_opponent.empty and not away_cibao.empty:
                                        away_team_avg = calculate_team_averages_from_df(away_opponent, selected_opponent, already_filtered=True)
                                        away_cibao_avg = calculate_team_averages_from_df(away_cibao, CIBAO_TEAM_NAME, already_filtered=True)
                                        
                                        if away_team_avg and away_cibao_avg:
                                            radar_fig = create_radar_chart(away_team_avg, away_cibao_avg, selected_opponent, selected_radar_metrics)
                                            try:
                                                from plotly.io import to_image
                                                radar_bytes = to_image(radar_fig, format='png', width=800, height=600, engine='kaleido')
                                                if radar_bytes and len(radar_bytes) > 0:
                                                    radar_charts['away'] = radar_bytes
                                            except:
                                                radar_charts['away'] = radar_fig
                    
                    except Exception as e:
                        st.warning(f" Error generando gráficos de radar: {e}")
                        import traceback
                        st.code(traceback.format_exc())
                
                # Generate PDF (placeholder for now - will implement PDF generation next)
                st.success(" Datos preparados correctamente!")
                st.info(" La generación del PDF estará disponible próximamente. Por ahora, los datos están listos.")
                
                # Show what was collected
                with st.expander(" Ver datos recopilados", expanded=False):
                    st.write(f"**Forma Reciente:** {len(recent_matches) if recent_matches else 0} partidos")
                    st.write(f"**Métricas Clave:** {len(key_metrics) if key_metrics else 0} métricas")
                    st.write(f"**Gráficos de Radar:** {len(radar_charts)} gráficos")
                    
                    if recent_matches:
                        st.write("**Ejemplo de partido reciente:**")
                        st.json(recent_matches[0] if recent_matches else {})
                    
                    if key_metrics:
                        st.write("**Métricas clave:**")
                        st.json(key_metrics)
                    
                    if radar_charts:
                        st.write("**Gráficos generados:**")
                        for key, val in radar_charts.items():
                            st.write(f"- {key}: {type(val).__name__}")
                
            except Exception as e:
                st.error(f" Error generando reporte: {str(e)}")
                import traceback
                with st.expander(" Detalles del error"):
                    st.code(traceback.format_exc())


if __name__ == "__main__":
    main()
