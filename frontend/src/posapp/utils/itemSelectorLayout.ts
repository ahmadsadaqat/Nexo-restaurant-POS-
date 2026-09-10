/**
 * Utility functions for responsive item card layout.
 */

/**
 * Calculates the number of columns based on container width.
 */
export const getCardColumns = (containerWidth: number, windowWidth: number): number => {
	if (windowWidth <= 768) {
		return 2;
	}
	if (containerWidth > 0) {
		const cols = Math.floor((containerWidth - 20) / 190);
		return Math.max(2, Math.min(cols, 8));
	}
	if (windowWidth <= 1200) {
		return 3;
	}
	return 4;
};

/**
 * Calculates the gap between cards based on container width.
 */
export const getCardGap = (containerWidth: number, windowWidth: number): number => {
	if (windowWidth <= 768) {
		return 10;
	}
	if (windowWidth <= 1200) {
		return 12;
	}
	return 16;
};

/**
 * Calculates the padding for the card container based on container width.
 */
export const getCardPadding = (containerWidth: number, windowWidth: number): number => {
	if (windowWidth <= 768) {
		return 10;
	}
	if (windowWidth <= 1200) {
		return 12;
	}
	return 16;
};
