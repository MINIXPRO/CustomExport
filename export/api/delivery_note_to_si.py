import frappe
from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice


# Fields that must differ to keep rows separate (grouping key)
MERGE_KEY_FIELDS = [
    "item_code",
    "uom",
    "rate",
    "warehouse",
    "sales_order",       # against_sales_order mapped to sales_order in SI
    "cost_center",
    "item_tax_template",
    "income_account",
]

# Custom CIF/export item fields to carry forward (take value from first row in group)
CUSTOM_ITEM_FIELDS = [
    "custom_duty_drawback",
    "custom_net_weight",
    "custom_freight__insurance_",
    "custom_cif_unit_price",
    "custom__cif_total_amount",
    "custom_cif_unit_price_",
    "custom___cif_total_amount",
]


def _merge_key(item):
    """Return a tuple used to group SI item rows."""
    return tuple(frappe.utils.cstr(item.get(f) or "") for f in MERGE_KEY_FIELDS)


def _merge_items(items):
    """
    Merge SI item rows that share the same grouping key.
    qty is summed; rate, amount, and other fields are taken from the first row.
    dn_detail is set to the first row's value (keeps one DN link per merged row).
    """
    groups = {}   # key -> first item row (mutated in place)
    order = []    # preserves original order of first occurrence

    for item in items:
        key = _merge_key(item)
        if key not in groups:
            groups[key] = item
            order.append(key)
        else:
            # Accumulate qty; amounts will be recalculated by ERPNext later
            groups[key].qty += item.qty

    return [groups[k] for k in order]


@frappe.whitelist()
def make_sales_invoice_custom(source_name, target_doc=None, args=None):
    """
    Override for Delivery Note → Sales Invoice creation.

    Delivery Notes intentionally split items into qty-1 rows for packing/export
    handling.  This override merges those rows back so the Sales Invoice has
    normal consolidated lines (one row per logical item with summed qty).
    """
    # 1. Run standard mapping (produces one SI row per DN row)
    doc = make_sales_invoice(source_name, target_doc=target_doc, args=args)

    # 2. Merge split rows on the Sales Invoice
    if doc.items:
        doc.items = _merge_items(doc.items)

        # Re-index row numbers so the child table is internally consistent
        for idx, item in enumerate(doc.items, start=1):
            item.idx = idx

    return doc
