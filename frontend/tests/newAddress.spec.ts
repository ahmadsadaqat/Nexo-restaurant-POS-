// @vitest-environment jsdom

import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { shallowMount } from "@vue/test-utils";

import NewAddress from "../src/posapp/components/pos/customer/NewAddress.vue";

describe("NewAddress", () => {
	beforeEach(() => {
		setActivePinia(createPinia());
		vi.clearAllMocks();
		(globalThis as any).__ = (value: string) => value;
		(globalThis as any).frappe = {
			_: (value: string) => value,
			call: vi.fn(),
		};
	});

	it("shows only Address Line 1 and selects the created address", async () => {
		const eventBus = {
			on: vi.fn(),
			off: vi.fn(),
			emit: vi.fn(),
		};
		const wrapper = shallowMount(NewAddress, {
			global: {
				config: {
					globalProperties: {
						__: (value: string) => value,
						frappe: (globalThis as any).frappe,
						eventBus,
					},
				},
			},
		});

		expect(wrapper.findAll("v-text-field")).toHaveLength(1);
		expect(wrapper.get("v-text-field").attributes("label")).toBe("Address Line 1");

		(wrapper.vm as any).customer = "John Doe";
		(wrapper.vm as any).address.address_line1 = "  789 Oak Avenue  ";
		(wrapper.vm as any).submit_dialog();

		expect((globalThis as any).frappe.call).toHaveBeenCalledWith(
			expect.objectContaining({
				method: "posawesome.posawesome.api.customers.make_address",
				args: {
					args: {
						name: "789 Oak Avenue",
						address_line1: "789 Oak Avenue",
						customer: "John Doe",
						doctype: "Customer",
					},
				},
			}),
		);

		const callOptions = vi.mocked((globalThis as any).frappe.call).mock.calls[0][0];
		const createdAddress = {
			name: "789 Oak Avenue-Shipping",
			address_title: "789 Oak Avenue",
			address_line1: "789 Oak Avenue",
			address_type: "Shipping",
		};
		callOptions.callback({ message: createdAddress });

		expect(eventBus.emit).toHaveBeenCalledWith(
			"add_the_new_address",
			createdAddress,
		);
		expect((wrapper.vm as any).addressDialog).toBe(false);
		expect((wrapper.vm as any).address.address_line1).toBe("");
	});

	it("opens in edit mode on open_edit_address and updates existing address", async () => {
		const listeners: Record<string, Function> = {};
		const eventBus = {
			on: vi.fn((event, cb) => {
				listeners[event] = cb;
			}),
			off: vi.fn(),
			emit: vi.fn(),
		};
		const wrapper = shallowMount(NewAddress, {
			global: {
				config: {
					globalProperties: {
						__: (value: string) => value,
						frappe: (globalThis as any).frappe,
						eventBus,
					},
				},
			},
		});

		expect(listeners["open_edit_address"]).toBeDefined();

		// Trigger open_edit_address
		listeners["open_edit_address"]({
			customer: "Ali Hamza",
			address: {
				name: "Ali Hamza-Shipping",
				address_title: "Ali Hamza",
				address_line1: "Old Street 123",
				city: "Lahore",
			},
		});

		expect((wrapper.vm as any).isEditing).toBe(true);
		expect((wrapper.vm as any).addressDialog).toBe(true);
		expect((wrapper.vm as any).address.address_line1).toBe("Old Street 123");
		expect((wrapper.vm as any).address.name).toBe("Ali Hamza-Shipping");

		// Modify address and submit
		(wrapper.vm as any).address.address_line1 = "New Street 456";
		(wrapper.vm as any).submit_dialog();

		expect((globalThis as any).frappe.call).toHaveBeenCalledWith(
			expect.objectContaining({
				method: "posawesome.posawesome.api.customers.update_address",
				args: {
					args: {
						name: "Ali Hamza-Shipping",
						address_line1: "New Street 456",
						customer: "Ali Hamza",
					},
				},
			}),
		);

		const callOptions = vi.mocked((globalThis as any).frappe.call).mock.calls[0][0];
		const updatedAddress = {
			name: "Ali Hamza-Shipping",
			address_title: "New Street 456",
			address_line1: "New Street 456",
			city: "Lahore",
		};
		callOptions.callback({ message: updatedAddress });

		expect(eventBus.emit).toHaveBeenCalledWith(
			"address_updated",
			updatedAddress,
		);
		expect((wrapper.vm as any).addressDialog).toBe(false);
		expect((wrapper.vm as any).isEditing).toBe(false);
	});
});
