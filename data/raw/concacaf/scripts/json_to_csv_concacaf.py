import os, json, pandas as pd

INPUT_DIR =  "../matchstats"
OUTPUT_FILE = "concacaf_matchstats_consolidado.csv"

def flatten_player_stats(json_path):
    """Extrae estadísticas de cada jugador de un archivo JSON."""
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    match = data["matchInfo"]
    lineups = data["liveData"].get("lineUp", [])

    rows = []
    for team in lineups:
        team_name = next(
            (c["name"] for c in match["contestant"] if c["id"] == team["contestantId"]),
            "Unknown"
        )
        for player in team.get("player", []):
            player_row = {
                "match_id": match["id"],
                "match_date": match.get("localDate"),
                "competition": match["competition"]["name"],
                "stage": match["stage"]["name"],
                "home_team": match["contestant"][0]["name"],
                "away_team": match["contestant"][1]["name"],
                "team": team_name,
                "player_id": player["playerId"],
                "player_name": player.get("matchName"),
                "position": player.get("position"),
                "side": player.get("positionSide"),
                "shirt_number": player.get("shirtNumber"),
                "formation_place": player.get("formationPlace"),
            }
            # Aplanar estadísticas del jugador
            for s in player.get("stat", []):
                player_row[s["type"]] = s["value"]
            rows.append(player_row)

    return pd.DataFrame(rows)


def main():
    dfs = []
    for f in os.listdir(INPUT_DIR):
        if f.endswith(".json"):
            path = os.path.join(INPUT_DIR, f)
            print("Procesando:", f)
            try:
                dfs.append(flatten_player_stats(path))
            except Exception as e:
                print(f" Error en {f}: {e}")

    if dfs:
        df = pd.concat(dfs, ignore_index=True)
        df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
        print(f"\n CSV generado: {OUTPUT_FILE}")
        print(f"Total filas: {len(df)}")
    else:
        print("No se encontraron archivos válidos.")


if __name__ == "__main__":
    main()
