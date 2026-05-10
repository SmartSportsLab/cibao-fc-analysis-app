#!/usr/bin/env python3
"""
Get Tournament ID for a Specific Competition
============================================

This script helps find the tournament calendar ID for a specific competition
by filtering competitions from Scoresway, similar to what the professor showed.

Usage:
    python3 get_tournament_id.py "Concacaf Caribbean Cup"
    python3 get_tournament_id.py --list  # List all available competitions
"""

import requests
import xml.etree.ElementTree as ET
import sys
import argparse
from typing import Optional, List, Dict

# Configuration
SDAPI_OUTLET_KEY = 'ft1tiv1inq7v1sk3y9tv12yh5'
COMPETITIONS_URL = f"https://api.performfeeds.com/soccerdata/competition/{SDAPI_OUTLET_KEY}/"


def fetch_competitions() -> List[Dict]:
    """
    Fetch all competitions from Scoresway API.
    
    Returns:
        List of dictionaries with competition information
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36',
        'Referer': 'https://www.scoresway.com/',
        'Origin': 'https://www.scoresway.com',
    }
    
    try:
        response = requests.get(COMPETITIONS_URL, headers=headers, timeout=30)
        if response.status_code == 200:
            return parse_competitions_xml(response.text)
        else:
            print(f" Failed to fetch competitions: HTTP {response.status_code}")
            return []
    except Exception as e:
        print(f" Error fetching competitions: {e}")
        return []


def parse_competitions_xml(xml_content: str) -> List[Dict]:
    """
    Parse the XML response to extract competition information.
    
    Args:
        xml_content: XML string from the API
        
    Returns:
        List of competition dictionaries
    """
    competitions = []
    try:
        root = ET.fromstring(xml_content)
        
        # Find all competition elements
        for comp_elem in root.findall('.//competition'):
            comp_info = comp_elem.find('competitionInfo')
            if comp_info is not None:
                comp_id = comp_info.get('id')
                name_elem = comp_info.find('name')
                known_name_elem = comp_info.find('knownName')
                
                # Get tournament calendar ID
                tournament_calendar = comp_info.find('tournamentCalendar')
                tournament_id = None
                if tournament_calendar is not None:
                    tournament_id = tournament_calendar.get('id')
                
                if comp_id:
                    competitions.append({
                        'id': comp_id,
                        'name': name_elem.text if name_elem is not None else 'Unknown',
                        'known_name': known_name_elem.text if known_name_elem is not None else 'Unknown',
                        'tournament_calendar_id': tournament_id,
                    })
    except ET.ParseError as e:
        print(f" Error parsing XML: {e}")
    except Exception as e:
        print(f" Error extracting competitions: {e}")
    
    return competitions


def find_tournament_id(competition_name: str) -> Optional[str]:
    """
    Find the tournament calendar ID for a specific competition.
    
    Args:
        competition_name: Name of the competition to search for
        
    Returns:
        Tournament calendar ID if found, None otherwise
    """
    print(f" Searching for competition: '{competition_name}'...")
    competitions = fetch_competitions()
    
    if not competitions:
        print(" No competitions found")
        return None
    
    # Search for matching competition (case-insensitive, partial match)
    competition_name_lower = competition_name.lower()
    matches = []
    
    for comp in competitions:
        comp_name = comp['name'].lower()
        comp_known_name = comp['known_name'].lower()
        
        if (competition_name_lower in comp_name or 
            competition_name_lower in comp_known_name or
            comp_name in competition_name_lower or
            comp_known_name in competition_name_lower):
            matches.append(comp)
    
    if not matches:
        print(f" No competition found matching '{competition_name}'")
        print(f"\nAvailable competitions (showing first 20):")
        for comp in competitions[:20]:
            print(f"   - {comp['name']} (ID: {comp['id']})")
        if len(competitions) > 20:
            print(f"   ... and {len(competitions) - 20} more")
        return None
    
    if len(matches) > 1:
        print(f"  Found {len(matches)} matches:")
        for i, match in enumerate(matches, 1):
            print(f"   {i}. {match['name']} (ID: {match['id']}, Tournament ID: {match['tournament_calendar_id']})")
        # Use the first match
        selected = matches[0]
        print(f"\n Using first match: {selected['name']}")
    else:
        selected = matches[0]
        print(f" Found: {selected['name']}")
    
    tournament_id = selected.get('tournament_calendar_id')
    if tournament_id:
        print(f" Tournament Calendar ID: {tournament_id}")
        return tournament_id
    else:
        print(f"  Competition found but no tournament calendar ID available")
        print(f"   Competition ID: {selected['id']}")
        return None


def list_all_competitions():
    """List all available competitions."""
    print(" Fetching all competitions from Scoresway...")
    competitions = fetch_competitions()
    
    if not competitions:
        print(" No competitions found")
        return
    
    print(f"\n Found {len(competitions)} competitions:\n")
    
    # Group by name for easier reading
    for comp in competitions:
        tournament_id = comp.get('tournament_calendar_id', 'N/A')
        print(f"   • {comp['name']}")
        print(f"     Competition ID: {comp['id']}")
        print(f"     Tournament Calendar ID: {tournament_id}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description='Find tournament calendar ID for a specific competition'
    )
    parser.add_argument(
        'competition_name',
        nargs='?',
        help='Name of the competition to search for (e.g., "Concacaf Caribbean Cup")'
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='List all available competitions'
    )
    
    args = parser.parse_args()
    
    if args.list:
        list_all_competitions()
    elif args.competition_name:
        tournament_id = find_tournament_id(args.competition_name)
        if tournament_id:
            print(f"\n Use this Tournament Calendar ID in your scripts:")
            print(f"   TOURNAMENT_CALENDAR_ID = '{tournament_id}'")
            sys.exit(0)
        else:
            sys.exit(1)
    else:
        parser.print_help()
        print("\n Example usage:")
        print("   python3 get_tournament_id.py 'Concacaf Caribbean Cup'")
        print("   python3 get_tournament_id.py --list")


if __name__ == "__main__":
    main()

