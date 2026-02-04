"""
CRUD Services for Central Planning Platform (CPP)
================================================

This module provides reusable database operations for:
- BudgetFile management
- BudgetItem operations
- User queries

All functions use the session context manager for proper transaction handling.

Author: CPP Development Team
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from decimal import Decimal

from sqlmodel import select, func
from sqlalchemy import and_

from config import FileStatus, UserRole, ChannelType, BudgetType
from database import get_session, User, BudgetFile, BudgetItem


# =============================================================================
# BUDGET FILE OPERATIONS
# =============================================================================

def create_budget_file(
    filename: str,
    budget_type: str,
    uploader_id: int,
    row_count: int = 0,
    total_amount: Optional[float] = None,
    planned_amount: Optional[float] = None,
    file_hash: Optional[str] = None,
    budget_code: Optional[str] = None,
    brand: Optional[str] = None,
    campaign_name: Optional[str] = None,
    specialist_name: Optional[str] = None,
    parent_file_id: Optional[int] = None
) -> BudgetFile:
    """
    Create a new budget file record.
    
    Args:
        filename: Original filename
        budget_type: Budget type (primary or additional)
        uploader_id: ID of the user uploading
        row_count: Number of data rows
        total_amount: Нийт бодит төсөв (actual budget from Excel)
        planned_amount: Нийт төсөв (planned budget from Excel)
        file_hash: MD5 hash for duplicate detection
        budget_code: Budget code from Excel
        brand: Brand name from Excel
        campaign_name: Official campaign name (required for PRIMARY)
        specialist_name: Marketing specialist/planner name
        parent_file_id: Parent PRIMARY file ID (for ADDITIONAL budgets)
    
    Returns:
        Created BudgetFile object with ID
    """
    from datetime import datetime, timezone, timedelta
    mongolia_tz = timezone(timedelta(hours=8))  # UTC+8
    
    with get_session() as session:
        budget_file = BudgetFile(
            filename=filename,
            budget_type=BudgetType(budget_type),
            uploader_id=uploader_id,
            status=FileStatus.PENDING_APPROVAL,  # Start with Stage 1
            row_count=row_count,
            total_amount=Decimal(str(total_amount)) if total_amount else None,
            planned_amount=Decimal(str(planned_amount)) if planned_amount else None,
            file_hash=file_hash,
            budget_code=budget_code,
            brand=brand,
            campaign_name=campaign_name,
            specialist_name=specialist_name,
            parent_file_id=parent_file_id,
            uploaded_at=datetime.now(mongolia_tz).replace(tzinfo=None),
        )
        session.add(budget_file)
        session.commit()
        session.refresh(budget_file)
        return budget_file


def get_budget_file_by_id(file_id: int) -> Optional[BudgetFile]:
    """Get a budget file by its ID."""
    with get_session() as session:
        return session.get(BudgetFile, file_id)


def get_budget_files_by_status(
    status: FileStatus,
    limit: int = 100
) -> List[BudgetFile]:
    """Get all budget files with a specific status."""
    with get_session() as session:
        statement = (
            select(BudgetFile)
            .where(BudgetFile.status == status)
            .order_by(BudgetFile.uploaded_at.desc())
            .limit(limit)
        )
        files = session.exec(statement).all()
        return files


def get_budget_files_by_uploader(
    uploader_id: int,
    limit: int = 50
) -> List[BudgetFile]:
    """Get all budget files uploaded by a specific user."""
    with get_session() as session:
        statement = (
            select(BudgetFile)
            .where(BudgetFile.uploader_id == uploader_id)
            .order_by(BudgetFile.uploaded_at.desc())
            .limit(limit)
        )
        return session.exec(statement).all()


def update_budget_file_status(
    file_id: int,
    new_status: FileStatus,
    reviewer_id: Optional[int] = None,
    reviewer_comment: Optional[str] = None
) -> Optional[BudgetFile]:
    """
    Update the status of a budget file.
    
    Args:
        file_id: ID of the file to update
        new_status: New workflow status
        reviewer_id: ID of the reviewer (for approvals/rejections)
        reviewer_comment: Feedback from reviewer
    
    Returns:
        Updated BudgetFile or None if not found
    """
    with get_session() as session:
        budget_file = session.get(BudgetFile, file_id)
        
        if budget_file:
            budget_file.status = new_status
            
            # Update timestamps based on status
            if new_status == FileStatus.APPROVED_FOR_PRINT:
                budget_file.reviewed_at = datetime.utcnow()
                budget_file.reviewer_id = reviewer_id
                budget_file.reviewer_comment = reviewer_comment
            elif new_status == FileStatus.REJECTED:
                # Store rejection info
                budget_file.reviewed_at = datetime.utcnow()
                budget_file.reviewer_id = reviewer_id
                budget_file.reviewer_comment = reviewer_comment
            elif new_status == FileStatus.SIGNING:
                budget_file.pdf_generated_at = datetime.utcnow()
            elif new_status == FileStatus.FINALIZED:
                budget_file.finalized_at = datetime.utcnow()
                budget_file.published_at = datetime.utcnow()  # Also set published_at for compatibility
            
            session.add(budget_file)
            session.commit()
            session.refresh(budget_file)
        
        return budget_file


def check_duplicate_file(file_hash: str) -> Optional[BudgetFile]:
    """Check if a file with the same hash already exists."""
    with get_session() as session:
        statement = select(BudgetFile).where(BudgetFile.file_hash == file_hash)
        return session.exec(statement).first()


def delete_budget_file(file_id: int) -> bool:
    """
    Delete a budget file and all its items.
    
    Note: This permanently deletes data. Use with caution!
    
    Returns:
        True if deleted, False if not found
    """
    with get_session() as session:
        budget_file = session.get(BudgetFile, file_id)
        
        if budget_file:
            session.delete(budget_file)  # Cascade deletes items
            session.commit()
            return True
        
        return False


# =============================================================================
# BUDGET ITEM OPERATIONS
# =============================================================================

def create_budget_items_bulk(items: List[Dict[str, Any]]) -> int:
    """
    Bulk insert budget items.
    
    Args:
        items: List of dictionaries with item data
    
    Returns:
        Number of items created
    """
    with get_session() as session:
        budget_items = []
        
        for item_data in items:
            # Convert channel string to enum if needed
            if isinstance(item_data.get('channel'), str):
                item_data['channel'] = ChannelType(item_data['channel'])
            
            # Convert amount to Decimal if needed
            if item_data.get('amount_planned') is not None:
                item_data['amount_planned'] = Decimal(str(item_data['amount_planned']))
            
            budget_item = BudgetItem(**item_data)
            budget_items.append(budget_item)
        
        session.add_all(budget_items)
        session.commit()
        
        return len(budget_items)


def get_budget_items_by_file(file_id: int) -> List[BudgetItem]:
    """Get all budget items for a specific file."""
    with get_session() as session:
        statement = (
            select(BudgetItem)
            .where(BudgetItem.file_id == file_id)
            .order_by(BudgetItem.row_number)
        )
        return session.exec(statement).all()


def get_published_items_by_channel(
    channel: ChannelType,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> List[BudgetItem]:
    """
    Get published budget items filtered by channel and date range.
    
    Only returns items from files with FINALIZED status.
    """
    with get_session() as session:
        # First, get finalized file IDs
        finalized_files = (
            select(BudgetFile.id)
            .where(BudgetFile.status == FileStatus.FINALIZED)
        )
        
        # Build query for items
        conditions = [
            BudgetItem.file_id.in_(finalized_files),
            BudgetItem.channel == channel
        ]
        
        if start_date:
            conditions.append(BudgetItem.start_date >= start_date)
        if end_date:
            conditions.append(BudgetItem.end_date <= end_date)
        
        statement = (
            select(BudgetItem)
            .where(and_(*conditions))
            .order_by(BudgetItem.start_date)
        )
        
        return session.exec(statement).all()


# =============================================================================
# DASHBOARD AGGREGATION QUERIES
# =============================================================================

def get_budget_summary_by_channel() -> List[Dict[str, Any]]:
    """
    Get aggregated budget summary grouped by channel.
    
    Returns data for dashboard charts.
    Only includes FINALIZED files.
    """
    with get_session() as session:
        # Only count finalized files
        finalized_files = (
            select(BudgetFile.id)
            .where(BudgetFile.status == FileStatus.FINALIZED)
        )
        
        statement = (
            select(
                BudgetItem.channel,
                func.count(BudgetItem.id).label('item_count'),
                func.sum(BudgetItem.amount_planned).label('total_amount')
            )
            .where(BudgetItem.file_id.in_(finalized_files))
            .group_by(BudgetItem.channel)
        )
        
        results = session.exec(statement).all()
        
        return [
            {
                'channel': row.channel.value if row.channel else 'Unknown',
                'item_count': row.item_count,
                'total_amount': float(row.total_amount) if row.total_amount else 0
            }
            for row in results
        ]


def get_monthly_budget_trend(year: int) -> List[Dict[str, Any]]:
    """
    Get monthly budget totals for a specific year.
    
    Returns data for trend charts.
    Only includes FINALIZED files.
    """
    with get_session() as session:
        finalized_files = (
            select(BudgetFile.id)
            .where(BudgetFile.status == FileStatus.FINALIZED)
        )
        
        # This query gets monthly aggregates
        # Note: Exact syntax may vary for PostgreSQL vs SQLite
        statement = (
            select(
                func.extract('month', BudgetItem.start_date).label('month'),
                func.sum(BudgetItem.amount_planned).label('total_amount')
            )
            .where(
                and_(
                    BudgetItem.file_id.in_(finalized_files),
                    func.extract('year', BudgetItem.start_date) == year
                )
            )
            .group_by(func.extract('month', BudgetItem.start_date))
            .order_by('month')
        )
        
        results = session.exec(statement).all()
        
        return [
            {
                'month': int(row.month),
                'total_amount': float(row.total_amount) if row.total_amount else 0
            }
            for row in results
        ]


# =============================================================================
# USER OPERATIONS
# =============================================================================

def get_user_by_username(username: str) -> Optional[User]:
    """Get user by username."""
    with get_session() as session:
        statement = select(User).where(User.username == username)
        return session.exec(statement).first()


def get_user_by_id(user_id: int) -> Optional[User]:
    """Get user by ID."""
    with get_session() as session:
        return session.get(User, user_id)


def get_users_by_role(role: UserRole) -> List[User]:
    """Get all users with a specific role."""
    with get_session() as session:
        statement = (
            select(User)
            .where(User.role == role)
            .where(User.is_active == True)
        )
        return session.exec(statement).all()


def update_user_last_login(user_id: int) -> None:
    """Update user's last login timestamp."""
    with get_session() as session:
        user = session.get(User, user_id)
        if user:
            user.last_login = datetime.utcnow()
            session.add(user)
            session.commit()


# =============================================================================
# WORKFLOW STATUS COUNTS
# =============================================================================

def get_workflow_status_counts() -> Dict[str, int]:
    """
    Get counts of files in each workflow status.
    
    Returns:
        Dictionary with status names as keys and counts as values
    """
    with get_session() as session:
        statement = (
            select(
                BudgetFile.status,
                func.count(BudgetFile.id).label('count')
            )
            .group_by(BudgetFile.status)
        )
        
        results = session.exec(statement).all()
        
        # Initialize all statuses with 0
        counts = {status.value: 0 for status in FileStatus}
        
        # Update with actual counts
        for row in results:
            counts[row.status.value] = row.count
        
        return counts


# =============================================================================
# 4-STAGE WORKFLOW HELPERS
# =============================================================================

def update_file_with_signed_document(
    file_id: int,
    signed_file_path: str
) -> Optional[BudgetFile]:
    """
    Update budget file with signed document path and move to FINALIZED status.
    
    Args:
        file_id: ID of the file to update
        signed_file_path: Path to the signed document (stored on disk)
    
    Returns:
        Updated BudgetFile or None if not found
    """
    with get_session() as session:
        budget_file = session.get(BudgetFile, file_id)
        
        if budget_file:
            budget_file.signed_file_path = signed_file_path
            budget_file.signed_uploaded_at = datetime.utcnow()
            budget_file.status = FileStatus.FINALIZED
            budget_file.finalized_at = datetime.utcnow()
            budget_file.published_at = datetime.utcnow()
            
            session.add(budget_file)
            session.commit()
            session.refresh(budget_file)
        
        return budget_file


def update_file_with_pdf(
    file_id: int,
    pdf_file_path: str
) -> Optional[BudgetFile]:
    """
    Update budget file with generated PDF path and move to SIGNING status.
    
    Args:
        file_id: ID of the file to update
        pdf_file_path: Path to the generated PDF file
    
    Returns:
        Updated BudgetFile or None if not found
    """
    with get_session() as session:
        budget_file = session.get(BudgetFile, file_id)
        
        if budget_file:
            budget_file.pdf_file_path = pdf_file_path
            budget_file.pdf_generated_at = datetime.utcnow()
            budget_file.status = FileStatus.SIGNING
            
            session.add(budget_file)
            session.commit()
            session.refresh(budget_file)
        
        return budget_file


def get_files_pending_approval(limit: int = 100) -> List[BudgetFile]:
    """Get all files awaiting manager approval (Stage 1)."""
    return get_budget_files_by_status(FileStatus.PENDING_APPROVAL, limit)


def get_files_approved_for_print(uploader_id: int, limit: int = 50) -> List[BudgetFile]:
    """Get files approved for printing for a specific planner (Stage 2)."""
    with get_session() as session:
        statement = (
            select(BudgetFile)
            .where(BudgetFile.status == FileStatus.APPROVED_FOR_PRINT)
            .where(BudgetFile.uploader_id == uploader_id)
            .order_by(BudgetFile.reviewed_at.desc())
            .limit(limit)
        )
        return session.exec(statement).all()


def get_files_in_signing(uploader_id: int, limit: int = 50) -> List[BudgetFile]:
    """Get files in signing stage for a specific planner (Stage 3)."""
    with get_session() as session:
        statement = (
            select(BudgetFile)
            .where(BudgetFile.status == FileStatus.SIGNING)
            .where(BudgetFile.uploader_id == uploader_id)
            .order_by(BudgetFile.pdf_generated_at.desc())
            .limit(limit)
        )
        return session.exec(statement).all()


def get_finalized_files(limit: int = 100) -> List[BudgetFile]:
    """Get all finalized files (Stage 4) visible on dashboard."""
    return get_budget_files_by_status(FileStatus.FINALIZED, limit)
