import frappe
from frappe.utils.file_manager import save_file
from frappe.utils import cstr, formatdate
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from io import BytesIO
import json
import re


def clean_filename(text):
    """Make filename safe for filesystem"""
    return re.sub(r'[^A-Za-z0-9_-]', '_', cstr(text))


@frappe.whitelist()
def generate_stamped_pdf(doctype, name, print_formats, letterhead=None):

    # Ensure list format
    if isinstance(print_formats, str):
        print_formats = json.loads(print_formats)

    files = []

    doc = frappe.get_doc(doctype, name)

    # Get Delivery Note date safely
    dn_date = None
    if getattr(doc, "delivery_note", None):
        dn_doc = frappe.get_doc("Delivery Note", doc.delivery_note)
        dn_date = formatdate(dn_doc.posting_date, "dd-MM-yyyy")

    # Clean document name once
    safe_name = clean_filename(name)

    for pf in print_formats:

        # 1. Generate PDF from print format
        html = frappe.get_print(
            doctype=doctype,
            name=name,
            print_format=pf,
            letterhead=letterhead,
        )

        pdf_bytes = frappe.utils.pdf.get_pdf(html)

        reader = PdfReader(BytesIO(pdf_bytes))
        writer = PdfWriter()

        # 2. Process pages
        for i, page in enumerate(reader.pages):

            # Skip first page
            if i == 0:
                writer.add_page(page)
                continue

            packet = BytesIO()
            can = canvas.Canvas(packet)

            # Position
            x = page.mediabox.width - 265
            y = page.mediabox.height - 20
            value_x = x + 75

            # Packing Slip
            can.setFont("Helvetica-Bold", 10)
            can.drawString(x, y, "Packing Slip:")

            can.setFont("Helvetica", 10)
            can.drawString(value_x, y, name)

            # Date
            can.setFont("Helvetica-Bold", 9)
            can.drawString(x, y - 12, "Date:")

            can.setFont("Helvetica", 9)
            can.drawString(value_x, y - 12, dn_date or "-")

            can.save()

            packet.seek(0)
            overlay_pdf = PdfReader(packet)

            page.merge_page(overlay_pdf.pages[0])
            writer.add_page(page)

        # 3. Save stamped PDF
        output = BytesIO()
        writer.write(output)

        safe_pf = clean_filename(pf)

        file_doc = save_file(
            fname=f"{safe_name}_{safe_pf}_stamped.pdf",
            content=output.getvalue(),
            dt=doctype,
            dn=name,
            is_private=0
        )

        files.append({
            "file_url": file_doc.file_url,
            "file_name": file_doc.file_name
        })

    return files