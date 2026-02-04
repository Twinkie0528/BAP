"""
Analytics Service for CPP Dashboard
====================================

This module provides analytics and reporting functions for the
Central Planning Platform (CPP) Dashboard.

Functions:
    - get_budget_summary_by_channel: Budget breakdown by marketing channel
    - get_budget_summary_by_company: Budget breakdown by company
    - get_budget_timeline: Monthly budget trend
    - get_top_campaigns: Top campaigns by budget amount
    - get_cpp_report_data: Full CPP report data for Excel export
"""

from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime
import pandas as pd

from sqlmodel import Session, select, func
from database.models import BudgetFile, BudgetItem
from config import FileStatus


def get_approved_files(session: Session) -> List[BudgetFile]:
    """
    Get all approved budget files.
    Includes files with status: APPROVED_FOR_PRINT, SIGNING, FINALIZED
    Only approved files should appear in Dashboard.
    """
    approved_statuses = [
        FileStatus.APPROVED_FOR_PRINT,
        FileStatus.SIGNING,
        FileStatus.FINALIZED
        # PENDING_APPROVAL and REJECTED are excluded from Dashboard
    ]
    
    query = select(BudgetFile).where(BudgetFile.status.in_(approved_statuses))
    return list(session.exec(query).all())


def get_budget_summary(session: Session) -> Dict[str, Any]:
    """
    Get overall budget summary statistics.
    
    Returns:
        Dict with:
        - total_planned: Total planned budget (НИЙТ ТӨСӨВ)
        - total_actual: Total actual budget (НИЙТ БОДИТ ТӨСӨВ)
        - file_count: Number of approved files
        - avg_budget: Average budget per file
    """
    files = get_approved_files(session)
    
    if not files:
        return {
            'total_planned': Decimal(0),
            'total_actual': Decimal(0),
            'file_count': 0,
            'avg_budget': Decimal(0)
        }
    
    total_planned = sum(f.planned_amount or Decimal(0) for f in files)
    total_actual = sum(f.total_amount or Decimal(0) for f in files)
    
    return {
        'total_planned': total_planned,
        'total_actual': total_actual,
        'file_count': len(files),
        'avg_budget': total_actual / len(files) if files else Decimal(0)
    }


def get_budget_by_company(session: Session) -> pd.DataFrame:
    """
    Get budget breakdown by company.
    Extracts company code from budget_code (first letter: A=Unitel, B=Univision, etc.)
    
    Returns:
        DataFrame with columns: Company, PlannedAmount, ActualAmount, FileCount
    """
    files = get_approved_files(session)
    
    company_map = {
        'A': 'Юнител',
        'B': 'Юнивишн',
        'G': 'Green Future',
        'J': 'IVLBS',
        'T': 'MPSC'
    }
    
    company_data = {}
    
    for f in files:
        if f.budget_code:
            company_code = f.budget_code[0].upper()
            company_name = company_map.get(company_code, f'Other ({company_code})')
            
            if company_name not in company_data:
                company_data[company_name] = {
                    'PlannedAmount': Decimal(0),
                    'ActualAmount': Decimal(0),
                    'FileCount': 0
                }
            
            company_data[company_name]['PlannedAmount'] += f.planned_amount or Decimal(0)
            company_data[company_name]['ActualAmount'] += f.total_amount or Decimal(0)
            company_data[company_name]['FileCount'] += 1
    
    if not company_data:
        return pd.DataFrame(columns=['Company', 'PlannedAmount', 'ActualAmount', 'FileCount'])
    
    df = pd.DataFrame([
        {
            'Company': company,
            'PlannedAmount': float(data['PlannedAmount']),
            'ActualAmount': float(data['ActualAmount']),
            'FileCount': data['FileCount']
        }
        for company, data in company_data.items()
    ])
    
    return df.sort_values('ActualAmount', ascending=False)


def get_budget_by_month(session: Session) -> pd.DataFrame:
    """
    Get budget breakdown by month (based on upload date).
    
    Returns:
        DataFrame with columns: Month, PlannedAmount, ActualAmount, FileCount
    """
    files = get_approved_files(session)
    
    month_data = {}
    
    for f in files:
        month_key = f.uploaded_at.strftime('%Y-%m')
        month_name = f.uploaded_at.strftime('%Y оны %m-р сар')
        
        if month_key not in month_data:
            month_data[month_key] = {
                'MonthName': month_name,
                'PlannedAmount': Decimal(0),
                'ActualAmount': Decimal(0),
                'FileCount': 0
            }
        
        month_data[month_key]['PlannedAmount'] += f.planned_amount or Decimal(0)
        month_data[month_key]['ActualAmount'] += f.total_amount or Decimal(0)
        month_data[month_key]['FileCount'] += 1
    
    if not month_data:
        return pd.DataFrame(columns=['Month', 'MonthName', 'PlannedAmount', 'ActualAmount', 'FileCount'])
    
    df = pd.DataFrame([
        {
            'Month': month,
            'MonthName': data['MonthName'],
            'PlannedAmount': float(data['PlannedAmount']),
            'ActualAmount': float(data['ActualAmount']),
            'FileCount': data['FileCount']
        }
        for month, data in month_data.items()
    ])
    
    return df.sort_values('Month')


def get_top_campaigns(session: Session, limit: int = 10) -> pd.DataFrame:
    """
    Get top campaigns by budget amount.
    
    Returns:
        DataFrame with columns: Campaign, BudgetCode, Company, ActualAmount, PlannedAmount
    """
    files = get_approved_files(session)
    
    company_map = {
        'A': 'Юнител',
        'B': 'Юнивишн',
        'G': 'Green Future',
        'J': 'IVLBS',
        'T': 'MPSC'
    }
    
    campaigns = []
    for f in files:
        # Extract campaign name from filename
        filename = f.filename
        campaign_name = filename
        
        # Try to extract campaign name from filename format: B2504E05_Campaign Name.xlsx
        if '_' in filename:
            parts = filename.split('_', 1)
            if len(parts) > 1:
                campaign_name = parts[1].replace('.xlsx', '').replace('.xls', '')
        
        company_code = f.budget_code[0].upper() if f.budget_code else 'X'
        company_name = company_map.get(company_code, 'Other')
        
        campaigns.append({
            'Campaign': campaign_name,
            'BudgetCode': f.budget_code or 'N/A',
            'Company': company_name,
            'ActualAmount': float(f.total_amount or 0),
            'PlannedAmount': float(f.planned_amount or 0)
        })
    
    if not campaigns:
        return pd.DataFrame(columns=['Campaign', 'BudgetCode', 'Company', 'ActualAmount', 'PlannedAmount'])
    
    df = pd.DataFrame(campaigns)
    df = df.sort_values('ActualAmount', ascending=False).head(limit)
    
    return df


def get_budget_efficiency(session: Session) -> pd.DataFrame:
    """
    Calculate budget efficiency (Actual vs Planned ratio) per file.
    
    Returns:
        DataFrame with columns: Campaign, BudgetCode, Planned, Actual, Efficiency, Status
    """
    files = get_approved_files(session)
    
    data = []
    for f in files:
        planned = float(f.planned_amount or 0)
        actual = float(f.total_amount or 0)
        
        if planned > 0:
            efficiency = (actual / planned) * 100
        else:
            efficiency = 0
        
        # Determine status
        if efficiency == 0:
            status = '⚪ Өгөгдөл байхгүй'
        elif efficiency <= 50:
            status = '🟢 Маш хэмнэлттэй'
        elif efficiency <= 80:
            status = '🟡 Хэвийн'
        elif efficiency <= 100:
            status = '🟠 Хязгаарт ойр'
        else:
            status = '🔴 Хэтрүүлсэн'
        
        # Extract campaign name
        filename = f.filename
        if '_' in filename:
            parts = filename.split('_', 1)
            if len(parts) > 1:
                filename = parts[1].replace('.xlsx', '').replace('.xls', '')
        
        data.append({
            'Campaign': filename[:40] + '...' if len(filename) > 40 else filename,
            'BudgetCode': f.budget_code or 'N/A',
            'Planned': planned,
            'Actual': actual,
            'Efficiency': efficiency,
            'Status': status
        })
    
    if not data:
        return pd.DataFrame(columns=['Campaign', 'BudgetCode', 'Planned', 'Actual', 'Efficiency', 'Status'])
    
    return pd.DataFrame(data).sort_values('Efficiency', ascending=False)


def get_status_distribution(session: Session) -> pd.DataFrame:
    """
    Get distribution of files by workflow status.
    
    Returns:
        DataFrame with columns: Status, Count, StatusName
    """
    query = select(BudgetFile.status, func.count(BudgetFile.id).label('count')).group_by(BudgetFile.status)
    results = session.exec(query).all()
    
    status_names = {
        FileStatus.PENDING_APPROVAL: 'Хүлээгдэж байна',
        FileStatus.APPROVED_FOR_PRINT: 'Батлагдсан',
        FileStatus.SIGNING: 'Гарын үсэг авч байна',
        FileStatus.FINALIZED: 'Дууссан',
    }
    
    data = []
    for status, count in results:
        data.append({
            'Status': status.value if hasattr(status, 'value') else str(status),
            'StatusName': status_names.get(status, str(status)),
            'Count': count
        })
    
    if not data:
        return pd.DataFrame(columns=['Status', 'StatusName', 'Count'])
    
    return pd.DataFrame(data)


def export_cpp_summary(session: Session) -> Dict[str, pd.DataFrame]:
    """
    Export full CPP summary data for Excel/CSV export.
    
    Returns:
        Dict of DataFrames:
        - summary: Overall summary
        - by_company: Breakdown by company
        - by_month: Monthly trend
        - top_campaigns: Top campaigns
        - efficiency: Budget efficiency
    """
    return {
        'summary': pd.DataFrame([get_budget_summary(session)]),
        'by_company': get_budget_by_company(session),
        'by_month': get_budget_by_month(session),
        'top_campaigns': get_top_campaigns(session, limit=20),
        'efficiency': get_budget_efficiency(session)
    }
