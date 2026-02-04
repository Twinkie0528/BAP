"""
Column Mapping Configurations for MD Budget Templates
======================================================

This file defines how columns from MD Unit Budget Excel files map to our 
standardized database schema.

Template Structure:
- Row 15-17: Header row with columns: №, ИДЭВХЖҮҮЛЭЛТИЙН СУВАГ, ХУГАЦАА, 
  ХАРИУЦАХ ЭЗЭН, ДАВТАМЖ, НЭГЖ ҮНЭ, НИЙТ ТӨСӨВ, ТАЙЛБАР
- Multiple sections: ДИЖИТАЛ СУВАГ, ВЭБСАЙТ СУВАГ, ТВ СУВАГ, etc.

Author: CPP Development Team
"""

# =============================================================================
# MD BUDGET TEMPLATE COLUMN MAPPINGS
# =============================================================================
# Maps columns from MD Unit Budget Excel template to standard database fields

COMMON_COLUMN_MAP = {
    # Row number
    "№": "row_number",
    "no": "row_number",
    "дугаар": "row_number",
    
    # Channel/Activity - ИДЭВХЖҮҮЛЭЛТИЙН СУВАГ
    "идэвхжүүлэлтийн суваг": "activity_channel",
    "суваг": "activity_channel",
    "төрөл": "item_type",
    "type": "item_type",
    
    # Item details
    "хийгдэх ажил": "work_description",
    "ажил": "work_description",
    "дэлгэрэнгүй": "work_description",
    "нөлөөлөгч": "influencer",
    
    # Time/Schedule
    "хугацаа": "schedule",
    "огноо": "schedule",
    "date": "schedule",
    
    # Responsible person
    "хариуцах эзэн": "responsible_person",
    "хариуцагч": "responsible_person",
    "specialist": "responsible_person",
    
    # Quantity/Frequency
    "давтамж": "frequency",
    "тоо ширхэг": "frequency",
    "quantity": "frequency",
    
    # Unit price
    "нэгж үнэ": "unit_price",
    "үнэ": "unit_price",
    "unit price": "unit_price",
    
    # Total budget
    "нийт төсөв": "amount_planned",
    "нийт": "amount_planned",
    "total": "amount_planned",
    "цогц үнэ": "amount_planned",
    "budget": "amount_planned",
    
    # Description/Notes
    "тайлбар": "description",
    "note": "description",
    "notes": "description",
}


# =============================================================================
# SECTION IDENTIFIERS (Channel sections in the Excel)
# =============================================================================
# These keywords identify section headers in the Excel file

SECTION_KEYWORDS = [
    "дижитал сурталчилгааны суваг",
    "вэбсайт сурталчилгааны суваг", 
    "дотоод сурталчилгааны суваг",
    "тв сурталчилгааны суваг",
    "fm сурталчилгааны суваг",
    "гадаа сурталчилгааны суваг",
    "кино театр сурталчилгааны суваг",
    "хоол зогсоол сурталчилгааны суваг",
    "контент хийцлэл",
    "арга хэмжээ",
    "судалгаа",
    "хамтын ажиллагаа",
    "сонин сэтгүүл",
    "бусад",
    # English variations
    "digital", "website", "tv", "fm", "ooh", "outdoor", "event", "content",
]


# =============================================================================
# METADATA EXTRACTION PATTERNS
# =============================================================================
# Patterns to extract metadata from the Excel file header area

METADATA_PATTERNS = {
    "budget_code": r"[A-Z]\d{4}[A-Z]\d{2}",  # e.g., B2504E05
    "marketing_code": r"[A-Z]{2,4}-[A-Z]+-[A-Z0-9]+-\d+",  # e.g., MBD-UNIVISION-MC1-110023
    "date_pattern": r"\d{4}\.\d{2}\.\d{2}",  # e.g., 2025.04.21
}


# =============================================================================
# REQUIRED AND RECOMMENDED COLUMNS
# =============================================================================

REQUIRED_COLUMNS = [
    "amount_planned",  # Must have budget amount
]

RECOMMENDED_COLUMNS = [
    "work_description",
    "responsible_person", 
    "frequency",
    "description",
]


# =============================================================================
# CHANNEL-SPECIFIC COLUMN MAPPINGS (Legacy - for backward compatibility)
# =============================================================================

CHANNEL_SPECIFIC_MAPS = {
    "TV": {},
    "FM": {},
    "OOH": {},
    "Digital": {},
    "Print": {},
    "Event": {},
    "Other": {},
}
