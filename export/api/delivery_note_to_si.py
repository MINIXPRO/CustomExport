import frappe
from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice


# Fields that must differ to keep rows separate (grouping key).
# so_detail is included to ensure we only merge rows originating from the
# same Sales Order item; rows from different SO items must stay separate so
# that so_detail on the merged row correctly represents all source DN rows.
MERGE_KEY_FIELDS = [
    "item_code",
    "uom",
    "rate",
    "warehouse",
    "sales_order",       # against_sales_order mapped to sales_order in SI
    "so_detail",         # SO Item row — keeps different SO items separate
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

    - qty is summed across all rows in the group.
    - rate, custom fields, and other fields come from the first row.
    - For merged groups (count > 1): dn_detail is cleared.

      Why clearing dn_detail fixes overbilling
      -----------------------------------------
      ERPNext's validate_multiple_billing (accounts_controller.py) checks:
          SI item amount  <=  DN Item[dn_detail].amount  * (1 + allowance%)
      A merged row has amount = N * single_dn_row_amount, so the comparison
      fires "Cannot overbill" because N * X > X.
      When dn_detail is None the loop skips the row entirely (line 2222:
          "if not key: continue").

      Billed-amount tracking after clearing dn_detail
      -------------------------------------------------
      ERPNext's on_submit handler iterates SI items:
          if d.dn_detail  → update_billed_amount_based_on_dn(d.dn_detail)
          elif d.so_detail → update_billed_amount_based_on_so(d.so_detail)
      With dn_detail=None and so_detail preserved, the elif branch runs.
      update_billed_amount_based_on_so distributes the billed amount FIFO
      across all DN items sharing so_detail, correctly setting billed_amt on
      each source DN row.

    - For single-row groups: dn_detail is kept intact (standard behavior).
    """
    groups = {}   # key -> {"item": first_item, "count": N}
    order = []    # preserves original insertion order

    for item in items:
        key = _merge_key(item)
        if key not in groups:
            groups[key] = {"item": item, "count": 1}
            order.append(key)
        else:
            groups[key]["item"].qty += item.qty
            groups[key]["count"] += 1

    result = []
    for k in order:
        g = groups[k]
        item = g["item"]
        if g["count"] > 1:
            # Clear dn_detail so the overbilling validation skips this row.
            # so_detail is preserved for update_billed_amount_based_on_so.
            item.dn_detail = None
        result.append(item)

    return result


def _get_fully_billed_dn_item_names(source_name):
    """
    Return the set of Delivery Note Item row names that are already fully billed.

    Why this is needed
    ------------------
    get_invoiced_qty_map (used by the standard make_sales_invoice internally)
    groups by dn_detail.  Merged SI rows have dn_detail=None, so those
    already-invoiced DN items are invisible to that query and appear as
    still-billable on a second SI creation attempt.

    We compensate by inspecting billed_amt on the DN items directly.
    billed_amt is populated after SI submission by update_billed_amount_based_on_so
    (FIFO) for rows where dn_detail was cleared.
    """
    dn_items = frappe.get_all(
        "Delivery Note Item",
        filters={"parent": source_name},
        fields=["name", "amount", "billed_amt"],
    )

    over_billing_allowance = (
        frappe.db.get_single_value("Accounts Settings", "over_billing_allowance") or 0
    )
    max_factor = 1 + over_billing_allowance / 100.0

    fully_billed = set()
    for d in dn_items:
        amount = d.amount or 0
        billed = d.billed_amt or 0
        if amount > 0 and billed >= amount * max_factor - 0.001:
            fully_billed.add(d.name)
        elif amount == 0 and billed > 0:
            fully_billed.add(d.name)

    return fully_billed


@frappe.whitelist()
def make_sales_invoice_custom(source_name, target_doc=None, args=None):
    """
    Override for Delivery Note → Sales Invoice creation.

    Delivery Notes intentionally split items into qty-1 rows for packing/export
    handling.  This override merges those rows back so the Sales Invoice has
    normal consolidated lines (one row per logical item with summed qty).

    Overbilling fix
    ---------------
    When N source DN rows (each qty=1, amount=X) are merged into one SI row
    (qty=N, amount=N*X), keeping dn_detail pointing to one DN row causes
    ERPNext's validate_multiple_billing to compare N*X against X and throw
    "Cannot overbill".

    Fix: for merged rows we clear dn_detail and preserve so_detail.
    ERPNext then uses update_billed_amount_based_on_so (FIFO) after SI
    submission to distribute the billed amount across all DN items with the
    same so_detail, correctly marking each source DN row as billed.

    Re-invoicing prevention
    -----------------------
    Because dn_detail is None on merged rows, get_invoiced_qty_map (which
    groups by dn_detail) misses them and would allow a second SI to be created
    from the same DN.  We compensate by checking billed_amt on each DN item —
    populated after SI submission — and filtering out fully billed items before
    the merge step.
    """
    # 1. Run standard mapping (produces one SI row per DN row, filtered by pending qty)
    doc = make_sales_invoice(source_name, target_doc=target_doc, args=args)

    if not doc.items:
        return doc

    # 2. Filter out DN items already fully billed.
    #    Handles the case where a prior merged SI cleared dn_detail, making
    #    those items invisible to the standard invoiced_qty_map check.
    fully_billed = _get_fully_billed_dn_item_names(source_name)
    if fully_billed:
        doc.items = [item for item in doc.items if item.dn_detail not in fully_billed]

    if not doc.items:
        return doc

    # 3. Merge split rows on the Sales Invoice
    doc.items = _merge_items(doc.items)

    # Re-index row numbers so the child table is internally consistent
    for idx, item in enumerate(doc.items, start=1):
        item.idx = idx

    return doc
