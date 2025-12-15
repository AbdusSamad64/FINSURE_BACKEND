from PIL import Image
import pytesseract
import fitz

# def extract_pdf_with_ocr(file_path):
#     text = ""
#     with fitz.open(file_path) as pdf:
#         for page in pdf:
#             # Convert each PDF page to image
#             pix = page.get_pixmap()
#             img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
#             # OCR on the image
#             text += pytesseract.image_to_string(img)
#     return text
# def extract_pdf_with_ocr(file_path):
#     text = ""
#     with fitz.open(file_path) as pdf:
#         for page_num, page in enumerate(pdf, start=1):
#             print(f"Processing page {page_num}/{len(pdf)}...")
            
#             # 1️⃣ Try to get text directly (fast for normal PDFs)
#             page_text = page.get_text().strip()
            
#             if page_text:  
#                 # Page contains real text
#                 text += f"\n--- Page {page_num} ---\n" + page_text
#             else:
#                 # 2️⃣ Page is likely scanned image → use OCR
#                 print(f"Page {page_num} seems scanned. Using OCR...")
#                 pix = page.get_pixmap()
#                 img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
#                 ocr_text = pytesseract.image_to_string(img)
#                 text += f"\n--- Page {page_num} (OCR) ---\n" + ocr_text

#     return text


# my version


# def extract_pdf_with_ocr(file_path, password=None):
#     text = ""
#     pdf = fitz.open(file_path)
    
#     # 🔒 Check if PDF is encrypted
#     if pdf.is_encrypted:
#         print("PDF is encrypted 🔐")
#         if password:
#             # Try to authenticate with password
#             if not pdf.authenticate(password):
#                 raise ValueError("❌ Incorrect password. Unable to open PDF.")
#             print("✅ PDF unlocked successfully!")
#         else:
#             raise ValueError("❌ PDF is password protected. Provide a password to open.")
    
#     # ✅ Now safe to read
#     for page_num, page in enumerate(pdf, start=1):
#         print(f"Processing page {page_num}/{len(pdf)}...")
#         page_text = page.get_text().strip()
#         name="output"+str(page_num)+".txt"
#         # with open(name,"w") as file:
#         with open(name,"w", encoding="utf-8") as file:    
#             file.write(page_text)
#         if page_text:
#             text += f"\n--- Page {page_num} ---\n" + page_text
#         else:
#             print(f"Page {page_num} seems scanned. Using OCR...")
#             pix = page.get_pixmap()
#             img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
#             ocr_text = pytesseract.image_to_string(img)
#             text += f"\n--- Page {page_num} (OCR) ---\n" + ocr_text
#     # with open("output.txt", "w") as file:
#     #     file.write(text)    

#     pdf.close()
#     return text

# version 1 sort

# import fitz
# from PIL import Image
# import pytesseract

# def extract_pdf_with_ocr(file_path, password=None):
#     text = ""
#     pdf = fitz.open(file_path)
    
#     if pdf.is_encrypted:
#         print("PDF is encrypted 🔐")
#         if password:
#             if not pdf.authenticate(password):
#                 raise ValueError("❌ Incorrect password. Unable to open PDF.")
#             print("✅ PDF unlocked successfully!")
#         else:
#             raise ValueError("❌ PDF is password protected. Provide a password to open.")

#     for page_num, page in enumerate(pdf, start=1):
#         print(f"Processing page {page_num}/{len(pdf)} …")
        
#         # Try sorted text extraction
#         page_text = page.get_text("text", sort=True).strip()
#         name = f"output{page_num}.txt"
#         with open(name, "w", encoding="utf-8") as file:
#             file.write(page_text)
        
#         if page_text:
#             text += f"\n--- Page {page_num} ---\n" + page_text
#         else:
#             print(f"Page {page_num} seems scanned or has no extractable text. Using OCR …")
#             pix = page.get_pixmap()
#             img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
#             ocr_text = pytesseract.image_to_string(img)
#             text += f"\n--- Page {page_num} (OCR) ---\n" + ocr_text
    
#     pdf.close()
#     return text

# version 3 blocks

import fitz
from PIL import Image
import pytesseract

def extract_pdf_with_ocr(file_path, password=None):
    text = ""
    pdf = fitz.open(file_path)
    total_no_pages=0 # checks how many no of pages pdf have
    
    # 🔒 Handle encrypted PDFs
    if pdf.is_encrypted:
        print("PDF is encrypted 🔐")
        if password:
            if not pdf.authenticate(password):
                raise ValueError("❌ Incorrect password. Unable to open PDF.")
            print("✅ PDF unlocked successfully!")
        else:
            raise ValueError("❌ PDF is password protected. Provide a password to open.")
    
    # ✅ Process each page
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
# extract_pdf_with_ocr("C:/Users/PMLS/Downloads/noorapi.pdf","0256")

# extract_pdf_with_ocr("C:/Users/PMLS/Downloads/talha2.pdf","1518")