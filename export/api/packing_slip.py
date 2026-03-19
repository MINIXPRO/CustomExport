import frappe
from frappe.utils import flt


# Parent-level fields to copy from Delivery Note → Packing Slip (same name on both).
PARENT_FIELDS = [
    "custom_order_type",
    "custom_mode",
    "custom_cif_total_amount_company_currency",
    "custom_cif_total_amount_",
]

# ---------------------------------------------------------------------------
# Item-level fields: SAME fieldname on both Delivery Note Item and Packing Slip Item.
# ---------------------------------------------------------------------------
ITEM_FIELDS = [
    # Legacy CIF fields (kept for backward compatibility)
    "custom_duty_drawback",
    "custom_freight__insurance_",
    "custom_cif_unit_price",
    "custom__cif_total_amount",
    "custom_cif_unit_price_",
    "custom___cif_total_amount",
    # Template packing/audit fields with identical names on both sides
    "custom_sales_order_no",
    "custom_box_type",
    "custom_doc_audit_qty",
    "custom_audit_remarks",
]

# ---------------------------------------------------------------------------
# Item-level fields with DIFFERENT names on DN Item vs PS Item.
#
# Key: DN Item fieldname   →   Value: PS Item fieldname
#
# Alignment rationale:
#   custom_customer_order_number  not on PS Item → use existing custom_cust_po_no
#   custom_customer_part_no       → custom_customer_part_number (pre-existing PS field)
#   actual_qty (standard DN)      → custom_total_available_quantity (existing PS custom)
#   custom_net_weight             → custom_unit_weight  (existing PS custom)
#   custom_net_wt                 → net_weight          (standard PS field)
#   custom_box_no                 → custom_box          (existing PS custom, avoids duplicate)
#   custom_gross_wt               → custom__gross_weight (existing PS custom, avoids duplicate)
#   custom_l/w/h                  → custom_length/width/height (existing PS customs)
#   custom_vol_cuft/cumtr         → custom_cubic_feet/meter    (existing PS customs)
# ---------------------------------------------------------------------------
ITEM_FIELD_REMAP = {
    "custom_customer_order_number": "custom_cust_po_no",
    "custom_customer_part_no":      "custom_customer_part_number",
    "actual_qty":                   "custom_total_available_quantity",
    "custom_net_weight":            "custom_unit_weight",
    # "custom_net_wt":                "net_weight",
    "custom_box_no":                "custom_box",
    "custom_gross_wt":              "custom__gross_weight",
    "custom_l":                     "custom_length",
    "custom_w":                     "custom_width",
    "custom_h":                     "custom_height",
    "custom_vol_cuft":              "custom_cubic_feet",
    "custom_vol_cumtr":             "custom_cubic_meter",
    "rate":                         "custom_rate",
}


@frappe.whitelist()
def make_packing_slip_custom(source_name, target_doc=None):
    """
    Override for erpnext.stock.doctype.delivery_note.delivery_note.make_packing_slip.

    Calls the standard ERPNext make_packing_slip and then copies custom fields
    (parent-level and item-level) from the Delivery Note to the Packing Slip.

    Standard fields (item_code, item_name, description, qty, net_weight, etc.)
    are already handled by the ERPNext base function and are NOT re-copied here.
    """
    from erpnext.stock.doctype.delivery_note.delivery_note import make_packing_slip

    doc = make_packing_slip(source_name, target_doc)

    dn = frappe.get_doc("Delivery Note", source_name)

    # --- Copy parent-level fields ---
    for field in PARENT_FIELDS:
        if hasattr(dn, field):
            setattr(doc, field, getattr(dn, field))

    # Copy currency (stored as custom_currency in Packing Slip)
    if hasattr(dn, "currency") and hasattr(doc, "custom_currency"):
        doc.custom_currency = dn.currency

    # --- Copy item-level custom fields ---
    # dn_detail on Packing Slip Item = name of the originating Delivery Note Item row
    dn_item_map = {row.name: row for row in dn.items}

    for ps_item in doc.items:
        dn_item = dn_item_map.get(ps_item.dn_detail)
        if not dn_item:
            continue

        # Same-name fields
        for field in ITEM_FIELDS:
            if hasattr(dn_item, field) and hasattr(ps_item, field):
                setattr(ps_item, field, getattr(dn_item, field))

        # Cross-name remapped fields
        for src_field, dst_field in ITEM_FIELD_REMAP.items():
            if hasattr(dn_item, src_field) and hasattr(ps_item, dst_field):
                setattr(ps_item, dst_field, getattr(dn_item, src_field))

        # Currency on each item row
        if hasattr(ps_item, "custom_currency"):
            ps_item.custom_currency = getattr(dn, "currency", None)

        # Set net_weight to per-unit weight so standard calculate_net_total_pkg
        # (which does net_weight × qty) gives the correct package total.
        if hasattr(dn_item, "weight_per_unit"):
            ps_item.net_weight = flt(dn_item.weight_per_unit)

    return doc
