#!/usr/bin/env python3
"""
Convert All JSON Files to Excel
================================

Converts all JSON files from matches and matchstats folders to Excel format.
Creates both player and team stats Excel files with clean naming
(e.g. 20250819_Cibao_vs_Cavalier_player_stats.xlsx).

Usage: python convert_all_json_to_excel.py
"""

import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path
from typing import Optional, Tuple

BASE_PATH = Path("/Users/daniel/Documents/Smart Sports Lab/Football/Sports Data Campus/Cibao/concacaf_final_4_teams_data")
LINEUP_SUFFIX = "_lineup.xlsx"
TEAM_SUFFIX = "_team_stats.xlsx"
PLAYER_SUFFIX = "_player_stats.xlsx"
TEAM_CLEAN_SUFFIX = "_team_stats.xlsx"


def sanitize_name(name: str) -> str:
    """Convert team name to filesystem-friendly slug."""
    normalized = unicodedata.normalize("NFKD", name)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_text = ascii_text.replace("&", "and")
    ascii_text = ascii_text.replace("/", "-")
    ascii_text = ascii_text.replace(" ", "_")
    ascii_text = re.sub(r"[^A-Za-z0-9_-]+", "", ascii_text)
    ascii_text = re.sub(r"_+", "_", ascii_text)
    return ascii_text.strip("_-") or "Unknown"


def extract_match_details(json_file: Path) -> Tuple[str, str, str]:
    """Return (home_team, away_team, date_tag) from a match JSON file."""
    try:
        with json_file.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception as err:
        print(f"      Unable to read JSON for naming: {err}")
        return "Unknown", "Unknown", ""

    match_info = data.get("matchInfo", {})
    contestants = match_info.get("contestant", []) or []
    home = away = None
    for contestant in contestants:
        name = contestant.get("name") or contestant.get("shortName") or contestant.get("officialName")
        position = (contestant.get("position") or "").lower()
        if position == "home" and not home:
            home = name
        elif position == "away" and not away:
            away = name

    # Fallback order if positions missing
    if not home and contestants:
        home = contestants[0].get("name") or contestants[0].get("shortName") or "Unknown"
    if not away and len(contestants) > 1:
        away = contestants[1].get("name") or contestants[1].get("shortName") or "Unknown"

    local_date = match_info.get("localDate", "")
    sanitized_date = local_date.replace("-", "")
    return home or "Unknown", away or "Unknown", sanitized_date


def build_output_path(folder: Path, home: str, away: str, suffix: str, date_tag: str) -> Path:
    prefix = f"{date_tag}_" if date_tag else ""
    base_name = f"{prefix}{sanitize_name(home)}_vs_{sanitize_name(away)}{suffix}"
    candidate = folder / base_name
    if not candidate.exists():
        return candidate

    counter = 2
    while True:
        alt = folder / f"{prefix}{sanitize_name(home)}_vs_{sanitize_name(away)}_{counter}{suffix}"
        if not alt.exists():
            return alt
        counter += 1


def rename_export(json_file: Path, original_suffix: str, clean_suffix: str) -> Optional[Path]:
    source_file = json_file.with_name(json_file.stem + original_suffix)
    if not source_file.exists():
        print(f"      Expected output not found: {source_file.name}")
        return None

    home, away, date_tag = extract_match_details(json_file)
    target_path = build_output_path(json_file.parent, home, away, clean_suffix, date_tag)
    if target_path == source_file:
        return source_file

    source_file.rename(target_path)
    print(f"     Renamed to: {target_path.name}")
    return target_path


def remove_previous_exports(folder: Path):
    patterns = ["*_player_stats.xlsx", "*_team_stats.xlsx", "*_lineup.xlsx", "*_team_stats.xlsx"]
    for pattern in patterns:
        for file in folder.glob(pattern):
            try:
                file.unlink()
            except Exception:
                pass


def convert_all_files():
    """Convert all JSON files to Excel with clean filenames."""
    if not BASE_PATH.exists():
        raise SystemExit(f"Base path not found: {BASE_PATH}")

    lineup_script = BASE_PATH / "extract_lineup_to_excel.py"
    team_stats_script = BASE_PATH / "extract_team_stats_to_excel.py"

    folders = {
        "matchstats": BASE_PATH / "matchstats",
        "matches": BASE_PATH / "matches",
    }

    print(" CONVERTING ALL JSON FILES TO EXCEL")
    print("=" * 60)

    total_files = 0
    successful = 0
    errors = 0

    for folder_name, folder_path in folders.items():
        if not folder_path.exists():
            print(f"  Folder not found: {folder_path}")
            continue

        remove_previous_exports(folder_path)

        json_files = sorted(folder_path.glob("*.json"))
        print(f"\n Processing {folder_name}: {len(json_files)} files")
        print("-" * 60)

        for json_file in json_files:
            total_files += 1
            print(f"\n  Converting: {json_file.name}")

            try:
                result = subprocess.run(
                    [sys.executable, str(lineup_script), str(json_file)],
                    capture_output=True,
                    text=True,
                    cwd=str(BASE_PATH),
                )
                if result.returncode == 0:
                    renamed = rename_export(json_file, LINEUP_SUFFIX, PLAYER_SUFFIX)
                    if renamed:
                        print("     Player stats ready")
                else:
                    print(f"      Player stats warning: {result.stderr[:120]}")
            except Exception as exc:
                print(f"     Player stats error: {exc}")
                errors += 1

            try:
                result = subprocess.run(
                    [sys.executable, str(team_stats_script), str(json_file)],
                    capture_output=True,
                    text=True,
                    cwd=str(BASE_PATH),
                )
                if result.returncode == 0:
                    renamed = rename_export(json_file, TEAM_SUFFIX, TEAM_CLEAN_SUFFIX)
                    if renamed:
                        print("     Team stats ready")
                        successful += 1
                else:
                    print(f"      Team stats warning: {result.stderr[:120]}")
            except Exception as exc:
                print(f"     Team stats error: {exc}")
                errors += 1

    print("\n" + "=" * 60)
    print(" Conversion complete!")
    print(f"   JSON files processed: {total_files}")
    print(f"   Team stat workbooks created: {successful}")
    if errors:
        print(f"   Errors: {errors}")

    print("\n Clean exports saved in:")
    for folder_name, folder_path in folders.items():
        print(f"   - {folder_path}/*_player_stats.xlsx")
        print(f"   - {folder_path}/*_team_stats.xlsx")


if __name__ == "__main__":
    convert_all_files()
