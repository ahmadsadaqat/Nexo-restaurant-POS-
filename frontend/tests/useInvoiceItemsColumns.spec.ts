// @vitest-environment jsdom

import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { ref } from "vue";

vi.mock("../src/posapp/stores/toastStore", () => ({
	useToastStore: () => ({
		show: vi.fn(),
	}),
}));

vi.mock("../src/posapp/composables/pos/shared/useStockUtils", () => ({
	useStockUtils: () => ({
		calc_stock_qty: vi.fn(),
	}),
}));

vi.mock("../src/posapp/composables/pos/items/useItemAddition", () => ({
	useItemAddition: () => ({
		removeItem: vi.fn(),
		addItem: vi.fn(),
	}),
}));

const taxTemplates: Record<string, any> = {};

vi.mock("../src/offline/index", () => ({
	getCachedDeliveryCharges: vi.fn(() => []),
	saveDeliveryChargesCache: vi.fn(),
	getTaxTemplate: vi.fn((name: string) => taxTemplates[name] || null),
	setTaxTemplate: vi.fn((name: string, data: any) => {
		taxTemplates[name] = data;
	}),
}));

describe("useInvoiceItems column preferences", () => {
	beforeEach(() => {
		vi.resetModules();
		setActivePinia(createPinia());
		localStorage.clear();
		(window as any).__ = (value: string) => value;
		(globalThis as any).__ = (value: string) => value;
		(globalThis as any).flt = (value: any) => Number(value || 0);
		(window as any).frappe = {
			defaults: {
				get_default: vi.fn(() => "2"),
			},
			datetime: {
				nowdate: vi.fn(() => "2026-07-10"),
			},
		};
		(globalThis as any).frappe = (window as any).frappe;
	});

	it("updates optional cart columns and persists only valid optional keys", async () => {
		const { useInvoiceItems } = await import(
			"../src/posapp/composables/pos/invoice/useInvoiceItems"
		);
		const invoiceItems = useInvoiceItems(ref("Invoice"));

		invoiceItems.setSelectedColumns([
			"uom",
			"price_list_rate",
			"item_name",
			"discount_value",
			"market_rate",
			"amount_after_tax",
			"unknown_column",
		]);
		invoiceItems.saveColumnPreferences();

		expect(invoiceItems.selected_columns.value).toEqual([
			"uom",
			"price_list_rate",
			"discount_percentage",
			"market_rate",
			"amount_after_tax",
		]);
		expect(invoiceItems.items_headers.value.map((column) => column.key)).toEqual(
			expect.arrayContaining([
				"item_name",
				"qty",
				"uom",
				"price_list_rate",
				"discount_percentage",
				"rate",
				"market_rate",
				"amount",
				"amount_after_tax",
				"actions",
			]),
		);
		expect(localStorage.getItem("posawesome_selected_columns")).toBe(
			JSON.stringify([
				"uom",
				"price_list_rate",
				"discount_percentage",
				"market_rate",
				"amount_after_tax",
			]),
		);
	});

	it("correctly calculates item amount after cash tax with Option B precedence", async () => {
		const { getItemCashTaxRate, getItemAmountAfterCashTax } = await import(
			"../src/posapp/utils/itemTaxUtils"
		);
		const { setTaxTemplate } = await import("../src/offline/index");

		const posProfile = {
			name: "Test Profile",
			posa_enable_payment_tax_templates: 1,
			posa_payment_tax_templates: [
				{ mode_of_payment: "Cash", tax_template: "Cash Tax 5%" },
				{ mode_of_payment: "Card", tax_template: "Card Tax 20%" },
			],
		};

		setTaxTemplate("Cash Tax 5%", {
			taxes: [
				{ account_head: "GST - NED", rate: 5.0, charge_type: "On Net Total" },
			],
		});

		// 1. Item with 0% Item Tax Template (e.g. SKU010)
		const itemWithZeroTax = {
			item_code: "SKU010",
			qty: 1,
			rate: 200,
			amount: 200,
			item_tax_template: "zero percent - NED",
			item_tax_rate: JSON.stringify({ "GST - NED": 0.0 }),
		};
		expect(getItemCashTaxRate(itemWithZeroTax, posProfile)).toBe(0);
		expect(getItemAmountAfterCashTax(itemWithZeroTax, posProfile)).toBe(200);

		// 2. Standard item without Item Tax Template (subject to Cash 5%)
		const standardItem = {
			item_code: "1234",
			qty: 2,
			rate: 100,
			amount: 200,
		};
		expect(getItemCashTaxRate(standardItem, posProfile)).toBe(5);
		expect(getItemAmountAfterCashTax(standardItem, posProfile)).toBe(210);

		// 3. Tax inclusive setting
		const inclusiveProfile = {
			...posProfile,
			posa_tax_inclusive: 1,
		};
		expect(getItemAmountAfterCashTax(standardItem, inclusiveProfile)).toBe(200);
	});
});
