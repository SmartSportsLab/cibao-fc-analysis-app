# =========================================================
#  METRICS DICTIONARY — CONCACAF COPA CIBAO FC
# =========================================================
# Mapeo de nombres de métricas en español (para visualizaciones)
# hacia las columnas reales del dataset de Concacaf Matchstats.
# =========================================================

METRICS_CONCACAF = {

    # =========================
    #  ATAQUE
    # =========================
    "Goles": "goals",
    "Asistencias de Gol": "goalAssist",
    "Disparos Totales": "totalScoringAtt",
    "Disparos al Arco": "ontargetScoringAtt",
    "Disparos Fuera del Arco": "shotOffTarget",
    "Disparos Bloqueados": "blockedScoringAtt",
    "Intentos de Gol": "totalScoringAtt",
    "Faltas a Favor": "wasFouled",
    "Fuera de Juego": "totalOffside",

    # =========================
    #  CONSTRUCCIÓN Y POSESIÓN
    # =========================
    "Total de Pases": "totalPass",
    "Pases Precisos": "accuratePass",
    "Posesión (aprox.)": "totalPass",  # no hay campo de posesión explícito
    "Saques de Banda": "totalThrows",
    "Saques de Meta": "goalKicks",

    # =========================
    #  DEFENSA
    # =========================
    "Entradas Totales": "totalTackle",
    "Entradas Ganadas": "wonTackle",
    "Despejes": "totalClearance",
    "Atajadas": "saves",
    "Valla Invicta": "cleanSheet",
    "Goles Recibidos": "goalsConceded",
    "Faltas Cometidas": "fouls",

    # =========================
    #  JUEGO A BALÓN PARADO (SET PIECES)
    # =========================
    "Saques de Esquina Ganados": "wonCorners",
    "Saques de Esquina Perdidos": "lostCorners",
    "Saques de Esquina Ejecutados": "cornerTaken",

    # =========================
    #  DISCIPLINA Y GENERAL
    # =========================
    "Tarjetas Amarillas": "yellowCard",
    "Tarjetas Rojas": "redCard",
    "Sustituciones Hechas": "totalSubOff",
    "Sustituciones Recibidas": "totalSubOn",
    "Minutos Jugados": "minsPlayed",
    "Formación": "formation_place",
}

# =========================================================
#  AGRUPACIÓN DE MÉTRICAS POR CATEGORÍA
# =========================================================
METRIC_GROUPS_CONCACAF = {
    "Ataque": [
        "Goles",
        "Asistencias de Gol",
        "Disparos Totales",
        "Disparos al Arco",
        "Disparos Fuera del Arco",
        "Disparos Bloqueados",
        "Intentos de Gol",
        "Faltas a Favor",
        "Fuera de Juego",
    ],
    "Pases": [
        "Total de Pases",
        "Pases Precisos",
        "Posesión (aprox.)",
    ],
    "Defensivo": [
        "Entradas Totales",
        "Entradas Ganadas",
        "Despejes",
        "Atajadas",
        "Valla Invicta",
        "Goles Recibidos",
        "Faltas Cometidas",
    ],
    "Set Pieces": [
        "Saques de Meta",
        "Saques de Banda",
        "Saques de Esquina Ganados",
        "Saques de Esquina Perdidos",
        "Saques de Esquina Ejecutados",
    ],
    "General": [
        "Minutos Jugados",
        "Formación",
        "Sustituciones Hechas",
        "Sustituciones Recibidas",
        "Tarjetas Amarillas",
        "Tarjetas Rojas",
    ],
}
