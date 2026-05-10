# ===========================================
# SIMPLE WYSCOUT UPLOADER - Clean & Working
# ===========================================
# Flow: Upload Excel → Clean Headers → Convert to Per90 → Save JSON → Done
# ===========================================

import streamlit as st
import pandas as pd
import json
from pathlib import Path
import sys
from datetime import datetime
import re
import os
import unicodedata

# Add src to path - try multiple methods for Streamlit Cloud
REPO_ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(REPO_ROOT))

# Also add src/data_processing to path for direct imports
src_data_processing = REPO_ROOT / "src" / "data_processing"
if str(src_data_processing) not in sys.path:
    sys.path.insert(0, str(src_data_processing))

# Import required functions with multiple fallbacks for Streamlit Cloud
fix_team_headers = None
convert_df_to_per90 = None

# Try importing fix_team_headers
try:
    from src.data_processing.fix_wyscout_headers import fix_team_headers
except ImportError:
    try:
        from fix_wyscout_headers import fix_team_headers
    except ImportError:
        # Last resort: use importlib to load directly
        try:
            import importlib.util
            fix_path = src_data_processing / "fix_wyscout_headers.py"
            if fix_path.exists():
                spec = importlib.util.spec_from_file_location("fix_wyscout_headers", fix_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    fix_team_headers = module.fix_team_headers
            else:
                raise ImportError(f"File not found: {fix_path}")
        except Exception as e:
            st.error(f" CRITICAL: Could not import fix_team_headers: {e}")
            st.stop()

# Try importing convert_df_to_per90
try:
    from src.data_processing.convert_to_per90_stats import convert_df_to_per90
except ImportError:
    try:
        from convert_to_per90_stats import convert_df_to_per90
    except ImportError:
        # Last resort: use importlib to load directly
        try:
            import importlib.util
            convert_path = src_data_processing / "convert_to_per90_stats.py"
            if convert_path.exists():
                spec = importlib.util.spec_from_file_location("convert_to_per90_stats", convert_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    convert_df_to_per90 = module.convert_df_to_per90
            else:
                raise ImportError(f"File not found: {convert_path}")
        except Exception as e:
            st.error(f" CRITICAL: Could not import convert_df_to_per90: {e}")
            st.stop()

# Try importing theme
try:
    from src.utils.global_dark_theme import inject_dark_theme
except ImportError:
    def inject_dark_theme():
        pass  # No theme if can't import

# Try importing navigation
try:
    from src.utils.navigation import render_top_navigation
except ImportError:
    def render_top_navigation():
        pass  # No navigation if can't import

# Directories
PROCESSED_DIR = REPO_ROOT / "data" / "processed" / "Wyscout"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
METADATA_FILE = PROCESSED_DIR / "upload_metadata.json"

def load_upload_metadata():
    """Load upload metadata from JSON file."""
    if METADATA_FILE.exists():
        try:
            with open(METADATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_upload_metadata(metadata):
    """Save upload metadata to JSON file."""
    try:
        with open(METADATA_FILE, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False, default=str)
    except Exception as e:
        st.warning(f"Could not save upload metadata: {e}")

def remove_accents(text):
    """Remove accents from text to normalize team names and match strings.
    
    This helps with matching teams that have accents (e.g., Atlético, Atlántico, San Cristóbal)
    by converting them to their non-accented equivalents (Atletico, Atlantico, San Cristobal).
    """
    if pd.isna(text) or not text:
        return text if isinstance(text, str) else ""
    
    text = str(text)
    # Normalize Unicode to NFD (decomposed form) - separates base characters from combining marks
    nfd = unicodedata.normalize('NFD', text)
    # Remove combining marks (accents) - keep only base characters
    no_accents = ''.join(c for c in nfd if unicodedata.category(c) != 'Mn')
    return no_accents

def clean_team_name_from_filename(filename):
    """Extract and clean team name from filename, removing (1) suffixes."""
    # Remove "Team Stats " prefix and file extension
    team_name = filename.replace("Team Stats ", "").replace(".xlsx", "").replace(".xls", "").strip()
    # Remove (1), (2), etc. suffixes
    team_name = re.sub(r'\s*\(\d+\)\s*$', '', team_name).strip()
    return team_name

def find_old_team_files(team_name_clean, directory):
    """Find all old files (JSON and Excel) for a given team name.
    
    Handles variations like:
    - Team Stats Cibao.xls
    - Team Stats Cibao (1).xls
    - Cibao_per_90.json
    """
    old_files = []
    
    # Clean the team name for matching (remove (1) suffixes)
    team_name_normalized = re.sub(r'\s*\(\d+\)\s*$', '', team_name_clean).strip()
    team_name_safe = team_name_normalized.replace(" ", "_").replace("/", "_").replace("\\", "_")
    
    if not directory.exists():
        return old_files
    
    # Find JSON files matching this team
    for file_path in directory.glob("*.json"):
        filename = file_path.name
        # Remove .json extension and normalize
        filename_base = filename.replace(".json", "").replace("_per_90", "")
        # Check if filename starts with the cleaned team name (handles variations)
        # This matches: "Cibao_per_90.json", "Cibao_something.json", etc.
        if filename_base.startswith(team_name_safe) or filename.startswith(team_name_safe + "_"):
            old_files.append(file_path)
    
    # Also check metadata for old filenames that might match
    metadata = load_upload_metadata()
    for stored_team_name, info in metadata.items():
        stored_team_clean = clean_team_name_from_filename(stored_team_name)
        stored_filename = info.get("filename", "")
        
        # If the stored team name matches (after cleaning), check for the Excel file
        if re.sub(r'\s*\(\d+\)\s*$', '', stored_team_clean).strip().lower() == team_name_normalized.lower():
            # Look for Excel files in the directory that match
            excel_patterns = [
                stored_filename,
                stored_filename.replace(".xlsx", ".xls"),
                stored_filename.replace(".xls", ".xlsx"),
            ]
            for pattern in excel_patterns:
                excel_path = directory / pattern
                if excel_path.exists():
                    old_files.append(excel_path)
    
    return old_files

def remove_old_team_files(team_name_clean, directory):
    """Remove all old files for a team before uploading new data."""
    old_files = find_old_team_files(team_name_clean, directory)
    
    removed_files = []
    for file_path in old_files:
        try:
            if file_path.exists():
                file_path.unlink()
                removed_files.append(file_path.name)
        except Exception as e:
            st.warning(f"   Could not delete old file {file_path.name}: {e}")
    
    # Also clean up metadata entries for this team (all variations)
    metadata = load_upload_metadata()
    team_name_normalized = re.sub(r'\s*\(\d+\)\s*$', '', team_name_clean).strip().lower()
    
    teams_to_remove = []
    for stored_team_name in metadata.keys():
        stored_team_clean = clean_team_name_from_filename(stored_team_name)
        stored_team_normalized = re.sub(r'\s*\(\d+\)\s*$', '', stored_team_clean).strip().lower()
        if stored_team_normalized == team_name_normalized:
            teams_to_remove.append(stored_team_name)
    
    for team_to_remove in teams_to_remove:
        metadata.pop(team_to_remove, None)
    
    if teams_to_remove:
        save_upload_metadata(metadata)
    
    return removed_files

def update_upload_metadata(team_name, filename):
    """Update metadata with new upload information."""
    metadata = load_upload_metadata()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    metadata[team_name] = {
        "filename": filename,
        "uploaded_at": timestamp,
        "uploaded_at_iso": datetime.now().isoformat()
    }
    save_upload_metadata(metadata)

st.set_page_config(page_title="Upload Wyscout Data", page_icon="", layout="wide")
inject_dark_theme()

# ---------- TOP NAVIGATION BAR ----------
render_top_navigation()

st.title(" Upload Wyscout Data")
st.markdown("**Simple flow:** Upload Excel → Clean headers → Convert to per90 → Save JSON")

# Display Current Data section
with st.expander(" Current Data", expanded=False):
    metadata = load_upload_metadata()
    if metadata:
        st.markdown("**Uploaded files by team:**")
        # Sort by upload time (most recent first)
        sorted_teams = sorted(metadata.items(), key=lambda x: x[1].get("uploaded_at_iso", ""), reverse=True)
        
        # Create a table-like display
        for team_name, info in sorted_teams:
            filename = info.get("filename", "Unknown")
            uploaded_at = info.get("uploaded_at", "Unknown")
            col1, col2, col3 = st.columns([2, 3, 2])
            with col1:
                st.markdown(f"**{team_name}**")
            with col2:
                st.markdown(f"`{filename}`")
            with col3:
                st.markdown(f" {uploaded_at}")
            st.markdown("---")
    else:
        st.info("No files have been uploaded yet.")

# Upload files
uploaded_files = st.file_uploader(
    "Select Excel files from Wyscout",
    type=["xlsx", "xls"],
    accept_multiple_files=True
)

if uploaded_files:
    if st.button(" Process Files", type="primary", use_container_width=True):
        progress_bar = st.progress(0)
        results = {"success": 0, "errors": []}
        
        for idx, uploaded_file in enumerate(uploaded_files):
            try:
                progress_bar.progress((idx + 1) / len(uploaded_files))
                st.write(f" **Processing:** {uploaded_file.name}")
                
                # Step 1: Extract team name from filename
                # Format: "Team Stats Cibao.xlsx" → "Cibao"
                # Also handles: "Team Stats Cibao (1).xlsx" → "Cibao"
                filename = uploaded_file.name
                team_name = clean_team_name_from_filename(filename)
                st.write(f"   Team from filename: {team_name}")
                
                # Step 1.5: Remove old files for this team (handles naming variations)
                st.write(f"   Removing old files for {team_name}...")
                removed_files = remove_old_team_files(team_name, PROCESSED_DIR)
                if removed_files:
                    st.write(f"   Removed {len(removed_files)} old file(s): {', '.join(removed_files)}")
                else:
                    st.write(f"  ℹ No old files found to remove")
                
                # Step 2: Load Excel (handle multiple sheets)
                xls = pd.ExcelFile(uploaded_file)
                
                # Check if it's TeamStats format (single sheet with all teams)
                if "TeamStats" in xls.sheet_names:
                    df = pd.read_excel(xls, sheet_name="TeamStats")
                else:
                    # Multiple sheets - combine them
                    all_sheets = []
                    for sheet_name in xls.sheet_names:
                        df_sheet = pd.read_excel(xls, sheet_name=sheet_name)
                        all_sheets.append(df_sheet)
                    df = pd.concat(all_sheets, ignore_index=True)
                
                # Step 3: Add Team column from filename (if not already present)
                if "Team" not in df.columns:
                    df["Team"] = team_name
                else:
                    # If Team column exists but is empty or has wrong values, use filename
                    if df["Team"].isna().all() or (df["Team"].iloc[0] if len(df) > 0 else None) in ["TeamStats", "Team", ""]:
                        df["Team"] = team_name
                
                # Step 4: Clean headers
                df = fix_team_headers(df)
                st.write("   Headers cleaned")
                
                # Step 5: Convert to per90 (if Duration exists)
                if "Duration" in df.columns:
                    df = convert_df_to_per90(df)
                    st.write("   Converted to per90")
                else:
                    st.warning("   No 'Duration' column - skipping per90 conversion")
                
                # Step 5.5: Normalize accents in Team and Match columns for consistent matching
                # This ensures teams with accents (Atlético, Atlántico, San Cristóbal) can be matched correctly
                if "Team" in df.columns:
                    # Store original team name in a separate column for display, but normalize the main Team column
                    df["Team_Original"] = df["Team"].copy()  # Keep original for reference
                    df["Team"] = df["Team"].apply(remove_accents)
                    st.write("   Normalized accents in Team column")
                
                if "Match" in df.columns:
                    # Normalize accents in Match column (contains team names)
                    df["Match"] = df["Match"].apply(remove_accents)
                    st.write("   Normalized accents in Match column")
                
                # Step 6: Save JSON (Team column is now guaranteed to exist from filename)
                # All rows are for the same team (from filename)
                team_df = df.copy()
                
                # Verify it has required columns
                if "Passes" not in team_df.columns or "Shots" not in team_df.columns:
                    st.error(f"   {team_name}: Missing 'Passes' or 'Shots' columns after processing")
                    results["errors"].append(f"{team_name}: Missing required columns")
                else:
                    # Save JSON
                    team_name_clean = team_name.replace(" ", "_").replace("/", "_").replace("\\", "_")
                    json_path = PROCESSED_DIR / f"{team_name_clean}_per_90.json"
                    
                    with open(json_path, "w", encoding="utf-8") as f:
                        json.dump(team_df.to_dict(orient="records"), f, indent=2, ensure_ascii=False, default=str)
                    
                    # Update upload metadata
                    update_upload_metadata(team_name, filename)
                    
                    st.success(f"   Saved: `{json_path.name}` ({len(team_df)} rows, {len(team_df.columns)} columns)")
                    results["success"] += 1
                    
            except Exception as e:
                st.error(f"   Error processing {uploaded_file.name}: {str(e)}")
                results["errors"].append(f"{uploaded_file.name}: {str(e)}")
                import traceback
                with st.expander("Error details", expanded=False):
                    st.code(traceback.format_exc())
        
        progress_bar.empty()
        
        # Summary
        st.markdown("---")
        st.markdown(f"###  Summary")
        st.success(f" **{results['success']} team(s) processed successfully**")
        
        if results["errors"]:
            st.markdown("###  Errors:")
            for error in results["errors"]:
                st.error(f"  - {error}")
        
        # Clear cache and refresh
        st.cache_data.clear()
        st.markdown("---")
        st.success(" **Processing complete!** Data is now available on analytics pages.")
        
        if st.button(" Refresh App", type="primary"):
            st.rerun()
