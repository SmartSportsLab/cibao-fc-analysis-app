#!/usr/bin/env python3
"""
Fix Wyscout Export Headers
===========================

This script fixes the merged headers in Wyscout exports, converting:
- "Passes / accurate" + "Unnamed: 13" → "Passes" + "Accurate Passes"
- "Shots / on target" + "Unnamed: 10" → "Shots" + "Shots on Target"

Works for both Player Stats and Team Stats exports.

Usage:
    - Import functions: from fix_wyscout_headers import fix_team_headers, fix_player_headers
    - Apply to DataFrame: df = fix_team_headers(df)
"""

import pandas as pd
import warnings
warnings.filterwarnings('ignore')

# Header mappings based on Wyscout official metrics
PLAYER_HEADER_MAPPING = {
    'Total actions / successful': ['Total Action', 'Successful Actions'],
    'Shots / on target': ['Shots', 'Shots on Target'],
    'Passes / accurate': ['Passes', 'Accurate Passes'],
    'Long passes / accurate': ['Long Passes', 'Accurate Long Passes'],
    'Crosses / accurate': ['Crosses', 'Accurate Crosses'],
    'Dribbles / successful': ['Dribbles', 'Successful Dribbles'],
    'Duels / won': ['Duels', 'Duels Won'],
    'Aerial duels / won': ['Aerial Duels', 'Aerial Duels Won'],
    'Losses / own half': ['Losses', 'Losses Own Half'],
    'Recoveries / opp. half': ['Recoveries', 'Recoveries Opp Half'],
    'Defensive duels / won': ['Defensive Duels', 'Defensive Duels Won'],
    'Loose ball duels / won': ['Loose Ball Duels', 'Loose Ball Duels Won'],
    'Sliding tackles / successful': ['Sliding Tackles', 'Sliding Tackles Successful'],
    'Offensive duels / won': ['Offensive Duels', 'Offensive Duels Won'],
    'Through passes / accurate': ['Through Passes', 'Through Passes Accurate'],
    'Passes to final third / accurate': ['Passes to Final Third', 'Passes to Final Third Accurate'],
    'Passes to penalty area / accurate': ['Passes to Penalty Area', 'Passes to Penalty Area Accurate'],
    'Forward passes / accurate': ['Forward Passes', 'Forward Passes Accurate'],
    'Back passes / accurate': ['Back Passes', 'Back Passes Accurate'],
    'Saves / with reflexes': ['Saves', 'Saves With Reflexes'],
    'Passes to GK / accurate': ['Passes to GK', 'Passes to GK Accurate'],
}

def fix_player_headers(df):
    """
    Fix merged headers in player stats exports
    
    Args:
        df: pandas DataFrame with Wyscout player stats
        
    Returns:
        DataFrame with fixed headers
    """
    new_columns = []
    skip_next = False
    
    for i, col in enumerate(df.columns):
        if skip_next:
            skip_next = False
            continue
            
        # Check if this is a merged header
        if col in PLAYER_HEADER_MAPPING:
            # Add both column names
            new_columns.extend(PLAYER_HEADER_MAPPING[col])
            skip_next = True  # Skip the next "Unnamed: X" column
        elif col.startswith('Unnamed:'):
            # This shouldn't happen if mapping is correct, but keep as fallback
            new_columns.append(col)
        else:
            new_columns.append(col)
    
    # Rename columns
    df.columns = new_columns
    return df

def fix_team_headers(df):
    """
    Fix merged headers in team stats exports
    Team stats have complex patterns like:
    - "Shots / on target" → "Shots", "Shots On Target", "Shots On Target %"
    - "Losses / Low / Medium / High" → "Losses", "Losses Low", "Losses Medium", "Losses High"
    
    Args:
        df: pandas DataFrame with Wyscout team stats
        
    Returns:
        DataFrame with fixed headers
    """
    new_columns = []
    skip_count = 0
    
    for i, col in enumerate(df.columns):
        if skip_count > 0:
            skip_count -= 1
            continue
        
        # Check for triple slash patterns (e.g., "Losses / Low / Medium / High")
        if col in ['Losses / Low / Medium / High']:
            new_columns.extend(['Losses', 'Losses Low', 'Losses Medium', 'Losses High'])
            skip_count = 3
        elif col in ['Recoveries / Low / Medium / High']:
            new_columns.extend(['Recoveries', 'Recoveries Low', 'Recoveries Medium', 'Recoveries High'])
            skip_count = 3
        
        # Check for double slash patterns with percentage (e.g., "Shots / on target")
        elif col == 'Shots / on target':
            new_columns.extend(['Shots', 'Shots On Target', 'Shots On Target %'])
            skip_count = 2
        elif col == 'Passes / accurate':
            new_columns.extend(['Passes', 'Passes Accurate', 'Passes Accurate %'])
            skip_count = 2
        elif col == 'Duels / won':
            new_columns.extend(['Duels', 'Duels Won', 'Duels Won %'])
            skip_count = 2
        elif col == 'Shots from outside penalty area / on target':
            new_columns.extend(['Shots From Outside Penalty Area', 'Shots From Outside Penalty Area On Target', 'Shots From Outside Penalty Area On Target %'])
            skip_count = 2
        elif col == 'Positional attacks / with shots':
            new_columns.extend(['Positional Attacks', 'Positional Attacks With Shots', 'Positional Attacks With Shots %'])
            skip_count = 2
        elif col == 'Counterattacks / with shots':
            new_columns.extend(['Counter Attacks', 'Counter Attacks With Shots', 'Counter Attacks With Shots %'])
            skip_count = 2
        elif col == 'Set pieces / with shots':
            new_columns.extend(['Set Pieces', 'Set Pieces With Shots', 'Set Pieces With Shots %'])
            skip_count = 2
        elif col == 'Corners / with shots':
            new_columns.extend(['Corners', 'Corners With Shots', 'Corners With Shots %'])
            skip_count = 2
        elif col == 'Free kicks / with shots':
            new_columns.extend(['Free Kicks', 'Free Kicks With Shots', 'Free Kicks With Shots %'])
            skip_count = 2
        elif col == 'Penalties / converted':
            new_columns.extend(['Penalties', 'Penalties Converted', 'Penalties Converted %'])
            skip_count = 2
        elif col == 'Crosses / accurate':
            new_columns.extend(['Crosses', 'Crosses Accurate', 'Crosses Accurate %'])
            skip_count = 2
        elif col == 'Penalty area entries (runs / crosses)':
            new_columns.extend(['Penalty Area Entries', 'Penalty Area Entries Runs', 'Penalty Area Entries Crosses'])
            skip_count = 2
        elif col == 'Offensive duels / won':
            new_columns.extend(['Offensive Duels', 'Offensive Duels Won', 'Offensive Duels Won %'])
            skip_count = 2
        elif col == 'Shots against / on target':
            new_columns.extend(['Shots Against', 'Shots Against On Target', 'Shots Against On Target %'])
            skip_count = 2
        elif col == 'Defensive duels / won':
            new_columns.extend(['Defensive Duels', 'Defensive Duels Won', 'Defensive Duels Won %'])
            skip_count = 2
        elif col == 'Aerial duels / won':
            new_columns.extend(['Aerial Duels', 'Aerial Duels Won', 'Aerial Duels Won %'])
            skip_count = 2
        elif col == 'Sliding tackles / successful':
            new_columns.extend(['Sliding Tackles', 'Sliding Tackles Successful', 'Sliding Tackles Successful %'])
            skip_count = 2
        elif col == 'Forward passes / accurate':
            new_columns.extend(['Forward Passes', 'Forward Passes Accurate', 'Forward Passes Accurate %'])
            skip_count = 2
        elif col == 'Back passes / accurate':
            new_columns.extend(['Back Passes', 'Back Passes Accurate', 'Back Passes Accurate %'])
            skip_count = 2
        elif col == 'Lateral passes / accurate':
            new_columns.extend(['Lateral Passes', 'Lateral Passes Accurate', 'Lateral Passes Accurate %'])
            skip_count = 2
        elif col == 'Long passes / accurate':
            new_columns.extend(['Long Passes', 'Long Passes Accurate', 'Long Passes Accurate %'])
            skip_count = 2
        elif col == 'Passes to final third / accurate':
            new_columns.extend(['Passes To Final Third', 'Passes To Final Third Accurate', 'Passes To Final Third Accurate %'])
            skip_count = 2
        elif col == 'Progressive passes / accurate':
            new_columns.extend(['Progressive Passes', 'Progressive Passes Accurate', 'Progressive Passes Accurate %'])
            skip_count = 2
        elif col == 'Smart passes / accurate':
            new_columns.extend(['Smart Passes', 'Smart Passes Accurate', 'Smart Passes Accurate %'])
            skip_count = 2
        elif col == 'Throw ins / accurate':
            new_columns.extend(['Throw Ins', 'Throw Ins Accurate', 'Throw Ins Accurate %'])
            skip_count = 2
        
        # Handle single columns
        elif col.startswith('Unnamed:'):
            # This shouldn't happen if our mapping is correct
            new_columns.append(col)
        else:
            new_columns.append(col)
    
    df.columns = new_columns
    return df

def fix_file_headers(file_path, file_type='player', create_backup=True):
    """
    Fix headers in a single file
    
    Args:
        file_path: Path to the file to fix (Path object or string)
        file_type: 'player' or 'team'
        create_backup: If True, creates a backup with '_original' suffix
        
    Returns:
        bool: True if successful, False otherwise
    """
    from pathlib import Path
    import shutil
    
    file_path = Path(file_path)
    
    try:
        # Create backup if requested
        if create_backup:
            backup_path = file_path.parent / f"{file_path.stem}_original{file_path.suffix}"
            # Only create backup if it doesn't already exist
            if not backup_path.exists():
                shutil.copy2(file_path, backup_path)
        
        # Read the file
        if file_path.suffix == '.xlsx':
            df = pd.read_excel(file_path)
        elif file_path.suffix == '.csv':
            df = pd.read_csv(file_path)
        else:
            print(f"   Unsupported file type: {file_path.suffix}")
            return False
        
        # Fix headers based on file type
        if file_type == 'player':
            df = fix_player_headers(df)
        else:
            df = fix_team_headers(df)
        
        # Save back to the same file
        if file_path.suffix == '.xlsx':
            df.to_excel(file_path, index=False)
        else:
            df.to_csv(file_path, index=False)
        
        return True
        
    except Exception as e:
        print(f"   Error processing {file_path.name}: {e}")
        return False
