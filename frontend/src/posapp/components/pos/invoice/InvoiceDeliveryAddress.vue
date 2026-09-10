<template>
	<div class="delivery-address-container">
		<!-- Multiple Addresses: Show Dropdown -->
		<v-autocomplete
			v-if="hasMultipleAddresses"
			ref="addressDropdown"
			v-model="selectedAddressName"
			:items="addressOptions"
			item-title="title"
			item-value="value"
			density="compact"
			variant="solo"
			color="primary"
			class="pos-themed-input sleek-field delivery-address-input"
			:label="__('Delivery Address')"
			:placeholder="__('Select delivery address')"
			prepend-inner-icon="mdi-map-marker"
			append-inner-icon="mdi-plus"
			@click:append-inner="openNewAddressDialog"
			hide-details
			clearable
			autocomplete="off"
			auto-select-first
			:loading="loading"
			@update:model-value="onAddressSelected"
		>
			<template #item="{ props: itemProps, item }">
				<v-list-item v-bind="itemProps" :title="item.raw.title" :subtitle="item.raw.subtitle">
					<template #prepend>
						<v-icon size="small" color="primary">mdi-map-marker-outline</v-icon>
					</template>
				</v-list-item>
			</template>
		</v-autocomplete>

		<!-- Single Address: Show Text Field with Fetched Address -->
		<v-text-field
			v-else-if="hasSingleAddress"
			:model-value="singleAddressDisplay"
			density="compact"
			variant="solo"
			color="primary"
			class="pos-themed-input sleek-field delivery-address-input"
			:label="__('Delivery Address')"
			prepend-inner-icon="mdi-map-marker"
			append-inner-icon="mdi-plus"
			@click:append-inner="openNewAddressDialog"
			hide-details
			readonly
			:loading="loading"
		></v-text-field>

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
			@update:model-value="onManualAddressInput"
		></v-text-field>
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
	const title = addr.address_title || addr.name || fullLine;
	const display =
		title && fullLine && title !== fullLine
			? `${title} - ${fullLine}`
			: fullLine || title || addr.name;

	return {
		...addr,
		display_title: display,
		title,
		full_address: fullLine,
	};
};

const hasMultipleAddresses = computed(() => addresses.value.length > 1);
const hasSingleAddress = computed(() => addresses.value.length === 1);

const singleAddressDisplay = computed(() => {
	if (addresses.value.length === 1 && addresses.value[0]) {
		return addresses.value[0].display_title || addresses.value[0].name || "";
	}
	return "";
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
			title: addr.display_title || addr.name,
			subtitle: addr.address_type ? `${addr.address_type}: ${full}` : full,
			value: addr.name,
			raw: addr,
		};
	});
});

const emitAddress = (addr: DeliveryAddressItem | null) => {
	emit("update:address", addr);
};

const syncSelection = () => {
	if (!addresses.value.length) {
		selectedAddressName.value = null;
		emitAddress(null);
		return;
	}

	// 1. Check if invoiceDoc already specifies an address that exists
	const existing =
		props.invoiceDoc?.shipping_address_name ||
		props.invoiceDoc?.customer_address;
	if (existing && addresses.value.some((a) => a.name === existing)) {
		selectedAddressName.value = existing;
		const match = addresses.value.find((a) => a.name === existing) || null;
		nextTick(() => {
			emitAddress(match);
		});
		return;
	}

	// 2. Default to shipping address type if available, otherwise first address
	const preferred =
		addresses.value.find(
			(a) => (a.address_type || "").toLowerCase() === "shipping",
		) || addresses.value[0];

	if (preferred) {
		selectedAddressName.value = preferred.name;
		nextTick(() => {
			emitAddress(preferred);
		});
	}
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
			addresses.value = cached
				.map(normalizeAddress)
				.filter((a): a is DeliveryAddressItem => a !== null);
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
				addresses.value = normalized;
				saveCustomerAddressesCache(customerName, normalized);
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
		title: val,
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
	eventBus?.emit("open_new_address", props.customer);
};

const handleNewAddressCreated = (newAddr: any) => {
	if (!newAddr) return;
	const normalized = normalizeAddress(newAddr);
	if (!normalized) return;
	const existing = addresses.value.filter((a) => a.name !== normalized.name);
	addresses.value = [...existing, normalized];
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
});

onBeforeUnmount(() => {
	eventBus?.off("add_the_new_address", handleNewAddressCreated);
});

defineExpose({
	addresses,
	selectedAddressName,
	manualAddressText,
	onAddressSelected,
	onManualAddressInput,
	fetchAddresses,
});
</script>

<style scoped>
.delivery-address-container {
	width: 100%;
	min-width: 0;
	display: flex;
	align-items: center;
}

.delivery-address-input {
	width: 100%;
	min-width: 0;
}
</style>
