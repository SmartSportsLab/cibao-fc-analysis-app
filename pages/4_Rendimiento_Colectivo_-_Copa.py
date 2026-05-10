import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from src.data_processing.load_concacaf_matchstats_data import load_concacaf_matchstats_data
from src.utils.metrics_dictionary_concacaf import METRICS_CONCACAF, METRIC_GROUPS_CONCACAF
from src.utils.global_dark_theme import inject_dark_theme, titulo_naranja
from src.utils.navigation import render_top_navigation
from graficos_de_navaja_suiza import make_team_scatter

CIBAO_ORANGE = "#FF8C00"  # Naranja vibrante principal
CIBAO_ORANGE_LIGHT = "#FFC966"  # Naranja dorado/ámbar claro para rivales (mayor contraste)
CIBAO_GRAY = "#D3D3D3"
WHITE_RIVAL = "#FFFFFF"

st.set_page_config(
    page_title="Rendimiento Colectivo - Copa",
    layout="wide",
    initial_sidebar_state="expanded"
)
inject_dark_theme()

# ---------- TOP NAVIGATION BAR ----------
render_top_navigation()

# ===========================================
# CUSTOM FONT SIZES
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

# =========================================================
#  ENCABEZADO PRINCIPAL
# =========================================================
titulo_naranja("Rendimiento Colectivo — Cibao FC (Copa)")
st.markdown(
    f"""
    <p style='text-align:center; color:{CIBAO_GRAY}; font-size:17px;'>
    Lectura de <b>modelo de juego</b>, <b>eficiencia por fases</b> y <b>tendencias competitivas</b>.
    Diseñado para soporte táctico del staff técnico — decisiones claras, con contexto.
    </p>
    """,
    unsafe_allow_html=True,
)

# =========================================================
#  CARGA DE DATOS COPA
# =========================================================
try:
    df_copa_merged, df_copa_cibao, df_copa_rivales = load_concacaf_matchstats_data()
except Exception as e:
    st.error(f" Error al cargar los datos de Copa Concacaf: {e}")
    st.stop()

if df_copa_cibao.empty:
    st.warning("No hay registros de partidos de Copa Concacaf disponibles.")
    st.stop()

df_copa_cibao["Match_Date"] = pd.to_datetime(df_copa_cibao["match_date"], errors="coerce")
df_copa_cibao = df_copa_cibao.sort_values("Match_Date")

ultima_fecha = df_copa_cibao["Match_Date"].dropna().max()
df_ultima_jornada = (
    df_copa_cibao[df_copa_cibao["Match_Date"] == ultima_fecha].copy()
    if pd.notna(ultima_fecha)
    else df_copa_cibao.head(0)
)

if df_ultima_jornada.empty:
    st.warning("No se pudo determinar la última jornada de Copa.")
    st.stop()

df_ultima_cibao = df_ultima_jornada[df_ultima_jornada["team"].str.contains("Cibao", case=False, na=False)].copy()
if df_ultima_cibao.empty:
    st.warning("No hay registros del Cibao FC en la última fecha.")
    st.stop()

fecha_str = ultima_fecha.strftime("%d-%m-%Y")
fila_principal = df_ultima_cibao.iloc[0]

st.markdown("### Indicadores del último partido (Copa)")
kpi_texts = [
    ("Fecha", fecha_str),
    ("Fase", fila_principal.get("stage", "-")),
    ("Equipo Local", fila_principal.get("home_team", "-")),
    ("Equipo Visitante", fila_principal.get("away_team", "-")),
]
cols_text = st.columns(len(kpi_texts))
for (label, value), col in zip(kpi_texts, cols_text):
    display = str(value) if pd.notna(value) else "-"
    with col:
        st.markdown(
            f"""
            <div style='background:rgba(25,25,25,0.95);
                        border:1px solid rgba(255,140,0,0.35);
                        border-radius:14px;padding:18px;
                        text-align:center;box-shadow:0 0 18px rgba(255,140,0,0.12);'>
                <div style='font-size:1.3rem;color:{CIBAO_ORANGE};font-weight:700;'>{display}</div>
                <div style='color:#cfcfcf;font-size:0.9rem;'>{label}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.markdown("<br>", unsafe_allow_html=True)

tarjetas = df_ultima_cibao[["yellowCard", "redCard"]].apply(pd.to_numeric, errors="coerce").fillna(0).sum()
kpi_cards = [
    ("Tarjetas Amarillas", int(tarjetas["yellowCard"])),
    ("Tarjetas Rojas", int(tarjetas["redCard"])),
]
cols_cards = st.columns(len(kpi_cards))
for (label, value), col in zip(kpi_cards, cols_cards):
    with col:
        st.markdown(
            f"""
            <div style='background: linear-gradient(135deg, #1E293B 0%, rgba(30, 41, 59, 0.8) 100%); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; padding: 1.5rem; text-align: center; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3); transition: transform 0.2s;'>
                <div style='color: #94A3B8; font-size: 1.2rem; margin-bottom: 0.5rem; font-weight: 500;'>{label}</div>
                <div style='color: #FFFFFF; font-size: 2rem; font-weight: bold;'>{value}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.markdown("<br>", unsafe_allow_html=True)
# =========================================================
#  COMPARATIVA CIBAO VS RIVAL (Copa)
# =========================================================
st.markdown(
    f"""
    <h2 style='text-align:center; color:{CIBAO_ORANGE}; font-weight:900;'>
        Comparativa Copa (Cibao vs Rival)
    </h2>
    <p style='text-align:center; color:{CIBAO_GRAY}; font-size:16px;'>
        Evalúa el rendimiento del Cibao FC frente a sus rivales en Copa Concacaf,
        considerando métricas ofensivas y defensivas clave.
    </p>
    """,
    unsafe_allow_html=True,
)

col_sel1, col_sel2, col_sel3 = st.columns([1.2, 1.2, 1])

team_options_copa = sorted(
    {
        str(t)
        for t in df_copa_cibao["rival"].dropna().unique()
        if str(t).strip().lower() != "cibao"
    }
)

opponent_copa = None
if not team_options_copa:
    st.info("No hay rivales disponibles en el dataset de Copa Concacaf.")
else:
    opponent_copa = col_sel1.selectbox("Selecciona rival de Copa", team_options_copa, index=0)

    metric_labels_copa = list(METRICS_CONCACAF.keys())
    x_default_copa = metric_labels_copa.index("Goles") if "Goles" in metric_labels_copa else 0
    y_default_copa = (
        metric_labels_copa.index("Goles Recibidos")
        if "Goles Recibidos" in metric_labels_copa
        else min(1, len(metric_labels_copa) - 1)
    )

    x_choice_copa = col_sel2.selectbox(
        "Métrica ofensiva (eje X)",
        metric_labels_copa,
        index=x_default_copa if metric_labels_copa else 0,
    )
    y_choice_copa = col_sel3.selectbox(
        "Métrica defensiva (eje Y)",
        metric_labels_copa,
        index=y_default_copa if metric_labels_copa else 0,
    )

    x_column_copa = METRICS_CONCACAF.get(x_choice_copa)
    y_column_copa = METRICS_CONCACAF.get(y_choice_copa)

    if x_column_copa is None or y_column_copa is None:
        st.error("No se encontró la métrica seleccionada en el dataset de Copa.")
    else:
        df_copa_adapter = df_copa_cibao.copy()
        df_copa_adapter["Team"] = df_copa_adapter["team"]
        df_copa_adapter["Opponent"] = df_copa_adapter.apply(
            lambda r: r["away_team"] if r["team"] == r["home_team"] else r["home_team"],
            axis=1,
        )
        df_copa_adapter["Competition"] = "Copa Concacaf"
        df_copa_adapter["Date"] = pd.to_datetime(df_copa_adapter["match_date"], errors="coerce")
        df_copa_adapter["Match"] = df_copa_adapter.apply(
            lambda r: f"{r['home_team']} vs {r['away_team']}",
            axis=1,
        )
        if "Jornada" not in df_copa_adapter.columns:
            df_copa_adapter["Jornada"] = df_copa_adapter.get("stage", "Copa")

        for col_num in [x_column_copa, y_column_copa]:
            if col_num in df_copa_adapter.columns:
                df_copa_adapter[col_num] = (
                    pd.to_numeric(df_copa_adapter[col_num], errors="coerce").fillna(0)
                )

        df_copa_view = df_copa_adapter.fillna(0)

        if df_copa_view.empty:
            st.info("No hay registros disponibles para el análisis de Copa.")
        else:
            try:
                fig_copa, resumen_copa, _ = make_team_scatter(
                    df_copa_view,
                    primary_team="Cibao",
                    opponent=opponent_copa,
                    x_metric=x_column_copa,
                    y_metric=y_column_copa,
                    x_label=x_choice_copa,
                    y_label=y_choice_copa,
                    title=f"Copa Concacaf — {x_choice_copa} vs {y_choice_copa}",
                    filters=None,
                )

                fig_copa.layout.annotations = [
                    ann for ann in fig_copa.layout.annotations if ann.yref != "paper" or ann.y < 1
                ]
                fig_copa.update_layout(
                    height=700,  # Increased height for better label visibility
                    margin=dict(t=120, b=100, l=80, r=120),  # Increased margins, especially right for "Promedio encajados" label
                    title_pad=dict(t=60),
                    title_font=dict(size=20),
                )

                st.plotly_chart(
                    fig_copa,
                    use_container_width=True,
                    config={"displayModeBar": True},
                )

                if resumen_copa:
                    st.markdown("---")
                    st.caption(f"**Resumen:** {resumen_copa}")

            except Exception as e:
                st.warning(f"No se pudo usar make_team_scatter ({e}). Se muestra un scatter básico.")
                fig_basic = px.scatter(
                    df_copa_view,
                    x=x_column_copa,
                    y=y_column_copa,
                    color="Team",
                    hover_data=["Match", "Date"],
                    title=f"Copa Concacaf — {x_choice_copa} vs {y_choice_copa}",
                    template="plotly_dark",
                )
                fig_basic.update_layout(
                    height=700,  # Increased height for better label visibility
                    margin=dict(t=120, b=100, l=80, r=120),  # Increased margins, especially right for labels
                    title_pad=dict(t=60),
                    title_font=dict(size=20),
                )
                st.plotly_chart(fig_basic, use_container_width=True)


def _ensure_numeric(df, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    return df


def _map_metrics(names):
    cols = []
    for n in names:
        col = METRICS_CONCACAF.get(n)
        if col:
            cols.append(col)
    return cols


# ===========================
# HELPERS DE COMPARACIÓN (Copa)
# ===========================

def normalize_team(name: str) -> str:
    name = str(name or "").strip()
    if name.lower().startswith("cibao"):
        return "Cibao"
    return name


def find_column_in_df(df: pd.DataFrame, col_name: str):
    """Find column in df with case-insensitive and normalized matching."""
    if col_name in df.columns:
        return col_name
    col_lower = str(col_name).lower()
    for df_col in df.columns:
        if str(df_col).lower() == col_lower:
            return df_col
    col_normalized = str(col_name).replace(" ", "_").replace("%", "percent").lower()
    for df_col in df.columns:
        df_col_normalized = str(df_col).replace(" ", "_").replace("%", "percent").lower()
        if df_col_normalized == col_normalized:
            return df_col
    return None


def get_team_colors(teams):
    return {
        team: CIBAO_ORANGE if normalize_team(team) == "Cibao" else WHITE_RIVAL
        for team in teams
    }


def build_comparison_df_copa(mapping: dict, opponent: str | None):
    """Devuelve df con columnas ['Team','metric','valor','label'] comparando Cibao vs rival elegido."""
    if df_copa_cibao.empty:
        return pd.DataFrame()

    df = df_copa_cibao.copy()
    df["Team"] = df["team"].apply(normalize_team)

    teams_to_include = ["Cibao"]
    if opponent:
        teams_to_include.append(normalize_team(opponent))

    df = df[df["Team"].isin(teams_to_include)]
    if df.empty:
        return pd.DataFrame()

    columnas = []
    etiquetas = {}
    for label, col in mapping.items():
        found_col = find_column_in_df(df, col)
        if found_col:
            columnas.append(found_col)
            etiquetas[found_col] = label

    if not columnas:
        return pd.DataFrame()

    for col in columnas:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df_means = df.groupby("Team")[columnas].mean().reset_index()
    df_means["Team"] = df_means["Team"].apply(normalize_team)

    df_melted = df_means.melt(
        id_vars=["Team"],
        value_vars=columnas,
        var_name="metric",
        value_name="valor",
    )
    df_melted["label"] = df_melted["metric"].map(etiquetas)
    df_melted["valor"] = pd.to_numeric(df_melted["valor"], errors="coerce").fillna(0)
    return df_melted
# =========================================================
#  PESTAÑAS DE ANÁLISIS ESPECÍFICO — COPA
# =========================================================
tab_ofensivo, tab_pases, tab_defensivo, tab_set_pieces, tab_general = st.tabs(
    [
        "Eficiencia y Ataque",
        "Construcción y Pases",
        "Defensa y Eficiencia",
        "Acciones a balón parado",
        "Análisis Comparativo (Tablas)",
    ]
)

def _dedup_pairs(metric_mapping):
    seen = set()
    pairs = []
    for label, col in metric_mapping.items():
        real_col = METRICS_CONCACAF.get(label, col)
        if real_col and real_col not in seen and real_col in df_copa_cibao.columns:
            seen.add(real_col)
            pairs.append((label, real_col))
    return pairs

def plot_horizontal_group(group_title, mapping_pairs):
    if not mapping_pairs:
        st.warning(f"No hay datos para {group_title}.")
        return

    mapping = {label: col for label, col in mapping_pairs}
    df_comp = build_comparison_df_copa(mapping, opponent_copa)

    if df_comp is None or df_comp.empty:
        st.warning(f"No hay datos disponibles para {group_title}.")
        return

    df_comp = df_comp.sort_values("valor", ascending=True)

    fig = px.bar(
        df_comp,
        x="valor",
        y="label",
        color="Team",
        text_auto=".2f",
        orientation="h",
        color_discrete_map=get_team_colors(df_comp["Team"].unique()),
        barmode="group",
        height=350,
    )

    fig.update_layout(
        template="plotly_dark",
        plot_bgcolor="#0B0B0B",
        paper_bgcolor="#0B0B0B",
        margin=dict(l=20, r=20, t=40, b=20),
        title=dict(text=f"<b>{group_title}</b>", font=dict(size=18, color=CIBAO_ORANGE)),
        title_x=0.5,
        font=dict(color=CIBAO_GRAY, size=12),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor="rgba(0,0,0,0.5)",
            font=dict(size=10)
        ),
    )

    st.plotly_chart(fig, use_container_width=True)

    df_cibao_only = df_comp[df_comp["Team"].str.lower() == "cibao"]
    if not df_cibao_only.empty:
        max_row = df_cibao_only.loc[df_cibao_only["valor"].idxmax()]
        min_row = df_cibao_only.loc[df_cibao_only["valor"].idxmin()]
        st.markdown(
            f"""
            <div style='background:#111; padding:12px; border-left:3px solid {CIBAO_ORANGE};
                        margin-top:-8px; margin-bottom:24px; border-radius:6px;'>
                <b>Conclusiones tácticas</b><br><br>
                • <b>Punto fuerte:</b> mayor incidencia en <b>{max_row['label']}</b> ({max_row['valor']:.2f}).<br>
                • <b>Área a potenciar:</b> menor impacto en <b>{min_row['label']}</b> ({min_row['valor']:.2f}).<br>
            </div>
            """,
            unsafe_allow_html=True,
        )

with tab_ofensivo:
    st.markdown(
        """
        <h3 style='text-align:center; color:#ff8c00;'>Eficiencia y Ataque</h3>
        <p style='text-align:center; color:#bbb; font-size:14px;'>
            Producción ofensiva, volumen de tiro y ventajas obtenidas en acciones ofensivas.
        </p>
        """,
        unsafe_allow_html=True,
    )

    grupo1 = {
        "Goles": "goals",
        "Intentos de Gol": "totalScoringAtt",
        "Asistencias de Gol": "goalAssist",
    }
    grupo2 = {
        "Disparos Totales": "totalScoringAtt",
        "Disparos al Arco": "ontargetScoringAtt",
        "Disparos Fuera del Arco": "shotOffTarget",
        "Disparos Bloqueados": "blockedScoringAtt",
    }
    grupo3 = {
        "Faltas a Favor": "wasFouled",
        "Fuera de Juego": "totalOffside",
    }

    col1, col2 = st.columns(2)
    with col1:
        plot_horizontal_group("Productividad ofensiva directa", _dedup_pairs(grupo1))
    with col2:
        plot_horizontal_group("Distribución de disparos", _dedup_pairs(grupo2))

    plot_horizontal_group("Ventajas generadas", _dedup_pairs(grupo3))
    
with tab_pases:
    st.markdown(
        """
        <h3 style='text-align:center; color:#ff8c00;'>Construcción y Pases</h3>
        <p style='text-align:center; color:#bbb; font-size:14px;'>
            Volumen total, precisión y proxy de posesión en Copa Concacaf.
        </p>
        """,
        unsafe_allow_html=True,
    )

    pases_grupo = {
        "Total de Pases": "totalPass",
        "Pases Precisos": "accuratePass",
        "Posesión (aprox.)": "totalPass",
    }

    pares = _dedup_pairs(pases_grupo)

    if pares:
        mapping = {label: col for label, col in pares}
        df_comp = build_comparison_df_copa(mapping, opponent_copa)

        if df_comp is None or df_comp.empty:
            st.warning("No hay datos disponibles para Construcción y Pases.")
        else:
            df_comp = df_comp.sort_values("valor", ascending=False)

            fig = px.bar(
                df_comp,
                x="label",
                y="valor",
                color="Team",
                text_auto=".2f",
                color_discrete_map=get_team_colors(df_comp["Team"].unique()),
                barmode="group",
                height=420,
            )

            fig.update_layout(
                template="plotly_dark",
                plot_bgcolor="#0B0B0B",
                paper_bgcolor="#0B0B0B",
                margin=dict(l=40, r=40, t=60, b=40),
                title=dict(text="<b>Volumen y precisión en la circulación</b>", font=dict(size=18, color=CIBAO_ORANGE)),
                title_x=0.5,
                font=dict(color=CIBAO_GRAY, size=12),
                xaxis=dict(tickangle=-15),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1,
                    bgcolor="rgba(0,0,0,0.5)",
                    font=dict(size=10)
                ),
            )

            st.plotly_chart(fig, use_container_width=True)

            df_cibao_only = df_comp[df_comp["Team"].str.lower() == "cibao"]
            if not df_cibao_only.empty:
                max_row = df_cibao_only.loc[df_cibao_only["valor"].idxmax()]
                min_row = df_cibao_only.loc[df_cibao_only["valor"].idxmin()]

                st.markdown(
                    f"""
                    <div style='background:#111; padding:12px; border-left:3px solid {CIBAO_ORANGE};
                                margin-top:-8px; border-radius:6px;'>
                        <b>Conclusiones tácticas</b><br><br>
                        • <b>Punto fuerte:</b> mayor aporte en <b>{max_row['label']}</b> ({max_row['valor']:.2f}).<br>
                        • <b>Área por optimizar:</b> menor incidencia en <b>{min_row['label']}</b> ({min_row['valor']:.2f}).<br>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
    else:
        st.warning("No hay datos disponibles para Construcción y Pases.")

with tab_defensivo:
    st.markdown(
        """
        <h3 style='text-align:center; color:#ff8c00;'>Defensa y Eficiencia</h3>
        <p style='text-align:center; color:#bbb; font-size:14px;'>
            Volumen de acciones defensivas, contenciones bajo palos y castigo recibido en Copa Concacaf.
        </p>
        """,
        unsafe_allow_html=True,
    )

    grupo_def1 = {
        "Entradas Totales": "totalTackle",
        "Entradas Ganadas": "wonTackle",
        "Despejes": "totalClearance",
        "Faltas Cometidas": "fouls",
    }

    grupo_def2 = {
        "Atajadas": "saves",
        "Valla Invicta": "cleanSheet",
        "Goles Recibidos": "goalsConceded",
    }

    def plot_def_block(title, mapping):
        pares = _dedup_pairs(mapping)
        if not pares:
            st.warning(f"No hay datos para {title}.")
            return

        mapping_dict = {label: col for label, col in pares}
        df_comp = build_comparison_df_copa(mapping_dict, opponent_copa)

        if df_comp is None or df_comp.empty:
            st.warning(f"No hay datos disponibles para {title}.")
            return

        df_comp = df_comp.sort_values("valor", ascending=True)

        fig = px.bar(
            df_comp,
            x="valor",
            y="label",
            color="Team",
            text_auto=".2f",
            orientation="h",
            color_discrete_map=get_team_colors(df_comp["Team"].unique()),
            barmode="group",
            height=360,
        )

        fig.update_layout(
            template="plotly_dark",
            plot_bgcolor="#0B0B0B",
            paper_bgcolor="#0B0B0B",
            margin=dict(l=20, r=20, t=40, b=20),
            title=dict(text=f"<b>{title}</b>", font=dict(size=18, color=CIBAO_ORANGE)),
            title_x=0.5,
            font=dict(color=CIBAO_GRAY, size=12),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                bgcolor="rgba(0,0,0,0.5)",
                font=dict(size=10)
            ),
        )

        st.plotly_chart(fig, use_container_width=True)

        df_cibao_only = df_comp[df_comp["Team"].str.lower() == "cibao"]
        if not df_cibao_only.empty:
            max_row = df_cibao_only.loc[df_cibao_only["valor"].idxmax()]
            min_row = df_cibao_only.loc[df_cibao_only["valor"].idxmin()]
            st.markdown(
                f"""
                <div style='background:#111; padding:12px; border-left:3px solid {CIBAO_ORANGE};
                            margin-top:-8px; margin-bottom:24px; border-radius:6px;'>
                    <b>Conclusiones tácticas</b><br><br>
                    • <b>Punto fuerte:</b> mayor impacto en <b>{max_row['label']}</b> ({max_row['valor']:.2f}).<br>
                    • <b>Área a vigilar:</b> menor incidencia en <b>{min_row['label']}</b> ({min_row['valor']:.2f}).<br>
                </div>
                """,
                unsafe_allow_html=True,
            )

    col_def1, col_def2 = st.columns(2)
    with col_def1:
        plot_def_block("Acciones defensivas y disputas", grupo_def1)
    with col_def2:
        plot_def_block("Contención bajo palos", grupo_def2)

with tab_set_pieces:
    st.markdown(
        """
        <h3 style='text-align:center; color:#ff8c00;'>Acciones a balón parado</h3>
        <p style='text-align:center; color:#bbb; font-size:14px;'>
            Lectura de reinicios y saques que activan el juego en Copa Concacaf.
        </p>
        """,
        unsafe_allow_html=True,
    )

    grupo_sp1 = {
        "Saques de Meta": "goalKicks",
        "Saques de Banda": "totalThrows",
    }

    grupo_sp2 = {
        "Saques de Esquina Ganados": "wonCorners",
        "Saques de Esquina Perdidos": "lostCorners",
        "Saques de Esquina Ejecutados": "cornerTaken",
    }

    def plot_setpiece_group(title, mapping):
        pares = _dedup_pairs(mapping)
        if not pares:
            st.warning(f"No hay datos para {title}.")
            return

        mapping_dict = {label: col for label, col in pares}
        df_comp = build_comparison_df_copa(mapping_dict, opponent_copa)

        if df_comp is None or df_comp.empty:
            st.warning(f"No hay datos disponibles para {title}.")
            return

        df_comp = df_comp.sort_values("valor", ascending=True)

        fig = px.bar(
            df_comp,
            x="valor",
            y="label",
            color="Team",
            text_auto=".2f",
            orientation="h",
            color_discrete_map=get_team_colors(df_comp["Team"].unique()),
            barmode="group",
            height=360,
        )

        fig.update_layout(
            template="plotly_dark",
            plot_bgcolor="#0B0B0B",
            paper_bgcolor="#0B0B0B",
            margin=dict(l=20, r=20, t=40, b=20),
            title=dict(text=f"<b>{title}</b>", font=dict(size=18, color=CIBAO_ORANGE)),
            title_x=0.5,
            font=dict(color=CIBAO_GRAY, size=12),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                bgcolor="rgba(0,0,0,0.5)",
                font=dict(size=10)
            ),
        )

        st.plotly_chart(fig, use_container_width=True)

        df_cibao_only = df_comp[df_comp["Team"].str.lower() == "cibao"]
        if not df_cibao_only.empty:
            max_row = df_cibao_only.loc[df_cibao_only["valor"].idxmax()]
            min_row = df_cibao_only.loc[df_cibao_only["valor"].idxmin()]
            st.markdown(
                f"""
                <div style='background:#111; padding:12px; border-left:3px solid {CIBAO_ORANGE};
                            margin-top:-8px; margin-bottom:24px; border-radius:6px;'>
                    <b>Conclusiones tácticas</b><br><br>
                    • <b>Punto fuerte:</b> mayor producción en <b>{max_row['label']}</b> ({max_row['valor']:.2f}).<br>
                    • <b>Área a seguir:</b> menor incidencia en <b>{min_row['label']}</b> ({min_row['valor']:.2f}).<br>
                </div>
                """,
                unsafe_allow_html=True,
            )

    col_sp1, col_sp2 = st.columns(2)
    with col_sp1:
        plot_setpiece_group("Reinicios básicos", grupo_sp1)
    with col_sp2:
        plot_setpiece_group("Saques de esquina", grupo_sp2)

with tab_general:
    st.markdown(
        """
        <h3 style='text-align:center; color:#ff8c00;'>Análisis Comparativo (Tablas)</h3>
        <p style='text-align:center; color:#bbb; font-size:14px;'>
            Comparación detallada de métricas clave entre Cibao FC y el promedio de sus rivales en Copa Concacaf.
        </p>
        """,
        unsafe_allow_html=True,
    )
    
    # Preparar datos comparativos
    metricas_comparativas = {
        " Ofensivas": {
            "Goles": "goals",
            "Intentos de Gol": "totalScoringAtt",
            "Disparos al Arco": "ontargetScoringAtt",
            "Asistencias": "goalAssist",
        },
        " Pases": {
            "Total de Pases": "totalPass",
            "Pases Precisos": "accuratePass",
        },
        " Defensivas": {
            "Entradas Totales": "totalTackle",
            "Entradas Ganadas": "wonTackle",
            "Despejes": "totalClearance",
            "Atajadas": "saves",
            "Goles Recibidos": "goalsConceded",
        },
        " Balón Parado": {
            "Saques de Esquina Ganados": "wonCorners",
            "Saques de Esquina Ejecutados": "cornerTaken",
            "Saques de Meta": "goalKicks",
        }
    }
    
    for categoria, metricas in metricas_comparativas.items():
        st.markdown(f"### {categoria}")
        
        # Filtrar métricas disponibles
        metricas_disponibles = {k: v for k, v in metricas.items() if v in df_copa_cibao.columns}
        
        if not metricas_disponibles:
            st.warning(f"No hay datos disponibles para {categoria}")
            continue

        df_comp = build_comparison_df_copa(metricas_disponibles, opponent_copa)
        if df_comp is None or df_comp.empty:
            st.warning(f"No hay datos disponibles para {categoria}")
            continue

        rival_name = normalize_team(opponent_copa) if opponent_copa else "Rival"

        pivot = df_comp.pivot(index="label", columns="Team", values="valor")
        if "Cibao" not in pivot.columns:
            pivot["Cibao"] = 0
        if rival_name not in pivot.columns:
            # If selected rival missing, try any other column as fallback
            other_cols = [c for c in pivot.columns if c != "Cibao"]
            if other_cols:
                pivot[rival_name] = pivot[other_cols[0]]
            else:
                pivot[rival_name] = 0

        tabla_data = []
        for label in pivot.index:
            cibao_val = pivot.loc[label, "Cibao"]
            rival_val = pivot.loc[label, rival_name]
            diferencia = cibao_val - rival_val
            porcentaje = ((cibao_val / rival_val - 1) * 100) if rival_val != 0 else 0

            if diferencia > 0:
                indicador = ""
            elif diferencia < 0:
                indicador = ""
            else:
                indicador = ""
            
            tabla_data.append({
                "Métrica": label,
                "Cibao FC": f"{cibao_val:.2f}",
                rival_name: f"{rival_val:.2f}",
                "Diferencia": f"{diferencia:+.2f}",
                "% Diferencia": f"{porcentaje:+.1f}%",
                "": indicador
            })

        df_tabla = pd.DataFrame(tabla_data)
        
        # Mostrar tabla con estilo
        st.dataframe(
            df_tabla,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Métrica": st.column_config.TextColumn("Métrica", width="medium"),
                "Cibao FC": st.column_config.TextColumn("Cibao FC", width="small"),
                rival_name: st.column_config.TextColumn(rival_name, width="small"),
                "Diferencia": st.column_config.TextColumn("Diferencia", width="small"),
                "% Diferencia": st.column_config.TextColumn("% Diferencia", width="small"),
                "": st.column_config.TextColumn("", width="small"),
            }
        )
        
        st.markdown("<br>", unsafe_allow_html=True)
    
    # Leyenda
    st.markdown(
        f"""
        <div style='background:#111; padding:12px; border-left:3px solid {CIBAO_ORANGE}; border-radius:6px; margin-top:20px;'>
            <b>Leyenda:</b><br>
             Cibao FC supera al promedio de rivales<br>
             Cibao FC por debajo del promedio de rivales<br>
             Valores iguales
        </div>
        """,
        unsafe_allow_html=True,
    )

