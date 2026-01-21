"""
Column Mapping Configurations
=============================

This file defines how columns from various Excel files map to our standardized
database schema. Each channel type (TV, OOH, FM, etc.) may have different 
column names in their source files.

IMPORTANT: When you receive a new file format, add its column mappings here.

Author: CPP Development Team
"""

# =============================================================================
# COMMON COLUMN MAPPINGS
# =============================================================================
# These mappings apply to ALL file types - the most frequently used columns
# Format: "source_column_name (lowercase)": "target_standard_name"

COMMON_COLUMN_MAP = {
    # Budget Code variations (English & Mongolian)
    "budget code": "budget_code",
    "budgetcode": "budget_code",
    "төсвийн код": "budget_code",
    "төсвийн_код": "budget_code",
    "код": "budget_code",
    
    # Campaign Name variations
    "campaign name": "campaign_name",
    "campaign": "campaign_name",
    "кампанит ажил": "campaign_name",
    "кампанит": "campaign_name",
    "нэр": "campaign_name",
    "campaign_name": "campaign_name",
    
    # Vendor/Company variations
    "vendor": "vendor",
    "company": "vendor",
    "компани": "vendor",
    "supplier": "vendor",
    "нийлүүлэгч": "vendor",
    "agency": "vendor",
    "агентлаг": "vendor",
    
    # Amount variations
    "amount": "amount_planned",
    "amount_planned": "amount_planned",
    "planned amount": "amount_planned",
    "нийт дүн": "amount_planned",
    "дүн": "amount_planned",
    "төсөв": "amount_planned",
    "budget": "amount_planned",
    "total": "amount_planned",
    "нийт": "amount_planned",
    "cost": "amount_planned",
    "зардал": "amount_planned",
    
    # Date variations
    "start date": "start_date",
    "start_date": "start_date",
    "эхлэх огноо": "start_date",
    "эхлэх": "start_date",
    "from": "start_date",
    "from date": "start_date",
    
    "end date": "end_date",
    "end_date": "end_date",
    "дуусах огноо": "end_date",
    "дуусах": "end_date",
    "to": "end_date",
    "to date": "end_date",
    
    # Description variations
    "description": "description",
    "тайлбар": "description",
    "note": "description",
    "notes": "description",
    "тэмдэглэл": "description",
    "comment": "description",
}


# =============================================================================
# CHANNEL-SPECIFIC COLUMN MAPPINGS
# =============================================================================
# These map channel-specific columns to our generic metric_1, metric_2 fields
# This allows storing varying data structures in a normalized table

TV_COLUMN_MAP = {
    # TV-specific metrics
    "duration": "metric_1",           # Spot duration (e.g., 30 sec)
    "хугацаа": "metric_1",
    "spot length": "metric_1",
    "секунд": "metric_1",
    
    "frequency": "metric_2",          # Number of airings
    "давтамж": "metric_2",
    "spots": "metric_2",
    "тоо": "metric_2",
    "airings": "metric_2",
    
    "grp": "metric_3",                # Gross Rating Points
    "rating": "metric_3",
    
    "channel name": "sub_channel",    # TV Channel (MNB, TV5, etc.)
    "суваг": "sub_channel",
    "tv channel": "sub_channel",
}

OOH_COLUMN_MAP = {
    # OOH-specific metrics  
    "size": "metric_1",               # Billboard size
    "хэмжээ": "metric_1",
    "dimensions": "metric_1",
    
    "quantity": "metric_2",           # Number of billboards
    "qty": "metric_2",
    "тоо хэмжээ": "metric_2",
    "ширхэг": "metric_2",
    "count": "metric_2",
    
    "location": "sub_channel",        # Physical location
    "байршил": "sub_channel",
    "address": "sub_channel",
    "хаяг": "sub_channel",
}

FM_COLUMN_MAP = {
    # FM/Radio-specific metrics
    "duration": "metric_1",           # Spot duration
    "хугацаа": "metric_1",
    "length": "metric_1",
    
    "frequency": "metric_2",          # Number of airings
    "давтамж": "metric_2",
    "spots per day": "metric_2",
    
    "station": "sub_channel",         # Radio station name
    "станц": "sub_channel",
    "radio": "sub_channel",
}

DIGITAL_COLUMN_MAP = {
    # Digital-specific metrics
    "impressions": "metric_1",        # Ad impressions
    "харагдалт": "metric_1",
    "views": "metric_1",
    
    "clicks": "metric_2",             # Click count
    "click": "metric_2",
    "дарах": "metric_2",
    
    "platform": "sub_channel",        # Platform (Facebook, Google, etc.)
    "платформ": "sub_channel",
    "media": "sub_channel",
}

PRINT_COLUMN_MAP = {
    # Print-specific metrics
    "size": "metric_1",               # Ad size (full page, half, etc.)
    "хэмжээ": "metric_1",
    
    "insertions": "metric_2",         # Number of insertions
    "тоо": "metric_2",
    "issues": "metric_2",
    
    "publication": "sub_channel",     # Newspaper/magazine name
    "сонин": "sub_channel",
    "сэтгүүл": "sub_channel",
}

EVENT_COLUMN_MAP = {
    # Event-specific metrics
    "attendees": "metric_1",          # Expected attendance
    "оролцогчид": "metric_1",
    "capacity": "metric_1",
    
    "days": "metric_2",               # Event duration in days
    "өдөр": "metric_2",
    
    "venue": "sub_channel",           # Event venue
    "байршил": "sub_channel",
    "location": "sub_channel",
}


# =============================================================================
# MASTER MAPPING DICTIONARY
# =============================================================================
# Access channel-specific mappings by channel type

CHANNEL_SPECIFIC_MAPS = {
    "TV": TV_COLUMN_MAP,
    "FM": FM_COLUMN_MAP,
    "OOH": OOH_COLUMN_MAP,
    "Digital": DIGITAL_COLUMN_MAP,
    "Print": PRINT_COLUMN_MAP,
    "Event": EVENT_COLUMN_MAP,
    "Other": {},  # No specific mappings for "Other"
}


# =============================================================================
# METRIC LABELS BY CHANNEL
# =============================================================================
# Human-readable labels for metric_1, metric_2, metric_3 by channel
# Used in the UI to show what each metric means

METRIC_LABELS = {
    "TV": {
        "metric_1": "Duration (sec)",
        "metric_2": "Frequency (spots)",
        "metric_3": "GRP",
        "sub_channel": "TV Channel",
    },
    "FM": {
        "metric_1": "Duration (sec)",
        "metric_2": "Frequency (spots)",
        "metric_3": None,
        "sub_channel": "Radio Station",
    },
    "OOH": {
        "metric_1": "Size",
        "metric_2": "Quantity",
        "metric_3": None,
        "sub_channel": "Location",
    },
    "Digital": {
        "metric_1": "Impressions",
        "metric_2": "Clicks",
        "metric_3": None,
        "sub_channel": "Platform",
    },
    "Print": {
        "metric_1": "Ad Size",
        "metric_2": "Insertions",
        "metric_3": None,
        "sub_channel": "Publication",
    },
    "Event": {
        "metric_1": "Attendees",
        "metric_2": "Days",
        "metric_3": None,
        "sub_channel": "Venue",
    },
}


# =============================================================================
# REQUIRED COLUMNS FOR VALIDATION
# =============================================================================
# Minimum required columns after mapping - file is invalid without these

REQUIRED_COLUMNS = [
    "budget_code",
    "campaign_name", 
    "amount_planned",
]

# Optional but recommended columns
RECOMMENDED_COLUMNS = [
    "vendor",
    "start_date",
    "end_date",
]
