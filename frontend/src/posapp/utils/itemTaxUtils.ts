import { getTaxTemplate, setTaxTemplate } from "../../offline/index";

declare const frappe: any;

/**
 * Get the effective tax rate percentage applicable to an item under the Cash payment method.
 *
 * Rules:
 * 1. If the item has its own item_tax_template, its tax rates take precedence (Option B).
 * 2. Otherwise, the POS Profile's Cash payment tax template is used (or taxes_and_charges fallback).
 */
export function getItemCashTaxRate(item: any, posProfile: any): number {
	if (!item) return 0;

	// 1. Item-level tax template precedence
	if (item.item_tax_template) {
		let itemMap: Record<string, number> = {};
		if (item.item_tax_rate) {
			try {
				itemMap =
					typeof item.item_tax_rate === "string"
						? JSON.parse(item.item_tax_rate)
						: item.item_tax_rate;
			} catch {
				itemMap = {};
			}
		}
		return Object.values(itemMap).reduce(
			(sum: number, rate: any) => sum + (Number(rate) || 0),
			0,
		);
	}

	// 2. POS Profile Cash payment tax template
	if (!posProfile) return 0;

	let templateName: string | null = null;
	if (
		posProfile.posa_enable_payment_tax_templates &&
		Array.isArray(posProfile.posa_payment_tax_templates)
	) {
		const cashRow = posProfile.posa_payment_tax_templates.find(
			(r: any) =>
				r.mode_of_payment &&
				String(r.mode_of_payment).trim().toLowerCase() === "cash",
		);
		if (cashRow?.tax_template) {
			templateName = cashRow.tax_template;
		}
	}

	if (!templateName) {
		templateName = posProfile.taxes_and_charges || null;
	}

	if (!templateName) return 0;

	let tmpl = getTaxTemplate(templateName);

	// Attempt lazy fetch if not cached yet
	if (!tmpl && typeof frappe !== "undefined" && frappe.call) {
		try {
			frappe.call({
				method: "frappe.client.get",
				args: {
					doctype: "Sales Taxes and Charges Template",
					name: templateName,
				},
				callback: (res: any) => {
					if (res.message && templateName) {
						setTaxTemplate(templateName, res.message);
					}
				},
			});
		} catch {
			// Ignore offline or fetch errors
		}
		return 0;
	}

	if (!tmpl || !Array.isArray(tmpl.taxes)) return 0;

	return tmpl.taxes.reduce((sum: number, t: any) => {
		if (t.charge_type === "On Net Total" || !t.charge_type) {
			return sum + (Number(t.rate) || 0);
		}
		return sum;
	}, 0);
}

/**
 * Calculate the line item amount after tax using the Cash payment tax template.
 */
export function getItemAmountAfterCashTax(item: any, posProfile: any): number {
	if (!item) return 0;

	const qty = Number(item.qty) || 0;
	const rate = Number(item.rate) || 0;
	const lineAmount = item.amount !== undefined ? Number(item.amount) : qty * rate;

	// Check if tax is inclusive
	let isInclusive = Boolean(posProfile?.posa_tax_inclusive);
	if (!isInclusive && !item.item_tax_template && posProfile) {
		let templateName: string | null = null;
		if (
			posProfile.posa_enable_payment_tax_templates &&
			Array.isArray(posProfile.posa_payment_tax_templates)
		) {
			const cashRow = posProfile.posa_payment_tax_templates.find(
				(r: any) =>
					r.mode_of_payment &&
					String(r.mode_of_payment).trim().toLowerCase() === "cash",
			);
			if (cashRow?.tax_template) {
				templateName = cashRow.tax_template;
			}
		}
		if (!templateName) {
			templateName = posProfile.taxes_and_charges || null;
		}
		if (templateName) {
			const tmpl = getTaxTemplate(templateName);
			if (tmpl && Array.isArray(tmpl.taxes)) {
				isInclusive = tmpl.taxes.some((t: any) => Boolean(t.included_in_print_rate));
			}
		}
	}

	if (isInclusive) {
		return lineAmount;
	}

	const taxRatePercent = getItemCashTaxRate(item, posProfile);
	const taxAmount = (lineAmount * taxRatePercent) / 100;
	return lineAmount + taxAmount;
}
