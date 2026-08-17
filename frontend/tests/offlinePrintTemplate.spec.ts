import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../src/offline/index", () => ({
	getPrintTemplate: vi.fn(() => ""),
	getTermsAndConditions: vi.fn(() => ""),
	memoryInitPromise: Promise.resolve(),
}));

import renderOfflineInvoiceHTML from "../src/offline_print_template";

describe("offline print fallback totals", () => {
	beforeEach(() => {
		vi.stubGlobal("frappe", { _: (text: string) => text });
	});

	it("prints paid amount net of change in invoice currency", async () => {
		const html = await renderOfflineInvoiceHTML({
			name: "ACC-SINV-OFFLINE-1",
			company: "Test Co",
			customer: "Walk In",
			posa_order_type: "Takeaway",
			grand_total: 100,
			change_amount: 20,
			payments: [{ mode_of_payment: "Cash", amount: 120 }],
			items: [{ item_name: "Item A", qty: 1, rate: 100, amount: 100 }],
			taxes: [],
		});

		expect(html).toContain("Kitchen 92");
		expect(html).toContain("Cash Received :");
		expect(html).toContain("100.00");
		expect(html).toContain("Cash Refund :");
		expect(html).toContain("20.00");
	});

	it("prints return paid amount as negative", async () => {
		const html = await renderOfflineInvoiceHTML({
			name: "ACC-SINV-RETURN-OFFLINE",
			company: "Test Co",
			customer: "Walk In",
			is_return: 1,
			posa_order_type: "Takeaway",
			grand_total: -80,
			payments: [{ mode_of_payment: "Cash", amount: -80 }],
			items: [],
			taxes: [],
		});

		expect(html).toContain("Cash Received :");
		expect(html).toContain("-80.00");
	});
});
