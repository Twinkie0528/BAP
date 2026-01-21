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

import sys
sys.path.append('..')
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


def pdf_exists(file_id: int) -> bool:
    """Check if PDF has already been generated for this file."""
    pdf_path = get_pdf_path(file_id)
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
