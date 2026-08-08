import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field

FIELDS = [
    {
        "fieldname": "posa_enable_kot_printing",
        "label": "Enable KOT Printing",
        "fieldtype": "Check",
        "insert_after": "print_format",
        "module": "POSAwesome",
    },
    {
        "fieldname": "posa_kot_printer_profile",
        "label": "KOT Printer Profile",
        "fieldtype": "Link",
        "options": "POSA Printer Profile",
        "insert_after": "posa_enable_kot_printing",
        "depends_on": "eval:doc.posa_enable_kot_printing==1",
        "module": "POSAwesome",
    },
    {
        "fieldname": "posa_kot_print_format",
        "label": "KOT Print Format",
        "fieldtype": "Link",
        "options": "Print Format",
        "insert_after": "posa_kot_printer_profile",
        "depends_on": "eval:doc.posa_enable_kot_printing==1",
        "module": "POSAwesome",
    },
    {
        "fieldname": "posa_enable_rider_dispatch_printing",
        "label": "Enable Rider Dispatch Printing",
        "fieldtype": "Check",
        "insert_after": "posa_kot_print_format",
        "module": "POSAwesome",
    },
    {
        "fieldname": "posa_rider_dispatch_printer_profile",
        "label": "Rider Dispatch Printer Profile",
        "fieldtype": "Link",
        "options": "POSA Printer Profile",
        "insert_after": "posa_enable_rider_dispatch_printing",
        "depends_on": "eval:doc.posa_enable_rider_dispatch_printing==1",
        "module": "POSAwesome",
    },
    {
        "fieldname": "posa_rider_dispatch_print_format",
        "label": "Rider Dispatch Print Format",
        "fieldtype": "Link",
        "options": "Print Format",
        "insert_after": "posa_rider_dispatch_printer_profile",
        "depends_on": "eval:doc.posa_enable_rider_dispatch_printing==1",
        "module": "POSAwesome",
    },
    {
        "fieldname": "custom_column_break_wwq3q",
        "fieldtype": "Column Break",
        "insert_after": "posa_rider_dispatch_print_format",
        "module": "POSAwesome",
    },
    {
        "fieldname": "custom_enable_kot_reprint",
        "label": "Enable KOT Reprint",
        "fieldtype": "Check",
        "insert_after": "custom_column_break_wwq3q",
        "module": "POSAwesome",
    },
    {
        "fieldname": "custom_reprint_kot_format",
        "label": "Reprint KOT Format",
        "fieldtype": "Link",
        "options": "Print Format",
        "insert_after": "custom_enable_kot_reprint",
        "depends_on": "eval:doc.custom_enable_kot_reprint==1",
        "module": "POSAwesome",
    },
    {
        "fieldname": "custom_table_order_printer",
        "label": "Table Order Printer",
        "fieldtype": "Link",
        "options": "POSA Printer Profile",
        "insert_after": "custom_reprint_kot_format",
        "depends_on": "eval:doc.custom_enable_kot_reprint==1",
        "module": "POSAwesome",
    },
    {
        "fieldname": "custom_parcel_order_printer",
        "label": "Parcel Order Printer",
        "fieldtype": "Link",
        "options": "POSA Printer Profile",
        "insert_after": "custom_table_order_printer",
        "depends_on": "eval:doc.custom_enable_kot_reprint==1",
        "module": "POSAwesome",
    },
]

def _upsert_custom_field(field):
    fieldname = field["fieldname"]
    custom_field_name = f"POS Profile-{fieldname}"

    if not frappe.db.exists("Custom Field", custom_field_name):
        create_custom_field("POS Profile", field)
        return

    frappe.db.set_value(
        "Custom Field",
        custom_field_name,
        {key: value for key, value in field.items() if key != "insert_after"},
        update_modified=False,
    )
    frappe.db.set_value(
        "Custom Field",
        custom_field_name,
        "insert_after",
        field["insert_after"],
        update_modified=False,
    )

def execute():
    for field in FIELDS:
        _upsert_custom_field(field)

    frappe.clear_cache(doctype="POS Profile")
