/************************************
 * SALES ORDER (PARENT)
 ************************************/
frappe.ui.form.on("Sales Order", {
    refresh(frm) {
        toggle_export_fields(frm);
        toggle_cif_total_by_currency(frm);
    },

    order_type(frm) {
        toggle_export_fields(frm);
        calculate_so_cif_totals(frm);
    },

    currency(frm) {
        toggle_cif_total_by_currency(frm);
        calculate_so_cif_totals(frm);
    },

    validate(frm) {
        calculate_so_cif_totals(frm);
        // Don't toggle fields during validate to avoid errors
    },

    onload(frm) {
        toggle_export_fields(frm);
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
 * SHOW / HIDE EXPORT FIELDS (ITEMS)
 ************************************/
function toggle_export_fields(frm) {
    if (!frm.fields_dict.items) return;
    
    const is_export = frm.doc.order_type === "Export";
    
    // Fields to toggle in grid view (in_list_view fields)
    const export_fields = [
        "custom_net_weight",
        "custom_cif_unit_price",
        "custom_cif_unit_price_",
        "custom_freight__insurance_",
        "custom__cif_total_amount",
        "custom___cif_total_amount"
    ];
    
    try {
        export_fields.forEach(fieldname => {
            // Toggle in the form view (when you open a row)
            frm.fields_dict.items.grid.update_docfield_property(
                fieldname,
                'hidden',
                is_export ? 0 : 1
            );
            
            // Toggle in the grid/list view
            frm.fields_dict.items.grid.update_docfield_property(
                fieldname,
                'in_list_view',
                is_export ? 1 : 0
            );
        });
        
        // Reset and re-render the grid columns
        let grid = frm.fields_dict.items.grid;
        
        // Clear cached columns
        grid.visible_columns = null;
        
        // Re-setup visible columns
        if (grid.setup_visible_columns) {
            grid.setup_visible_columns();
        }
        
        // Force complete grid refresh
        grid.reset_grid();
        grid.refresh();
        
    } catch (e) {
        console.log("Error toggling export fields:", e);
    }
    
    // Final refresh
    frm.refresh_field("items");
}


/************************************
 * SALES ORDER ITEM EVENTS
 ************************************/
frappe.ui.form.on("Sales Order Item", {
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
        // Recalculate when item changes
        setTimeout(() => {
            calculate_cif_values(frm, cdt, cdn);
        }, 300);
    }
});


/************************************
 * ROW-LEVEL CIF CALCULATION
 ************************************/
function calculate_cif_values(frm, cdt, cdn) {
    if (frm.doc.order_type !== "Export") return;

    let row = locals[cdt][cdn];

    let base_rate = flt(row.base_rate); // company currency (INR)
    let rate = flt(row.rate);           // order currency
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

    // Recalculate totals after updating row values
    setTimeout(() => {
        calculate_so_cif_totals(frm);
    }, 100);
}


/************************************
 * SALES ORDER TOTAL CIF
 ************************************/
function calculate_so_cif_totals(frm) {
    if (frm.doc.order_type !== "Export") {
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