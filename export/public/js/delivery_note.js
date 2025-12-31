/************************************
 * DELIVERY NOTE (PARENT)
 ************************************/
frappe.ui.form.on("Delivery Note", {
    refresh(frm) {
        toggle_export_fields_dn(frm);
    },

    custom_order_type(frm) {
        toggle_export_fields_dn(frm);
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
 * DELIVERY NOTE ITEM - REFRESH TOGGLE
 ************************************/
frappe.ui.form.on("Delivery Note Item", {
    items_add(frm, cdt, cdn) {
        // Ensure visibility is set when new row is added
        setTimeout(() => {
            toggle_export_fields_dn(frm);
        }, 100);
    }
});