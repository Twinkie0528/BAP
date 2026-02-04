"""
Simple Excel Handler for Budget Platform
=========================================

This module reads Excel files exactly as they are, without any filtering.
Only reads TEMPLATE or гүйцэтгэл sheets.

Author: CPP Development Team
"""

import hashlib
import logging
import re
import warnings
from io import BytesIO
from typing import Tuple, Optional, List, Dict, Any
from datetime import datetime

import pandas as pd
import numpy as np

# Suppress openpyxl Data Validation warnings
warnings.filterwarnings('ignore', message='Data Validation extension is not supported')

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# MAIN PROCESSING FUNCTION
# =============================================================================

def process_uploaded_file(
    uploaded_file,
    budget_type: str,
    sheet_name: str = None
) -> Tuple[Optional[pd.DataFrame], Dict[str, Any], List[str]]:
    """
    Read Excel file exactly as it is from TEMPLATE or гүйцэтгэл sheet.
    
    NO filtering, NO row skipping - just read the exact data.
    
    Args:
        uploaded_file: Streamlit UploadedFile object or file path
        budget_type: Budget type (primary or additional)
        sheet_name: Sheet to process (auto-detect if None)
    
    Returns:
        Tuple of (DataFrame, metadata_dict, errors_list)
    """
    errors = []
    metadata = {
        "filename": None,
        "budget_type": budget_type,
        "sheet_name": None,
        "budget_code": None,
        "row_count": 0,
        "total_amount": None,
        "file_hash": None,
    }
    
    try:
        # Get filename and content
        if hasattr(uploaded_file, 'name'):
            metadata["filename"] = uploaded_file.name
            file_content = uploaded_file.read()
            uploaded_file.seek(0)
        else:
            metadata["filename"] = str(uploaded_file)
            with open(uploaded_file, 'rb') as f:
                file_content = f.read()
        
        # Calculate file hash
        metadata["file_hash"] = hashlib.md5(file_content).hexdigest()
        
        # Check file type
        filename_lower = metadata["filename"].lower()
        if not filename_lower.endswith(('.xlsx', '.xls')):
            errors.append("Зөвхөн Excel файл (.xlsx, .xls) дэмжигдэнэ")
            return None, metadata, errors
        
        # Read Excel file
        try:
            if hasattr(uploaded_file, 'read'):
                uploaded_file.seek(0)
                xl = pd.ExcelFile(uploaded_file)
            else:
                xl = pd.ExcelFile(uploaded_file)
        except Exception as e:
            errors.append(f"Excel файл уншихад алдаа: {str(e)}")
            return None, metadata, errors
        
        # ======================
        # Find the right sheet (TEMPLATE or гүйцэтгэл only)
        # ======================
        
        sheet_names = xl.sheet_names
        target_sheet = None
        
        # Priority keywords for sheets we want
        priority_keywords = ['template', 'гүйцэтгэл']
        # Keywords for sheets we DON'T want
        exclude_keywords = ['general', 'employee', 'target', 'all employee']
        
        for sn in sheet_names:
            sn_lower = sn.lower()
            
            # Skip excluded sheets
            if any(ex in sn_lower for ex in exclude_keywords):
                continue
            
            # Check for priority keywords
            for kw in priority_keywords:
                if kw in sn_lower:
                    target_sheet = sn
                    break
            
            if target_sheet:
                break
        
        # If not found, use first non-excluded sheet
        if target_sheet is None:
            for sn in sheet_names:
                sn_lower = sn.lower()
                if not any(ex in sn_lower for ex in exclude_keywords):
                    target_sheet = sn
                    break
        
        if target_sheet is None:
            target_sheet = sheet_names[0]
        
        metadata["sheet_name"] = target_sheet
        logger.info(f"Reading sheet: {target_sheet}")
        
        # ======================
        # Read the ENTIRE sheet - NO filtering
        # ======================
        
        # Read without any header specification first
        df = pd.read_excel(xl, sheet_name=target_sheet, header=None)
        
        if df.empty:
            errors.append("Sheet хоосон байна")
            return None, metadata, errors
        
        logger.info(f"Raw data shape: {df.shape}")
        
        # Convert all columns to string to avoid Arrow serialization issues
        for col in df.columns:
            df[col] = df[col].apply(lambda x: str(x) if pd.notna(x) else "")
        
        # Set meaningful column names (just col_0, col_1, etc.)
        df.columns = [f"col_{i}" for i in range(len(df.columns))]
        
        # Add row number column at the beginning
        df.insert(0, 'Мөр', range(1, len(df) + 1))
        
        # ======================
        # Extract metadata
        # ======================
        
        metadata["row_count"] = len(df)
        
        # Try to find budget code in first 15 rows
        for idx in range(min(15, len(df))):
            row_text = ' '.join([str(v) for v in df.iloc[idx].values])
            budget_match = re.search(r'[A-Z]\d{4}[A-Z]\d{2}', row_text)
            if budget_match:
                metadata["budget_code"] = budget_match.group()
                break
        
        # Try to calculate total (find column with large numbers)
        try:
            for col in df.columns:
                if col == 'Мөр':
                    continue
                # Try to convert to numeric and sum
                numeric_vals = pd.to_numeric(df[col].str.replace(',', '').str.replace(' ', ''), errors='coerce')
                col_sum = numeric_vals.sum()
                if col_sum > 1000000:  # Likely a budget column
                    metadata["total_amount"] = float(col_sum)
                    break
        except:
            pass
        
        logger.info(f"Successfully read {metadata['row_count']} rows from {target_sheet}")
        
        return df, metadata, errors
        
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        errors.append(f"Боловсруулахад алдаа: {str(e)}")
        return None, metadata, errors


# =============================================================================
# PREVIEW FUNCTION
# =============================================================================

def get_file_preview(uploaded_file, max_rows: int = 20) -> Tuple[pd.DataFrame, List[str]]:
    """
    Get a preview of the uploaded file - exact as is.
    """
    try:
        if hasattr(uploaded_file, 'seek'):
            uploaded_file.seek(0)
        
        xl = pd.ExcelFile(uploaded_file)
        sheet_names = xl.sheet_names
        
        # Find the right sheet
        target_sheet = None
        priority_keywords = ['template', 'гүйцэтгэл']
        exclude_keywords = ['general', 'employee', 'target', 'all']
        
        for sn in sheet_names:
            sn_lower = sn.lower()
            if any(ex in sn_lower for ex in exclude_keywords):
                continue
            for kw in priority_keywords:
                if kw in sn_lower:
                    target_sheet = sn
                    break
            if target_sheet:
                break
        
        if target_sheet is None:
            for sn in sheet_names:
                sn_lower = sn.lower()
                if not any(ex in sn_lower for ex in exclude_keywords):
                    target_sheet = sn
                    break
        
        if target_sheet is None:
            target_sheet = sheet_names[0]
        
        # Read sheet
        df = pd.read_excel(xl, sheet_name=target_sheet, header=None)
        
        # Convert all to string
        for col in df.columns:
            df[col] = df[col].apply(lambda x: str(x) if pd.notna(x) else "")
        
        return df.head(max_rows), sheet_names
        
    except Exception as e:
        logger.error(f"Preview error: {str(e)}")
        return pd.DataFrame(), []


# =============================================================================
# VALIDATION FUNCTION
# =============================================================================

def validate_dataframe(df: pd.DataFrame) -> List[str]:
    """Validate a processed DataFrame. Returns list of warning messages."""
    warnings = []
    
    if df.empty:
        warnings.append("DataFrame хоосон байна")
    
    return warnings


# =============================================================================
# BUDGET ITEMS CONVERSION (for database storage)
# =============================================================================

def dataframe_to_budget_items(
    df: pd.DataFrame,
    file_id: int,
    budget_type: str,
    specialist_username: str
) -> List[Dict[str, Any]]:
    """
    Convert DataFrame rows to BudgetItem dictionaries.
    
    Stores each row as a simple record.
    """
    if not specialist_username:
        raise ValueError("specialist_username is required")
    
    items = []
    
    for idx, row in df.iterrows():
        # Create item with row data
        item = {
            "file_id": file_id,
            "specialist": specialist_username,
            "row_number": row.get('Мөр', idx + 1),
        }
        
        # Store row content as description (concatenate all columns)
        row_content = []
        for col in df.columns:
            if col != 'Мөр':
                val = row[col]
                if pd.notna(val) and str(val).strip():
                    row_content.append(str(val))
        
        item["description"] = " | ".join(row_content[:5])  # First 5 columns
        
        # Try to find amount
        for col in df.columns:
            try:
                val = str(row[col]).replace(',', '').replace(' ', '')
                num_val = float(val)
                if num_val > 10000:  # Likely a budget amount
                    item["amount_planned"] = num_val
                    break
            except:
                continue
        
        items.append(item)
    
    return items


# =============================================================================
# LEGACY STUBS
# =============================================================================

def detect_channel_from_filename(filename: str) -> Optional[str]:
    """Legacy function - kept for compatibility."""
    return None
