"""
PDF Generation for Budget Summaries
===================================

Generates printable PDF summaries from budget data.
Used in the APPROVED_FOR_PRINT -> SIGNING workflow stage.

Author: CPP Development Team
"""

from typing import Optional
from datetime import datetime
import io

try:
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("⚠️ reportlab not installed. PDF generation will not work.")
    print("   Install with: pip install reportlab")

from database import BudgetFile, BudgetItem
from modules.file_storage import get_pdf_path


# =============================================================================
# PDF GENERATION
# =============================================================================

def generate_budget_pdf(
    budget_file: BudgetFile,
    budget_items: list[BudgetItem],
    output_path: Optional[str] = None
) -> tuple[bool, str, Optional[str]]:
    """
    Generate a PDF summary for printing and signing.
    
    Args:
        budget_file: BudgetFile object with metadata
        budget_items: List of BudgetItem objects
        output_path: Optional custom output path (uses default if None)
    
    Returns:
        Tuple of (success: bool, message: str, file_path: str)
    """
    if not REPORTLAB_AVAILABLE:
        return False, "reportlab library not installed", None
    
    try:
        # Get output path
        if output_path is None:
            output_path = get_pdf_path(budget_file.id)
        
        # Create PDF document
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=1*inch,
            bottomMargin=0.75*inch
        )
        
        # Container for elements
        story = []
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1f4788'),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        # ===================
        # HEADER
        # ===================
        
        story.append(Paragraph("ТӨСӨВ БАТЛАХ МАЯГТ", title_style))
        story.append(Spacer(1, 0.2*inch))
        
        # File information
        info_data = [
            ["Файлын ID:", str(budget_file.id)],
            ["Файлын нэр:", budget_file.filename],
            ["Сувaг:", budget_file.channel_type.value],
            ["Хуулсан:", budget_file.uploader.full_name if budget_file.uploader else "Тодорхойгүй"],
            ["Хуулсан огноо:", budget_file.uploaded_at.strftime("%Y-%m-%d %H:%M") if budget_file.uploaded_at else "Байхгүй"],
            ["Нийт зүйл:", str(budget_file.row_count)],
            ["Нийт дүн:", f"₮{float(budget_file.total_amount):,.2f}" if budget_file.total_amount else "Байхгүй"],
        ]
        
        info_table = Table(info_data, colWidths=[2*inch, 4*inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        
        story.append(info_table)
        story.append(Spacer(1, 0.3*inch))
        
        # ===================
        # BUDGET ITEMS TABLE
        # ===================
        
        story.append(Paragraph("<b>Төсвийн мөрүүд:</b>", styles['Heading2']))
        story.append(Spacer(1, 0.1*inch))
        
        # Table headers
        table_data = [
            ["№", "Төсвийн код", "Кампанит ажил", "Нийлүүлэгч", "Дүн (₮)", "Эхлэх огноо"]
        ]
        
        # Add items
        for idx, item in enumerate(budget_items, 1):
            row = [
                str(idx),
                item.budget_code or "",
                item.campaign_name or "",
                item.vendor or "",
                f"{float(item.amount_planned):,.0f}" if item.amount_planned else "0",
                item.start_date.strftime("%Y-%m-%d") if item.start_date else ""
            ]
            table_data.append(row)
        
        # Create table
        items_table = Table(
            table_data,
            colWidths=[0.4*inch, 1.2*inch, 2*inch, 1.5*inch, 1.2*inch, 1*inch]
        )
        
        items_table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            
            # Data rows
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Row number centered
            ('ALIGN', (4, 1), (4, -1), 'RIGHT'),   # Amount right-aligned
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            
            # Alternating row colors
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))
        
        story.append(items_table)
        story.append(Spacer(1, 0.5*inch))
        
        # ===================
        # SIGNATURE SECTION
        # ===================
        
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph("<b>БАТЛАЛУУД:</b>", styles['Heading2']))
        story.append(Spacer(1, 0.2*inch))
        
        signature_data = [
            ["Бэлтгэсэн:", "", "Огноо:", ""],
            ["", "", "", ""],
            ["Гарын үсэг: ___________________", "", "", ""],
            ["", "", "", ""],
            ["Батласан (Менежер):", "", "Огноо:", ""],
            ["", "", "", ""],
            ["Гарын үсэг: ___________________", "", "", ""],
        ]
        
        sig_table = Table(signature_data, colWidths=[2.5*inch, 1.5*inch, 1*inch, 1.5*inch])
        sig_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        story.append(sig_table)
        
        # ===================
        # FOOTER
        # ===================
        
        story.append(Spacer(1, 0.5*inch))
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.grey,
            alignment=TA_CENTER
        )
        
        generated_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        story.append(Paragraph(
            f"Төсвийн автоматжуулалтын платформоос үүсгэсэн {generated_time}",
            footer_style
        ))
        
        # Build PDF
        doc.build(story)
        
        return True, f"PDF generated successfully at {output_path}", output_path
        
    except Exception as e:
        return False, f"Error generating PDF: {str(e)}", None


# =============================================================================
# SIMPLIFIED PDF GENERATION (fallback if reportlab not available)
# =============================================================================

def generate_simple_text_file(
    budget_file: BudgetFile,
    budget_items: list[BudgetItem],
    output_path: str
) -> tuple[bool, str, Optional[str]]:
    """
    Generate a simple text file as fallback when PDF library is not available.
    
    Args:
        budget_file: BudgetFile object
        budget_items: List of BudgetItem objects
        output_path: Output file path
    
    Returns:
        Tuple of (success: bool, message: str, file_path: str)
    """
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("ТӨСӨВ БАТЛАХ МАЯГТ\n")
            f.write("=" * 80 + "\n\n")
            
            f.write(f"Файлын ID: {budget_file.id}\n")
            f.write(f"Файлын нэр: {budget_file.filename}\n")
            f.write(f"Сувaг: {budget_file.channel_type.value}\n")
            f.write(f"Нийт зүйл: {budget_file.row_count}\n")
            f.write(f"Нийт дүн: ₮{float(budget_file.total_amount):,.2f}\n" if budget_file.total_amount else "Нийт дүн: Байхгүй\n")
            f.write("\n" + "-" * 80 + "\n\n")
            
            f.write("ТӨСВИЙН МӨРҮҮД:\n\n")
            
            for idx, item in enumerate(budget_items, 1):
                f.write(f"{idx}. {item.budget_code} - {item.campaign_name}\n")
                f.write(f"   Нийлүүлэгч: {item.vendor or 'Байхгүй'}\n")
                f.write(f"   Дүн: ₮{float(item.amount_planned):,.0f}\n" if item.amount_planned else "   Дүн: Байхгүй\n")
                f.write(f"   Огноо: {item.start_date.strftime('%Y-%m-%d') if item.start_date else 'Байхгүй'}\n")
                f.write("\n")
            
            f.write("\n" + "=" * 80 + "\n")
            f.write("БАТЛАЛУУД:\n\n")
            f.write("Бэлтгэсэн: ___________________  Огноо: ___________\n\n")
            f.write("Батласан (Менежер): ___________________  Огноо: ___________\n\n")
            
        return True, f"Text file generated at {output_path}", output_path
        
    except Exception as e:
        return False, f"Error generating text file: {str(e)}", None


# =============================================================================
# MAIN - For testing
# =============================================================================

if __name__ == "__main__":
    """Test PDF generation."""
    
    print("Testing PDF generation...")
    
    if not REPORTLAB_AVAILABLE:
        print("❌ reportlab not available. Install with: pip install reportlab")
    else:
        print("✅ reportlab is available")
        print("   To test PDF generation, run from Streamlit application")
