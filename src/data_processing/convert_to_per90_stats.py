#!/usr/bin/env python3
"""
Convert Team Stats to Per 90 Statistics
========================================

This script converts team statistics to per 90 minute statistics,
normalizing metrics for better comparison across matches with different durations.

For team stats, uses the "Duration" column (match duration in minutes).
Converts counting stats (Goals, Fouls, Passes, etc.) to per 90 values.
Excludes percentages and already standardized metrics.

Usage:
    - Import function: from convert_to_per90_stats import convert_df_to_per90
    - Apply to DataFrame: df_per90 = convert_df_to_per90(df)
"""

import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

def get_excluded_columns():
    """
    Get list of columns that should NOT be converted to per 90 stats.
    These are already standardized metrics (percentages, ratios, etc.)
    """
    excluded_columns = [
        # Match/team identifiers
        'Date', 'Match', 'Competition', 'Duration', 'Team', 'Scheme',
        
        # Percentages (already standardized)
        'Possession, %', 'Shot Accuracy %', 'Pass Accuracy %', 'Duels Win %',
        'Shots On Target %', 'Shots Outside PA Accuracy %', 
        'Positional Attacks With Shot %', 'Counter Attacks With Shot %',
        'Set Pieces With Shot %', 'Corners With Shot %',
        'Free Kicks With Shot %', 'Penalties Conversion %', 'Cross Accuracy %',
        'Offensive Duels Win %', 'Shots Against Accuracy %', 
        'Defensive Duels Win %', 'Aerial Duels Win %', 
        'Sliding Tackles Success %', 'Forward Passes Accuracy %',
        'Back Passes Accuracy %', 'Lateral Passes Accuracy %', 
        'Long Passes Accuracy %', 'Passes To Final Third Accuracy %',
        'Progressive Passes Accuracy %', 'Smart Passes Accuracy %',
        'Throw Ins Accuracy %', 'Passes Accurate %',
        
        # Already standardized metrics
        'Match Tempo', 'Average Passes Per Possession', 'Long Pass %', 
        'Average Shot Distance', 'Average Pass Length', 'PPDA',
        
        # Wyscout-specific percentages/ratios
        'Successful defensive actions, %', 'Successful attacking actions, %',
        'Accurate passes, %', 'Pass accuracy', 'Shot accuracy', 
        'Duel win %', 'Aerial duel win %',
    ]
    
    return excluded_columns

def convert_df_to_per90(df):
    """
    Convert team statistics DataFrame to per 90 minute statistics.
    
    Args:
        df: pandas DataFrame with team stats (must have 'Duration' column)
        
    Returns:
        DataFrame with per 90 stats (same structure, values converted)
    """
    if df.empty:
        return df
    
    # Check for Duration column (required for conversion)
    if 'Duration' not in df.columns:
        print(" Warning: 'Duration' column not found. Cannot convert to per 90.")
        return df
    
    # Create a copy of the dataframe
    per90_df = df.copy()
    
    # Get excluded columns
    excluded_cols = get_excluded_columns()
    
    # Get all numeric columns that should be converted
    columns_to_convert = []
    for col in per90_df.columns:
        # Skip excluded columns
        if col in excluded_cols:
            continue
        
        # Skip Duration column (used for calculation, not converted)
        if col == 'Duration':
            continue
        
        # Skip columns with '%' in name (percentages)
        if '%' in col:
            continue
        
        # Skip standalone 'accuracy' columns (but NOT "something / accurate" columns)
        # Examples to SKIP: "Pass accuracy", "Shot accuracy"
        # Examples to CONVERT: "Passes / accurate", "Long passes / accurate"
        if 'accuracy' in col.lower():
            # Only skip if it doesn't have " / " (which indicates it's a counting stat)
            if ' / ' not in col:
                continue
        
        # Skip columns that contain 'Average', ' per ', or other rate indicators
        skip_keywords = [' average ', ' per ', ' ratio ', ' rate ', ' tempo']
        col_lower = ' ' + col.lower() + ' '  # Add spaces to catch keywords at start/end
        if any(keyword in col_lower for keyword in skip_keywords):
            continue
        
        # Check if column is numeric
        try:
            if pd.api.types.is_numeric_dtype(per90_df[col]):
                columns_to_convert.append(col)
        except:
            continue
    
    # Convert each column to per 90
    for col in columns_to_convert:
        if col in per90_df.columns:
            try:
                # Convert to per 90: (value / duration) * 90
                # Handle both single values and series
                per90_df[col] = per90_df.apply(
                    lambda row: (row[col] / row['Duration'] * 90) 
                    if pd.notna(row['Duration']) and row['Duration'] > 0 
                    else row[col],
                    axis=1
                )
            except Exception as e:
                # Skip if conversion fails
                pass
    
    return per90_df

def convert_file_to_per90(file_path, output_path=None):
    """
    Convert a single Excel or CSV file to per 90 stats.
    
    Args:
        file_path: Path to input file (Excel or CSV)
        output_path: Path to output file (optional, defaults to input with '_per90' suffix)
        
    Returns:
        bool: True if successful, False otherwise
    """
    from pathlib import Path
    
    file_path = Path(file_path)
    
    try:
        # Read the file
        if file_path.suffix == '.xlsx':
            # Try to read TeamStats sheet first, otherwise read first sheet
            try:
                df = pd.read_excel(file_path, sheet_name='TeamStats')
            except:
                df = pd.read_excel(file_path)
        elif file_path.suffix == '.csv':
            df = pd.read_csv(file_path)
        else:
            print(f"   Unsupported file type: {file_path.suffix}")
            return False
        
        if df.empty:
            print(f"   File is empty: {file_path.name}")
            return False
        
        # Convert to per 90
        df_per90 = convert_df_to_per90(df)
        
        # Determine output path
        if output_path is None:
            output_path = file_path.parent / f"{file_path.stem}_per90{file_path.suffix}"
        else:
            output_path = Path(output_path)
        
        # Save the converted file
        if file_path.suffix == '.xlsx':
            # If original had TeamStats sheet, preserve that structure
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                df_per90.to_excel(writer, sheet_name='TeamStats', index=False)
        else:
            df_per90.to_csv(output_path, index=False)
        
        print(f"   Converted {file_path.name} → {output_path.name}")
        return True
        
    except Exception as e:
        print(f"   Error processing {file_path.name}: {e}")
        return False
