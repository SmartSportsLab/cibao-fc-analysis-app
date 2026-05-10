# Scoresway Match Scraper

## Overview

This scraper uses Playwright to load Scoresway match pages and intercept the full match JSON data that Opta widgets load dynamically. It saves the JSON files to `data/raw/concacaf/matchstats/` for processing.

## Setup

1. **Install Playwright:**
   ```bash
   cd "/Users/daniel/Documents/Smart Sports Lab/Football/Sports Data Campus/Cibao/Cibao-fc-analytics"
   source .venv/bin/activate  # or activate your virtual environment
   python3 -m pip install playwright
   python3 -m playwright install chromium
   ```

2. **Verify installation:**
   ```bash
   python3 -c "from playwright.async_api import async_playwright; print('Playwright installed!')"
   ```

## Usage

### Scrape a single match:

```bash
# Using match ID
python3 src/data_processing/scrape_scoresway_match.py 2zhrn3wxg2ma02g2u2j5lotuc

# Using full URL
python3 src/data_processing/scrape_scoresway_match.py --url "https://www.scoresway.com/en_GB/soccer/concacaf-caribbean-cup-2025/bygi47fmsxgbzysjdf9u481lg/match/view/2zhrn3wxg2ma02g2u2j5lotuc"
```

### Scrape multiple matches:

Create a text file with one match ID per line:
```
2zhrn3wxg2ma02g2u2j5lotuc
2ks7mo0v65uuhvrs1px2dcnbo
e79xdwc30oj2yajnpg8mauqz8
```

Then run:
```bash
python3 src/data_processing/scrape_scoresway_match.py --list fixture_ids.txt
```

## Output

The scraper saves JSON files to:
- `data/raw/concacaf/matchstats/YYYYMMDD_HomeTeam_vs_AwayTeam.json`

The JSON structure matches the existing format with:
- `matchInfo` - Match metadata, teams, competition info
- `liveData` - Match details, goals, lineups, stats

## Next Steps

After scraping, use the existing converter to generate Excel files:

```bash
# From the concacaf_final_4_teams_data directory
python3 convert_all_json_to_excel.py
```

This will create:
- `*_player_stats.xlsx` - Player lineup data
- `*_team_stats.xlsx` - Team statistics (FH, SH, Total)

## Troubleshooting

1. **"Could not find match data"**
   - The page might take longer to load. The scraper waits up to 30 seconds.
   - Try running with a visible browser (modify `headless=True` to `headless=False` in the script)

2. **Playwright browser not found**
   - Run: `python3 -m playwright install chromium`

3. **Timeout errors**
   - Increase the timeout values in the script if your connection is slow

## Integration with Automation

This scraper can be integrated into the automation pipeline:
1. Fetch fixture list from Scoresway
2. Extract match IDs
3. Run this scraper for each match
4. Convert JSON to Excel using existing scripts
5. Update Streamlit dashboard

