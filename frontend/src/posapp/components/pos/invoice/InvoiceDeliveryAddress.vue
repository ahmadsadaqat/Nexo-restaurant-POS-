<template>
	<div class="delivery-address-container" :title="selectedAddressFullText || ''">
		<!-- Customer Has An Address: Show Single Address Field with Edit Action -->
		<v-text-field
			v-if="hasAddress"
			:model-value="singleAddressDisplay"
			density="compact"
			variant="solo"
			color="primary"
			class="pos-themed-input sleek-field delivery-address-input address-field-clickable"
			:label="__('Delivery Address')"
			prepend-inner-icon="mdi-map-marker"
			hide-details
			readonly
			:loading="loading"
			@click="openEditAddressDialog"
		>
			<template #append-inner>
				<v-icon
					size="small"
					class="icon-btn mr-1"
					color="primary"
					:title="__('Edit address')"
					@click.stop="openEditAddressDialog"
				>
					mdi-pencil
				</v-icon>
			</template>
		</v-text-field>

		<!-- Zero Addresses / No Customer: Show Helper Field with Add Action -->
		<v-text-field
			v-else
			:model-value="manualAddressDisplay"
			density="compact"
			variant="solo"
			color="primary"
			class="pos-themed-input sleek-field delivery-address-input"
			:label="__('Delivery Address')"
			:placeholder="
				customer
					? __('No address found - Click + to add')
					: __('Select customer first')
			"
			prepend-inner-icon="mdi-map-marker-outline"
			append-inner-icon="mdi-plus"
			@click:append-inner="openNewAddressDialog"
			hide-details
			:readonly="!customer"
			:loading="loading"
			@click="customer ? openNewAddressDialog() : undefined"
			@update:model-value="onManualAddressInput"
		></v-text-field>

		<!-- Address Verification Helper Line -->
		<div
			v-if="selectedAddressFullText"
			class="delivery-address-preview text-caption mt-1"
			:title="selectedAddressFullText"
		>
			<v-icon size="12" color="primary" class="mr-1">mdi-map-marker-check</v-icon>
			<span class="delivery-address-preview__label font-weight-medium text-primary mr-1">{{ __("Delivery to:") }}</span>
			<span class="delivery-address-preview__text">{{ selectedAddressFullText }}</span>
		</div>
	</div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick, inject } from "vue";
import { getCachedCustomerAddresses, saveCustomerAddressesCache } from "../../../../offline/index";
import { bus } from "../../../bus";
import { useToastStore } from "../../../stores/toastStore.js";

const __ =
	(typeof window !== "undefined" && (window as any).__) ||
	((text: string) => text);

export interface DeliveryAddressItem {
	name: string;
	address_title?: string;
	address_line1?: string;
	address_line2?: string;
	city?: string;
	state?: string;
	country?: string;
	address_type?: string;
	display_title?: string;
	clean_display?: string;
	title?: string;
	full_address?: string;
	[key: string]: any;
}

const props = withDefaults(
	defineProps<{
		customer?: string | null;
		customerInfo?: Record<string, any> | null;
		invoiceDoc?: Record<string, any> | null;
	}>(),
	{
		customer: "",
		customerInfo: () => ({}),
		invoiceDoc: () => ({}),
	},
);

const emit = defineEmits(["update:address"]);

const toastStore = useToastStore();
const injectedBus = inject("eventBus", bus) as any;
const eventBus = injectedBus || bus;

const addresses = ref<DeliveryAddressItem[]>([]);
const selectedAddressName = ref<string | null>(null);
const manualAddressText = ref("");
const loading = ref(false);

const normalizeAddress = (address: any): DeliveryAddressItem | null => {
	if (!address) return null;
	const addr = { ...address };
	const parts = [
		addr.address_line1,
		addr.address_line2,
		addr.city,
		addr.state,
		addr.country,
	].filter(Boolean);
	const fullLine = parts.join(", ");

	const cleanTitle = fullLine || addr.address_line1 || addr.name || "";

	return {
		...addr,
		display_title: cleanTitle,
		clean_display: cleanTitle,
		title: cleanTitle,
		full_address: fullLine || cleanTitle,
	};
};

// Enforce single address model: a customer has 0 or 1 active delivery address
const hasAddress = computed(() => addresses.value.length > 0 && Boolean(addresses.value[0]?.name));
const hasSingleAddress = computed(() => hasAddress.value);
const hasMultipleAddresses = computed(() => false);

const selectedAddress = computed(() => {
	if (addresses.value.length > 0 && addresses.value[0]) {
		return addresses.value[0];
	}
	return null;
});

const singleAddressDisplay = computed(() => {
	if (addresses.value.length > 0 && addresses.value[0]) {
		return (
			addresses.value[0].clean_display ||
			addresses.value[0].full_address ||
			addresses.value[0].display_title ||
			addresses.value[0].address_line1 ||
			addresses.value[0].name ||
			""
		);
	}
	return "";
});

const selectedAddressFullText = computed(() => {
	if (selectedAddress.value) {
		return (
			selectedAddress.value.full_address ||
			selectedAddress.value.clean_display ||
			selectedAddress.value.address_line1 ||
			""
		);
	}
	if (props.invoiceDoc?.address_display) {
		return props.invoiceDoc.address_display;
	}
	return manualAddressText.value || "";
});

const manualAddressDisplay = computed(() => {
	if (props.invoiceDoc?.address_display) {
		return props.invoiceDoc.address_display;
	}
	return manualAddressText.value;
});

const addressOptions = computed(() => {
	return addresses.value.map((addr) => {
		const full = addr.full_address || addr.address_line1 || addr.city || "";
		return {
			title: addr.clean_display || addr.display_title || addr.name,
			subtitle: addr.address_type ? `${addr.address_type}: ${full}` : full,
			value: addr.name,
			raw: addr,
		};
	});
});

const emitAddress = (addr: DeliveryAddressItem | null) => {
	emit("update:address", addr);
};

const pickPreferredAddress = (list: DeliveryAddressItem[]): DeliveryAddressItem | null => {
	if (!list.length) return null;
	// 1. If invoiceDoc already specifies an address
	const existing =
		props.invoiceDoc?.shipping_address_name ||
		props.invoiceDoc?.customer_address;
	if (existing) {
		const match = list.find((a) => a.name === existing);
		if (match) return match;
	}
	// 2. Shipping address type
	const shipping = list.find((a) => (a.address_type || "").toLowerCase() === "shipping");
	if (shipping) return shipping;
	// 3. First address
	return list[0] || null;
};

const syncSelection = () => {
	const preferred = addresses.value[0];
	if (!preferred) {
		selectedAddressName.value = null;
		emitAddress(null);
		return;
	}

	selectedAddressName.value = preferred.name;
	nextTick(() => {
		emitAddress(preferred);
	});
};

const fetchAddresses = async (customerName = props.customer) => {
	if (!customerName) {
		addresses.value = [];
		selectedAddressName.value = null;
		manualAddressText.value = "";
		emitAddress(null);
		return;
	}

	loading.value = true;

	// 1. Offline cache check
	try {
		const cached = getCachedCustomerAddresses(customerName);
		if (Array.isArray(cached) && cached.length) {
			const normalized = cached
				.map(normalizeAddress)
				.filter((a): a is DeliveryAddressItem => a !== null);
			const best = pickPreferredAddress(normalized);
			addresses.value = best ? [best] : [];
			syncSelection();
		}
	} catch (e) {
		console.error("[InvoiceDeliveryAddress] Cache lookup error:", e);
	}

	// 2. Online API check
	const frappeObj = typeof window !== "undefined" ? (window as any).frappe : undefined;
	if (frappeObj && typeof frappeObj.call === "function") {
		try {
			const r = await frappeObj.call({
				method: "posawesome.posawesome.api.customers.get_customer_addresses",
				args: { customer: customerName },
			});
			if (!r?.exc && Array.isArray(r?.message)) {
				const normalized = r.message
					.map(normalizeAddress)
					.filter((a): a is DeliveryAddressItem => a !== null);
				const best = pickPreferredAddress(normalized);
				addresses.value = best ? [best] : [];
				saveCustomerAddressesCache(customerName, addresses.value);
				syncSelection();
			}
		} catch (e) {
			console.error("[InvoiceDeliveryAddress] API fetch error:", e);
		}
	}

	// 3. Fallback: check customerInfo if addresses still empty
	if (!addresses.value.length && props.customerInfo) {
		const line1 =
			props.customerInfo.address_line1 ||
			props.customerInfo.primary_address ||
			props.customerInfo.customer_address;
		if (line1) {
			const fallback = normalizeAddress({
				name:
					props.customerInfo.customer_address ||
					props.customerInfo.primary_address ||
					"Customer Address",
				address_title: props.customerInfo.customer_name || customerName,
				address_line1: line1,
				address_line2: props.customerInfo.address_line2 || "",
				city: props.customerInfo.city || "",
				state: props.customerInfo.state || "",
				country: props.customerInfo.country || "",
				address_type: "Shipping",
			});
			if (fallback) {
				addresses.value = [fallback];
				syncSelection();
			}
		}
	}

	loading.value = false;
};

const onAddressSelected = (val: string | null) => {
	selectedAddressName.value = val;
	if (val) {
		const match = addresses.value.find((a) => a.name === val) || null;
		emitAddress(match);
	} else {
		emitAddress(null);
	}
};

const onManualAddressInput = (val: string) => {
	manualAddressText.value = val;
	emitAddress({
		name: "",
		address_display: val,
		display_title: val,
		clean_display: val,
		title: val,
		full_address: val,
	});
};

const openNewAddressDialog = () => {
	if (!props.customer) {
		toastStore.show({
			title: __("Please select a customer first"),
			color: "warning",
		});
		return;
	}
	// If the customer already has an address, redirect to editing that single address
	if (selectedAddress.value) {
		openEditAddressDialog();
		return;
	}
	eventBus?.emit("open_new_address", props.customer);
};

const openEditAddressDialog = () => {
	if (!props.customer) {
		toastStore.show({
			title: __("Please select a customer first"),
			color: "warning",
		});
		return;
	}
	if (!selectedAddress.value) {
		openNewAddressDialog();
		return;
	}
	eventBus?.emit("open_edit_address", {
		customer: props.customer,
		address: selectedAddress.value,
	});
};

const handleNewAddressCreated = (newAddr: any) => {
	if (!newAddr) return;
	const normalized = normalizeAddress(newAddr);
	if (!normalized) return;
	addresses.value = [normalized];
	if (props.customer) {
		saveCustomerAddressesCache(props.customer, addresses.value);
	}
	selectedAddressName.value = normalized.name;
	emitAddress(normalized);
};

const handleAddressUpdated = (updatedAddr: any) => {
	if (!updatedAddr) return;
	const normalized = normalizeAddress(updatedAddr);
	if (!normalized) return;
	addresses.value = [normalized];
	if (props.customer) {
		saveCustomerAddressesCache(props.customer, addresses.value);
	}
	selectedAddressName.value = normalized.name;
	emitAddress(normalized);
};

watch(
	() => props.customer,
	(newCust) => {
		fetchAddresses(newCust);
	},
	{ immediate: true },
);

watch(
	() => props.customerInfo,
	() => {
		if (!addresses.value.length && props.customer) {
			fetchAddresses(props.customer);
		}
	},
	{ deep: true },
);

watch(
	() => [
		props.invoiceDoc?.shipping_address_name,
		props.invoiceDoc?.customer_address,
	],
	() => {
		const target =
			props.invoiceDoc?.shipping_address_name ||
			props.invoiceDoc?.customer_address;
		if (target && target !== selectedAddressName.value) {
			const match = addresses.value.find((a) => a.name === target);
			if (match) {
				selectedAddressName.value = target;
			}
		}
	},
);

onMounted(() => {
	eventBus?.on("add_the_new_address", handleNewAddressCreated);
	eventBus?.on("address_updated", handleAddressUpdated);
});

onBeforeUnmount(() => {
	eventBus?.off("add_the_new_address", handleNewAddressCreated);
	eventBus?.off("address_updated", handleAddressUpdated);
});

defineExpose({
	addresses,
	selectedAddress,
	selectedAddressName,
	manualAddressText,
	onAddressSelected,
	onManualAddressInput,
	fetchAddresses,
	openNewAddressDialog,
	openEditAddressDialog,
});
</script>

<style scoped>
.delivery-address-container {
	width: 100%;
	min-width: 0;
	display: flex;
	flex-direction: column;
	align-items: stretch;
}

.delivery-address-input {
	width: 100%;
	min-width: 0;
}

.address-field-clickable {
	cursor: pointer;
}

.address-field-clickable :deep(input) {
	cursor: pointer;
}

.icon-btn {
	cursor: pointer;
	opacity: 0.8;
	transition: opacity 0.2s ease, transform 0.15s ease;
}

.icon-btn:hover {
	opacity: 1;
	transform: scale(1.1);
}

.delivery-address-preview {
	display: flex;
	align-items: center;
	padding: 2px 4px;
	color: var(--pos-text-secondary, #666);
	overflow: hidden;
	white-space: nowrap;
	text-overflow: ellipsis;
	max-width: 100%;
}

.delivery-address-preview__label {
	flex: 0 0 auto;
}

.delivery-address-preview__text {
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}
</style>
