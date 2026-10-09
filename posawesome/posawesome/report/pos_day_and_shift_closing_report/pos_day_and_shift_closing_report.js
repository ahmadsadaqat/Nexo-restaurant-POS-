// Copyright (c) 2026, POSAwesome contributors
// For license information, please see license.txt

frappe.query_reports["POS Day and Shift Closing Report"] = {
	filters: [
		{
			fieldname: "report_view",
			label: __("Report View"),
			fieldtype: "Select",
			options: ["Daily Summary", "Shift Summary", "Invoice Details"],
			default: "Daily Summary",
			reqd: 1,
		},
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "cashier",
			label: __("Cashier"),
			fieldtype: "Link",
			options: "User",
		},
		{
			fieldname: "pos_profile",
			label: __("POS Profile"),
			fieldtype: "Link",
			options: "POS Profile",
			get_query() {
				const company = frappe.query_report.get_filter_value("company");
				return company ? { filters: { company } } : {};
			},
		},
		{
			fieldname: "opening_shift",
			label: __("POS Opening Shift"),
			fieldtype: "Link",
			options: "POS Opening Shift",
			get_query() {
				const filters = {};
				const company = frappe.query_report.get_filter_value("company");
				const cashier = frappe.query_report.get_filter_value("cashier");
				const pos_profile = frappe.query_report.get_filter_value("pos_profile");

				if (company) filters.company = company;
				if (cashier) filters.user = cashier;
				if (pos_profile) filters.pos_profile = pos_profile;

				return { filters };
			},
		},
		{
			fieldname: "shift_status",
			label: __("Shift Status"),
			fieldtype: "Select",
			options: ["All", "Open", "Closed"],
			default: "All",
		},
		{
			fieldname: "payment_category",
			label: __("Mode of Payment"),
			fieldtype: "Select",
			options: ["All", "Cash", "Card", "Other"],
			default: "All",
		},
		{
			fieldname: "differences_only",
			label: __("Differences Only"),
			fieldtype: "Check",
			default: 0,
		},
	],

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (!data) return value;

		const difference_fields = [
			"sales_difference",
			"cash_difference",
			"card_difference",
			"other_difference",
			"payment_difference",
			"quantity_difference",
		];

		if (difference_fields.includes(column.fieldname) && Math.abs(data[column.fieldname] || 0) >= 0.005) {
			return `<span class="text-danger font-weight-bold">${value}</span>`;
		}

		if (column.fieldname === "shift_status") {
			const colour = data.shift_status === "Closed" ? "green" : "orange";
			return `<span class="indicator-pill ${colour}">${value}</span>`;
		}

		return value;
	},
};
