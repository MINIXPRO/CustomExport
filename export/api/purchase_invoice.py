import frappe


def validate(doc, method=None):
    _validate_bill_no_unique(doc)


def _validate_bill_no_unique(doc):
    """
    Prevent saving a Purchase Invoice whose bill_no already exists in another
    non-cancelled Purchase Invoice.

    Scope  : all suppliers, all dates (stricter than the ERPNext built-in check
             which is supplier+fiscal-year scoped and requires a settings flag).
    Skipped: blank bill_no, cancelled documents, the document itself.
    """
    bill_no = (doc.bill_no or "").strip()
    if not bill_no:
        return

    duplicate = frappe.db.get_value(
        "Purchase Invoice",
        {
            "bill_no":   bill_no,
            "name":      ("!=", doc.name),
            "docstatus": ("<", 2),          # 0=Draft, 1=Submitted — both count; 2=Cancelled is excluded
        },
        ["name", "supplier", "posting_date"],
        as_dict=True,
    )

    if duplicate:
        frappe.throw(
            frappe._(
                "Supplier Invoice No <b>{bill_no}</b> already exists in "
                "{link} (Supplier: {supplier}, Date: {date}). "
                "Duplicate bill_no entries are not allowed."
            ).format(
                bill_no=bill_no,
                link=frappe.utils.get_link_to_form("Purchase Invoice", duplicate.name),
                supplier=duplicate.supplier,
                date=frappe.utils.formatdate(duplicate.posting_date),
            ),
            title=frappe._("Duplicate Supplier Invoice No"),
        )
