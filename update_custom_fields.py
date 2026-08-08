import json

with open("posawesome/fixtures/custom_field.json", "r") as f:
    data = json.load(f)

# Fields to add
new_fields = [
    {
        "docstatus": 0,
        "doctype": "Custom Field",
        "name": "POS Profile-posa_enable_kot_printing",
        "dt": "POS Profile",
        "fieldname": "posa_enable_kot_printing",
        "fieldtype": "Check",
        "insert_after": "print_format",
        "label": "Enable KOT Printing",
        "module": "POSAwesome",
    },
    {
        "docstatus": 0,
        "doctype": "Custom Field",
        "name": "POS Profile-posa_kot_printer_profile",
        "dt": "POS Profile",
        "fieldname": "posa_kot_printer_profile",
        "fieldtype": "Link",
        "options": "POSA Printer Profile",
        "insert_after": "posa_enable_kot_printing",
        "label": "KOT Printer Profile",
        "depends_on": "eval:doc.posa_enable_kot_printing==1",
        "module": "POSAwesome",
    },
    {
        "docstatus": 0,
        "doctype": "Custom Field",
        "name": "POS Profile-posa_kot_print_format",
        "dt": "POS Profile",
        "fieldname": "posa_kot_print_format",
        "fieldtype": "Link",
        "options": "Print Format",
        "insert_after": "posa_kot_printer_profile",
        "label": "KOT Print Format",
        "depends_on": "eval:doc.posa_enable_kot_printing==1",
        "module": "POSAwesome",
    },
    {
        "docstatus": 0,
        "doctype": "Custom Field",
        "name": "POS Profile-posa_enable_rider_dispatch_printing",
        "dt": "POS Profile",
        "fieldname": "posa_enable_rider_dispatch_printing",
        "fieldtype": "Check",
        "insert_after": "posa_kot_print_format",
        "label": "Enable Rider Dispatch Printing",
        "module": "POSAwesome",
    },
    {
        "docstatus": 0,
        "doctype": "Custom Field",
        "name": "POS Profile-posa_rider_dispatch_printer_profile",
        "dt": "POS Profile",
        "fieldname": "posa_rider_dispatch_printer_profile",
        "fieldtype": "Link",
        "options": "POSA Printer Profile",
        "insert_after": "posa_enable_rider_dispatch_printing",
        "label": "Rider Dispatch Printer Profile",
        "depends_on": "eval:doc.posa_enable_rider_dispatch_printing==1",
        "module": "POSAwesome",
    },
    {
        "docstatus": 0,
        "doctype": "Custom Field",
        "name": "POS Profile-posa_rider_dispatch_print_format",
        "dt": "POS Profile",
        "fieldname": "posa_rider_dispatch_print_format",
        "fieldtype": "Link",
        "options": "Print Format",
        "insert_after": "posa_rider_dispatch_printer_profile",
        "label": "Rider Dispatch Print Format",
        "depends_on": "eval:doc.posa_enable_rider_dispatch_printing==1",
        "module": "POSAwesome",
    },
    {
        "docstatus": 0,
        "doctype": "Custom Field",
        "name": "POS Profile-custom_column_break_wwq3q",
        "dt": "POS Profile",
        "fieldname": "custom_column_break_wwq3q",
        "fieldtype": "Column Break",
        "insert_after": "posa_rider_dispatch_print_format",
        "module": "POSAwesome",
    },
    {
        "docstatus": 0,
        "doctype": "Custom Field",
        "name": "POS Profile-custom_enable_kot_reprint",
        "dt": "POS Profile",
        "fieldname": "custom_enable_kot_reprint",
        "fieldtype": "Check",
        "insert_after": "custom_column_break_wwq3q",
        "label": "Enable KOT Reprint",
        "module": "POSAwesome",
    },
    {
        "docstatus": 0,
        "doctype": "Custom Field",
        "name": "POS Profile-custom_reprint_kot_format",
        "dt": "POS Profile",
        "fieldname": "custom_reprint_kot_format",
        "fieldtype": "Link",
        "options": "Print Format",
        "insert_after": "custom_enable_kot_reprint",
        "label": "Reprint KOT Format",
        "depends_on": "eval:doc.custom_enable_kot_reprint==1",
        "module": "POSAwesome",
    },
    {
        "docstatus": 0,
        "doctype": "Custom Field",
        "name": "POS Profile-custom_table_order_printer",
        "dt": "POS Profile",
        "fieldname": "custom_table_order_printer",
        "fieldtype": "Link",
        "options": "POSA Printer Profile",
        "insert_after": "custom_reprint_kot_format",
        "label": "Table Order Printer",
        "depends_on": "eval:doc.custom_enable_kot_reprint==1",
        "module": "POSAwesome",
    },
    {
        "docstatus": 0,
        "doctype": "Custom Field",
        "name": "POS Profile-custom_parcel_order_printer",
        "dt": "POS Profile",
        "fieldname": "custom_parcel_order_printer",
        "fieldtype": "Link",
        "options": "POSA Printer Profile",
        "insert_after": "custom_table_order_printer",
        "label": "Parcel Order Printer",
        "depends_on": "eval:doc.custom_enable_kot_reprint==1",
        "module": "POSAwesome",
    },
]

# Update or append custom field definitions in data
existing_fields = {f.get("fieldname"): idx for idx, f in enumerate(data) if f.get("dt") == "POS Profile"}
for nf in new_fields:
    fn = nf["fieldname"]
    if fn in existing_fields:
        data[existing_fields[fn]].update(nf)
    else:
        data.append(nf)

with open("posawesome/fixtures/custom_field.json", "w") as f:
    json.dump(data, f, indent=1)
