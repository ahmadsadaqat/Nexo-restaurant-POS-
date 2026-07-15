/**
 * Utility functions for responsive item card layout.
 */

/**
 * Calculates the number of columns based on container width.
 */
export const getCardColumns = (containerWidth: number, windowWidth: number): number => {
	const isFullScreen = containerWidth > windowWidth * 0.6;

	if (windowWidth <= 768) {
		return 2;
	}
	if (windowWidth <= 1200) {
		return isFullScreen ? 5 : 3;
	}
	return isFullScreen ? 7 : 4;
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
