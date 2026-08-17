import {
	getPrintTemplate,
	getTermsAndConditions,
	memoryInitPromise,
} from "./offline/index";
import nunjucks from "nunjucks";

declare const frappe: any;

export const DEFAULT_OFFLINE_PRINT_TEMPLATE = `<div class="print-format thermal-receipt">
    <!-- Header Section -->
    <div class="text-center header">
        <h2 style="margin: 0; font-size: 20px; font-weight: bold; font-family: 'Times New Roman', Times, serif;">Kitchen 92</h2>
        <div style="font-size: 15px; font-weight: bold; font-family: 'Times New Roman', Times, serif; font-style: italic;">Taste the Magic</div>
        <div style="font-size: 11px; margin-top: 5px; font-family: Arial, sans-serif;">
            Near United Sweets and Bakers<br>
            Multan Road Lodhran<br>
            03-111-777-468, 0303-5552141<br>
            PNTN: H672614-8
        </div>
    </div>

    <div class="receipt-line"></div>

    <!-- Meta Information (Centered) -->
    <div class="text-center" style="font-size: 12px; margin-bottom: 5px; font-family: Arial, sans-serif;">
        <div style="display: flex; justify-content: center; gap: 15px;">
            <span>{{ doc.get_formatted("posting_date") }}</span>
            <span>{{ doc.get_formatted("posting_time") }}</span>
        </div>
        <div style="font-weight: bold; font-size: 15px; margin-top: 4px;">
             {{ doc.name }}
        </div>
        <div style="font-weight: bold; font-size: 15px; margin-top: 2px;">
            Order Type : {{ doc.posa_order_type }}
        </div>
        {% if doc.posa_order_type | lower in ["dine-in", "dine in"] %}
        <div style="font-weight: bold; font-size: 15px; margin-top: 2px;">
            Table No : {{ doc.posa_table_no or doc.table_no or doc.table or 'N/A' }}
        </div>
        {% endif %}
    </div>

    <div class="receipt-line"></div>

    <!-- Extract Total Tax Rate and Calculate Running Totals for Amount Column -->
    {% set ns = namespace(total_tax_rate=0, calculated_amount_total=0) %}
    {% if doc.taxes %}
        {% for tax in doc.taxes %}
            {% set ns.total_tax_rate = ns.total_tax_rate + tax.rate %}
        {% endfor %}
    {% endif %}

    <!-- Items Table -->
    <table class="table-items" style="width: 100%; font-size: 11px; border-collapse: collapse; font-family: Arial, sans-serif;">
        <thead>
            <tr style="border-bottom: 1.5px solid #000;">
                <th style="text-align: left; width: 38%; padding-bottom: 3px;">Deal</th>
                <th style="text-align: center; width: 12%; padding-bottom: 3px;">Qty.</th>
                <th style="text-align: right; width: 15%; padding-bottom: 3px;">Price</th>
                <th style="text-align: right; width: 15%; padding-bottom: 3px;">Tax</th>
                <th style="text-align: right; width: 20%; padding-bottom: 3px;">Amount</th>
            </tr>
        </thead>
        <tbody>
            {% for item in doc.items %}
            {% set item_tax = (item.amount * ns.total_tax_rate / 100) %}
            {% set item_total_with_tax = item.amount + item_tax %}
            {% set ns.calculated_amount_total = ns.calculated_amount_total + item_total_with_tax %}
            <tr>
                <td style="text-align: left; padding: 4px 0; vertical-align: top; text-transform: uppercase;">{{ item.item_name }}</td>
                <td style="text-align: center; padding: 4px 0; vertical-align: top;">{{ item.qty | int }}</td>
                <td style="text-align: right; padding: 4px 0; vertical-align: top;">{{ "%.2f" | format(item.rate) }}</td>
                <td style="text-align: right; padding: 4px 0; vertical-align: top;">{{ "%.2f" | format(item_tax) }}</td>
                <td style="text-align: right; padding: 4px 0; vertical-align: top;">{{ "%.2f" | format(item_total_with_tax) }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>

    <div class="receipt-line"></div>

    <!-- Totals Section (Right Aligned Structure) -->
    <div style="font-size: 13px; font-family: Arial, sans-serif; margin-left: auto; width: 75%; padding-left: 5px; padding-right: 5px; box-sizing: border-box;">
        <div style="display: flex; justify-content: space-between; font-weight: bold; font-size: 14px;">
            <span>Total :</span>
            <span>{{ "%.2f" | format(ns.calculated_amount_total) }}</span>
        </div>
        <div style="display: flex; justify-content: space-between; margin-top: 2px;">
            <span>Service Charges :</span>
            <span>{{ "%.2f" | format(doc.service_charges or 0) }}</span>
        </div>
        <div style="display: flex; justify-content: space-between; margin-top: 2px;">
            <span>Discount :</span>
            <span>{{ "%.2f" | format(doc.discount_amount or 0) }}</span>
        </div>
    </div>

    <div class="receipt-line" style="border-top: 1.5px solid #000; margin: 4px 0;"></div>

    <!-- Grand Total Calculation (Amount Total + Service Charges - Discount) -->
    {% set service_charges_val = doc.service_charges if doc.service_charges else 0 %}
    {% set discount_val = doc.discount_amount if doc.discount_amount else 0 %}
    {% set final_grand_total = ns.calculated_amount_total + service_charges_val - discount_val %}

    <div style="font-size: 14px; font-weight: bold; font-family: Arial, sans-serif; margin-left: auto; width: 75%; padding-left: 5px; padding-right: 5px; box-sizing: border-box;">
        <div style="display: flex; justify-content: space-between; font-size: 15px;">
            <span>Grand Total :</span>
            <span>{{ "%.2f" | format(final_grand_total) }}</span>
        </div>
        <div style="display: flex; justify-content: space-between; margin-top: 2px;">
            <span>Cash Received :</span>
            <span>{{ "%.2f" | format(doc.paid_amount or final_grand_total) }}</span>
        </div>
        <div style="display: flex; justify-content: space-between; margin-top: 2px;">
            <span>Cash Refund :</span>
            <span>{{ "%.2f" | format(doc.change_amount or 0) }}</span>
        </div>
    </div>

    <div class="receipt-line"></div>

    <!-- PRA Image & QR Code Side-by-Side Section -->
    <div style="display: flex; justify-content: space-between; align-items: center; margin: 10px 0;">
        <div style="width: 45%; text-align: left;">
            <img src="https://usab.nexo4erp.com/files/pra-logo.png" style="max-width: 100%; height: auto; display: block;" alt="PRA Logo">
        </div>
        <div style="width: 45%; text-align: right;">
            <img src="https://api.qrserver.com/v1/create-qr-code/?size=100x100&data={{ doc.name }}" style="width: 80px; height: 80px; display: inline-block;" alt="QR Code">
        </div>
    </div>

    <div class="receipt-line"></div>

    <!-- Footer Information -->
    <div style="font-size: 12px; margin-top: 8px; font-family: Arial, sans-serif;">
        <div style="margin-bottom: 8px;">
            <span style="font-weight: bold; font-size: 14px;">User Name : </span>
            <span style="font-size: 14px;">{{ doc.owner }}</span>
        </div>
        <div style="font-weight: bold; font-size: 16px; margin-bottom: 10px;">
            {{ doc.posa_order_type }}
        </div>
        <div class="text-center" style="font-size: 13px; font-weight: bold; margin-top: 10px; font-style: italic;">
            {% if doc.posa_order_type | lower in ["dine-in", "dine in"] %}
                Thank you for dining with us! Please come again.
            {% elif doc.posa_order_type | lower in ["takeaway", "take away"] %}
                Thank you for your takeaway! Enjoy your meal at home.
            {% elif doc.posa_order_type | lower == "delivery" %}
                Thank you for ordering from us! Enjoy your meal.
            {% else %}
                Thank you for your order! Please come again.
            {% endif %}
        </div>
    </div>
</div>

<style>
    .print-format.thermal-receipt {
        width: 80mm;
        max-width: 80mm;
        margin: 0 auto;
        color: #000;
        background: #fff;
        padding: 5px;
        box-sizing: border-box;
    }
    .text-center {
        text-align: center;
    }
    .receipt-line {
        border-top: 1px dashed #000;
        margin: 6px 0;
        width: 100%;
    }
    @media print {
        .print-format {
            width: 80mm;
        }
    }
</style>`;

function normaliseTemplate(template: string) {
	if (!template) return template;
	return template.replace(/"""([\s\S]*?)"""/g, (_, str) => {
		const escaped = str
			.replace(/\\/g, "\\\\")
			.replace(/"/g, '\\"')
			.replace(/\r?\n/g, "\\n");
		return `"${escaped}"`;
	});
}

function preprocessTemplate(template: string) {
	if (!template) return template;
	return template.replace(
		/\{%\s*set\s+ns\.([a-zA-Z0-9_]+)\s*=\s*(.+?)\s*%\}/g,
		'{{ set_ns_prop(ns, "$1", $2) }}',
	);
}

function attachFormatter(obj: any) {
	if (!obj || typeof obj !== "object" || obj.get_formatted) return;
	obj.get_formatted = function (field: string) {
		return this?.[field] ?? "";
	};
}

function computePaidAmount(doc: any) {
	if (!doc) return 0;

	const sign = doc.is_return ? -1 : 1;
	const paymentsTotal = (doc.payments || []).reduce(
		(sum: number, p: any) => sum + Math.abs(parseFloat(p.amount) || 0),
		0,
	);
	const changeAmount = Math.abs(parseFloat(doc.change_amount) || 0);

	const creditSale =
		doc.is_credit_sale === true ||
		doc.is_credit_sale === 1 ||
		doc.is_credit_sale === "1" ||
		String(doc.is_credit_sale).toLowerCase() === "yes";

	if (creditSale || paymentsTotal === 0) {
		return 0;
	}

	const paidAmount = paymentsTotal
		? Math.max(paymentsTotal - changeAmount, 0)
		: Math.abs(parseFloat(doc.paid_amount ?? doc.grand_total ?? 0) || 0);
	return sign * paidAmount;
}

export default async function renderOfflineInvoiceHTML(invoice: any) {
	if (!invoice) return "";

	await memoryInitPromise;

	const cachedTemplate = normaliseTemplate(getPrintTemplate());
	const template = cachedTemplate || DEFAULT_OFFLINE_PRINT_TEMPLATE;
	const terms = getTermsAndConditions();
	const doc = {
		...invoice,
		terms: invoice.terms || terms,
		terms_and_conditions: invoice.terms_and_conditions || terms,
	};

	doc.paid_amount = computePaidAmount(doc);
	attachFormatter(doc);
	(doc.items || []).forEach(attachFormatter);
	(doc.taxes || []).forEach(attachFormatter);

	try {
		const env = nunjucks.configure({ autoescape: false });
		env.addFilter("format_currency", (value: unknown, currency: string) => {
			const number =
				typeof value === "number" ? value : parseFloat(String(value));
			if (Number.isNaN(number)) return value;
			try {
				return new Intl.NumberFormat(undefined, {
					style: currency ? "currency" : "decimal",
					currency: currency || undefined,
				}).format(number);
			} catch {
				return currency ? `${currency} ${number}` : String(number);
			}
		});
		env.addFilter("currency", (value: unknown, currency: string) =>
			(env as any).filters.format_currency(value, currency),
		);
		env.addFilter("int", (value: unknown) => {
			const number = parseInt(String(value ?? 0), 10);
			return Number.isNaN(number) ? 0 : number;
		});
		env.addFilter("lower", (value: unknown) =>
			String(value ?? "").toLowerCase(),
		);
		env.addFilter("format", (a: unknown, b: unknown) => {
			let fmt = "";
			let val: any = 0;
			if (typeof a === "string" && a.includes("%")) {
				fmt = a;
				val = b;
			} else if (typeof b === "string" && b.includes("%")) {
				fmt = b;
				val = a;
			} else {
				val = a;
			}
			const num = parseFloat(String(val ?? 0));
			if (Number.isNaN(num)) return "0.00";
			if (fmt.includes("%.2f")) return num.toFixed(2);
			const match = fmt.match(/%\.(\d+)f/);
			if (match && match[1]) {
				return num.toFixed(parseInt(match[1], 10));
			}
			return num.toFixed(2);
		});
		(env as any).getFilter = function (name: string) {
			return (this as any).filters[name] || ((v: unknown) => v);
		};

		const context = {
			doc,
			terms: doc.terms,
			terms_and_conditions: doc.terms_and_conditions,
			namespace: (initialObj: Record<string, any> = {}) => ({ ...initialObj }),
			set_ns_prop: (ns: any, key: string, val: any) => {
				if (ns && typeof ns === "object") {
					ns[key] = val;
				}
				return "";
			},
			_: frappe?._ ? frappe._ : (t: string) => t,
			frappe: {
				db: { get_value: () => "", sql: () => [] },
				get_list: () => [],
			},
		};
		return env.renderString(preprocessTemplate(template), context);
	} catch (e) {
		console.error("Failed to render offline invoice", e);
		return "";
	}
}
