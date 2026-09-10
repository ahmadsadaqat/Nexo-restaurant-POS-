// @vitest-environment jsdom

import { defineComponent, h } from "vue";
import { describe, expect, it, vi } from "vitest";
import { mount } from "@vue/test-utils";
import ItemsTableExpandedRow from "../src/posapp/components/pos/invoice/ItemsTableExpandedRow.vue";

const VTextFieldStub = defineComponent({
	name: "VTextFieldStub",
	props: {
		modelValue: { type: [String, Number], default: "" },
		label: { type: String, default: "" },
		disabled: { type: Boolean, default: false },
	},
	emits: ["update:modelValue", "change"],
	setup(props, { attrs, emit }) {
		return () =>
			h("div", { class: "v-text-field-stub", "data-label": props.label }, [
				h("span", { class: "field-label" }, props.label),
				h("input", {
					...attrs,
					"data-label": props.label,
					value: props.modelValue,
					disabled: props.disabled,
					onInput: (event: Event) =>
						emit(
							"update:modelValue",
							(event.target as HTMLInputElement).value,
						),
				}),
			]);
	},
});

const SimpleStub = defineComponent({
	name: "SimpleStub",
	setup(_, { slots }) {
		return () => h("div", {}, slots.default ? slots.default() : []);
	},
});

describe("ItemsTableExpandedRow - Item Remarks", () => {
	const createProps = (itemOverrides: Record<string, any> = {}) => ({
		item: {
			item_code: "ITEM-001",
			item_name: "Test Item",
			qty: 2,
			uom: "Nos",
			rate: 100,
			amount: 200,
			posa_row_id: "row-1",
			posa_notes: "",
			remarks: "",
			item_uoms: [{ uom: "Nos" }],
			...itemOverrides,
		},
		isExpanded: true,
		colspan: 6,
		pos_profile: {},
		invoiceType: "Sales Invoice",
		isReturnInvoice: false,
		invoice_doc: {},
		hide_qty_decimals: false,
		expandedContentClasses: {},
		formatFloat: (val: any) => String(val),
		formatCurrency: (val: any) => String(val),
		currencySymbol: () => "$",
		isNumber: () => true,
		setFormatedCurrency: vi.fn(),
		calcPrices: vi.fn(),
		calcUom: vi.fn(),
		changePriceListRate: vi.fn(),
		getSerialOptions: () => [],
		setSerialNo: vi.fn(),
		setBatchQty: vi.fn(),
		validateDueDate: vi.fn(),
	});

	it("renders the Item Remarks field in Basic Information section", () => {
		(window as any).__ = (s: string) => s;
		(window as any).frappe = { _: (s: string) => s };

		const props = createProps({ posa_notes: "Handle with care" });
		const wrapper = mount(ItemsTableExpandedRow, {
			props,
			global: {
				mocks: {
					frappe: { _: (value: string) => value },
					__: (value: string) => value,
				},
				components: {
					VTextField: VTextFieldStub,
					VSelect: SimpleStub,
					VIcon: SimpleStub,
					VCheckbox: SimpleStub,
					VAutocomplete: SimpleStub,
					VueDatePicker: SimpleStub,
					VProgressCircular: SimpleStub,
					VBtn: SimpleStub,
				},
			},
		});

		// Check that the Remarks field exists
		const remarksField = wrapper.find('[data-label="Item Remarks"] input');
		expect(remarksField.exists()).toBe(true);

		// Check that its value matches posa_notes
		expect((remarksField.element as HTMLInputElement).value).toBe("Handle with care");
	});

	it("updates both posa_notes and remarks when input value changes", async () => {
		(window as any).__ = (s: string) => s;
		(window as any).frappe = { _: (s: string) => s };

		const props = createProps({ posa_notes: "" });
		const wrapper = mount(ItemsTableExpandedRow, {
			props,
			global: {
				mocks: {
					frappe: { _: (value: string) => value },
					__: (value: string) => value,
				},
				components: {
					VTextField: VTextFieldStub,
					VSelect: SimpleStub,
					VIcon: SimpleStub,
					VCheckbox: SimpleStub,
					VAutocomplete: SimpleStub,
					VueDatePicker: SimpleStub,
					VProgressCircular: SimpleStub,
					VBtn: SimpleStub,
				},
			},
		});

		const input = wrapper.find('[data-label="Item Remarks"] input');
		expect(input.exists()).toBe(true);

		await input.setValue("Extra spicy, packed separately");

		expect(props.item.posa_notes).toBe("Extra spicy, packed separately");
		expect(props.item.remarks).toBe("Extra spicy, packed separately");
	});
});
