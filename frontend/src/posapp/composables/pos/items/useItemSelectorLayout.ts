import { ref, computed, onMounted, onUnmounted, nextTick } from "vue";
import _ from "lodash";
import {
	getCardColumns,
	getCardGap,
	getCardPadding,
} from "../../../utils/itemSelectorLayout.js";

type SelectorLayoutOptions = {
	resizeDebounce?: number;
	loadVisibleItems?: () => void;
};

/**
 * Manages the layout metrics and resize behavior for the ItemsSelector component.
 * Handles calculation of grid columns, card dimensions, and overflow detection.
 */
export function useItemSelectorLayout(options: SelectorLayoutOptions = {}) {
	const {
		resizeDebounce = 100,
		loadVisibleItems, // Method to load more items on scroll (pagination)
	} = options;

	// State
	const windowWidth = ref(window.innerWidth);
	const containerActualWidth = ref(0);
	const isOverflowing = ref(false);
	const itemsContainerRef = ref<any>(null);
	const scrollThrottle = ref<number | null>(null);

	// Computed Metrics
	const cardContainerWidth = computed(() => {
		if (containerActualWidth.value > 0) {
			return containerActualWidth.value;
		}
		return windowWidth.value * 0.4; // Approx 40% of screen for items selector usually
	});

	const cardColumns = computed(() => getCardColumns(cardContainerWidth.value, windowWidth.value));
	const cardGap = computed(() => getCardGap(cardContainerWidth.value, windowWidth.value));
	const cardPadding = computed(() => getCardPadding(cardContainerWidth.value, windowWidth.value));

	const cardRowHeight = computed(() => {
		if (windowWidth.value <= 768) {
			return 210;
		}
		if (windowWidth.value <= 1200) {
			return 230;
		}
		return 240;
	});

	const cardSlotHeight = computed(() => cardRowHeight.value + cardGap.value);
	const cardSlotWidth = computed(() => cardColumnWidth.value + cardGap.value);

	const cardColumnWidth = computed(() => {
		const columns = Math.max(1, cardColumns.value);
		const containerWidth = cardContainerWidth.value || 0;
		if (!containerWidth) {
			return 240; // Safe default
		}

		const gapTotal = cardGap.value * (columns - 1);
		const paddingTotal = cardPadding.value * 2;
		const available = Math.max(0, containerWidth - gapTotal - paddingTotal);
		const width = Math.floor(available / columns);
		return Math.max(140, width);
	});

	// Actions
	const updateWindowWidth = () => {
		windowWidth.value = window.innerWidth;
	};

	const scheduleCardMetricsUpdate = _.debounce(() => {
		updateWindowWidth();
		if (itemsContainerRef.value && itemsContainerRef.value.$el) {
			containerActualWidth.value = itemsContainerRef.value.$el.clientWidth;
		} else if (itemsContainerRef.value) {
			containerActualWidth.value = itemsContainerRef.value.clientWidth || 0;
		}
		checkItemContainerOverflow();
	}, resizeDebounce);

	const getItemsContainerElement = (): HTMLElement | null => {
		if (!itemsContainerRef.value) return null;
		// Handle both Vue component ref and raw element
		return (itemsContainerRef.value.$el ||
			itemsContainerRef.value) as HTMLElement | null;
	};

	const checkItemContainerOverflow = () => {
		const el = getItemsContainerElement();
		if (!el) {
			isOverflowing.value = false;
			return;
		}

		const shell = el.closest(".items-selector-shell") as HTMLElement | null;
		let containerHeight = window.innerHeight * 0.85; // Fallback

		if (shell) {
			containerHeight = shell.clientHeight;
		} else {
			const rawVal = getComputedStyle(el).getPropertyValue("--container-height");
			if (rawVal.includes("vh")) {
				containerHeight = (parseFloat(rawVal) / 100) * window.innerHeight;
			} else {
				containerHeight = parseFloat(rawVal);
			}
		}

		if (isNaN(containerHeight) || containerHeight <= 0) {
			isOverflowing.value = false;
			return;
		}

		const stickyHeader = el
			.closest(".dynamic-padding")
			?.querySelector(".sticky-header") as HTMLElement | null;
		const headerHeight = stickyHeader ? stickyHeader.offsetHeight : 0;
		// Leave a small buffer for paddings/margins
		const availableHeight = containerHeight - headerHeight - 30;

		// Only apply if calculated height is valid
		if (availableHeight > 0) {
			el.style.maxHeight = `${availableHeight}px`;
			isOverflowing.value = el.scrollHeight > availableHeight;
		}
	};

	const onListScroll = (event: Event) => {
		if (scrollThrottle.value) return;

		scrollThrottle.value = requestAnimationFrame(() => {
			try {
				const el = event.target as HTMLElement | null;
				if (!el) return;
				if (el.scrollTop + el.clientHeight >= el.scrollHeight - 50) {
					// Trigger pagination via callback
					if (typeof loadVisibleItems === "function") {
						loadVisibleItems();
					}
				}
			} catch (error: unknown) {
				console.error("Error in list scroll handler:", error);
			} finally {
				scrollThrottle.value = null;
			}
		});
	};

	let resizeObserver: ResizeObserver | null = null;

	// Lifecycle
	onMounted(() => {
		window.addEventListener("resize", scheduleCardMetricsUpdate);
		nextTick(() => {
			updateWindowWidth();
			const el = getItemsContainerElement();
			if (el) {
				containerActualWidth.value = el.clientWidth;
				if (typeof ResizeObserver !== 'undefined') {
					resizeObserver = new ResizeObserver(() => {
						if (el.clientWidth > 0 && el.clientWidth !== containerActualWidth.value) {
							containerActualWidth.value = el.clientWidth;
							checkItemContainerOverflow();
						}
					});
					resizeObserver.observe(el);
				}
			}
			checkItemContainerOverflow();
		});
	});

	onUnmounted(() => {
		window.removeEventListener("resize", scheduleCardMetricsUpdate);
		if (resizeObserver) {
			resizeObserver.disconnect();
			resizeObserver = null;
		}
		if (scrollThrottle.value) {
			cancelAnimationFrame(scrollThrottle.value);
		}
		scheduleCardMetricsUpdate.cancel();
	});

	return {
		// Refs
		windowWidth,
		isOverflowing,
		itemsContainerRef, // Bind this to the container in template

		// Computed
		cardColumns,
		cardGap,
		cardPadding,
		cardRowHeight,
		cardSlotHeight,
		cardSlotWidth,
		cardColumnWidth,

		// Methods
		checkItemContainerOverflow,
		scheduleCardMetricsUpdate,
		onListScroll,
	};
}
