import frappe
from erpnext.selling.doctype.sales_order.sales_order import (
    make_sales_invoice,
    make_delivery_note
)


# ------------------ SALES INVOICE ------------------

@frappe.whitelist()
def make_sales_invoice_custom(source_name, target_doc=None, ignore_permissions=False):
    doc = make_sales_invoice(source_name, target_doc, ignore_permissions)

    so = frappe.get_doc("Sales Order", source_name)

    # Pass Order Type → Sales Invoice
    doc.custom_order_type = so.order_type

    if so.order_type == "Export":
        # Carry forward parent-level export fields
        parent_fields = [
            "custom_total_amount",
            "custom_total_company_currency",
            "custom_cif_total_amount_",
            "custom_cif_total_amount_company_currency",
            "custom_mode",
            "custom_loading_port",
            "custom_loading_port_code",
            "custom_discharge_port",
            "custom_discharge_port_code",
            "custom_final_destination",
            "custom_shipping_mark",
            "custom_the_state_of_origin_of_goods",
            "custom_district_of_origin_of_goods",
            "custom_we_intend_to_claim_benefit_under_rodtep_scheme",
            "custom_export_under_advance_license",
            "custom_details_of_preferential_agreements",
        ]
        for field in parent_fields:
            if hasattr(so, field):
                setattr(doc, field, getattr(so, field))

        # Carry forward item-level CIF fields
        item_fields = [
            "custom_duty_drawback",
            "custom_net_weight",
            "custom_freight__insurance_",
            "custom_cif_unit_price",
            "custom__cif_total_amount",
            "custom_cif_unit_price_",
            "custom___cif_total_amount",
        ]

        # Build lookup from SO Item name → SO Item row
        so_item_map = {row.name: row for row in so.items}

        for si_item in doc.items:
            so_item = so_item_map.get(si_item.so_detail)
            if not so_item:
                continue
            for field in item_fields:
                if hasattr(so_item, field):
                    setattr(si_item, field, getattr(so_item, field))

    # Reset weight_per_unit from Item Master (overrides whatever SO carried forward)
    item_codes = list({item.item_code for item in doc.items if item.item_code})
    if item_codes:
        weight_map = {
            r.name: r.weight_per_unit
            for r in frappe.get_all("Item", filters={"name": ["in", item_codes]}, fields=["name", "weight_per_unit"])
        }
        for item in doc.items:
            if item.item_code in weight_map:
                item.weight_per_unit = weight_map[item.item_code]

    return doc


# ------------------ DELIVERY NOTE ------------------

@frappe.whitelist()
def make_delivery_note_custom(source_name, target_doc=None, ignore_permissions=False):
    doc = make_delivery_note(source_name, target_doc, ignore_permissions)

    so = frappe.get_doc("Sales Order", source_name)

    # Pass Order Type → Delivery Note
    doc.custom_order_type = so.order_type

    # Reset weight_per_unit from Item Master (overrides whatever SO carried forward)
    item_codes = list({item.item_code for item in doc.items if item.item_code})
    if item_codes:
        weight_map = {
            r.name: r.weight_per_unit
            for r in frappe.get_all("Item", filters={"name": ["in", item_codes]}, fields=["name", "weight_per_unit"])
        }
        for item in doc.items:
            if item.item_code in weight_map:
                item.weight_per_unit = weight_map[item.item_code]

    return doc
