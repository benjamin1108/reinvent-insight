/**
 * Test Data Generator
 * Provides functions to generate random test data for components
 */

/**
 * Generate random integer between min and max (inclusive)
 * @param {number} min - Minimum value
 * @param {number} max - Maximum value
 * @returns {number}
 */
export function randomInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

/**
 * Generate random float between min and max
 * @param {number} min - Minimum value
 * @param {number} max - Maximum value
 * @returns {number}
 */
export function randomFloat(min, max) {
  return Math.random() * (max - min) + min;
}

/**
 * Pick random element from array
 * @param {Array} array - Array to pick from
 * @returns {*}
 */
export function randomChoice(array) {
  return array[randomInt(0, array.length - 1)];
}

/**
 * Generate random string
 * @param {number} length - String length
 * @returns {string}
 */
export function randomString(length) {
  const chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ';
  let result = '';
  for (let i = 0; i < length; i++) {
    result += chars.charAt(randomInt(0, chars.length - 1));
  }
  return result.trim();
}

/**
 * Generate random RGB color
 * @returns {{r: number, g: number, b: number, a: number}}
 */
export function randomColor() {
  return {
    r: randomInt(0, 255),
    g: randomInt(0, 255),
    b: randomInt(0, 255),
    a: randomFloat(0, 1)
  };
}

/**
 * Convert RGB object to CSS rgba string
 * @param {{r: number, g: number, b: number, a: number}} rgb
 * @returns {string}
 */
export function rgbToString(rgb) {
  return `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, ${rgb.a})`;
}

/**
 * Generate random spacing value in rem
 * @param {number} min - Minimum rem value
 * @param {number} max - Maximum rem value
 * @returns {string}
 */
export function randomSpacing(min = 0, max = 5) {
  const value = randomFloat(min, max);
  // Round to nearest 0.25rem
  const rounded = Math.round(value * 4) / 4;
  return `${rounded.toFixed(2)}rem`;
}

/**
 * Generate random card data
 * @returns {Object}
 */
export function generateCardData() {
  const years = ['2020', '2021', '2022', '2023', '2024'];
  const levels = ['100', '200', '300', '400', 'Keynote'];
  const summaryTypes = ['reinvent', 'other'];
  
  const year = randomChoice(years);
  const level = randomChoice(levels);
  const summaryType = randomChoice(summaryTypes);
  
  let titleEn = randomString(randomInt(40, 100));
  
  // Add re:Invent prefix for some titles
  if (summaryType === 'reinvent' && Math.random() > 0.5) {
    titleEn = `AWS re:Invent ${year} - ${titleEn}`;
  }
  
  return {
    titleEn,
    titleCn: randomString(randomInt(30, 80)),
    wordCount: randomInt(1000, 50000),
    year: Math.random() > 0.2 ? year : null,
    level: Math.random() > 0.2 ? level : null,
    summaryType,
    hash: Math.random().toString(36).substring(7),
    contentType: randomChoice(['pdf', 'youtube', 'other']),
    isPdf: Math.random() > 0.5
  };
}

/**
 * Generate array of card data
 * @param {number} count - Number of cards to generate
 * @returns {Object[]}
 */
export function generateCardDataArray(count) {
  return Array.from({ length: count }, () => generateCardData());
}

/**
 * Generate card data with specific properties
 * @param {Object} overrides - Properties to override
 * @returns {Object}
 */
export function generateCardDataWith(overrides = {}) {
  return {
    ...generateCardData(),
    ...overrides
  };
}

/**
 * Generate re:Invent card data
 * @returns {Object}
 */
export function generateReinventCardData() {
  const data = generateCardData();
  data.summaryType = 'reinvent';
  
  // Ensure it has re:Invent prefix
  if (!data.titleEn.toLowerCase().includes('reinvent')) {
    const year = data.year || '2024';
    data.titleEn = `AWS re:Invent ${year} - ${data.titleEn}`;
  }
  
  return data;
}

/**
 * Generate array of re:Invent card data
 * @param {number} count - Number of cards
 * @returns {Object[]}
 */
export function generateReinventCardDataArray(count) {
  return Array.from({ length: count }, () => generateReinventCardData());
}

/**
 * Generate varied titles (for testing title variation)
 * @param {number} count - Number of titles
 * @returns {string[]}
 */
export function generateVariedTitles(count) {
  const prefixes = [
    'Deep dive into',
    'Introduction to',
    'Advanced techniques for',
    'Best practices for',
    'Getting started with',
    'Optimizing',
    'Scaling',
    'Securing',
    'Monitoring',
    'Deploying'
  ];
  
  const topics = [
    'serverless architecture',
    'machine learning',
    'container orchestration',
    'data analytics',
    'cloud security',
    'microservices',
    'DevOps practices',
    'database optimization',
    'network infrastructure',
    'cost optimization'
  ];
  
  return Array.from({ length: count }, () => {
    const prefix = randomChoice(prefixes);
    const topic = randomChoice(topics);
    return `${prefix} ${topic}`;
  });
}

/**
 * Generate repetitive titles (for testing title variation)
 * @param {number} count - Number of titles
 * @param {string} prefix - Common prefix
 * @returns {string[]}
 */
export function generateRepetitiveTitles(count, prefix = 'AWS re:Invent 2024 -') {
  return Array.from({ length: count }, () => {
    return `${prefix} ${randomString(randomInt(20, 40))}`;
  });
}

/**
 * Generate test colors with specific properties
 * @param {Object} options - Color generation options
 * @returns {{r: number, g: number, b: number, a: number}}
 */
export function generateColorWith(options = {}) {
  const {
    minLuminance = 0,
    maxLuminance = 1,
    minSaturation = 0,
    maxSaturation = 100,
    hueRange = null, // [min, max] or null for any
    alpha = null
  } = options;
  
  let color;
  let attempts = 0;
  const maxAttempts = 100;
  
  do {
    color = randomColor();
    if (alpha !== null) {
      color.a = alpha;
    }
    attempts++;
  } while (attempts < maxAttempts && !meetsColorConstraints(color, options));
  
  return color;
}

/**
 * Check if color meets constraints
 * @param {{r: number, g: number, b: number, a: number}} color
 * @param {Object} options
 * @returns {boolean}
 */
function meetsColorConstraints(color, options) {
  // This is a simplified check - in real implementation,
  // you'd calculate actual luminance and saturation
  return true;
}

/**
 * Generate dark color (luminance < 0.3)
 * @returns {{r: number, g: number, b: number, a: number}}
 */
export function generateDarkColor() {
  return {
    r: randomInt(0, 76),
    g: randomInt(0, 76),
    b: randomInt(0, 76),
    a: randomFloat(0.1, 1)
  };
}

/**
 * Generate light color (luminance > 0.7)
 * @returns {{r: number, g: number, b: number, a: number}}
 */
export function generateLightColor() {
  return {
    r: randomInt(179, 255),
    g: randomInt(179, 255),
    b: randomInt(179, 255),
    a: randomFloat(0.1, 1)
  };
}

/**
 * Generate semi-transparent color
 * @returns {{r: number, g: number, b: number, a: number}}
 */
export function generateSemiTransparentColor() {
  const color = randomColor();
  color.a = randomFloat(0.1, 0.9);
  return color;
}
