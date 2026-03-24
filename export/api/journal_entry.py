import frappe
from frappe.utils import cstr


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_against_jv(doctype, txt, searchfield, start, page_len, filters):
	if not frappe.db.has_column("Journal Entry", searchfield):
		return []

	return frappe.db.sql(
		f"""
		SELECT jv.name, jv.posting_date, jv.bill_no, jv.user_remark
		FROM `tabJournal Entry` jv, `tabJournal Entry Account` jv_detail
		WHERE jv_detail.parent = jv.name
			AND jv_detail.account = %(account)s
			AND IFNULL(jv_detail.party, '') = %(party)s
			AND (
				jv_detail.reference_type IS NULL
				OR jv_detail.reference_type = ''
			)
			AND jv.docstatus = 1
			AND (
				jv.`{searchfield}` LIKE %(txt)s
				OR jv.bill_no LIKE %(txt)s
			)
		ORDER BY jv.name DESC
		LIMIT %(limit)s OFFSET %(offset)s
		""",
		dict(
			account=filters.get("account"),
			party=cstr(filters.get("party")),
			txt=f"%{txt}%",
			offset=start,
			limit=page_len,
		),
	)
