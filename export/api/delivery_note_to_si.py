import frappe
from frappe.utils import flt
from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice


# Fields that must differ to keep rows separate (grouping key).
# so_detail is included to ensure we only merge rows originating from the
# same Sales Order item; rows from different SO items must stay separate so
# that so_detail on the merged row correctly represents all source DN rows.
# Note: "rate" is intentionally excluded from the key.  Rate equality is
# handled inside _merge_items: rows with one distinct non-zero rate merge
# (using that rate); rows with multiple different non-zero rates stay separate.
MERGE_KEY_FIELDS = [
    "item_code",
    "uom",
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


def _resolve_rate(rows):
    """
    Determine the single rate to use when merging a group of rows.

    Rules (in order):
    1. Collect all distinct non-zero rates in the group (rounded to 9 dp to
       avoid float noise).
    2. If there is exactly one distinct non-zero rate → use it.
    3. If all rates are zero/missing → use 0.
    4. If there are multiple distinct non-zero rates → return None, which
       signals to the caller that this group must NOT be merged.
    """
    nonzero = set()
    for item in rows:
        r = flt(item.rate)
        if r:
            nonzero.add(round(r, 9))
    if len(nonzero) == 0:
        return 0
    if len(nonzero) == 1:
        return nonzero.pop()
    return None   # multiple different rates → cannot safely merge


def _merge_items(items):
    """
    Merge SI item rows that share the same grouping key.

    Rate resolution
    ---------------
    Within each candidate group we look at the distinct non-zero rates:
    - Exactly one non-zero rate → use it for the merged row; amount = qty × rate.
    - All rates are zero        → merged rate stays 0; amount = 0.
    - Multiple different rates  → skip the merge; keep rows as-is so no
                                   information is lost.

    This means a row with qty=20/rate=25 and a row with qty=1/rate=0 merge to
    qty=21/rate=25/amount=525, NOT the diluted rate=23.81.

    Overbilling / billed-amount tracking
    -------------------------------------
    For merged groups (count > 1) dn_detail is cleared and so_detail is
    preserved.  See make_sales_invoice_custom docstring for the full rationale.
    Single-row groups keep dn_detail intact (standard behavior).
    """
    # First pass: collect all rows per merge-key, preserving order.
    groups = {}
    order = []
    for item in items:
        key = _merge_key(item)
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(item)

    result = []
    for key in order:
        rows = groups[key]

        if len(rows) == 1:
            result.append(rows[0])
            continue

        chosen_rate = _resolve_rate(rows)

        if chosen_rate is None:
            # Multiple distinct non-zero rates — keep rows separate.
            result.extend(rows)
            continue

        # Safe to merge: sum qty, set the chosen rate, derive amount.
        total_qty = sum(flt(r.qty) for r in rows)
        first = rows[0]
        first.qty = total_qty
        first.rate = chosen_rate
        first.amount = flt(total_qty * chosen_rate)
        # Clear dn_detail so the overbilling validation skips this row.
        # so_detail is preserved for update_billed_amount_based_on_so.
        first.dn_detail = None
        result.append(first)

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
