import io
import frappe


# ---------------------------------------------------------------------------
# 19-column template for the custom Delivery Note Item import/export flow.
#
# Column order matches the business spec exactly.
# Fieldnames are the FINAL aligned names on Delivery Note Item.
#
# Key alignment changes vs old code:
#   "Cust PO No"              → custom_customer_order_number  (was: custom_cust_po_no)
#   "Customer Part No"        → custom_customer_part_no       (dedicated custom Data field on DNI)
#   "Total Avilable quantity" → actual_qty                    (was: custom_total_available_quantity)
# ---------------------------------------------------------------------------
TEMPLATE_FIELDS = [
    ("Sales Order No",            "custom_sales_order_no"),
    ("Cust PO No",                "custom_customer_order_number"),
    ("Part No",                   "item_code"),
    ("Customer Part No",          "custom_customer_part_no"),
    ("Item Name",                 "item_name"),
    ("Quantity",                  "qty"),
    ("Total Avilable quantity",   "actual_qty"),
    ("UnitWT (Kg)",               "custom_net_weight"),
    ("Net WT (Kg)",               "custom_net_wt"),
    ("Box No.",                   "custom_box_no"),
    ("Gross WT (Kg)",             "custom_gross_wt"),
    ("L (Inch)",                  "custom_l"),
    ("W (Inch)",                  "custom_w"),
    ("H (Inch)",                  "custom_h"),
    ("Box Type",                  "custom_box_type"),
    ("Vol. (CuFt)",               "custom_vol_cuft"),
    ("Vol. (CuMtr)",              "custom_vol_cumtr"),
    ("Doc Audit Qty",             "custom_doc_audit_qty"),
    ("Audit Remarks",             "custom_audit_remarks"),
]


@frappe.whitelist()
def get_delivery_note_custom_template(delivery_note=None):
    """
    Generate and return an XLSX template for Delivery Note Item bulk import/export.

    Row 1 → column labels  (human-readable, styled dark-blue)
    Row 2 → fieldnames     (machine-readable, styled mid-blue)
    Row 3+ → existing item data when `delivery_note` is provided and has rows.

    The file is returned as a direct download response.
    """
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment
    except ImportError:
        frappe.throw("openpyxl is required. Run: pip install openpyxl")

    wb = Workbook()
    ws = wb.active
    ws.title = "Delivery Note Items"

    header_font    = Font(bold=True, color="FFFFFF")
    header_fill    = PatternFill(start_color="2E4057", end_color="2E4057", fill_type="solid")
    fieldname_fill = PatternFill(start_color="5B8DB8", end_color="5B8DB8", fill_type="solid")
    fieldname_font = Font(bold=False, color="FFFFFF")
    center_align   = Alignment(horizontal="center", vertical="center", wrap_text=True)

    labels     = [label     for label, _        in TEMPLATE_FIELDS]
    fieldnames = [fieldname for _, fieldname in TEMPLATE_FIELDS]

    ws.append(labels)       # Row 1 – human-readable labels
    ws.append(fieldnames)   # Row 2 – fieldnames for import

    for col_idx, _ in enumerate(TEMPLATE_FIELDS, start=1):
        cell_label = ws.cell(row=1, column=col_idx)
        cell_label.font      = header_font
        cell_label.fill      = header_fill
        cell_label.alignment = center_align

        cell_field = ws.cell(row=2, column=col_idx)
        cell_field.font      = fieldname_font
        cell_field.fill      = fieldname_fill
        cell_field.alignment = center_align

        max_len = max(len(labels[col_idx - 1]), len(fieldnames[col_idx - 1]))
        ws.column_dimensions[
            ws.cell(row=1, column=col_idx).column_letter
        ].width = max(14, min(max_len + 2, 40))

    ws.row_dimensions[1].height = 30
    ws.row_dimensions[2].height = 22

    # Fill existing item data when a Delivery Note name is supplied
    if delivery_note:
        dn = frappe.get_doc("Delivery Note", delivery_note)
        for item in dn.items:
            row = []
            for _, fn in TEMPLATE_FIELDS:
                val = getattr(item, fn, None)
                row.append("" if val is None else val)
            ws.append(row)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    fname = (
        f"dn_items_{delivery_note}.xlsx"
        if delivery_note
        else "delivery_note_custom_template.xlsx"
    )
    frappe.response["filename"]    = fname
    frappe.response["filecontent"] = output.read()
    frappe.response["type"]        = "download"


@frappe.whitelist()
def import_delivery_note_items(delivery_note, file_url):
    """
    Import Delivery Note Item rows from the custom XLSX / CSV template.

    Row 1: labels    (ignored)
    Row 2: fieldnames  (used as column-to-field mapping, read dynamically)
    Row 3+: data rows  → matched to existing DN items by item_code (in order)

    Protected identity fields (item_code, name, parent, …) are never overwritten.
    Returns a dict with the count of updated rows.
    """
    import os
    from collections import defaultdict

    # Resolve file path
    site_path = frappe.get_site_path()
    if file_url.startswith("/files/"):
        file_path = os.path.join(site_path, "public", file_url.lstrip("/"))
    elif file_url.startswith("/private/files/"):
        file_path = os.path.join(site_path, file_url.lstrip("/"))
    else:
        frappe.throw(f"Unsupported file URL format: {file_url}")

    if not os.path.exists(file_path):
        frappe.throw(f"File not found on disk: {file_path}")

    # Read rows (XLSX or CSV)
    ext = os.path.splitext(file_url.lower())[1]
    if ext in (".xlsx", ".xls"):
        try:
            from openpyxl import load_workbook
        except ImportError:
            frappe.throw("openpyxl is required. Run: pip install openpyxl")
        wb   = load_workbook(file_path, data_only=True)
        rows = list(wb.active.iter_rows(values_only=True))
    elif ext == ".csv":
        import csv
        with open(file_path, newline="", encoding="utf-8-sig") as f:
            rows = [tuple(r) for r in csv.reader(f)]
    else:
        frappe.throw(f"Unsupported file format '{ext}'. Upload a .xlsx or .csv file.")

    if len(rows) < 3:
        frappe.throw(
            "The uploaded file must have at least 3 rows "
            "(Row 1 = labels, Row 2 = fieldnames, Row 3+ = data)."
        )

    # Row 2 (index 1) → fieldname list
    fieldnames = [str(f).strip() if f is not None else None for f in rows[1]]

    # Data starts at row 3 (index 2)
    data_rows = rows[2:]

    dn = frappe.get_doc("Delivery Note", delivery_note)
    frappe.has_permission("Delivery Note", "write", dn, throw=True)

    # Map item_code → ordered list of DN item rows (preserves duplicate-item order)
    dn_item_map = defaultdict(list)
    for item in dn.items:
        dn_item_map[str(item.item_code).strip()].append(item)

    usage_counter = defaultdict(int)
    updated_count = 0
    created_count = 0

    # Fields that must never be overwritten on EXISTING rows during import.
    # For NEW rows appended by this import, item_code IS writable (it identifies the item).
    PROTECTED_EXISTING = {"item_code", "name", "parent", "parenttype", "parentfield", "idx"}
    # Frappe internals that must never be set even on brand-new child rows.
    PROTECTED_NEW      = {"name", "parent", "parenttype", "parentfield"}

    for data_row in data_rows:
        # Skip entirely blank rows
        if all(v is None or str(v).strip() == "" for v in data_row):
            continue

        # Build fieldname → value dict for this row
        row_data = {}
        for col_idx, fn in enumerate(fieldnames):
            if not fn or fn == "None":
                continue
            row_data[fn] = data_row[col_idx] if col_idx < len(data_row) else None

        # item_code is required to identify / create a row
        item_code = str(row_data.get("item_code") or "").strip()
        if not item_code:
            continue

        candidates = dn_item_map.get(item_code, [])
        idx = usage_counter[item_code]

        if idx < len(candidates):
            # ── Update existing DN item ──────────────────────────────────────
            dn_item   = candidates[idx]
            protected = PROTECTED_EXISTING
            is_new    = False
        else:
            # ── No matching existing row → append a new child row ────────────
            dn_item   = dn.append("items", {})
            protected = PROTECTED_NEW
            is_new    = True

        usage_counter[item_code] += 1

        # Apply values
        for fn, value in row_data.items():
            if fn in protected:
                continue
            if not hasattr(dn_item, fn):
                continue
            setattr(dn_item, fn, None if (value is None or str(value).strip() == "") else value)

        if is_new:
            created_count += 1
        else:
            updated_count += 1

    total = updated_count + created_count
    dn.save(ignore_permissions=True)
    frappe.db.commit()

    parts = []
    if updated_count:
        parts.append(f"updated {updated_count}")
    if created_count:
        parts.append(f"created {created_count} new")
    summary = " and ".join(parts) or "processed 0"

    return {
        "updated": updated_count,
        "created": created_count,
        "total":   total,
        "message": f"Successfully {summary} item row(s) in {delivery_note}.",
    }
