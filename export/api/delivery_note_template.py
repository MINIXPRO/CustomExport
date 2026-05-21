import io
import frappe


# ---------------------------------------------------------------------------
# 20-column template for the custom Delivery Note Item import/export flow.
#
# Column order matches the business spec exactly.
# Fieldnames are the FINAL aligned names on Delivery Note Item.
#
# Key alignment changes vs old code:
#   "Cust PO No"              → custom_customer_order_number  (was: custom_cust_po_no)
#   "Customer Part No"        → customer_item_code             (standard DN Item field)
#   "Total Avilable quantity" → actual_qty                    (was: custom_total_available_quantity)
# ---------------------------------------------------------------------------
TEMPLATE_FIELDS = [
    ("Sales Order No",            "custom_sales_order_no"),
    ("Cust PO No",                "custom_customer_order_number"),
    ("Part No",                   "item_code"),
    ("Customer Item Code",         "customer_item_code"),
    ("Item Name",                 "item_name"),
    ("Quantity",                  "qty"),
    ("Rate",                      "rate"),
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
    ("Sales Order Item ID",       "so_detail"),
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

    # Fill existing item data when a saved Delivery Note name is supplied.
    # Gracefully skip if the document doesn't exist yet (new/unsaved doc).
    if delivery_note:
        try:
            dn = frappe.get_doc("Delivery Note", delivery_note)
            for item in dn.items:
                row = []
                for _, fn in TEMPLATE_FIELDS:
                    val = getattr(item, fn, None)
                    row.append("" if val is None else val)
                ws.append(row)
        except frappe.DoesNotExistError:
            pass  # Unsaved / new doc – return blank template with headers only

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


# @frappe.whitelist()
# def import_delivery_note_items(delivery_note, file_url):
#     """
#     Import Delivery Note Item rows from the custom XLSX / CSV template.

#     STRATEGY: Clear and Rebuild.
#     The uploaded rows are the single source of truth for dn.items.
#     Rows absent from the upload are removed. Rows present are kept/created.

#     Row 1: labels      (ignored)
#     Row 2: fieldnames  (column-to-field mapping)
#     Row 3+: data rows  → become the complete new dn.items

#     For each uploaded row the matching existing DN item (by item_code, in order)
#     is used as the base so ERPNext-linked fields (warehouse, SO reference,
#     income account, etc.) are preserved. Template field values are applied on top.
#     If no existing item matches, a fresh child row is created.
#     """
#     import os
#     from collections import defaultdict

#     # ── Resolve file path ────────────────────────────────────────────────────
#     site_path = frappe.get_site_path()
#     if file_url.startswith("/files/"):
#         file_path = os.path.join(site_path, "public", file_url.lstrip("/"))
#     elif file_url.startswith("/private/files/"):
#         file_path = os.path.join(site_path, file_url.lstrip("/"))
#     else:
#         frappe.throw(f"Unsupported file URL format: {file_url}")

#     if not os.path.exists(file_path):
#         frappe.throw(f"File not found on disk: {file_path}")

#     # ── Read rows (XLSX or CSV) ──────────────────────────────────────────────
#     ext = os.path.splitext(file_url.lower())[1]
#     if ext in (".xlsx", ".xls"):
#         try:
#             from openpyxl import load_workbook
#         except ImportError:
#             frappe.throw("openpyxl is required. Run: pip install openpyxl")
#         wb   = load_workbook(file_path, data_only=True)
#         rows = list(wb.active.iter_rows(values_only=True))
#     elif ext == ".csv":
#         import csv
#         with open(file_path, newline="", encoding="utf-8-sig") as f:
#             rows = [tuple(r) for r in csv.reader(f)]
#     else:
#         frappe.throw(f"Unsupported file format '{ext}'. Upload a .xlsx or .csv file.")

#     if len(rows) < 3:
#         frappe.throw(
#             "The uploaded file must have at least 3 rows "
#             "(Row 1 = labels, Row 2 = fieldnames, Row 3+ = data)."
#         )

#     # ── Parse fieldnames from row 2 ──────────────────────────────────────────
#     fieldnames = [str(f).strip() if f is not None else None for f in rows[1]]

#     # Fields managed by Frappe / used only as match key — never set from template
#     SKIP_FIELDS = {"item_code", "name", "parent", "parenttype", "parentfield", "idx"}

#     # ── Parse all valid data rows upfront ────────────────────────────────────
#     parsed_rows = []
#     for data_row in rows[2:]:
#         if all(v is None or str(v).strip() == "" for v in data_row):
#             continue
#         row_data = {}
#         for col_idx, fn in enumerate(fieldnames):
#             if not fn or fn == "None":
#                 continue
#             row_data[fn] = data_row[col_idx] if col_idx < len(data_row) else None
#         item_code = str(row_data.get("item_code") or "").strip()
#         if not item_code:
#             continue
#         parsed_rows.append((item_code, row_data))

#     if not parsed_rows:
#         frappe.throw("No valid item rows found in the uploaded file.")

#     dn = frappe.get_doc("Delivery Note", delivery_note)
#     frappe.has_permission("Delivery Note", "write", dn, throw=True)

#     # ── Build lookup of existing items by item_code (ordered for duplicates) ─
#     existing_map = defaultdict(list)
#     for item in dn.items:
#         existing_map[str(item.item_code).strip()].append(item)

#     # ── Clear child table and rebuild from uploaded rows ─────────────────────
#     dn.items = []
#     usage_counter = defaultdict(int)

#     for item_code, row_data in parsed_rows:
#         candidates = existing_map.get(item_code, [])
#         idx = usage_counter[item_code]
#         usage_counter[item_code] += 1

#         if idx < len(candidates):
#             # Base the new row on the existing DN item to preserve linked fields
#             base = candidates[idx].as_dict()
#             base.pop("name", None)
#             base.pop("idx", None)
#             new_item = dn.append("items", base)
#         else:
#             # No existing row for this item_code — create a fresh child row
#             new_item = dn.append("items", {"item_code": item_code})

#         # Apply uploaded field values on top (skip identity/protected fields)
#         for fn, value in row_data.items():
#             if fn in SKIP_FIELDS:
#                 continue
#             if not hasattr(new_item, fn):
#                 continue
#             setattr(new_item, fn, None if (value is None or str(value).strip() == "") else value)

#     total = len(parsed_rows)
#     dn.save(ignore_permissions=True)
#     frappe.db.commit()

#     return {
#         "total":   total,
#         "message": f"Successfully imported {total} item row(s) into {delivery_note}. Delivery Note items replaced.",
#     }



@frappe.whitelist()
def import_delivery_note_items(delivery_note, file_url):
    """
    Import Delivery Note Item rows from the custom XLSX / CSV template.

    STRATEGY: Clear and Rebuild.
    The uploaded rows are the single source of truth for dn.items.
    Rows absent from the upload are removed. Rows present are kept/created.

    Row 1: labels      (ignored)
    Row 2: fieldnames  (column-to-field mapping)
    Row 3+: data rows  → become the complete new dn.items

    For each uploaded row the matching existing DN item (by item_code, in order)
    is used as the base so ERPNext-linked fields (warehouse, SO reference,
    income account, etc.) are preserved. Template field values are merged on top
    BEFORE appending so Frappe picks up all values correctly on save().
    """
    import os
    from collections import defaultdict

    # ── Resolve file path ────────────────────────────────────────────────────
    site_path = frappe.get_site_path()
    if file_url.startswith("/files/"):
        file_path = os.path.join(site_path, "public", file_url.lstrip("/"))
    elif file_url.startswith("/private/files/"):
        file_path = os.path.join(site_path, file_url.lstrip("/"))
    else:
        frappe.throw(f"Unsupported file URL format: {file_url}")

    if not os.path.exists(file_path):
        frappe.throw(f"File not found on disk: {file_path}")

    # ── Read rows (XLSX or CSV) ──────────────────────────────────────────────
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

    # ── Parse fieldnames from row 2 ──────────────────────────────────────────
    fieldnames = [str(f).strip() if f is not None else None for f in rows[1]]

    # Fields managed by Frappe / used only as match key — never overwrite from template
    SKIP_FIELDS = {"item_code", "name", "parent", "parenttype", "parentfield", "idx"}

    # ── Parse all valid data rows upfront ────────────────────────────────────
    parsed_rows = []
    for data_row in rows[2:]:
        if all(v is None or str(v).strip() == "" for v in data_row):
            continue
        row_data = {}
        for col_idx, fn in enumerate(fieldnames):
            if not fn or fn == "None":
                continue
            row_data[fn] = data_row[col_idx] if col_idx < len(data_row) else None
        item_code = str(row_data.get("item_code") or "").strip()
        if not item_code:
            continue
        parsed_rows.append((item_code, row_data))

    if not parsed_rows:
        frappe.throw("No valid item rows found in the uploaded file.")

    dn = frappe.get_doc("Delivery Note", delivery_note)
    frappe.has_permission("Delivery Note", "write", dn, throw=True)

    # ── Build lookup of existing items by item_code (ordered for duplicates) ─
    existing_map = defaultdict(list)
    for item in dn.items:
        existing_map[str(item.item_code).strip()].append(item)

    # ── Clear child table and rebuild from uploaded rows ─────────────────────
    dn.items = []
    usage_counter = defaultdict(int)

    invalid_rows = []             # PO mismatch
    missing_so_detail_rows = []   # Missing so_detail

    for item_code, row_data in parsed_rows:
        so_name     = str(row_data.get("custom_sales_order_no") or "").strip()
        customer_po = str(row_data.get("custom_customer_order_number") or "").strip()

        # Validate so_detail first
        so_detail = str(row_data.get("so_detail") or "").strip()
        if not so_detail:
            missing_so_detail_rows.append({
                "item_code":   item_code,
                "sales_order": so_name,
                "row_po":      customer_po,
            })
            continue

        # Validate PO match against the Sales Order
        if so_name:
            try:
                so_doc = frappe.get_doc("Sales Order", so_name)
                so_po  = str(getattr(so_doc, "po_no", "") or "").strip()
                if so_po and customer_po and so_po != customer_po:
                    invalid_rows.append({
                        "item_code":   item_code,
                        "sales_order": so_name,
                        "so_po":       so_po,
                        "row_po":      customer_po,
                    })
                    continue
            except frappe.DoesNotExistError:
                invalid_rows.append({
                    "item_code":   item_code,
                    "sales_order": so_name,
                    "so_po":       "NOT FOUND",
                    "row_po":      customer_po,
                })
                continue

        candidates = existing_map.get(item_code, [])
        idx = usage_counter[item_code]
        usage_counter[item_code] += 1

        if idx < len(candidates):
            base = candidates[idx].as_dict()
            base.pop("name", None)
            base.pop("idx", None)
            for fn, value in row_data.items():
                if fn in SKIP_FIELDS:
                    continue
                base[fn] = None if (value is None or str(value).strip() == "") else value
            dn.append("items", base)
        else:
            merged = {"item_code": item_code}
            for fn, value in row_data.items():
                if fn in SKIP_FIELDS:
                    continue
                merged[fn] = None if (value is None or str(value).strip() == "") else value
            # Carry SO linkage from the first existing candidate so ERPNext
            # validation passes when the user splits one row into multiple rows.
            first_candidate = existing_map.get(item_code, [None])[0]
            if first_candidate:
                merged["against_sales_order"] = first_candidate.against_sales_order
                merged["so_detail"]           = first_candidate.so_detail
            dn.append("items", merged)

    total = len(dn.items)
    dn.save(ignore_permissions=True)
    frappe.db.commit()

    if invalid_rows or missing_so_detail_rows:
        message = '<div style="max-height:300px; overflow:auto;">'

        if missing_so_detail_rows:
            message += """
                <p style="margin:10px 0;"><b>Rows skipped due to missing Sales Order Item ID:</b></p>
                <table style="width:100%; border-collapse:separate; border-spacing:0; font-size:13px;">
                <thead>
                    <tr style="background-color:#fff3cd;">
                        <th style="padding:8px; border:1px solid #d1d8dd;">Item Code</th>
                        <th style="padding:8px; border:1px solid #d1d8dd;">Sales Order</th>
                        <th style="padding:8px; border:1px solid #d1d8dd;">File PO</th>
                    </tr>
                </thead>
                <tbody>
            """
            for r in missing_so_detail_rows:
                message += f"""
                    <tr>
                        <td style="padding:8px; border:1px solid #e4e7eb;">{r['item_code']}</td>
                        <td style="padding:8px; border:1px solid #e4e7eb;">{r['sales_order']}</td>
                        <td style="padding:8px; border:1px solid #e4e7eb;">{r['row_po']}</td>
                    </tr>
                """
            message += "</tbody></table>"

        if invalid_rows:
            message += """
                <p style="margin:10px 0;"><b>Rows skipped due to PO mismatch:</b></p>
                <table style="width:100%; border-collapse:separate; border-spacing:0; font-size:13px;">
                <thead>
                    <tr style="background-color:#f7fafc;">
                        <th style="padding:8px; border:1px solid #d1d8dd;">Item Code</th>
                        <th style="padding:8px; border:1px solid #d1d8dd;">Sales Order</th>
                        <th style="padding:8px; border:1px solid #d1d8dd;">SO PO</th>
                        <th style="padding:8px; border:1px solid #d1d8dd;">File PO</th>
                    </tr>
                </thead>
                <tbody>
            """
            for r in invalid_rows:
                message += f"""
                    <tr>
                        <td style="padding:8px; border:1px solid #e4e7eb;">{r['item_code']}</td>
                        <td style="padding:8px; border:1px solid #e4e7eb;">{r['sales_order']}</td>
                        <td style="padding:8px; border:1px solid #e4e7eb; color:#d9534f;">{r['so_po']}</td>
                        <td style="padding:8px; border:1px solid #e4e7eb; color:#5bc0de;">{r['row_po']}</td>
                    </tr>
                """
            message += "</tbody></table>"

        message += "</div>"
        frappe.msgprint(message)

    return {
        "total":   total,
        "message": f"Imported {total} valid row(s). "
                   f"{len(missing_so_detail_rows)} missing SO detail, "
                   f"{len(invalid_rows)} PO mismatch.",
    }