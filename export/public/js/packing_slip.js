/************************************
 * PACKING SLIP (PARENT)
 ************************************/
frappe.ui.form.on("Packing Slip", {
    refresh(frm) {
        toggle_export_fields(frm);
        toggle_cif_total_by_currency(frm);
        toggle_sub_items_columns(frm);
        hide_items_rows(frm);
        // recalculate_all_cubic_rows(frm);

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
        calculate_ps_cif_totals(frm);
    },

    custom_currency(frm) {
        toggle_cif_total_by_currency(frm);
        calculate_ps_cif_totals(frm);
    },

    validate(frm) {
        // Recalculate all sub-item values first
        if (frm.doc.custom_sub_items) {
            frm.doc.custom_sub_items.forEach(row => {
                calculate_sub_item_cif_values(frm, 'Packing Slip Sub Items', row.name);
            });
        }

        apply_parent_values_from_sub_items(frm);
        calculate_ps_cif_totals(frm);
        recalculate_all_cubic_rows(frm);

        hide_items_rows(frm);
    },

    onload_post_render(frm) {
        toggle_export_fields(frm);
        toggle_sub_items_columns(frm);

        set_currency(frm);

        carry_forward_sub_items(frm);
        hide_items_rows(frm);
        // recalculate_all_cubic_rows(frm);
    }
});

function set_currency(frm) {
    if (frm.doc.docstatus !== 0) return;

    if (!frm.doc.delivery_note) return;

    // Skip if currency already set (existing document) — avoids making form dirty on open
    if (frm.doc.custom_currency) return;

    frappe.db.get_value("Delivery Note", frm.doc.delivery_note, "currency")
    .then(r => {

        if (!r.message) return;

        let currency = r.message.currency;

        frm.set_value("custom_currency", currency);

        (frm.doc.items || []).forEach(row => {
            frappe.model.set_value(row.doctype, row.name, "custom_currency", currency);
        });

        frm.refresh_field("items");

    });
}


function carry_forward_sub_items(frm) {
    // Never mutate a submitted or cancelled document
    if (frm.doc.docstatus !== 0) return;

    // If custom_sub_items already populated, skip
    if (frm.doc.custom_sub_items && frm.doc.custom_sub_items.length > 0) return;

    // Get Delivery Note reference from parent-level delivery_note field
    let delivery_note_ref = frm.doc.delivery_note;

    if (delivery_note_ref) {
        frappe.call({
            method: 'frappe.client.get',
            args: {
                doctype: 'Delivery Note',
                name: delivery_note_ref
            },
            callback: function(r) {

                if (r.message && r.message.custom_sub_items && r.message.custom_sub_items.length > 0) {
                    frm.doc.custom_sub_items = [];
                    r.message.custom_sub_items.forEach(function(sub_item) {
                        let new_sub = frm.add_child('custom_sub_items');
                        new_sub.parent_row_uid = sub_item.parent_row_uid;
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
                        frappe.model.set_value(new_sub.doctype, new_sub.name, "custom_currency", r.message.currency);
                        calculate_sub_item_cif_values(frm, "Packing Slip Sub Items", new_sub.name);
                        // new_sub.custom_cif_unit_price = sub_item.custom_cif_unit_price;
                        // new_sub.custom__cif_total_amount = sub_item.custom__cif_total_amount;
                        // new_sub.custom_cif_unit_price_ = sub_item.custom_cif_unit_price_;
                        // new_sub.custom___cif_total_amount = sub_item.custom___cif_total_amount;
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

    // Group sub-items by parent_row_uid (unique per parent row)
    let grouped = {};
    sub_items.forEach(sub => {
        let key = sub.parent_row_uid;
        if (!key) return;

        if (!grouped[key]) {
            grouped[key] = {
                rate_sum: 0,
                qty: null,
                has_qty: false,
                freight_pct: null,
                has_freight: false
            };
        }

        grouped[key].rate_sum += flt(sub.rate);

        if (!grouped[key].has_qty && (sub.qty || sub.qty === 0)) {
            grouped[key].qty = flt(sub.qty);
            grouped[key].has_qty = true;
        }

        if (!grouped[key].has_freight && (sub.custom_freight__insurance_ || sub.custom_freight__insurance_ === 0)) {
            grouped[key].freight_pct = flt(sub.custom_freight__insurance_);
            grouped[key].has_freight = true;
        }
    });

    let conversion_rate = flt(frm.doc.conversion_rate) || 1;
    if (!conversion_rate) conversion_rate = 1;

    (frm.doc.items || []).forEach(row => {
        let group = grouped[row.custom_row_uid];
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
    frm.toggle_display("custom_cif_total_amount_", false);
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
            { fieldname: 'custom_unit_weight', columns: 1 },
            { fieldname: 'custom__gross_weight', columns: 1 },
            { fieldname: 'custom_box', columns: 1 },
            { fieldname: 'custom_length', columns: 1 },
            { fieldname: 'custom_width', columns: 1 },
            { fieldname: 'custom_height', columns: 1 },
            { fieldname: 'custom_cubic_feet', columns: 1 },
            { fieldname: 'custom_cubic_meter', columns: 1 }
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
 * HIDE Bank Charges (ITEMS)
 ************************************/

function hide_items_rows(frm) {
    const grid = frm.fields_dict?.items?.grid;
    if (!grid) return;

    const hide = () => {
        const rows = grid.grid_rows || [];
        if (!rows.length) return;

        rows.forEach((row) => {
            if (row?.doc?.item_code === "Bank Charges") {
                row.wrapper.hide();
            }
        });
    };

    setTimeout(hide, 0);
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
            { fieldname: 'item_code', columns: 1 },
            { fieldname: 'qty', columns: 1 },
            { fieldname: 'custom_unit_weight', columns: 1 },
            { fieldname: 'custom__gross_weight', columns: 1 },
            { fieldname: 'custom_box', columns: 1 },
            { fieldname: 'custom_length', columns: 1 },
            { fieldname: 'custom_width', columns: 1 },
            { fieldname: 'custom_height', columns: 1 },
            { fieldname: 'custom_cubic_feet', columns: 1 },
            { fieldname: 'custom_cubic_meter', columns: 1 },
        ];
    } else {
        // Reset to default columns for non-Export order types
        columns_to_show = [
            { fieldname: 'item_code', columns: 1 },
            { fieldname: 'qty', columns: 1 },
            { fieldname: 'custom_unit_weight', columns: 1 },
            { fieldname: 'custom__gross_weight', columns: 1 },
            { fieldname: 'custom_box', columns: 1 },
            { fieldname: 'custom_length', columns: 1 },
            { fieldname: 'custom_width', columns: 1 },
            { fieldname: 'custom_height', columns: 1 },
            { fieldname: 'custom_cubic_feet', columns: 1 },
            { fieldname: 'custom_cubic_meter', columns: 1 },
        ];
    }

    try {
        let value = {};
        value[grid.doctype] = columns_to_show;

        frappe.model.user_settings.save(frm.doctype, 'GridView', value).then((r) => {
            frappe.model.user_settings[frm.doctype] = r.message || r;
            grid.reset_grid();
            frm.refresh_field("items");
            hide_items_rows(frm);
        });

    } catch (e) {
        console.log("Error toggling export fields:", e);
    }
}



frappe.ui.form.on("Packing Slip Item", {
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
            // Generate a unique ID for this parent row if it doesn't have one,
            // or regenerate if item_code changed (old sub-items need cleanup)
            let old_uid = row.custom_row_uid;
            let new_uid = frappe.utils.get_random(8) + '_' + Date.now();
            frappe.model.set_value(cdt, cdn, 'custom_row_uid', new_uid);

            // Remove any existing sub-items for the old UID of this row
            if (old_uid) {
                let existing_sub_items = frm.doc.custom_sub_items || [];
                frm.doc.custom_sub_items = existing_sub_items.filter(function(sub) {
                    return sub.parent_row_uid !== old_uid;
                });
            }

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
                            sub_row.parent_row_uid = new_uid;
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
        if (row.custom_row_uid && frm.doc.custom_sub_items) {
            // Remove only sub-items linked to this specific row's UID
            frm.doc.custom_sub_items = frm.doc.custom_sub_items.filter(function(sub) {
                return sub.parent_row_uid !== row.custom_row_uid;
            });
            frm.refresh_field('custom_sub_items');
        }
    },

    custom_length(frm, cdt, cdn) {
        calculate_cubic(frm, cdt, cdn);
    },

    custom_width(frm, cdt, cdn) {
        calculate_cubic(frm, cdt, cdn);
    },

    custom_height(frm, cdt, cdn) {
        calculate_cubic(frm, cdt, cdn);
    },

    form_render(frm) {
        hide_items_rows(frm);
    }
});



frappe.ui.form.on("Packing Slip Sub Items", {
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
 * CUBIC FEET / CUBIC METER CALCULATION
 ************************************/
function recalculate_all_cubic_rows(frm) {
    if (frm.doc.docstatus !== 0) return;
    (frm.doc.items || []).forEach(row => {
        calculate_cubic(frm, row.doctype, row.name);
    });
}

function calculate_cubic(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    let l = flt(row.custom_length);
    let w = flt(row.custom_width);
    let h = flt(row.custom_height);

    let cubic_feet = 0.00058 * l * w * h;
    let cubic_meter = 0.0283 * cubic_feet;

    frappe.model.set_value(cdt, cdn, "custom_cubic_feet", cubic_feet);
    frappe.model.set_value(cdt, cdn, "custom_cubic_meter", cubic_meter);
}


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
        calculate_ps_cif_totals(frm);
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
    let row = locals[cdt] && locals[cdt][cdn];

    // Fallback: if row not in locals, find it in frm.doc
    if (!row) {
        row = frm.doc.custom_sub_items.find(r => r.name === cdn);
    }

    if (!row) return; // Exit if row still not found

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
 * PACKING SLIP TOTAL CIF
 ************************************/
function calculate_ps_cif_totals(frm) {
    if (frm.doc.custom_order_type !== "Export") {
        // Clear totals if not export
        frm.set_value("custom_cif_total_amount_company_currency", 0);
        frm.set_value("custom_cif_total_amount_", 0);
        return;
    }

    let total_company = 0;
    let total_currency = 0;

    (frm.doc.items || []).forEach(row => {

        if (row.item_code === "Bank Charges") return;

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

frappe.ui.form.on("Packing Slip", {
    refresh(frm) {
        toggle_export_custom_fields(frm);
    },

    custom_order_type(frm) {
        toggle_export_custom_fields(frm);
    },

    onload(frm) {
        toggle_export_custom_fields(frm);
    }
});


function toggle_export_custom_fields(frm) {
    if (!frm.fields_dict.items) {
        console.log("Items field not found");
        return;
    }

    const is_export = frm.doc.custom_order_type === "Export";
    console.log("Order Type:", frm.doc.custom_order_type, "Is Export:", is_export);

    const export_fields = [
        "custom__gross_weight",
        "custom_unit_weight",
        "custom_length",
        "custom_width",
        "custom_height",
        "custom_cubic_meter",
        "custom_cubic_feet",
        "custom_box",
        "custom_customer_part_number",
        "net_weight"
    ];

    // Method 1: Update the doctype meta
    export_fields.forEach(fieldname => {
        const meta = frappe.meta.get_docfield("Packing Slip Item", fieldname);
        if (meta) {
            meta.hidden = is_export ? 0 : 1;
            meta.in_list_view = is_export ? 1 : 0;
        }
    });

    // Method 2: Update grid properties
    const grid = frm.fields_dict.items.grid;
    export_fields.forEach(fieldname => {
        grid.update_docfield_property(fieldname, "hidden", is_export ? 0 : 1);
        grid.update_docfield_property(fieldname, "in_list_view", is_export ? 1 : 0);
    });

    // Method 3: Force complete grid refresh
    grid.reset_grid();
    frm.refresh_field("items");
}


frappe.ui.form.on("Packing Slip Item", {
    items_add(frm, cdt, cdn) {
        setTimeout(() => {
            toggle_export_custom_fields(frm);
        }, 100);
    }
});

===== END OLD CODE ===== */
