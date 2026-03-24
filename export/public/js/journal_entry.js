frappe.ui.form.on("Journal Entry", {
    setup(frm) {
        frm.set_query("custom_journal_entry", "accounts", function (doc, cdt, cdn) {
            var row = frappe.get_doc(cdt, cdn);
            frappe.model.validate_missing(row, "account");
            return {
                query: "export.api.journal_entry.get_against_jv",
                filters: {
                    account: row.account,
                    party: row.party,
                },
            };
        });
    }
});

frappe.ui.form.on("Journal Entry Account", {
    custom_journal_entry(frm, cdt, cdn) {
        var row = frappe.get_doc(cdt, cdn);
        if (row.custom_journal_entry && row.reference_type === "Journal Entry") {
            frappe.model.set_value(cdt, cdn, "reference_name", row.custom_journal_entry);
        } else {
            frappe.model.set_value(cdt, cdn, "reference_name", "");
        }
    },

    reference_type(frm, cdt, cdn) {
        var row = frappe.get_doc(cdt, cdn);
        if (row.reference_type !== "Journal Entry") {
            frappe.model.set_value(cdt, cdn, "custom_journal_entry", "");
        }
    }
});
