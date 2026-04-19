"""
Generates FINSURE_GUIDE.pdf - the knowledge base consumed by the RAG chatbot.

Run once after installing requirements:
    python app/chatbot/build_guide.py

The PDF is re-created from the structured content below, so editing this file
and re-running is the normal way to refresh what the chatbot knows.
"""

from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak,
)

OUTPUT_PATH = Path(__file__).parent / "tools" / "FINSURE_GUIDE.pdf"


# --------------------------------------------------------------------------
# Content - mirrors the in-app Documentation page plus FAQs and navigation.
# Keep paragraphs short and self-contained so retrieval returns focused chunks.
# --------------------------------------------------------------------------

SECTIONS = [
    (
        "About FINSURE",
        [
            "FINSURE is an intelligent financial-management platform built for freelancers and small business owners. "
            "It automates the tedious work of organising and analysing financial data by extracting information from receipts, "
            "invoices, bank statements and payment screenshots using OCR (Optical Character Recognition) and NLP "
            "(Natural Language Processing).",
            "FINSURE turns uploaded documents into categorised transactions, dashboards and downloadable reports so users can "
            "understand their income, expenses, cash flow and taxable earnings without manual bookkeeping.",
            "Supported users: freelancers and small/medium business owners who need quick, reliable financial insights without "
            "full accounting software.",
        ],
    ),
    (
        "Key Features",
        [
            "Multi-format document processing supporting PDF, JPG, PNG and HEIC files up to 10 MB each.",
            "Automated OCR-based data extraction with 95–99% accuracy on clear documents.",
            "Intelligent transaction categorisation into Income, Expenses and Client Payments using NLP.",
            "Automated financial reports: Income vs Expenses, Tax Summary, Cash Flow Analysis and a simplified Profit & Loss "
            "statement.",
            "Taxable vs non-taxable income classification to simplify tax compliance and filing.",
            "Interactive visual dashboards powered by Apache Superset plus built-in charts for quick trends.",
            "Bank-grade security with Two-Factor Authentication, AES-256 encryption at rest, and TLS encryption in transit.",
        ],
    ),
    (
        "Dashboard Overview",
        [
            "After logging in the user lands on the Dashboard. It shows four summary cards at the top.",
            "Total Income card: the sum of all income transactions for the selected period.",
            "Total Expenses card: the sum of all expense transactions for the selected period.",
            "Net Profit card: Total Income minus Total Expenses.",
            "Taxable Income card: income automatically classified as taxable based on category and rules.",
            "Below the cards users see Recent Uploads (latest files with status) and an Activity Feed summarising recent actions.",
            "Navigation: the Dashboard is reachable from the sidebar item labelled 'Dashboard' or by visiting /dashboard.",
        ],
    ),
    (
        "Uploading Documents",
        [
            "Open the Upload page from the sidebar 'Upload' item or the Upload button in the top-right of any page.",
            "Two ways to submit files: drag-and-drop directly onto the upload area, or click the area to open a native file picker.",
            "Supported file formats: PDF (digital or scanned statements, invoices, receipts), JPG/JPEG (photos of receipts), "
            "PNG (screenshots of digital transactions) and HEIC (iPhone photos).",
            "Maximum file size is 10 MB per file. Larger files should be compressed or split before upload.",
            "Before extraction starts, FINSURE scans every file for malware and security threats.",
            "During processing FINSURE runs OCR to pull text, analyses layout to locate transaction tables, applies NLP to "
            "categorise each line, and stores validated rows in the user's secure database.",
            "Tips for best results: use clear well-lit photos, keep documents flat, avoid shadows and creases, and upload "
            "multiple documents at once for batch processing.",
            "If a bank statement is password-protected, the Upload form asks for the password so FINSURE can open the PDF.",
        ],
    ),
    (
        "Extraction Review",
        [
            "After upload completes, open the Extraction Review page to verify the data FINSURE extracted before it is saved "
            "permanently. Reach it from the sidebar 'Extraction' item or /extracted.",
            "The review table has these columns: Date (YYYY-MM-DD), Description (payee or payer), Amount "
            "(green for income, red for expense), Category (income, rent, software, utilities, etc.), Taxable (Yes/No), "
            "and Actions (edit icon).",
            "To edit a transaction: click the pencil icon in the Actions column, modify any field, then press Save Changes to "
            "persist the edit.",
            "Bulk actions are available above the table - select multiple rows to edit category or taxable status in one go.",
            "Export options: click Export CSV to download all transactions in a spreadsheet-friendly format, or click Save Changes "
            "to finalise and store the transactions.",
            "Always double-check amounts and dates because OCR can misread digits on low-quality scans. Verify category "
            "assignments to keep reports accurate and check the taxable flag for tax compliance.",
        ],
    ),
    (
        "Upload History",
        [
            "The Upload History page, at /history in the sidebar, lists every document the user has uploaded.",
            "Each document card displays the original filename, the upload date and time, the number of transactions extracted, "
            "the total amount, a document-type badge (Invoice, Receipt, Bank Statement) and a status badge.",
            "Status values: Processing (yellow - file is still being analysed), Completed (green - extraction finished and data is "
            "ready), Failed (red - processing error, user should try re-uploading).",
            "Filters: click the Filters button to narrow the list by document type, date range or status.",
            "Pagination: use the Previous and Next buttons at the bottom of the list to move between pages.",
        ],
    ),
    (
        "Generated Reports",
        [
            "FINSURE generates four professional reports from the categorised transactions. Open them from the Reports page "
            "in the sidebar or /reports.",
            "Income vs Expense Report: compares total income against total expenses for a period and shows net profit or loss.",
            "Tax Summary Report: breaks down taxable vs non-taxable income to simplify tax filing.",
            "Cash Flow Analysis: tracks money flowing in and out of the business over time, highlighting trends and patterns.",
            "Profit and Loss Statement (simplified): a plain-language P&L showing revenue, expenses and profitability without "
            "complex accounting jargon.",
            "To generate a new report: click the '+ Generate Report' button, choose the report type and a date range, then let "
            "FINSURE compile the data and produce a downloadable PDF.",
            "To view an existing report click 'View Report' on its card. Use the share icon to download or share it.",
            "Reports are designed to be shareable with banks, investors or accountants.",
        ],
    ),
    (
        "Visual Dashboards",
        [
            "The Dashboards page, at /dashboards in the sidebar, provides interactive charts powered by Apache Superset.",
            "Monthly Income vs Expenses chart: a bar chart comparing income (cyan bars) and expenses (dark blue bars) month by "
            "month. Hovering over a bar shows exact amounts.",
            "Cash Flow Trend Line: a line chart showing cash flow trends over weekly periods, useful for forecasting and spotting "
            "cash shortages. Interactive points reveal exact weekly values.",
            "For advanced analytics click 'Connect to Apache Superset' to open the full dashboard suite where users can build "
            "custom dashboards, write queries and share interactive boards with team members.",
            "Dashboards update automatically as new transactions are added, so users should check them regularly to spot spending "
            "patterns and seasonal variations.",
        ],
    ),
    (
        "Account Settings",
        [
            "The Settings page, at /settings in the sidebar, lets users manage their profile and preferences.",
            "Profile Information: update the full name, email address and profile photo. Click Save Changes to apply edits.",
            "Notification Preferences: toggle email notifications for new reports, alerts when a document finishes processing, "
            "and weekly financial summary emails.",
            "Data and Privacy: export all financial data in CSV or JSON, configure how long FINSURE retains transaction data, or "
            "permanently delete the account along with its data.",
            "Password changes and 2FA setup live in the separate Security page described below.",
        ],
    ),
    (
        "Security Features",
        [
            "Security settings live at /security in the sidebar. FINSURE uses multiple layers of protection for financial data.",
            "Two-Factor Authentication (2FA): open Security, click Enable 2FA, scan the QR code with an authenticator app "
            "(Google Authenticator, Authy, Microsoft Authenticator), then enter the verification code. After setup every login "
            "requires the password plus a six-digit code.",
            "Active Session Management: view every device currently logged into the account with location information. The "
            "current session is marked as Active. Users can instantly log out any suspicious session.",
            "Encryption: all stored data is encrypted at rest with AES-256 bank-grade encryption; all network traffic uses TLS/SSL.",
            "Every uploaded file is scanned for malware and OCR runs inside a sandboxed environment so raw document contents are "
            "never exposed through dashboards - only summarised insights are shared.",
            "Security best practices: enable 2FA, use a strong unique password, log out from shared or public devices, and review "
            "active sessions periodically.",
        ],
    ),
    (
        "Frequently Asked Questions",
        [
            "Q: Which file formats does FINSURE accept? A: PDF, JPG/JPEG, PNG and HEIC, up to 10 MB per file.",
            "Q: How accurate is the extraction? A: FINSURE achieves 95–99% accuracy on clear, well-lit documents. Blurry photos "
            "or faded receipts reduce accuracy, which is why the Extraction Review step exists.",
            "Q: Can I edit the extracted data? A: Yes. Open Extraction Review, click the pencil icon on a row, change any field, "
            "then Save Changes.",
            "Q: Can FINSURE handle password-protected bank statements? A: Yes. The Upload page has a password field that FINSURE "
            "uses to open the PDF before running OCR.",
            "Q: Can I export my data? A: Yes. Export transactions as CSV from the Extraction Review page, or export all financial "
            "data as CSV or JSON from Settings → Data and Privacy.",
            "Q: Is my financial data safe? A: Data is encrypted at rest with AES-256 and in transit with TLS. Files are scanned "
            "for malware and processed in an isolated environment. You can also enable Two-Factor Authentication for your account.",
            "Q: How do I generate a tax report? A: Open Reports, click '+ Generate Report', choose 'Tax Summary Report', pick the "
            "date range and download the generated PDF.",
            "Q: How do I delete my account? A: Go to Settings → Data and Privacy → Delete Account. This permanently removes the "
            "account and all stored data.",
        ],
    ),
    (
        "Navigation Summary",
        [
            "Sidebar items (protected app): Dashboard, Upload, Extraction, History, Reports, Dashboards, Settings, Security, "
            "Help, Documentation.",
            "Public pages (before login): Landing (/), Quickstart (/quickstart), Pricing (/pricing), FAQs (/faqs), Login (/login), "
            "Signup (/signup).",
            "Top bar: global search, notifications bell, and the user profile menu with a Logout option.",
            "Mobile: a bottom navigation bar mirrors the main sidebar items so the app remains reachable on small screens.",
        ],
    ),
]


def build() -> Path:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "FinsureTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=26,
        spaceAfter=6 * mm,
        alignment=TA_LEFT,
        textColor="#0ab6ff",
    )
    heading_style = ParagraphStyle(
        "FinsureHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        spaceBefore=6 * mm,
        spaceAfter=2 * mm,
        textColor="#14354a",
    )
    body_style = ParagraphStyle(
        "FinsureBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10.5,
        leading=15,
        spaceAfter=3 * mm,
        alignment=TA_LEFT,
    )

    doc = SimpleDocTemplate(
        str(OUTPUT_PATH),
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title="FINSURE Product Guide",
        author="FINSURE",
    )

    story = [
        Paragraph("FINSURE Product Guide", title_style),
        Paragraph(
            "This guide is the knowledge base used by the in-app FINSURE assistant. "
            "It covers what FINSURE is, how to use every page in the app, and answers common questions.",
            body_style,
        ),
        Spacer(1, 4 * mm),
    ]

    for i, (heading, paragraphs) in enumerate(SECTIONS):
        story.append(Paragraph(heading, heading_style))
        for para in paragraphs:
            story.append(Paragraph(para, body_style))
        if i != len(SECTIONS) - 1:
            story.append(Spacer(1, 2 * mm))

    story.append(PageBreak())
    story.append(Paragraph("End of Guide", heading_style))
    story.append(
        Paragraph(
            "Re-generate this PDF after editing build_guide.py by running: "
            "<font face='Courier'>python app/chatbot/build_guide.py</font>",
            body_style,
        )
    )

    doc.build(story)
    return OUTPUT_PATH


if __name__ == "__main__":
    path = build()
    print(f"Wrote {path}")
