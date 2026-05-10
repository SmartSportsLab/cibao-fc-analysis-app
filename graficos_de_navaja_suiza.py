#!/usr/bin/env python3
"""
graficos_de_navaja_suiza.py
============================

Swiss-army-knife helper to produce quick visualizations from the
Liga Mayor per-90 data set. Edit the CONFIG section and run the script
with `python graficos_de_navaja_suiza.py` to generate the figure.

Requirements: pandas, plotly
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, Optional

import unicodedata
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ---------------------------------------------------------------------------
# CONFIG — edit these variables to change the behaviour
# ---------------------------------------------------------------------------

# Path to the Excel file (relative to project root)
DATA_FILE = Path("data/raw/wyscout/Global/Liga_Mayor_Clean_Per_90.xlsx")

# Choose chart type: "scatter", "bar", "line", "box"
CHART_TYPE = "scatter"

# Filtering options. Keys correspond to column names and values are callables
# that take a pandas Series and return a boolean mask.
FILTERS: Dict[str, callable] = {}

# Aggregate by team (True) or show match-by-match data (False)
AGGREGATE_BY_TEAM = True
GROUP_BY_COLUMN = "Team"
AGG_FUNCTION = "mean"  # "mean", "median", "sum", etc.
# Columns to preserve during aggregation (e.g., league name)
KEEP_COLUMNS = []

# Highlight settings
PRIMARY_TEAM = "Cibao"
NEXT_OPPONENT = "Atlético Pantoja"
# Teams in this list keep their club colors; others are greyed out
FOCUS_TEAMS = [PRIMARY_TEAM, NEXT_OPPONENT]
DEFAULT_OTHER_COLOR = "#6B7280"  # lighter grey
DEFAULT_OTHER_OPACITY = 0.6

# Metric configuration depending on chart type
# For scatter/line we expect x and y; optional: color, size, hover_data list.
SCATTER_CONFIG = {
    "x": ("Goles por 90", "Goals"),
    "y": ("Goles en contra por 90", "Conceded goals"),
    "color": None,
    "size": None,
    "hover_data": [],
    "title": "Liga Mayor — Goles a favor vs Goles en contra por 90",
}

# For bar charts we provide a list of metrics to display with friendly labels
BAR_CONFIG = {
    "category": ("Equipo", "Team"),
    "metrics": [
        ("Goles por 90", "Goals"),
        ("Goles en contra por 90", "Conceded goals"),
        ("xG por 90", "xG"),
    ],
    "orientation": "v",  # "v" o "h"
    "title": "Liga Mayor — Métricas ofensivas vs defensivas",
}

# For line charts
LINE_CONFIG = {
    "x": ("Fecha", "Date"),
    "y": ("Goles por 90", "Goals"),
    "color": ("Equipo", "Team"),
    "title": "Evolución de los goles por 90",
}

# For box plots
BOX_CONFIG = {
    "x": ("Equipo", "Team"),
    "y": ("Goles por 90", "Goals"),
    "title": "Distribución de los goles por 90",
}

METRIC_OPTIONS = {
    "Goles por 90": "Goals",  # Updated to match actual column name
    "Goles en contra por 90": "Conceded goals",  # Updated to match actual column name
    "xG por 90": "xG",
    "Tiros a puerta por 90": "Shots On Target",  # NEW FORMAT
    "Posesión (%)": "Possession, %",  # Updated to match actual column name
    # Note: "Tiros por 90" removed as there's no total shots column in the data
}

METRIC_LABELS = {value: label for label, value in METRIC_OPTIONS.items()}

# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def load_data(file_path: Path) -> pd.DataFrame:
    path = Path(__file__).resolve().parent / file_path
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {path}")

    sheets = pd.read_excel(path, sheet_name=None)
    frames = []
    for sheet_name, df_sheet in sheets.items():
        df_sheet = df_sheet.copy()
        df_sheet.columns = [c.strip().replace("\n", " ").replace("  ", " ") for c in df_sheet.columns]
        if "Team" not in df_sheet.columns:
            display_name = TEAM_NAMES_NORMALIZED.get(normalize_team_name(sheet_name), sheet_name)
            df_sheet["Team"] = display_name
        else:
            df_sheet["Team"] = df_sheet["Team"].astype(str).str.strip()
            df_sheet["Team"] = df_sheet["Team"].apply(lambda name: TEAM_NAMES_NORMALIZED.get(normalize_team_name(name), name))
        if "Date" in df_sheet.columns:
            df_sheet["Date"] = pd.to_datetime(df_sheet["Date"], errors="coerce")
        frames.append(df_sheet)

    df = pd.concat(frames, ignore_index=True)
    return df


def load_team_colors(csv_path: Path = Path("assets/Esquema de Colores.csv")) -> dict:
    color_path = Path(__file__).resolve().parent / csv_path
    if not color_path.exists():
        return {}
    try:
        df_colors = pd.read_csv(color_path)
        if {"Equipo", "Hex Color"}.issubset(df_colors.columns):
            df_colors["Equipo"] = df_colors["Equipo"].astype(str).str.strip()
            df_colors["Hex Color"] = df_colors["Hex Color"].astype(str).str.strip()
            return dict(zip(df_colors["Equipo"], df_colors["Hex Color"]))
    except Exception as exc:
        print(f" Could not load color scheme: {exc}")
    return {}




def normalize_team_name(name: str) -> str:
    if not isinstance(name, str):
        return ""
    normalized = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    return normalized.strip().lower()




def build_summary_text(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    primary_team: Optional[str] = None,
    opponent: Optional[str] = None,
    group_col: str = GROUP_BY_COLUMN,
) -> str:
    total = len(df)
    if total == 0:
        return ""
    names = df[group_col].astype(str)
    normalized = names.apply(normalize_team_name)
    goals_rank = df[x_col].rank(ascending=False, method="min")
    conceded_rank = df[y_col].rank(ascending=True, method="min")
    teams = []
    if isinstance(primary_team, str) and primary_team.strip():
        teams.append(primary_team)
    if isinstance(opponent, str) and opponent.strip() and normalize_team_name(opponent) != normalize_team_name(primary_team or ""):
        teams.append(opponent)
    if not teams:
        teams = [PRIMARY_TEAM, NEXT_OPPONENT]
    fragments = []
    for team in teams:
        norm = normalize_team_name(team)
        match_indices = normalized[normalized == norm].index
        if match_indices.empty:
            continue
        idx = match_indices[0]
        display_name = names.loc[idx]
        goals = df.loc[idx, x_col]
        conceded = df.loc[idx, y_col]
        goals_pos = int(goals_rank.loc[idx])
        conceded_pos = int(conceded_rank.loc[idx])
        fragments.append(
            f"{display_name}: {goals:.2f} goles/90 (puesto {goals_pos}/{total} en ataque) y "
            f"{conceded:.2f} recibidos/90 (puesto {conceded_pos}/{total} en defensa)"
        )
    return "  |  ".join(fragments)


TEAM_COLORS = load_team_colors()
TEAM_COLORS_NORMALIZED = {normalize_team_name(k): (v if v.startswith("#") else f"#{v}") for k, v in TEAM_COLORS.items()}
TEAM_COLORS = {k: (v if v.startswith("#") else f"#{v}") for k, v in TEAM_COLORS.items()}
TEAM_NAMES_NORMALIZED = {normalize_team_name(k): k for k in TEAM_COLORS.keys()}


def apply_filters(df: pd.DataFrame, filters: Optional[Dict[str, callable]] = None) -> pd.DataFrame:
    filters = filters if filters is not None else FILTERS
    filtered = df.copy()
    for column, func in filters.items():
        if column in filtered.columns:
            try:
                mask = func(filtered[column])
                filtered = filtered[mask]
            except Exception as exc:
                print(f" Filter on column '{column}' failed: {exc}")
    return filtered


def aggregate(
    df: pd.DataFrame,
    aggregate_by_team: Optional[bool] = None,
    group_col: str = GROUP_BY_COLUMN,
    keep_columns: Optional[list] = None,
    agg_function: str = AGG_FUNCTION,
) -> pd.DataFrame:
    aggregate_flag = AGGREGATE_BY_TEAM if aggregate_by_team is None else aggregate_by_team
    if not aggregate_flag:
        return df
    if group_col not in df.columns:
        raise KeyError(f"Group-by column '{group_col}' missing in data")

    numeric_columns = df.select_dtypes(include="number").columns.tolist()
    numeric_columns = [col for col in numeric_columns if col != group_col]

    agg_dict = {col: agg_function for col in numeric_columns}
    keep_list = keep_columns if keep_columns is not None else KEEP_COLUMNS
    for col in keep_list:
        if col in df.columns and col != group_col:
            agg_dict[col] = "first"

    if not agg_dict:
        raise ValueError("No numeric columns available for aggregation. Set aggregate_by_team=False or adjust configuration.")

    grouped = df.groupby(group_col).agg(agg_dict).reset_index()
    return grouped


def get_metric(df: pd.DataFrame, config_entry: Optional[tuple]):
    if config_entry is None:
        return None, None
    label, column = config_entry
    
    # Try exact match first
    if column in df.columns:
        return label, column
    
    # Try case-insensitive match
    df_cols_lower = {str(c).lower(): c for c in df.columns}
    column_lower = column.lower()
    if column_lower in df_cols_lower:
        return label, df_cols_lower[column_lower]
    
    # Normalize column name for mapping lookup (replace spaces with underscores)
    column_normalized = column_lower.replace(" ", "_").replace("-", "_")
    
    # Try mapping common variations
    column_mappings = {
        "goals": ["Goals", "Goles", "goal", "gol", "Goles A Favor", "goals"],  # Added lowercase
        "conceded_goals": ["Conceded goals", "Goles en contra", "Goles En Contra", "conceded", "goles_concedidos", "Goals Against", "Goals conceded", "goalsConceded", "Goals Conceded"],  # Added camelCase and title case
        "xg": ["xG", "Expected Goals", "expected_goals"],
        "shots": ["Shots", "Tiros", "shot", "tiro"],  # NEW FORMAT only
        "shots_on_target": ["Shots On Target", "Tiros a puerta", "shots_on_target", "on_target"],  # NEW FORMAT
        "possession_percent": ["Possession, %", "Posesión", "possession", "posesion", "Possession, %"]
    }
    
    # Check both the normalized version and the original lowercase
    mapping_key = column_normalized if column_normalized in column_mappings else column_lower
    if mapping_key in column_mappings:
        for mapped_col in column_mappings[mapping_key]:
            if mapped_col in df.columns:
                return label, mapped_col
            # Try case-insensitive
            for df_col in df.columns:
                if str(df_col).lower() == mapped_col.lower():
                    return label, df_col
    
    # Last resort: try partial matching for common terms
    if "conceded" in column_lower or "against" in column_lower:
        for df_col in df.columns:
            col_lower = str(df_col).lower()
            if "conceded" in col_lower or "against" in col_lower or "recibidos" in col_lower:
                return label, df_col
    
    # Show more columns in error message for debugging
    available_cols = list(df.columns)
    cols_preview = available_cols[:20] if len(available_cols) > 20 else available_cols
    raise KeyError(f"Column '{column}' not found for metric '{label}'. Available columns ({len(available_cols)} total): {cols_preview}...")


# ---------------------------------------------------------------------------
# CHART BUILDERS
# ---------------------------------------------------------------------------

def build_scatter(
    df: pd.DataFrame,
    scatter_config: Optional[dict] = None,
    aggregate_by_team: Optional[bool] = None,
    group_by_column: Optional[str] = None,
    focus_teams: Optional[list] = None,
    primary_team: Optional[str] = None,
    opponent: Optional[str] = None,
    default_other_color: Optional[str] = None,
    default_other_opacity: Optional[float] = None,
) -> go.Figure:
    config = scatter_config or SCATTER_CONFIG
    aggregate_flag = AGGREGATE_BY_TEAM if aggregate_by_team is None else aggregate_by_team
    group_col = group_by_column or GROUP_BY_COLUMN
    primary_name = PRIMARY_TEAM if primary_team is None else primary_team
    opponent_name = NEXT_OPPONENT if opponent is None else opponent
    other_color = default_other_color or DEFAULT_OTHER_COLOR
    other_opacity = DEFAULT_OTHER_OPACITY if default_other_opacity is None else default_other_opacity
    focus_list = focus_teams[:] if focus_teams else []
    if not focus_list:
        for name in (primary_name, opponent_name):
            if isinstance(name, str) and name.strip() and name not in focus_list:
                focus_list.append(name)
    if not focus_list:
        focus_list = [name for name in FOCUS_TEAMS if isinstance(name, str) and name.strip()]

    x_label, x_col = get_metric(df, config.get("x"))
    y_label, y_col = get_metric(df, config.get("y"))
    color_label, color_col = get_metric(df, config.get("color"))
    size_label, size_col = get_metric(df, config.get("size"))

    # Only label Cibao and the selected opponent
    text_labels = None
    if aggregate_flag and group_col in df.columns:
        focus_normalized = {normalize_team_name(t) for t in focus_list if isinstance(t, str) and t}
        text_labels = []
        for team in df[group_col]:
            team_norm = normalize_team_name(team)
            if team_norm in focus_normalized:
                text_labels.append(team)
            else:
                text_labels.append("")  # Empty string for non-focus teams

    fig = px.scatter(
        df,
        x=x_col,
        y=y_col,
        color=color_col if color_col else None,
        size=size_col if size_col else None,
        hover_data=config.get("hover_data", []),
        text=text_labels,  # Only labels Cibao and selected opponent
        labels={x_col: x_label, y_col: y_label},
        title=config.get("title"),
        template="plotly_dark",
    )

    if aggregate_flag:
        resumen = build_summary_text(df, x_col, y_col, primary_team=primary_name, opponent=opponent_name, group_col=group_col)
        if resumen:
            fig.add_annotation(
                text=resumen,
                xref="paper",
                yref="paper",
                x=0,
                y=1.08,
                showarrow=False,
                align="left",
                font=dict(color="#E5E7EB", size=13),
            )
        avg_x = df[x_col].mean()
        avg_y = df[y_col].mean()
        x_min_data, x_max_data = df[x_col].min(), df[x_col].max()
        y_min_data, y_max_data = df[y_col].min(), df[y_col].max()
        x_pad = max((x_max_data - x_min_data) * 0.08, 0.05)
        y_pad = max((y_max_data - y_min_data) * 0.08, 0.05)
        x_min, x_max = x_min_data - x_pad, x_max_data + x_pad
        y_min, y_max = y_min_data - y_pad, y_max_data + y_pad
        fig.update_xaxes(range=[x_min, x_max])
        fig.update_yaxes(range=[y_min, y_max])
        focus_normalized = {normalize_team_name(t) for t in focus_list if isinstance(t, str) and t}
        quadrants = {"top_left": False, "top_right": False, "bottom_left": False, "bottom_right": False}
        for team in df[group_col]:
            team_norm = normalize_team_name(team)
            if team_norm in focus_normalized:
                row = df[df[group_col] == team]
                if row.empty:
                    continue
                x_val = row.iloc[0][x_col]
                y_val = row.iloc[0][y_col]
                if x_val <= avg_x and y_val >= avg_y:
                    quadrants["top_left"] = True
                if x_val > avg_x and y_val >= avg_y:
                    quadrants["top_right"] = True
                if x_val <= avg_x and y_val < avg_y:
                    quadrants["bottom_left"] = True
                if x_val > avg_x and y_val < avg_y:
                    quadrants["bottom_right"] = True
        x_text_low = x_label.lower()
        x_text_high = x_label.lower()
        y_text_low = y_label.lower()
        y_text_high = y_label.lower()
        fill_styles = {
            "top_left": ("rgba(94,234,212,0.12)", f"Menos {x_text_high}<br>Más {y_text_high}"),
            "top_right": ("rgba(252,165,165,0.14)", f"Más {x_text_high}<br>Más {y_text_high}"),
            "bottom_left": ("rgba(148,163,184,0.12)", f"Menos {x_text_high}<br>Menos {y_text_low}"),
            "bottom_right": ("rgba(147,197,253,0.16)", f"Más {x_text_high}<br>Menos {y_text_low}"),
        }
        if quadrants["top_left"]:
            fig.add_shape(type="rect", x0=x_min, x1=avg_x, y0=avg_y, y1=y_max,
                          fillcolor=fill_styles["top_left"][0], line=dict(width=0))
            fig.add_annotation(
                x=x_min + (avg_x - x_min)/2,
                y=avg_y + (y_max - avg_y)/2,
                text=fill_styles["top_left"][1],
                showarrow=False,
                font=dict(color="#F9FAFB", size=12),
                align="center",
                bgcolor="rgba(17,24,39,0.80)",
                borderpad=6,
                bordercolor="rgba(15,23,42,0.9)",
                borderwidth=1,
                opacity=0.95,
            )
        if quadrants["top_right"]:
            fig.add_shape(type="rect", x0=avg_x, x1=x_max, y0=avg_y, y1=y_max,
                          fillcolor=fill_styles["top_right"][0], line=dict(width=0))
            fig.add_annotation(
                x=avg_x + (x_max - avg_x)/2,
                y=avg_y + (y_max - avg_y)/2,
                text=fill_styles["top_right"][1],
                showarrow=False,
                font=dict(color="#F9FAFB", size=12),
                align="center",
                bgcolor="rgba(17,24,39,0.80)",
                borderpad=6,
                bordercolor="rgba(15,23,42,0.9)",
                borderwidth=1,
                opacity=0.95,
            )
        if quadrants["bottom_left"]:
            fig.add_shape(type="rect", x0=x_min, x1=avg_x, y0=y_min, y1=avg_y,
                          fillcolor=fill_styles["bottom_left"][0], line=dict(width=0))
            fig.add_annotation(
                x=x_min + (avg_x - x_min)/2,
                y=y_min + (avg_y - y_min)/2,
                text=fill_styles["bottom_left"][1],
                showarrow=False,
                font=dict(color="#F9FAFB", size=12),
                align="center",
                bgcolor="rgba(17,24,39,0.80)",
                borderpad=6,
                bordercolor="rgba(15,23,42,0.9)",
                borderwidth=1,
                opacity=0.95,
            )
        if quadrants["bottom_right"]:
            fig.add_shape(type="rect", x0=avg_x, x1=x_max, y0=y_min, y1=avg_y,
                          fillcolor=fill_styles["bottom_right"][0], line=dict(width=0))
            fig.add_annotation(
                x=avg_x + (x_max - avg_x)/2,
                y=y_min + (avg_y - y_min)/2,
                text=fill_styles["bottom_right"][1],
                showarrow=False,
                font=dict(color="#F9FAFB", size=12),
                align="center",
                bgcolor="rgba(17,24,39,0.80)",
                borderpad=6,
                bordercolor="rgba(15,23,42,0.9)",
                borderwidth=1,
                opacity=0.95,
            )
        fig.add_shape(
            type="line",
            x0=avg_x,
            x1=avg_x,
            y0=y_min,
            y1=y_max,
            line=dict(color="rgba(229,231,235,0.55)", width=1, dash="dash"),
        )
        fig.add_shape(
            type="line",
            x0=x_min,
            x1=x_max,
            y0=avg_y,
            y1=avg_y,
            line=dict(color="rgba(229,231,235,0.55)", width=1, dash="dash"),
        )
        fig.add_annotation(x=avg_x, y=y_max, text="Promedio goles", showarrow=False, yshift=12, font=dict(color="#E5E7EB"))
        fig.add_annotation(x=x_max, y=avg_y, text="Promedio encajados", showarrow=False, xshift=-90, font=dict(color="#E5E7EB"))

        colors = []
        opacities = []
        for team in df[group_col]:
            team_norm = normalize_team_name(team)
            color = TEAM_COLORS.get(team) or TEAM_COLORS_NORMALIZED.get(team_norm)
            if team_norm in focus_normalized:
                colors.append(color if color else "#636EFA")
                opacities.append(1.0)
            else:
                colors.append(other_color)
                opacities.append(other_opacity)
        fig.update_traces(marker=dict(color=colors, size=18, opacity=opacities))
    else:
        fig.update_traces(marker=dict(size=18))
    # Only set textposition if we have text labels (for Cibao and selected opponent)
    if aggregate_flag and group_col in df.columns and text_labels and any(text_labels):
        fig.update_traces(textposition="top center", cliponaxis=False)
    return fig


def build_bar(df: pd.DataFrame) -> go.Figure:
    cat_label, cat_col = get_metric(df, BAR_CONFIG.get("category"))
    if cat_col is None:
        raise ValueError("BAR_CONFIG needs a 'category' entry")

    df_long = df[[cat_col] + [col for _, col in BAR_CONFIG["metrics"] if col in df.columns]].copy()
    df_long = df_long.melt(id_vars=cat_col, var_name="metric", value_name="value")
    metric_map = {col: label for label, col in BAR_CONFIG["metrics"]}
    df_long["metric_label"] = df_long["metric"].map(metric_map)

    fig = px.bar(
        df_long,
        x=cat_col if BAR_CONFIG.get("orientation", "v") == "v" else "value",
        y="value" if BAR_CONFIG.get("orientation", "v") == "v" else cat_col,
        color="metric_label",
        orientation=BAR_CONFIG.get("orientation", "v"),
        title=BAR_CONFIG.get("title"),
        template="plotly_dark",
    )
    fig.update_layout(barmode="group")
    return fig


def build_line(df: pd.DataFrame) -> go.Figure:
    x_label, x_col = get_metric(df, LINE_CONFIG.get("x"))
    y_label, y_col = get_metric(df, LINE_CONFIG.get("y"))
    color_label, color_col = get_metric(df, LINE_CONFIG.get("color"))

    fig = px.line(
        df,
        x=x_col,
        y=y_col,
        color=color_col if color_col else None,
        labels={x_col: x_label, y_col: y_label},
        title=LINE_CONFIG.get("title"),
        template="plotly_dark",
    )
    return fig


def build_box(df: pd.DataFrame) -> go.Figure:
    x_label, x_col = get_metric(df, BOX_CONFIG.get("x"))
    y_label, y_col = get_metric(df, BOX_CONFIG.get("y"))

    fig = px.box(
        df,
        x=x_col,
        y=y_col,
        labels={x_col: x_label, y_col: y_label},
        title=BOX_CONFIG.get("title"),
        template="plotly_dark",
    )
    return fig




def make_team_scatter(
    df: pd.DataFrame,
    primary_team: str = PRIMARY_TEAM,
    opponent: Optional[str] = NEXT_OPPONENT,
    x_metric: str = SCATTER_CONFIG["x"][1],
    y_metric: str = SCATTER_CONFIG["y"][1],
    x_label: Optional[str] = None,
    y_label: Optional[str] = None,
    title: Optional[str] = None,
    filters: Optional[Dict[str, callable]] = None,
    aggregate_by_team: Optional[bool] = None,
    keep_columns: Optional[list] = None,
    focus_teams: Optional[list] = None,
) -> tuple[go.Figure, str, pd.DataFrame]:
    df_filtered = apply_filters(df, filters)
    prepared = aggregate(
        df_filtered,
        aggregate_by_team=aggregate_by_team,
        group_col=GROUP_BY_COLUMN,
        keep_columns=keep_columns if keep_columns is not None else KEEP_COLUMNS,
    )

    x_display = x_label or METRIC_LABELS.get(x_metric, x_metric)
    y_display = y_label or METRIC_LABELS.get(y_metric, y_metric)
    scatter_config = {
        "x": (x_display, x_metric),
        "y": (y_display, y_metric),
        "color": None,
        "size": None,
        "hover_data": [],
        "title": title or SCATTER_CONFIG.get("title"),
    }

    focus = focus_teams[:] if focus_teams else []
    if not focus:
        for name in (primary_team, opponent):
            if isinstance(name, str) and name.strip() and name not in focus:
                focus.append(name)

    fig = build_scatter(
        prepared,
        scatter_config=scatter_config,
        aggregate_by_team=aggregate_by_team,
        group_by_column=GROUP_BY_COLUMN,
        focus_teams=focus,
        primary_team=primary_team,
        opponent=opponent,
        default_other_color=DEFAULT_OTHER_COLOR,
        default_other_opacity=DEFAULT_OTHER_OPACITY,
    )
    
    # Get the actual column names from the DataFrame using get_metric
    _, x_col_actual = get_metric(prepared, scatter_config.get("x"))
    _, y_col_actual = get_metric(prepared, scatter_config.get("y"))
    
    resumen = build_summary_text(
        prepared,
        x_col_actual if x_col_actual else x_metric,
        y_col_actual if y_col_actual else y_metric,
        primary_team=primary_team,
        opponent=opponent,
        group_col=GROUP_BY_COLUMN,
    )
    return fig, resumen, prepared


BUILDERS = {
    "scatter": build_scatter,
    "bar": build_bar,
    "line": build_line,
    "box": build_box,
}


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    df = load_data(DATA_FILE)
    df = apply_filters(df)
    df = aggregate(df)

    builder = BUILDERS.get(CHART_TYPE.lower())
    if builder is None:
        raise ValueError(f"Unsupported chart type: {CHART_TYPE}")

    fig = builder(df)
    fig.show()


if __name__ == "__main__":
    main()