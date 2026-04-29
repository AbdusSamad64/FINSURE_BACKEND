from PIL import Image
import pytesseract
import fitz

# version 3 blocks

import fitz              # part of PyMuPDF to read and handle pdfs
from PIL import Image    # to handle images
import pytesseract

def extract_pdf_with_ocr(file_path, password=None):
    text = ""
    pdf = fitz.open(file_path)
    total_no_pages=0 # checks how many no of pages pdf have
    
    #  Handle encrypted PDFs
    if pdf.is_encrypted:
        print("PDF is encrypted 🔐")
        if password:
            if not pdf.authenticate(password):
                raise ValueError("❌ Incorrect password. Unable to open PDF.")
            print("✅ PDF unlocked successfully!")
        else:
            raise ValueError("❌ PDF is password protected. Provide a password to open.")
    
    #  Process each page
    for page_num, page in enumerate(pdf, start=1):
        print(f"Processing page {page_num}/{len(pdf)}...")

        # --- sort text blocks in reading order ---
        blocks = page.get_text("blocks")  # returns list of tuples (x0, y0, x1, y1, text, block_no, ...)
        blocks = sorted(blocks, key=lambda b: (round(b[1]), round(b[0])))  # sort by y (top→bottom), then x (left→right)
        page_text = "\n".join(block[4].strip() for block in blocks if block[4].strip())

        if not page_text:
            print(f"Page {page_num} seems scanned. Using OCR...")
            pix = page.get_pixmap()
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            page_text = pytesseract.image_to_string(img)

        # Write each page separately
        name = f"output{page_num}.txt"
        with open(name, "w", encoding="utf-8") as file:
            file.write(page_text)
        total_no_pages+=1
        text += f"\n--- Page {page_num} ---\n{page_text}"

    pdf.close()
    return text,total_no_pages


# extract_pdf_with_ocr("C:/Users/PMLS/Downloads/7557476_010795_01-09-2025_30-09-2025.pdf","5074")
# print(extract_pdf_with_ocr("C:/Users/PMLS/Downloads/e-statement-1760797788358.pdf"))

# print(extract_pdf_with_ocr("C:/Users/PMLS/Downloads/statement.pdf"))
# extract_pdf_with_ocr("C:/Users/PMLS/Downloads/statement.pdf")
# extract_pdf_with_ocr("C:/Users/PMLS/Downloads/noorapi_meezan.pdf","0256")

# extract_pdf_with_ocr("C:/Users/PMLS/Downloads/talha2.pdf","1518")

# extract_pdf_with_ocr("D:/Abdullah/FYDP/Bank_Statements/noorapi_meezan.pdf","0256")
# extract_pdf_with_ocr("D:/Abdullah/FYDP/Bank_Statements/ramsha_jan_ubl.pdf")

# extract_pdf_with_ocr("C:/Users/PMLS/Downloads/hussain_meezan_5857.pdf","5857")
# extract_pdf_with_ocr("D:/Abdullah/FYDP/Bank_Statements/samad_meezan.pdf","5074")
# extract_pdf_with_ocr("D:/Abdullah/FYDP/Bank_Statements/saad_dec_alfalah.pdf","136")



# "C:\Users\PMLS\Downloads\hussain_meezan_5857.pdf"