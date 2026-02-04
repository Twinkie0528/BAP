"""
Excel to PDF Converter - Enterprise Standard
=============================================

Native conversion using Microsoft Excel (Windows) or LibreOffice (Linux).
This provides the best quality PDF output with:
- 100% original formatting preserved
- Print areas, margins, fonts, colors, merged cells
- Multi-page pagination with headers
- Searchable vector text (not images)

Author: CPP Development Team
"""

import sys
import os
import platform
import subprocess
import threading
import time
from typing import Optional

# Lock to prevent concurrent Excel access
_excel_lock = threading.Lock()


def convert_excel_to_pdf(
    input_excel_path: str, 
    output_pdf_path: str,
    sheet_name: str = None
) -> bool:
    """
    Excel файлыг PDF болгох Universal функц.
    
    - Windows: MS Excel ашиглана (Best Quality)
    - Linux: LibreOffice ашиглана (Server Standard)
    
    Args:
        input_excel_path: Excel файлын зам
        output_pdf_path: PDF гаралтын зам
        sheet_name: Тодорхой sheet нэр (None бол бүгдийг хөрвүүлнэ)
    
    Returns:
        bool: Амжилттай бол True
    """
    
    # Зам (Path)-ыг бүрэн зам (Absolute path) болгох
    input_path = os.path.abspath(input_excel_path)
    output_path = os.path.abspath(output_pdf_path)
    
    # Output folder байгаа эсэхийг шалгах
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    current_os = platform.system()
    
    print(f"🔄 Converting to PDF on {current_os}...")
    print(f"   Input: {input_path}")
    print(f"   Output: {output_path}")

    # ==========================================
    # WINDOWS SOLUTION (Microsoft Excel)
    # ==========================================
    if current_os == "Windows":
        return _convert_with_excel(input_path, output_path, sheet_name)

    # ==========================================
    # LINUX SOLUTION (LibreOffice)
    # ==========================================
    elif current_os == "Linux":
        return _convert_with_libreoffice(input_path, output_path)
    
    # ==========================================
    # MAC SOLUTION (LibreOffice or Numbers)
    # ==========================================
    elif current_os == "Darwin":
        return _convert_with_libreoffice(input_path, output_path)
            
    print(f"❌ Unsupported OS: {current_os}")
    return False


def _convert_with_excel(
    input_path: str, 
    output_path: str, 
    sheet_name: str = None
) -> bool:
    """
    Microsoft Excel ашиглан PDF болгох (Windows only).
    Хамгийн сайн чанартай output өгнө.
    
    FIT TO PAGE тохиргоотой:
    - Бүх баганыг 1 нүүрэнд багтаана
    - Landscape (хэвтээ) байрлал
    - A4 цаас
    """
    # Lock ашиглаж нэг удаад нэг л Excel process
    with _excel_lock:
        try:
            import pythoncom
            from win32com import client
            
            # COM объектыг эхлүүлэх
            pythoncom.CoInitialize()
            
            excel = None
            wb = None
            
            try:
                # Excel Application-ийг цаана нь чимээгүй нээх
                # DispatchEx ашиглаж шинэ process эхлүүлнэ (Dispatch биш)
                excel = client.DispatchEx("Excel.Application")
                excel.Visible = False
                excel.DisplayAlerts = False
                excel.ScreenUpdating = False
                
                # Calculation, Events-ийг try-except дотор тохируулах
                # (зарим Excel хувилбар дээр workbook нээгдсэний дараа л ажиллана)
                try:
                    excel.EnableEvents = False
                except:
                    pass
                
                # Файлыг нээх - UpdateLinks=0 гэж өгч гадаад линкүүдийг шинэчлэхгүй болгох
                # Энэ нь МААНЙ их хурдасгадаг!
                wb = excel.Workbooks.Open(
                    input_path, 
                    UpdateLinks=0,      # Гадаад линкүүдийг UPDATE хийхгүй
                    ReadOnly=True,      # ReadOnly - илүү хурдан
                    IgnoreReadOnlyRecommended=True
                )
                
                # Workbook нээгдсний дараа Calculation-г унтраах
                try:
                    excel.Calculation = -4135  # xlCalculationManual
                except:
                    pass
                
                # ==========================================
                # Find the target sheet (template sheet)
                # ==========================================
                target_ws = None
                all_sheet_names = []
                
                for i in range(1, wb.Worksheets.Count + 1):
                    ws = wb.Worksheets(i)
                    all_sheet_names.append(ws.Name)
                    
                    # Check if this is the template sheet (without "target")
                    ws_name_lower = ws.Name.lower()
                    if 'template' in ws_name_lower and 'target' not in ws_name_lower:
                        target_ws = ws
                        print(f"   Found clean template: {ws.Name}")
                
                # If not found, try template with "target"
                if target_ws is None:
                    for i in range(1, wb.Worksheets.Count + 1):
                        ws = wb.Worksheets(i)
                        if 'template' in ws.Name.lower():
                            target_ws = ws
                            print(f"   Found template (with target): {ws.Name}")
                            break
                
                # If specific sheet requested, try to find it
                if sheet_name:
                    for i in range(1, wb.Worksheets.Count + 1):
                        ws = wb.Worksheets(i)
                        if ws.Name == sheet_name or sheet_name.lower() in ws.Name.lower():
                            target_ws = ws
                            break
                
                # If no template found, use first sheet
                if target_ws is None:
                    target_ws = wb.Worksheets(1)
                
                print(f"   Using sheet: {target_ws.Name}")
                
                # ==========================================
                # FIT TO SINGLE A4 PAGE - Бүгдийг 1 хуудсанд багтаах
                # ==========================================
                
                # ХУРД: Принтертэй харилцахыг унтраах
                excel.Application.PrintCommunication = False

                try:
                    # 1. Хуучин page break устгах
                    target_ws.ResetAllPageBreaks()

                    # 2. Print Area = UsedRange
                    used_range = target_ws.UsedRange
                    if used_range:
                        target_ws.PageSetup.PrintArea = used_range.Address

                    # 3. БҮГДИЙГ НЭГ ХУУДСАНД БАГТААХ
                    target_ws.PageSetup.Zoom = False
                    target_ws.PageSetup.FitToPagesWide = 1   # Өргөн = 1 хуудас
                    target_ws.PageSetup.FitToPagesTall = 1   # Өндөр = 1 хуудас (БҮГД 1 A4-д!)

                    # 4. Portrait A4 (Босоо)
                    target_ws.PageSetup.Orientation = 1      # 1 = Portrait (Босоо)
                    target_ws.PageSetup.PaperSize = 9

                    # 5. Хамгийн бага margins
                    target_ws.PageSetup.LeftMargin = excel.Application.InchesToPoints(0.1)
                    target_ws.PageSetup.RightMargin = excel.Application.InchesToPoints(0.1)
                    target_ws.PageSetup.TopMargin = excel.Application.InchesToPoints(0.2)
                    target_ws.PageSetup.BottomMargin = excel.Application.InchesToPoints(0.2)
                    target_ws.PageSetup.HeaderMargin = 0
                    target_ws.PageSetup.FooterMargin = 0
                    
                    # 6. Төвлөрүүлэх
                    target_ws.PageSetup.CenterHorizontally = True
                    target_ws.PageSetup.CenterVertically = True

                except Exception as page_err:
                    print(f"⚠️ PageSetup warning: {page_err}")
                
                # Принтер харилцааг буцааж асаах
                excel.Application.PrintCommunication = True
                # ==========================================
                
                # Зөвхөн target sheet-ийг PDF болгох
                target_ws.Select()
                target_ws.ExportAsFixedFormat(
                    Type=0,  # 0 = xlTypePDF
                    Filename=output_path,
                    Quality=0,  # 0 = xlQualityStandard
                    IncludeDocProperties=True,
                    IgnorePrintAreas=False,
                    OpenAfterPublish=False
                )
                
                print(f"✅ PDF created successfully: {output_path}")
                return True
                
            finally:
                # Cleanup - Өөрчлөлтийг хадгалахгүй
                if wb:
                    try:
                        wb.Close(SaveChanges=False)
                    except:
                        pass
                if excel:
                    try:
                        excel.Quit()
                        del excel
                    except:
                        pass
                
                pythoncom.CoUninitialize()
                
        except ImportError:
            print("❌ pywin32 is not installed. Run: pip install pywin32")
            return False
        except Exception as e:
            print(f"❌ Excel conversion failed: {e}")
            return False
        return False
    


def _convert_with_libreoffice(input_path: str, output_path: str) -> bool:
    """
    LibreOffice ашиглан PDF болгох (Linux/Mac).
    Server environment-д тохиромжтой.
    """
    try:
        output_dir = os.path.dirname(output_path)
        input_filename = os.path.basename(input_path)
        expected_pdf_name = os.path.splitext(input_filename)[0] + ".pdf"
        expected_pdf_path = os.path.join(output_dir, expected_pdf_name)
        
        # LibreOffice команд
        command = [
            "libreoffice",
            "--headless",
            "--convert-to", "pdf",
            "--outdir", output_dir,
            input_path
        ]
        
        result = subprocess.run(
            command, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            timeout=120  # 2 минут timeout
        )
        
        if result.returncode == 0:
            # LibreOffice-ийн үүсгэсэн файлыг хүссэн нэр рүү rename хийх
            if expected_pdf_path != output_path and os.path.exists(expected_pdf_path):
                os.rename(expected_pdf_path, output_path)
            
            print(f"✅ PDF created successfully: {output_path}")
            return True
        else:
            print(f"❌ LibreOffice error: {result.stderr.decode()}")
            return False
            
    except FileNotFoundError:
        print("❌ LibreOffice is not installed. Install with: sudo apt install libreoffice")
        return False
    except subprocess.TimeoutExpired:
        print("❌ LibreOffice conversion timed out")
        return False
    except Exception as e:
        print(f"❌ LibreOffice conversion failed: {e}")
        return False


def convert_excel_sheet_to_pdf(
    input_excel_path: str,
    output_pdf_path: str,
    sheet_name: str
) -> bool:
    """
    Тодорхой нэг sheet-ийг PDF болгох.
    
    Args:
        input_excel_path: Excel файлын зам
        output_pdf_path: PDF гаралтын зам
        sheet_name: Sheet нэр
    
    Returns:
        bool: Амжилттай бол True
    """
    return convert_excel_to_pdf(input_excel_path, output_pdf_path, sheet_name)


def get_pdf_as_bytes(excel_path: str, sheet_name: str = None) -> Optional[bytes]:
    """
    Excel-ийг PDF болгоод bytes хэлбэрээр буцаана.
    Streamlit download button-д шууд ашиглахад тохиромжтой.
    
    Args:
        excel_path: Excel файлын зам
        sheet_name: Sheet нэр (optional)
    
    Returns:
        bytes: PDF файлын bytes эсвэл None
    """
    import tempfile
    
    # Temp файл үүсгэх
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        temp_pdf_path = tmp.name
    
    try:
        success = convert_excel_to_pdf(excel_path, temp_pdf_path, sheet_name)
        
        if success and os.path.exists(temp_pdf_path):
            with open(temp_pdf_path, 'rb') as f:
                pdf_bytes = f.read()
            return pdf_bytes
        return None
        
    finally:
        # Cleanup temp file
        if os.path.exists(temp_pdf_path):
            try:
                os.remove(temp_pdf_path)
            except:
                pass


# Test function
if __name__ == "__main__":
    print("PDF Converter Module")
    print(f"Running on: {platform.system()}")
    print("Usage: from modules.pdf_converter import convert_excel_to_pdf")
