<template>
	<v-row justify="center">
		<v-dialog v-model="visible" max-width="500px" persistent>
			<v-card min-height="300px" class="addon-dialog-card">
				<v-card-title class="d-flex align-center justify-between pb-2 border-bottom">
					<span class="text-h5 text-primary">{{ __("Select Add-Ons") }} - {{ item?.item_name || item?.item_code }}</span>
					<v-spacer></v-spacer>
					<v-btn color="grey-lighten-1" variant="text" icon="mdi-close" @click="skipSelection"></v-btn>
				</v-card-title>

				<v-card-text class="pa-4">
					<div v-if="loading" class="d-flex justify-center align-center py-8">
						<v-progress-circular indeterminate color="primary"></v-progress-circular>
					</div>
					<div v-else-if="!addons.length" class="text-center py-8 text-medium-emphasis">
						{{ __("No add-ons available for this item.") }}
					</div>
					<v-list v-else select-strategy="multiple" class="pa-0">
						<v-list-item
							v-for="addon in addons"
							:key="addon.item_code"
							class="addon-list-item mb-2 border rounded-lg"
							@click="toggleSelection(addon)"
						>
							<template v-slot:prepend>
								<v-checkbox-btn
									:model-value="isSelected(addon)"
									color="primary"
									@click.stop="toggleSelection(addon)"
								></v-checkbox-btn>
							</template>

							<v-list-item-title class="font-weight-medium">
								{{ addon.item_name || addon.item_code }}
							</v-list-item-title>

							<template v-slot:append>
								<span class="text-subtitle-1 font-weight-bold text-primary">
									+ {{ formatCurrency(addon.price) }}
								</span>
							</template>
						</v-list-item>
					</v-list>
				</v-card-text>

				<v-card-actions class="pa-4 border-top">
					<v-btn
						color="grey-darken-1"
						variant="outlined"
						rounded="pill"
						@click="skipSelection"
						class="px-6"
					>
						{{ __("Skip") }}
					</v-btn>
					<v-spacer></v-spacer>
					<v-btn
						color="primary"
						variant="flat"
						rounded="pill"
						@click="confirmSelection"
						class="px-6"
						:disabled="loading"
					>
						{{ __("Add to Cart") }}
					</v-btn>
				</v-card-actions>
			</v-card>
		</v-dialog>
	</v-row>
</template>

<script setup>
import { ref, watch, computed } from "vue";

const props = defineProps({
	modelValue: { type: Boolean, default: false },
	item: { type: Object, default: null },
	posProfile: { type: Object, default: null },
});

const emit = defineEmits(["update:modelValue", "confirm", "skip"]);

const visible = computed({
	get: () => props.modelValue,
	set: (val) => emit("update:modelValue", val),
});

const addons = ref([]);
const selectedAddons = ref([]);
const loading = ref(false);

const isSelected = (addon) => {
	return selectedAddons.value.some((a) => a.item_code === addon.item_code);
};

const toggleSelection = (addon) => {
	const index = selectedAddons.value.findIndex((a) => a.item_code === addon.item_code);
	if (index > -1) {
		selectedAddons.value.splice(index, 1);
	} else {
		selectedAddons.value.push(addon);
	}
};

const fetchAddons = async () => {
	if (!props.item?.item_code) return;
	loading.value = true;
	addons.value = [];
	selectedAddons.value = [];
	try {
		const res = await frappe.call({
			method: "nexo_ota.nexo_ota.api.get_item_addons",
			args: {
				item_code: props.item.item_code,
				price_list: props.posProfile?.selling_price_list || "Standard Selling",
			},
		});
		if (res && res.message) {
			addons.value = res.message;
		}
	} catch (e) {
		console.error("Failed to fetch addons", e);
	} finally {
		loading.value = false;
	}
};

const formatCurrency = (val) => {
	const currency = props.posProfile?.currency || "PKR";
	return new Intl.NumberFormat("en-PK", {
		style: "currency",
		currency: currency,
		minimumFractionDigits: 0,
		maximumFractionDigits: 2,
	}).format(val || 0);
};

watch(
	() => props.modelValue,
	(newVal) => {
		if (newVal) {
			fetchAddons();
		}
	}
);

const confirmSelection = () => {
	emit("confirm", selectedAddons.value);
	visible.value = false;
};

const skipSelection = () => {
	emit("skip");
	visible.value = false;
};
</script>

<style scoped>
.addon-dialog-card {
	border-radius: 16px;
	overflow: hidden;
}
.border-bottom {
	border-bottom: 1px solid var(--pos-border, #e2e8f0);
}
.border-top {
	border-top: 1px solid var(--pos-border, #e2e8f0);
}
.addon-list-item {
	transition: all 0.2s ease;
	cursor: pointer;
}
.addon-list-item:hover {
	background-color: var(--pos-surface-hover, #f8fafc);
	border-color: var(--pos-primary, #3b82f6) !important;
}
</style>
