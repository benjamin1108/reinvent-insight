/**
 * Color Utility Functions for Testing and Accessibility
 * Provides contrast ratio calculation, color conversion, and WCAG compliance checking
 */

/**
 * Convert RGB color to relative luminance
 * @param {number} r - Red value (0-255)
 * @param {number} g - Green value (0-255)
 * @param {number} b - Blue value (0-255)
 * @returns {number} Relative luminance (0-1)
 */
export function getLuminance(r, g, b) {
  // Normalize RGB values to 0-1
  const [rs, gs, bs] = [r, g, b].map(val => {
    const normalized = val / 255;
    // Apply gamma correction
    return normalized <= 0.03928
      ? normalized / 12.92
      : Math.pow((normalized + 0.055) / 1.055, 2.4);
  });
  
  // Calculate relative luminance using ITU-R BT.709 coefficients
  return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs;
}

/**
 * Calculate contrast ratio between two colors
 * @param {string} color1 - First color (any CSS color format)
 * @param {string} color2 - Second color (any CSS color format)
 * @returns {number} Contrast ratio (1-21)
 */
export function getContrastRatio(color1, color2) {
  const rgb1 = parseColor(color1);
  const rgb2 = parseColor(color2);
  
  if (!rgb1 || !rgb2) {
    console.warn('Invalid color format:', color1, color2);
    return 1;
  }
  
  const lum1 = getLuminance(rgb1.r, rgb1.g, rgb1.b);
  const lum2 = getLuminance(rgb2.r, rgb2.g, rgb2.b);
  
  const lighter = Math.max(lum1, lum2);
  const darker = Math.min(lum1, lum2);
  
  return (lighter + 0.05) / (darker + 0.05);
}

/**
 * Parse CSS color string to RGB object
 * @param {string} color - CSS color string
 * @returns {{r: number, g: number, b: number, a: number}|null}
 */
export function parseColor(color) {
  // Create a temporary element to compute color
  const temp = document.createElement('div');
  temp.style.color = color;
  document.body.appendChild(temp);
  
  const computed = window.getComputedStyle(temp).color;
  document.body.removeChild(temp);
  
  // Parse rgb/rgba format
  const match = computed.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\)/);
  
  if (match) {
    return {
      r: parseInt(match[1]),
      g: parseInt(match[2]),
      b: parseInt(match[3]),
      a: match[4] ? parseFloat(match[4]) : 1
    };
  }
  
  return null;
}

/**
 * Convert RGB to HSL
 * @param {number} r - Red value (0-255)
 * @param {number} g - Green value (0-255)
 * @param {number} b - Blue value (0-255)
 * @returns {{h: number, s: number, l: number}}
 */
export function rgbToHsl(r, g, b) {
  r /= 255;
  g /= 255;
  b /= 255;
  
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  let h, s, l = (max + min) / 2;
  
  if (max === min) {
    h = s = 0; // achromatic
  } else {
    const d = max - min;
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    
    switch (max) {
      case r: h = ((g - b) / d + (g < b ? 6 : 0)) / 6; break;
      case g: h = ((b - r) / d + 2) / 6; break;
      case b: h = ((r - g) / d + 4) / 6; break;
    }
  }
  
  return {
    h: Math.round(h * 360),
    s: Math.round(s * 100),
    l: Math.round(l * 100)
  };
}

/**
 * Convert color string to HSL
 * @param {string} color - CSS color string
 * @returns {{h: number, s: number, l: number}|null}
 */
export function colorToHsl(color) {
  const rgb = parseColor(color);
  if (!rgb) return null;
  return rgbToHsl(rgb.r, rgb.g, rgb.b);
}

/**
 * Check if contrast ratio meets WCAG AA standard
 * @param {number} ratio - Contrast ratio
 * @param {boolean} isLargeText - Whether text is large (18pt+ or 14pt+ bold)
 * @returns {boolean}
 */
export function meetsWCAG_AA(ratio, isLargeText = false) {
  return isLargeText ? ratio >= 3 : ratio >= 4.5;
}

/**
 * Check if contrast ratio meets WCAG AAA standard
 * @param {number} ratio - Contrast ratio
 * @param {boolean} isLargeText - Whether text is large (18pt+ or 14pt+ bold)
 * @returns {boolean}
 */
export function meetsWCAG_AAA(ratio, isLargeText = false) {
  return isLargeText ? ratio >= 4.5 : ratio >= 7;
}

/**
 * Get saturation level from color
 * @param {string} color - CSS color string
 * @returns {number} Saturation percentage (0-100)
 */
export function getSaturation(color) {
  const hsl = colorToHsl(color);
  return hsl ? hsl.s : 0;
}

/**
 * Check if color is in red hue range
 * @param {string} color - CSS color string
 * @returns {boolean}
 */
export function isRedHue(color) {
  const hsl = colorToHsl(color);
  if (!hsl) return false;
  // Red hue is 0-30° or 330-360°
  return (hsl.h >= 0 && hsl.h <= 30) || (hsl.h >= 330 && hsl.h <= 360);
}

/**
 * Check if color is in orange hue range
 * @param {string} color - CSS color string
 * @returns {boolean}
 */
export function isOrangeHue(color) {
  const hsl = colorToHsl(color);
  if (!hsl) return false;
  // Orange hue is 30-60°
  return hsl.h >= 30 && hsl.h <= 60;
}

/**
 * Get luminance difference between two colors
 * @param {string} color1 - First color
 * @param {string} color2 - Second color
 * @returns {number} Absolute luminance difference (0-1)
 */
export function getLuminanceDifference(color1, color2) {
  const rgb1 = parseColor(color1);
  const rgb2 = parseColor(color2);
  
  if (!rgb1 || !rgb2) return 0;
  
  const lum1 = getLuminance(rgb1.r, rgb1.g, rgb1.b);
  const lum2 = getLuminance(rgb2.r, rgb2.g, rgb2.b);
  
  return Math.abs(lum1 - lum2);
}

/**
 * Check if color is dark (luminance < 0.3)
 * @param {string} color - CSS color string
 * @returns {boolean}
 */
export function isDarkColor(color) {
  const rgb = parseColor(color);
  if (!rgb) return false;
  return getLuminance(rgb.r, rgb.g, rgb.b) < 0.3;
}

/**
 * Get alpha channel value from color
 * @param {string} color - CSS color string
 * @returns {number} Alpha value (0-1)
 */
export function getAlpha(color) {
  const rgb = parseColor(color);
  return rgb ? rgb.a : 1;
}

/**
 * Check if background is semi-transparent
 * @param {string} color - CSS color string
 * @returns {boolean}
 */
export function isSemiTransparent(color) {
  const alpha = getAlpha(color);
  return alpha > 0 && alpha < 1;
}
