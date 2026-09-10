// @vitest-environment jsdom

import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { shallowMount, flushPromises } from "@vue/test-utils";

const mockGetCachedCustomerAddresses = vi.fn();
const mockSaveCustomerAddressesCache = vi.fn();

vi.mock("../src/offline/index", () => ({
	getCachedCustomerAddresses: (customer: string) => mockGetCachedCustomerAddresses(customer),
	saveCustomerAddressesCache: (customer: string, data: any) => mockSaveCustomerAddressesCache(customer, data),
}));

describe("InvoiceDeliveryAddress component", () => {
	beforeEach(() => {
		vi.resetModules();
		setActivePinia(createPinia());
		mockGetCachedCustomerAddresses.mockReset();
		mockSaveCustomerAddressesCache.mockReset();
		(window as any).__ = (val: string) => val;
		(globalThis as any).__ = (val: string) => val;
		(window as any).frappe = {
			call: vi.fn(),
		};
	});

	it("renders a dropdown when customer has multiple addresses", async () => {
		mockGetCachedCustomerAddresses.mockReturnValue([
			{
				name: "ADDR-001",
				address_title: "Home",
				address_line1: "123 Elm St",
				city: "Springfield",
				address_type: "Shipping",
			},
			{
				name: "ADDR-002",
				address_title: "Office",
				address_line1: "456 Tech Blvd",
				city: "Metropolis",
				address_type: "Billing",
			},
		]);

		const { default: InvoiceDeliveryAddress } = await import(
			"../src/posapp/components/pos/invoice/InvoiceDeliveryAddress.vue"
		);

		const onUpdateAddress = vi.fn();
		const wrapper = shallowMount(InvoiceDeliveryAddress, {
			props: {
				customer: "John Doe",
				invoiceDoc: {},
				"onUpdate:address": onUpdateAddress,
			},
		});

		await flushPromises();

		// Should render autocomplete dropdown, not single text field
		expect(wrapper.find("v-autocomplete").exists()).toBe(true);
		expect(wrapper.find("v-text-field").exists()).toBe(false);
		expect(wrapper.find("v-autocomplete").attributes("modelvalue")).toBe("ADDR-001");

		expect(onUpdateAddress).toHaveBeenCalled();
		expect(onUpdateAddress.mock.calls[0][0]?.name).toBe("ADDR-001");
	});

	it("renders a text field when customer has a single address", async () => {
		mockGetCachedCustomerAddresses.mockReturnValue([
			{
				name: "ADDR-001",
				address_title: "Home",
				address_line1: "123 Elm St",
				city: "Springfield",
				address_type: "Shipping",
			},
		]);

		const { default: InvoiceDeliveryAddress } = await import(
			"../src/posapp/components/pos/invoice/InvoiceDeliveryAddress.vue"
		);

		const onUpdateAddress = vi.fn();
		const wrapper = shallowMount(InvoiceDeliveryAddress, {
			props: {
				customer: "Jane Smith",
				invoiceDoc: {},
				"onUpdate:address": onUpdateAddress,
			},
		});

		await flushPromises();

		// Should render text field, not dropdown
		expect(wrapper.find("v-text-field").exists()).toBe(true);
		expect(wrapper.find("v-autocomplete").exists()).toBe(false);

		const field = wrapper.find("v-text-field");
		const val =
			field.attributes("modelvalue") ||
			field.attributes("model-value") ||
			(field.props() as any)?.modelValue ||
			"";
		expect(val).toContain("123 Elm St");

		expect(onUpdateAddress).toHaveBeenCalled();
		expect(onUpdateAddress.mock.calls[0][0]?.name).toBe("ADDR-001");
	});

	it("renders placeholder text field when customer has 0 addresses", async () => {
		mockGetCachedCustomerAddresses.mockReturnValue([]);

		const { default: InvoiceDeliveryAddress } = await import(
			"../src/posapp/components/pos/invoice/InvoiceDeliveryAddress.vue"
		);

		const wrapper = shallowMount(InvoiceDeliveryAddress, {
			props: {
				customer: "No Address Customer",
				invoiceDoc: {},
			},
		});

		await flushPromises();

		expect(wrapper.find("v-text-field").exists()).toBe(true);
		expect(wrapper.find("v-autocomplete").exists()).toBe(false);

		const field = wrapper.find("v-text-field");
		expect(field.attributes("placeholder")).toContain("No address found");
	});

	it("renders select customer placeholder when no customer is provided", async () => {
		mockGetCachedCustomerAddresses.mockReturnValue([]);

		const { default: InvoiceDeliveryAddress } = await import(
			"../src/posapp/components/pos/invoice/InvoiceDeliveryAddress.vue"
		);

		const wrapper = shallowMount(InvoiceDeliveryAddress, {
			props: {
				customer: "",
				invoiceDoc: {},
			},
		});

		await flushPromises();

		expect(wrapper.find("v-text-field").exists()).toBe(true);
		expect(wrapper.find("v-autocomplete").exists()).toBe(false);

		const field = wrapper.find("v-text-field");
		expect(field.attributes("placeholder")).toContain("Select customer first");
	});

	it("emits updated address when a new address is selected from autocomplete", async () => {
		mockGetCachedCustomerAddresses.mockReturnValue([
			{
				name: "ADDR-001",
				address_title: "Home",
				address_line1: "123 Elm St",
				city: "Springfield",
				address_type: "Shipping",
			},
			{
				name: "ADDR-002",
				address_title: "Office",
				address_line1: "456 Tech Blvd",
				city: "Metropolis",
				address_type: "Billing",
			},
		]);

		const { default: InvoiceDeliveryAddress } = await import(
			"../src/posapp/components/pos/invoice/InvoiceDeliveryAddress.vue"
		);

		const onUpdateAddress = vi.fn();
		const wrapper = shallowMount(InvoiceDeliveryAddress, {
			props: {
				customer: "John Doe",
				invoiceDoc: {},
				"onUpdate:address": onUpdateAddress,
			},
		});

		await flushPromises();

		// Initial address emitted: ADDR-001
		expect(onUpdateAddress).toHaveBeenCalledWith(
			expect.objectContaining({ name: "ADDR-001" }),
		);

		// Now simulate selecting ADDR-002
		const autocomplete = wrapper.find("v-autocomplete");
		await autocomplete.trigger("update:model-value", "ADDR-002");
		// In template: @update:model-value="onAddressSelected"
		(wrapper.vm as any).onAddressSelected("ADDR-002");
		await flushPromises();

		expect(onUpdateAddress).toHaveBeenLastCalledWith(
			expect.objectContaining({ name: "ADDR-002" }),
		);
	});

	it("emits address update when entering manual address for customer with 0 addresses", async () => {
		mockGetCachedCustomerAddresses.mockReturnValue([]);

		const { default: InvoiceDeliveryAddress } = await import(
			"../src/posapp/components/pos/invoice/InvoiceDeliveryAddress.vue"
		);

		const onUpdateAddress = vi.fn();
		const wrapper = shallowMount(InvoiceDeliveryAddress, {
			props: {
				customer: "New Customer",
				invoiceDoc: {},
				"onUpdate:address": onUpdateAddress,
			},
		});

		await flushPromises();

		(wrapper.vm as any).onManualAddressInput("789 Oak Ave, Springfield");
		await flushPromises();

		expect(onUpdateAddress).toHaveBeenLastCalledWith(
			expect.objectContaining({
				name: "",
				address_display: "789 Oak Ave, Springfield",
			}),
		);
	});
});
