frappe.ui.form.on("Sales Order", {
    refresh(frm) {
        toggle_export_fields(frm);
        //calculate_so_cif_totals(frm);
        toggle_cif_total_by_currency(frm);
    },

    order_type(frm) {
        toggle_export_fields(frm);
    },

    validate(frm) {
        calculate_so_cif_totals(frm);
    },

    currency(frm) {
        calculate_so_cif_totals(frm);
        toggle_cif_total_by_currency(frm);
    }
});

// Show/hide CIF total field based on currency
function toggle_cif_total_by_currency(frm) {
    const show = frm.doc.currency !== "INR";
    frm.toggle_display("custom_cif_total_amount_", show);
}

// Show/hide export-specific fields in the child table grid
function toggle_export_fields(frm) {
    const is_export = frm.doc.order_type === "Export";

    const export_fields = [
        "custom_net_weight",
        "custom_cif_unit_price",
        "custom_freight__insurance_",
        "custom__cif_total_amount"
    ];

    // Toggle columns in child table grid
    export_fields.forEach(fieldname => {
        frm.fields_dict.items.grid.toggle_display(fieldname, is_export);
    });

    // No need to toggle individual rows to avoid hiding Add/Create button
    frm.refresh_field("items");
}

// Sales Order Item triggers for CIF calculations
frappe.ui.form.on('Sales Order Item', {
    rate: function(frm, cdt, cdn) {
        calculate_cif_values(frm, cdt, cdn);
    },
    
    custom_freight__insurance_: function(frm, cdt, cdn) {
        calculate_cif_values(frm, cdt, cdn);
    },
    
    qty: function(frm, cdt, cdn) {
        calculate_cif_values(frm, cdt, cdn);
    }
});

// Calculate CIF Unit Price and Total for a row
function calculate_cif_values(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    
    let unit_price = row.base_rate || 0;
    let freight_insurance_percent = row.custom_freight__insurance_ || 0;
    let quantity = row.qty || 0;
    
    // CIF Unit Price = Unit Price + (Unit Price × Freight & Insurance %)
    let cif_unit_price = unit_price + (unit_price * freight_insurance_percent / 100);
    
    // CIF Total Amount = CIF Unit Price × Quantity
    let cif_total_amount = cif_unit_price * quantity;
    
    // Update fields
    frappe.model.set_value(cdt, cdn, 'custom_cif_unit_price', cif_unit_price);
    frappe.model.set_value(cdt, cdn, 'custom__cif_total_amount', cif_total_amount);
    
    frm.refresh_field('items');
}

// Calculate total CIF amounts for the Sales Order
function calculate_so_cif_totals(frm) {
    if (frm.doc.order_type !== "Export") return;

    let total_company_currency = 0;

    (frm.doc.items || []).forEach(row => {
        total_company_currency += flt(row.custom__cif_total_amount);
    });

    // Company Currency CIF (INR)
    frm.set_value(
        "custom_cif_total_amount_company_currency",
        total_company_currency
    );

    // Convert to Sales Order currency
    const conversion_rate = flt(frm.doc.conversion_rate) || 1;
    const order_currency_total = total_company_currency / conversion_rate;

    frm.set_value(
        "custom_cif_total_amount_",
        order_currency_total
    );
}
