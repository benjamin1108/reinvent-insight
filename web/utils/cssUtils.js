/**
 * CSS Utility Functions for Testing
 * Provides CSS property extraction, validation, and analysis
 */

/**
 * Get computed CSS property value
 * @param {HTMLElement} element - DOM element
 * @param {string} property - CSS property name
 * @returns {string} Computed value
 */
export function getComputedProperty(element, property) {
  return window.getComputedStyle(element).getPropertyValue(property);
}

/**
 * Get all computed padding values
 * @param {HTMLElement} element - DOM element
 * @returns {{top: number, right: number, bottom: number, left: number}}
 */
export function getPadding(element) {
  const style = window.getComputedStyle(element);
  return {
    top: parseFloat(style.paddingTop),
    right: parseFloat(style.paddingRight),
    bottom: parseFloat(style.paddingBottom),
    left: parseFloat(style.paddingLeft)
  };
}

/**
 * Get all computed margin values
 * @param {HTMLElement} element - DOM element
 * @returns {{top: number, right: number, bottom: number, left: number}}
 */
export function getMargin(element) {
  const style = window.getComputedStyle(element);
  return {
    top: parseFloat(style.marginTop),
    right: parseFloat(style.marginRight),
    bottom: parseFloat(style.marginBottom),
    left: parseFloat(style.marginLeft)
  };
}

/**
 * Convert rem to pixels
 * @param {number} rem - Rem value
 * @returns {number} Pixel value
 */
export function remToPx(rem) {
  return rem * parseFloat(getComputedStyle(document.documentElement).fontSize);
}

/**
 * Convert pixels to rem
 * @param {number} px - Pixel value
 * @returns {number} Rem value
 */
export function pxToRem(px) {
  return px / parseFloat(getComputedStyle(document.documentElement).fontSize);
}

/**
 * Check if element has transition property defined
 * @param {HTMLElement} element - DOM element
 * @returns {boolean}
 */
export function hasTransition(element) {
  const transition = getComputedProperty(element, 'transition');
  return transition !== 'all 0s ease 0s' && transition !== 'none';
}

/**
 * Get gap value from flex/grid container
 * @param {HTMLElement} element - DOM element
 * @returns {number} Gap in pixels
 */
export function getGap(element) {
  const gap = getComputedProperty(element, 'gap');
  return parseFloat(gap) || 0;
}

/**
 * Check if element uses CSS custom property for a given property
 * @param {HTMLElement} element - DOM element
 * @param {string} property - CSS property name
 * @returns {boolean}
 */
export function usesCustomProperty(element, property) {
  // Get inline style
  const inlineValue = element.style.getPropertyValue(property);
  if (inlineValue && inlineValue.includes('var(--')) {
    return true;
  }
  
  // Check computed style (this won't show var() but we can check if custom props are defined)
  const computedValue = getComputedProperty(element, property);
  
  // Get all stylesheets and check for var() usage
  for (const sheet of document.styleSheets) {
    try {
      for (const rule of sheet.cssRules || []) {
        if (rule.style && rule.style.getPropertyValue(property)) {
          const value = rule.style.getPropertyValue(property);
          if (value.includes('var(--')) {
            return true;
          }
        }
      }
    } catch (e) {
      // Cross-origin stylesheet, skip
      continue;
    }
  }
  
  return false;
}

/**
 * Validate BEM class name
 * @param {string} className - Class name to validate
 * @returns {boolean}
 */
export function isValidBEMClassName(className) {
  // BEM pattern: block__element--modifier
  // Block: [a-z][a-z0-9-]*
  // Element: __[a-z][a-z0-9-]*
  // Modifier: --[a-z][a-z0-9-]*
  
  const bemPattern = /^[a-z][a-z0-9-]*(__[a-z][a-z0-9-]*)?(--[a-z][a-z0-9-]*)?$/;
  return bemPattern.test(className);
}

/**
 * Get all class names from element
 * @param {HTMLElement} element - DOM element
 * @returns {string[]}
 */
export function getClassNames(element) {
  return Array.from(element.classList);
}

/**
 * Check if all class names follow BEM convention
 * @param {HTMLElement} element - DOM element
 * @returns {boolean}
 */
export function followsBEMConvention(element) {
  const classNames = getClassNames(element);
  return classNames.every(isValidBEMClassName);
}

/**
 * Get spacing scale consistency
 * @param {number[]} values - Array of spacing values in pixels
 * @param {number} baseUnit - Base unit in pixels (default: 4px = 0.25rem)
 * @returns {boolean}
 */
export function isConsistentSpacingScale(values, baseUnit = 4) {
  return values.every(value => {
    const remainder = value % baseUnit;
    return remainder < 0.1 || remainder > baseUnit - 0.1; // Allow small floating point errors
  });
}

/**
 * Check if element has ARIA label or role
 * @param {HTMLElement} element - DOM element
 * @returns {boolean}
 */
export function hasAccessibilityAttributes(element) {
  return !!(
    element.getAttribute('aria-label') ||
    element.getAttribute('aria-labelledby') ||
    element.getAttribute('role') ||
    element.getAttribute('aria-describedby')
  );
}

/**
 * Get vertical center alignment of elements
 * @param {HTMLElement[]} elements - Array of elements
 * @returns {boolean} True if all elements share same vertical center
 */
export function areVerticallyCentered(elements) {
  if (elements.length < 2) return true;
  
  const centers = elements.map(el => {
    const rect = el.getBoundingClientRect();
    return rect.top + rect.height / 2;
  });
  
  const first = centers[0];
  const tolerance = 2; // 2px tolerance
  
  return centers.every(center => Math.abs(center - first) <= tolerance);
}

/**
 * Get opacity from element
 * @param {HTMLElement} element - DOM element
 * @returns {number} Opacity value (0-1)
 */
export function getOpacity(element) {
  return parseFloat(getComputedProperty(element, 'opacity'));
}

/**
 * Check if background is transparent
 * @param {HTMLElement} element - DOM element
 * @returns {boolean}
 */
export function hasTransparentBackground(element) {
  const bg = getComputedProperty(element, 'background-color');
  return bg === 'rgba(0, 0, 0, 0)' || bg === 'transparent';
}

/**
 * Get font weight
 * @param {HTMLElement} element - DOM element
 * @returns {number}
 */
export function getFontWeight(element) {
  return parseInt(getComputedProperty(element, 'font-weight'));
}

/**
 * Get font size in pixels
 * @param {HTMLElement} element - DOM element
 * @returns {number}
 */
export function getFontSize(element) {
  return parseFloat(getComputedProperty(element, 'font-size'));
}

/**
 * Check if text is large (18pt+ or 14pt+ bold)
 * @param {HTMLElement} element - DOM element
 * @returns {boolean}
 */
export function isLargeText(element) {
  const fontSize = getFontSize(element);
  const fontWeight = getFontWeight(element);
  
  // 18pt = 24px, 14pt = 18.67px
  return fontSize >= 24 || (fontSize >= 18.67 && fontWeight >= 700);
}

/**
 * Get line height
 * @param {HTMLElement} element - DOM element
 * @returns {number}
 */
export function getLineHeight(element) {
  return parseFloat(getComputedProperty(element, 'line-height'));
}

/**
 * Get letter spacing
 * @param {HTMLElement} element - DOM element
 * @returns {number}
 */
export function getLetterSpacing(element) {
  const spacing = getComputedProperty(element, 'letter-spacing');
  return spacing === 'normal' ? 0 : parseFloat(spacing);
}

/**
 * Calculate variance of an array of numbers
 * @param {number[]} values - Array of numbers
 * @returns {number}
 */
export function calculateVariance(values) {
  if (values.length === 0) return 0;
  
  const mean = values.reduce((sum, val) => sum + val, 0) / values.length;
  const squaredDiffs = values.map(val => Math.pow(val - mean, 2));
  return squaredDiffs.reduce((sum, val) => sum + val, 0) / values.length;
}

/**
 * Check if values are consistent (low variance)
 * @param {number[]} values - Array of numbers
 * @param {number} maxVariance - Maximum allowed variance
 * @returns {boolean}
 */
export function areValuesConsistent(values, maxVariance) {
  return calculateVariance(values) <= maxVariance;
}
