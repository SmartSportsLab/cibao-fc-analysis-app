# ==========================================================
#        DICCIONARIO COMPLETO Y ACTUALIZADO DE MÉTRICAS
#     (Incluye TODAS las columnas del dataset + TODAS las
#      que pediste + la faltante + sin duplicados)
# ==========================================================

METRICS_DICT = {

    # =========================
    #  INFORMACIÓN GENERAL
    # =========================
    "Fecha": "Date",
    "Jornada": "Jornada",
    "Partido": "Match",
    "Goles a favor": "Goles A Favor",
    "Goles en contra": "Goles En Contra",
    "Resultado final": "Final Result",
    "Competición": "competition",
    "Alineación": "Alineacion",
    "Porcentaje de alineación (%)": "% Alineacion",
    "Duración del partido": "duration",
    "Equipo": "Team",
    "Esquema táctico": "Scheme",

    # =========================
    #  RENDIMIENTO GENERAL
    # =========================
    "Goles por partido": "goals",
    "Goles en contra por partido": "conceded_goals",
    "xG (Goles esperados)": "xg",
    "Disparos por partido": "shots",
    "Disparos a puerta por partido": "shots_on_target",
    "Porcentaje de disparos a puerta (%)": "shots_on_target_percent",

    # =========================
    #  ATAQUE / EFICIENCIA
    # =========================
    "Disparos desde fuera del área": "shots_from_outside_penalty_area",
    "Disparos desde fuera del área a puerta": "shots_from_outside_penalty_area_on_target",
    "Disparos desde fuera del área a puerta (%)": "shots_from_outside_penalty_area_on_target_percent",

    "Ataques posicionales por 90": "positional_attacks",
    "Ataques posicionales con disparo (%)": "positional_attacks_with_shots_percent",

    "Contraataques por 90": "counter_attacks",
    "Contraataques con disparo (%)": "counter_attacks_with_shots_percent",

    "Balones parados por 90": "set_pieces",
    "Balones parados con disparo (%)": "set_pieces_with_shots_percent",

    "Corners por 90": "corners",
    "Corners con disparo (%)": "corners_with_shots_percent",

    "Faltas directas por 90": "free_kicks",
    "Faltas directas con disparo (%)": "free_kicks_with_shots_percent",

    "Penaltis por 90": "penalties",
    "Conversión de penaltis (%)": "penalties_converted_percent",

    "Entradas al área por 90": "penalty_area_entries",
    "Entradas al área con conducción": "penalty_area_entries_runs",
    "Entradas al área con centros": "penalty_area_entries_crosses",
    "Toques en el área por 90": "touches_in_penalty_area",

    "Centros por 90": "crosses",
    "Centros precisos": "crosses_accurate",
    "Precisión de centros (%)": "crosses_accurate_percent",

    "Centros profundos completados por 90": "deep_completed_crosses",
    "Pases profundos completados por 90": "deep_completed_passes",

    # =========================
    #  CONSTRUCCIÓN Y POSESIÓN
    # =========================
    "Posesión (%)": "possession_percent",

    "Pases totales por 90": "passes",
    "Pases precisos": "passes_accurate",
    "Precisión de pase (%)": "passes_accurate_percent",

    "Pases hacia adelante por 90": "forward_passes",
    "Precisión pases hacia adelante (%)": "forward_passes_accurate_percent",

    "Pases hacia atrás por 90": "back_passes",
    "Precisión pases hacia atrás (%)": "back_passes_accurate_percent",

    "Pases laterales por 90": "lateral_passes",
    "Precisión pases laterales (%)": "lateral_passes_accurate_percent",

    "Pases largos por 90": "long_passes",
    "Pases largos precisos": "long_passes_accurate",
    "Precisión pases largos (%)": "long_pass_percent",

    "Pases al último tercio por 90": "passes_to_final_third",
    "Precisión pases al último tercio (%)": "passes_to_final_third_accurate_percent",

    "Pases progresivos por 90": "progressive_passes",
    "Precisión pases progresivos (%)": "progressive_passes_accurate_percent",

    "Pases inteligentes por 90": "smart_passes",
    "Precisión pases inteligentes (%)": "smart_passes_accurate_percent",

    "Saques de banda por 90": "throw_ins",
    "Precisión saques de banda (%)": "throw_ins_accurate_percent",

    "Saques de meta por 90": "goal_kicks",

    "Promedio de pases por posesión": "average_passes_per_possession",
    "Longitud media de pase": "average_pass_length",

    # =========================
    #  DEFENSA Y PRESIÓN
    # =========================
    "Duelos defensivos por 90": "defensive_duels",
    "Duelos defensivos ganados (%)": "defensive_duels_won_percent",

    "Duelos aéreos por 90": "aerial_duels",
    "Duelos aéreos ganados (%)": "aerial_duels_won_percent",

    "Entradas por 90": "sliding_tackles",
    "Éxito en entradas (%)": "sliding_tackles_successful_percent",

    "Intercepciones por 90": "interceptions",
    "Despejes por 90": "clearances",

    "Presión alta (estimada)": "losses_high",
    "Presión media (estimada)": "losses_medium",
    "Presión baja (estimada)": "losses_low",

    "Intensidad de presión (PPDA)": "ppda",

    # =========================
    #  DUELOS Y FÍSICO
    # =========================
    "Duelos totales por 90": "duels",
    "Duelos ganados (%)": "duels_won_percent",

    "Duelos ofensivos por 90": "offensive_duels",
    "Duelos ofensivos ganados (%)": "offensive_duels_won_percent",

    "Recuperaciones por 90": "recoveries",
    "Recuperaciones altas por 90": "recoveries_high",
    "Recuperaciones medias por 90": "recoveries_medium",
    "Recuperaciones bajas por 90": "recoveries_low",

    "Pérdidas de balón por 90": "losses",

    # =========================
    #  DISCIPLINA
    # =========================
    "Faltas cometidas por 90": "fouls",
    "Tarjetas amarillas por 90": "yellow_cards",
    "Tarjetas rojas por 90": "red_cards",
    "Offsides por 90": "offsides",

    # =========================
    #  EFICIENCIA DEFENSIVA
    # =========================
    "Disparos en contra por 90": "shots_against",
    "Disparos en contra a puerta": "shots_against_on_target",
    "Eficiencia rival (tiros a puerta %)": "shots_against_on_target_percent",

    "Promedio de ritmo de partido": "match_tempo",
    "Distancia media de disparo": "average_shot_distance",
}
