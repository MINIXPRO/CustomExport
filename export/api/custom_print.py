import frappe
from frappe.utils.file_manager import save_file
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from io import BytesIO


@frappe.whitelist()
def generate_stamped_pdf(doctype, name, print_format, letterhead=None, stamp_text=None):

    doc = frappe.get_doc(doctype, name)

    # Get Delivery Note date safely
    dn_date = None
    if getattr(doc, "delivery_note", None):
        dn_doc = frappe.get_doc("Delivery Note", doc.delivery_note)
        dn_date = frappe.utils.formatdate(dn_doc.posting_date, "dd-MM-yyyy")

    # 1. Get existing PDF (from ERPNext print format)
    html = frappe.get_print(
        doctype=doctype,
        name=name,
        print_format=print_format,
        letterhead=letterhead,
    )

    pdf_bytes = frappe.utils.pdf.get_pdf(html)

    # 2. Read PDF
    reader = PdfReader(BytesIO(pdf_bytes))
    writer = PdfWriter()

    # 3. Process pages
    for i, page in enumerate(reader.pages):

        # ❌ Skip first page completely
        if i == 0:
            writer.add_page(page)
            continue

        packet = BytesIO()
        can = canvas.Canvas(packet)

        # Position (top-right area)
        x = page.mediabox.width - 265
        y = page.mediabox.height - 20

        # ===== PACKING SLIP =====
        value_x = x + 75   # fixed column for all values

        # Packing Slip
        can.setFont("Helvetica-Bold", 10)
        can.drawString(x, y, "Packing Slip:")

        can.setFont("Helvetica", 10)
        can.drawString(value_x, y, name)

        # Date (aligned under value column)
        can.setFont("Helvetica-Bold", 9)
        can.drawString(x, y - 12, "Date:")

        can.setFont("Helvetica", 9)
        can.drawString(value_x, y - 12, dn_date or "-")

        can.save()

        packet.seek(0)
        overlay_pdf = PdfReader(packet)

        page.merge_page(overlay_pdf.pages[0])
        writer.add_page(page)

    # 4. Save final PDF
    output = BytesIO()
    writer.write(output)

    file_doc = save_file(
        fname=f"{name}_stamped.pdf",
        content=output.getvalue(),
        dt=doctype,
        dn=name,
        is_private=0
    )

    return {
        "file_url": file_doc.file_url,
        "file_name": file_doc.file_name
    }