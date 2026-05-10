"""
Generador de HTML profesional con paginación correcta para impresión PDF
Los gráficos se embeben directamente como Plotly JSON
"""

import base64
from datetime import datetime
from typing import Optional, List, Dict

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import plotly.io as pio

# Colores Cibao FC
CIBAO_ORANGE = "#FF8C00"
CIBAO_ORANGE_LIGHT = "#FFC966"
CIBAO_BLACK = "#111111"
CIBAO_GRAY = "#D3D3D3"
CIBAO_WHITE = "#E8E8E8"

LOGO_URL = "https://www.cibaofc.com/wp-content/uploads/2025/02/cropped-LOGO-CFC-5-NARANJA-BLANCO.png"


def get_logo_base64():
    """Descarga logo y lo convierte a base64"""
    try:
        import requests
        r = requests.get(LOGO_URL, timeout=10)
        if r.status_code == 200:
            return base64.b64encode(r.content).decode()
    except:
        pass
    return None


def create_plot_group_figure(df_filtrado, df_liga_mayor, mostrar_promedio_liga, nombre_grupo, mapping):
    """Crea figura de barras horizontales"""
    columnas = [v for v in mapping.values() if v in df_filtrado.columns]
    etiquetas = {v: k for k, v in mapping.items() if v in df_filtrado.columns}
    
    if len(columnas) == 0:
        return None
    
    df_cibao_filtered = df_filtrado.copy()
    cibao_means = df_cibao_filtered[columnas].mean()
    
    comparison_data = []
    for col in columnas:
        comparison_data.append({
            "label": etiquetas[col],
            "Equipo": "Cibao FC",
            "valor": cibao_means[col]
        })
    
    if mostrar_promedio_liga and not df_liga_mayor.empty:
        df_liga_sin_cibao = df_liga_mayor[df_liga_mayor["Team"].str.lower() != "cibao"].copy()
        for col in columnas:
            if col in df_liga_sin_cibao.columns:
                liga_val = pd.to_numeric(df_liga_sin_cibao[col], errors="coerce").mean()
                comparison_data.append({
                    "label": etiquetas[col],
                    "Equipo": "Promedio Liga",
                    "valor": liga_val if not pd.isna(liga_val) else 0
                })
    
    df_plot = pd.DataFrame(comparison_data)
    cibao_order = df_plot[df_plot["Equipo"] == "Cibao FC"].sort_values("valor", ascending=True)["label"].tolist()
    df_plot["label"] = pd.Categorical(df_plot["label"], categories=cibao_order, ordered=True)
    df_plot = df_plot.sort_values("label")
    
    color_map = {
        "Cibao FC": CIBAO_ORANGE,
        "Promedio Liga": CIBAO_ORANGE_LIGHT,
    }
    
    fig = px.bar(
        df_plot,
        x="valor",
        y="label",
        color="Equipo",
        orientation="h",
        text_auto=".2f",
        color_discrete_map=color_map,
        barmode="group",
    )
    
    fig.update_layout(
        height=350,
        template="plotly_dark",
        plot_bgcolor=CIBAO_BLACK,
        paper_bgcolor=CIBAO_BLACK,
        font=dict(color=CIBAO_GRAY, size=12),
        title=dict(text=f"<b>{nombre_grupo}</b>", font=dict(size=18, color=CIBAO_ORANGE)),
        title_x=0.5,
        margin=dict(l=20, r=20, t=50, b=20),
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
    
    return fig


def create_plot_group_vertical_figure(df_filtrado, df_liga_mayor, mostrar_promedio_liga, nombre_grupo, mapping):
    """Crea figura de barras verticales"""
    columnas = [v for v in mapping.values() if v in df_filtrado.columns]
    etiquetas = {v: k for k, v in mapping.items() if v in df_filtrado.columns}
    
    if len(columnas) == 0:
        return None
    
    df_cibao_filtered = df_filtrado.copy()
    cibao_means = df_cibao_filtered[columnas].mean()
    
    comparison_data = []
    for col in columnas:
        comparison_data.append({
            "label": etiquetas[col],
            "Equipo": "Cibao FC",
            "valor": cibao_means[col]
        })
    
    if mostrar_promedio_liga and not df_liga_mayor.empty:
        df_liga_sin_cibao = df_liga_mayor[df_liga_mayor["Team"].str.lower() != "cibao"].copy()
        for col in columnas:
            if col in df_liga_sin_cibao.columns:
                liga_val = pd.to_numeric(df_liga_sin_cibao[col], errors="coerce").mean()
                comparison_data.append({
                    "label": etiquetas[col],
                    "Equipo": "Promedio Liga",
                    "valor": liga_val if not pd.isna(liga_val) else 0
                })
    
    df_plot = pd.DataFrame(comparison_data)
    cibao_order = df_plot[df_plot["Equipo"] == "Cibao FC"].sort_values("valor", ascending=False)["label"].tolist()
    df_plot["label"] = pd.Categorical(df_plot["label"], categories=cibao_order, ordered=True)
    df_plot = df_plot.sort_values("label")
    
    color_map = {
        "Cibao FC": CIBAO_ORANGE,
        "Promedio Liga": CIBAO_ORANGE_LIGHT,
    }
    
    fig = px.bar(
        df_plot,
        x="label",
        y="valor",
        color="Equipo",
        orientation="v",
        text_auto=".2f",
        color_discrete_map=color_map,
        barmode="group",
    )
    
    fig.update_layout(
        height=400,
        template="plotly_dark",
        plot_bgcolor="#111",
        paper_bgcolor="#111",
        font=dict(color="#D3D3D3", size=12),
        title=dict(text=f"<b>{nombre_grupo}</b>", font=dict(size=18, color="#FF8C00")),
        title_x=0.5,
        margin=dict(l=20, r=20, t=50, b=20),
        xaxis=dict(tickangle=-35),
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
    
    return fig


def create_plot_horizontal_figure(df_filtrado, df_liga_mayor, mostrar_promedio_liga, nombre, mapping):
    """Crea figura horizontal"""
    return create_plot_group_figure(df_filtrado, df_liga_mayor, mostrar_promedio_liga, nombre, mapping)


def create_plot_vertical_figure(df_filtrado, df_liga_mayor, mostrar_promedio_liga, nombre, mapping):
    """Crea figura vertical"""
    return create_plot_group_vertical_figure(df_filtrado, df_liga_mayor, mostrar_promedio_liga, nombre, mapping)


def create_gauge_figure(df_filtrado, df_liga_mayor, mostrar_promedio_liga, mapping):
    """Crea gauge"""
    col = list(mapping.values())[0]
    label = list(mapping.keys())[0]
    
    if col not in df_filtrado.columns:
        return None
    
    value = df_filtrado[col].mean()
    max_rango = max(40, value * 1.8)
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title={'text': f"<b>{label}</b>", 'font': {'color': CIBAO_ORANGE, 'size': 18}},
        gauge={
            'axis': {'range': [0, max_rango]},
            'bar': {'color': CIBAO_ORANGE},
            'bgcolor': "#333",
            'borderwidth': 1,
            'bordercolor': "#555",
        }
    ))
    
    fig.update_layout(
        paper_bgcolor=CIBAO_BLACK,
        plot_bgcolor=CIBAO_BLACK,
        height=260,
        margin=dict(l=20, r=20, t=60, b=20),
        font=dict(color=CIBAO_GRAY)
    )
    
    return fig


def create_longitud_pase_figure(df_filtrado, df_liga_mayor, mostrar_promedio_liga, mapping):
    """Crea gauge longitud pase"""
    col = list(mapping.values())[0]
    label = list(mapping.keys())[0]
    
    if col not in df_filtrado.columns:
        return None
    
    value_cibao = df_filtrado[col].mean()
    value_liga = None
    if mostrar_promedio_liga and not df_liga_mayor.empty and col in df_liga_mayor.columns:
        df_liga_sin_cibao = df_liga_mayor[df_liga_mayor["Team"].str.lower() != "cibao"].copy()
        value_liga = pd.to_numeric(df_liga_sin_cibao[col], errors="coerce").mean()
    
    fig = go.Figure()
    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=value_cibao,
        title={'text': f"<b>{label}</b><br><span style='font-size:12px; color:#FFC966'>Cibao FC</span>", 
               'font': {'color': '#FF8C00', 'size': 18}},
        number={'font': {'color': '#FF8C00', 'size': 40}},
        gauge={
            'axis': {'range': [0, max(40, value_cibao * 1.5)]},
            'bar': {'color': "#FF8C00", 'thickness': 0.7},
            'bgcolor': "#333",
            'borderwidth': 1,
            'bordercolor': "#555",
            'steps': [{'range': [0, max(40, value_cibao * 1.5)], 'color': "#1a1a1a"}],
            'threshold': {
                'line': {'color': "#FFC966", 'width': 3},
                'thickness': 0.8,
                'value': value_liga if value_liga and not pd.isna(value_liga) else 0
            } if value_liga and not pd.isna(value_liga) else None
        },
    ))
    
    fig.update_layout(
        height=280,
        margin=dict(l=20, r=20, t=80, b=20),
        paper_bgcolor="#111",
        font=dict(color="#D3D3D3")
    )
    
    return fig


def create_heatmap_figure(df_filtrado, nombre_grupo, mapping):
    """Crea heatmap"""
    dfp = df_filtrado.copy()
    cols = [v for v in mapping.values() if v in dfp.columns]
    labels = [k for k, v in mapping.items() if v in dfp.columns]
    
    if len(cols) == 0:
        return None
    
    series_real = dfp[cols].mean().fillna(0)
    rank = series_real.rank(method="dense") - 1
    rank = rank.astype(int)
    z_vals = rank.to_numpy().reshape(1, -1)
    
    HEATMAP_COLORSCALE = [
        [0.0, "#2a2a2a"],
        [0.5, "#ff7b00"],
        [1.0, "#ffae42"]
    ]
    
    fig = go.Figure(
        data=go.Heatmap(
            z=z_vals,
            x=labels,
            y=[""],
            colorscale=HEATMAP_COLORSCALE,
            showscale=True,
            colorbar=dict(
                thickness=10,
                tickvals=[0, 1, 2],
                ticktext=["Bajo", "Medio", "Alto"],
                bgcolor="#111",
                tickfont=dict(color=CIBAO_GRAY)
            )
        )
    )
    
    annotations = []
    for j, label in enumerate(labels):
        annotations.append(
            dict(
                x=label,
                y="",
                text=f"{series_real.iloc[j]:.2f}",
                font=dict(color="white", size=13),
                showarrow=False
            )
        )
    
    fig.update_layout(
        annotations=annotations,
        height=280,
        template="plotly_dark",
        title=dict(
            text=f"<b>{nombre_grupo}</b>",
            font=dict(size=18, color=CIBAO_ORANGE)
        ),
        title_x=0.5,
        paper_bgcolor="#111",
        plot_bgcolor="#111",
        margin=dict(l=20, r=20, t=50, b=20)
    )
    
    return fig


def generate_html_report(
    df_cibao: pd.DataFrame,
    df_filtrado: pd.DataFrame,
    df_liga_mayor: pd.DataFrame,
    partidos_seleccionados: List[str],
    mostrar_promedio_liga: bool = True,
    grupos: Dict = None,
    grupos_pases: Dict = None,
    grupos_def: Dict = None,
    grupos_tacticos: Dict = None,
    metrics_blocks: Dict = None,
    opponent_choice: str = None,
    x_metric: str = None,
    y_metric: str = None,
    x_label: str = None,
    y_label: str = None,
    make_team_scatter_func=None,
) -> str:
    """
    Genera HTML completo con paginación correcta para impresión PDF
    """
    
    logo_b64 = get_logo_base64()
    fecha = datetime.now().strftime("%d de %B de %Y")
    chart_counter = 0
    
    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reporte Cibao FC</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        @page {{
            size: A4 landscape;
            margin: 15mm;
        }}
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Arial', sans-serif;
            background: {CIBAO_BLACK};
            color: {CIBAO_WHITE};
        }}
        
        .page {{
            width: 277mm;
            min-height: 180mm;
            max-height: 180mm;
            background: {CIBAO_BLACK};
            margin: 0 auto;
            padding: 15mm;
            page-break-after: always;
            page-break-inside: avoid;
            overflow: hidden;
        }}
        
        .page:last-child {{
            page-break-after: auto;
        }}
        
        .portada {{
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
            height: 100%;
        }}
        
        .portada img {{
            max-width: 120px;
            margin-bottom: 20px;
        }}
        
        .portada h1 {{
            color: {CIBAO_ORANGE};
            font-size: 32px;
            margin-bottom: 15px;
        }}
        
        .portada h2 {{
            color: {CIBAO_WHITE};
            font-size: 20px;
            margin-bottom: 10px;
        }}
        
        .portada p {{
            color: {CIBAO_GRAY};
            font-size: 12px;
        }}
        
        .section-title {{
            color: {CIBAO_ORANGE};
            font-size: 22px;
            text-align: center;
            margin-bottom: 15px;
            padding-bottom: 8px;
            border-bottom: 2px solid {CIBAO_ORANGE};
        }}
        
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            margin-bottom: 15px;
        }}
        
        .kpi-box {{
            background: rgba(255, 140, 0, 0.1);
            border: 2px solid {CIBAO_ORANGE};
            padding: 12px;
            text-align: center;
            border-radius: 5px;
        }}
        
        .kpi-value {{
            color: {CIBAO_ORANGE};
            font-size: 20px;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        
        .kpi-label {{
            color: {CIBAO_GRAY};
            font-size: 11px;
        }}
        
        .charts-grid-3 {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            margin-bottom: 10px;
        }}
        
        .charts-grid-2 {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
            margin-bottom: 10px;
        }}
        
        .chart-container {{
            background: rgba(255, 255, 255, 0.05);
            padding: 10px;
            border-radius: 5px;
            min-height: 200px;
            max-height: 200px;
            overflow: hidden;
        }}
        
        .chart-container-large {{
            background: rgba(255, 255, 255, 0.05);
            padding: 10px;
            border-radius: 5px;
            min-height: 250px;
            max-height: 250px;
            overflow: hidden;
        }}
        
        .table-container {{
            margin-top: 10px;
            font-size: 10px;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            background: rgba(255, 255, 255, 0.05);
        }}
        
        th {{
            background: {CIBAO_ORANGE};
            color: {CIBAO_BLACK};
            padding: 8px;
            text-align: left;
            font-size: 11px;
        }}
        
        td {{
            padding: 6px;
            border-bottom: 1px solid rgba(255, 140, 0, 0.3);
            font-size: 10px;
        }}
        
        @media print {{
            body {{
                background: {CIBAO_BLACK};
            }}
            .page {{
                margin: 0;
                page-break-after: always;
                page-break-inside: avoid;
            }}
        }}
    </style>
</head>
<body>
"""
    
    # ===== PORTADA =====
    html += f"""
    <div class="page portada">
        {f'<img src="data:image/png;base64,{logo_b64}" alt="Logo Cibao FC">' if logo_b64 else ''}
        <h1>REPORTE DE RENDIMIENTO COLECTIVO</h1>
        <h2>Cibao FC - Liga Dominicana</h2>
        <p>Fecha de generación: {fecha}</p>
    </div>
    """
    
    # ===== KPIs Y GRÁFICO COMPARATIVO =====
    html += '<div class="page">'
    html += '<h2 class="section-title">INDICADORES DEL ÚLTIMO PARTIDO</h2>'
    
    if not df_filtrado.empty:
        ultimo_partido = df_filtrado.sort_values("Date", ascending=False).iloc[0]
        
        fecha_str = "-"
        if pd.notna(ultimo_partido.get("Date", None)):
            try:
                fecha_str = pd.to_datetime(ultimo_partido["Date"]).strftime("%d-%m-%Y")
            except:
                fecha_str = str(ultimo_partido.get("Date", ""))
        
        kpi_data = [
            ("Fecha", fecha_str),
            ("Jornada", str(ultimo_partido.get("Jornada", ""))),
            ("Resultado", str(ultimo_partido.get("Final Result", ""))),
            ("xG", f"{ultimo_partido.get('xg', 0):.2f}" if pd.notna(ultimo_partido.get('xg')) else "-"),
            ("Posesión %", f"{ultimo_partido.get('possession_percent', 0):.1f}%" if pd.notna(ultimo_partido.get('possession_percent')) else "-"),
            ("Tarjetas A", str(int(ultimo_partido.get("yellow_cards", 0))) if pd.notna(ultimo_partido.get("yellow_cards")) else "-"),
        ]
        
        html += '<div class="kpi-grid">'
        for label, value in kpi_data:
            html += f'''
            <div class="kpi-box">
                <div class="kpi-value">{value}</div>
                <div class="kpi-label">{label}</div>
            </div>
            '''
        html += '</div>'
        
        # Gráfico comparativo
        if make_team_scatter_func and not df_liga_mayor.empty and opponent_choice:
            try:
                filters = {"Competition": lambda s: s.str.contains("Liga", case=False, na=False)}
                fig_scatter, _, _ = make_team_scatter_func(
                    df_liga_mayor,
                    primary_team="Cibao",
                    opponent=opponent_choice,
                    x_metric=x_metric or "goals",
                    y_metric=y_metric or "conceded_goals",
                    x_label=x_label or "Goles por 90",
                    y_label=y_label or "Goles en contra por 90",
                    title="Comparativa Liga",
                    filters=filters,
                )
                fig_json = pio.to_json(fig_scatter)
                html += f'<div class="chart-container-large"><div id="chart-{chart_counter}"></div></div>'
                html += f'<script>Plotly.newPlot("chart-{chart_counter}", {fig_json}, {{responsive: true, displayModeBar: false}});</script>'
                chart_counter += 1
            except Exception as e:
                html += f'<p>Error: {str(e)}</p>'
    
    html += '</div>'
    
    # ===== EFICIENCIA Y ATAQUE =====
    if grupos:
        html += '<div class="page">'
        html += '<h2 class="section-title">Eficiencia y Ataque</h2>'
        html += '<div class="charts-grid-3">'
        
        grupos_lista = [
            "Producción ofensiva directa",
            "Eficiencia en el tiro",
            "Patrones de ataque"
        ]
        
        for nombre_grupo in grupos_lista:
            if nombre_grupo in grupos:
                try:
                    fig = create_plot_group_figure(
                        df_filtrado, df_liga_mayor, mostrar_promedio_liga,
                        nombre_grupo, grupos[nombre_grupo]
                    )
                    if fig:
                        fig_json = pio.to_json(fig)
                        html += f'<div class="chart-container"><div id="chart-{chart_counter}"></div></div>'
                        html += f'<script>Plotly.newPlot("chart-{chart_counter}", {fig_json}, {{responsive: true, displayModeBar: false}});</script>'
                        chart_counter += 1
                except Exception as e:
                    html += f'<p>Error: {str(e)}</p>'
        
        html += '</div>'
        html += '<div class="charts-grid-2" style="margin-top: 10px;">'
        
        grupos_abajo = [
            "Balón parado y definición",
            "Juego interior y profundidad"
        ]
        
        for nombre_grupo in grupos_abajo:
            if nombre_grupo in grupos:
                try:
                    fig = create_plot_group_figure(
                        df_filtrado, df_liga_mayor, mostrar_promedio_liga,
                        nombre_grupo, grupos[nombre_grupo]
                    )
                    if fig:
                        fig_json = pio.to_json(fig)
                        html += f'<div class="chart-container"><div id="chart-{chart_counter}"></div></div>'
                        html += f'<script>Plotly.newPlot("chart-{chart_counter}", {fig_json}, {{responsive: true, displayModeBar: false}});</script>'
                        chart_counter += 1
                except Exception as e:
                    html += f'<p>Error: {str(e)}</p>'
        
        html += '</div></div>'
    
    # ===== CONSTRUCCIÓN Y PASES =====
    if grupos_pases:
        html += '<div class="page">'
        html += '<h2 class="section-title">Construcción y Pases</h2>'
        html += '<div class="charts-grid-3">'
        
        grupos_lista = [
            "Control y estabilidad en la circulación",
            "Seguridad en la progresión",
            "Conexiones de alto valor táctico"
        ]
        
        for nombre_grupo in grupos_lista:
            if nombre_grupo in grupos_pases:
                try:
                    fig = create_plot_group_vertical_figure(
                        df_filtrado, df_liga_mayor, mostrar_promedio_liga,
                        nombre_grupo, grupos_pases[nombre_grupo]
                    )
                    if fig:
                        fig_json = pio.to_json(fig)
                        html += f'<div class="chart-container"><div id="chart-{chart_counter}"></div></div>'
                        html += f'<script>Plotly.newPlot("chart-{chart_counter}", {fig_json}, {{responsive: true, displayModeBar: false}});</script>'
                        chart_counter += 1
                except Exception as e:
                    html += f'<p>Error: {str(e)}</p>'
        
        html += '</div>'
        html += '<div class="charts-grid-2" style="margin-top: 10px;">'
        
        # Reinicios
        if "Reinicios del juego" in grupos_pases:
            try:
                fig = create_plot_group_vertical_figure(
                    df_filtrado, df_liga_mayor, mostrar_promedio_liga,
                    "Reinicios del juego", grupos_pases["Reinicios del juego"]
                )
                if fig:
                    fig_json = pio.to_json(fig)
                    html += f'<div class="chart-container"><div id="chart-{chart_counter}"></div></div>'
                    html += f'<script>Plotly.newPlot("chart-{chart_counter}", {fig_json}, {{responsive: true, displayModeBar: false}});</script>'
                    chart_counter += 1
            except Exception as e:
                html += f'<p>Error: {str(e)}</p>'
        
        # Longitud pase
        if "Longitud media de pase" in grupos_pases:
            try:
                fig = create_longitud_pase_figure(
                    df_filtrado, df_liga_mayor, mostrar_promedio_liga,
                    grupos_pases["Longitud media de pase"]
                )
                if fig:
                    fig_json = pio.to_json(fig)
                    html += f'<div class="chart-container"><div id="chart-{chart_counter}"></div></div>'
                    html += f'<script>Plotly.newPlot("chart-{chart_counter}", {fig_json}, {{responsive: true, displayModeBar: false}});</script>'
                    chart_counter += 1
            except Exception as e:
                html += f'<p>Error: {str(e)}</p>'
        
        html += '</div></div>'
    
    # ===== DEFENSA =====
    if grupos_def:
        html += '<div class="page">'
        html += '<h2 class="section-title">Defensa y Eficiencia</h2>'
        html += '<div class="charts-grid-2">'
        
        grupos_horizontales = [
            "Dominio en los duelos (ofensivos y generales)",
            "Solidez defensiva en disputas"
        ]
        
        for nombre_grupo in grupos_horizontales:
            if nombre_grupo in grupos_def:
                try:
                    fig = create_plot_horizontal_figure(
                        df_filtrado, df_liga_mayor, mostrar_promedio_liga,
                        nombre_grupo, grupos_def[nombre_grupo]
                    )
                    if fig:
                        fig_json = pio.to_json(fig)
                        html += f'<div class="chart-container"><div id="chart-{chart_counter}"></div></div>'
                        html += f'<script>Plotly.newPlot("chart-{chart_counter}", {fig_json}, {{responsive: true, displayModeBar: false}});</script>'
                        chart_counter += 1
                except Exception as e:
                    html += f'<p>Error: {str(e)}</p>'
        
        html += '</div>'
        html += '<div class="charts-grid-2" style="margin-top: 10px;">'
        
        grupos_verticales = [
            "Acciones defensivas por 90'",
            "Volumen y calidad de llegadas rivales"
        ]
        
        for nombre_grupo in grupos_verticales:
            if nombre_grupo in grupos_def:
                try:
                    fig = create_plot_vertical_figure(
                        df_filtrado, df_liga_mayor, mostrar_promedio_liga,
                        nombre_grupo, grupos_def[nombre_grupo]
                    )
                    if fig:
                        fig_json = pio.to_json(fig)
                        html += f'<div class="chart-container"><div id="chart-{chart_counter}"></div></div>'
                        html += f'<script>Plotly.newPlot("chart-{chart_counter}", {fig_json}, {{responsive: true, displayModeBar: false}});</script>'
                        chart_counter += 1
                except Exception as e:
                    html += f'<p>Error: {str(e)}</p>'
        
        html += '</div>'
        
        # Gauge
        if "Distancia media de disparo" in grupos_def:
            try:
                fig = create_gauge_figure(
                    df_filtrado, df_liga_mayor, mostrar_promedio_liga,
                    grupos_def["Distancia media de disparo"]
                )
                if fig:
                    fig_json = pio.to_json(fig)
                    html += f'<div class="chart-container" style="max-width: 300px; margin: 10px auto;"><div id="chart-{chart_counter}"></div></div>'
                    html += f'<script>Plotly.newPlot("chart-{chart_counter}", {fig_json}, {{responsive: true, displayModeBar: false}});</script>'
                    chart_counter += 1
            except Exception as e:
                html += f'<p>Error: {str(e)}</p>'
        
        html += '</div>'
    
    # ===== DISTRIBUCIÓN TÁCTICA =====
    if grupos_tacticos:
        html += '<div class="page">'
        html += '<h2 class="section-title">Distribución Táctica</h2>'
        html += '<div class="charts-grid-2">'
        
        heatmaps = [
            "Mapa de Recuperaciones por Altura",
            "Mapa de Presión por Altura"
        ]
        
        for nombre_grupo in heatmaps:
            if nombre_grupo in grupos_tacticos:
                try:
                    fig = create_heatmap_figure(
                        df_filtrado, nombre_grupo, grupos_tacticos[nombre_grupo]
                    )
                    if fig:
                        fig_json = pio.to_json(fig)
                        html += f'<div class="chart-container-large"><div id="chart-{chart_counter}"></div></div>'
                        html += f'<script>Plotly.newPlot("chart-{chart_counter}", {fig_json}, {{responsive: true, displayModeBar: false}});</script>'
                        chart_counter += 1
                except Exception as e:
                    html += f'<p>Error: {str(e)}</p>'
        
        html += '</div></div>'
    
    # ===== TABLAS =====
    if metrics_blocks and not df_filtrado.empty:
        html += '<div class="page">'
        html += '<h2 class="section-title">Análisis Comparativo (Tablas)</h2>'
        
        df_base = df_filtrado.copy().sort_values("Date", ascending=False)
        df_base = df_base.head(min(len(df_base), 5))
        
        df_liga_sin_cibao = None
        if mostrar_promedio_liga and not df_liga_mayor.empty:
            df_liga_sin_cibao = df_liga_mayor[df_liga_mayor["Team"].str.lower() != "cibao"].copy()
        
        for block_name, metrics_dict in metrics_blocks.items():
            html += f'<div class="table-container">'
            html += f'<h3 style="color: {CIBAO_ORANGE}; margin: 15px 0 10px 0; font-size: 16px;">Bloque {block_name}</h3>'
            
            columnas_existentes = [c for c in metrics_dict.values() if c in df_base.columns]
            if not columnas_existentes:
                continue
            
            columnas_existentes = columnas_existentes[:5]
            label_map = {v: k for k, v in metrics_dict.items() if v in columnas_existentes}
            
            html += '<table>'
            html += '<thead><tr>'
            html += '<th>Match</th>'
            for col in columnas_existentes:
                label = label_map.get(col, col)
                if len(label) > 20:
                    label = label[:17] + "..."
                html += f'<th>{label}</th>'
            html += '</tr></thead><tbody>'
            
            for _, row in df_base.iterrows():
                html += '<tr>'
                match_name = str(row.get("Match", ""))[:25]
                html += f'<td>{match_name}</td>'
                for col in columnas_existentes:
                    val = row.get(col, pd.nan)
                    if pd.notna(val):
                        if isinstance(val, (int, float)):
                            val_str = f"{val:.2f}"
                        else:
                            val_str = str(val)
                    else:
                        val_str = "-"
                    html += f'<td>{val_str}</td>'
                html += '</tr>'
            
            # Promedio liga
            if df_liga_sin_cibao is not None:
                html += '<tr style="background: rgba(255, 140, 0, 0.2); font-weight: bold;">'
                html += '<td>Promedio Liga</td>'
                for col in columnas_existentes:
                    if col in df_liga_sin_cibao.columns:
                        liga_val = pd.to_numeric(df_liga_sin_cibao[col], errors="coerce").mean()
                        if pd.notna(liga_val):
                            val_str = f"{liga_val:.2f}"
                        else:
                            val_str = "-"
                    else:
                        val_str = "-"
                    html += f'<td>{val_str}</td>'
                html += '</tr>'
            
            html += '</tbody></table></div>'
        
        html += '</div>'
    
    html += """
    </body>
</html>
    """
    
    return html
