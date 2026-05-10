import os, json, pandas as pd

INPUT_DIR = "../matches"
OUTPUT_FILE = "concacaf_matches_consolidado.csv"

def flatten_match_events(json_path):
    """Extrae eventos de partido desde JSONs de la carpeta matches."""
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    match = data.get("matchInfo", {})
    events = data.get("liveData", {}).get("event", [])
    
    rows = []
    for e in events:
        row = {
            "match_id": match.get("id"),
            "match_date": match.get("localDate"),
            "competition": match.get("competition", {}).get("name"),
            "stage": match.get("stage", {}).get("name"),
            "home_team": match.get("contestant", [{}])[0].get("name"),
            "away_team": match.get("contestant", [{}])[1].get("name"),
            "venue": match.get("venue", {}).get("longName"),
            "event_id": e.get("id"),
            "typeId": e.get("typeId"),
            "periodId": e.get("periodId"),
            "timeMin": e.get("timeMin"),
            "timeSec": e.get("timeSec"),
            "playerName": e.get("playerName"),
            "contestantId": e.get("contestantId"),
            "outcome": e.get("outcome"),
            "x": e.get("x"),
            "y": e.get("y"),
        }

        # Aplanar qualifiers si existen
        if "qualifier" in e:
            for q in e["qualifier"]:
                row[f"qual_{q['qualifierId']}"] = q.get("value")

        rows.append(row)
    return pd.DataFrame(rows)


def main():
    all_dfs = []
    for f in os.listdir(INPUT_DIR):
        if f.endswith(".json"):
            path = os.path.join(INPUT_DIR, f)
            print(f"Procesando: {f}")
            try:
                df = flatten_match_events(path)
                all_dfs.append(df)
            except Exception as e:
                print(f" Error procesando {f}: {e}")

    if all_dfs:
        final_df = pd.concat(all_dfs, ignore_index=True)
        final_df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
        print(f"\n CSV generado: {OUTPUT_FILE}")
        print(f"Total filas: {len(final_df)}")
    else:
        print(" No se encontraron archivos válidos.")


if __name__ == "__main__":
    main()
