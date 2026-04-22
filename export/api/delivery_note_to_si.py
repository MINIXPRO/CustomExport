import frappe
from frappe.utils import flt
from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice


# Fields copied from each DN Sub Item row → Sales Invoice Sub Item row.
# All fieldnames are identical on both doctypes; no remap needed.
_DN_TO_SI_SUB_ITEM_FIELDS = [
    "parent_item",
    "parent_item_name",
    "sub_item_code",
    "sub_item_name",
    "sub_description",
    "qty",
    "custom_net_weight",
    "base_rate",
    "rate",
    "amount",
    "custom_freight__insurance_",
    "custom_cif_unit_price",
    "custom__cif_total_amount",
    "custom_cif_unit_price_",
    "custom___cif_total_amount",
    "custom_customer_po_no",
    "parent_row_uid",
]


# Fields that must differ to keep rows separate (grouping key).
#
# Merge rule: same item_code + not kit item → merge into one SI row.
# Fields like warehouse, cost_center, income_account, sales_order, so_detail
# must NOT block the merge — they may legitimately differ across DN rows for
# the same item in a split-shipment workflow.
# Rate differences are the only commercially meaningful split signal and are
# handled separately by _resolve_rate (multiple distinct non-zero rates → keep separate).
MERGE_KEY_FIELDS = [
    "item_code",
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


def _merge_items(items, kit_item_codes=None):
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

    KIT items
    ---------
    Items whose item_code appears in kit_item_codes are never merged,
    regardless of how many rows share the same grouping key.
    """
    if kit_item_codes is None:
        kit_item_codes = set()

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

        # KIT items must never be merged — keep every row separate.
        if rows[0].item_code in kit_item_codes:
            result.extend(rows)
            continue

        chosen_rate = _resolve_rate(rows)

        if chosen_rate is None:
            # Multiple distinct non-zero rates in the DN.
            # If all rows originate from the same SO line, the DN rates may simply
            # contain a data-entry error.  Fall back to the canonical SO item rate
            # so the merge can still proceed at the correct contracted price.
            so_details = {str(r.so_detail or "") for r in rows}
            if len(so_details) == 1 and "" not in so_details:
                so_rate = flt(frappe.db.get_value("Sales Order Item", so_details.pop(), "rate"))
                if so_rate:
                    chosen_rate = so_rate
                else:
                    result.extend(rows)
                    continue
            else:
                # Genuinely different SO lines with different rates — keep separate.
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


def _carry_forward_dn_sub_items(source_name, doc):
    """
    Copy DN custom_sub_items rows into the Sales Invoice's custom_sub_items table.
    Sub items are grouped and merged by (parent_item, sub_item_code) so that rows
    split across multiple DN item rows of the same parent item are consolidated.

    Merge key: parent_item (item_code) + sub_item_code.
    Summed fields: qty, amount, custom_net_weight, custom__cif_total_amount,
                   custom___cif_total_amount.
    All other fields are taken from the first row in the group.

    SI item lookup uses parent_item (item_code) instead of parent_row_uid so that
    sub items linked to DN rows that were merged away (whose custom_row_uid is no
    longer present in doc.items) are still resolved correctly via the surviving
    merged SI item.

    NULL parent_item (legacy / orphaned rows)
    -----------------------------------------
    DN sub items without a parent_item are carried forward with parent_row_uid=NULL.
    """
    dn_sub_items = frappe.get_all(
        "Delivery Note Sub Items",
        filters={"parent": source_name},
        fields=_DN_TO_SI_SUB_ITEM_FIELDS,
    )
    if not dn_sub_items:
        return

    # Build customer_item_code lookup: sub_item_code → ref_code from Item Customer Detail.
    customer = doc.customer or frappe.db.get_value("Sales Invoice", doc.name, "customer")
    sub_item_codes = list({d.sub_item_code for d in dn_sub_items if d.sub_item_code})
    customer_item_map = {}
    if sub_item_codes and customer:
        rows = frappe.get_all(
            "Item Customer Detail",
            filters={"parent": ["in", sub_item_codes], "customer_name": customer},
            fields=["parent", "ref_code"],
        )
        customer_item_map = {r.parent: r.ref_code for r in rows}

    # Build SI item lookup by item_code (post-merge).
    # For kit items that have multiple rows, the first occurrence is used.
    si_item_by_code = {}
    for item in doc.items:
        code = item.item_code
        if code and code not in si_item_by_code:
            si_item_by_code[code] = item

    # Snapshot of (parent_row_uid, sub_item_code) pairs already in the SI.
    existing = {
        (row.parent_row_uid, row.sub_item_code)
        for row in (doc.get("custom_sub_items") or [])
    }

    # Group DN sub items by (parent_item, sub_item_code), preserving insertion order.
    sub_groups = {}
    sub_order = []
    for dn_sub in dn_sub_items:
        key = (dn_sub.parent_item or "", dn_sub.sub_item_code or "")
        if key not in sub_groups:
            sub_groups[key] = []
            sub_order.append(key)
        sub_groups[key].append(dn_sub)

    for key in sub_order:
        group = sub_groups[key]
        parent_item, sub_item_code = key

        if parent_item:
            si_item = si_item_by_code.get(parent_item)
            if not si_item:
                # Parent DN item was filtered out (fully billed) — skip.
                continue
            parent_uid_for_si = si_item.custom_row_uid or None
        else:
            # Orphaned sub item — carry forward with NULL parent_row_uid.
            parent_uid_for_si = None

        if (parent_uid_for_si, sub_item_code) in existing:
            # Already present — skip to prevent duplication.
            continue

        # Build the SI sub item row from the first group member, then sum numeric fields.
        first = group[0]
        sub = frappe._dict({field: first.get(field) for field in _DN_TO_SI_SUB_ITEM_FIELDS})
        sub["parent_row_uid"] = parent_uid_for_si
        sub["customer_item_code"] = customer_item_map.get(first.sub_item_code) or None

        if len(group) > 1:
            sub["qty"]                       = sum(flt(r.qty)                       for r in group)
            sub["amount"]                    = sum(flt(r.amount)                    for r in group)
            sub["custom_net_weight"]         = sum(flt(r.custom_net_weight)         for r in group)
            sub["custom__cif_total_amount"]  = sum(flt(r.custom__cif_total_amount)  for r in group)
            sub["custom___cif_total_amount"] = sum(flt(r.custom___cif_total_amount) for r in group)

        doc.append("custom_sub_items", sub)
        existing.add((parent_uid_for_si, sub_item_code))


def _get_fully_billed_dn_item_names(source_name):
    """
    Return the set of Delivery Note Item row names that are already fully billed.

    Two complementary detection strategies are used:

    Strategy A — billed_amt check
    ------------------------------
    Works for DN items that were invoiced as single (non-merged) SI rows, where
    ERPNext preserves dn_detail and standard post-submission hooks update billed_amt.

    Strategy B — merged SI row check
    ----------------------------------
    When our merge logic groups N same-key DN rows into one SI row, it clears
    dn_detail (to avoid the overbilling validator).  If the source DN items also
    have no so_detail, ERPNext's update_billed_amount_based_on_so cannot trace back
    and billed_amt stays 0 forever — making those rows appear unbillable on any
    second SI attempt.

    We compensate by directly querying submitted SI items that:
      • reference this delivery_note
      • have dn_detail = NULL  (our merge cleared it)
    and treating every DN item with a matching item_code as already covered.

    Together the two strategies correctly identify all billed DN rows regardless
    of whether they were merged or not.
    """
    dn_items = frappe.get_all(
        "Delivery Note Item",
        filters={"parent": source_name},
        fields=["name", "item_code", "amount", "billed_amt"],
    )

    over_billing_allowance = (
        frappe.db.get_single_value("Accounts Settings", "over_billing_allowance") or 0
    )
    max_factor = 1 + over_billing_allowance / 100.0

    fully_billed = set()

    # Strategy A: billed_amt tracks (single rows with dn_detail preserved)
    for d in dn_items:
        amount = d.amount or 0
        billed = d.billed_amt or 0
        if amount > 0 and billed >= amount * max_factor - 0.001:
            fully_billed.add(d.name)
        elif amount == 0 and billed > 0:
            fully_billed.add(d.name)

    # Strategy B: merged SI rows (dn_detail = NULL) already covering these DN items.
    # A merged row's item_code tells us which DN item group it covers entirely.
    merged_billed = frappe.db.sql(
        """
        SELECT DISTINCT sii.item_code
        FROM `tabSales Invoice Item` sii
        JOIN `tabSales Invoice` si ON si.name = sii.parent
        WHERE sii.delivery_note = %s
          AND (sii.dn_detail IS NULL OR sii.dn_detail = '')
          AND si.docstatus = 1
        """,
        source_name,
        as_dict=True,
    )
    merged_billed_codes = {r.item_code for r in merged_billed}

    for d in dn_items:
        if d.item_code in merged_billed_codes:
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

    # 3. Identify KIT items — these must never be merged into a single SI row.
    item_codes = list({item.item_code for item in doc.items if item.item_code})
    kit_item_codes = set()
    if item_codes:
        kit_item_codes = {
            r.name
            for r in frappe.get_all(
                "Item",
                filters={"name": ["in", item_codes], "custom_is_kit": 1},
                fields=["name"],
            )
        }

    # 4. Merge split rows on the Sales Invoice (KIT items are kept separate)
    doc.items = _merge_items(doc.items, kit_item_codes=kit_item_codes)

    # Re-index row numbers so the child table is internally consistent
    for idx, item in enumerate(doc.items, start=1):
        item.idx = idx

    # 5. Carry custom_customer_order_number from DN Item to SI Item (by item_code).
    dn_items_for_order = frappe.get_all(
        "Delivery Note Item",
        filters={"parent": source_name},
        fields=["item_code", "custom_customer_order_number"],
    )
    dn_order_map = {d.item_code: d.custom_customer_order_number for d in dn_items_for_order if d.custom_customer_order_number}
    for si_item in doc.items:
        if si_item.item_code in dn_order_map:
            si_item.custom_customer_order_number = dn_order_map[si_item.item_code]

    # 7. Reset weight_per_unit from Item Master
    item_codes = list({item.item_code for item in doc.items if item.item_code})
    if item_codes:
        weight_map = {
            r.name: r.weight_per_unit
            for r in frappe.get_all("Item", filters={"name": ["in", item_codes]}, fields=["name", "weight_per_unit"])
        }
        for item in doc.items:
            if item.item_code in weight_map:
                item.weight_per_unit = weight_map[item.item_code]

    # 8. Carry forward DN sub items into the Sales Invoice sub items table.
    _carry_forward_dn_sub_items(source_name, doc)

    return doc
