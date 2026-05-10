#!/usr/bin/env python3
"""
Automated Concacaf Caribbean Cup Match Scraper
===============================================

This script automatically discovers and scrapes all matches from the Concacaf Caribbean Cup.
It:
1. Fetches the list of all matches from PerformFeeds API
2. Compares with already scraped matches
3. Scrapes only new matches
4. Can be run on a schedule (cron/launchd) for full automation

Usage:
    python3 scrape_all_concacaf_matches.py [--force] [--dry-run]
"""

import asyncio
import json
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Set, Optional
import argparse

# Add parent directory to path to import scrape_scoresway_match
sys.path.insert(0, str(Path(__file__).parent))
from scrape_scoresway_match import scrape_match

# Configuration
SDAPI_OUTLET_KEY = 'ft1tiv1inq7v1sk3y9tv12yh5'
# Tournament Calendar ID for Concacaf Caribbean Cup
# You can find this by running: python3 get_tournament_id.py "Concacaf Caribbean Cup"
TOURNAMENT_CALENDAR_ID = 'bygi47fmsxgbzysjdf9u481lg'
DATA_DIR = Path(__file__).parent.parent.parent / 'data' / 'raw' / 'concacaf' / 'matchstats'
# Note: _pgSz=400 is the page size parameter (discovered from Scoresway website)
# Without it, API returns only 20 matches. With it, returns all matches including August!
MATCHES_LIST_URL = f"https://api.performfeeds.com/soccerdata/match/{SDAPI_OUTLET_KEY}/?_rt=c&tmcl={TOURNAMENT_CALENDAR_ID}&_pgSz=400"


def get_tournament_id_for_competition(competition_name: str = "Concacaf Caribbean Cup") -> Optional[str]:
    """
    Dynamically find the tournament calendar ID for a competition.
    This allows filtering competitions like the professor showed.
    
    Args:
        competition_name: Name of the competition to search for
        
    Returns:
        Tournament calendar ID if found, None otherwise
    """
    import requests
    import xml.etree.ElementTree as ET
    
    COMPETITIONS_URL = f"https://api.performfeeds.com/soccerdata/competition/{SDAPI_OUTLET_KEY}/"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36',
        'Referer': 'https://www.scoresway.com/',
        'Origin': 'https://www.scoresway.com',
    }
    
    try:
        response = requests.get(COMPETITIONS_URL, headers=headers, timeout=30)
        if response.status_code != 200:
            return None
        
        root = ET.fromstring(response.text)
        competition_name_lower = competition_name.lower()
        
        # Search for matching competition
        for comp_elem in root.findall('.//competition'):
            comp_info = comp_elem.find('competitionInfo')
            if comp_info is not None:
                name_elem = comp_info.find('name')
                known_name_elem = comp_info.find('knownName')
                
                comp_name = (name_elem.text if name_elem is not None else '').lower()
                comp_known_name = (known_name_elem.text if known_name_elem is not None else '').lower()
                
                # Check if this competition matches
                if (competition_name_lower in comp_name or 
                    competition_name_lower in comp_known_name or
                    comp_name in competition_name_lower or
                    comp_known_name in competition_name_lower):
                    
                    # Get tournament calendar ID
                    tournament_calendar = comp_info.find('tournamentCalendar')
                    if tournament_calendar is not None:
                        tournament_id = tournament_calendar.get('id')
                        if tournament_id:
                            print(f" Found tournament ID for '{competition_name}': {tournament_id}")
                            return tournament_id
        
        return None
    except Exception as e:
        print(f"  Error fetching tournament ID: {e}")
        return None


def get_scraped_match_ids() -> Set[str]:
    """Get set of already scraped match IDs from existing JSON files."""
    scraped_ids = set()
    if DATA_DIR.exists():
        for json_file in DATA_DIR.glob('*.json'):
            # Extract match ID from filename (format: YYYYMMDD_Team1_vs_Team2.json)
            # Or try to read the JSON and get matchInfo.id
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if 'matchInfo' in data and 'id' in data['matchInfo']:
                        scraped_ids.add(data['matchInfo']['id'])
            except:
                # If we can't read it, try to extract from filename
                # Some files have match ID in filename: {match_id}_date_team_team.json
                filename = json_file.stem
                # Try to extract match ID if it's at the start of filename
                parts = filename.split('_')
                if len(parts) > 0 and len(parts[0]) > 10:  # Match IDs are usually long alphanumeric strings
                    potential_id = parts[0]
                    if len(potential_id) >= 20:  # Match IDs are typically 20+ characters
                        scraped_ids.add(potential_id)
    return scraped_ids


def parse_matches_xml(xml_content: str) -> List[Dict]:
    """Parse the XML response to extract match information."""
    from datetime import datetime
    
    matches = []
    try:
        root = ET.fromstring(xml_content)
        today = datetime.now().date()
        
        # Find all match elements
        for match_elem in root.findall('.//match'):
            match_info = match_elem.find('matchInfo')
            if match_info is not None:
                match_id = match_info.get('id')
                description = match_info.find('description')
                date_elem = match_info.get('date', '')
                
                # Check if match date is in the past
                match_date_past = False
                match_date_obj = None
                if date_elem:
                    try:
                        # Parse date (format: YYYY-MM-DDZ or similar)
                        date_str = date_elem.replace('Z', '').split('T')[0]
                        match_date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                        match_date_past = match_date_obj < today
                    except:
                        pass
                
                # Check for actual match data (goals, cards, substitutes, etc.)
                # Future fixtures have matchDetails structure but no actual data
                live_data = match_elem.find('liveData')
                has_actual_data = False
                
                if live_data is not None:
                    # Check for actual match events/data
                    has_goals = live_data.find('.//goal') is not None
                    has_cards = live_data.find('.//card') is not None
                    has_subs = live_data.find('.//substitute') is not None
                    has_var = live_data.find('.//VAR') is not None
                    has_extra = live_data.find('.//matchDetailsExtra') is not None
                    
                    # Check matchDetails for score
                    match_details = live_data.find('matchDetails')
                    has_score = False
                    if match_details is not None:
                        score_elem = match_details.find('.//score')
                        if score_elem is not None:
                            # Check if score has actual values (not just empty structure)
                            home_score = score_elem.get('home', '')
                            away_score = score_elem.get('away', '')
                            if home_score or away_score:
                                has_score = True
                    
                    has_actual_data = has_goals or has_cards or has_subs or has_var or has_extra or has_score
                
                # Match is considered played if:
                # 1. Date is in the past AND has actual match data, OR
                # 2. Has actual match data (goals, cards, etc.) regardless of date
                is_played = (match_date_past and has_actual_data) or has_actual_data
                
                if match_id:
                    matches.append({
                        'id': match_id,
                        'description': description.text if description is not None else 'Unknown',
                        'date': date_elem,
                        'status': is_played,
                        'date_past': match_date_past,
                        'has_actual_data': has_actual_data
                    })
    except ET.ParseError as e:
        print(f" Error parsing XML: {e}")
    except Exception as e:
        print(f" Error extracting matches: {e}")
    
    return matches


def fetch_all_matches() -> List[Dict]:
    """Fetch the list of all matches from PerformFeeds API."""
    import requests
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36',
        'Referer': 'https://www.scoresway.com/',
        'Origin': 'https://www.scoresway.com',
    }
    
    try:
        response = requests.get(MATCHES_LIST_URL, headers=headers, timeout=30)
        if response.status_code == 200:
            matches = parse_matches_xml(response.text)
            return matches
        else:
            print(f" Failed to fetch matches list: HTTP {response.status_code}")
            return []
    except Exception as e:
        print(f" Error fetching matches: {e}")
        return []


async def scrape_new_matches(force: bool = False, dry_run: bool = False, competition_name: str = "Concacaf Caribbean Cup"):
    """Main function to discover and scrape new matches."""
    print(" Automated Match Scraper")
    print("=" * 60)
    
    # Optionally get tournament ID dynamically (like professor showed)
    # This allows filtering competitions dynamically
    global TOURNAMENT_CALENDAR_ID, MATCHES_LIST_URL
    dynamic_tournament_id = get_tournament_id_for_competition(competition_name)
    if dynamic_tournament_id:
        TOURNAMENT_CALENDAR_ID = dynamic_tournament_id
        # Note: _pgSz=400 is the page size parameter (discovered from Scoresway website)
        # Without it, API returns only 20 matches. With it, returns all matches including August!
        MATCHES_LIST_URL = f"https://api.performfeeds.com/soccerdata/match/{SDAPI_OUTLET_KEY}/?_rt=c&tmcl={TOURNAMENT_CALENDAR_ID}&_pgSz=400"
        print(f" Using Tournament ID: {TOURNAMENT_CALENDAR_ID}")
    else:
        print(f" Using configured Tournament ID: {TOURNAMENT_CALENDAR_ID}")
        print(f"   (Competition: {competition_name})")
    
    print("=" * 60)
    
    # Ensure data directory exists
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Get already scraped match IDs
    scraped_ids = get_scraped_match_ids()
    print(f" Already scraped: {len(scraped_ids)} matches")
    
    # Fetch all matches from API
    print(f" Fetching all matches from PerformFeeds API...")
    print(f"    Using _pgSz=400 parameter to get all matches (including August)")
    all_matches = fetch_all_matches()
    
    if not all_matches:
        print(" No matches found or failed to fetch")
        return
    
    print(f" Found {len(all_matches)} matches from API list endpoint")
    
    # Note: The API list endpoint is limited, but individual matches (including August ones)
    # are accessible via direct calls. We rely on existing scraped files for historical matches.
    
    # Filter for played matches only (exclude future fixtures)
    played_matches = [m for m in all_matches if m.get('status', False)]
    fixtures = [m for m in all_matches if not m.get('status', False)]
    
    print(f" Match breakdown:")
    print(f"    Played matches: {len(played_matches)}")
    print(f"    Future fixtures: {len(fixtures)}")
    
    if fixtures:
        print(f"\n   ⏭  Skipping fixtures (not yet played):")
        for fixture in fixtures[:5]:
            print(f"      - {fixture['description']} ({fixture['date']})")
        if len(fixtures) > 5:
            print(f"      ... and {len(fixtures) - 5} more")
    
    # Filter for new matches (only from played matches)
    if force:
        new_matches = played_matches
        print(f"\n Force mode: will scrape all {len(new_matches)} played matches")
    else:
        new_matches = [m for m in played_matches if m['id'] not in scraped_ids]
        print(f"\n🆕 New played matches to scrape: {len(new_matches)}")
    
    if not new_matches:
        print(" All matches already scraped!")
        return
    
    if dry_run:
        print("\n DRY RUN - Would scrape these matches:")
        for match in new_matches[:10]:  # Show first 10
            print(f"   - {match['id']}: {match['description']} ({match['date']})")
        if len(new_matches) > 10:
            print(f"   ... and {len(new_matches) - 10} more")
        return
    
    # Scrape new matches
    print(f"\n Scraping {len(new_matches)} new matches...")
    success_count = 0
    fail_count = 0
    
    for i, match in enumerate(new_matches, 1):
        match_id = match['id']
        description = match['description']
        print(f"\n[{i}/{len(new_matches)}] {description} ({match_id})")
        
        try:
            result = await scrape_match(match_id)
            if result:
                success_count += 1
                print(f"    Success")
            else:
                fail_count += 1
                print(f"    Failed")
        except Exception as e:
            fail_count += 1
            print(f"    Error: {e}")
        
        # Small delay between requests
        await asyncio.sleep(1)
    
    print("\n" + "=" * 60)
    print(f" Scraping complete!")
    print(f"   Success: {success_count}")
    print(f"   Failed: {fail_count}")
    print(f"   Total scraped (this run): {success_count}")
    print(f"   Total matches in database: {len(scraped_ids) + success_count}")


def main():
    parser = argparse.ArgumentParser(
        description='Automatically discover and scrape Concacaf Caribbean Cup matches'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Scrape all matches, even if already scraped'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be scraped without actually scraping'
    )
    parser.add_argument(
        '--competition',
        type=str,
        default='Concacaf Caribbean Cup',
        help='Name of the competition to scrape (default: "Concacaf Caribbean Cup")'
    )
    
    args = parser.parse_args()
    
    asyncio.run(scrape_new_matches(force=args.force, dry_run=args.dry_run, competition_name=args.competition))


if __name__ == "__main__":
    main()

