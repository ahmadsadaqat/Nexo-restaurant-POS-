<template>
	<v-row justify="center">
		<v-dialog v-model="addressDialog" max-width="600px">
			<v-card>
				<v-card-title>
					<span class="text-h5 text-primary">{{ __("Add New Address") }}</span>
				</v-card-title>
				<v-card-text class="pa-0">
					<v-container>
						<v-row>
							<v-col cols="12">
								<v-text-field
									data-test="new-address-line-1"
									density="compact"
									color="primary"
									:label="__('Address Line 1')"
									class="pos-themed-input"
									hide-details
									v-model="address.address_line1"
									autofocus
									@keyup.enter="submit_dialog"
								></v-text-field>
							</v-col>
						</v-row>
					</v-container>
				</v-card-text>
				<v-card-actions>
					<v-spacer></v-spacer>
					<v-btn color="error" theme="dark" @click="close_dialog">{{ __("Close") }}</v-btn>
					<v-btn
						data-test="new-address-submit"
						color="success"
						theme="dark"
						:loading="creatingAddress"
						:disabled="creatingAddress"
						@click="submit_dialog"
					>
						{{ __("Submit") }}
					</v-btn>
				</v-card-actions>
			</v-card>
		</v-dialog>
	</v-row>
</template>

<script>
import { useToastStore } from "../../../stores/toastStore";

export default {
	setup() {
		const toastStore = useToastStore();
		return { toastStore };
	},
	data: () => ({
		addressDialog: false,
		address: {
			address_line1: "",
		},
		customer: "",
		creatingAddress: false,
		openNewAddressHandler: null,
	}),
	computed: {},

	methods: {
		close_dialog() {
			this.addressDialog = false;
			this.address = { address_line1: "" };
		},

		submit_dialog() {
			const addressLine1 = (this.address.address_line1 || "").trim();
			if (!addressLine1) {
				this.toastStore.show({
					text: __("Address Line 1 is required."),
					color: "warning",
				});
				return;
			}

			this.creatingAddress = true;
			frappe.call({
				method: "posawesome.posawesome.api.customers.make_address",
				args: {
					args: {
						name: addressLine1,
						address_line1: addressLine1,
						customer: this.customer,
						doctype: "Customer",
					},
				},
				callback: (r) => {
					this.creatingAddress = false;
					if (!r.exc) {
						this.eventBus.emit("add_the_new_address", r.message);
						this.toastStore.show({
							text: __("Customer Address created successfully."),
							color: "success",
						});
						this.addressDialog = false;
						this.customer = "";
						this.address = { address_line1: "" };
					}
				},
				error: () => {
					this.creatingAddress = false;
				},
			});
		},
	},
	created: function () {
		this.openNewAddressHandler = (data) => {
			this.address = { address_line1: "" };
			this.addressDialog = true;
			this.customer = data;
		};
		this.eventBus.on("open_new_address", this.openNewAddressHandler);
	},
	beforeUnmount() {
		if (this.openNewAddressHandler) {
			this.eventBus.off("open_new_address", this.openNewAddressHandler);
			this.openNewAddressHandler = null;
		}
	},
};
</script>

<style scoped></style>
