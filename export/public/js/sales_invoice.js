/************************************
 * SALES INVOICE (PARENT)
 ************************************/
frappe.ui.form.on("Sales Invoice", {
    refresh(frm) {
        toggle_export_fields(frm);
        toggle_cif_total_by_currency(frm);
        toggle_sub_items_columns(frm);

        // Sub-items table configuration (only if field exists)
        if (frm.fields_dict.custom_sub_items) {
            frm.fields_dict.custom_sub_items.grid.cannot_add_rows = true;

            // Set fields as read-only, checking if they exist first
            const readonly_fields = ['parent_item', 'parent_item_name', 'sub_item_code', 'sub_item_name'];
            readonly_fields.forEach(function(fieldname) {
                if (frm.fields_dict.custom_sub_items.grid.docfields.find(f => f.fieldname === fieldname)) {
                    frm.fields_dict.custom_sub_items.grid.update_docfield_property(fieldname, 'read_only', 1);
                }
            });

            frm.refresh_field('custom_sub_items');
        }
    },

    custom_order_type(frm) {
        toggle_export_fields(frm);
        toggle_sub_items_columns(frm);
        calculate_si_cif_totals(frm);
    },

    currency(frm) {
        toggle_cif_total_by_currency(frm);
        calculate_si_cif_totals(frm);
    },

    validate(frm) {
        // Recalculate all sub-item values first
        if (frm.doc.custom_sub_items) {
            frm.doc.custom_sub_items.forEach(row => {
                calculate_sub_item_cif_values(frm, 'Sales Invoice Sub Item', row.name);
            });
        }

        apply_parent_values_from_sub_items(frm);
        calculate_si_cif_totals(frm);
    },

    onload_post_render(frm) {
        toggle_export_fields(frm);
        toggle_sub_items_columns(frm);
        carry_forward_sub_items(frm);
    }
});


function carry_forward_sub_items(frm) {
    // If custom_sub_items already populated, skip
    if (frm.doc.custom_sub_items && frm.doc.custom_sub_items.length > 0) return;

    // Get reference from items child table - try Sales Order first, then Delivery Note
    let ref_doctype = null;
    let ref_name = null;
    if (frm.doc.items && frm.doc.items.length > 0) {
         if (frm.doc.items[0].delivery_note) {
            ref_doctype = 'Delivery Note';
            ref_name = frm.doc.items[0].delivery_note;
        } else if (frm.doc.items[0].sales_order) {
            ref_doctype = 'Sales Order';
            ref_name = frm.doc.items[0].sales_order;
        }
    }

    if (ref_doctype && ref_name) {
        frappe.call({
            method: 'frappe.client.get',
            args: {
                doctype: ref_doctype,
                name: ref_name
            },
            callback: function(r) {
                if (r.message && r.message.custom_sub_items && r.message.custom_sub_items.length > 0) {
                    frm.doc.custom_sub_items = [];
                    r.message.custom_sub_items.forEach(function(sub_item) {
                        let new_sub = frm.add_child('custom_sub_items');
                        new_sub.parent_item = sub_item.parent_item;
                        new_sub.parent_item_name = sub_item.parent_item_name;
                        new_sub.sub_item_code = sub_item.sub_item_code;
                        new_sub.sub_item_name = sub_item.sub_item_name;
                        new_sub.sub_description = sub_item.sub_description;
                        new_sub.qty = sub_item.qty;
                        new_sub.custom_net_weight = sub_item.custom_net_weight;
                        new_sub.base_rate = sub_item.base_rate;
                        new_sub.rate = sub_item.rate;
                        new_sub.amount = sub_item.amount;
                        new_sub.custom_freight__insurance_ = sub_item.custom_freight__insurance_;
                        new_sub.custom_cif_unit_price = sub_item.custom_cif_unit_price;
                        new_sub.custom__cif_total_amount = sub_item.custom__cif_total_amount;
                        new_sub.custom_cif_unit_price_ = sub_item.custom_cif_unit_price_;
                        new_sub.custom___cif_total_amount = sub_item.custom___cif_total_amount;
                    });
                    frm.refresh_field('custom_sub_items');
                }
            }
        });
    }
}


function apply_parent_values_from_sub_items(frm) {
    if (!frm.doc.items || !frm.doc.custom_sub_items) return;

    let sub_items = frm.doc.custom_sub_items || [];
    if (!sub_items.length) return;

    let grouped = {};
    sub_items.forEach(sub => {
        if (!sub.parent_item) return;

        if (!grouped[sub.parent_item]) {
            grouped[sub.parent_item] = {
                rate_sum: 0,
                qty: null,
                has_qty: false,
                freight_pct: null,
                has_freight: false
            };
        }

        grouped[sub.parent_item].rate_sum += flt(sub.rate);

        if (!grouped[sub.parent_item].has_qty && (sub.qty || sub.qty === 0)) {
            grouped[sub.parent_item].qty = flt(sub.qty);
            grouped[sub.parent_item].has_qty = true;
        }

        if (!grouped[sub.parent_item].has_freight && (sub.custom_freight__insurance_ || sub.custom_freight__insurance_ === 0)) {
            grouped[sub.parent_item].freight_pct = flt(sub.custom_freight__insurance_);
            grouped[sub.parent_item].has_freight = true;
        }
    });

    let conversion_rate = flt(frm.doc.conversion_rate) || 1;

    (frm.doc.items || []).forEach(row => {
        let group = grouped[row.item_code];
        if (!group) return;

        let next_rate = group.rate_sum;
        let next_qty = group.has_qty ? group.qty : flt(row.qty);
        let next_freight = group.has_freight ? group.freight_pct : flt(row.custom_freight__insurance_);

        frappe.model.set_value(row.doctype, row.name, "rate", next_rate);

        if (group.has_qty) {
            frappe.model.set_value(row.doctype, row.name, "qty", next_qty);
        }

        if (group.has_freight) {
            frappe.model.set_value(row.doctype, row.name, "custom_freight__insurance_", next_freight);
        }

        let base_rate = next_rate * conversion_rate;
        let amount = next_rate * next_qty;

        frappe.model.set_value(row.doctype, row.name, "base_rate", base_rate);
        frappe.model.set_value(row.doctype, row.name, "amount", amount);

        calculate_cif_values(frm, row.doctype, row.name);
    });
}


function toggle_cif_total_by_currency(frm) {
    const show = frm.doc.currency !== "INR";
    frm.toggle_display("custom_cif_total_amount_", show);
}


function toggle_sub_items_columns(frm) {
    if (!frm.fields_dict.custom_sub_items) return;

    const is_export = frm.doc.custom_order_type === "Export";

    let grid = frm.fields_dict.custom_sub_items.grid;
    let columns_to_show = [];

    if (is_export) {
        // Display columns for Export order type
        columns_to_show = [
            { fieldname: 'parent_item', columns: 1 },
            { fieldname: 'sub_item_code', columns: 1 },
            { fieldname: 'qty', columns: 1 },
            { fieldname: 'rate', columns: 1 },
            { fieldname: 'amount', columns: 1 },
            { fieldname: 'custom_net_weight', columns: 1 },
            { fieldname: 'custom_freight__insurance_', columns: 1 },
            { fieldname: 'custom_cif_unit_price_', columns: 1 },
            { fieldname: 'custom___cif_total_amount', columns: 1 }
        ];
    } else {
        // Reset to default columns for non-Export order types
        columns_to_show = [];
    }


        let value = {};
        value[grid.doctype] = columns_to_show;

        frappe.model.user_settings.save(frm.doctype, 'GridView', value).then((r) => {
            frappe.model.user_settings[frm.doctype] = r.message || r;
            grid.reset_grid();
            frm.refresh_field("custom_sub_items");
        });

}


/************************************
 * SHOW / HIDE EXPORT FIELDS (ITEMS)
 ************************************/
function toggle_export_fields(frm) {
    if (!frm.fields_dict.items) return;

    const is_export = frm.doc.custom_order_type === "Export";

    let grid = frm.fields_dict.items.grid;
    let columns_to_show = [];

    if (is_export) {
        // Display columns for Export order type
        columns_to_show = [
            { fieldname: 'custom_duty_drawback', columns: 1 },
            { fieldname: 'item_code', columns: 1 },
            { fieldname: 'qty', columns: 1 },
            { fieldname: 'rate', columns: 1 },
            { fieldname: 'amount', columns: 1 },
            { fieldname: 'custom_net_weight', columns: 1 },
            { fieldname: 'custom_freight__insurance_', columns: 1 },
            { fieldname: 'custom_cif_unit_price_', columns: 1 },
            { fieldname: 'custom___cif_total_amount', columns: 1 }
        ];
    } else {
        // Reset to default columns for non-Export order types
        columns_to_show = [
            { fieldname: 'item_code', columns: 2 },
            { fieldname: 'qty', columns: 2 },
            { fieldname: 'rate', columns: 2 },
            { fieldname: 'amount', columns: 2 },];
    }

    try {
        let value = {};
        value[grid.doctype] = columns_to_show;

        frappe.model.user_settings.save(frm.doctype, 'GridView', value).then((r) => {
            frappe.model.user_settings[frm.doctype] = r.message || r;
            grid.reset_grid();
            frm.refresh_field("items");
        });

    } catch (e) {
        console.log("Error toggling export fields:", e);
    }
}



frappe.ui.form.on("Sales Invoice Item", {
    items_add(frm, cdt, cdn) {
        // Ensure visibility is set when new row is added
        setTimeout(() => {
            toggle_export_fields(frm);
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
        let row = locals[cdt][cdn];

        if (row.item_code) {
            // First, remove any existing sub-items for this parent item to avoid duplicates
            let existing_sub_items = frm.doc.custom_sub_items || [];
            frm.doc.custom_sub_items = existing_sub_items.filter(function(sub) {
                return sub.parent_item !== row.item_code;
            });

            frappe.call({
                method: 'frappe.client.get',
                args: {
                    doctype: 'Item',
                    name: row.item_code
                },
                callback: function(r) {
                    if (r.message && r.message.custom_sub_items && r.message.custom_sub_items.length > 0) {
                        r.message.custom_sub_items.forEach(function(sub_item) {
                            let sub_row = frm.add_child('custom_sub_items');
                            sub_row.parent_item = row.item_code;
                            // Only set parent_item_name if field exists
                            if (frm.fields_dict.custom_sub_items.grid.docfields.find(f => f.fieldname === 'parent_item_name')) {
                                sub_row.parent_item_name = row.item_name;
                            }
                            sub_row.sub_item_code = sub_item.sub_item_code;
                            sub_row.sub_item_name = sub_item.sub_item_name;
                            sub_row.sub_description = sub_item.sub_description;
                        });

                        frm.refresh_field('custom_sub_items');
                        frappe.show_alert({
                            message: __('Sub-items populated for {0}', [row.item_code]),
                            indicator: 'green'
                        }, 3);
                    }

                    // Toggle visibility after operation
                    // toggle_sub_items_table_visibility(frm);
                }
            });
        } else {
            // Recalculate when item changes
            setTimeout(() => {
                calculate_cif_values(frm, cdt, cdn);
            }, 300);
        }
    },

    before_items_remove(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.item_code && frm.doc.custom_sub_items) {
            // Remove all sub-items related to this parent item
            frm.doc.custom_sub_items = frm.doc.custom_sub_items.filter(function(sub) {
                return sub.parent_item !== row.item_code;
            });
            frm.refresh_field('custom_sub_items');

            // Toggle visibility after removal
            // toggle_sub_items_table_visibility(frm);
        }
    }
});



frappe.ui.form.on("Sales Invoice Sub Items", {
    rate(frm, cdt, cdn) {
        calculate_sub_item_base_rate(frm, cdt, cdn);
        calculate_sub_item_cif_values(frm, cdt, cdn);
    },

    qty(frm, cdt, cdn) {
        calculate_sub_item_cif_values(frm, cdt, cdn);
    },

    custom_freight__insurance_(frm, cdt, cdn) {
        calculate_sub_item_cif_values(frm, cdt, cdn);
    }
});


/************************************
 * ROW-LEVEL CIF CALCULATION
 ************************************/
function calculate_cif_values(frm, cdt, cdn) {
    if (frm.doc.custom_order_type !== "Export") return;

    let row = locals[cdt][cdn];

    let base_rate = flt(row.base_rate); // company currency (INR)
    let rate = flt(row.rate);           // order currency
    let qty = flt(row.qty);
    let freight_pct = flt(row.custom_freight__insurance_);

    // Company currency CIF
    let cif_unit_company = base_rate + (base_rate * freight_pct / 100);
    let cif_total_company = cif_unit_company * qty;

    // Order currency CIF
    let cif_unit_currency = rate + (rate * freight_pct / 100);
    let cif_total_currency = cif_unit_currency * qty;

    frappe.model.set_value(cdt, cdn, "custom_cif_unit_price", cif_unit_company);
    frappe.model.set_value(cdt, cdn, "custom__cif_total_amount", cif_total_company);
    frappe.model.set_value(cdt, cdn, "custom_cif_unit_price_", cif_unit_currency);
    frappe.model.set_value(cdt, cdn, "custom___cif_total_amount", cif_total_currency);

    // Recalculate totals after updating row values
    setTimeout(() => {
        calculate_si_cif_totals(frm);
    }, 100);
}


/************************************
 * SUB-ITEM BASE RATE CALCULATION
 ************************************/
function calculate_sub_item_base_rate(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    let rate = flt(row.rate);
    let conversion_rate = flt(frm.doc.conversion_rate);

    if (!conversion_rate) {
        conversion_rate = 1;
    }

    let base_rate = rate * conversion_rate;
    frappe.model.set_value(cdt, cdn, "base_rate", base_rate);
}


/************************************
 * SUB-ITEM ROW-LEVEL CIF CALCULATION
 ************************************/
function calculate_sub_item_cif_values(frm, cdt, cdn) {
    let row = locals[cdt][cdn];

    let base_rate = flt(row.base_rate);
    let rate = flt(row.rate);
    let qty = flt(row.qty);
    let freight_pct = flt(row.custom_freight__insurance_);

    // Calculate Amount (always)
    let amount = rate * qty;
    frappe.model.set_value(cdt, cdn, "amount", amount);

    // CIF calculations only for Export orders
    if (frm.doc.custom_order_type !== "Export") return;

    // Company currency CIF
    let cif_unit_company = base_rate + (base_rate * freight_pct / 100);
    let cif_total_company = cif_unit_company * qty;

    // Order currency CIF
    let cif_unit_currency = rate + (rate * freight_pct / 100);
    let cif_total_currency = cif_unit_currency * qty;

    frappe.model.set_value(cdt, cdn, "custom_cif_unit_price", cif_unit_company);
    frappe.model.set_value(cdt, cdn, "custom__cif_total_amount", cif_total_company);
    frappe.model.set_value(cdt, cdn, "custom_cif_unit_price_", cif_unit_currency);
    frappe.model.set_value(cdt, cdn, "custom___cif_total_amount", cif_total_currency);
}


/************************************
 * SALES INVOICE TOTAL CIF
 ************************************/
function calculate_si_cif_totals(frm) {
    if (frm.doc.custom_order_type !== "Export") {
        // Clear totals if not export
        frm.set_value("custom_cif_total_amount_company_currency", 0);
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


/* ===== OLD CODE (COMMENTED) =====

frappe.ui.form.on("Sales Invoice", {
    refresh(frm) {
        toggle_export_fields_si(frm);
        toggle_cif_total_by_currency(frm);
    },

    custom_order_type(frm) {
        toggle_export_fields_si(frm);
        calculate_si_cif_totals(frm);
    },

    currency(frm) {
        toggle_cif_total_by_currency(frm);
        calculate_si_cif_totals(frm);
    },

    validate(frm) {
        calculate_si_cif_totals(frm);
    },

    onload(frm) {
        toggle_export_fields_si(frm);
    }
});


function toggle_export_fields_si(frm) {
    if (!frm.fields_dict.items) return;

    const is_export = frm.doc.custom_order_type === "Export";
    const grid = frm.fields_dict.items.grid;

    const export_fields = [
        "custom_net_weight",
        "custom_cif_unit_price",
        "custom_cif_unit_price_",
        "custom_freight__insurance_",
        "custom__cif_total_amount",
        "custom___cif_total_amount"
    ];

    export_fields.forEach(fieldname => {
        grid.update_docfield_property(
            fieldname,
            "hidden",
            is_export ? 0 : 1
        );

        grid.update_docfield_property(
            fieldname,
            "in_list_view",
            is_export ? 1 : 0
        );
    });

    frm.refresh_field("items");
}


frappe.ui.form.on("Sales Invoice Item", {
    items_add(frm) {
        setTimeout(() => {
            toggle_export_fields_si(frm);
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


function toggle_cif_total_by_currency(frm) {
    const show = frm.doc.currency !== "INR";
    frm.toggle_display("custom_cif_total_amount_", show);
}


function calculate_cif_values(frm, cdt, cdn) {
    if (frm.doc.custom_order_type !== "Export") return;

    const row = locals[cdt][cdn];

    const base_rate = flt(row.base_rate);
    const rate = flt(row.rate);
    const qty = flt(row.qty);
    const freight_pct = flt(row.custom_freight__insurance_);

    const cif_unit_company =
        base_rate + (base_rate * freight_pct / 100);
    const cif_total_company = cif_unit_company * qty;

    const cif_unit_currency =
        rate + (rate * freight_pct / 100);
    const cif_total_currency = cif_unit_currency * qty;

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
        calculate_si_cif_totals(frm);
    }, 100);
}


function calculate_si_cif_totals(frm) {
    if (frm.doc.custom_order_type !== "Export") {
        frm.set_value("custom_cif_total_amount_company_currency", 0);
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

===== END OLD CODE ===== */
