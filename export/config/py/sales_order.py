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

    return doc


# ------------------ DELIVERY NOTE ------------------

@frappe.whitelist()
def make_delivery_note_custom(source_name, target_doc=None, ignore_permissions=False):
    doc = make_delivery_note(source_name, target_doc, ignore_permissions)

    so = frappe.get_doc("Sales Order", source_name)

    # Pass Order Type → Delivery Note
    doc.custom_order_type = so.order_type

    return doc
