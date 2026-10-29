// @vitest-environment jsdom

import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { shallowMount } from "@vue/test-utils";

import NewAddress from "../src/posapp/components/pos/customer/NewAddress.vue";

describe("NewAddress", () => {
	beforeEach(() => {
		setActivePinia(createPinia());
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
});
