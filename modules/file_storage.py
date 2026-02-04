"""
File Storage Utilities for BAP
==============================

Handles storage of signed documents on disk (not in database).
Prevents database bloat from storing large files as BLOBs.

Author: CPP Development Team
"""

import os
import hashlib
from datetime import datetime
from typing import Optional, Tuple
from pathlib import Path

from config import SIGNED_FILES_DIR, ALLOWED_SIGNED_FILE_TYPES


# =============================================================================
# DIRECTORY MANAGEMENT
# =============================================================================

def ensure_storage_directories():
    """
    Create storage directories if they don't exist.
    
    Creates:
        - assets/signed_files/
        - assets/generated_pdfs/
    """
    directories = [
        SIGNED_FILES_DIR,
        "assets/generated_pdfs"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)


# =============================================================================
# SIGNED DOCUMENT STORAGE
# =============================================================================

def save_signed_document(
    uploaded_file,
    file_id: int,
    username: str
) -> Tuple[bool, Optional[str], str]:
    """
    Save uploaded signed document to disk.
    
    Args:
        uploaded_file: Streamlit UploadedFile object
        file_id: BudgetFile ID
        username: Username of uploader
    
    Returns:
        Tuple of (success: bool, file_path: str, message: str)
    """
    try:
        # Ensure directory exists
        ensure_storage_directories()
        
        # Get file extension
        filename = uploaded_file.name
        file_extension = os.path.splitext(filename)[1].lower()
        
        # Validate file type
        if file_extension not in ALLOWED_SIGNED_FILE_TYPES:
            return False, None, f"Invalid file type. Allowed: {ALLOWED_SIGNED_FILE_TYPES}"
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_username = username.replace(" ", "_").replace("/", "_")
        new_filename = f"signed_{file_id}_{safe_username}_{timestamp}{file_extension}"
        
        # Full path
        file_path = os.path.join(SIGNED_FILES_DIR, new_filename)
        
        # Save file
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # Calculate file hash for verification
        file_hash = calculate_file_hash(file_path)
        
        return True, file_path, f"File saved successfully: {new_filename}"
        
    except Exception as e:
        return False, None, f"Error saving file: {str(e)}"


def calculate_file_hash(file_path: str) -> str:
    """Calculate MD5 hash of a file."""
    md5_hash = hashlib.md5()
    
    with open(file_path, "rb") as f:
        # Read in chunks to handle large files
        for chunk in iter(lambda: f.read(4096), b""):
            md5_hash.update(chunk)
    
    return md5_hash.hexdigest()


def delete_signed_document(file_path: str) -> bool:
    """
    Delete a signed document from disk.
    
    Args:
        file_path: Path to file to delete
    
    Returns:
        True if deleted, False otherwise
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False
    except Exception:
        return False


def get_signed_document_info(file_path: str) -> dict:
    """
    Get information about a signed document.
    
    Args:
        file_path: Path to file
    
    Returns:
        Dictionary with file info
    """
    if not os.path.exists(file_path):
        return {
            "exists": False,
            "error": "File not found"
        }
    
    try:
        stat = os.stat(file_path)
        return {
            "exists": True,
            "filename": os.path.basename(file_path),
            "size_bytes": stat.st_size,
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "modified": datetime.fromtimestamp(stat.st_mtime),
        }
    except Exception as e:
        return {
            "exists": False,
            "error": str(e)
        }


# =============================================================================
# PDF GENERATION STORAGE
# =============================================================================

def get_pdf_path(file_id: int) -> str:
    """
    Get the path where a generated PDF should be stored.
    
    Args:
        file_id: BudgetFile ID
    
    Returns:
        Full path for PDF file
    """
    ensure_storage_directories()
    filename = f"budget_summary_{file_id}.pdf"
    return os.path.join("assets/generated_pdfs", filename)


# =============================================================================
# EXCEL FILE STORAGE
# =============================================================================

UPLOADED_FILES_DIR = "assets/uploaded_files"

def save_excel_file(
    uploaded_file,
    file_id: int,
    username: str
) -> Tuple[bool, Optional[str], str]:
    """
    Save uploaded Excel file to disk (exact copy, no modifications).
    
    Args:
        uploaded_file: Streamlit UploadedFile object
        file_id: BudgetFile ID
        username: Username of uploader
    
    Returns:
        Tuple of (success: bool, file_path: str, message: str)
    """
    try:
        # Ensure directory exists
        Path(UPLOADED_FILES_DIR).mkdir(parents=True, exist_ok=True)
        
        # Get original filename
        original_filename = uploaded_file.name
        file_extension = os.path.splitext(original_filename)[1].lower()
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_username = username.replace(" ", "_").replace("/", "_")
        new_filename = f"budget_{file_id}_{safe_username}_{timestamp}{file_extension}"
        
        # Full path
        file_path = os.path.join(UPLOADED_FILES_DIR, new_filename)
        
        # Save file (exact copy)
        uploaded_file.seek(0)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.read())
        
        return True, file_path, f"File saved: {new_filename}"
        
    except Exception as e:
        return False, None, f"Error saving file: {str(e)}"


def get_excel_file_path(file_id: int) -> Optional[str]:
    """
    Find the Excel file for a given file_id.
    
    Args:
        file_id: BudgetFile ID
    
    Returns:
        File path if found, None otherwise
    """
    if not os.path.exists(UPLOADED_FILES_DIR):
        return None
    
    # Look for files matching the pattern
    for filename in os.listdir(UPLOADED_FILES_DIR):
        if filename.startswith(f"budget_{file_id}_"):
            return os.path.join(UPLOADED_FILES_DIR, filename)
    
    return None


def read_excel_file(file_path: str):
    """
    Read an Excel file and return as DataFrame for preview.
    
    Args:
        file_path: Path to Excel file
    
    Returns:
        DataFrame or None
    """
    import pandas as pd
    
    if not os.path.exists(file_path):
        return None
    
    try:
        xl = pd.ExcelFile(file_path)
        
        # Find target sheet
        target_sheet = None
        priority_keywords = ['template', 'гүйцэтгэл']
        exclude_keywords = ['general', 'employee', 'target', 'all']
        
        for sn in xl.sheet_names:
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
            target_sheet = xl.sheet_names[0]
        
        df = pd.read_excel(xl, sheet_name=target_sheet, header=None)
        
        # Format numbers nicely (remove decimals from money)
        for col in df.columns:
            df[col] = df[col].apply(lambda x: format_cell_value(x))
        
        return df
    except Exception as e:
        return None


def format_cell_value(val):
    """Format cell value - clean up money values."""
    import pandas as pd
    
    if pd.isna(val):
        return ""
    
    # If it's a number, format nicely
    if isinstance(val, (int, float)):
        # Large numbers are likely money - format with commas, no decimals
        if abs(val) >= 1000:
            return f"{int(val):,}".replace(",", " ")
        elif val == int(val):
            return str(int(val))
        else:
            return str(val)
    
    return str(val)


def read_excel_file_bytes(file_path: str):
    """
    Read an Excel file and return as bytes for download.
    
    Args:
        file_path: Path to Excel file
    
    Returns:
        File bytes or None
    """
    if not os.path.exists(file_path):
        return None
    
    with open(file_path, "rb") as f:
        return f.read()


def pdf_exists(file_id: int) -> bool:
    """Check if PDF has already been generated for this file."""
    pdf_path = get_pdf_path(file_id)
    return os.path.exists(pdf_path)


def get_preview_pdf_path(file_id: int) -> str:
    """
    Get the path where a preview PDF should be stored.
    
    Args:
        file_id: BudgetFile ID
    
    Returns:
        Full path for preview PDF file
    """
    ensure_storage_directories()
    # Preview PDFs saved in assets/generated_pdfs/previews/
    preview_dir = os.path.join("assets/generated_pdfs", "previews")
    Path(preview_dir).mkdir(parents=True, exist_ok=True)
    filename = f"preview_{file_id}.pdf"
    return os.path.join(preview_dir, filename)


def create_preview_pdf(excel_path: str, file_id: int) -> Optional[str]:
    """
    Create a PDF preview from Excel file.
    
    Args:
        excel_path: Path to Excel file
        file_id: BudgetFile ID
    
    Returns:
        PDF path if successful, None otherwise
    """
    from modules.pdf_converter import convert_excel_to_pdf
    
    if not os.path.exists(excel_path):
        return None
    
    pdf_path = get_preview_pdf_path(file_id)
    
    # Check if preview already exists
    if os.path.exists(pdf_path):
        return pdf_path
    
    # Convert Excel to PDF
    try:
        success = convert_excel_to_pdf(excel_path, pdf_path)
        if success and os.path.exists(pdf_path):
            return pdf_path
    except Exception as e:
        print(f"Error creating preview PDF: {e}")
    
    return None


def read_pdf_as_base64(pdf_path: str) -> Optional[str]:
    """
    Read a PDF file and return as base64 encoded string.
    
    Args:
        pdf_path: Path to PDF file
    
    Returns:
        Base64 encoded string or None
    """
    import base64
    
    if not os.path.exists(pdf_path):
        return None
    
    try:
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
        return base64.b64encode(pdf_bytes).decode('utf-8')
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return None


def preview_pdf_exists(file_id: int) -> bool:
    """Check if preview PDF has already been generated for this file."""
    pdf_path = get_preview_pdf_path(file_id)
    return os.path.exists(pdf_path)


# =============================================================================
# CLEANUP UTILITIES
# =============================================================================

def cleanup_orphaned_files():
    """
    Remove files that don't have corresponding database records.
    
    This is a maintenance function that should be run periodically.
    """
    # This would need to query the database to find orphaned files
    # Left as a placeholder for now
    pass


def get_storage_stats() -> dict:
    """
    Get statistics about file storage usage.
    
    Returns:
        Dictionary with storage statistics
    """
    stats = {
        "signed_files_count": 0,
        "signed_files_size_mb": 0,
        "pdf_files_count": 0,
        "pdf_files_size_mb": 0,
    }
    
    # Count signed files
    if os.path.exists(SIGNED_FILES_DIR):
        for filename in os.listdir(SIGNED_FILES_DIR):
            file_path = os.path.join(SIGNED_FILES_DIR, filename)
            if os.path.isfile(file_path):
                stats["signed_files_count"] += 1
                stats["signed_files_size_mb"] += os.path.getsize(file_path) / (1024 * 1024)
    
    # Count PDF files
    pdf_dir = "assets/generated_pdfs"
    if os.path.exists(pdf_dir):
        for filename in os.listdir(pdf_dir):
            file_path = os.path.join(pdf_dir, filename)
            if os.path.isfile(file_path):
                stats["pdf_files_count"] += 1
                stats["pdf_files_size_mb"] += os.path.getsize(file_path) / (1024 * 1024)
    
    # Round sizes
    stats["signed_files_size_mb"] = round(stats["signed_files_size_mb"], 2)
    stats["pdf_files_size_mb"] = round(stats["pdf_files_size_mb"], 2)
    
    return stats


# =============================================================================
# MAIN - For testing
# =============================================================================

if __name__ == "__main__":
    """Test file storage utilities."""
    
    print("Testing file storage utilities...")
    
    # Ensure directories
    ensure_storage_directories()
    print("✅ Storage directories created")
    
    # Get stats
    stats = get_storage_stats()
    print(f"📊 Storage stats: {stats}")
