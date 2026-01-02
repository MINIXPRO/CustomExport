/************************************
 * PACKING SLIP (PARENT)
 ************************************/
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


/************************************
 * SHOW / HIDE EXPORT FIELDS (ITEMS)
 ************************************/
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


/************************************
 * PACKING SLIP ITEM EVENTS
 ************************************/
frappe.ui.form.on("Packing Slip Item", {
    items_add(frm, cdt, cdn) {
        setTimeout(() => {
            toggle_export_custom_fields(frm);
        }, 100);
    }
});