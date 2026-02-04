"""
SQLite to PostgreSQL Migration Script
=====================================

This script migrates all data from SQLite to PostgreSQL.
Run this once to transfer all existing data.

Usage:
    python migrate_to_postgres.py
"""

import sqlite3
from sqlmodel import SQLModel, Session, create_engine, select
from database.models import (
    User, BudgetFile, BudgetItem, CppBudgetItem,
    ChannelCategory, ChannelActivity, BudgetCodeRef,
    CampaignType, ProductService, Approver, HeaderTemplate
)

# Database URLs
SQLITE_URL = "sqlite:///./cpp_database.db"
POSTGRES_URL = "postgresql://postgres:0528@localhost:5432/cpp_db"

# Create engines
sqlite_engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})
postgres_engine = create_engine(
    POSTGRES_URL,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True
)


def migrate_table(model_class, sqlite_session, postgres_session):
    """Migrate a single table from SQLite to PostgreSQL."""
    table_name = model_class.__tablename__
    
    try:
        # Get all records from SQLite
        records = sqlite_session.exec(select(model_class)).all()
        count = len(records)
        
        if count == 0:
            print(f"  ⚪ {table_name}: No data to migrate")
            return 0
        
        # Insert into PostgreSQL
        for record in records:
            # Create a new instance with the same data
            data = {}
            for column in record.__table__.columns:
                col_name = column.name
                value = getattr(record, col_name)
                data[col_name] = value
            
            new_record = model_class(**data)
            postgres_session.add(new_record)
        
        postgres_session.commit()
        print(f"  ✅ {table_name}: {count} records migrated")
        return count
        
    except Exception as e:
        postgres_session.rollback()
        print(f"  ❌ {table_name}: Error - {str(e)}")
        return 0


def reset_sequences(postgres_session):
    """Reset PostgreSQL sequences to max ID + 1 for each table."""
    from sqlalchemy import text
    
    tables_with_id = [
        'users', 'budget_files', 'budget_items', 'cpp_budget_items',
        'channel_categories', 'channel_activities', 'budget_code_refs',
        'campaign_types', 'product_services', 'approvers', 'header_templates'
    ]
    
    print("\n🔄 Resetting sequences...")
    for table in tables_with_id:
        try:
            # Get max ID
            result = postgres_session.exec(text(f"SELECT MAX(id) FROM {table}"))
            max_id = result.scalar() or 0
            
            # Reset sequence
            seq_name = f"{table}_id_seq"
            postgres_session.exec(text(f"SELECT setval('{seq_name}', {max_id + 1}, false)"))
            print(f"  ✅ {table}: sequence set to {max_id + 1}")
        except Exception as e:
            print(f"  ⚠️ {table}: {str(e)[:50]}")
    
    postgres_session.commit()


def main():
    print("=" * 60)
    print("🚀 SQLite → PostgreSQL Migration")
    print("=" * 60)
    
    # Check if SQLite database exists
    import os
    if not os.path.exists("cpp_database.db"):
        print("❌ SQLite database not found: cpp_database.db")
        return
    
    print("\n📊 Source: SQLite (cpp_database.db)")
    print("📊 Target: PostgreSQL (cpp_db)")
    
    # Create tables in PostgreSQL
    print("\n🔨 Creating tables in PostgreSQL...")
    SQLModel.metadata.create_all(postgres_engine)
    print("  ✅ Tables created")
    
    # Migration order (respecting foreign keys)
    migration_order = [
        # Independent tables first
        User,
        ChannelCategory,
        BudgetCodeRef,
        CampaignType,
        ProductService,
        Approver,
        HeaderTemplate,
        # Tables with foreign keys
        ChannelActivity,  # depends on ChannelCategory
        BudgetFile,       # depends on User
        BudgetItem,       # depends on BudgetFile
        CppBudgetItem,    # depends on BudgetFile, User
    ]
    
    total_migrated = 0
    
    print("\n📦 Migrating data...")
    
    with Session(sqlite_engine) as sqlite_session:
        with Session(postgres_engine) as postgres_session:
            for model in migration_order:
                count = migrate_table(model, sqlite_session, postgres_session)
                total_migrated += count
            
            # Reset sequences for auto-increment
            reset_sequences(postgres_session)
    
    print("\n" + "=" * 60)
    print(f"✅ Migration Complete! Total records: {total_migrated}")
    print("=" * 60)
    
    # Verify
    print("\n🔍 Verification:")
    with Session(postgres_engine) as session:
        for model in migration_order:
            count = len(session.exec(select(model)).all())
            print(f"  {model.__tablename__}: {count} records")


if __name__ == "__main__":
    main()
