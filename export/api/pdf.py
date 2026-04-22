"""
Custom PDF generation for Sales Invoice (Commercial Invoice).

Uses wkhtmltopdf --header-html to render a fully dynamic header
(company logo, invoice info, consignee table, column headers) on
EVERY page of the PDF output.

Architecture
────────────
  ci_header.html   ← Jinja2 template, rendered to a temp file with doc context
                     Passed to wkhtmltopdf via --header-html.
                     Repeats on every page automatically.

  cusstomm         ← Existing print format, used for the body only.
                     The header section (company block → column headers)
                     must be removed from cusstomm (see notes below).

  --margin-top     ← Must be >= rendered header height (≈115 mm by default).
                     Increase if long consignee addresses clip the header.
"""
import os
import tempfile
import base64

import frappe
from frappe.utils.pdf import get_pdf


# ────────────────────────────────────────────────────────────────────────────
# Adjust these two values if the header is clipped or leaves too much whitespace.
# HEADER_MARGIN_MM   = space reserved at the top of every page for the header
# HEADER_SPACING_MM  = gap (in mm) between the bottom of the header and body text
# ────────────────────────────────────────────────────────────────────────────
HEADER_MARGIN_MM  = "115mm"
HEADER_SPACING_MM = "2"

HEADER_TEMPLATE = "export/templates/print_formats/ci_header.html"
BODY_PRINT_FORMAT = "cusstomm"


def _get_logo_src(site_url: str) -> str:
    """
    Return an img src for the company logo.
    Prefers a base64 data-URI so wkhtmltopdf never needs a network call
    for the header temp file.  Falls back to the HTTP URL.
    """
    try:
        img_path = frappe.get_site_path("public", "files", "GME.png")
        if os.path.exists(img_path):
            with open(img_path, "rb") as fh:
                b64 = base64.b64encode(fh.read()).decode("utf-8")
            return f"data:image/png;base64,{b64}"
    except Exception:
        pass
    return f"{site_url}/files/GME.png"


@frappe.whitelist()
def download_commercial_invoice_pdf(name):
    """
    Generate a Sales Invoice PDF with a dynamic repeating header on every page.

    Call via:
        GET /api/method/export.api.pdf.download_commercial_invoice_pdf?name=SI-XXXX
    Or via frappe.call() → triggers browser download.
    """
    frappe.has_permission("Sales Invoice", "print", doc=name, throw=True)

    doc      = frappe.get_doc("Sales Invoice", name)
    site_url = frappe.utils.get_url()

    # ── 1. Render header template → static HTML with actual doc values ──────
    img_src = _get_logo_src(site_url)

    header_html = frappe.render_template(
        HEADER_TEMPLATE,
        {"doc": doc, "frappe": frappe, "img_src": img_src},
        is_path=True,
    )

    # ── 2. Get body HTML from the cusstomm print format ──────────────────────
    # no_letterhead=1 prevents Frappe from prepending its own company letterhead
    body_html = frappe.get_print(
        doctype="Sales Invoice",
        name=name,
        print_format=BODY_PRINT_FORMAT,
        doc=doc,
        no_letterhead=1,
    )

    # ── 3. Write rendered header to a temp file on disk ──────────────────────
    header_path = None
    try:
        fd, header_path = tempfile.mkstemp(suffix=".html", prefix="ci_hdr_")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(header_html)

        # ── 4. Build wkhtmltopdf options ─────────────────────────────────────
        # margin-top must be >= the rendered height of ci_header.html.
        # Increase HEADER_MARGIN_MM at the top of this file if the header is cut off.
        options = {
            "page-size":                "A4",
            "orientation":              "Landscape",
            "margin-top":               HEADER_MARGIN_MM,
            "margin-bottom":            "15mm",
            "margin-left":              "10mm",
            "margin-right":             "10mm",
            "header-html":              header_path,
            "header-spacing":           HEADER_SPACING_MM,
            "enable-local-file-access": "",
            "disable-smart-shrinking":  "",
            "print-media-type":         "",
            "encoding":                 "UTF-8",
        }

        # ── 5. Generate PDF ───────────────────────────────────────────────────
        pdf_bytes = get_pdf(body_html, options)

    finally:
        if header_path and os.path.exists(header_path):
            os.unlink(header_path)

    if not pdf_bytes:
        frappe.throw("PDF generation failed — wkhtmltopdf returned empty output.")

    # ── 6. Return as a browser-triggered file download ────────────────────────
    frappe.response.filename    = f"{name}.pdf"
    frappe.response.filecontent = pdf_bytes
    frappe.response.type        = "download"
