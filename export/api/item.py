import frappe


def before_save(doc, method):
    if doc.custom_item_description:
        doc.description = doc.custom_item_description
