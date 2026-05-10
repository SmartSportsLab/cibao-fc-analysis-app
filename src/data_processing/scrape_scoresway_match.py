#!/usr/bin/env python3
"""
Scoresway Match Scraper
========================

Uses Playwright to load Scoresway match pages and intercept the full match JSON
data that Opta widgets load. Saves the JSON to the raw data directory.

Usage:
    python scrape_scoresway_match.py <match_url_or_id>
    python scrape_scoresway_match.py --list <fixture_ids_file.txt>
    python scrape_scoresway_match.py --url "https://scoresway.com/.../match/view/2zhrn3wxg2ma02g2u2j5lotuc"
"""

import asyncio
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, Dict, Any
from playwright.async_api import async_playwright, Page, Response

# Paths
REPO_ROOT = Path(__file__).parent.parent.parent
RAW_DATA_DIR = REPO_ROOT / "data" / "raw" / "concacaf"
MATCHSTATS_DIR = RAW_DATA_DIR / "matchstats"
MATCHES_DIR = RAW_DATA_DIR / "matches"

# Ensure directories exist
MATCHSTATS_DIR.mkdir(parents=True, exist_ok=True)
MATCHES_DIR.mkdir(parents=True, exist_ok=True)


def extract_match_id(url_or_id: str) -> Optional[str]:
    """Extract match ID from URL or return if already an ID."""
    # If it's already just an ID (alphanumeric string)
    if re.match(r'^[a-z0-9]+$', url_or_id):
        return url_or_id
    
    # Extract from URL
    match = re.search(r'/match/view/([a-z0-9]+)', url_or_id)
    if match:
        return match.group(1)
    
    return None


def build_match_url(match_id: str, base_url: str = "https://www.scoresway.com") -> str:
    """Build Scoresway match URL from match ID."""
    # Default to Concacaf Caribbean Cup 2025
    return f"{base_url}/en_GB/soccer/concacaf-caribbean-cup-2025/bygi47fmsxgbzysjdf9u481lg/match/view/{match_id}"


def find_match_data_in_responses(captured_responses: list, match_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Search through captured responses to find match data."""
    for url, data in captured_responses:
        if isinstance(data, dict):
            # Check for XML structure (from PerformFeeds)
            if 'matches' in data and isinstance(data['matches'], dict):
                matches = data['matches']
                # Find match by ID if provided, otherwise take first
                if 'match' in matches:
                    match_list = matches['match']
                    if not isinstance(match_list, list):
                        match_list = [match_list]
                    
                    for match in match_list:
                        if isinstance(match, dict):
                            # Extract matchInfo and liveData
                            match_info = match.get('matchInfo', {})
                            live_data = match.get('liveData', {})
                            
                            if match_info or live_data:
                                # Check if this is the right match
                                if match_id:
                                    match_info_id = match_info.get('id', '')
                                    if match_id in match_info_id or match_info_id in match_id:
                                        result = {'matchInfo': match_info, 'liveData': live_data}
                                        print(f"     Found match data in XML: {url[:100]}...")
                                        return result
                                else:
                                    # No match ID specified, return first match
                                    result = {'matchInfo': match_info, 'liveData': live_data}
                                    print(f"     Found match data in XML: {url[:100]}...")
                                    return result
            
            # Direct check for JSON structure
            if 'matchInfo' in data or 'liveData' in data:
                print(f"     Found match data in: {url[:100]}...")
                return data
            
            # Recursive check
            def has_match_structure(obj, depth=0):
                if depth > 3:
                    return False
                if isinstance(obj, dict):
                    if 'matchInfo' in obj or 'liveData' in obj:
                        return True
                    return any(has_match_structure(v, depth+1) for v in obj.values() if isinstance(v, (dict, list)))
                if isinstance(obj, list):
                    return any(has_match_structure(v, depth+1) for v in obj if isinstance(v, (dict, list)))
                return False
            
            if has_match_structure(data):
                print(f"     Found match data in captured response: {url[:100]}...")
                return data
    
    return None


async def scrape_match(match_id: str, output_dir: Path = MATCHSTATS_DIR, headless: bool = True) -> bool:
    """Scrape a single match and save the JSON."""
    match_url = build_match_url(match_id)
    
    print(f"\n Scraping match: {match_id}")
    print(f"   URL: {match_url}")
    
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36'
        )
        page = await context.new_page()
        
        try:
            # Set up response handler BEFORE navigation
            captured_responses = []
            response_tasks = []
            
            response_count = 0
            
            async def handle_response(response: Response):
                nonlocal response_count
                response_count += 1
                url = response.url
                content_type = response.headers.get('content-type', '')
                
                # Log first 20 responses to see what's happening
                if response_count <= 20:
                    print(f"     Response #{response_count}: {url[:80]}... (type: {content_type[:20]})")
                
                # Always log PerformFeeds requests
                if 'performfeeds.com' in url:
                    print(f"     PerformFeeds request detected: {url[:100]}...")
                
                # Log relevant responses for debugging
                if any(domain in url for domain in ['opta', 'statsperform', 'widgets', 'ngdata', 'performfeeds']):
                    print(f"     Relevant Response: {url[:100]}... (type: {content_type[:30]})")
                
                # Capture JSON responses from Opta/StatsPerform
                if any(domain in url for domain in ['opta', 'statsperform', 'widgets', 'ngdata']):
                    if 'application/json' in content_type or 'text/json' in content_type or url.endswith('.json'):
                        try:
                            # Wait for response to be ready
                            await response.finished()
                            body = await response.body()
                            if body and len(body) > 100:
                                data = json.loads(body)
                                captured_responses.append((url, data))
                                print(f"     Captured JSON: {url[:80]}... ({len(body)} bytes)")
                        except Exception as e:
                            if response_count <= 5:  # Only log first few errors
                                print(f"      Error reading response: {e}")
                
                # Capture XML responses from PerformFeeds (the actual match data!)
                if 'performfeeds.com' in url and '/soccerdata/match/' in url:
                    try:
                        await response.finished()
                        body = await response.body()
                        if body and len(body) > 1000:  # Match data should be substantial
                            # Check if it's XML (starts with < or has xml content-type)
                            body_start = body[:100].decode('utf-8', errors='ignore')
                            is_xml = ('xml' in content_type or 
                                     'text/xml' in content_type or 
                                     url.endswith('.xml') or
                                     body_start.strip().startswith('<'))
                            
                            if is_xml:
                                # Parse XML and convert to dict
                                xml_str = body.decode('utf-8')
                                root = ET.fromstring(xml_str)
                                
                                # Convert XML to dict (simple approach)
                                def xml_to_dict(element):
                                    result = {}
                                    if element.text and element.text.strip():
                                        result['_text'] = element.text.strip()
                                    
                                    # Add attributes
                                    if element.attrib:
                                        result.update(element.attrib)
                                    
                                    # Process children
                                    children = {}
                                    for child in element:
                                        child_dict = xml_to_dict(child)
                                        child_tag = child.tag
                                        
                                        # Handle multiple children with same tag
                                        if child_tag in children:
                                            if not isinstance(children[child_tag], list):
                                                children[child_tag] = [children[child_tag]]
                                            children[child_tag].append(child_dict)
                                        else:
                                            children[child_tag] = child_dict
                                    
                                    if children:
                                        result.update(children)
                                    
                                    return result
                                
                                data = xml_to_dict(root)
                                captured_responses.append((url, data))
                                print(f"     Captured XML: {url[:80]}... ({len(body)} bytes)")
                            else:
                                # Might be JSON, try that
                                try:
                                    data = json.loads(body)
                                    captured_responses.append((url, data))
                                    print(f"     Captured JSON from PerformFeeds: {url[:80]}... ({len(body)} bytes)")
                                except:
                                    pass
                    except Exception as e:
                        print(f"      Error parsing PerformFeeds response: {e}")
            
            # Set up response handler (BEFORE navigation)
            page.on('response', lambda r: response_tasks.append(asyncio.create_task(handle_response(r))))
            
            # Navigate to match page
            print(f"     Loading page...")
            await page.goto(match_url, wait_until='domcontentloaded', timeout=30000)
            
            # Wait for page to load
            print(f"    ⏳ Waiting for page to load...")
            try:
                await page.wait_for_load_state('networkidle', timeout=30000)
                await asyncio.sleep(5)
            except Exception as e:
                print(f"      Timeout waiting for page load: {e}")
            
            # Try clicking "Match Stats" tab to trigger data loading
            print(f"     Clicking 'Match Stats' tab to trigger data load...")
            try:
                # Look for the match-stats link
                match_stats_link = await page.query_selector('a[href*="match-stats"]')
                if match_stats_link:
                    await match_stats_link.click()
                    await asyncio.sleep(5)  # Wait for data to load
                    print(f"     Clicked Match Stats tab")
                else:
                    print(f"      Could not find Match Stats tab")
            except Exception as e:
                print(f"      Could not click tab: {e}")
            
            # Wait for all async handlers to complete
            print(f"    ⏳ Waiting for response handlers to complete...")
            if response_tasks:
                await asyncio.gather(*response_tasks, return_exceptions=True)
            await asyncio.sleep(3)
            
            print(f"     Found {len(captured_responses)} potential responses to check...")
            
            # Search for match data in captured responses
            match_data = find_match_data_in_responses(captured_responses, match_id)
            
            if not match_data:
                print(f"     Could not find match data via interception. Trying alternative methods...")
                
                # Alternative 1: Try to extract from page JavaScript context
                try:
                    print(f"     Method 1: Checking page JavaScript context...")
                    
                    # Wait a bit more for widgets to load
                    await asyncio.sleep(8)
                    
                    page_data = await page.evaluate("""
                        () => {
                            // Look for embedded JSON in script tags
                            const scripts = Array.from(document.querySelectorAll('script[type="application/json"]'));
                            for (const script of scripts) {
                                try {
                                    const data = JSON.parse(script.textContent);
                                    if (data.matchInfo || data.liveData) {
                                        return data;
                                    }
                                } catch (e) {}
                            }
                            
                            // Look in window object (common patterns)
                            if (window.matchData) return window.matchData;
                            if (window.optaData) return window.optaData;
                            if (window.matchJSON) return window.matchJSON;
                            if (window.__INITIAL_STATE__) {
                                const state = window.__INITIAL_STATE__;
                                if (state.match && (state.match.matchInfo || state.match.liveData)) {
                                    return state.match;
                                }
                            }
                            
                            // Try to find data in Opta widget instances
                            if (window.Opta && window.Opta.widgets) {
                                for (let widget of Object.values(window.Opta.widgets)) {
                                    if (widget.data && (widget.data.matchInfo || widget.data.liveData)) {
                                        return widget.data;
                                    }
                                }
                            }
                            
                            // Try to access via Opta API if available
                            if (window.Opta && window.Opta.api) {
                                try {
                                    const widgets = document.querySelectorAll('opta-widget');
                                    for (let widget of widgets) {
                                        if (widget._optaWidget && widget._optaWidget.data) {
                                            const data = widget._optaWidget.data;
                                            if (data.matchInfo || data.liveData) {
                                                return data;
                                            }
                                        }
                                    }
                                } catch (e) {}
                            }
                            
                            // Try to find in all script tags (look for JSON.parse or data assignments)
                            const allScripts = Array.from(document.querySelectorAll('script'));
                            for (const script of allScripts) {
                                const content = script.textContent || script.innerHTML;
                                // Look for patterns like: var matchData = {...} or matchData = {...}
                                const matchPatterns = [
                                    /(?:var|let|const)\\s+matchData\\s*=\\s*({[\\s\\S]*?matchInfo[\\s\\S]*?});/,
                                    /matchData\\s*=\\s*({[\\s\\S]*?matchInfo[\\s\\S]*?});/,
                                    /window\\.matchData\\s*=\\s*({[\\s\\S]*?matchInfo[\\s\\S]*?});/,
                                ];
                                for (const pattern of matchPatterns) {
                                    const match = content.match(pattern);
                                    if (match) {
                                        try {
                                            const data = JSON.parse(match[1]);
                                            if (data.matchInfo || data.liveData) {
                                                return data;
                                            }
                                        } catch (e) {}
                                    }
                                }
                            }
                            
                            return null;
                        }
                    """)
                    
                    if page_data:
                        match_data = page_data
                        print(f"     Found match data in page context")
                    else:
                        print(f"      Could not find data in page context")
                        
                except Exception as e:
                    print(f"      Method 1 failed: {e}")
                
                # Alternative 2: Try to trigger widget data loading by clicking tabs
                if not match_data:
                    try:
                        print(f"     Method 2: Trying to trigger data loading...")
                        # Try clicking the "Match Stats" tab to trigger data load
                        try:
                            await page.click('a[href*="match-stats"]', timeout=5000)
                            await asyncio.sleep(3)
                            # Check responses again
                            if response_tasks:
                                await asyncio.gather(*response_tasks, return_exceptions=True)
                            match_data = find_match_data_in_responses(captured_responses, match_id)
                            if match_data:
                                print(f"     Found match data after clicking tab")
                        except:
                            pass
                    except Exception as e:
                        print(f"      Method 2 failed: {e}")
                
                # Alternative 3: Try direct API calls based on known patterns
                if not match_data:
                    try:
                        print(f"     Method 3: Trying direct API calls...")
                        
                        # Try known Opta API patterns. The widgets-api key is read
                        # from the env var STATSPERFORM_WIDGETS_API_KEY so it isn't
                        # hardcoded in a public showcase repo.
                        api_base = "https://widgets-api.ngdata.statsperform.com/widgets"
                        api_key = os.environ.get("STATSPERFORM_WIDGETS_API_KEY", "")
                        
                        # Try different endpoint patterns with fixtureUUID
                        endpoints_to_try = [
                            f"{api_base}/excitementIndexEvents/?fixtureUUID={match_id}&cnt=2000",  # User found this one
                            f"{api_base}/matchDetails/?fixtureUUID={match_id}",
                            f"{api_base}/match/?fixtureUUID={match_id}",
                            f"{api_base}/matchData/?fixtureUUID={match_id}",
                            f"{api_base}/matchStats/?fixtureUUID={match_id}",
                            f"{api_base}/matchSummary/?fixtureUUID={match_id}",
                            f"{api_base}/lineups/?fixtureUUID={match_id}",
                            f"{api_base}/matchLineups/?fixtureUUID={match_id}",
                            f"{api_base}/matchEvents/?fixtureUUID={match_id}",
                        ]
                        
                        headers = {
                            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                            'Origin': 'https://www.scoresway.com',
                            'Referer': 'https://www.scoresway.com/',
                            'x-api-key': api_key,
                            'Accept': 'application/json',
                        }
                        
                        for endpoint in endpoints_to_try:
                            try:
                                print(f"     Trying: {endpoint[:80]}...")
                                response = await page.request.get(endpoint, headers=headers)
                                if response.status == 200:
                                    body = await response.body()
                                    if body and len(body) > 100:
                                        data = json.loads(body)
                                        if isinstance(data, dict) and ('matchInfo' in data or 'liveData' in data):
                                            match_data = data
                                            print(f"     Found match data via direct API: {endpoint[:80]}...")
                                            break
                                        elif isinstance(data, dict):
                                            print(f"     Response structure: {list(data.keys())[:5]}")
                            except Exception as e:
                                if 'endpoints_to_try.index(endpoint)' == '0':  # Only log first error
                                    print(f"      API call error: {e}")
                    except Exception as e:
                        print(f"      Method 3 failed: {e}")
                
                # Alternative 4: Try PerformFeeds matchstats API (the working method!)
                if not match_data:
                    try:
                        print(f"     Method 4: Trying PerformFeeds matchstats API (authenticated)...")
                        
                        # Credentials from the old working scraper
                        SDAPI_OUTLET_KEY = 'ft1tiv1inq7v1sk3y9tv12yh5'
                        CALLBACK_ID = 'W34bead4c41ca9fb2b9da261f6a64f68abed1d2172'
                        
                        # Build the API URL (JSONP format)
                        api_url = (
                            f"https://api.performfeeds.com/soccerdata/matchstats/{SDAPI_OUTLET_KEY}/"
                            f"{match_id}?_rt=c&_lcl=en&_fmt=jsonp&sps=widgets&_clbk={CALLBACK_ID}"
                        )
                        
                        # Build referer URL
                        referer_url = (
                            f"https://www.scoresway.com/en_GB/soccer/"
                            f"concacaf-caribbean-cup-2025/bygi47fmsxgbzysjdf9u481lg/fixtures"
                        )
                        
                        print(f"     Trying: {api_url[:80]}...")
                        response = await page.request.get(api_url, headers={
                            'Accept': 'application/json',
                            'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36',
                            'Referer': referer_url,
                            'Origin': 'https://www.scoresway.com',
                        })
                        
                        if response.status == 200:
                            body = await response.body()
                            if body and len(body) > 1000:
                                body_text = body.decode('utf-8')
                                
                                # Extract JSON from JSONP response
                                # JSONP format: callback_name({...json...})
                                inicio_json = body_text.find('(') + 1
                                final_json = body_text.rfind(')')
                                
                                if inicio_json > 0 and final_json > 0 and inicio_json < final_json:
                                    json_str = body_text[inicio_json:final_json]
                                    try:
                                        data = json.loads(json_str)
                                        if isinstance(data, dict) and ('matchInfo' in data or 'liveData' in data):
                                            match_data = data
                                            print(f"     Found match data via PerformFeeds matchstats API!")
                                        else:
                                            print(f"     Response structure: {list(data.keys())[:10] if isinstance(data, dict) else 'not a dict'}")
                                    except json.JSONDecodeError as e:
                                        print(f"      Error parsing JSON: {e}")
                                else:
                                    print(f"      Response is not JSONP format")
                        elif response.status == 403 or response.status == 401:
                            print(f"      PerformFeeds requires authentication (status {response.status})")
                        else:
                            print(f"      PerformFeeds returned status {response.status}")
                    except Exception as e:
                        print(f"      Method 4 failed: {e}")
                
                # Alternative 5: Try loading team fixtures page to get PerformFeeds data
                if not match_data:
                    try:
                        print(f"     Method 5: Loading team fixtures page to capture PerformFeeds XML...")
                        
                        # Clear previous responses (but keep the handler active)
                        captured_responses.clear()
                        response_tasks.clear()
                        # Note: response_count is a nonlocal, we'll just continue counting
                        
                        # Load Cibao's team fixtures page (where we know PerformFeeds requests happen)
                        team_id = "6lrtx6i2hsf52v8fh1j43f6cp"  # Cibao's team ID
                        team_url = f"https://www.scoresway.com/en_GB/soccer/concacaf-caribbean-cup-2025/bygi47fmsxgbzysjdf9u481lg/teams/view/{team_id}"
                        
                        print(f"     Loading team fixtures page: {team_url}")
                        await page.goto(team_url, wait_until='domcontentloaded', timeout=30000)
                        
                        # Wait and log what we see
                        print(f"    ⏳ Waiting for network requests...")
                        await asyncio.sleep(3)
                        await page.wait_for_load_state('networkidle', timeout=30000)
                        await asyncio.sleep(5)  # Give extra time for PerformFeeds requests
                        
                        print(f"     Response count so far: {response_count}")
                        print(f"     Captured responses: {len(captured_responses)}")
                        
                        # Wait for all handlers
                        if response_tasks:
                            await asyncio.gather(*response_tasks, return_exceptions=True)
                        await asyncio.sleep(3)
                        
                        print(f"     Found {len(captured_responses)} responses from team page...")
                        
                        # Now search for our match in the captured data
                        # The fixtureUUID might be in the match URL or we need to match by date/teams
                        match_data = find_match_data_in_responses(captured_responses, match_id)
                        
                        if match_data:
                            print(f"     Found match data from team fixtures page")
                        else:
                            print(f"      Match not found in team fixtures data. Found {len(captured_responses)} responses.")
                            # Print what we found for debugging
                            for url, data in captured_responses[:3]:
                                if isinstance(data, dict):
                                    print(f"     Sample data keys: {list(data.keys())[:10]}")
                    except Exception as e:
                        print(f"      Method 4 failed: {e}")
                
                if not match_data:
                    print(f"     Tip: The data might be loaded via a different mechanism.")
                    print(f"     Consider checking the Network tab manually to find the API endpoint.")
                    print(f"     You found PerformFeeds XML - we need to find the endpoint for individual matches.")
            
            await browser.close()
            
            if match_data:
                # Extract match details for filename
                match_info = match_data.get('matchInfo', {})
                contestants = match_info.get('contestant', []) or []
                
                home_team = "Unknown"
                away_team = "Unknown"
                if len(contestants) >= 2:
                    home_team = contestants[0].get('name') or contestants[0].get('shortName') or "Unknown"
                    away_team = contestants[1].get('name') or contestants[1].get('shortName') or "Unknown"
                
                local_date = match_info.get('localDate', '').replace('-', '')
                
                # Create filename
                from unicodedata import normalize
                def sanitize(name):
                    normalized = normalize('NFKD', name)
                    ascii_text = normalized.encode('ascii', 'ignore').decode('ascii')
                    return ascii_text.replace(' ', '_').replace('/', '-')
                
                filename = f"{local_date}_{sanitize(home_team)}_vs_{sanitize(away_team)}.json"
                if not local_date:
                    filename = f"{match_id}.json"
                
                output_path = output_dir / filename
                
                # Save JSON
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(match_data, f, ensure_ascii=False, indent=2)
                
                print(f"     Saved: {output_path.name}")
                return True
            else:
                print(f"     Could not extract match data")
                return False
                
        except Exception as e:
            print(f"     Error: {e}")
            await browser.close()
            return False


async def scrape_multiple_matches(match_ids: list[str], output_dir: Path = MATCHSTATS_DIR, headless: bool = True) -> Dict[str, bool]:
    """Scrape multiple matches."""
    results = {}
    
    for i, match_id in enumerate(match_ids, 1):
        print(f"\n[{i}/{len(match_ids)}]")
        success = await scrape_match(match_id, output_dir, headless=headless)
        results[match_id] = success
        
        # Be polite - wait between requests
        if i < len(match_ids):
            await asyncio.sleep(2)
    
    return results


def main():
    """Main entry point."""
    headless = True
    args = sys.argv[1:]
    
    # Check for --visible flag
    if '--visible' in args:
        headless = False
        args.remove('--visible')
    
    if len(args) < 1:
        print(__doc__)
        print("\nExamples:")
        print("  python scrape_scoresway_match.py 2zhrn3wxg2ma02g2u2j5lotuc")
        print("  python scrape_scoresway_match.py --url 'https://scoresway.com/.../match/view/2zhrn3wxg2ma02g2u2j5lotuc'")
        print("  python scrape_scoresway_match.py --list fixture_ids.txt")
        print("  python scrape_scoresway_match.py 2zhrn3wxg2ma02g2u2j5lotuc --visible  # Run with visible browser")
        sys.exit(1)
    
    if args[0] == '--list':
        # Read match IDs from file
        if len(args) < 2:
            print("Error: --list requires a file path")
            sys.exit(1)
        
        file_path = Path(args[1])
        if not file_path.exists():
            print(f"Error: File not found: {file_path}")
            sys.exit(1)
        
        with open(file_path, 'r') as f:
            match_ids = [line.strip() for line in f if line.strip()]
        
        print(f" Found {len(match_ids)} match IDs in {file_path}")
        results = asyncio.run(scrape_multiple_matches(match_ids))
        
    elif args[0] == '--url':
        # Extract match ID from URL
        if len(args) < 2:
            print("Error: --url requires a URL")
            sys.exit(1)
        
        match_id = extract_match_id(args[1])
        if not match_id:
            print(f"Error: Could not extract match ID from URL: {args[1]}")
            sys.exit(1)
        
        success = asyncio.run(scrape_match(match_id, headless=headless))
        sys.exit(0 if success else 1)
        
    else:
        # Single match ID
        match_id = extract_match_id(args[0])
        if not match_id:
            print(f"Error: Invalid match ID or URL: {args[0]}")
            sys.exit(1)
        
        success = asyncio.run(scrape_match(match_id, headless=headless))
        sys.exit(0 if success else 1)
    
    # Summary
    successful = sum(1 for v in results.values() if v)
    print(f"\n{'='*60}")
    print(f" Successfully scraped: {successful}/{len(results)}")
    if successful < len(results):
        print(f" Failed: {len(results) - successful}")


if __name__ == "__main__":
    main()

