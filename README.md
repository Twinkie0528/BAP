# Budget Automation Platform (BAP)

A web-based system for automating the verification and archiving of marketing budgets with a strict 4-stage workflow.

## Overview

The Budget Automation Platform transforms disjointed Excel-based budget planning into a streamlined digital workflow with complete audit trails, electronic signatures, and centralized analytics.

### Key Features

- **4-Stage Workflow**: Structured approval process from upload to finalization
- **Multi-Channel Support**: TV, OOH, FM, Digital, Print, and Event budgets
- **Smart Excel Processing**: Automatic header detection and column normalization
- **Row-Level Security**: Users can only edit their own budget entries
- **Disk-based Storage**: Signed documents stored on disk (not in database)
- **Interactive Dashboard**: View and edit finalized budgets with AgGrid
- **PDF Generation**: Automatic generation of printable budget summaries

## The 4-Stage Workflow

### Stage 1: PENDING_APPROVAL (Upload)
- **Actor**: Planner
- **Action**: Upload Excel/CSV budget file
- **Result**: Data saved to database
- **Visibility**: ⚠️ NOT visible on Main Dashboard

### Stage 2: APPROVED_FOR_PRINT (Manager Review)
- **Actor**: Manager
- **Action**: Review and approve/reject budget
- **Result**: Planner can generate PDF summary
- **Visibility**: Still not visible on dashboard

### Stage 3: SIGNING (Offline Process)
- **Actor**: Planner
- **Actions**:
  1. Download system-generated PDF
  2. Print document
  3. Obtain physical signatures/stamps
  4. Scan signed document
  5. Upload scanned file
- **Result**: Ready for finalization
- **Visibility**: Still not visible on dashboard

### Stage 4: FINALIZED (Archiving)
- **Actor**: Planner
- **Action**: Click "Finalize" button
- **Result**: ✅ Data NOW appears on Main Analytics Dashboard
- **Storage**: Signed document path stored in database, file on disk

## Technical Architecture

### Technology Stack

- **Frontend**: Streamlit
- **Data Grid**: Streamlit-AgGrid (with JsCode for row-level security)
- **Backend**: Python 3.9+
- **Database**: SQLModel (supports SQLite & PostgreSQL)
- **Excel Processing**: Pandas, openpyxl
- **PDF Generation**: reportlab
- **Authentication**: bcrypt

### Project Structure

```
BAP/
├── app.py                          # Main application entry point
├── config.py                       # Configuration and enums
├── requirements.txt                # Python dependencies
├── database/
│   ├── models.py                   # SQLModel database models
│   └── connection.py               # Database connection management
├── modules/
│   ├── auth.py                     # Authentication utilities
│   ├── services.py                 # Business logic and CRUD operations
│   ├── excel_handler.py            # Excel/CSV processing
│   ├── file_storage.py             # Disk-based file storage
│   └── pdf_generator.py            # PDF generation for printing
├── mappings/
│   └── column_maps.py              # Excel column name mappings
├── pages/
│   ├── 1_🔄_Workflow.py            # Workflow management (all 4 stages)
│   ├── 2_📤_Upload.py              # Budget file upload
│   └── 3_📊_Dashboard.py           # Analytics dashboard with AgGrid
└── assets/
    ├── signed_files/               # Uploaded signed documents
    └── generated_pdfs/             # System-generated PDFs
```

### Database Schema

#### User Table
- username, email, full_name
- role (planner/manager/admin)
- password_hash

#### BudgetFile Table
- filename, channel_type, status
- uploader_id, reviewer_id
- uploaded_at, reviewed_at, finalized_at
- pdf_file_path, signed_file_path
- row_count, total_amount

#### BudgetItem Table
- file_id (FK to BudgetFile)
- campaign_name, budget_code, vendor
- channel, sub_channel
- amount_planned, start_date, end_date
- metric_1, metric_2, metric_3 (channel-specific data)
- **specialist** (for row-level security)
- description

## Installation

### Prerequisites

- Python 3.9 or higher
- pip (Python package manager)

### Steps

1. Clone the repository:
```bash
git clone https://github.com/Twinkie0528/BAP.git
cd BAP
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Initialize the database:
```bash
python database/connection.py
```

5. Run the application:
```bash
streamlit run app.py
```

6. Access the application at `http://localhost:8501`

## Configuration

### Database Configuration

Edit `config.py` to switch between SQLite and PostgreSQL:

```python
# For Development (SQLite)
DATABASE_TYPE = "sqlite"

# For Production (PostgreSQL)
DATABASE_TYPE = "postgresql"
POSTGRES_URL = "postgresql://user:password@host:port/database"
```

### File Storage

Signed documents are stored in `assets/signed_files/` by default. Configure in `config.py`:

```python
SIGNED_FILES_DIR = "assets/signed_files"
ALLOWED_SIGNED_FILE_TYPES = [".pdf", ".jpg", ".jpeg", ".png"]
```

## Usage

### Demo Credentials

- **Admin**: `admin` / `admin123`
- **Manager**: `manager` / `manager123`
- **Planner**: `planner` / `planner123`

### Workflow Example

1. **Planner logs in** and navigates to "📤 Upload"
2. **Uploads Excel file** (e.g., TV budget for Q1)
3. File enters **PENDING_APPROVAL** status
4. **Manager logs in** and navigates to "🔄 Workflow"
5. **Reviews and approves** the budget
6. File moves to **APPROVED_FOR_PRINT** status
7. **Planner returns** to "🔄 Workflow"
8. **Generates PDF** for printing
9. File moves to **SIGNING** status
10. **Planner prints, signs, scans** document
11. **Uploads signed scan** in "🔄 Workflow"
12. **Clicks Finalize**
13. File moves to **FINALIZED** status
14. **Budget now visible** on "📊 Dashboard"
15. **Planner can edit** their own rows in the dashboard

## Excel File Format

### Required Columns

- Budget Code
- Campaign Name
- Amount

### Recommended Columns

- Vendor
- Start Date
- End Date

### Channel-Specific Columns

**TV/FM:**
- Duration (maps to metric_1)
- Frequency (maps to metric_2)

**OOH:**
- Size (maps to metric_1)
- Quantity (maps to metric_2)

**Digital:**
- Impressions (maps to metric_1)
- Clicks (maps to metric_2)

### Smart Header Detection

The system automatically:
- Detects the header row (skips metadata rows)
- Maps Mongolian and English column names
- Normalizes data types
- Validates required fields

## Security Features

### Row-Level Security

Dashboard uses AgGrid JsCode to enforce:
- Users can only **edit** rows where `specialist == current_user`
- All other rows are **read-only**
- Visual indicators (green = editable, gray = read-only)
- Backend verification before saving changes

### Authentication

- bcrypt password hashing
- Session-based authentication
- Role-based access control (Planner/Manager/Admin)

### File Storage

- Signed documents stored on disk (not in database)
- Prevents database bloat
- File paths stored as strings in database
- Proper file naming with timestamps

## Dashboard Features

### Visibility Rules

- Shows **ONLY** data where `status = FINALIZED`
- Global visibility: All users can view all finalized data
- Edit restrictions: Users can only edit their own entries

### Interactive Grid

- Sortable and filterable columns
- Inline editing for authorized rows
- Pagination (20 rows per page)
- Export capabilities
- Real-time validation

### Analytics

- Summary metrics by channel
- Monthly budget trends
- Campaign tracking
- Vendor analysis

## Development

### Adding New Channels

1. Add to `ChannelType` enum in `config.py`
2. Add column mappings in `mappings/column_maps.py`
3. Define metric labels for the channel

### Extending Workflow

The workflow is implemented as a state machine in `config.py`:

```python
class FileStatus(str, Enum):
    PENDING_APPROVAL = "pending_approval"
    APPROVED_FOR_PRINT = "approved_for_print"
    SIGNING = "signing"
    FINALIZED = "finalized"
```

Add new statuses and update transition logic in `modules/services.py`.

## Troubleshooting

### Database Connection Issues

```bash
# Test database connection
python database/connection.py
```

### Excel Processing Errors

- Ensure file has a clear header row
- Check for required columns
- Verify data types (numbers, dates)
- Use UTF-8 encoding for CSV files

### PDF Generation Issues

```bash
# Install reportlab if missing
pip install reportlab
```

## License

This project is for internal use by the marketing department.

## Support

For issues and questions, please contact the CPP Development Team.

---

**Version**: 1.0.0  
**Last Updated**: 2024
