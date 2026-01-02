/************************************
 * DELIVERY NOTE (PARENT)
 ************************************/
frappe.ui.form.on("Delivery Note", {
    refresh(frm) {
        toggle_export_fields_dn(frm);
        toggle_cif_total_by_currency(frm);
    },

    custom_order_type(frm) {
        toggle_export_fields_dn(frm);
        calculate_so_cif_totals(frm);
    },

    currency(frm) {
        toggle_cif_total_by_currency(frm);
        calculate_so_cif_totals(frm);
    },

    validate(frm) {
        calculate_so_cif_totals(frm);
    },

    onload(frm) {
        toggle_export_fields_dn(frm);
    }
});


/************************************
 * SHOW / HIDE EXPORT FIELDS (ITEMS)
 ************************************/
function toggle_export_fields_dn(frm) {
    if (!frm.fields_dict.items) return;

    const is_export = frm.doc.custom_order_type === "Export";

    const export_fields = [
        "custom_net_weight",
        "custom_cif_unit_price",
        "custom_cif_unit_price_",
        "custom_freight__insurance_",
        "custom__cif_total_amount",
        "custom___cif_total_amount"
    ];

    const grid = frm.fields_dict.items.grid;

    export_fields.forEach(fieldname => {
        // Form view (row popup)
        grid.update_docfield_property(
            fieldname,
            "hidden",
            is_export ? 0 : 1
        );

        // Grid list view
        grid.update_docfield_property(
            fieldname,
            "in_list_view",
            is_export ? 1 : 0
        );
    });

    // Refresh grid safely
    frm.refresh_field("items");
}


/************************************
 * DELIVERY NOTE ITEM EVENTS
 ************************************/
frappe.ui.form.on("Delivery Note Item", {
    items_add(frm) {
        setTimeout(() => {
            toggle_export_fields_dn(frm);
        }, 100);
    },

    rate(frm, cdt, cdn) {
        calculate_cif_values(frm, cdt, cdn);
    },

    qty(frm, cdt, cdn) {
        calculate_cif_values(frm, cdt, cdn);
    },

    custom_freight__insurance_(frm, cdt, cdn) {
        calculate_cif_values(frm, cdt, cdn);
    },

    item_code(frm, cdt, cdn) {
        setTimeout(() => {
            calculate_cif_values(frm, cdt, cdn);
        }, 300);
    }
});


/************************************
 * SHOW / HIDE CIF TOTAL BY CURRENCY
 ************************************/
function toggle_cif_total_by_currency(frm) {
    const show = frm.doc.currency !== "INR";
    frm.toggle_display("custom_cif_total_amount_", show);
}


/************************************
 * ROW-LEVEL CIF CALCULATION
 ************************************/
function calculate_cif_values(frm, cdt, cdn) {
    if (frm.doc.custom_order_type !== "Export") return;

    let row = locals[cdt][cdn];

    let base_rate = flt(row.base_rate);
    let rate = flt(row.rate);
    let qty = flt(row.qty);
    let freight_pct = flt(row.custom_freight__insurance_);

    // Company currency CIF
    let cif_unit_company =
        base_rate + (base_rate * freight_pct / 100);
    let cif_total_company = cif_unit_company * qty;

    // Order currency CIF
    let cif_unit_currency =
        rate + (rate * freight_pct / 100);
    let cif_total_currency = cif_unit_currency * qty;

    frappe.model.set_value(
        cdt,
        cdn,
        "custom_cif_unit_price",
        cif_unit_company
    );

    frappe.model.set_value(
        cdt,
        cdn,
        "custom__cif_total_amount",
        cif_total_company
    );

    frappe.model.set_value(
        cdt,
        cdn,
        "custom_cif_unit_price_",
        cif_unit_currency
    );

    frappe.model.set_value(
        cdt,
        cdn,
        "custom___cif_total_amount",
        cif_total_currency
    );

    setTimeout(() => {
        calculate_so_cif_totals(frm);
    }, 100);
}


/************************************
 * DELIVERY NOTE TOTAL CIF
 ************************************/
function calculate_so_cif_totals(frm) {
    if (frm.doc.custom_order_type !== "Export") {
        frm.set_value(
            "custom_cif_total_amount_company_currency",
            0
        );
        frm.set_value("custom_cif_total_amount_", 0);
        return;
    }

    let total_company = 0;
    let total_currency = 0;

    (frm.doc.items || []).forEach(row => {
        total_company += flt(row.custom__cif_total_amount);
        total_currency += flt(row.custom___cif_total_amount);
    });

    frm.set_value(
        "custom_cif_total_amount_company_currency",
        total_company
    );

    frm.set_value(
        "custom_cif_total_amount_",
        total_currency
    );
}
