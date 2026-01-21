"""
Universal Excel Handler for Central Planning Platform (CPP)
==========================================================

This is the CORE module for processing varied Excel files from different
marketing channels (TV, OOH, FM, etc.). It handles:

1. Smart Header Detection - Skips metadata/junk rows automatically
2. Column Normalization - Maps varied column names to standard schema
3. Data Cleaning - Handles dates, numbers, and missing values
4. Validation - Ensures required fields are present

Usage:
    from modules.excel_handler import process_uploaded_file
    
    df, metadata, errors = process_uploaded_file(
        uploaded_file=st_uploaded_file,
        channel_type="TV"
    )

Author: CPP Development Team
"""

import re
import hashlib
import logging
from io import BytesIO
from typing import Tuple, Optional, List, Dict, Any
from datetime import datetime

import pandas as pd
import numpy as np

# Import our mappings
import sys
sys.path.append('..')
from config import (
    MAX_HEADER_SEARCH_ROWS,
    HEADER_KEYWORDS, 
    SUPPORTED_EXTENSIONS,
    ChannelType
)
from mappings.column_maps import (
    COMMON_COLUMN_MAP,
    CHANNEL_SPECIFIC_MAPS,
    REQUIRED_COLUMNS,
    RECOMMENDED_COLUMNS
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# MAIN PROCESSING FUNCTION
# =============================================================================

def process_uploaded_file(
    uploaded_file,
    channel_type: str,
    sheet_name: int = 0
) -> Tuple[Optional[pd.DataFrame], Dict[str, Any], List[str]]:
    """
    Process an uploaded Excel/CSV file and return a normalized DataFrame.
    
    This is the main entry point for file processing. It:
    1. Reads the file (Excel or CSV)
    2. Detects the header row automatically
    3. Maps columns to standard names
    4. Cleans and validates data
    5. Adds channel information
    
    Args:
        uploaded_file: Streamlit UploadedFile object or file path string
        channel_type: Marketing channel type (TV, OOH, FM, etc.)
        sheet_name: Excel sheet index to process (default: 0 = first sheet)
    
    Returns:
        Tuple of (DataFrame, metadata_dict, errors_list):
        - DataFrame: Cleaned and normalized data (None if failed)
        - metadata: File info (rows, columns, hash, etc.)
        - errors: List of error/warning messages
        
    Example:
        >>> df, meta, errors = process_uploaded_file(file, "TV")
        >>> if df is not None:
        >>>     st.success(f"Loaded {meta['row_count']} rows")
        >>> else:
        >>>     st.error("\\n".join(errors))
    """
    errors = []
    metadata = {
        "filename": None,
        "channel_type": channel_type,
        "original_columns": [],
        "mapped_columns": [],
        "row_count": 0,
        "total_amount": None,
        "file_hash": None,
        "header_row": None,
        "processing_time": None,
    }
    
    start_time = datetime.now()
    
    try:
        # ======================
        # STEP 1: Read the File
        # ======================
        
        # Get filename
        if hasattr(uploaded_file, 'name'):
            metadata["filename"] = uploaded_file.name
            file_content = uploaded_file.read()
            uploaded_file.seek(0)  # Reset for re-reading
        else:
            metadata["filename"] = str(uploaded_file)
            with open(uploaded_file, 'rb') as f:
                file_content = f.read()
        
        # Calculate file hash for duplicate detection
        metadata["file_hash"] = hashlib.md5(file_content).hexdigest()
        
        # Determine file type and read
        filename_lower = metadata["filename"].lower()
        
        if filename_lower.endswith('.csv'):
            df_raw = _read_csv_smart(uploaded_file)
        elif filename_lower.endswith(('.xlsx', '.xls')):
            df_raw = _read_excel_smart(uploaded_file, sheet_name)
        else:
            errors.append(f"Unsupported file type. Supported: {SUPPORTED_EXTENSIONS}")
            return None, metadata, errors
        
        if df_raw is None or df_raw.empty:
            errors.append("File is empty or could not be read")
            return None, metadata, errors
        
        logger.info(f"Read file with shape: {df_raw.shape}")
        
        # ======================
        # STEP 2: Find Header Row
        # ======================
        
        header_row_idx = _find_header_row(df_raw)
        
        if header_row_idx is None:
            errors.append(
                f"Could not find header row. Looking for keywords: {HEADER_KEYWORDS[:4]}... "
                f"Please ensure your file has a header row with these column names."
            )
            return None, metadata, errors
        
        metadata["header_row"] = header_row_idx
        logger.info(f"Found header at row {header_row_idx}")
        
        # Re-read with correct header
        if filename_lower.endswith('.csv'):
            df = _read_csv_smart(uploaded_file, header_row=header_row_idx)
        else:
            df = _read_excel_smart(uploaded_file, sheet_name, header_row=header_row_idx)
        
        # Store original columns for reference
        metadata["original_columns"] = df.columns.tolist()
        
        # ======================
        # STEP 3: Map Columns
        # ======================
        
        df = _normalize_columns(df, channel_type)
        metadata["mapped_columns"] = df.columns.tolist()
        
        # ======================
        # STEP 4: Validate Required Columns
        # ======================
        
        missing_required = []
        for col in REQUIRED_COLUMNS:
            if col not in df.columns:
                missing_required.append(col)
        
        if missing_required:
            errors.append(
                f"Missing required columns after mapping: {missing_required}. "
                f"Original columns: {metadata['original_columns'][:10]}..."
            )
            return None, metadata, errors
        
        # Warnings for missing recommended columns
        missing_recommended = [col for col in RECOMMENDED_COLUMNS if col not in df.columns]
        if missing_recommended:
            errors.append(f"⚠️ Warning: Missing recommended columns: {missing_recommended}")
        
        # ======================
        # STEP 5: Clean Data
        # ======================
        
        df = _clean_dataframe(df)
        
        # Add channel column
        df["channel"] = channel_type
        
        # Add row numbers for traceability
        df["row_number"] = range(1, len(df) + 1)
        
        # Remove completely empty rows
        df = df.dropna(how='all', subset=[c for c in df.columns if c not in ['row_number', 'channel']])
        
        # ======================
        # STEP 6: Calculate Metadata
        # ======================
        
        metadata["row_count"] = len(df)
        
        if "amount_planned" in df.columns:
            # Convert to numeric and sum
            amounts = pd.to_numeric(df["amount_planned"], errors='coerce')
            metadata["total_amount"] = float(amounts.sum()) if not amounts.isna().all() else None
        
        metadata["processing_time"] = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"Successfully processed {metadata['row_count']} rows")
        
        return df, metadata, errors
        
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        errors.append(f"Processing error: {str(e)}")
        return None, metadata, errors


# =============================================================================
# HELPER FUNCTIONS - File Reading
# =============================================================================

def _read_excel_smart(
    file_source,
    sheet_name: int = 0,
    header_row: Optional[int] = None
) -> pd.DataFrame:
    """
    Read Excel file with smart settings.
    
    Args:
        file_source: File path or BytesIO object
        sheet_name: Sheet index to read
        header_row: Row index for column headers (None = let pandas decide)
    
    Returns:
        DataFrame with raw data
    """
    try:
        if hasattr(file_source, 'read'):
            file_source.seek(0)
        
        return pd.read_excel(
            file_source,
            sheet_name=sheet_name,
            header=header_row,
            dtype=str,  # Read everything as string initially
            na_values=['', 'N/A', 'NA', 'n/a', 'NULL', 'null', '-'],
        )
    except Exception as e:
        logger.error(f"Error reading Excel: {str(e)}")
        raise


def _read_csv_smart(
    file_source,
    header_row: Optional[int] = None
) -> pd.DataFrame:
    """
    Read CSV file with smart encoding detection.
    
    Args:
        file_source: File path or BytesIO object
        header_row: Row index for column headers
    
    Returns:
        DataFrame with raw data
    """
    # Try different encodings (Mongolian files often use UTF-8 or Windows-1251)
    encodings = ['utf-8', 'utf-8-sig', 'cp1251', 'latin1']
    
    for encoding in encodings:
        try:
            if hasattr(file_source, 'read'):
                file_source.seek(0)
            
            return pd.read_csv(
                file_source,
                header=header_row,
                dtype=str,
                encoding=encoding,
                na_values=['', 'N/A', 'NA', 'n/a', 'NULL', 'null', '-'],
            )
        except UnicodeDecodeError:
            continue
        except Exception as e:
            logger.error(f"Error reading CSV with {encoding}: {str(e)}")
            raise
    
    raise ValueError("Could not decode CSV file with any supported encoding")


# =============================================================================
# HELPER FUNCTIONS - Header Detection
# =============================================================================

def _find_header_row(df: pd.DataFrame) -> Optional[int]:
    """
    Find the row containing column headers by searching for keywords.
    
    This handles files where the first several rows contain metadata
    (company name, date, title, etc.) before the actual data table.
    
    Algorithm:
    1. Search each row for header keywords
    2. Score each row by how many keywords match
    3. Return the row with highest score (if score > 0)
    
    Args:
        df: Raw DataFrame read without header specification
    
    Returns:
        Row index where headers are found, or None if not found
    """
    max_rows_to_check = min(MAX_HEADER_SEARCH_ROWS, len(df))
    best_row = None
    best_score = 0
    
    # Prepare keywords for matching (lowercase)
    keywords = [kw.lower().strip() for kw in HEADER_KEYWORDS]
    
    for row_idx in range(max_rows_to_check):
        row_values = df.iloc[row_idx].astype(str).str.lower().str.strip().tolist()
        
        # Calculate match score for this row
        score = 0
        for val in row_values:
            for keyword in keywords:
                if keyword in val:
                    score += 1
                    break  # Count each cell once
        
        # Update best if this row has more matches
        if score > best_score:
            best_score = score
            best_row = row_idx
    
    # Require at least 2 keyword matches to be confident
    if best_score >= 2:
        return best_row
    
    return None


# =============================================================================
# HELPER FUNCTIONS - Column Normalization
# =============================================================================

def _normalize_columns(df: pd.DataFrame, channel_type: str) -> pd.DataFrame:
    """
    Rename columns from source names to standard database schema names.
    
    Uses a two-pass approach:
    1. First apply common mappings (budget_code, campaign_name, etc.)
    2. Then apply channel-specific mappings (duration -> metric_1 for TV)
    
    Args:
        df: DataFrame with original column names
        channel_type: Channel type to get specific mappings
    
    Returns:
        DataFrame with standardized column names
    """
    df = df.copy()
    
    # Normalize column names for matching (lowercase, strip whitespace)
    original_columns = df.columns.tolist()
    normalized_lookup = {col.lower().strip(): col for col in original_columns}
    
    # Build the rename mapping
    rename_map = {}
    
    # Pass 1: Common mappings
    for source_pattern, target_name in COMMON_COLUMN_MAP.items():
        # Check if any column matches this pattern
        for norm_col, orig_col in normalized_lookup.items():
            if source_pattern in norm_col or norm_col in source_pattern:
                # Don't override if already mapped
                if orig_col not in rename_map:
                    rename_map[orig_col] = target_name
                    logger.debug(f"Mapped '{orig_col}' -> '{target_name}'")
    
    # Pass 2: Channel-specific mappings
    channel_map = CHANNEL_SPECIFIC_MAPS.get(channel_type, {})
    for source_pattern, target_name in channel_map.items():
        for norm_col, orig_col in normalized_lookup.items():
            if source_pattern in norm_col or norm_col in source_pattern:
                # Don't override common mappings
                if orig_col not in rename_map:
                    rename_map[orig_col] = target_name
                    logger.debug(f"Mapped '{orig_col}' -> '{target_name}' (channel-specific)")
    
    # Apply the rename
    df = df.rename(columns=rename_map)
    
    # Log unmapped columns
    unmapped = [col for col in original_columns if col not in rename_map]
    if unmapped:
        logger.info(f"Unmapped columns (kept as-is): {unmapped[:5]}...")
    
    return df


# =============================================================================
# HELPER FUNCTIONS - Data Cleaning
# =============================================================================

def _clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and standardize data types in the DataFrame.
    
    Operations:
    - Strip whitespace from string columns
    - Convert amount_planned to numeric
    - Parse date columns
    - Handle missing values
    
    Args:
        df: DataFrame with normalized columns
    
    Returns:
        DataFrame with cleaned data types
    """
    df = df.copy()
    
    # Strip whitespace from all string columns
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].astype(str).str.strip()
            # Replace 'nan' strings with actual NaN
            df[col] = df[col].replace(['nan', 'None', 'NaN', ''], np.nan)
    
    # Clean amount column
    if "amount_planned" in df.columns:
        df["amount_planned"] = _clean_numeric_column(df["amount_planned"])
    
    # Clean date columns
    for date_col in ["start_date", "end_date"]:
        if date_col in df.columns:
            df[date_col] = _parse_date_column(df[date_col])
    
    # Clean budget_code - remove extra whitespace, standardize format
    if "budget_code" in df.columns:
        df["budget_code"] = df["budget_code"].astype(str).str.strip()
        df["budget_code"] = df["budget_code"].str.upper()  # Standardize to uppercase
    
    return df


def _clean_numeric_column(series: pd.Series) -> pd.Series:
    """
    Clean a numeric column by removing non-numeric characters.
    
    Handles:
    - Comma separators (1,000,000 -> 1000000)
    - Currency symbols (₮, $, etc.)
    - Whitespace
    - Parentheses for negatives: (100) -> -100
    
    Args:
        series: Pandas Series with numeric data as strings
    
    Returns:
        Series with clean float values
    """
    # Convert to string
    cleaned = series.astype(str)
    
    # Remove currency symbols and whitespace
    cleaned = cleaned.str.replace(r'[₮$€¥\s]', '', regex=True)
    
    # Remove thousands separators (commas and spaces)
    cleaned = cleaned.str.replace(',', '')
    cleaned = cleaned.str.replace(' ', '')
    
    # Handle parentheses as negative: (100) -> -100
    def convert_parens(val):
        if pd.isna(val) or val in ['nan', 'None', '']:
            return np.nan
        val = str(val).strip()
        if val.startswith('(') and val.endswith(')'):
            return '-' + val[1:-1]
        return val
    
    cleaned = cleaned.apply(convert_parens)
    
    # Convert to numeric
    return pd.to_numeric(cleaned, errors='coerce')


def _parse_date_column(series: pd.Series) -> pd.Series:
    """
    Parse date column supporting multiple formats.
    
    Supported formats:
    - YYYY-MM-DD
    - DD/MM/YYYY
    - DD.MM.YYYY (common in Mongolia)
    - Excel serial dates
    
    Args:
        series: Pandas Series with date strings
    
    Returns:
        Series with datetime values
    """
    # Try pandas automatic parsing first
    try:
        # dayfirst=True because DD/MM/YYYY is common in Asia
        return pd.to_datetime(series, dayfirst=True, errors='coerce')
    except Exception:
        pass
    
    # Manual parsing for stubborn formats
    def parse_single_date(val):
        if pd.isna(val) or val in ['nan', 'None', '', 'NaT']:
            return pd.NaT
        
        val = str(val).strip()
        
        # Try common formats
        formats = [
            '%Y-%m-%d',
            '%d/%m/%Y',
            '%d.%m.%Y',
            '%Y/%m/%d',
            '%d-%m-%Y',
            '%m/%d/%Y',
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(val, fmt)
            except ValueError:
                continue
        
        # Try Excel serial date (days since 1899-12-30)
        try:
            serial = float(val)
            if 1 < serial < 100000:  # Reasonable date range
                return pd.Timestamp('1899-12-30') + pd.Timedelta(days=serial)
        except ValueError:
            pass
        
        return pd.NaT
    
    return series.apply(parse_single_date)


# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================

def validate_dataframe(df: pd.DataFrame) -> List[str]:
    """
    Validate a processed DataFrame for data quality issues.
    
    Checks:
    - Required columns have values
    - Amount values are positive
    - Dates are in reasonable range
    - No duplicate budget codes
    
    Args:
        df: Processed DataFrame
    
    Returns:
        List of validation warnings/errors
    """
    issues = []
    
    # Check for empty required fields
    for col in REQUIRED_COLUMNS:
        if col in df.columns:
            null_count = df[col].isna().sum()
            if null_count > 0:
                issues.append(f"Column '{col}' has {null_count} empty values")
    
    # Check amount values
    if "amount_planned" in df.columns:
        negative_count = (df["amount_planned"] < 0).sum()
        if negative_count > 0:
            issues.append(f"Found {negative_count} negative amounts")
        
        zero_count = (df["amount_planned"] == 0).sum()
        if zero_count > 0:
            issues.append(f"⚠️ Found {zero_count} zero amounts")
    
    # Check date ranges
    current_year = datetime.now().year
    for date_col in ["start_date", "end_date"]:
        if date_col in df.columns:
            dates = pd.to_datetime(df[date_col], errors='coerce')
            valid_dates = dates.dropna()
            
            if len(valid_dates) > 0:
                min_year = valid_dates.dt.year.min()
                max_year = valid_dates.dt.year.max()
                
                if min_year < current_year - 5:
                    issues.append(f"⚠️ '{date_col}' has dates from {min_year} (very old)")
                if max_year > current_year + 2:
                    issues.append(f"⚠️ '{date_col}' has dates in {max_year} (far future)")
    
    # Check for duplicate budget codes
    if "budget_code" in df.columns:
        duplicates = df["budget_code"].duplicated().sum()
        if duplicates > 0:
            issues.append(f"⚠️ Found {duplicates} duplicate budget codes")
    
    return issues


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_file_preview(
    uploaded_file,
    max_rows: int = 10,
    sheet_name: int = 0
) -> Tuple[pd.DataFrame, int]:
    """
    Get a preview of the file without full processing.
    
    Useful for displaying to users before they confirm upload.
    
    Args:
        uploaded_file: File to preview
        max_rows: Maximum rows to return
        sheet_name: Excel sheet to read
    
    Returns:
        Tuple of (preview DataFrame, total row count)
    """
    try:
        if hasattr(uploaded_file, 'read'):
            uploaded_file.seek(0)
        
        filename = uploaded_file.name if hasattr(uploaded_file, 'name') else str(uploaded_file)
        
        if filename.lower().endswith('.csv'):
            df = pd.read_csv(uploaded_file, nrows=max_rows + 15)
        else:
            df = pd.read_excel(uploaded_file, sheet_name=sheet_name, nrows=max_rows + 15)
        
        # Find header row
        header_row = _find_header_row(df)
        
        if header_row is not None:
            # Re-read with correct header
            if hasattr(uploaded_file, 'read'):
                uploaded_file.seek(0)
            
            if filename.lower().endswith('.csv'):
                df = pd.read_csv(uploaded_file, header=header_row, nrows=max_rows)
            else:
                df = pd.read_excel(uploaded_file, sheet_name=sheet_name, header=header_row, nrows=max_rows)
        
        return df.head(max_rows), len(df)
        
    except Exception as e:
        logger.error(f"Error getting file preview: {str(e)}")
        return pd.DataFrame(), 0


def detect_channel_from_filename(filename: str) -> Optional[str]:
    """
    Attempt to detect channel type from filename.
    
    Examples:
        "TV_Budget_2024.xlsx" -> "TV"
        "ooh_plan_q1.xlsx" -> "OOH"
        "Radio_FM_spots.xlsx" -> "FM"
    
    Args:
        filename: Original filename
    
    Returns:
        Detected channel type or None
    """
    filename_lower = filename.lower()
    
    channel_patterns = {
        "TV": [r'\btv\b', r'television'],
        "FM": [r'\bfm\b', r'\bradio\b'],
        "OOH": [r'\booh\b', r'outdoor', r'billboard'],
        "Digital": [r'digital', r'online', r'web', r'social'],
        "Print": [r'print', r'newspaper', r'magazine'],
        "Event": [r'event', r'activation', r'btl'],
    }
    
    for channel, patterns in channel_patterns.items():
        for pattern in patterns:
            if re.search(pattern, filename_lower):
                return channel
    
    return None


# =============================================================================
# DATAFRAME TO MODEL CONVERSION
# =============================================================================

def dataframe_to_budget_items(
    df: pd.DataFrame,
    file_id: int,
    channel_type: str
) -> List[Dict[str, Any]]:
    """
    Convert a processed DataFrame to list of BudgetItem dictionaries.
    
    This prepares data for bulk insertion into the database.
    
    Args:
        df: Processed and validated DataFrame
        file_id: ID of the parent BudgetFile
        channel_type: Channel type string
    
    Returns:
        List of dictionaries ready for BudgetItem creation
    """
    items = []
    
    # Define the mapping from DataFrame columns to model fields
    field_mapping = {
        "campaign_name": "campaign_name",
        "budget_code": "budget_code",
        "vendor": "vendor",
        "amount_planned": "amount_planned",
        "start_date": "start_date",
        "end_date": "end_date",
        "metric_1": "metric_1",
        "metric_2": "metric_2",
        "metric_3": "metric_3",
        "sub_channel": "sub_channel",
        "description": "description",
        "row_number": "row_number",
    }
    
    for _, row in df.iterrows():
        item = {
            "file_id": file_id,
            "channel": channel_type,
        }
        
        for df_col, model_field in field_mapping.items():
            if df_col in df.columns:
                value = row[df_col]
                # Convert NaN to None for database
                if pd.isna(value):
                    value = None
                # Convert numpy types to Python types
                elif hasattr(value, 'item'):
                    value = value.item()
                # Convert Timestamp to datetime
                elif isinstance(value, pd.Timestamp):
                    value = value.to_pydatetime()
                
                item[model_field] = value
        
        items.append(item)
    
    return items


# =============================================================================
# MAIN - For testing
# =============================================================================

if __name__ == "__main__":
    """
    Test the excel handler with a sample file.
    
    Usage:
        python modules/excel_handler.py path/to/test/file.xlsx TV
    """
    import sys
    
    if len(sys.argv) >= 3:
        file_path = sys.argv[1]
        channel = sys.argv[2]
        
        print(f"Processing: {file_path}")
        print(f"Channel: {channel}")
        print("-" * 50)
        
        df, metadata, errors = process_uploaded_file(file_path, channel)
        
        if df is not None:
            print(f"✅ Success!")
            print(f"Rows: {metadata['row_count']}")
            print(f"Total Amount: {metadata['total_amount']:,.2f}" if metadata['total_amount'] else "N/A")
            print(f"Header found at row: {metadata['header_row']}")
            print(f"Processing time: {metadata['processing_time']:.2f}s")
            print(f"\nColumns: {list(df.columns)}")
            print(f"\nPreview:")
            print(df.head())
            
            # Validate
            issues = validate_dataframe(df)
            if issues:
                print(f"\n⚠️ Validation Issues:")
                for issue in issues:
                    print(f"  - {issue}")
        else:
            print(f"❌ Failed!")
            for error in errors:
                print(f"  - {error}")
    else:
        print("Usage: python excel_handler.py <file_path> <channel_type>")
        print("Example: python excel_handler.py budget.xlsx TV")
