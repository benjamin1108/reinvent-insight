/**
 * Title Processing Utilities
 * Provides functions for smart title processing and formatting
 */

/**
 * Process card title by removing redundant prefixes
 * @param {string} title - Original title
 * @param {string} summaryType - Type of summary ('reinvent' or 'other')
 * @param {boolean} inFilteredSection - Whether card is in a filtered section
 * @returns {string} Processed title
 */
export function processCardTitle(title, summaryType, inFilteredSection = false) {
  // Error handling: return empty string for invalid input
  if (!title || typeof title !== 'string') {
    console.warn('processCardTitle: Invalid title input', title);
    return '';
  }
  
  try {
    // Remove "AWS re:Invent YYYY -" prefix when in re:Invent section
    if (summaryType === 'reinvent' && inFilteredSection) {
      // Match patterns like:
      // "AWS re:Invent 2024 - "
      // "AWS re:Invent 2024: "
      // "AWS re:Invent 2024 – " (em dash)
      const reinventPattern = /^AWS\s+re:Invent\s+\d{4}\s*[-:–]\s*/i;
      title = title.replace(reinventPattern, '');
    }
    
    return title.trim();
  } catch (error) {
    // Fallback: return original title if processing fails
    console.error('processCardTitle: Error processing title', error);
    return title;
  }
}

/**
 * Extract year from title
 * @param {string} title - Title string
 * @returns {string|null} Year or null if not found
 */
export function extractYearFromTitle(title) {
  if (!title) return null;
  
  const yearMatch = title.match(/\b(20\d{2})\b/);
  return yearMatch ? yearMatch[1] : null;
}

/**
 * Check if title starts with re:Invent prefix
 * @param {string} title - Title string
 * @returns {boolean}
 */
export function hasReinventPrefix(title) {
  if (!title) return false;
  
  const reinventPattern = /^AWS\s+re:Invent\s+\d{4}/i;
  return reinventPattern.test(title);
}

/**
 * Get first N characters of title for comparison
 * @param {string} title - Title string
 * @param {number} length - Number of characters
 * @returns {string}
 */
export function getTitlePrefix(title, length = 10) {
  if (!title) return '';
  return title.substring(0, length).toLowerCase();
}

/**
 * Calculate title variation ratio in a collection
 * @param {string[]} titles - Array of titles
 * @param {number} prefixLength - Length of prefix to compare
 * @returns {number} Ratio of unique prefixes (0-1)
 */
export function calculateTitleVariation(titles, prefixLength = 10) {
  if (!titles || titles.length === 0) return 0;
  
  const prefixes = titles.map(title => getTitlePrefix(title, prefixLength));
  const uniquePrefixes = new Set(prefixes);
  
  return uniquePrefixes.size / titles.length;
}

/**
 * Check if titles in collection are varied enough
 * @param {string[]} titles - Array of titles
 * @param {number} minVariation - Minimum variation ratio (default 0.7)
 * @returns {boolean}
 */
export function areTitlesVaried(titles, minVariation = 0.7) {
  const variation = calculateTitleVariation(titles);
  return variation >= minVariation;
}

/**
 * Truncate title to fit within max length
 * @param {string} title - Title string
 * @param {number} maxLength - Maximum length
 * @returns {string}
 */
export function truncateTitle(title, maxLength = 100) {
  if (!title || title.length <= maxLength) return title;
  
  // Try to break at word boundary
  const truncated = title.substring(0, maxLength);
  const lastSpace = truncated.lastIndexOf(' ');
  
  if (lastSpace > maxLength * 0.8) {
    return truncated.substring(0, lastSpace) + '...';
  }
  
  return truncated + '...';
}

/**
 * Format title for display with optional processing
 * @param {string} title - Original title
 * @param {Object} options - Processing options
 * @returns {string}
 */
export function formatTitle(title, options = {}) {
  const {
    summaryType = 'other',
    inFilteredSection = false,
    maxLength = null,
    preserveOriginal = false
  } = options;
  
  if (preserveOriginal) {
    return title;
  }
  
  let processed = processCardTitle(title, summaryType, inFilteredSection);
  
  if (maxLength) {
    processed = truncateTitle(processed, maxLength);
  }
  
  return processed;
}
