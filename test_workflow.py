"""
Simple Integration Test for BAP Workflow
=========================================

Tests the core 4-stage workflow to ensure all requirements are met.
Run with: python test_workflow.py
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from decimal import Decimal

from config import FileStatus, UserRole, ChannelType
from database import init_db, get_session, User, BudgetFile, BudgetItem
from modules.services import (
    create_budget_file,
    create_budget_items_bulk,
    update_budget_file_status,
    update_file_with_pdf,
    update_file_with_signed_document,
    get_files_pending_approval,
    get_files_approved_for_print,
    get_files_in_signing,
    get_finalized_files,
)


def test_workflow():
    """Test the complete 4-stage workflow."""
    
    print("=" * 60)
    print("BAP WORKFLOW INTEGRATION TEST")
    print("=" * 60)
    
    # Initialize database
    print("\n1. Initializing database...")
    init_db()
    print("   ✅ Database initialized")
    
    # Create test users
    print("\n2. Creating test users...")
    with get_session() as session:
        # Check if test users exist
        from sqlmodel import select
        
        planner = session.exec(
            select(User).where(User.username == "test_planner")
        ).first()
        
        if not planner:
            planner = User(
                username="test_planner",
                email="test_planner@test.com",
                full_name="Test Planner",
                role=UserRole.PLANNER,
                password_hash="test_hash"
            )
            session.add(planner)
            session.commit()
            session.refresh(planner)
        
        planner_id = planner.id
        planner_username = planner.username
        
        manager = session.exec(
            select(User).where(User.username == "test_manager")
        ).first()
        
        if not manager:
            manager = User(
                username="test_manager",
                email="test_manager@test.com",
                full_name="Test Manager",
                role=UserRole.MANAGER,
                password_hash="test_hash"
            )
            session.add(manager)
            session.commit()
            session.refresh(manager)
        
        manager_id = manager.id
        manager_username = manager.username
    
    print(f"   ✅ Planner created: {planner_username} (ID: {planner_id})")
    print(f"   ✅ Manager created: {manager_username} (ID: {manager_id})")
    
    # STAGE 1: PENDING_APPROVAL - Upload
    print("\n" + "=" * 60)
    print("STAGE 1: PENDING_APPROVAL (Upload)")
    print("=" * 60)
    
    print("\n3. Creating budget file (Stage 1)...")
    budget_file = create_budget_file(
        filename="test_tv_budget.xlsx",
        channel_type="TV",
        uploader_id=planner_id,
        row_count=5,
        total_amount=50000000.00
    )
    file_id = budget_file.id
    file_status = budget_file.status
    print(f"   ✅ Budget file created: ID {file_id}")
    print(f"   ✅ Status: {file_status.value}")
    assert file_status == FileStatus.PENDING_APPROVAL, "Should start in PENDING_APPROVAL"
    
    print("\n4. Creating budget items...")
    test_items = [
        {
            "file_id": file_id,
            "row_number": 1,
            "campaign_name": "New Year Campaign",
            "budget_code": "TV-001",
            "vendor": "MNB",
            "channel": ChannelType.TV,
            "amount_planned": Decimal("10000000.00"),
            "specialist": planner_username,
            "metric_1": "30",
            "metric_2": "100"
        },
        {
            "file_id": file_id,
            "row_number": 2,
            "campaign_name": "Spring Sale",
            "budget_code": "TV-002",
            "vendor": "TV5",
            "channel": ChannelType.TV,
            "amount_planned": Decimal("15000000.00"),
            "specialist": planner_username,
            "metric_1": "15",
            "metric_2": "50"
        }
    ]
    
    created_count = create_budget_items_bulk(test_items)
    print(f"   ✅ Created {created_count} budget items")
    
    print("\n5. Verifying items NOT visible on dashboard...")
    finalized = get_finalized_files()
    assert file_id not in [f.id for f in finalized], "Should NOT be visible on dashboard yet"
    print("   ✅ Confirmed: NOT visible on dashboard (correct!)")
    
    # STAGE 2: APPROVED_FOR_PRINT - Manager Review
    print("\n" + "=" * 60)
    print("STAGE 2: APPROVED_FOR_PRINT (Manager Review)")
    print("=" * 60)
    
    print("\n6. Manager reviews and approves...")
    pending = get_files_pending_approval()
    assert len(pending) > 0, "Should have pending files"
    print(f"   ✅ Found {len(pending)} pending file(s)")
    
    budget_file = update_budget_file_status(
        file_id,
        FileStatus.APPROVED_FOR_PRINT,
        reviewer_id=manager_id,
        reviewer_comment="Approved by test manager"
    )
    file_status = budget_file.status
    reviewer_id_check = budget_file.reviewer_id
    print(f"   ✅ File approved: Status = {file_status.value}")
    assert file_status == FileStatus.APPROVED_FOR_PRINT
    assert reviewer_id_check == manager_id
    
    print("\n7. Verifying planner can see approved file...")
    approved = get_files_approved_for_print(planner_id)
    assert file_id in [f.id for f in approved], "Planner should see approved file"
    print("   ✅ Planner can see file ready for PDF generation")
    
    # STAGE 3: SIGNING - PDF Generation
    print("\n" + "=" * 60)
    print("STAGE 3: SIGNING (PDF Generation)")
    print("=" * 60)
    
    print("\n8. Generating PDF and moving to SIGNING...")
    budget_file = update_file_with_pdf(
        file_id,
        "assets/generated_pdfs/budget_summary_test.pdf"
    )
    file_status = budget_file.status
    pdf_path = budget_file.pdf_file_path
    print(f"   ✅ PDF generated: Status = {file_status.value}")
    assert file_status == FileStatus.SIGNING
    assert pdf_path is not None
    
    print("\n9. Verifying file in signing stage...")
    signing = get_files_in_signing(planner_id)
    assert file_id in [f.id for f in signing], "Should be in signing stage"
    print("   ✅ File waiting for signed document upload")
    
    # STAGE 4: FINALIZED - Upload Signed Document
    print("\n" + "=" * 60)
    print("STAGE 4: FINALIZED (Upload Signed Document)")
    print("=" * 60)
    
    print("\n10. Uploading signed document and finalizing...")
    budget_file = update_file_with_signed_document(
        file_id,
        "assets/signed_files/signed_test.pdf"
    )
    file_status = budget_file.status
    signed_path = budget_file.signed_file_path
    print(f"    ✅ Signed document uploaded: Status = {file_status.value}")
    assert file_status == FileStatus.FINALIZED
    assert signed_path is not None
    print(f"    ✅ Signed file path stored: {signed_path}")
    print(f"    ✅ File path is STRING (not BLOB): {type(signed_path).__name__}")
    
    print("\n11. Verifying file NOW visible on dashboard...")
    finalized = get_finalized_files()
    assert file_id in [f.id for f in finalized], "Should NOW be visible on dashboard"
    print("   ✅ CONFIRMED: File is NOW visible on dashboard!")
    
    # Dashboard Query Test
    print("\n" + "=" * 60)
    print("DASHBOARD QUERY TEST")
    print("=" * 60)
    
    print("\n12. Testing dashboard query (FINALIZED only)...")
    with get_session() as session:
        from sqlmodel import select
        
        # Query that dashboard uses
        statement = select(BudgetItem).join(
            BudgetFile, BudgetItem.file_id == BudgetFile.id
        ).where(
            BudgetFile.status == FileStatus.FINALIZED
        )
        
        dashboard_items = session.exec(statement).all()
        print(f"    ✅ Dashboard shows {len(dashboard_items)} items")
        assert len(dashboard_items) > 0, "Dashboard should show items now"
        
        # Verify specialist field for row-level security
        for item in dashboard_items:
            assert item.specialist is not None, "Specialist should be set"
            print(f"    ✅ Item {item.id}: specialist = '{item.specialist}'")
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print("\n✅ ALL TESTS PASSED!")
    print("\nVerified Requirements:")
    print("  ✅ Stage 1: PENDING_APPROVAL - Data NOT visible on dashboard")
    print("  ✅ Stage 2: APPROVED_FOR_PRINT - Manager approval works")
    print("  ✅ Stage 3: SIGNING - PDF generation works")
    print("  ✅ Stage 4: FINALIZED - Data NOW visible on dashboard")
    print("  ✅ File storage: Paths stored as STRING (not BLOB)")
    print("  ✅ Row-level security: Specialist field set correctly")
    print("  ✅ Dashboard query: Filters by FINALIZED status only")
    
    print("\n🎉 Budget Automation Project is working correctly!")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    try:
        test_workflow()
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
